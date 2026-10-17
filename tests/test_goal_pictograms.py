"""Goal pictograms: one amber product per scene. Book YAML does not publish them."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generators.goal_pictograms import ACCENT_NAMES, GENERATORS, PLATE_NAME


def _load_goals() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / "project_goals").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id") and not data.get("is_boundary_condition"):
            items.append(data)
    return items


def test_each_scene_has_one_amber_primary() -> None:
    assert set(GENERATORS) == set(ACCENT_NAMES)
    for slug, build in GENERATORS.items():
        ifc_file, primary = build()
        accent = ACCENT_NAMES[slug]
        assert primary.Name == accent
        assert primary.Representation is not None
        named = [
            product
            for product in ifc_file.by_type("IfcProduct")
            if getattr(product, "Name", None) == accent
        ]
        assert named == [primary], slug


def test_each_scene_has_shared_ground_plate() -> None:
    for slug, build in GENERATORS.items():
        ifc_file, _primary = build()
        plates = [
            product
            for product in ifc_file.by_type("IfcProduct")
            if getattr(product, "Name", None) == PLATE_NAME
        ]
        assert len(plates) == 1, slug
        assert plates[0].Representation is not None


@pytest.mark.xfail(
    reason="project goal critical-infrastructure has no pictogram generator yet",
    strict=True,
)
def test_goal_yaml_does_not_publish_pictogram() -> None:
    """Rejected pictograms stay out of the book until a replacement is linked."""
    goals = _load_goals()
    assert goals
    slugs = set()
    for goal in goals:
        slug = str(goal["id"]).rsplit("/", 1)[-1]
        assert not goal.get("picture_link"), slug
        assert not goal.get("picture_print_link"), slug
        assert slug in GENERATORS
        slugs.add(slug)
    assert slugs == set(GENERATORS)
