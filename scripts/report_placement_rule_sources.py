#!/usr/bin/env python3
"""List placement rules by source.kind per room type."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROOM_TYPES = ROOT / "room_types"


def _rules(doc: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for config in doc.get("configurations") or []:
        for key in ("equipment", "openings"):
            for entry in config.get(key) or []:
                for rule in entry.get("placement_rules") or []:
                    out.append((entry["id"], rule))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--defaults-only",
        action="store_true",
        help="Print only rules with source.kind default",
    )
    args = parser.parse_args()

    totals: Counter[str] = Counter()
    for path in sorted(ROOM_TYPES.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        by_kind: Counter[str] = Counter()
        defaults: list[str] = []
        for _entry_id, rule in _rules(doc):
            kind = (rule.get("source") or {}).get("kind") or "missing"
            by_kind[kind] += 1
            totals[kind] += 1
            if kind == "default":
                defaults.append(rule["id"])
        if not by_kind:
            continue
        if args.defaults_only:
            if defaults:
                print(f"{path.stem}:")
                for rule_id in defaults:
                    print(f"  {rule_id}")
            continue
        summary = ", ".join(f"{k}={by_kind[k]}" for k in sorted(by_kind))
        print(f"{path.stem}: {summary}")

    if not args.defaults_only:
        print("---")
        print("total: " + ", ".join(f"{k}={totals[k]}" for k in sorted(totals)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
