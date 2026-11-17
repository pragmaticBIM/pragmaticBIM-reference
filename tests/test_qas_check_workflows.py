"""Guard the QAS check workflows for award, cost interface and post-calculation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
QAS_PARENT = "pragmaticbim:workflow/qas"
LANGUAGES = {"de", "fr", "it", "en"}

WORKFLOWS = (
    ("qas-award-interface-visualization", "QAS-AWARD-INTERFACE", "koordination"),
    ("qas-cost-interface-tenant-fitout", "QAS-COST-INTERFACE", "koordination"),
    ("qas-element-cost-post-calculation", "QAS-ELEMENT-COST-POSTCALC", "fachpruefung"),
)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _referenced_workflows(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"needed_for_workflows", "activated_workflows"} and isinstance(value, list):
                found.update(str(item) for item in value)
            else:
                found |= _referenced_workflows(value)
    elif isinstance(node, list):
        for item in node:
            found |= _referenced_workflows(item)
    return found


def test_check_workflows_sit_under_qas() -> None:
    for slug, code, group in WORKFLOWS:
        workflow = _load_yaml(REPO_ROOT / "workflows" / f"{slug}.yaml")
        assert workflow["id"] == f"pragmaticbim:workflow/{slug}"
        assert workflow["code"] == code
        assert workflow["parent_workflow"] == QAS_PARENT
        assert workflow["workflow_group"] == group
        assert workflow["status"] == "active"
        assert isinstance(workflow["sort_order"], int)
        assert set(workflow["name"]) == LANGUAGES
        assert set(workflow["description"]) == LANGUAGES


def test_check_workflows_keep_their_references() -> None:
    element_refs: set[str] = set()
    for path in sorted((REPO_ROOT / "elements").glob("*.yaml")):
        element_refs |= _referenced_workflows(yaml.safe_load(path.read_text(encoding="utf-8")))
    goal_refs: set[str] = set()
    for path in sorted((REPO_ROOT / "project_goals").glob("*.yaml")):
        goal_refs |= _referenced_workflows(yaml.safe_load(path.read_text(encoding="utf-8")))

    for slug, _code, _group in WORKFLOWS:
        workflow_id = f"pragmaticbim:workflow/{slug}"
        assert workflow_id in element_refs, f"no element needs {workflow_id}"
        assert workflow_id in goal_refs, f"no project goal activates {workflow_id}"
