"""VKF 13-15 Baustoffe und Bauteile: classification value lists (RF, EI, E, REI and related) (#139)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
DURATIONS = ["30", "60", "90", "120", "180", "240"]
LISTS = {
    "fire-material-class-en": ["A1", "A2", "B", "C", "D", "E", "F"],
    "fire-smoke-class": ["s1", "s2", "s3"],
    "fire-droplet-class": ["d0", "d1", "d2"],
    "fire-rating-r": [f"R {d}" for d in DURATIONS],
    "fire-rating-rei": [f"REI {d}" for d in DURATIONS],
    "fire-rating-e": [f"E {d}" for d in DURATIONS],
    "fire-rating-ei-extended": [f"EI {d}" for d in DURATIONS],
    "fire-cladding-k": ["K 30", "K 60"],
    "fire-rating-vkf-f": [f"F {d}" for d in DURATIONS] + ["F 30 bb", "F 60 bb"],
    "fire-criteria-additional": ["W", "M", "C", "S"],
}


def _load(slug: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "values" / f"{slug}.yaml").read_text(encoding="utf-8"))


def test_value_lists_are_complete_and_parallel() -> None:
    for slug, expected in LISTS.items():
        data = _load(slug)
        assert data["id"] == f"pragmaticbim:value/{slug}", slug
        assert data["code"] == slug.upper(), slug
        assert data["status"] == "active", slug
        assert data["norm_reference"] == "VKF", slug
        for lang in LANGS:
            assert str(data["name"].get(lang) or "").strip(), (slug, "name", lang)
            assert str(data["description"].get(lang) or "").strip(), (slug, "description", lang)
            assert data["values"][lang] == expected, (slug, lang)


def test_descriptions_cite_the_directive_in_every_language() -> None:
    cite = {"de": "VKF 13-15", "fr": "AEAI 13-15", "it": "AICAA 13-15", "en": "VKF 13-15"}
    for slug in LISTS:
        data = _load(slug)
        for lang in LANGS:
            assert cite[lang] in data["description"][lang], (slug, lang)


def test_euroclass_description_maps_to_the_rf_groups() -> None:
    data = _load("fire-material-class-en")
    for lang in LANGS:
        text = data["description"][lang]
        for token in ("RF1", "RF2", "RF3", "RF4", "cr", "reaction-to-fire"):
            assert token in text, (lang, token)


def test_existing_fire_value_lists_are_unchanged() -> None:
    assert _load("reaction-to-fire")["values"]["de"] == ["RF1", "RF2", "RF3", "RF4"]
    assert _load("fire-rating-ei")["values"]["de"] == ["EI 30", "EI 60", "EI 90"]
    assert _load("fire-rating-r-rei")["values"]["de"] == ["R 30", "R 60", "R 90", "REI 30", "REI 60", "REI 90"]
    assert "E 30" in _load("fire-rating")["values"]["de"]


def test_extended_lists_name_the_list_they_extend() -> None:
    for slug, target in (
        ("fire-rating-r", "fire-rating-r-rei"),
        ("fire-rating-rei", "fire-rating-r-rei"),
        ("fire-rating-ei-extended", "fire-rating-ei"),
    ):
        data = _load(slug)
        for lang in LANGS:
            assert target in data["description"][lang], (slug, lang)
