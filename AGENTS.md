# Agent workflow

Standing instructions for every coding agent working on the pragmaticBIM Reference. How changes are merged: [MERGE_POLICY.md](MERGE_POLICY.md). Structure and writing style: [CONTRIBUTING.md](CONTRIBUTING.md) and [`.cursor/rules/`](.cursor/rules/).

## Issues and labels

Labels are the state machine. Only the maintainer sets `agent_ready`.

| Label | Meaning |
|-------|---------|
| `agent_ready` | Well-specified; an agent may take it |
| `agent_working` | An agent has picked it up |
| `agent_finished` | PR is open; waiting for the merge gate or the maintainer |
| `needs-maintainer` | Agent is blocked or needs a decision |

- Only work on issues labeled `agent_ready`.
- Before pickup, check the issue's dependencies: `gh api repos/{owner}/{repo}/issues/{n}/dependencies/blocked_by`. If any blocking issue is still open (in any repo), do not start: leave `agent_ready` on, comment "Blocked by #…" once, and pick another issue.
- **Parent issues and epics:** an `agent_ready` issue with sub-issues (`gh api repos/{owner}/{repo}/issues/{n}/sub_issues`) is worked through its open sub-issues in order. Check each sub-issue's blockers before starting it. One branch and PR per sub-issue (`feature/issue-<sub>`, `Closes #<sub>`). Labels move on the sub-issue being worked; the parent keeps `agent_working` until all sub-issues are closed. An epic with a checklist but no sub-issues is not worked as a whole: comment with the proposed split into sub-issues, add `needs-maintainer`, and stop.
- When writing an issue that depends on another, name it under "Depends on" and add it as blocked-by: `gh api -X POST repos/{owner}/{repo}/issues/{n}/dependencies/blocked_by -F issue_id=<blocker's id>` (the numeric `id`, not the number).
- On pickup: remove `agent_ready`, add `agent_working`.
- After opening the PR (with `Closes #N`): remove `agent_working`, add `agent_finished`.
- If the issue is unclear, needs a content or modelling decision, or would require touching a protected path (below): comment on the issue with a concrete question (offer options where possible), remove `agent_working`, add `needs-maintainer`, and stop. Do not guess.

## Branches and pull requests

- Branch from `main`. Name the branch `feature/issue-<number>`, e.g. `feature/issue-42`.
- One issue = one PR, opened against `main`. The PR description contains `Closes #<number>`.
- Never push to `main` directly. Everyone works through pull requests.
- Do not enable auto-merge yourself. The merge gate decides (see MERGE_POLICY.md); a PR it escalates waits for the maintainer.

## Interactive sessions (no issue number)

- If the current branch is not `main`, stay on it: commit there, no new branch, no new PR.
- On `main`, ask for a branch name before changing anything.
- Push only when asked. Open the PR only when asked.
- Commit only your own changes: stage explicit files, never `git add -A`.

## Before opening the PR

1. `python -m pytest` passes.
2. `python scripts/audit_translations.py --gaps --lint --placeholders` is clean, and `--consistency` reports no new findings.
3. Every new or changed `name`, `definition` and `description` is filled in de, fr, it and en, written from German as `.cursor/rules/*-style.mdc` describes.
4. Behaviour changes in `catalog/`, `checks/`, `generators/` or `scripts/` come with tests.

## Content rules

- **Norms and directives:** never copy text from a norm or directive. Paraphrase and cite the clause (`rule_source.source_quote`, e.g. `VKF 15-15, Ziff. 3.2.3`). Licensed norms (SIA, SN EN) may only be used through extractions the maintainer provides; never take requirement values for them from memory.
- **Rules:** set `rule_status` and `rule_source`, but leave `reviewed_by` and `reviewed_at` empty. Only a person sets them.
- **SHACL:** a rule with `rule_status: shacl_defined` needs a passing and a failing test graph once the test harness exists (#70).
- **Ids and codes:** never change the meaning of an existing `id`, `code`, attribute, allowed value or IFC mapping. Deprecate with `status` and add a new entry instead.

## Do not touch

Changes in these paths need the maintainer. If an issue requires them, set `needs-maintainer` instead.

- **Repo tooling and merge rules:** `.github/`, `MERGE_POLICY.md`, `.coderabbit.yaml`
- **License and published texts:** `LICENSE`, `README.md`
- **Release state:** `project.yaml`, version tags
