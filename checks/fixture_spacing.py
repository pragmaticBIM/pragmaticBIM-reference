"""Minimum distances between fixtures from ``rules/fixture_spacing.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "rules" / "fixture_spacing.yaml"


@dataclass(frozen=True)
class SpacingRule:
    between: tuple[str, str]
    min: float
    measure: str
    source: dict[str, Any]

    def matches(self, function_a: str, function_b: str) -> bool:
        a, b = self.between
        return {a, b} == {function_a, function_b} or (
            a == b == function_a == function_b
        )


@lru_cache(maxsize=1)
def load_matrix() -> list[SpacingRule]:
    data = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
    rules: list[SpacingRule] = []
    for pair in data.get("pairs") or []:
        left, right = pair["between"]
        rules.append(
            SpacingRule(
                between=(left, right),
                min=float(pair["distance"]["min"]),
                measure=pair["measure"],
                source=dict(pair["source"]),
            )
        )
    return rules


def min_distance(function_a: str, function_b: str) -> SpacingRule | None:
    """Return the spacing rule for two equipment functions, if any."""
    for rule in load_matrix():
        if rule.matches(function_a, function_b):
            return rule
    return None


def rules_for_room_functions(functions: set[str]) -> list[SpacingRule]:
    """Spacing rules that apply because the room contains the needed functions."""
    out: list[SpacingRule] = []
    for rule in load_matrix():
        a, b = rule.between
        if a == b:
            if a in functions:
                out.append(rule)
        elif a in functions and b in functions:
            out.append(rule)
    return out
