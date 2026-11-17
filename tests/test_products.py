"""Product data sheets (products/) against the pinned data contract name index."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sync_products as sp  # noqa: E402

ALLOWED_KEYS = {
    "id",
    "sort_order",
    "status",
    "name",
    "product_classification",
    "tender_text",
    "application_notes",
    "picture_link",
    "attachment_link",
    "comment",
}
LANGS = ("de", "fr", "it", "en")

NAMES = sp.load_names()
SHEETS = sp.load_sheets()
CONCEPTS = {
    concept["code"]: (scheme, concept) for scheme in NAMES["schemes"] for concept in scheme["concepts"]
}


def test_name_index_matches_pin():
    pin = sp.load_pin()
    assert NAMES["contract"]["commit"] == pin["commit"]
    assert [scheme["path"] for scheme in NAMES["schemes"]] == [entry["path"] for entry in pin["schemes"]]


@pytest.mark.parametrize("code", sorted(SHEETS))
def test_sheet_matches_contract(code):
    sheet = SHEETS[code]
    assert set(sheet) <= ALLOWED_KEYS, f"{code}: unexpected keys {set(sheet) - ALLOWED_KEYS}"
    assert sheet["id"] == sp.sheet_id(code)
    assert sp.sheet_path(code).exists(), f"{code}: file must be named {sp.sheet_path(code).name}"
    assert code in CONCEPTS, f"{code}: not a product class in the pinned contract"
    scheme, concept = CONCEPTS[code]
    assert concept["top"], f"{code}: LCA layer concepts get no data sheet"
    assert scheme["sheets"], f"{code}: scheme {scheme['scheme']} is marked as having no sheets"
    assert sheet["product_classification"]["classification_scheme"] == scheme["scheme"]
    for lang in ("de", "en"):
        assert sheet["name"].get(lang) == concept["label"][lang], f"{code}: name.{lang} must match the contract label"
    assert set(sheet["name"]) <= set(LANGS)
    for field in ("tender_text", "application_notes"):
        text = sheet.get(field)
        if text is None:
            continue
        assert set(text) <= set(LANGS)
        assert all(isinstance(value, str) and value.strip() for value in text.values())
    assert sheet["tender_text"].get("de"), f"{code}: tender_text.de is required"


def test_every_top_concept_has_a_sheet():
    missing = [
        concept["code"]
        for scheme in NAMES["schemes"]
        if scheme["sheets"]
        for concept in scheme["concepts"]
        if concept["top"] and concept["code"] not in SHEETS
    ]
    assert not missing, f"product classes without a data sheet: {missing}"


def test_sort_order_unique_per_scheme():
    seen: dict[tuple[str, int], str] = {}
    for code, sheet in SHEETS.items():
        key = (sheet["product_classification"]["classification_scheme"], sheet["sort_order"])
        assert key not in seen, f"{code} and {seen.get(key)} share sort_order {key[1]}"
        seen[key] = code


def test_value_lists_are_generated():
    for path, content in sp.expected_value_sets(NAMES, SHEETS).items():
        assert path.read_text(encoding="utf-8") == content, (
            f"{path.name} is stale: run python scripts/sync_products.py --values-only"
        )
