"""Merge gate for pragmaticBIM repositories.

Decides per pull request whether it may auto-merge, waits, goes back to the
author, or escalates to the maintainer. The rules are described in
MERGE_POLICY.md; the per-repository settings live in .github/merge-gate.json.
The same script runs in every repository; only the JSON differs.

The script never checks out or runs code from the pull request. It only reads
PR metadata through the GitHub API, so it is safe under pull_request_target.

required_checks in the JSON lists checks that must have reported before the
gate merges in direct mode (in auto_merge mode the branch ruleset does this).

Merge modes (merge_mode in the JSON):
  auto_merge  GitHub native auto-merge. Needs branch protection with required
              checks, so GitHub waits for them. Used on public repositories.
  direct      The gate waits for all other checks on the head commit itself
              and then merges through the REST API. Used where GitHub offers
              no branch protection (private repositories on GitHub Free).
              Nothing stops a direct push there; the gate only covers PRs.

AI review (optional, require_ai_review in the JSON): when set, the PR also
needs a commit status named "ai-review" with state success on its head commit.
Any reviewer (for example the Gemini step in Orchestrator) can post it:
  gh api repos/OWNER/REPO/statuses/SHA -f context=ai-review -f state=success

Environment:
  GITHUB_TOKEN       token of the workflow (labels, comments, direct merge)
  AUTOMERGE_TOKEN    optional fine-grained PAT of the maintainer; in
                     auto_merge mode it enables native auto-merge. Without it
                     the gate labels the PR "automerge-ready" and the
                     maintainer clicks "Enable auto-merge".
  GITHUB_REPOSITORY  owner/repo
  PR_NUMBER          pull request number, or
  STATUS_SHA         commit sha from a status event (gate looks up its PRs)
  GATE_CONFIG        path of the JSON (default .github/merge-gate.json)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# --- Policy --------------------------------------------------------------

AI_REVIEW_CONTEXT = "ai-review"
GATE_CHECK_NAME = "gate"  # job name in merge-gate.yml, ignored when waiting for checks

LABEL_READY = "automerge-ready"
LABEL_ESCALATE = "needs-maintainer"
LABEL_BLOCK = "do-not-merge"

MAX_CHANGE_REQUEST_ROUNDS = 2
DIRECT_WAIT_SECONDS = 25 * 60
DIRECT_POLL_SECONDS = 30

COMMENT_MARKER = "<!-- merge-gate -->"


@dataclass
class Config:
    base_branch: str
    maintainer: str
    trusted_authors: frozenset[str]
    auto_merge_paths: tuple[str, ...]
    auto_merge_suffixes: tuple[str, ...]
    max_files: int = 25
    max_changed_lines: int = 400
    merge_mode: str = "auto_merge"
    require_ai_review: bool = False
    required_checks: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: str | os.PathLike) -> "Config":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        cfg = cls(
            base_branch=raw["base_branch"],
            maintainer=raw["maintainer"],
            trusted_authors=frozenset(raw["trusted_authors"]),
            auto_merge_paths=tuple(raw["auto_merge_paths"]),
            auto_merge_suffixes=tuple(raw.get("auto_merge_suffixes", [])),
            max_files=raw.get("max_files", 25),
            max_changed_lines=raw.get("max_changed_lines", 400),
            merge_mode=raw.get("merge_mode", "auto_merge"),
            require_ai_review=raw.get("require_ai_review", False),
            required_checks=tuple(raw.get("required_checks", [])),
        )
        if cfg.merge_mode not in ("auto_merge", "direct"):
            raise ValueError(f"unknown merge_mode {cfg.merge_mode!r}")
        return cfg

    def in_auto_lane(self, filename: str) -> bool:
        """A path in the auto lane: an exact listed file, or a file under a
        listed folder (entry ending in "/") with an allowed suffix."""
        for entry in self.auto_merge_paths:
            if entry.endswith("/"):
                if filename.startswith(entry) and (
                    not self.auto_merge_suffixes or filename.endswith(self.auto_merge_suffixes)
                ):
                    return True
            elif filename == entry:
                return True
        return False


# --- Decision logic (pure, unit tested) ---------------------------------

@dataclass
class Decision:
    action: str  # "automerge" | "wait" | "fix" | "escalate"
    reasons: list[str] = field(default_factory=list)


def evaluate(
    cfg: Config,
    pr: dict,
    files: list[dict],
    labels: set[str],
    reviews: list[str],
    unresolved_threads: int,
    checks: str | None,
    ai_review: str | None = None,
) -> Decision:
    """Return the gate decision for one pull request.

    pr: GitHub PR object (user.login, base.ref, head.repo.full_name,
        base.repo.full_name, draft)
    files: GitHub PR file objects (filename, status, additions, deletions)
    reviews: states of submitted reviews (APPROVED / CHANGES_REQUESTED), oldest first
    checks: combined state of the other checks on the head commit:
            "success", "pending", "failure" or None (no checks)
    ai_review: state of the "ai-review" status, used when cfg.require_ai_review
    """
    escalate: list[str] = []

    author = pr["user"]["login"]
    if author not in cfg.trusted_authors:
        escalate.append(f"author `{author}` is not on the auto-merge list")

    head_repo = (pr.get("head") or {}).get("repo") or {}
    if head_repo.get("full_name") != pr["base"]["repo"]["full_name"]:
        escalate.append("PR comes from a fork")

    if pr["base"]["ref"] != cfg.base_branch:
        escalate.append(f"base branch is `{pr['base']['ref']}`, not `{cfg.base_branch}`")

    outside = [f["filename"] for f in files if not cfg.in_auto_lane(f["filename"])]
    if outside:
        shown = ", ".join(f"`{p}`" for p in outside[:5])
        more = f" and {len(outside) - 5} more" if len(outside) > 5 else ""
        escalate.append(f"touches files outside the auto-merge lane: {shown}{more}")

    removed = [f["filename"] for f in files if f["status"] in ("removed", "renamed")]
    if removed:
        shown = ", ".join(f"`{p}`" for p in removed[:5])
        escalate.append(f"removes or renames files: {shown}")

    if len(files) > cfg.max_files:
        escalate.append(f"{len(files)} files changed (limit {cfg.max_files})")

    changed = sum(f["additions"] + f["deletions"] for f in files)
    if changed > cfg.max_changed_lines:
        escalate.append(f"{changed} lines changed (limit {cfg.max_changed_lines})")

    for label in (LABEL_ESCALATE, LABEL_BLOCK):
        if label in labels:
            escalate.append(f"label `{label}` is set")

    if cfg.require_ai_review and ai_review in ("failure", "error"):
        escalate.append("AI review failed or could not complete")

    rounds = sum(1 for s in reviews if s == "CHANGES_REQUESTED")
    if rounds >= MAX_CHANGE_REQUEST_ROUNDS:
        escalate.append(f"changes were requested {rounds} times")

    if escalate:
        return Decision("escalate", escalate)

    if pr.get("draft"):
        return Decision("wait", ["PR is a draft"])

    if cfg.require_ai_review and ai_review != "success":
        return Decision("wait", ["AI review not finished"])

    fix: list[str] = []
    if reviews and reviews[-1] == "CHANGES_REQUESTED":
        fix.append("a reviewer requested changes")
    if unresolved_threads:
        fix.append(f"{unresolved_threads} unresolved review thread(s)")
    if checks == "failure":
        fix.append("a check failed")
    if fix:
        return Decision("fix", fix)

    return Decision("automerge", ["low-risk change within the auto-merge lane"])


def combine_checks(
    check_runs: list[dict], statuses: list[dict], ignore: set[str], required: tuple[str, ...] = ()
) -> str | None:
    """Fold check runs and commit statuses into one state; names in ignore are skipped.

    A required check that has not reported yet counts as pending, so the gate
    never merges in the gap before CI has registered its runs.
    """
    seen = {r["name"] for r in check_runs} | {s["context"] for s in statuses}
    states: list[str] = ["pending" for name in required if name not in seen]
    for run in check_runs:
        if run["name"] in ignore:
            continue
        if run["status"] != "completed":
            states.append("pending")
        elif run["conclusion"] in ("failure", "timed_out", "cancelled", "action_required", "startup_failure"):
            states.append("failure")
        else:  # success, neutral, skipped
            states.append("success")
    for status in statuses:
        if status["context"] in ignore:
            continue
        states.append({"error": "failure"}.get(status["state"], status["state"]))
    if not states:
        return None
    if "failure" in states:
        return "failure"
    if "pending" in states:
        return "pending"
    return "success"


# --- GitHub API ----------------------------------------------------------

API = "https://api.github.com"


def _request(method: str, url: str, token: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url if url.startswith("http") else API + url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _paged(path: str, token: str, key: str | None = None) -> list:
    out, page = [], 1
    sep = "&" if "?" in path else "?"
    while True:
        batch = _request("GET", f"{path}{sep}per_page=100&page={page}", token)
        items = batch[key] if key else batch
        out.extend(items)
        if len(items) < 100:
            return out
        page += 1


def _graphql(query: str, variables: dict, token: str) -> dict:
    result = _request("POST", "/graphql", token, {"query": query, "variables": variables})
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]


def unresolved_thread_count(repo: str, number: int, token: str) -> int:
    owner, name = repo.split("/")
    data = _graphql(
        """query($owner:String!,$name:String!,$number:Int!){
             repository(owner:$owner,name:$name){
               pullRequest(number:$number){
                 reviewThreads(first:100){ nodes{ isResolved } } } } }""",
        {"owner": owner, "name": name, "number": number},
        token,
    )
    nodes = data["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return sum(1 for n in nodes if not n["isResolved"])


def head_state(cfg: Config, repo: str, sha: str, token: str) -> tuple[str | None, str | None]:
    """Return (combined state of other checks, state of the ai-review status)."""
    runs = _paged(f"/repos/{repo}/commits/{sha}/check-runs", token, key="check_runs")
    statuses = _request("GET", f"/repos/{repo}/commits/{sha}/status", token).get("statuses", [])
    ai = next((s["state"] for s in statuses if s["context"] == AI_REVIEW_CONTEXT), None)
    return combine_checks(runs, statuses, {GATE_CHECK_NAME, AI_REVIEW_CONTEXT}, cfg.required_checks), ai


def set_labels(repo: str, number: int, add: str | None, current: set[str], token: str) -> None:
    for label in (LABEL_READY, LABEL_ESCALATE):
        if label != add and label in current:
            try:
                _request("DELETE", f"/repos/{repo}/issues/{number}/labels/{label}", token)
            except urllib.error.HTTPError:
                pass
    if add and add not in current:
        _request("POST", f"/repos/{repo}/issues/{number}/labels", token, {"labels": [add]})


def upsert_comment(repo: str, number: int, body: str, token: str) -> None:
    body = f"{COMMENT_MARKER}\n{body}"
    for comment in _paged(f"/repos/{repo}/issues/{number}/comments", token):
        if comment["body"].startswith(COMMENT_MARKER):
            if comment["body"] != body:
                _request("PATCH", comment["url"], token, {"body": body})
            return
    _request("POST", f"/repos/{repo}/issues/{number}/comments", token, {"body": body})


def set_auto_merge(pr: dict, enable: bool, token: str) -> None:
    if enable:
        _graphql(
            """mutation($id:ID!){ enablePullRequestAutoMerge(input:{
                 pullRequestId:$id, mergeMethod:SQUASH}){ clientMutationId } }""",
            {"id": pr["node_id"]},
            token,
        )
    elif pr.get("auto_merge"):
        _graphql(
            """mutation($id:ID!){ disablePullRequestAutoMerge(input:{
                 pullRequestId:$id}){ clientMutationId } }""",
            {"id": pr["node_id"]},
            token,
        )


def merge_directly(repo: str, pr: dict, token: str) -> None:
    """Squash-merge, but only if the head is still the commit the gate checked."""
    _request("PUT", f"/repos/{repo}/pulls/{pr['number']}/merge", token, {
        "merge_method": "squash",
        "sha": pr["head"]["sha"],
        "commit_title": f"{pr['title']} (#{pr['number']})",
    })


def render(cfg: Config, decision: Decision, outcome: str) -> str:
    title = {
        "automerge": {
            "enabled": "Auto-merge enabled",
            "merged": "Merged by the gate",
            "ready": "Ready for auto-merge",
        }.get(outcome, "Ready for auto-merge"),
        "wait": "Waiting",
        "fix": "Back to the author",
        "escalate": f"Escalated to @{cfg.maintainer}",
    }[decision.action]
    lines = [f"**Merge gate: {title}**", ""]
    lines += [f"- {r}" for r in decision.reasons]
    if decision.action == "automerge" and outcome == "ready":
        lines += ["", "A maintainer can click *Enable auto-merge*; it merges once all required checks pass."]
    if decision.action == "fix":
        lines += ["", "Fix the failing check or answer the review and resolve the threads. "
                      "A second change request escalates to the maintainer."]
    lines += ["", f"Rules: [MERGE_POLICY.md](../blob/{cfg.base_branch}/MERGE_POLICY.md)"]
    return "\n".join(lines)


def _snapshot(cfg: Config, repo: str, number: int, token: str):
    pr = _request("GET", f"/repos/{repo}/pulls/{number}", token)
    files = _paged(f"/repos/{repo}/pulls/{number}/files", token)
    labels = {l["name"] for l in pr["labels"]}
    reviews = [
        r["state"]
        for r in _paged(f"/repos/{repo}/pulls/{number}/reviews", token)
        if r["state"] in ("APPROVED", "CHANGES_REQUESTED")
    ]
    checks, ai = head_state(cfg, repo, pr["head"]["sha"], token)
    decision = evaluate(cfg, pr, files, labels, reviews,
                        unresolved_thread_count(repo, number, token), checks, ai)
    return pr, labels, checks, decision


def gate(cfg: Config, repo: str, number: int, token: str, automerge_token: str | None) -> Decision:
    pr, labels, checks, decision = _snapshot(cfg, repo, number, token)
    if pr["state"] != "open":
        return Decision("wait", ["PR is closed"])

    # Direct mode: wait for the other checks, then re-evaluate on fresh data.
    if cfg.merge_mode == "direct" and decision.action == "automerge" and checks == "pending":
        deadline = time.monotonic() + DIRECT_WAIT_SECONDS
        while checks == "pending" and time.monotonic() < deadline:
            time.sleep(DIRECT_POLL_SECONDS)
            pr, labels, checks, decision = _snapshot(cfg, repo, number, token)
        if checks == "pending" and decision.action == "automerge":
            decision = Decision("wait", ["checks still running; the next push or label change re-runs the gate"])

    outcome = ""
    if decision.action == "automerge":
        set_labels(repo, number, LABEL_READY, labels, token)
        if cfg.merge_mode == "direct":
            merge_directly(repo, pr, token)
            outcome = "merged"
        elif automerge_token:
            set_auto_merge(pr, True, automerge_token)
            outcome = "enabled"
        else:
            outcome = "ready"
    else:
        if cfg.merge_mode == "auto_merge":
            set_auto_merge(pr, False, automerge_token or token)
        if decision.action == "escalate":
            set_labels(repo, number, LABEL_ESCALATE, labels, token)
            try:
                _request("POST", f"/repos/{repo}/pulls/{number}/requested_reviewers", token,
                         {"reviewers": [cfg.maintainer]})
            except urllib.error.HTTPError:
                pass  # the maintainer authored the PR
        else:
            set_labels(repo, number, None, labels, token)

    if decision.action != "wait":
        upsert_comment(repo, number, render(cfg, decision, outcome), token)
    return decision


def main() -> int:
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    automerge_token = os.environ.get("AUTOMERGE_TOKEN") or None
    cfg = Config.load(os.environ.get("GATE_CONFIG", ".github/merge-gate.json"))

    numbers: list[int] = []
    if os.environ.get("PR_NUMBER"):
        numbers = [int(os.environ["PR_NUMBER"])]
    elif os.environ.get("STATUS_SHA"):
        prs = _request("GET", f"/repos/{repo}/commits/{os.environ['STATUS_SHA']}/pulls", token)
        numbers = [p["number"] for p in prs if p["state"] == "open"]

    for number in numbers:
        decision = gate(cfg, repo, number, token, automerge_token)
        print(f"PR #{number}: {decision.action} - {'; '.join(decision.reasons)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
