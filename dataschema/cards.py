"""Card registry: data-schema element id → scene, accent and framing."""

from __future__ import annotations

from dataschema import scenes_abstract as abstract
from dataschema import scenes_building as building
from dataschema import scenes_civil as civil
from dataschema import scenes_rooms as rooms
from dataschema.render import Card
from render.engrave_specs import EngraveSpec

_BACK_WALL = EngraveSpec(prefer_wall=True, wall_name="Rueckwand", wall_top=True)
_LOWEST = EngraveSpec(prefer_lowest=True)
_WALL_TOP = EngraveSpec(prefer_wall=True, wall_top=True)
_FACADE = EngraveSpec(prefer_wall=True, wall_name="Gebaeude", wall_top=True)

def _room_cards(build, ids, **kwargs) -> dict[str, Card]:
    return {card_id: Card(build, card_id, engrave=_BACK_WALL, **kwargs) for card_id in ids}


def _civil_cards(build, ids, **scene_kwargs) -> dict[str, Card]:
    return {card_id: Card(build, card_id, scene_kwargs, camera_padding=1.3, engrave=_FACADE) for card_id in ids}


CARDS: dict[str, Card] = {
    # Heizraum ---------------------------------------------------------------
    **_room_cards(
        rooms.heating_room,
        (
            "rohrformteil",
            "rohrzubehor",
            "motoranschluss",
            "elektromotor",
            "messgerat-prozess",
            "durchflussmesser",
            "i-075-warmevert-entsalzung",
            "i-076-warmevert-magflussfi",
            "brenner",
            "regler",
            "verbrennungsmotor",
            "i-021-energiemanagement",
            "i-027-gebaudeleitsystem-gebaudeautomation",
            "i-077-warmevert-entgasung",
            "i-078-warmevert-expansion",
        ),
    ),
    "i-070-warmeerz-stuckholz": Card(rooms.heating_room, "heat-gen", {"fuel": "log"}, engrave=_BACK_WALL),
    "i-071-warmeerz-pellets": Card(rooms.heating_room, "heat-gen", {"fuel": "pellet"}, engrave=_BACK_WALL),
    "i-072-warmeerz-schnitzel": Card(rooms.heating_room, "heat-gen", {"fuel": "chip"}, engrave=_BACK_WALL),
    # Kaeltezentrale ---------------------------------------------------------
    **_room_cards(rooms.chiller_room, ("verdampfer", "kondensator", "energieumwandlungsgerat", "i-073-warmeerz-warmepumpen")),
    # Wasserzentrale ---------------------------------------------------------
    **_room_cards(
        rooms.water_room,
        (
            "i-016-chlordosierungsanlage",
            "i-018-druckerhohungsanlage",
            "i-022-enthartungsanlage",
            "i-023-entsalzungsanlage",
            "i-036-osmoseanlage",
            "i-065-uv-anlage",
        ),
    ),
    # Lueftungszentrale ------------------------------------------------------
    **_room_cards(rooms.air_handling_room, ("filter", "register-heiz-kuhlregister", "schalldampfer", "luftkanalformteil", "luftkanalzubehor")),
    # Hauptverteilung --------------------------------------------------------
    **_room_cards(
        rooms.switchboard_room,
        (
            "schutzeinrichtung",
            "ausloseeinheit",
            "kabel",
            "kabel-formteil",
            "kabeltrassen-formteil",
            "i-015-blindstromkompensation",
            "i-020-einspeisezahler",
            "i-032-hs-schaltanlage",
            "i-017-co2-loschanlage",
        ),
    ),
    # Korridor ---------------------------------------------------------------
    **{
        card_id: Card(building.corridor, card_id, {"system": card_id}, engrave=_BACK_WALL)
        for card_id in (
            "i-002-notlichtanlage",
            "i-009-personenvereinzelungsanlage",
            "i-010-videouberwachung",
            "i-012-alarmmanagement",
            "i-014-abschlusse",
            "i-025-evakuationsanlage",
            "i-079-el-zutrittskontrolle",
        )
    },
    # Wandabschnitt / Kueche / Buero -----------------------------------------
    **{
        card_id: Card(
            building.electro_wall,
            card_id,
            camera_padding=1.3,
            engrave=EngraveSpec(prefer_wall=True, wall_name="Trennwand", wall_top=True),
        )
        for card_id in ("abzweigdose", "i-080-domotik")
    },
    **{
        card_id: Card(
            building.kitchen,
            card_id,
            camera_padding=1.4,
            engrave=EngraveSpec(prefer_wall=True, wall_name="Aussenwand", wall_top=True),
        )
        for card_id in ("elektrisches-gerat", "endgerat-fluid")
    },
    **{
        card_id: Card(building.office_lighting, card_id, camera_padding=1.35, engrave=_LOWEST)
        for card_id in ("lampe", "lichtquelle")
    },
    # Dach / Halle / Gelaende ------------------------------------------------
    **{
        card_id: Card(building.roof_energy, card_id, engrave=_WALL_TOP)
        for card_id in ("solargerat", "dach-abgasterminal", "i-037-photovoltaikanlage", "i-074-warmeerz-solar")
    },
    **_room_cards(building.hall, ("i-003-krananlagen", "i-028-gleisanlagen")),
    **{
        card_id: Card(building.site_power, card_id, camera_padding=1.3, engrave=_LOWEST)
        for card_id in ("i-067-wasserkraftwerke", "i-068-windkraftwerke")
    },
    # Tiefbau ----------------------------------------------------------------
    **_civil_cards(
        civil.sewage,
        (
            "abwasser-haltung-kanal",
            "abwasser-kaliberwechsel",
            "abwasser-normalschacht",
            "abwasserkanalschacht",
            "abwasser-leitung",
            "abwasser-entwasserungsrinne",
            "abwasser-versickerungsanlage",
        ),
    ),
    **_civil_cards(
        civil.sewage_structures,
        (
            "abwasser-spezialbauwerk-regenbecken",
            "abwasser-spezialbauwerk-pumpwerk",
            "abwasser-spezialbauwerk-oelabscheider-schwimmstoffabscheider",
            "abwasser-spezialbauwerk-weitere",
        ),
    ),
    **_civil_cards(
        civil.electricity,
        (
            "elektrizitat-trasse-unterirdisch",
            "elektrizitaet-schacht",
            "elektrizitaet-kabine",
            "elektrizitaet-oeffentlicher-verbraucher",
            "elektrizitat-station",
            "elektrizitat-tragwerk",
            "elektrizitat-trasse-oberirdisch",
            "elektrizitaet-anker-strebe",
        ),
    ),
    **_civil_cards(
        civil.electricity,
        (
            "elektrizitaet-spezialbauwerk-schacht",
            "elektrizitat-spezialbauwerk-station",
            "elektrizitaet-spezialbauwerk-kabine",
            "elektrizitat-spezialbauwerk-oeffentlicher-verbraucher",
        ),
        special=True,
    ),
    **_civil_cards(
        civil.district_energy,
        (
            "fernwarme-leitung",
            "fernwarme-trasse-unterirdisch",
            "fernwarme-trasse-oberirdisch",
            "fernwarme-bauwerk-kammer",
            "fernwarme-bauwerk-station",
            "fernwarme-bauwerk-spezialbauwerk",
        ),
        network="fernwarme",
    ),
    **_civil_cards(
        civil.district_energy,
        (
            "fernkalte-leitung",
            "fernkalte-trasse-unterirdisch",
            "fernkalte-trasse-oberirdisch",
            "fernkalte-bauwerk-station",
            "fernkalte-bauwerk-spezialbauwerk",
        ),
        network="fernkalte",
    ),
    **_civil_cards(
        civil.gas,
        ("gas-leitung", "gas-sicherheitskorridor", "gas-absperrorgan", "gas-schacht", "gas-siphon", "gas-gaslaterne"),
    ),
    # Klassifizierung und Gruppierung ----------------------------------------
    "ebkp-name-der-klassifizierung": Card(abstract.ebkp, abstract.EBKP_GROUPS, camera_padding=1.3, engrave=_LOWEST),
    "ebkp-werte-fur-klassifizierung": Card(abstract.ebkp, "ebkp-e", camera_padding=1.3, engrave=_LOWEST),
    "sia416-name-der-klassifizierung": Card(abstract.sia416, abstract.SIA_AREAS, camera_padding=1.3, engrave=_LOWEST),
    "sia416-werte-fur-klassifizierung": Card(abstract.sia416, "sia-hnf", camera_padding=1.3, engrave=_LOWEST),
    "sicherheitszone-schutzzonen": Card(abstract.protection_zone, "schutzzone", camera_padding=1.3, engrave=_LOWEST),
    "etappe": Card(abstract.stages, "etappe-1", camera_padding=1.3, engrave=_LOWEST),
}
