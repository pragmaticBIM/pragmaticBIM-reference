"""Card registry: data-schema element id → scene, accent and framing."""

from __future__ import annotations

from dataschema import scenes_abstract as abstract
from dataschema import scenes_access as access
from dataschema import scenes_building as building
from dataschema import scenes_civil as civil
from dataschema import scenes_rooms as rooms
from dataschema import scenes_safety as safety
from dataschema import scenes_site as site
from dataschema import scenes_spatial as spatial
from dataschema import scenes_special as special
from dataschema import scenes_transport as transport
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
    "d04-02-001-gasmeldeanlage": Card(rooms.heating_room, "gasmeldeanlage", {"gas_detection": True}, engrave=_BACK_WALL),
    **{
        key: Card(rooms.heating_room, key, {"extra": key}, engrave=_BACK_WALL)
        for key in (rooms.HEAT_ELECTRIC_STORAGE, rooms.HEAT_SUBDISTRIBUTION)
    },
    **{
        key: Card(rooms.heating_room, key, {"extra": key}, camera_padding=1.5, camera_focus=(key, "heat-gen"), engrave=_BACK_WALL)
        for key in (rooms.HEAT_SAFETY, rooms.HEAT_FLUE_MEASUREMENT)
    },
    **{
        key: Card(rooms.heating_room, key, {"fuel": fuel, "extra": key}, engrave=_BACK_WALL)
        for key, fuel in (
            (rooms.HEAT_FLUE_FILTER, "log"),
            (rooms.HEAT_SCRUBBER, "log"),
            (rooms.HEAT_CHIP_STORE, "chip"),
            (rooms.HEAT_PELLET_STORE, "pellet"),
        )
    },
    # Kaeltezentrale ---------------------------------------------------------
    **_room_cards(rooms.chiller_room, ("verdampfer", "kondensator", "energieumwandlungsgerat", "i-073-warmeerz-warmepumpen")),
    rooms.TUBE_BUNDLE: Card(rooms.chiller_room, rooms.TUBE_BUNDLE, {"extra": rooms.TUBE_BUNDLE}, camera_focus=("verdampfer", "kondensator"), engrave=_BACK_WALL),
    rooms.GAS_ENGINE_HEAT_PUMP: Card(rooms.chiller_room, rooms.GAS_ENGINE_HEAT_PUMP, {"extra": rooms.GAS_ENGINE_HEAT_PUMP}, engrave=_BACK_WALL),
    # Wasserzentrale ---------------------------------------------------------
    **{key: Card(rooms.water_room, key, {"extra": key}, engrave=_BACK_WALL) for key in (rooms.WATER_FILTER, rooms.WATER_NEUTRALISATION)},
    rooms.DRAIN_NEUTRALISATION: Card(
        rooms.water_room,
        rooms.DRAIN_NEUTRALISATION,
        {"extra": rooms.DRAIN_NEUTRALISATION},
        camera_focus=(rooms.DRAIN_NEUTRALISATION, "i-036-osmoseanlage"),
        engrave=_BACK_WALL,
    ),
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
    # Untergeschoss ----------------------------------------------------------
    **_room_cards(rooms.backflow_basement, ("d09-01-002-ruckstauverschlusse-elektrisch", "d09-01-001-leitungen"), camera_padding=1.4),
    # Hausanschlussraum ------------------------------------------------------
    **_room_cards(rooms.internal_lightning_protection, ("d01-04-007-innere-blitzschutzanlagen",), camera_padding=1.3),
    # Schutzanlage -----------------------------------------------------------
    **_room_cards(rooms.nemp_protection, ("d01-04-008-schutzschaltungen-nemp-uberspannungsschutz",), camera_padding=1.3),
    # Serverraum -------------------------------------------------------------
    **_room_cards(rooms.water_mist_room, ("d04-03-003-wassernebelloschanlage",)),
    **_room_cards(rooms.foam_room, ("d04-03-004-schaumloschanlage",)),
    # Lueftungszentrale ------------------------------------------------------
    **_room_cards(rooms.air_handling_room, ("filter", "register-heiz-kuhlregister", "schalldampfer", "luftkanalformteil", "luftkanalzubehor")),
    **{key: Card(rooms.air_handling_room, key, {"extra": key}, engrave=_BACK_WALL) for key in (rooms.HUMIDIFIER, rooms.HEAT_RECOVERY)},
    rooms.VIBRATION_ISOLATOR: Card(
        rooms.air_handling_room,
        rooms.VIBRATION_ISOLATOR,
        {"extra": rooms.VIBRATION_ISOLATOR},
        camera_focus=(rooms.VIBRATION_ISOLATOR,),
        camera_padding=1.9,
        engrave=_BACK_WALL,
    ),
    # Hauptverteilung --------------------------------------------------------
    **_room_cards(
        rooms.switchboard_room,
        (
            "schutzeinrichtung",
            "ausloseeinheit",
            "kabel",
            "kabeltrassen-formteil",
            "i-015-blindstromkompensation",
            "i-020-einspeisezahler",
            "i-032-hs-schaltanlage",
            "i-017-co2-loschanlage",
        ),
    ),
    "kabel-formteil": Card(
        rooms.switchboard_room,
        "kabel-formteil",
        camera_padding=2.0,
        camera_focus=("kabel-formteil", "schutzeinrichtung"),
        engrave=_BACK_WALL,
    ),
    "zeitsteuergerat": Card(rooms.switchboard_room, "zeitsteuergerat", {"time_switch": True}, engrave=_BACK_WALL),
    rooms.OT_NETWORK: Card(rooms.switchboard_room, rooms.OT_NETWORK, {"ot_network": True}, engrave=_BACK_WALL),
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
            "d01-11-003-telefon-anlagen",
            "d01-11-004-ruf-such-und-sprechanlage",
            "d01-11-005-lichtrufanlage",
            "d04-03-002-nassloschposten",
            "audiovisuelles-gerat",
            "d01-11-031-gegensprechanlagen",
            "d03-02-002-sicherheitsleitsysteme",
            "d03-02-004-schlusseldepot-elektronisch",
            "d04-05-001-handfeuerloscher",
            "g05-07-001-schliessanlage",
            "g05-07-002-sicherheits-und-brandschutzturen-mit-elektr-alarmkomponenten",
            "g05-07-016-brandschutzturen-tore-ohne-elektr-alarmkomponenten",
            "d12-02-003-rohrpostanlage",
        )
    },
    # Gebaeudeeingang --------------------------------------------------------
    "g05-07-008-schleusen-automatisch": Card(
        building.building_entry,
        "g05-07-008-schleusen-automatisch",
        camera_padding=1.3,
        engrave=EngraveSpec(prefer_wall=True, wall_name="Fassade", wall_top=True),
    ),
    building.INTERIOR_DOOR: Card(building.automatic_interior_doors, building.INTERIOR_DOOR, camera_padding=1.3, engrave=_BACK_WALL),
    building.INTERIOR_GATE: Card(
        building.automatic_interior_doors,
        building.INTERIOR_GATE,
        {"key": building.INTERIOR_GATE, "gate": True},
        camera_padding=1.3,
        engrave=_BACK_WALL,
    ),
    building.EXTERIOR_GATE: Card(
        building.gate_facade,
        building.EXTERIOR_GATE,
        camera_padding=1.25,
        engrave=EngraveSpec(prefer_wall=True, wall_name="Fassade", wall_top=True),
    ),
    # Wandabschnitt / Kueche / Buero -----------------------------------------
    **{
        card_id: Card(
            building.electro_wall,
            card_id,
            camera_padding=1.3,
            engrave=EngraveSpec(prefer_wall=True, wall_name="Trennwand", wall_top=True),
        )
        for card_id in ("i-080-domotik",)
    },
    "einheitsregler": Card(
        building.electro_wall,
        "einheitsregler",
        {"room_unit": True},
        camera_padding=1.3,
        engrave=EngraveSpec(prefer_wall=True, wall_name="Trennwand", wall_top=True),
    ),
    "abzweigdose": Card(
        building.detector_line_wall,
        "abzweigdose",
        camera_padding=1.3,
        engrave=EngraveSpec(prefer_wall=True, wall_name="Trennwand", wall_top=True),
    ),
    **{
        card_id: Card(
            building.kitchen,
            card_id,
            camera_padding=1.4,
            engrave=EngraveSpec(prefer_wall=True, wall_name="Aussenwand", wall_top=True),
        )
        for card_id in ("elektrisches-gerat", "endgerat-fluid")
    },
    "d07-01-001-luftungsanlage-kuche": Card(
        building.kitchen,
        "d07-01-001-luftungsanlage-kuche",
        {"hood": "d07-01-001-luftungsanlage-kuche"},
        camera_padding=1.4,
        engrave=EngraveSpec(prefer_wall=True, wall_name="Aussenwand", wall_top=True),
    ),
    "lampe": Card(building.office_lighting, "lampe", {"ghost_fixtures": True}, camera_padding=1.35, engrave=_LOWEST),
    "lichtquelle": Card(building.office_lighting, "lichtquelle", camera_padding=1.35, engrave=_LOWEST),
    "d01-05-003-bus-beleuchtung-system-knx-dali-usw": Card(
        building.office_lighting,
        "d01-05-003-bus-beleuchtung-system-knx-dali-usw",
        {"bus": "d01-05-003-bus-beleuchtung-system-knx-dali-usw"},
        camera_padding=1.35,
        engrave=_LOWEST,
    ),
    "verdunstungskuhler": Card(building.mobile_cooler, "verdunstungskuhler", camera_padding=1.3, engrave=_BACK_WALL),
    # Dach / Halle / Gelaende ------------------------------------------------
    **{
        card_id: Card(building.roof_energy, card_id, engrave=_WALL_TOP)
        for card_id in ("solargerat", "dach-abgasterminal", "i-037-photovoltaikanlage", "i-074-warmeerz-solar")
    },
    "d01-11-006-funkanlage": Card(building.roof_radio, "d01-11-006-funkanlage", camera_padding=1.3, engrave=_WALL_TOP),
    "d01-11-007-antennenanlagen": Card(building.antenna_system, "d01-11-007-antennenanlagen", camera_padding=1.3, engrave=_BACK_WALL),
    "d04-06-001-maschinelle-rauch-und-warmeabzugsanlage": Card(
        building.smoke_exhaust, "d04-06-001-maschinelle-rauch-und-warmeabzugsanlage", camera_padding=1.3, engrave=_BACK_WALL
    ),
    "d04-06-002-naturliche-rauch-und-warmeabzugsanlage": Card(
        building.smoke_exhaust,
        "d04-06-002-naturliche-rauch-und-warmeabzugsanlage",
        {"key": "d04-06-002-naturliche-rauch-und-warmeabzugsanlage", "natural": True},
        camera_padding=1.3,
        engrave=_BACK_WALL,
    ),
    **_room_cards(building.hall, ("i-003-krananlagen", "i-028-gleisanlagen")),
    **{
        key: Card(building.hall, key, {"gate": key, "gate_drive": drive}, engrave=_BACK_WALL)
        for key, drive in (("g05-07-006-schallschutztore-automatisch", True), ("g05-07-007-schallschutztore-handbetrieben", False))
    },
    **_room_cards(building.parking_garage, ("d04-02-002-co-und-dieselabgas-uberwachungsanlage",), camera_padding=1.3),
    "h09-06-001-parkieranlage": Card(
        building.parking_garage, "h09-06-001-parkieranlage", {"stacker_key": "h09-06-001-parkieranlage"}, camera_padding=1.3, engrave=_BACK_WALL
    ),
    "i-013-anpassrampen": Card(
        building.delivery_dock,
        "i-013-anpassrampen",
        camera_padding=1.3,
        camera_direction=(1.0, 0.45, 0.6),
        engrave=EngraveSpec(prefer_wall=True, wall_name="Fassade", wall_top=True),
    ),
    # Sonderraeume ------------------------------------------------------------
    **_room_cards(special.extinguishing_plant_room, (special.POWDER, special.HALON_EXTRACT, special.FIRE_MAIN), camera_padding=1.4),
    special.SPLIT_AC: Card(special.split_ac_office, special.SPLIT_AC, camera_padding=1.35, engrave=_BACK_WALL),
    special.DEHUMIDIFIER: Card(special.dehumidified_store, special.DEHUMIDIFIER, camera_padding=1.35, engrave=_BACK_WALL),
    special.COLD_ROOM: Card(special.cold_room_store, special.COLD_ROOM, camera_padding=1.35, engrave=_BACK_WALL),
    special.MEDICAL: Card(special.first_aid_room, special.MEDICAL, camera_padding=1.35, engrave=_BACK_WALL),
    **_room_cards(special.compressed_air_room, (special.AIR_DRYER, special.VACUUM), camera_padding=1.4),
    special.CLIMATE_CHAMBER: Card(special.climate_lab, special.CLIMATE_CHAMBER, camera_padding=1.4, engrave=_BACK_WALL),
    special.BREATHING_COURSE: Card(special.breathing_training, special.BREATHING_COURSE, camera_padding=1.4, engrave=_BACK_WALL),
    special.TARGET_SYSTEM: Card(special.shooting_range, special.TARGET_SYSTEM, camera_padding=1.3, engrave=_BACK_WALL),
    special.GAS_PRODUCTION: Card(special.gas_production, special.GAS_PRODUCTION, camera_padding=1.4, engrave=_BACK_WALL),
    special.FACADE_BMU: Card(special.facade_maintenance, special.FACADE_BMU, camera_padding=1.3, engrave=EngraveSpec(prefer_wall=True, wall_name="Fassade", wall_top=True)),
    # Transportanlagen -------------------------------------------------------
    transport.FUNICULAR: Card(transport.slope_railway, transport.FUNICULAR, {"kind": "funicular"}, camera_padding=1.15),
    transport.WINCH_RAILWAY: Card(transport.slope_railway, transport.WINCH_RAILWAY, {"kind": "winch"}, camera_padding=1.15),
    transport.MONORACK: Card(transport.slope_railway, transport.MONORACK, {"kind": "monorack"}, camera_padding=1.15),
    transport.TUNNEL_RAILWAY: Card(transport.tunnel_railway, transport.TUNNEL_RAILWAY, camera_padding=1.2),
    transport.STAIR_LIFT: Card(transport.stair_lift, transport.STAIR_LIFT, camera_padding=1.25, engrave=_BACK_WALL),
    transport.ESCALATOR: Card(transport.escalator, transport.ESCALATOR, camera_padding=1.5, camera_focus=(transport.ESCALATOR,), engrave=_BACK_WALL),
    transport.MOVING_WALKWAY: Card(transport.moving_walkway, transport.MOVING_WALKWAY, camera_padding=1.3),
    transport.MANUAL_CRANE: Card(transport.manual_crane, transport.MANUAL_CRANE, camera_padding=1.25, camera_direction=(1.0, 1.0, 1.25), engrave=_BACK_WALL),
    transport.VEHICLE_LIFT: Card(transport.vehicle_lift, transport.VEHICLE_LIFT, camera_padding=1.2, camera_direction=(1.0, 1.0, 0.8), engrave=_BACK_WALL),
    transport.AERIAL_ROPEWAY: Card(transport.cableway, transport.AERIAL_ROPEWAY, {"kind": "aerial"}, camera_padding=1.1),
    transport.MATERIAL_ROPEWAY: Card(transport.cableway, transport.MATERIAL_ROPEWAY, {"kind": "material"}, camera_padding=1.1),
    transport.TARGET_ROPEWAY: Card(transport.cableway, transport.TARGET_ROPEWAY, {"kind": "target"}, camera_padding=1.15),
    # Umgebung ---------------------------------------------------------------
    **{
        key: Card(build, key, camera_padding=padding, camera_focus=(key,))
        for build, key, padding in (
            (site.site_water, site.WELL, 2.2),
            (site.site_water, site.RAINWATER, 1.9),
            (site.site_water, site.SPRING_CHAMBER, 1.9),
            (site.site_water, site.RESERVOIR, 1.6),
            (site.site_wastewater, site.CESSPIT, 2.2),
            (site.site_wastewater, site.WASTEWATER_PIT, 2.0),
            (site.site_wastewater, site.TREATMENT_SMALL, 1.5),
            (site.site_energy, site.HEAT_PLANT, 1.4),
            (site.site_energy, site.GROUND_PROBES, 1.4),
            (site.site_access, site.BARRIER, 2.0),
            (site.site_access, site.GATE_AUTOMATIC, 1.9),
            (site.site_access, site.GATE_MANUAL, 2.4),
            (site.site_access, site.DOOR_AUTOMATIC, 3.2),
        )
    },
    site.TREATMENT_LARGE: Card(site.treatment_plant, site.TREATMENT_LARGE, camera_padding=1.1),
    site.TOILETS: Card(site.toilet_block, site.TOILETS, camera_padding=1.3, camera_direction=(0.35, 1.0, 0.75), engrave=_BACK_WALL),
    # Absturzsicherung -------------------------------------------------------
    **{
        key: Card(safety.fall_protection, key, {"setting": setting}, camera_padding=1.15)
        for setting, keys in safety.SETTINGS.items()
        for key in keys[:2]
    },
    **{
        keys[2]: Card(safety.fall_protection, keys[2], {"setting": setting}, camera_padding=padding, camera_focus=(keys[2],))
        for setting, keys in safety.SETTINGS.items()
        for padding in [{"facade": 1.7, "flat_roof": 1.9, "pitched_roof": 1.9, "interior": 5.0, "surroundings": 3.5}[setting]]
    },
    safety.SETTINGS["flat_roof"][2]: Card(
        safety.fall_protection,
        safety.SETTINGS["flat_roof"][2],
        {"setting": "flat_roof", "lifeline": False},
        camera_padding=1.9,
        camera_focus=(safety.SETTINGS["flat_roof"][2],),
    ),
    safety.PSA: Card(safety.fall_protection, safety.PSA, {"setting": "flat_roof"}, camera_padding=5.0, camera_focus=(safety.PSA,)),
    # Schutzbau --------------------------------------------------------------
    **{
        key: Card(access.protected_structure, key, camera_padding=1.3, engrave=_BACK_WALL)
        for key in (access.ARMOURED_AUTOMATIC, access.ARMOURED_SWING_GATE, access.ARMOURED_MANUAL, access.LOCK_MANUAL, access.KEY_SAFE)
    },
    access.NEMP_SHIELD: Card(access.protected_structure, access.NEMP_SHIELD, {"shield": True}, camera_padding=1.3, engrave=_BACK_WALL),
    # Brandabschnitt ---------------------------------------------------------
    **_room_cards(building.fire_compartment, ("feuer-diamant",)),
    "feuerwehr-objekt": Card(building.fire_compartment, "feuerwehr-objekt", {"fire_object": True}, engrave=_BACK_WALL),
    **{
        card_id: Card(building.fire_brigade_site, card_id, {"element": card_id}, camera_padding=1.3, engrave=_LOWEST)
        for card_id in ("freihalteflache-feuerwehr", "sammelplatz", "feuerwehr-zugang")
    },
    "i-067-wasserkraftwerke": Card(building.site_power, "i-067-wasserkraftwerke", {"plant": "hydro"}, camera_padding=1.3, engrave=_LOWEST),
    "i-068-windkraftwerke": Card(building.site_power, "i-068-windkraftwerke", camera_padding=1.3, engrave=_LOWEST),
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
    # Raumstruktur -----------------------------------------------------------
    **{
        card_id: Card(spatial.spatial_hierarchy, key, camera_padding=1.4, engrave=_LOWEST)
        for card_id, key in (
            ("projekt", spatial.PROJECT),
            ("planungsperimeter-projektperimeter", spatial.SITE),
            ("gebaude-bauwerke", spatial.BUILDING),
            ("geschoss-stockwerk", spatial.STOREY),
        )
    },
    # Klassifizierung und Gruppierung ----------------------------------------
    "ebkp-name-der-klassifizierung": Card(abstract.ebkp, abstract.EBKP_GROUPS, camera_padding=1.3, engrave=_LOWEST),
    "ebkp-werte-fur-klassifizierung": Card(abstract.ebkp, "ebkp-e", camera_padding=1.3, engrave=_LOWEST),
    "sia416-name-der-klassifizierung": Card(abstract.sia416, abstract.SIA_AREAS, camera_padding=1.3, engrave=_LOWEST),
    "sia416-werte-fur-klassifizierung": Card(abstract.sia416, "sia-hnf", camera_padding=1.3, engrave=_LOWEST),
    "sicherheitszone-schutzzonen": Card(abstract.protection_zone, "schutzzone", camera_padding=1.3, engrave=_LOWEST),
    "etappe": Card(abstract.stages, "etappe-1", camera_padding=1.3, engrave=_LOWEST),
    "modelleinfugepunkt-disziplin": Card(abstract.discipline_insertion_point, abstract.DISCIPLINES, camera_padding=1.3),
}
