"""Merge gate for the pragmaticBIM Reference.

Decides per pull request whether it may auto-merge, waits, goes back to the
author, or escalates to the maintainer. The rules are described in
MERGE_POLICY.md; keep both in sync.

The script never checks out or runs code from the pull request. It only reads
PR metadata through the GitHub API, so it is safe under pull_request_target.

Environment:
  GITHUB_TOKEN       token of the workflow (labels, comments, reviews)
  AUTOMERGE_TOKEN    optional fine-grained PAT of a maintainer who may push to
                     development; used only to enable auto-merge. Without it the gate
                     labels the PR "automerge-ready" and a maintainer clicks
                     "Enable auto-merge".
  GITHUB_REPOSITORY  owner/repo
  PR_NUMBER          pull request number, or
  STATUS_SHA         commit sha from a status event (gate looks up its PRs)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

# --- Policy --------------------------------------------------------------

BASE_BRANCH = "development"
MAINTAINER = "simondilhas"

# Authors whose PRs may auto-merge. Everyone else is reviewed by the maintainer.
TRUSTED_AUTHORS = frozenset({
    "simondilhas",
    "elementplan-v3-local[bot]",  # web application (elementplan.pragmaticbim.ch)
})

# Data folders where small, additive edits may auto-merge.
AUTO_MERGE_DIRS = (
    "elements/",
    "values/",
    "workflows/",
    "project_goals/",
    "domains/",
    "models/",
    "documents/",
    "uses/",
    "usage_scenarios/",
    "room_types/",
)
AUTO_MERGE_SUFFIXES = (".yaml", ".yml")

MAX_FILES = 25
MAX_CHANGED_LINES = 400
MAX_CHANGE_REQUEST_ROUNDS = 2

CODERABBIT_LOGIN = "coderabbitai[bot]"
CODERABBIT_STATUS = "CodeRabbit"

LABEL_READY = "automerge-ready"
LABEL_ESCALATE = "needs-maintainer"
LABEL_BLOCK = "do-not-merge"

COMMENT_MARKER = "<!-- merge-gate -->"


# --- Decision logic (pure, unit tested) ---------------------------------

@dataclass
class Decision:
    action: str  # "automerge" | "wait" | "fix" | "escalate"
    reasons: list[str] = field(default_factory=list)


def evaluate(
    pr: dict,
    files: list[dict],
    labels: set[str],
    coderabbit_status: str | None,
    coderabbit_reviews: list[str],
    unresolved_threads: int,
) -> Decision:
    """Return the gate decision for one pull request.

    pr: GitHub PR object (user.login, base.ref, head.repo.full_name,
        base.repo.full_name, draft)
    files: GitHub PR file objects (filename, status, additions, deletions)
    coderabbit_status: state of the CodeRabbit commit status on the head sha
    coderabbit_reviews: states of CodeRabbit reviews, oldest first
    """
    escalate: list[str] = []

    author = pr["user"]["login"]
    if author not in TRUSTED_AUTHORS:
        escalate.append(f"author `{author}` is not on the auto-merge list")

    head_repo = (pr.get("head") or {}).get("repo") or {}
    if head_repo.get("full_name") != pr["base"]["repo"]["full_name"]:
        escalate.append("PR comes from a fork")

    if pr["base"]["ref"] != BASE_BRANCH:
        escalate.append(f"base branch is `{pr['base']['ref']}`, not `{BASE_BRANCH}`")

    outside = [
        f["filename"]
        for f in files
        if not (
            f["filename"].startswith(AUTO_MERGE_DIRS)
            and f["filename"].endswith(AUTO_MERGE_SUFFIXES)
        )
    ]
    if outside:
        shown = ", ".join(f"`{p}`" for p in outside[:5])
        more = f" and {len(outside) - 5} more" if len(outside) > 5 else ""
        escalate.append(f"touches files outside the data folders: {shown}{more}")

    removed = [f["filename"] for f in files if f["status"] in ("removed", "renamed")]
    if removed:
        shown = ", ".join(f"`{p}`" for p in removed[:5])
        escalate.append(f"removes or renames files: {shown}")

    if len(files) > MAX_FILES:
        escalate.append(f"{len(files)} files changed (limit {MAX_FILES})")

    changed = sum(f["additions"] + f["deletions"] for f in files)
    if changed > MAX_CHANGED_LINES:
        escalate.append(f"{changed} lines changed (limit {MAX_CHANGED_LINES})")

    for label in (LABEL_ESCALATE, LABEL_BLOCK):
        if label in labels:
            escalate.append(f"label `{label}` is set")

    if coderabbit_status in ("failure", "error"):
        escalate.append("CodeRabbit could not complete its review")

    rounds = sum(1 for s in coderabbit_reviews if s == "CHANGES_REQUESTED")
    if rounds >= MAX_CHANGE_REQUEST_ROUNDS:
        escalate.append(f"CodeRabbit requested changes {rounds} times")

    if escalate:
        return Decision("escalate", escalate)

    if pr.get("draft"):
        return Decision("wait", ["PR is a draft"])

    if coderabbit_status != "success":
        return Decision("wait", ["CodeRabbit review not finished"])

    fix: list[str] = []
    if coderabbit_reviews and coderabbit_reviews[-1] == "CHANGES_REQUESTED":
        fix.append("CodeRabbit requested changes")
    if unresolved_threads:
        fix.append(f"{unresolved_threads} unresolved review thread(s)")
    if fix:
        return Decision("fix", fix)

    return Decision("automerge", ["low-risk data change, CodeRabbit review clean"])


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


def _paged(path: str, token: str) -> list:
    out, page = [], 1
    sep = "&" if "?" in path else "?"
    while True:
        batch = _request("GET", f"{path}{sep}per_page=100&page={page}", token)
        out.extend(batch)
        if len(batch) < 100:
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


def coderabbit_status_of(repo: str, sha: str, token: str) -> str | None:
    combined = _request("GET", f"/repos/{repo}/commits/{sha}/status", token)
    for status in combined.get("statuses", []):
        if status["context"] == CODERABBIT_STATUS:
            return status["state"]
    return None


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


def render(decision: Decision, auto_merge_enabled: bool) -> str:
    title = {
        "automerge": "Auto-merge enabled" if auto_merge_enabled else "Ready for auto-merge",
        "wait": "Waiting",
        "fix": "Back to the author",
        "escalate": f"Escalated to @{MAINTAINER}",
    }[decision.action]
    lines = [f"**Merge gate: {title}**", ""]
    lines += [f"- {r}" for r in decision.reasons]
    if decision.action == "automerge" and not auto_merge_enabled:
        lines += ["", "A maintainer can click *Enable auto-merge*; it merges once all required checks pass."]
    if decision.action == "fix":
        lines += ["", "Address or answer the CodeRabbit findings and resolve the threads. A second change request escalates to the maintainer."]
    lines += ["", "Rules: [MERGE_POLICY.md](../blob/development/MERGE_POLICY.md)"]
    return "\n".join(lines)


def gate(repo: str, number: int, token: str, automerge_token: str | None) -> Decision:
    pr = _request("GET", f"/repos/{repo}/pulls/{number}", token)
    if pr["state"] != "open":
        return Decision("wait", ["PR is closed"])
    files = _paged(f"/repos/{repo}/pulls/{number}/files", token)
    labels = {l["name"] for l in pr["labels"]}
    reviews = [
        r["state"]
        for r in _paged(f"/repos/{repo}/pulls/{number}/reviews", token)
        if r["user"]["login"] == CODERABBIT_LOGIN and r["state"] in ("APPROVED", "CHANGES_REQUESTED")
    ]
    decision = evaluate(
        pr,
        files,
        labels,
        coderabbit_status_of(repo, pr["head"]["sha"], token),
        reviews,
        unresolved_thread_count(repo, number, token),
    )

    enabled = False
    if decision.action == "automerge":
        set_labels(repo, number, LABEL_READY, labels, token)
        if automerge_token:
            set_auto_merge(pr, True, automerge_token)
            enabled = True
    else:
        set_auto_merge(pr, False, automerge_token or token)
        if decision.action == "escalate":
            set_labels(repo, number, LABEL_ESCALATE, labels, token)
            try:
                _request("POST", f"/repos/{repo}/pulls/{number}/requested_reviewers", token,
                         {"reviewers": [MAINTAINER]})
            except urllib.error.HTTPError:
                pass  # the maintainer authored the PR
        else:
            set_labels(repo, number, None, labels, token)

    if decision.action != "wait":
        upsert_comment(repo, number, render(decision, enabled), token)
    return decision


def main() -> int:
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    automerge_token = os.environ.get("AUTOMERGE_TOKEN") or None

    numbers: list[int] = []
    if os.environ.get("PR_NUMBER"):
        numbers = [int(os.environ["PR_NUMBER"])]
    elif os.environ.get("STATUS_SHA"):
        prs = _request("GET", f"/repos/{repo}/commits/{os.environ['STATUS_SHA']}/pulls", token)
        numbers = [p["number"] for p in prs if p["state"] == "open"]

    for number in numbers:
        decision = gate(repo, number, token, automerge_token)
        print(f"PR #{number}: {decision.action} - {'; '.join(decision.reasons)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
