from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_WORKFLOW = "pragmaticbim:workflow/qas-usage-agreement-verification"

STRUCTURAL = {"DesignAreaLoad", "DesignPointLoad", "VibrationRequirements"}
MEP = {
    "WinterTemperatureMin",
    "WinterTemperatureMax",
    "SummerTemperatureMin",
    "SummerTemperatureMax",
    "RelativeHumidityMin",
    "RelativeHumidityMax",
    "OutdoorAirFlowRate",
    "PeakOccupancy",
    "DailyOperatingHours",
    "RequiredIlluminance",
}


def _attributes(element: str) -> list[dict]:
    path = ROOT / "elements" / f"{element}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["attributes"]


def _names_by_pset(element: str, pset: str) -> set[str]:
    return {
        attribute["name"]
        for attribute in _attributes(element)
        if attribute.get("pset") == pset
    }


def _actual_name(name: str) -> str:
    return f"{name}Actual"


def test_structural_usage_agreement_has_matching_requirement_and_actual_sets() -> None:
    for element in ("spaces-interior", "spaces-exterior"):
        assert STRUCTURAL <= _names_by_pset(element, "ePset_SpaceRequirement")
        assert {_actual_name(name) for name in STRUCTURAL} <= _names_by_pset(
            element, "ePset_Space"
        )


def test_mep_usage_agreement_has_matching_requirement_and_actual_sets() -> None:
    assert MEP <= _names_by_pset("spaces-interior", "ePset_SpaceRequirement")
    assert {_actual_name(name) for name in MEP} <= _names_by_pset(
        "spaces-interior", "ePset_Space"
    )


def test_comparison_workflow_uses_every_requirement_and_actual_value() -> None:
    for element in ("spaces-interior", "spaces-exterior"):
        requirement_names = _names_by_pset(element, "ePset_SpaceRequirement")
        actual_names = {_actual_name(name) for name in requirement_names}
        for attribute in _attributes(element):
            if attribute.get("pset") == "ePset_SpaceRequirement":
                assert COMPARISON_WORKFLOW in attribute["needed_for_workflows"]
            if (
                attribute.get("pset") == "ePset_Space"
                and attribute["name"] in actual_names
            ):
                assert COMPARISON_WORKFLOW in attribute["needed_for_workflows"]


def test_structural_visualization_no_longer_aligns_the_usage_agreement() -> None:
    path = ROOT / "workflows" / "des-usage-agreement-visualization.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "und mit der Nutzungsvereinbarung abstimmen" not in workflow["description"]["de"]
