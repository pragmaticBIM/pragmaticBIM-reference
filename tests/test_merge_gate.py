"""Unit tests for the merge gate decision rules (MERGE_POLICY.md)."""

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("merge_gate", _ROOT / ".github" / "scripts" / "merge_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["merge_gate"] = gate
_spec.loader.exec_module(gate)

CFG = gate.Config.load(_ROOT / ".github" / "merge-gate.json")
REPO = {"full_name": "pragmaticBIM/pragmaticBIM-reference"}


def pr(author="simondilhas", fork=False, base=CFG.base_branch, draft=False):
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


def run(p=None, files=DATA, labels=(), reviews=(), threads=0, checks="success", ai=None, cfg=CFG):
    return gate.evaluate(cfg, p or pr(), files, set(labels), list(reviews), threads, checks, ai)


# --- config ---------------------------------------------------------------

def test_config_is_valid():
    assert CFG.base_branch == "development"
    assert CFG.merge_mode == "auto_merge"
    assert CFG.maintainer in CFG.trusted_authors


def test_unknown_merge_mode_rejected(tmp_path):
    p = tmp_path / "gate.json"
    p.write_text('{"base_branch":"main","maintainer":"m","trusted_authors":[],'
                 '"auto_merge_paths":[],"merge_mode":"yolo"}')
    with pytest.raises(ValueError):
        gate.Config.load(p)


def test_exact_file_entry_in_lane():
    cfg = gate.Config("main", "m", frozenset({"m"}), ("reference", "book/locales/"), (".yaml",))
    assert cfg.in_auto_lane("reference")
    assert cfg.in_auto_lane("book/locales/de.yaml")
    assert not cfg.in_auto_lane("reference/x.yaml")
    assert not cfg.in_auto_lane("book/locales/de.py")


# --- decisions ------------------------------------------------------------

def test_clean_data_change_auto_merges():
    assert run().action == "automerge"


def test_pending_checks_still_auto_merge():
    # native auto-merge waits for required checks itself
    assert run(checks="pending").action == "automerge"
    assert run(checks=None).action == "automerge"


def test_web_app_bot_auto_merges():
    assert run(pr(author="pragmaticbim-editor-staging[bot]")).action == "automerge"


def test_old_v3_bot_escalates():
    assert run(pr(author="elementplan-v3-local[bot]")).action == "escalate"


def test_approved_after_fix_auto_merges():
    assert run(reviews=["CHANGES_REQUESTED", "APPROVED"]).action == "automerge"


def test_unknown_author_escalates():
    assert run(pr(author="stranger")).action == "escalate"


def test_fork_escalates():
    assert run(pr(fork=True)).action == "escalate"


def test_other_base_escalates():
    assert run(pr(base="main")).action == "escalate"


def test_schema_change_escalates():
    d = run(files=DATA + [f("schema/component.schema.json")])
    assert d.action == "escalate"
    assert "schema/component.schema.json" in d.reasons[0]


def test_tests_ci_and_phases_escalate():
    for path in ("tests/test_units.py", ".github/workflows/checks.yml", ".github/merge-gate.json",
                 "phases/sia-112.yaml", "components/door.yaml", "requirements.txt"):
        assert run(files=[f(path)]).action == "escalate", path


def test_removed_or_renamed_file_escalates():
    assert run(files=[f("elements/wall.yaml", status="removed")]).action == "escalate"
    assert run(files=[f("values/x.yaml", status="renamed")]).action == "escalate"


def test_size_limits_escalate():
    many = [f(f"values/v{i}.yaml") for i in range(CFG.max_files + 1)]
    assert run(files=many).action == "escalate"
    big = [f("elements/wall.yaml", add=CFG.max_changed_lines, delete=1)]
    assert run(files=big).action == "escalate"


def test_labels_escalate():
    assert run(labels=["needs-maintainer"]).action == "escalate"
    assert run(labels=["do-not-merge"]).action == "escalate"


def test_second_change_request_escalates():
    assert run(reviews=["CHANGES_REQUESTED", "CHANGES_REQUESTED"]).action == "escalate"


def test_first_change_request_goes_back_to_author():
    assert run(reviews=["CHANGES_REQUESTED"]).action == "fix"


def test_unresolved_threads_go_back_to_author():
    assert run(threads=2).action == "fix"


def test_failed_check_goes_back_to_author():
    assert run(checks="failure").action == "fix"


def test_draft_waits():
    assert run(pr(draft=True)).action == "wait"


def test_ai_review_ignored_unless_required():
    assert run(ai=None).action == "automerge"
    assert run(ai="failure").action == "automerge"


def test_ai_review_when_required():
    cfg = gate.Config(**{**CFG.__dict__, "require_ai_review": True})
    assert run(cfg=cfg, ai=None).action == "wait"
    assert run(cfg=cfg, ai="pending").action == "wait"
    assert run(cfg=cfg, ai="success").action == "automerge"
    assert run(cfg=cfg, ai="failure").action == "escalate"


# --- check aggregation ----------------------------------------------------

def cr(name, status="completed", conclusion="success"):
    return {"name": name, "status": status, "conclusion": conclusion}


def test_combine_checks():
    ignore = {"gate", "ai-review"}
    assert gate.combine_checks([], [], ignore) is None
    assert gate.combine_checks([cr("gate", "in_progress", None)], [], ignore) is None
    assert gate.combine_checks([cr("tests"), cr("lint", conclusion="skipped")], [], ignore) == "success"
    assert gate.combine_checks([cr("tests", "queued", None)], [], ignore) == "pending"
    assert gate.combine_checks([cr("tests", conclusion="failure"), cr("x", "queued", None)], [], ignore) == "failure"
    assert gate.combine_checks([], [{"context": "ci", "state": "error"}], ignore) == "failure"
    assert gate.combine_checks([], [{"context": "ai-review", "state": "failure"}], ignore) is None


def test_missing_required_check_is_pending():
    ignore = {"gate"}
    assert gate.combine_checks([], [], ignore, ("tests",)) == "pending"
    assert gate.combine_checks([cr("other")], [], ignore, ("tests",)) == "pending"
    assert gate.combine_checks([cr("tests")], [], ignore, ("tests",)) == "success"
