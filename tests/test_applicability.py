"""Guard the shape and token consistency of element ``applicability``."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("de", "fr", "it", "en")


def _load_dir(folder: str) -> list[dict[str, Any]]:
    items = []
    for path in sorted((REPO_ROOT / folder).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            data["_name"] = path.name
            items.append(data)
    return items


@lru_cache(maxsize=1)
def _elements() -> tuple[dict[str, Any], ...]:
    return tuple(_load_dir("elements"))


@lru_cache(maxsize=1)
def _values() -> dict[str, dict[str, Any]]:
    return {v["id"]: v for v in _load_dir("values")}


def _tokens(value_id: str, lang: str) -> list[str]:
    return [str(t) for t in (_values()[value_id].get("values") or {}).get(lang) or []]


def _is_localised(value_id: str) -> bool:
    """True when the value list's tokens differ between languages."""
    if value_id not in _values():
        return False
    return len({tuple(_tokens(value_id, lang)) for lang in LANGS}) > 1


def _localised_applicability_attrs(element: dict[str, Any]) -> dict[str, str]:
    """Applicability attributes whose tokens are language-specific, by name."""
    return {
        str(attr["name"]): str(attr["allowed_values"])
        for attr in element.get("attributes") or []
        if attr.get("is_applicability")
        and attr.get("allowed_values")
        and _is_localised(str(attr["allowed_values"]))
    }


def _literals(expr: str, attr: str) -> set[str]:
    """Literal values compared against ``attr`` in a filter expression."""
    pattern = re.compile(rf'\b{re.escape(attr)}=(?:"(?P<q>[^"]*)"|(?P<b>[^\s()]+))')
    return {m.group("q") or m.group("b") for m in pattern.finditer(expr)}


def _ids() -> list[str]:
    return [e["_name"] for e in _elements()]


@pytest.mark.parametrize("element", _elements(), ids=_ids())
def test_localised_applicability_uses_all_four_languages(element: dict[str, Any]) -> None:
    appl = element.get("applicability")
    if not isinstance(appl, dict):
        return
    assert set(appl) == set(LANGS), f"expected exactly {LANGS}, got {sorted(appl)}"
    for lang in LANGS:
        assert str(appl[lang]).strip(), f"{lang} applicability is empty"


@pytest.mark.parametrize("element", _elements(), ids=_ids())
def test_each_language_uses_only_its_own_tokens(element: dict[str, Any]) -> None:
    appl = element.get("applicability")
    if not isinstance(appl, dict):
        return
    for attr, value_id in _localised_applicability_attrs(element).items():
        for lang in LANGS:
            found = _literals(str(appl[lang]), attr)
            allowed = set(_tokens(value_id, lang))
            assert found <= allowed, (
                f"{lang}: {attr} uses {sorted(found - allowed)}, "
                f"expected one of {sorted(allowed)}"
            )


@pytest.mark.parametrize("element", _elements(), ids=_ids())
def test_language_dependent_expression_is_not_a_plain_string(
    element: dict[str, Any],
) -> None:
    """A localised literal in the expression forces the four-language block."""
    appl = element.get("applicability")
    if appl is None or isinstance(appl, dict):
        return
    carried = {
        attr
        for attr in _localised_applicability_attrs(element)
        if _literals(str(appl), attr)
    }
    assert not carried, (
        f"applicability filters on language-specific {sorted(carried)} but is a "
        "plain string; use a de/fr/it/en block"
    )
