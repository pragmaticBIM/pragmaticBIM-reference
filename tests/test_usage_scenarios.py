"""Usage scenario ids, uses and legacy ids."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "pragmaticbim:usage-scenario/"
OPTION = "pragmaticbim:scenario-option/"
USE = "pragmaticbim:use/"

WASTE_USES = (
    "arbeit", "beherbergung", "bildung", "gastronomie", "gesundheit", "labor", "logistik",
    "produktion", "rechenzentrum", "sport", "verkauf", "verkehr", "versammlung",
)
ORGANIC_USES = tuple(use for use in WASTE_USES if use != "labor") + ("wohnen",)
TOILET_USES = (
    "beherbergung", "bildung", "gastronomie", "gesundheit", "sport", "verkauf", "verkehr",
    "versammlung",
)
# Shared scenario → (uses that had a per-use copy, old option suffix → new option suffix).
SHARED = {
    "abfall-entsorgen": (
        WASTE_USES,
        {"kehricht": "kehricht", "papier": "papier", "glas": "glas", "pet": "pet"},
    ),
    "bioabfall-entsorgen": (
        ORGANIC_USES,
        {"im-abfallraum": "im-abfallraum", "aussen": "aussen"},
    ),
    "toiletten-benutzen": (
        TOILET_USES,
        {"separate": "separate", "all-gender": "all-gender"},
    ),
}


def _scenarios() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((REPO_ROOT / "usage_scenarios").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        assert data["id"] not in out, f"{path}: duplicate id"
        out[data["id"]] = data
    return out


def _use_ids() -> set[str]:
    return {
        yaml.safe_load(path.read_text(encoding="utf-8"))["id"]
        for path in (REPO_ROOT / "uses").glob("*.yaml")
    }


def _legacy_targets(scenarios: dict[str, dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    """Old scenario id → live scenario id, old option id → live option id."""
    live = set(scenarios)
    live_options = {option["id"] for item in scenarios.values() for option in item.get("options") or []}
    scenario_map: dict[str, str] = {}
    option_map: dict[str, str] = {}
    for scenario in scenarios.values():
        for old in scenario.get("legacy_ids") or []:
            assert old.startswith(SCENARIO), f"{scenario['id']}: {old}"
            assert old not in live, f"{scenario['id']}: legacy id {old} is still live"
            assert old not in scenario_map, f"{old} maps twice"
            scenario_map[old] = scenario["id"]
        for option in scenario.get("options") or []:
            for old in option.get("legacy_ids") or []:
                assert old.startswith(OPTION), f"{option['id']}: {old}"
                assert old not in live_options, f"{option['id']}: legacy id {old} is still live"
                assert old not in option_map, f"{old} maps twice"
                option_map[old] = option["id"]
    return scenario_map, option_map


def test_option_ids_unique() -> None:
    seen: set[str] = set()
    for scenario in _scenarios().values():
        for option in scenario.get("options") or []:
            assert option["id"] not in seen, f"duplicate option id {option['id']}"
            seen.add(option["id"])


def test_uses_reference_known_uses() -> None:
    known = _use_ids()
    for scenario in _scenarios().values():
        uses = scenario.get("uses") or []
        assert len(uses) == len(set(uses)), scenario["id"]
        assert not set(uses) - known, f"{scenario['id']}: unknown uses {sorted(set(uses) - known)}"
        for option in scenario.get("options") or []:
            if "uses" not in option:
                continue
            assert option["uses"], f"{option['id']}: empty uses"
            assert not set(option["uses"]) - set(uses), f"{option['id']}: uses outside the scenario's uses"


def test_legacy_ids_resolve_once() -> None:
    _legacy_targets(_scenarios())


def test_shared_scenarios_replace_per_use_copies() -> None:
    scenarios = _scenarios()
    scenario_map, option_map = _legacy_targets(scenarios)
    for slug, (uses, suffixes) in SHARED.items():
        scenario_id = SCENARIO + slug
        scenario = scenarios[scenario_id]
        assert scenario.get("scope") == "project", scenario_id
        assert "use" not in scenario, scenario_id
        assert set(scenario["uses"]) >= {USE + use for use in uses}, scenario_id
        for use in uses:
            old = f"{slug}-{use}"
            assert SCENARIO + old not in scenarios, f"per-use copy {old} still exists"
            assert scenario_map.get(SCENARIO + old) == scenario_id, f"{old} has no legacy mapping"
            for old_suffix, new_suffix in suffixes.items():
                old_option = f"{OPTION}{old}-{old_suffix}"
                assert option_map.get(old_option) == f"{OPTION}{slug}-{new_suffix}", old_option
    kompost = OPTION + "bioabfall-entsorgen-wohnen-kompost"
    assert option_map.get(kompost) == OPTION + "bioabfall-entsorgen-kompost", kompost
