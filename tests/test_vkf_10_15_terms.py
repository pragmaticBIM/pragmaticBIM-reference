"""VKF 10-15 Begriffe und Definitionen: small value lists aligned with the directive (#138)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")
LISTS = {
    "fire-building-geometry": 5,
    "fire-safe-place": 2,
    "fire-route-type": 4,
    "fire-storage-type": 5,
    "fire-storage-separation": 3,
}


def _load(slug: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "values" / f"{slug}.yaml").read_text(encoding="utf-8"))


def test_value_lists_are_complete_and_parallel() -> None:
    for slug, size in LISTS.items():
        data = _load(slug)
        assert data["id"] == f"pragmaticbim:value/{slug}", slug
        assert data["code"] == slug.upper(), slug
        assert data["status"] == "active", slug
        assert data["norm_reference"] == "VKF", slug
        for lang in LANGS:
            assert str(data["name"].get(lang) or "").strip(), (slug, "name", lang)
            assert str(data["description"].get(lang) or "").strip(), (slug, "description", lang)
            assert len(data["values"][lang]) == size, (slug, lang)
            assert len(set(data["values"][lang])) == size, (slug, lang)
            assert all(str(value).strip() for value in data["values"][lang]), (slug, lang)


def test_descriptions_cite_the_directive_in_every_language() -> None:
    cite = {"de": "VKF 10-15", "fr": "AEAI 10-15", "it": "AICAA 10-15", "en": "VKF 10-15"}
    for slug in LISTS:
        data = _load(slug)
        for lang in LANGS:
            assert cite[lang] in data["description"][lang], (slug, lang)


def test_building_geometry_states_the_height_limits() -> None:
    data = _load("fire-building-geometry")
    for lang in LANGS:
        text = data["description"][lang]
        for token in ("11 m", "30 m", "600 m", "150 m"):
            assert token in text, (lang, token)


def test_storage_height_limit_for_high_bay_racking() -> None:
    data = _load("fire-storage-type")
    for lang in LANGS:
        assert "7.50 m" in data["description"][lang] or "7,50 m" in data["description"][lang], lang


def test_existing_fire_value_lists_keep_their_ids() -> None:
    for slug in ("reaction-to-fire", "fire-rating", "fire-rating-ei", "fire-rating-r-rei"):
        assert _load(slug)["id"] == f"pragmaticbim:value/{slug}"
