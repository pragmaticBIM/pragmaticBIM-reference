"""Guard the client domain and the client-requirements workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from catalog.baseline import attribute_applies_to_all_workflows


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_ID = "pragmaticbim:domain/client"
WORKFLOW_ID = "pragmaticbim:workflow/bes-client-requirements"
LANGS = ("de", "fr", "it", "en")
CLIENT_ELEMENTS = (
    "client",
    "client-invoice-address",
    "project",
    "site",
    "building",
    "storey",
    "survey-reference-point",
    "spaces-interior",
    "spaces-exterior",
)
MILESTONES = ("DesignStartDate", "PermitSubmissionDate", "ConstructionStartDate", "HandoverDate")
ADDRESS = ("Purpose", "UserDefinedPurpose", "AddressLines", "PostalCode", "Town", "Country")
ORDER_PSETS = {
    ("client", "Name"): None,
    **{("client-invoice-address", name): None for name in ADDRESS},
    ("project", "TargetCost"): "ePset_ProjectRequirement",
    **{("project", name): "ePset_ProjectRequirement" for name in MILESTONES},
}
SPACE_LINKS = (
    "Name",
    "PredefinedType",
    "InteriorOrExteriorSpace",
    "LongName",
    "NetPlannedArea",
    "MinClearHeight",
    "MinClearLength",
    "MinClearWidth",
    "UsageUnitReference",
)
LINKS = {
    *ORDER_PSETS,
    *(("spaces-interior", name) for name in SPACE_LINKS),
    *(("spaces-exterior", name) for name in SPACE_LINKS),
    ("spaces-exterior", "FloorCovering"),
}


def _load(relative_path: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _attribute(slug: str, name: str) -> dict[str, Any]:
    for attribute in _load(f"elements/{slug}.yaml").get("attributes") or []:
        if attribute.get("name") == name and attribute.get("status") == "active":
            return attribute
    raise AssertionError(f"{slug} {name} missing")


def test_client_domain_is_localized() -> None:
    domain = _load("domains/client.yaml")

    assert domain["id"] == DOMAIN_ID
    assert domain["code"] == "BHR"
    assert domain["status"] == "active"
    for field in ("name", "definition", "file_name"):
        assert all(str(domain[field].get(lang) or "").strip() for lang in LANGS)
    assert all("_BHR_" in domain["file_name"][lang] for lang in LANGS)


def test_client_requirements_workflow_is_localized_and_active() -> None:
    workflow = _load("workflows/bes-client-requirements.yaml")

    assert workflow["id"] == WORKFLOW_ID
    assert workflow["code"] == "BES-CLIENT-REQUIREMENTS"
    assert workflow["status"] == "active"
    assert workflow["parent_workflow"] == "pragmaticbim:workflow/bes"
    assert workflow["needed_in_domain"] == [DOMAIN_ID]
    for field in ("name", "description"):
        assert all(str(workflow[field].get(lang) or "").strip() for lang in LANGS)


def test_room_programme_is_part_of_the_client_domain() -> None:
    workflow = _load("workflows/bes-room-program-brief.yaml")

    assert DOMAIN_ID in workflow["needed_in_domain"]


def test_client_elements_name_the_client_domain() -> None:
    for slug in CLIENT_ELEMENTS:
        assert DOMAIN_ID in _load(f"elements/{slug}.yaml")["needed_in_domain"], slug


def test_order_attributes_use_native_ifc_where_possible() -> None:
    for (slug, name), pset in ORDER_PSETS.items():
        attribute = _attribute(slug, name)
        assert attribute["pset"] == pset, (slug, name)
        assert all(str(attribute["definition"].get(lang) or "").strip() for lang in LANGS)

    assert _attribute("project", "TargetCost")["unit"] == "CHF"
    for name in MILESTONES:
        attribute = _attribute("project", name)
        assert attribute["datatype"] == "IfcDate", name
        assert "ifc2x3" not in attribute["ifc_versions"], name


def test_client_and_invoice_address_map_to_native_entities() -> None:
    client = _load("elements/client.yaml")
    address = _load("elements/client-invoice-address.yaml")

    for key in ("entity_ifc2x3", "entity_ifc4", "entity_ifc4_3"):
        assert client[key] == "IfcActor"
        assert address[key] == "IfcPostalAddress"
    assert _attribute("client-invoice-address", "Purpose")["is_applicability"] is True
    assert _attribute("client-invoice-address", "UserDefinedPurpose")["is_applicability"] is True
    for lang in LANGS:
        purpose = _load("values/userdefinedpurpose-invoice-address.yaml")["values"][lang][0]
        assert purpose in address["applicability"][lang], lang


def test_invoice_address_is_not_the_site_or_building_address() -> None:
    for slug in ("site", "building", "project"):
        for attribute in _load(f"elements/{slug}.yaml").get("attributes") or []:
            assert attribute["name"] not in {"Street", "PostalCode", "Town", "Country", "ClientName"}, slug


def test_client_requirements_links_order_attributes() -> None:
    workflows = [
        _load(f"workflows/{path.name}")
        for path in sorted((ROOT / "workflows").glob("*.yaml"))
    ]
    linked: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "elements").glob("*.yaml")):
        element = yaml.safe_load(path.read_text(encoding="utf-8"))
        for attribute in element.get("attributes") or []:
            if WORKFLOW_ID not in (attribute.get("needed_for_workflows") or []):
                continue
            if attribute_applies_to_all_workflows(attribute, workflows):
                continue
            linked.add((path.stem, attribute["name"]))

    assert linked == LINKS
