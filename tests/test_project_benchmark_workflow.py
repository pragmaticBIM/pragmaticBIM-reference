"""Guard the project-benchmark workflow and its space inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog.baseline import attribute_applies_to_all_workflows


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ID = "pragmaticbim:workflow/qas-project-benchmark"
LANGS = ("de", "fr", "it", "en")
LINKS = {
    ("spaces-interior", "LongName"),
    ("spaces-interior", "IsExternal"),
    ("spaces-exterior", "LongName"),
    ("spaces-exterior", "IsExternal"),
    ("architecture-window-exterior", "PredefinedType"),
    ("architecture-window-interior", "PredefinedType"),
    ("architecture-door-exterior", "PredefinedType"),
    ("architecture-door-interior", "PredefinedType"),
}


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_project_benchmark_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/qas-project-benchmark.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "QAS-BENCHMARK"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/qas"
    assert workflow["needed_in_domain"] == ["pragmaticbim:domain/architecture"]
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_benchmark_links_spaces_windows_and_doors() -> None:
    workflows = [
        _load(f"workflows/{path.name}")
        for path in sorted((ROOT / "workflows").glob("*.yaml"))
    ]
    linked: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "elements").glob("*.yaml")):
        element = yaml.safe_load(path.read_text(encoding="utf-8"))
        for attribute in element.get("attributes") or []:
            refs = attribute.get("needed_for_workflows") or []
            if WORKFLOW_ID not in refs:
                continue
            if attribute_applies_to_all_workflows(attribute, workflows):
                continue
            linked.add((path.stem, attribute["name"]))

    assert linked == LINKS


def test_project_benchmark_is_activated_at_high_planning_level() -> None:
    goal = _load("project_goals/planning-certainty.yaml")
    levels = {level["code"]: level for level in goal["levels"]}

    assert WORKFLOW_ID not in (levels["PLN-01"].get("activated_workflows") or [])
    assert WORKFLOW_ID not in (levels["PLN-02"].get("activated_workflows") or [])
    assert WORKFLOW_ID in levels["PLN-03"]["activated_workflows"]
