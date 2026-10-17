from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
ELEMENTS_DIR = REPO_ROOT / "elements"
WORKFLOW_ID = "pragmaticbim:workflow/qas-component-cost-plausibility"
EARLY_COST_WORKFLOW = "pragmaticbim:workflow/des-element-based-cost-early"
LATE_COST_WORKFLOW = "pragmaticbim:workflow/des-element-based-cost-late"
TENDER_WORKFLOW = "pragmaticbim:workflow/bes-element-based-tendering"
POSTCALC_WORKFLOW = (
    "pragmaticbim:workflow/bes-element-cost-post-calculation"
)

REFERENCE_QUANTITIES = {
    "architecture-wall-exterior": ("Qto_WallBaseQuantities.NetSideArea", "CHF/m²"),
    "architecture-wall-interior-loadbearing": (
        "Qto_WallBaseQuantities.NetSideArea",
        "CHF/m²",
    ),
    "architecture-wall-interior": ("Qto_WallBaseQuantities.NetSideArea", "CHF/m²"),
    "architecture-wall-cladding-exterior": (
        "Qto_CoveringBaseQuantities.NetArea",
        "CHF/m²",
    ),
    "architecture-wall-cladding-interior": (
        "Qto_CoveringBaseQuantities.NetArea",
        "CHF/m²",
    ),
    "architecture-floor-covering": ("Qto_CoveringBaseQuantities.NetArea", "CHF/m²"),
    "architecture-ceiling-suspended": (
        "Qto_CoveringBaseQuantities.NetArea",
        "CHF/m²",
    ),
    "architecture-slab-base": ("Qto_SlabBaseQuantities.GrossVolume", "CHF/m³"),
    "architecture-slab-floor": ("Qto_SlabBaseQuantities.GrossArea", "CHF/m²"),
    "architecture-slab-balcony": ("Qto_SlabBaseQuantities.GrossArea", "CHF/m²"),
    "architecture-slab-flat-roof": (
        "Qto_SlabBaseQuantities.GrossArea",
        "CHF/m²",
    ),
    "architecture-roof-pitched": ("Qto_RoofBaseQuantities.GrossArea", "CHF/m²"),
    "architecture-roof-drainage": (
        "Qto_CoveringBaseQuantities.NetArea",
        "CHF/m²",
    ),
    "architecture-footing": ("Qto_FootingBaseQuantities.GrossVolume", "CHF/m³"),
    "architecture-column": ("Qto_ColumnBaseQuantities.GrossVolume", "CHF/m³"),
    "architecture-beam": ("Qto_BeamBaseQuantities.Length", "CHF/m"),
    "architecture-stair": ("Qto_StairBaseQuantities.GrossVolume", "CHF/m³"),
    "architecture-railing": ("Qto_RailingBaseQuantities.Length", "CHF/m"),
    "architecture-window-exterior": ("Qto_WindowBaseQuantities.Area", "CHF/m²"),
    "architecture-window-interior": ("Qto_WindowBaseQuantities.Area", "CHF/m²"),
    "architecture-door-exterior": ("Qto_DoorBaseQuantities.Area", "CHF/m²"),
    "architecture-door-interior": ("Qto_DoorBaseQuantities.Area", "CHF/m²"),
}


def _load_element(slug: str) -> dict:
    return yaml.safe_load((ELEMENTS_DIR / f"{slug}.yaml").read_text())


def _attribute(element: dict, name: str, pset: str) -> dict:
    matches = [
        attribute
        for attribute in element["attributes"]
        if attribute["name"] == name and attribute.get("pset") == pset
    ]
    assert len(matches) == 1, f"Expected one {pset}.{name}, found {len(matches)}"
    return matches[0]


def test_cost_properties_and_reference_quantities_are_consistent():
    assert len(REFERENCE_QUANTITIES) == 22

    for slug, (quantity_path, price_unit) in REFERENCE_QUANTITIES.items():
        element = _load_element(slug)
        quantity_pset, quantity_name = quantity_path.split(".", maxsplit=1)

        unit_price = _attribute(element, "UnitPrice", "ePset_Cost")
        assert unit_price["datatype"] == "IfcMonetaryMeasure"
        assert unit_price["unit"] == price_unit
        assert WORKFLOW_ID in unit_price["needed_for_workflows"]

        reference_quantity = _attribute(element, "ReferenceQuantity", "ePset_Cost")
        assert reference_quantity["datatype"] == "IfcLabel"
        assert WORKFLOW_ID in reference_quantity["needed_for_workflows"]
        for definition in reference_quantity["definition"].values():
            assert quantity_path in definition

        quantity = _attribute(element, quantity_name, quantity_pset)
        assert WORKFLOW_ID in quantity["needed_for_workflows"]
        assert {"31", "32", "33", "41"}.issubset(
            set(quantity["needed_in_phases"])
        )

        if slug != "architecture-roof-drainage":
            assert {
                EARLY_COST_WORKFLOW,
                LATE_COST_WORKFLOW,
                POSTCALC_WORKFLOW,
            }.issubset(set(unit_price["needed_for_workflows"]))
            assert {
                EARLY_COST_WORKFLOW,
                LATE_COST_WORKFLOW,
                TENDER_WORKFLOW,
                POSTCALC_WORKFLOW,
            }.issubset(set(reference_quantity["needed_for_workflows"]))
            assert {
                EARLY_COST_WORKFLOW,
                LATE_COST_WORKFLOW,
                TENDER_WORKFLOW,
                POSTCALC_WORKFLOW,
            }.issubset(set(quantity["needed_for_workflows"]))

            award_interfaces = [
                attribute
                for attribute in element["attributes"]
                if attribute["name"] == "AwardInterface"
            ]
            if award_interfaces:
                assert {TENDER_WORKFLOW, POSTCALC_WORKFLOW}.issubset(
                    set(award_interfaces[0]["needed_for_workflows"])
                )
