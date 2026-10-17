#!/usr/bin/env python3
"""Apply reviewed English rewrites to the catalogue YAML files.

The rewrite map is a YAML list of ``old``/``new`` pairs::

    - old: |-
        Element status for coordination on existing buildings.
      new: |-
        Component status for coordination in existing buildings.

Matching is on the complete ``en`` scalar, so a string that 68 elements share
is reviewed and rewritten once. German, French, and Italian are never touched:
the script edits the lines of an ``en`` value and nothing else, which keeps the
rest of the file byte-identical and leaves flow-style lists such as
``needed_in_phases: ['32', '33']`` alone.

After writing, ``yaml.safe_load`` of the old and the new file must differ only
at ``en`` leaves; anything else aborts the run.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Iterator

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIRS = (
    "elements",
    "workflows",
    "values",
    "documents",
    "models",
    "project_goals",
    "phases",
    "domains",
)

EN_KEY_RE = re.compile(r"^(\s*)(-\s+)?en:(\s*)(.*)$")
BLOCK_SCALAR_RE = re.compile(r"^([|>])([+-]?)(\d*)$")


class VerificationError(RuntimeError):
    """The rewrite changed something other than an ``en`` leaf."""


def load_map(path: Path) -> dict[str, str]:
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    mapping: dict[str, str] = {}
    for entry in entries:
        old, new = entry["old"], entry["new"]
        if not isinstance(old, str) or not isinstance(new, str):
            raise ValueError(f"old/new must be strings: {entry!r}")
        old, new = old.rstrip("\n"), new.rstrip("\n")
        if old in mapping and mapping[old] != new:
            raise ValueError(f"two different rewrites for the same source:\n{old}")
        mapping[old] = new
    return mapping


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _en_values(lines: list[str]) -> Iterator[tuple[int, int, str, str]]:
    """Yield ``(start, end, kind, value)`` for every ``en`` scalar.

    ``start``/``end`` is the half-open line range that holds the value, and
    ``kind`` is either ``inline`` or the block header (``|-``, ``>``, …).
    """
    index = 0
    while index < len(lines):
        match = EN_KEY_RE.match(lines[index])
        if not match:
            index += 1
            continue
        indent, dash, _, rest = match.groups()
        key_indent = len(indent) + len(dash or "")
        header = rest.strip()
        if header and not BLOCK_SCALAR_RE.match(header):
            yield index, index + 1, "inline", rest
            index += 1
            continue
        if not header:
            # Either an empty value or a nested mapping/sequence; skip both.
            index += 1
            continue
        start = index + 1
        end = start
        while end < len(lines):
            line = lines[end]
            if line.strip() and _indent_of(line) <= key_indent:
                break
            end += 1
        # Trailing blank lines belong to the next key, not to this value.
        while end > start and not lines[end - 1].strip():
            end -= 1
        body = lines[start:end]
        if not body:
            index = end
            continue
        body_indent = min(_indent_of(line) for line in body if line.strip())
        value = "\n".join(
            line[body_indent:] if line.strip() else "" for line in body
        )
        yield start, end, header, value
        index = end


def _parse_inline(rest: str) -> str | None:
    try:
        # The space matters: ``v:"x"`` is a plain scalar, ``v: "x"`` a mapping.
        value = yaml.safe_load("v: " + rest.strip())["v"]
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _emit_inline(value: str) -> str:
    if "\n" in value:
        # safe_dump would break a multi-line string across lines; the source
        # wrote it as one double-quoted scalar with escapes, so keep that shape.
        escaped = (
            value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        )
        return f'"{escaped}"'
    dumped = yaml.safe_dump(
        value, allow_unicode=True, default_flow_style=True, width=10**6
    )
    return dumped.removesuffix("\n").removesuffix("\n...").strip()


def rewrite_file(
    path: Path, mapping: dict[str, str], matched: set[str]
) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    # Collect first, rewrite back to front so earlier spans stay valid.
    spans = list(_en_values(lines))
    hits = 0
    for start, end, kind, value in reversed(spans):
        if kind == "inline":
            parsed = _parse_inline(value)
            if parsed is None or parsed not in mapping:
                continue
            matched.add(parsed)
            new = mapping[parsed]
            if new == parsed:
                continue
            head = lines[start][: lines[start].index("en:") + 3]
            lines[start : start + 1] = [f"{head} {_emit_inline(new)}"]
            hits += 1
            continue

        if value not in mapping:
            continue
        matched.add(value)
        new = mapping[value]
        if new == value:
            continue
        body_indent = min(
            _indent_of(line) for line in lines[start:end] if line.strip()
        )
        pad = " " * body_indent
        lines[start:end] = [pad + line if line else "" for line in new.split("\n")]
        hits += 1
    return "\n".join(lines), hits


def _en_only_diff(old: Any, new: Any, pointer: str = "") -> Iterator[str]:
    """Yield pointers where old and new differ outside an ``en`` leaf."""
    if isinstance(old, dict) and isinstance(new, dict):
        if old.keys() != new.keys():
            yield f"{pointer}: keys changed"
            return
        for key in old:
            if key == "en":
                continue
            yield from _en_only_diff(old[key], new[key], f"{pointer}.{key}")
        return
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            yield f"{pointer}: list length changed"
            return
        for i, (a, b) in enumerate(zip(old, new)):
            yield from _en_only_diff(a, b, f"{pointer}[{i}]")
        return
    if old != new:
        yield f"{pointer}: value changed outside an en leaf"


def verify(path: Path, before: str, after: str) -> None:
    old = yaml.safe_load(before)
    new = yaml.safe_load(after)
    problems = list(_en_only_diff(old, new))
    if problems:
        raise VerificationError(f"{path}:\n  " + "\n  ".join(problems))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path, help="YAML file with old/new pairs")
    parser.add_argument(
        "--dir",
        action="append",
        choices=DATA_DIRS,
        help="restrict to one catalogue directory; repeatable",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report without writing"
    )
    args = parser.parse_args()

    mapping = load_map(args.map)
    dirs = tuple(args.dir) if args.dir else DATA_DIRS

    matched: set[str] = set()
    total = 0
    changed_files = 0
    for name in dirs:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            before = path.read_text(encoding="utf-8")
            after, hits = rewrite_file(path, mapping, matched)
            if not hits or after == before:
                continue
            verify(path, before, after)
            changed_files += 1
            total += hits
            if not args.dry_run:
                path.write_text(after, encoding="utf-8")

    verb = "would rewrite" if args.dry_run else "rewrote"
    print(f"{verb} {total} value(s) in {changed_files} file(s)")

    unmatched = sorted(set(mapping) - matched)
    if unmatched:
        print(f"\n{len(unmatched)} source string(s) matched nothing:", file=sys.stderr)
        for old in unmatched:
            print(f"  {' '.join(old.split())[:100]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
