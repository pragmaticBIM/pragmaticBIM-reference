"""Unit tests for the merge gate decision rules (MERGE_POLICY.md)."""

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "merge_gate", Path(__file__).resolve().parents[1] / ".github" / "scripts" / "merge_gate.py"
)
gate = importlib.util.module_from_spec(_spec)
sys.modules["merge_gate"] = gate
_spec.loader.exec_module(gate)

REPO = {"full_name": "pragmaticBIM/pragmaticBIM-reference"}


def pr(author="simondilhas", fork=False, base="main", draft=False):
    head_repo = {"full_name": "someone/fork"} if fork else REPO
    return {
        "user": {"login": author},
        "base": {"ref": base, "repo": REPO},
        "head": {"repo": head_repo},
        "draft": draft,
    }


def f(name, status="modified", add=5, delete=2):
    return {"filename": name, "status": status, "additions": add, "deletions": delete}


DATA = [f("elements/wall.yaml"), f("values/ebkp-h-mep-heat-emit.yaml", status="added")]


def run(p=None, files=DATA, labels=(), status="success", reviews=(), threads=0):
    return gate.evaluate(p or pr(), files, set(labels), status, list(reviews), threads)


def test_clean_data_change_auto_merges():
    assert run().action == "automerge"


def test_web_app_bot_auto_merges():
    assert run(pr(author="elementplan-v3-local[bot]")).action == "automerge"


def test_approved_after_fix_auto_merges():
    assert run(reviews=["CHANGES_REQUESTED", "APPROVED"]).action == "automerge"


def test_unknown_author_escalates():
    assert run(pr(author="stranger")).action == "escalate"


def test_fork_escalates():
    assert run(pr(fork=True)).action == "escalate"


def test_other_base_escalates():
    assert run(pr(base="release")).action == "escalate"


def test_schema_change_escalates():
    d = run(files=DATA + [f("schema/component.schema.json")])
    assert d.action == "escalate"
    assert "schema/component.schema.json" in d.reasons[0]


def test_tests_ci_and_phases_escalate():
    for path in ("tests/test_units.py", ".github/workflows/checks.yml", "phases/sia-112.yaml",
                 "components/door.yaml", "requirements.txt", ".coderabbit.yaml"):
        assert run(files=[f(path)]).action == "escalate", path


def test_removed_or_renamed_file_escalates():
    assert run(files=[f("elements/wall.yaml", status="removed")]).action == "escalate"
    assert run(files=[f("values/x.yaml", status="renamed")]).action == "escalate"


def test_size_limits_escalate():
    many = [f(f"values/v{i}.yaml") for i in range(gate.MAX_FILES + 1)]
    assert run(files=many).action == "escalate"
    big = [f("elements/wall.yaml", add=gate.MAX_CHANGED_LINES, delete=1)]
    assert run(files=big).action == "escalate"


def test_labels_escalate():
    assert run(labels=["needs-maintainer"]).action == "escalate"
    assert run(labels=["do-not-merge"]).action == "escalate"


def test_coderabbit_failure_escalates():
    assert run(status="failure").action == "escalate"


def test_second_change_request_escalates():
    d = run(reviews=["CHANGES_REQUESTED", "CHANGES_REQUESTED"])
    assert d.action == "escalate"


def test_first_change_request_goes_back_to_author():
    assert run(reviews=["CHANGES_REQUESTED"]).action == "fix"


def test_unresolved_threads_go_back_to_author():
    assert run(threads=2).action == "fix"


def test_pending_review_and_draft_wait():
    assert run(status="pending").action == "wait"
    assert run(status=None).action == "wait"
    assert run(pr(draft=True)).action == "wait"
