"""Street scene: tree, car, and road on a ground slab."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from generators.street_scene import CAR_NAME, ROAD_NAME, TREE_NAME, generate_street_scene

ROOT = Path(__file__).resolve().parents[1]


def test_street_scene_has_tree_car_and_road() -> None:
    ifc_file, products = generate_street_scene()
    assert products["tree"].Name == TREE_NAME
    assert products["road"].Name == ROAD_NAME
    assert products["car"].Name == CAR_NAME
    assert products["tree"].is_a("IfcGeographicElement")
    assert products["tree"].PredefinedType == "VEGETATION"
    for product in products.values():
        assert product.Representation is not None
        named = [
            item
            for item in ifc_file.by_type("IfcProduct")
            if getattr(item, "Name", None) == product.Name
        ]
        assert product in named


def test_street_scene_picture_is_published() -> None:
    png = ROOT / "media" / "images" / "scene-tree-car-road.png"
    tif = ROOT / "media" / "images" / "scene-tree-car-road-print.tif"
    ifc_path = ROOT / "media" / "attachments" / "scene-tree-car-road.ifc"
    assert png.is_file()
    assert tif.is_file()
    assert ifc_path.is_file()
    with Image.open(png) as image:
        assert image.size == (1024, 1024)
        orange = 0
        for y in range(0, image.height, 4):
            for x in range(0, image.width, 4):
                red, green, blue = image.getpixel((x, y))[:3]
                if red > 160 and red > green + 25 and blue < 140:
                    orange += 1
        assert orange > 200
