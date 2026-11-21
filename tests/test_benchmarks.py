"""Benchmark ranges per use (benchmarks/) against uses/ and the data contract notations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
USES_DIR = REPO_ROOT / "uses"
# Pinned notations of the data contract (no network). Documented in the fixture itself.
NOTATIONS_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "building_metric_notations.yaml"
# Optional sibling checkout; when present the pinned notations are cross-checked against it.
CONTRACT_DIR = REPO_ROOT.parents[1] / "pragmatic-bim-data-contract"

LANGS = ("de", "fr", "it", "en")
BENCHMARK_KEYS = {"id", "use", "name", "ranges", "status"}
RANGE_KEYS = {"metric", "min", "max", "target", "source", "comment"}
REQUIRED_USES = {"wohnen", "arbeit", "bildung"}


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def _benchmarks() -> dict[str, dict[str, Any]]:
    return {path.stem: _load(path) for path in sorted(BENCHMARKS_DIR.glob("*.yaml"))}


def _pinned_notations() -> set[str]:
    fixture = _load(NOTATIONS_FIXTURE)
    return {n for scheme in fixture["schemes"] for n in scheme["notations"]}


BENCHMARKS = _benchmarks()
USES = {_load(path)["id"] for path in USES_DIR.glob("*.yaml")}
NOTATIONS = _pinned_notations()


def test_new_contract_notations_are_pinned():
    """The notations added by data-contract#11 must be in the pinned list."""
    assert {
        "ratio_main_usable_area_to_gross_floor_area",
        "ratio_circulation_area_to_gross_floor_area",
        "ratio_envelope_area_to_gross_volume",
        "ratio_envelope_area_to_energy_reference_area",
        "total_main_usable_area",
        "total_circulation_area",
    } <= NOTATIONS


def test_pinned_notations_exist_in_sibling_contract():
    ttl_dir = CONTRACT_DIR / "classification"
    if not ttl_dir.is_dir():
        pytest.skip("no sibling data-contract checkout; using the pinned notation list only")
    fixture = _load(NOTATIONS_FIXTURE)
    for scheme in fixture["schemes"]:
        text = (ttl_dir / scheme["path"]).read_text(encoding="utf-8")
        for notation in scheme["notations"]:
            assert f'skos:notation "{notation}"' in text, f"{notation}: not in {scheme['path']}"


def test_one_file_per_required_use():
    assert {b["use"].rsplit("/", 1)[-1] for b in BENCHMARKS.values()} >= REQUIRED_USES
    assert {"wohnen", "buero", "schule"} <= set(BENCHMARKS)


@pytest.mark.parametrize("slug", sorted(BENCHMARKS))
def test_benchmark_shape(slug):
    benchmark = BENCHMARKS[slug]
    assert set(benchmark) <= BENCHMARK_KEYS, f"{slug}: unexpected keys {set(benchmark) - BENCHMARK_KEYS}"
    assert benchmark["id"] == f"pragmaticbim:benchmark/{slug}"
    assert benchmark["use"] in USES, f"{slug}: unknown use {benchmark['use']}"
    assert set(benchmark["name"]) == set(LANGS)
    assert all(isinstance(v, str) and v.strip() for v in benchmark["name"].values())
    assert benchmark["ranges"], f"{slug}: no ranges"
    metrics = [r["metric"] for r in benchmark["ranges"]]
    assert len(metrics) == len(set(metrics)), f"{slug}: duplicate metric"


@pytest.mark.parametrize("slug", sorted(BENCHMARKS))
def test_metric_resolves_to_contract_notation(slug):
    for rng in BENCHMARKS[slug]["ranges"]:
        assert rng["metric"] in NOTATIONS, f"{slug}: {rng['metric']} is not a data contract notation"


@pytest.mark.parametrize("slug", sorted(BENCHMARKS))
def test_range_values(slug):
    for rng in BENCHMARKS[slug]["ranges"]:
        where = f"{slug}/{rng['metric']}"
        assert set(rng) <= RANGE_KEYS, f"{where}: unexpected keys {set(rng) - RANGE_KEYS}"
        bounds = [rng[k] for k in ("min", "max", "target") if k in rng]
        assert bounds, f"{where}: needs at least one of min, max, target"
        assert all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in bounds), where
        if "min" in rng and "max" in rng:
            assert rng["min"] <= rng["max"], f"{where}: min > max"
        if "target" in rng:
            assert rng.get("min", rng["target"]) <= rng["target"] <= rng.get("max", rng["target"]), (
                f"{where}: target outside min..max"
            )


@pytest.mark.parametrize("slug", sorted(BENCHMARKS))
def test_range_has_source_or_assumption_comment(slug):
    for rng in BENCHMARKS[slug]["ranges"]:
        where = f"{slug}/{rng['metric']}"
        assert rng.get("source") or rng.get("comment"), f"{where}: needs a source or a comment marking an assumption"
        for field in ("source", "comment"):
            text = rng.get(field)
            if isinstance(text, dict):
                assert set(text) == set(LANGS), f"{where}: {field} must be filled in {LANGS}"
                assert all(isinstance(v, str) and v.strip() for v in text.values()), where
            elif text is not None:
                assert isinstance(text, str) and text.strip(), where
