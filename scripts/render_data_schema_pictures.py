#!/usr/bin/env python3
"""Pictures for arma-elementplan-data elements in the Reference isometric style.

Sources are keyed by data-schema element id:

- ``dataschema.cards.CARDS``: scenes rendered here (no Reference element exists).
- ``REUSE``: Reference scenes (``runner.SAMPLE_CATALOG``) under the data-schema id.

Every picture is rendered in the armasuisse style: red accent, no
pragmaticBIM engraving or watermark.

arma ids equal to a data-schema id use that source; other arma ids are
mapped in ``dataschema.arma.ARMA_SOURCES`` (to a data-schema id or straight
to a Reference slug). Elements without a source are left untouched.

Default output is a draft folder. ``--publish`` writes into the arma media
folder as ``{arma-id}.png`` / ``{arma-id}-print.tif``, sets ``picture_link``
/ ``picture_print_link`` on the element YAML and deletes replaced pictures
no element references any more. ``--prune`` also deletes every other
unreferenced picture in the arma media folder.

    python scripts/render_data_schema_pictures.py --only brenner
    python scripts/render_data_schema_pictures.py --publish --prune
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataschema.arma import ARMA_SOURCES  # noqa: E402
from dataschema.cards import CARDS  # noqa: E402
from dataschema.render import render_card  # noqa: E402
from runner import SAMPLE_CATALOG, run_catalog  # noqa: E402

ARMA = ROOT.parent / "arma-elementplan-data"
ARMA_ELEMENTS = ARMA / "elements"
ARMA_IMAGES = ARMA / "media" / "images"
REFERENCE_IMAGES = ROOT / "media" / "images"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
# Material colour; lit top faces render as the armasuisse red #D43131.
ARMA_ACCENT = (0.53, 0.02, 0.02)

# data-schema id → Reference picture slug.
REUSE: dict[str, str] = {
    "abwasseranschluss": "mep-waste-terminal",
    "abwasserhebepumpe": "mep-pump",
    "aktor": "mep-actuator",
    "alarmgerat": "mep-alarm",
    "aussenraum": "spaces-exterior",
    "baurechtliche-parzelle": "architecture-building-law-parcel",
    "beleuchtung": "mep-light-fixture",
    "bodenaufbauten": "architecture-floor-covering",
    "brandschutzklappe": "mep-damper",
    "decken-flachdacher": "architecture-slab-floor",
    "elektrischer-speicher": "mep-ups",
    "elektroverteilungspunkt": "mep-electric-distribution-board",
    "fenster-oberlichter": "architecture-window-exterior",
    "feuerloschanschluss": "mep-fire-suppression-terminal",
    "fundamente": "architecture-footing",
    "gebaude-bauwerke": "building",
    "generator": "mep-electric-generator",
    "geschoss-stockwerk": "storey",
    "geschossvolumen": "spaces-gross-volume",
    "gitter": "mep-air-terminal",
    "heizkorper": "mep-space-heater",
    "innenraum": "spaces-interior",
    "kabeltrasse": "mep-schematic-tray",
    "kaltemaschine-luft-wasser": "mep-chiller",
    "konvektor-mit-ventilator": "mep-unitary-equipment",
    "kuhlbalken": "mep-cooled-beam",
    "kuhlturm": "mep-cooling-tower",
    "luftauslasskasten": "mep-air-terminal-box",
    "luftkanal": "mep-schematic-duct",
    "luftraum": "spaces-luftraum",
    "modelleinfugepunkt-disziplin": "survey-reference-point",
    "modelleinfugepunkt-perimeter-bauwerk": "survey-reference-point",
    "monoblock": "mep-unitary-equipment",
    "planungsperimeter-projektperimeter": "site",
    "projekt": "project",
    "rauchmelder": "mep-sensor",
    "regelventil": "mep-valve",
    "rohrleitung": "mep-schematic-pipe",
    "sanitarobjekt": "mep-sanitary-terminal",
    "schaltgerat": "mep-switching-device",
    "steckdose": "mep-outlet",
    "stutzen": "architecture-column",
    "tank-behalter": "mep-tank",
    "transformator": "mep-transformer",
    "tur-tor-revisionsoffnung": "architecture-door-interior",
    "unter-uberzuge": "architecture-beam",
    "ventilator": "mep-fan",
    # System proxies: the main component stands for the system.
    "i-001-usv": "mep-ups",
    "i-005-druckluft": "mep-compressor",
    "i-006-kalteanlagen": "mep-chiller",
    "i-007-aufzuge": "spaces-elevator",
    "i-008-brandmeldeanlage": "mep-alarm",
    "i-011-abwasserpumpen": "mep-pump",
    "i-013-anpassrampen": "structural-ramp",
    "i-019-einbruchmeldeanlage": "mep-sensor",
    "i-024-ersatzstromanlage": "mep-electric-generator",
    "i-026-gas-gebaudeinstallation": "mep-gas-terminal",
    "i-029-heiz-warmeerzeugung": "mep-boiler",
    "i-030-heiz-warmeverteilung": "mep-valve",
    "i-031-heiz-versorg-lager": "mep-tank",
    "i-033-kaltespeicher": "mep-tank",
    "i-034-luftungsanlagen": "mep-unitary-equipment",
    "i-035-ns-schaltanlage": "mep-electric-distribution-board",
    "i-064-transformatoren": "mep-transformer",
    "i-066-wassererwarmer": "mep-boiler",
    "i-069-warmeerz-oel-gas": "mep-boiler",
    "i-081-oel-und-fettabscheider": "mep-tank",
}


def resolve(source: str) -> tuple[str, str]:
    """``("card", card id)`` or ``("slug", Reference slug)`` for a picture source."""
    if source in CARDS:
        return "card", source
    if source in REUSE:
        return "slug", REUSE[source]
    if (REFERENCE_IMAGES / f"{source}.png").exists():
        return "slug", source
    raise KeyError(f"unknown picture source {source!r}")


def arma_sources() -> dict[str, str]:
    """arma id → picture source for every arma element that has one."""
    sources: dict[str, str] = {}
    for path in sorted(ARMA_ELEMENTS.glob("*.yaml")):
        arma_id = path.stem
        if arma_id in ARMA_SOURCES:
            sources[arma_id] = ARMA_SOURCES[arma_id]
        elif arma_id in CARDS or arma_id in REUSE:
            sources[arma_id] = arma_id
    return sources


def catalog_entry(slug: str) -> dict:
    """Reference catalog entry that renders the picture of ``slug``."""
    for entry in SAMPLE_CATALOG:
        if entry.get("attach_element") == slug:
            return entry
    for entry in SAMPLE_CATALOG:
        if entry.get("id") == f"spatial-{slug}-01":
            return entry
    raise KeyError(f"no Reference catalog entry for {slug!r}")


def render_reference(slug: str, out_dir: Path) -> tuple[Path, Path]:
    entry = catalog_entry(slug)
    with contextlib.redirect_stdout(io.StringIO()):
        _, failed, _ = run_catalog([entry], out_dir, attach=False, accent=ARMA_ACCENT, brand=False)
    if failed:
        raise RuntimeError(f"Reference render failed for {slug!r}")
    return out_dir / f"{entry['id']}.png", out_dir / f"{entry['id']}-print.tif"


def source_files(kind: str, key: str, work_dir: Path, rendered: dict[str, tuple[Path, Path]]) -> tuple[Path, Path]:
    """PNG and print TIF for a source; each source is rendered once per run."""
    if key not in rendered:
        if kind == "card":
            rendered[key] = render_card(key, CARDS[key], work_dir / "cards", work_dir / "ifc", accent=ARMA_ACCENT, brand=False)
        else:
            rendered[key] = render_reference(key, work_dir / "reference")
    return rendered[key]


def place(arma_id: str, png: Path, tif: Path | None, image_dir: Path) -> tuple[Path, Path | None]:
    image_dir.mkdir(parents=True, exist_ok=True)
    target_png = image_dir / f"{arma_id}.png"
    shutil.copyfile(png, target_png)
    if tif is None:
        return target_png, None
    target_tif = image_dir / f"{arma_id}-print.tif"
    shutil.copyfile(tif, target_tif)
    return target_png, target_tif


def referenced_pictures() -> set[str]:
    names: set[str] = set()
    for path in ARMA_ELEMENTS.glob("*.yaml"):
        for match in re.finditer(r"^picture(?:_print)?_link:\s*(\S+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE):
            if match.group(1) != "null":
                names.add(match.group(1))
    return names


def _set_scalar(text: str, key: str, value: str | None, after: str) -> str:
    rendered = "null" if value is None else value
    pattern = re.compile(rf"^{key}:.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(f"{key}: {rendered}", text, count=1)
    anchor = re.compile(rf"^{after}:.*$", re.MULTILINE)
    match = anchor.search(text)
    if not match:
        raise ValueError(f"no {after!r} line to insert {key!r} after")
    return text[: match.end()] + f"\n{key}: {rendered}" + text[match.end():]


def link_element(arma_id: str, png: Path, tif: Path | None) -> set[str]:
    """Point the element YAML at the new pictures; return the replaced file names."""
    path = ARMA_ELEMENTS / f"{arma_id}.yaml"
    text = path.read_text(encoding="utf-8")
    old = {
        match.group(1)
        for match in re.finditer(r"^picture(?:_print)?_link:\s*(\S+)\s*$", text, re.MULTILINE)
        if match.group(1) != "null"
    }
    text = _set_scalar(text, "picture_link", png.name, after="entity_ifc4_3")
    text = _set_scalar(text, "picture_print_link", tif.name if tif else None, after="picture_link")
    path.write_text(text, encoding="utf-8")
    return old - {png.name, tif.name if tif else None}


def delete_unreferenced(candidates: set[str]) -> list[str]:
    keep = referenced_pictures()
    deleted = []
    for name in sorted(candidates - keep):
        path = ARMA_IMAGES / name
        if path.suffix.lower() in IMAGE_SUFFIXES and path.exists():
            path.unlink()
            deleted.append(name)
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", help="arma element ids (default: all with a source)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "data-schema")
    parser.add_argument("--publish", action="store_true", help="Write into arma-elementplan-data and link the YAML")
    parser.add_argument("--prune", action="store_true", help="With --publish: delete all unreferenced arma pictures")
    args = parser.parse_args(argv)

    sources = arma_sources()
    image_dir = ARMA_IMAGES if args.publish else args.output_dir
    wanted = set(args.only) if args.only else None
    unknown = (wanted or set()) - set(sources)
    if unknown:
        print(f"No picture source for: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1

    failed: list[str] = []
    replaced: set[str] = set()
    rendered: dict[str, tuple[Path, Path]] = {}
    done = 0
    for arma_id, source in sources.items():
        if wanted is not None and arma_id not in wanted:
            continue
        try:
            kind, key = resolve(source)
            png, tif = place(arma_id, *source_files(kind, key, args.output_dir, rendered), image_dir)
            if args.publish:
                replaced |= link_element(arma_id, png, tif)
            done += 1
            print(f"OK  {arma_id} ({kind} {key})")
        except Exception:
            failed.append(arma_id)
            print(f"ERR {arma_id}", file=sys.stderr)
            traceback.print_exc()
    if args.publish:
        candidates = replaced
        if args.prune:
            candidates |= {path.name for path in ARMA_IMAGES.iterdir()}
        for name in delete_unreferenced(candidates):
            print(f"DEL {name}")
    print(f"\n{done} written, {len(failed)} failed")
    if failed:
        print("Failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
