#!/usr/bin/env python3
"""Audit the English translations in the catalogue YAML files.

Five modes, combinable:

    --gaps          nodes that carry ``de`` but no ``en``
    --worklist      deduplicated de/en pairs, grouped into review batches
    --lint          spelling variants and German calques (see english-style.mdc)
    --consistency   one German string rendered several ways, and glossary drift
    --placeholders  broken, half-translated, or dropped placeholders

Every mode except ``--worklist`` exits non-zero on findings so they can gate CI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
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

# Oxford British English: British word stock, -ize endings.
# (pattern, replacement shown in the report, explanation)
SPELLING_RULES: tuple[tuple[str, str, str], ...] = (
    (r"\bmodel(ing|ed|er|ers)\b", "modell\\1", "double the l"),
    # "user stories" and "success stories" are correct English, not levels.
    (
        r"(?<!user )(?<!success )\bstor(y|ies)\b",
        "storey/storeys",
        "storey for a building level",
    ),
    (r"\bcolors?\b", "colour", "British spelling"),
    (r"\bbehaviors?\b", "behaviour", "British spelling"),
    (r"\bneighbor", "neighbour", "British spelling"),
    (r"\bcenters?\b", "centre", "British spelling"),
    (r"\bfibers?\b", "fibre", "British spelling"),
    (r"\bcatalogs?\b", "catalogue", "British spelling"),
    (r"\bdialogs?\b", "dialogue", "British spelling"),
    (r"\bprograms?\b", "programme", "programme unless it means software"),
    (r"\bfulfill(s|ment)\b", "fulfil/fulfilment", "single l in British English"),
    (r"\bcancel(ed|ing)\b", "cancell\\1", "double the l"),
    (r"\blevel(ed|ing)\b", "levell\\1", "double the l"),
    (r"\bsignaling\b", "signalling", "double the l"),
    (r"\bgray\b", "grey", "British spelling"),
    (r"\baging\b", "ageing", "British spelling"),
    (r"organis(e|es|ed|ing|ation)", "organiz\\1", "-ize ending"),
    (r"optimis(e|es|ed|ing|ation)", "optimiz\\1", "-ize ending"),
    (r"visualis(e|es|ed|ing|ation)", "visualiz\\1", "-ize ending"),
    (r"prioritis(e|es|ed|ing|ation)", "prioritiz\\1", "-ize ending"),
    (r"harmonis(e|es|ed|ing|ation)", "harmoniz\\1", "-ize ending"),
    (r"standardis(e|es|ed|ing|ation)", "standardiz\\1", "-ize ending"),
    (r"normalis(e|es|ed|ing|ation)", "normaliz\\1", "-ize ending"),
    (r"synchronis(e|es|ed|ing|ation)", "synchroniz\\1", "-ize ending"),
    (r"categoris(e|es|ed|ing|ation)", "categoriz\\1", "-ize ending"),
    (r"characteris(e|es|ed|ing|ation)", "characteriz\\1", "-ize ending"),
    (r"authoris(e|es|ed|ing|ation)", "authoriz\\1", "-ize ending"),
    (r"recognis(e|es|ed|ing)", "recogniz\\1", "-ize ending"),
    (r"summaris(e|es|ed|ing)", "summariz\\1", "-ize ending"),
    (r"minimis(e|es|ed|ing)", "minimiz\\1", "-ize ending"),
    (r"maximis(e|es|ed|ing)", "maximiz\\1", "-ize ending"),
    (r"utilis(e|es|ed|ing|ation)", "utiliz\\1", "-ize ending"),
    (r"digitalis(e|es|ed|ing|ation)", "digitaliz\\1", "-ize ending"),
    (r"specialis(e|es|ed|ing|ation)\b", "specializ\\1", "-ize ending"),
)

TERM_RULES: tuple[tuple[str, str], ...] = (
    (r"\bexisting stock\b", "existing building / existing structure"),
    (r"\bbuilding owners?\b", "client"),
    (r"\bemployers?\b", "client"),
    # "principal" is left alone: in this catalogue it is always the adjective
    # ("principal dimensions", "principal storeys"), never a party to a contract.
    (r"\broom programs?\b", "room programme"),
    (r"\bspace programs?\b", "room programme"),
    (r"\butilisation agreement\b", "usage agreement"),
    (r"\bplausibilisation\b", "plausibility check"),
    (r"\bapplication case\b", "use case"),
    (r"\blist of values\b", "value list"),
    (r"\bconstruction element\b", "component"),
    (r"\bbuilding part\b", "component"),
    (r"\bplanners?\b", "designer (German 'Planer' is a false friend)"),
    (r"\bassess (them|it) professionally\b", "have the relevant specialist assess it"),
    (r"\bplan graphics\b", "drawing graphics"),
    (r"\baward (package|lot)s?\b", "procurement package"),
    (r"\btender lots?\b", "procurement package"),
    (r"\belement status\b", "component status"),
    (r"\bprocessing status\b", "status"),
    (r"\bidentifies if\b", "marks whether"),
    (r"\bsee value list\b", "see the … value list"),
)

CALQUE_RULES: tuple[tuple[str, str], ...] = (
    (r"\brespectively\b", "German 'bzw.' — name both options instead"),
    (r"\bin each case\b", "German 'jeweils' — usually redundant"),
    (r"\bthereby\b", "German 'dadurch' — rewrite with a verb"),
    (r"\bhereby\b", "German 'hiermit' — drop it"),
    (r"\bas well as\b", "use 'and'"),
    (r"\boffers? the possibility\b", "say what it does"),
    (r"\bpossibilit(y|ies)\b", "say what is possible instead"),
    (r"\bis to be (\w+ed)\b", "use the imperative"),
    (r"\bat the latest\b", "German 'spätestens' — use 'by'"),
    (r"\bin the run-?up\b", "German 'im Vorfeld' — use 'before'"),
    (r"\bfor this purpose\b", "German 'hierfür' — usually redundant"),
)

# German words that must never appear inside an English block. Technical tokens
# such as CalculatedType examples are excluded via TOKEN_RE below.
GERMAN_WORDS = (
    "und",
    "oder",
    "nicht",
    "werden",
    "wird",
    "muss",
    "müssen",
    "gemäss",
    "Bauteil",
    "Gebäude",
    "Geschoss",
    "Raum",
    "Wand",
    "Decke",
    "Planung",
    "Bauherr",
    "Anwendungsfall",
    "Modellierung",
)

# Rewrites safe enough to apply unattended. Everything that needs judgement —
# terminology, calques, sentence shape — stays out of this list and is reported
# by --lint only. `program` is only touched in "room program", because the word
# is correct when it means software.
FIX_RULES: tuple[tuple[str, str], ...] = (
    (r"\bmodel(ing|ed|er|ers)\b", r"modell\1"),
    (r"\bcolor(s|ed|ing)?\b", r"colour\1"),
    (r"\bbehavior(s|al)?\b", r"behaviour\1"),
    (r"\bneighbor(s|ing|hood|hoods)?\b", r"neighbour\1"),
    (r"\bfiber(s)?\b", r"fibre\1"),
    (r"\bcatalog(s)?\b", r"catalogue\1"),
    (r"\bdialog(s)?\b", r"dialogue\1"),
    (r"\broom program(s)?\b", r"room programme\1"),
    # British English drops the second l only before a vowel-less ending:
    # fulfil / fulfils / fulfilment, but fulfilled / fulfilling keep it.
    (r"\bfulfill(s|ment)?\b", r"fulfil\1"),
    (r"\bcancel(ed|ing)\b", r"cancell\1"),
    (r"\bsignaling\b", "signalling"),
    (r"\bgray\b", "grey"),
    (r"organis(e|es|ed|ing|ation|ations|ational)\b", r"organiz\1"),
    (r"optimis(e|es|ed|ing|ation|ations)\b", r"optimiz\1"),
    (r"visualis(e|es|ed|ing|ation|ations)\b", r"visualiz\1"),
    (r"prioritis(e|es|ed|ing|ation)\b", r"prioritiz\1"),
    (r"harmonis(e|es|ed|ing|ation)\b", r"harmoniz\1"),
    (r"standardis(e|es|ed|ing|ation)\b", r"standardiz\1"),
    (r"normalis(e|es|ed|ing|ation)\b", r"normaliz\1"),
    (r"synchronis(e|es|ed|ing|ation)\b", r"synchroniz\1"),
    (r"categoris(e|es|ed|ing|ation)\b", r"categoriz\1"),
    (r"characteris(e|es|ed|ing|ation)\b", r"characteriz\1"),
    (r"authoris(e|es|ed|ing|ation)\b", r"authoriz\1"),
    (r"recognis(e|es|ed|ing)\b", r"recogniz\1"),
    (r"summaris(e|es|ed|ing)\b", r"summariz\1"),
    (r"minimis(e|es|ed|ing)\b", r"minimiz\1"),
    (r"maximis(e|es|ed|ing)\b", r"maximiz\1"),
    (r"utilis(e|es|ed|ing|ation)\b", r"utiliz\1"),
    (r"digitalis(e|es|ed|ing|ation)\b", r"digitaliz\1"),
    # False friend: German "Planer" is the designer. An English planner does
    # programming or town planning.
    (r"\bplanner(s)?\b", r"designer\1"),
    # "prüfbar" had two renderings in roughly equal numbers; settle on one.
    (r"\bcheckable\b", "verifiable"),
    (r"\bquantity takeoff\b", "quantity take-off"),
)

# Placeholders that ended up truncated, half-translated, or reshaped in an en
# block. The Swiss status letters are codes that reach real filenames, so they
# stay German rather than being translated to E/N.
PLACEHOLDER_FIXES: tuple[tuple[str, str, str], ...] = (
    ("{Free}", "{FreeText}", "truncated placeholder"),
    ("{Mietername}", "{TenantName}", "German token in an en block"),
    ("{E|D|N|T}", "{B|A|N|T}", "status letters are codes, not words"),
    ("{E|N}", "{B|N}", "status letters are codes, not words"),
    ("{Plant type}", "{PlantType}", "placeholders are CamelCase without spaces"),
    ("{storey}", "{Storey}", "placeholders start with a capital"),
)

# Placeholders that are deliberately identical in every language.
PLACEHOLDER_SHARED = frozenset(
    {"{ext}", "{nnn}", "{Phase}", "{Project}", "{B|A|N|T}", "{B|N}", "{YYYYMMDD}"}
)
PLACEHOLDER_RE = re.compile(r"\{[^{}]{1,40}\}")

# German term to the English stem it must map to. Matching on stems keeps
# idiomatic wordings such as "cost plausibility" out of the report.
GLOSSARY: tuple[tuple[str, str], ...] = (
    (r"Vergabepaket", r"procurement[ -]package"),
    (r"Raumprogramm", r"room[ -]programme"),
    (r"Nutzungsvereinbarung", r"usage[ -]agreement"),
    (r"Anwendungsfall|Anwendungsfälle", r"use[ -]case"),
    (r"Werteliste", r"value[ -]list"),
    (r"Plausibilisierung", r"plausibilit"),
    # Building fabric is deconstructed; temporary site equipment is dismantled.
    # Demolish is the catalogue's own abstract phase code for the Rückbau phase.
    (r"Rückbau", r"deconstruct|dismantl|Demolish"),
)

# Backticked tokens, IFC identifiers and links are excluded from every check.
TOKEN_RE = re.compile(
    r"`[^`]*`"
    r"|\bIfc\w+"
    r"|\bPset_\w+|\bQto_\w+|\bePset_\w+"
    r"|\bpragmaticbim:[\w/.-]+"
    r"|https?://\S+"
    r"|\*\*[^*]+\*\*"
)


@dataclass(frozen=True)
class Block:
    """One translatable node in a catalogue file."""

    path: Path
    pointer: str
    de: Any
    en: Any
    has_en: bool

    @property
    def de_text(self) -> str:
        return self.de if isinstance(self.de, str) else ""

    @property
    def en_text(self) -> str:
        return self.en if isinstance(self.en, str) else ""


def _preview(value: Any, width: int = 90) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = yaml.safe_dump(value, allow_unicode=True, default_flow_style=True)
    flat = " ".join(str(text).split())
    return flat[:width] + ("…" if len(flat) > width else "")


def _iter_blocks(node: Any, pointer: str, path: Path) -> Iterator[Block]:
    if isinstance(node, dict):
        if "de" in node:
            yield Block(
                path,
                pointer or ".",
                node.get("de"),
                node.get("en"),
                "en" in node,
            )
        for key, value in node.items():
            yield from _iter_blocks(value, f"{pointer}.{key}", path)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_blocks(value, f"{pointer}[{index}]", path)


def collect(dirs: tuple[str, ...]) -> list[Block]:
    blocks: list[Block] = []
    for name in dirs:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            blocks.extend(_iter_blocks(data, "", path.relative_to(REPO_ROOT)))
    return blocks


def _mask(text: str) -> str:
    """Blank out tokens that must not be linted."""
    return TOKEN_RE.sub(lambda m: " " * len(m.group(0)), text)


def _context(text: str, start: int, end: int, width: int = 55) -> str:
    snippet = text[max(0, start - width) : end + width]
    return " ".join(snippet.split())


def _match_case(original: str, replacement: str) -> str:
    """Carry the original capitalization over to the rewritten word."""
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _fix_segment(text: str) -> str:
    for pattern, template in FIX_RULES:
        def substitute(match: re.Match[str]) -> str:
            return _match_case(match.group(0), match.expand(template))

        text = re.sub(pattern, substitute, text, flags=re.IGNORECASE)
    return text


def _fix_text(text: str) -> str:
    """Rewrite everything except backticked tokens, identifiers, and links."""
    out: list[str] = []
    cursor = 0
    for token in TOKEN_RE.finditer(text):
        out.append(_fix_segment(text[cursor : token.start()]))
        out.append(token.group(0))
        cursor = token.end()
    out.append(_fix_segment(text[cursor:]))
    return "".join(out)


BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\d*$")


def _en_line_spans(lines: list[str]) -> Iterator[tuple[int, int]]:
    """Yield (line index, first column) for every line inside an ``en`` value.

    French shares words such as ``organisation`` and ``optimisation`` with the
    wrong English spelling, so rewrites must never leave the ``en`` blocks.
    """
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)en:(\s*)(.*)$", lines[index])
        if not match:
            index += 1
            continue
        indent, gap, rest = match.group(1), match.group(2), match.group(3)
        if rest and not BLOCK_SCALAR_RE.match(rest.strip()):
            yield index, len(indent) + 3 + len(gap)
            index += 1
            continue
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip()) <= len(indent):
                break
            if line.strip():
                yield index, 0
            index += 1


def apply_fixes(dirs: tuple[str, ...], dry_run: bool) -> int:
    changed_files = 0
    changed_lines = 0
    for name in dirs:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            lines = path.read_text(encoding="utf-8").split("\n")
            touched = False
            for index, column in _en_line_spans(lines):
                head, tail = lines[index][:column], lines[index][column:]
                fixed = _fix_text(tail)
                if fixed == tail:
                    continue
                lines[index] = head + fixed
                touched = True
                changed_lines += 1
                rel = path.relative_to(REPO_ROOT)
                print(f"  {rel}:{index + 1}")
                print(f"    - {tail.strip()[:110]}")
                print(f"    + {fixed.strip()[:110]}")
            if touched:
                changed_files += 1
                if not dry_run:
                    path.write_text("\n".join(lines), encoding="utf-8")
    verb = "would change" if dry_run else "changed"
    print(f"\nfix: {verb} {changed_lines} line(s) in {changed_files} file(s)")
    return 0


def report_gaps(blocks: list[Block]) -> int:
    gaps = [b for b in blocks if not b.has_en]
    if not gaps:
        print("gaps: none — every de block has an en counterpart")
        return 0
    print(f"gaps: {len(gaps)} node(s) with de but no en\n")
    for block in gaps:
        print(f"  {block.path}{block.pointer}")
        print(f"      de: {_preview(block.de)}")
    return 1


def report_worklist(blocks: list[Block], batch_size: int, as_json: bool) -> int:
    by_dir: dict[str, dict[str, list[str]]] = defaultdict(dict)
    occurrences: dict[str, int] = defaultdict(int)
    de_for: dict[str, str] = {}
    for block in blocks:
        en = block.en_text
        if not en or not block.de_text:
            continue
        top = block.path.parts[0]
        by_dir[top].setdefault(en, []).append(f"{block.path}{block.pointer}")
        occurrences[en] += 1
        de_for.setdefault(en, block.de_text)

    if as_json:
        payload = {
            top: [
                {
                    "en": en,
                    "de": de_for[en],
                    "occurrences": len(where),
                    "where": where,
                }
                for en, where in sorted(entries.items(), key=lambda kv: -len(kv[1]))
            ]
            for top, entries in sorted(by_dir.items())
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for top, entries in sorted(by_dir.items()):
        unique = len(entries)
        total = sum(len(v) for v in entries.values())
        chars = sum(len(k) for k in entries)
        batches = (unique + batch_size - 1) // batch_size
        print(
            f"{top:15} unique={unique:5} occurrences={total:5} "
            f"chars={chars:7} batches={batches}"
        )
    print()
    shared = sorted(
        ((n, en) for en, n in occurrences.items() if n > 1), reverse=True
    )[:15]
    if shared:
        print("most reused strings (fix once, applies everywhere):")
        for count, en in shared:
            print(f"  {count:4}x  {' '.join(en.split())[:88]}")
    return 0


def report_lint(blocks: list[Block], limit: int) -> int:
    findings: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    checks: list[tuple[str, str, str]] = []
    for pattern, correct, why in SPELLING_RULES:
        checks.append((pattern, f"spelling → {correct} ({why})", "spelling"))
    for pattern, correct in TERM_RULES:
        checks.append((pattern, f"term → {correct}", "terminology"))
    for pattern, hint in CALQUE_RULES:
        checks.append((pattern, f"calque: {hint}", "calque"))
    for word in GERMAN_WORDS:
        checks.append((rf"\b{word}\b", f"German word '{word}' in an en block", "german"))

    for block in blocks:
        en = block.en_text
        if not en:
            continue
        masked = _mask(en)
        for pattern, message, kind in checks:
            flags = 0 if kind == "german" else re.IGNORECASE
            for match in re.finditer(pattern, masked, flags):
                # One report per location and wording; a string reused by 60
                # elements is still one fix, but every distinct site is listed.
                key = (
                    str(block.path),
                    block.pointer,
                    message,
                    match.group(0).lower(),
                )
                if key in seen:
                    continue
                seen.add(key)
                findings[kind].append(
                    f"  {block.path}{block.pointer}\n"
                    f"      {message}\n"
                    f"      …{_context(en, match.start(), match.end())}…"
                )

    total = sum(len(v) for v in findings.values())
    if not total:
        print("lint: clean")
        return 0
    for kind in ("german", "terminology", "spelling", "calque"):
        entries = findings.get(kind)
        if not entries:
            continue
        print(f"\n== {kind}: {len(entries)} distinct finding(s) ==")
        for entry in entries[:limit]:
            print(entry)
        if len(entries) > limit:
            print(f"  … {len(entries) - limit} more (raise --limit to see them)")
    print(f"\nlint: {total} distinct finding(s)")
    return 1


def report_placeholders(blocks: list[Block], limit: int) -> int:
    """Placeholders that are broken, half-translated, or dropped in the en block."""
    findings: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for block in blocks:
        en = block.en_text
        if not en:
            continue
        for broken, correct, why in PLACEHOLDER_FIXES:
            if broken not in en:
                continue
            key = (str(block.path), block.pointer, broken)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                f"  {block.path}{block.pointer}\n"
                f"      {broken} → {correct} ({why})"
            )

        de_tokens = set(PLACEHOLDER_RE.findall(block.de_text)) & PLACEHOLDER_SHARED
        missing = sorted(token for token in de_tokens if token not in en)
        if missing:
            key = (str(block.path), block.pointer, ",".join(missing))
            if key not in seen:
                seen.add(key)
                findings.append(
                    f"  {block.path}{block.pointer}\n"
                    f"      shared placeholder(s) dropped from en: {', '.join(missing)}"
                )

    if not findings:
        print("placeholders: clean")
        return 0
    print(f"\n== placeholders: {len(findings)} finding(s) ==")
    for entry in findings[:limit]:
        print(entry)
    if len(findings) > limit:
        print(f"  … {len(findings) - limit} more (raise --limit to see them)")
    return 1


def report_consistency(blocks: list[Block], limit: int) -> int:
    """One German string rendered several ways, and glossary terms not honoured."""
    renderings: dict[str, set[str]] = defaultdict(set)
    sites: dict[str, list[str]] = defaultdict(list)
    glossary: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for block in blocks:
        de, en = block.de_text.strip(), block.en_text.strip()
        if not de or not en:
            continue
        renderings[de].add(en)
        sites[de].append(f"{block.path}{block.pointer}")
        for german, english in GLOSSARY:
            if not re.search(german, de, re.IGNORECASE):
                continue
            if re.search(english, en, re.IGNORECASE):
                continue
            key = (str(block.path), block.pointer, german)
            if key in seen:
                continue
            seen.add(key)
            glossary.append(
                f"  {block.path}{block.pointer}\n"
                f"      de has '{german}' but en does not use '{english}'\n"
                f"      …{' '.join(en.split())[:88]}…"
            )

    split = {de: ens for de, ens in renderings.items() if len(ens) > 1}
    total = len(split) + len(glossary)
    if not total:
        print("consistency: clean")
        return 0

    if split:
        print(f"\n== consistency: {len(split)} German string(s) rendered several ways ==")
        for de, ens in list(split.items())[:limit]:
            print(f"  de: {' '.join(de.split())[:88]}")
            for en in sorted(ens):
                print(f"      en: {' '.join(en.split())[:88]}")
            print(f"      at: {sites[de][0]} (+{len(sites[de]) - 1} more)")
    if glossary:
        print(f"\n== consistency: {len(glossary)} glossary finding(s) ==")
        for entry in glossary[:limit]:
            print(entry)
        if len(glossary) > limit:
            print(f"  … {len(glossary) - limit} more (raise --limit to see them)")
    print(f"\nconsistency: {total} finding(s)")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gaps", action="store_true", help="de blocks without en")
    parser.add_argument(
        "--worklist", action="store_true", help="deduplicated review batches"
    )
    parser.add_argument(
        "--lint", action="store_true", help="spelling, terminology, and calques"
    )
    parser.add_argument(
        "--consistency",
        action="store_true",
        help="one German string rendered several ways, and glossary drift",
    )
    parser.add_argument(
        "--placeholders",
        action="store_true",
        help="broken, half-translated, or dropped placeholders",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="apply the unambiguous spelling rewrites to en blocks",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="with --fix: preview without writing"
    )
    parser.add_argument(
        "--dir",
        action="append",
        choices=DATA_DIRS,
        help="restrict to one catalogue directory; repeatable",
    )
    parser.add_argument("--batch-size", type=int, default=60)
    parser.add_argument("--limit", type=int, default=40, help="findings per category")
    parser.add_argument("--json", action="store_true", help="worklist as JSON")
    args = parser.parse_args()

    if not (
        args.gaps
        or args.worklist
        or args.lint
        or args.fix
        or args.consistency
        or args.placeholders
    ):
        args.gaps = args.lint = args.consistency = args.placeholders = True

    dirs = tuple(args.dir) if args.dir else DATA_DIRS

    if args.fix:
        apply_fixes(dirs, args.dry_run)

    blocks = collect(dirs)

    status = 0
    if args.gaps:
        status |= report_gaps(blocks)
    if args.worklist:
        report_worklist(blocks, args.batch_size, args.json)
    if args.lint:
        status |= report_lint(blocks, args.limit)
    if args.consistency:
        status |= report_consistency(blocks, args.limit)
    if args.placeholders:
        status |= report_placeholders(blocks, args.limit)
    return status


if __name__ == "__main__":
    sys.exit(main())
