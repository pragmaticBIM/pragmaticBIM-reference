# Merge policy

How a change reaches `development` and then `main`: who may merge, when a pull request merges on its own, and when a person decides.

## Branches

| Branch | Role | Who merges |
| --- | --- | --- |
| `development` | target of every pull request, including the web application and coding agents | the merge gate (auto-merge) or the maintainer |
| `main` | released state | maintainer only, by a promotion pull request from `development` |

Nobody pushes directly to either branch. Everyone, including the web application and coding agents, works through pull requests from a branch or fork into `development`.

`development` is protected:

| Rule | Setting |
| --- | --- |
| Pull request required | yes, no direct pushes |
| Required checks | `tests` (GitHub Actions), `CodeRabbit` (review finished) |
| Conversations resolved | required, so open CodeRabbit findings block the merge |
| Applies to admins | yes |
| Force push, deletion | blocked |
| Merge method for auto-merge | squash |

`main` is protected:

| Rule | Setting |
| --- | --- |
| Pull request required | yes, from `development` only |
| Required checks | `tests` |
| Who can merge | maintainer only, no auto-merge |
| Force push, deletion | blocked |

## Review flow

1. A PR opens. CodeRabbit reviews it and the `tests` workflow runs.
2. The merge gate (`.github/workflows/merge-gate.yml`) runs on every push, label change and finished CodeRabbit review and decides one of four outcomes:

| Outcome | Meaning | Label |
| --- | --- | --- |
| **Auto-merge** | all criteria below met; merges once required checks pass | `automerge-ready` |
| **Wait** | draft, or CodeRabbit not finished | – |
| **Back to author** | CodeRabbit requested changes or threads are open | – |
| **Escalate** | a person decides; maintainer is requested as reviewer | `needs-maintainer` |

Every new commit re-runs the gate. If a new commit leaves the auto-merge lane, auto-merge is switched off.

## Auto-merge criteria

All must hold:

1. **Trusted author**: the maintainer or the web application (`elementplan-v3-local[bot]`). Branch in this repository, not a fork.
2. **Data only**: every changed file is a `.yaml` file in `elements/`, `values/`, `workflows/`, `project_goals/`, `domains/`, `models/`, `documents/`, `uses/`, `usage_scenarios/` or `room_types/`.
3. **Additive**: no file removed or renamed.
4. **Small**: at most 25 files and 400 changed lines.
5. **CodeRabbit clean**: review finished, last CodeRabbit verdict is not "changes requested", no unresolved review threads. CodeRabbit's pre-merge checks *No breaking data change* and *Four-language parity* pass.
6. **Checks green**: `tests` passes.
7. **No stop label**: neither `needs-maintainer` nor `do-not-merge` is set.

## Escalate when

The gate escalates automatically when any of these apply:

- the author is not on the trusted list, or the PR comes from a fork
- a file outside the data folders changes: `schema/`, `catalog/`, `generators/`, `render/`, `runner.py`, `scripts/`, `tests/`, `.github/`, `.coderabbit.yaml`, `requirements.txt`, `pytest.ini`, `project.yaml`, `phases/`, `components/`, `media/`, `LICENSE`, docs
- a file is removed or renamed
- more than 25 files or 400 lines change
- CodeRabbit cannot complete its review (status `failure`)
- CodeRabbit requested changes twice on the same PR
- someone sets `needs-maintainer` or `do-not-merge`

Escalate by hand (set `needs-maintainer`) when:

- an `id`, `code`, attribute, allowed value or IFC mapping would change meaning, even if CodeRabbit did not catch it
- a change rests on a norm (SIA, eBKP-H, HOAI, RIBA) and the source is not cited
- the author disagrees with a CodeRabbit finding: the maintainer decides, not the author resolving the thread
- a change affects licensing, published texts on pragmaticbim.ch, or the web application's data contract
- tests had to be loosened to pass

## Maintainer duties on escalation

1. Review within 3 working days.
2. Merge, request changes, or close with a reason.
3. To return a PR to the auto-merge lane after fixing the cause, remove `needs-maintainer`; the gate re-checks.

## Setup reference

- CodeRabbit: `.coderabbit.yaml`
- Gate rules: `.github/scripts/merge_gate.py`, tested in `tests/test_merge_gate.py`
- Automatic review requests: `.github/CODEOWNERS`
- Optional secret `AUTOMERGE_TOKEN`: fine-grained token of the maintainer, this repository only, *Contents* and *Pull requests* read/write. It can enable auto-merge on `development` only, since `main` requires the maintainer. With it the gate switches auto-merge on by itself; without it the gate labels `automerge-ready` and the maintainer clicks *Enable auto-merge*.
