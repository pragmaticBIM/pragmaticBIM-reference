"""Plant-room vignettes: heating, chiller, water treatment, air handling, main switchboard.

Every room is the open-corner room of the Reference MEP cards (back wall y = 0,
side wall x = 0). Devices are tagged with the data-schema element id and, where
they belong to one, the id of the building system they form.
"""

from __future__ import annotations

from generators.mep_parts import (
    add_corner_room,
    box_solid,
    duct_solid,
    pipe_solid,
    vertical_cylinder_solid,
)

from dataschema.scene import Scene

ROOM_WIDTH = 6.5
ROOM_DEPTH = 4.5
WALL_HEIGHT = 3.0

_HEADER_Y = 0.22
_FLOW_Z = 1.95
_RETURN_Z = 2.2
_PIPE_R = 0.05


def corner_room(name: str, width: float = ROOM_WIDTH, depth: float = ROOM_DEPTH, height: float = WALL_HEIGHT) -> Scene:
    scene = Scene.new(name, storey_name="UG")
    add_corner_room(
        scene.ifc_file,
        body_context=scene.body_context,
        storey=scene.storey,
        width=width,
        depth=depth,
        wall_height=height,
    )
    return scene


def horizontal_cylinder(f, x0: float, x1: float, y: float, z: float, r: float, segments: int = 16):
    return pipe_solid(f, (x0, y, z), (x1, y, z), r, segments=segments)


# ---------------------------------------------------------------------------
# Heizraum
# ---------------------------------------------------------------------------

def heating_room(fuel: str = "gas") -> Scene:
    """Boiler + burner, header with pump groups, meters, controls, CHP, hydronic accessories.

    ``fuel``: ``gas`` (oil/gas boiler), ``log``, ``pellet`` or ``chip``.
    """
    s = corner_room("Heizraum")
    f = s.ifc_file
    gen = ("i-029-heiz-warmeerzeugung", "heat-gen")

    # Heat generator against the back wall, burner on its front.
    if fuel == "log":
        s.add("IfcBoiler", "WE-01", [box_solid(f, 0.35, 0.1, 0.0, 1.45, 1.1, 1.6)], keys=gen, predefined_type="WATER")
        s.add("IfcBuildingElementProxy", "Fuelltuer", [box_solid(f, 0.6, 1.1, 0.9, 1.2, 1.16, 1.4)], keys=gen, object_type="Fuelltuer")
        for i in range(4):
            s.add(
                "IfcBuildingElementProxy",
                f"Holzstapel-{i + 1}",
                [box_solid(f, 0.3 + i * 0.45, 3.0, 0.0, 0.7 + i * 0.45, 4.3, 1.1)],
                keys=("heat-gen",),
                object_type="Stueckholz",
            )
    else:
        s.add("IfcBoiler", "WE-01", [box_solid(f, 0.4, 0.1, 0.0, 1.4, 0.95, 1.5)], keys=gen, predefined_type="WATER")
        s.add(
            "IfcBurner",
            "BR-01",
            [
                box_solid(f, 0.7, 0.95, 0.65, 1.1, 1.25, 1.05),
                pipe_solid(f, (0.9, 1.25, 0.85), (0.9, 1.4, 0.85), 0.12, segments=12),
            ],
            keys=("brenner", *gen),
        )
    s.add("IfcChimney", "Abgasrohr", [vertical_cylinder_solid(f, 0.9, 0.5, 1.5, 0.12, WALL_HEIGHT - 1.5, segments=10)])

    if fuel in ("pellet", "chip"):
        store_h = 2.2 if fuel == "pellet" else 2.6
        s.add(
            "IfcTank",
            "Brennstofflager",
            [box_solid(f, 0.2, 2.6, 0.0, 2.6, 4.4, store_h)],
            keys=("heat-gen",),
            predefined_type="STORAGE",
        )
        s.add(
            "IfcBuildingElementProxy",
            "Foerderschnecke",
            [duct_solid(f, (0.9, 2.6, 0.35), (0.9, 0.95, 0.35), 0.22, 0.22)],
            keys=("heat-gen",),
            object_type="Foerderschnecke",
        )

    # Header pair along the back wall.
    for name, z in (("Verteiler-VL", _FLOW_Z), ("Verteiler-RL", _RETURN_Z)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (1.7, _HEADER_Y, z), (4.25, _HEADER_Y, z), _PIPE_R)])
    s.add("IfcPipeSegment", "WE-VL", [pipe_solid(f, (1.4, _HEADER_Y, 1.2), (1.6, _HEADER_Y, 1.2), _PIPE_R)])
    s.add("IfcPipeSegment", "WE-Steig", [pipe_solid(f, (1.65, _HEADER_Y, 1.2), (1.65, _HEADER_Y, _FLOW_Z - 0.05), _PIPE_R)])

    # Fittings: elbows at the header ends, tees at the circuit branches.
    fittings = [
        box_solid(f, 1.57, _HEADER_Y - 0.08, 1.12, 1.73, _HEADER_Y + 0.08, 1.28),
        box_solid(f, 1.57, _HEADER_Y - 0.08, _FLOW_Z - 0.08, 1.73, _HEADER_Y + 0.08, _FLOW_Z + 0.08),
        box_solid(f, 4.2, _HEADER_Y - 0.08, _FLOW_Z - 0.08, 4.36, _HEADER_Y + 0.08, _FLOW_Z + 0.08),
        box_solid(f, 4.2, _HEADER_Y - 0.08, _RETURN_Z - 0.08, 4.36, _HEADER_Y + 0.08, _RETURN_Z + 0.08),
    ]
    for x in (2.3, 3.0, 3.7):
        fittings.append(box_solid(f, x - 0.08, _HEADER_Y - 0.08, _FLOW_Z - 0.08, x + 0.08, _HEADER_Y + 0.08, _FLOW_Z + 0.08))
    s.add("IfcPipeFitting", "Formteile", fittings, keys=("rohrformteil",), predefined_type="BEND")
    s.add("IfcPipeSegment", "Rueckfuehrung", [pipe_solid(f, (4.28, _HEADER_Y, _RETURN_Z), (4.28, _HEADER_Y, _FLOW_Z), _PIPE_R)])

    # Three pump groups: pump on the riser, motor in front, coupling between.
    for i, x in enumerate((2.3, 3.0, 3.7)):
        s.add("IfcPipeSegment", f"Heizgruppe-{i + 1}", [pipe_solid(f, (x, _HEADER_Y, 0.0), (x, _HEADER_Y, _FLOW_Z - 0.08), _PIPE_R)])
        s.add("IfcPump", f"P-0{i + 1}", [vertical_cylinder_solid(f, x, _HEADER_Y, 1.0, 0.13, 0.3, segments=12)], keys=("i-030-heiz-warmeverteilung",))
        s.add(
            "IfcMotorConnection",
            f"Kupplung-0{i + 1}",
            [pipe_solid(f, (x, _HEADER_Y + 0.12, 1.15), (x, _HEADER_Y + 0.32, 1.15), 0.09, segments=12)],
            keys=("motoranschluss",),
        )
        s.add(
            "IfcElectricMotor",
            f"M-0{i + 1}",
            [box_solid(f, x - 0.12, _HEADER_Y + 0.32, 1.03, x + 0.12, _HEADER_Y + 0.6, 1.27)],
            keys=("elektromotor",),
        )
        s.add(
            "IfcFlowInstrument",
            f"TI-0{i + 1}",
            [
                pipe_solid(f, (x, _HEADER_Y, 1.62), (x, _HEADER_Y + 0.14, 1.62), 0.025, segments=8),
                pipe_solid(f, (x, _HEADER_Y + 0.14, 1.62), (x, _HEADER_Y + 0.2, 1.62), 0.11, segments=16),
            ],
            keys=("messgerat-prozess", "i-027-gebaudeleitsystem-gebaudeautomation"),
            predefined_type="THERMOMETER",
        )
        s.add(
            "IfcActuator",
            f"MV-0{i + 1}",
            [box_solid(f, x - 0.07, _HEADER_Y + 0.05, 0.55, x + 0.07, _HEADER_Y + 0.25, 0.72)],
            keys=("i-027-gebaudeleitsystem-gebaudeautomation",),
        )
    s.add(
        "IfcFlowMeter",
        "WMZ-01",
        [box_solid(f, 3.6, _HEADER_Y - 0.08, 0.25, 3.8, _HEADER_Y + 0.12, 0.42)],
        keys=("durchflussmesser", "i-021-energiemanagement"),
        predefined_type="ENERGYMETER",
    )
    s.add(
        "IfcPipeFitting",
        "Schmutzfaenger",
        [pipe_solid(f, (3.0, _HEADER_Y - 0.08, 0.3), (3.0, _HEADER_Y + 0.32, 0.3), 0.1, segments=12),
         box_solid(f, 2.9, _HEADER_Y - 0.08, 0.12, 3.1, _HEADER_Y + 0.08, 0.48)],
        keys=("rohrzubehor",),
        object_type="Rohrzubehoer",
    )

    # Hydronic accessories on the right of the back wall (kept below the brand corner).
    s.add("IfcFilter", "Schlammabscheider", [vertical_cylinder_solid(f, 4.05, 0.35, 0.15, 0.13, 0.65, segments=14)], keys=("i-076-warmevert-magflussfi",), predefined_type="WATERFILTER")
    s.add(
        "IfcFilter",
        "Entsalzung",
        [vertical_cylinder_solid(f, x, 0.32, 0.0, 0.11, 1.15, segments=14) for x in (4.45, 4.75)],
        keys=("i-075-warmevert-entsalzung",),
        object_type="Entsalzungspatrone",
    )
    s.add("IfcTank", "Ausdehnungsgefaess", [vertical_cylinder_solid(f, 5.35, 0.45, 0.0, 0.35, 1.05, segments=18)], keys=("i-078-warmevert-expansion",), predefined_type="EXPANSION")
    s.add("IfcBuildingElementProxy", "Entgasung", [box_solid(f, 5.85, 0.0, 0.3, 6.35, 0.4, 1.1)], keys=("i-077-warmevert-entgasung",), object_type="Vakuumentgasung")
    for name, x0, x1 in (("Anschluss-MAG", 4.28, 5.35), ("Anschluss-Entgasung", 5.35, 6.1)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (x0, _HEADER_Y, 1.25), (x1, _HEADER_Y, 1.25), 0.03)])

    # Controls and metering on the side wall.
    s.add("IfcController", "Regler-Heizung", [box_solid(f, 0.0, 1.5, 1.0, 0.3, 2.1, 1.9)], keys=("regler", "i-027-gebaudeleitsystem-gebaudeautomation"))
    s.add("IfcFlowMeter", "Elektrozaehler", [box_solid(f, 0.0, 2.25, 1.25, 0.18, 2.55, 1.7)], keys=("i-021-energiemanagement",), predefined_type="ENERGYMETER")
    s.add("IfcController", "Energiemanager", [box_solid(f, 0.0, 2.65, 1.25, 0.15, 2.9, 1.6)], keys=("i-021-energiemanagement",))

    # Combined heat and power unit: engine coupled to a generator on a plinth.
    if fuel in ("gas",):
        s.add("IfcBuildingElementProxy", "Sockel-BHKW", [box_solid(f, 3.4, 2.5, 0.0, 6.0, 3.8, 0.12)], object_type="Sockel")
        s.add(
            "IfcEngine",
            "BHKW-Motor",
            [box_solid(f, 3.55, 2.65, 0.12, 4.9, 3.65, 1.25), vertical_cylinder_solid(f, 4.2, 3.15, 1.25, 0.09, WALL_HEIGHT - 1.25, segments=8)],
            keys=("verbrennungsmotor",),
        )
        s.add("IfcElectricGenerator", "BHKW-Generator", [box_solid(f, 4.95, 2.75, 0.12, 5.85, 3.55, 1.05)])
    return s


# ---------------------------------------------------------------------------
# Kaeltezentrale
# ---------------------------------------------------------------------------

def chiller_room() -> Scene:
    """Opened water chiller (evaporator, condenser, compressor) and a brine heat pump with buffer."""
    s = corner_room("Kaeltezentrale")
    f = s.ifc_file

    # Chiller frame along the back wall: evaporator below, condenser above.
    s.add("IfcBuildingElementProxy", "Rahmen-KM", [box_solid(f, 0.4, 0.15, 0.0, 3.6, 1.15, 0.12)], object_type="Rahmen")
    s.add("IfcEvaporator", "Verdampfer", [horizontal_cylinder(f, 0.6, 3.4, 0.65, 0.5, 0.32)], keys=("verdampfer",), predefined_type="FLOODEDSHELLANDTUBE")
    s.add("IfcCondenser", "Verflüssiger", [horizontal_cylinder(f, 0.6, 3.4, 0.65, 1.2, 0.28)], keys=("kondensator",), predefined_type="WATERCOOLEDSHELLTUBE")
    s.add(
        "IfcCompressor",
        "Verdichter",
        [vertical_cylinder_solid(f, 1.6, 0.65, 1.5, 0.28, 0.55, segments=16), box_solid(f, 2.1, 0.4, 1.5, 2.8, 0.9, 1.85)],
    )
    s.add("IfcController", "Schaltschrank-KM", [box_solid(f, 3.75, 0.0, 0.0, 4.35, 0.5, 2.0)])
    for name, z in (("KW-VL", 0.5), ("KW-RL", 1.2)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (0.0, 0.65, z), (0.6, 0.65, z), 0.08)])

    # Brine/water heat pump with buffer tank (front left).
    s.add(
        "IfcEnergyConversionDevice",
        "WP-01",
        [box_solid(f, 0.3, 2.4, 0.0, 1.3, 3.2, 1.4)],
        keys=("energieumwandlungsgerat", "i-073-warmeerz-warmepumpen"),
        object_type="Waermepumpe",
    )
    s.add("IfcTank", "Pufferspeicher", [vertical_cylinder_solid(f, 2.1, 2.8, 0.0, 0.45, 2.0, segments=18)], keys=("i-073-warmeerz-warmepumpen",), predefined_type="STORAGE")
    for name, z in (("WP-VL", 1.1), ("WP-RL", 0.4)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (1.3, 2.8, z), (1.65, 2.8, z), 0.05)])
    s.add("IfcPipeSegment", "Sole", [pipe_solid(f, (0.0, 2.6, 0.3), (0.3, 2.6, 0.3), 0.05)])
    return s


# ---------------------------------------------------------------------------
# Wasserzentrale
# ---------------------------------------------------------------------------

def water_room() -> Scene:
    """Water treatment line: softener, desalination, reverse osmosis, UV, booster, chlorine dosing."""
    s = corner_room("Wasserzentrale")
    f = s.ifc_file

    s.add("IfcPipeSegment", "Trinkwasser", [pipe_solid(f, (0.0, 0.25, 2.1), (6.2, 0.25, 2.1), 0.05)])

    # Softener: two resin columns and a brine tank.
    s.add(
        "IfcFilter",
        "Enthaertung",
        [vertical_cylinder_solid(f, x, 0.45, 0.0, 0.2, 1.5, segments=16) for x in (0.45, 0.95)]
        + [vertical_cylinder_solid(f, 1.55, 0.45, 0.0, 0.28, 0.9, segments=16)],
        keys=("i-022-enthartungsanlage",),
        object_type="Enthaertungsanlage",
    )
    # Ion-exchange desalination: two taller columns.
    s.add(
        "IfcFilter",
        "Entsalzung",
        [vertical_cylinder_solid(f, x, 0.45, 0.0, 0.24, 1.8, segments=16) for x in (2.2, 2.75)],
        keys=("i-023-entsalzungsanlage",),
        object_type="Entsalzungsanlage",
    )
    # Reverse-osmosis rack: horizontal membrane tubes in a frame.
    rack = [box_solid(f, 3.3, 0.1, 0.0, 3.36, 0.8, 1.7), box_solid(f, 4.9, 0.1, 0.0, 4.96, 0.8, 1.7)]
    rack += [horizontal_cylinder(f, 3.3, 4.96, 0.45, z, 0.1, segments=12) for z in (0.5, 0.85, 1.2, 1.55)]
    s.add("IfcFilter", "Osmose", rack, keys=("i-036-osmoseanlage",), object_type="Umkehrosmose")
    # UV reactor on the outgoing line (kept low, right of the rack).
    s.add("IfcFilter", "UV-Reaktor", [horizontal_cylinder(f, 5.2, 6.2, 0.35, 1.1, 0.12, segments=14)], keys=("i-065-uv-anlage",), object_type="UV-Desinfektion")
    s.add("IfcPipeSegment", "UV-Anschluss", [pipe_solid(f, (5.3, 0.35, 1.1), (5.3, 0.35, 2.05), 0.04)])

    # Booster set on the side wall: three vertical pumps on a base + pressure vessel.
    s.add("IfcBuildingElementProxy", "Grundrahmen-DEA", [box_solid(f, 0.15, 1.6, 0.0, 0.85, 3.0, 0.1)], keys=("i-018-druckerhohungsanlage",), object_type="Grundrahmen")
    s.add(
        "IfcPump",
        "DEA-Pumpen",
        [vertical_cylinder_solid(f, 0.5, y, 0.1, 0.12, 0.9, segments=12) for y in (1.85, 2.3, 2.75)],
        keys=("i-018-druckerhohungsanlage",),
        predefined_type="VERTICALINLINE",
    )
    s.add("IfcTank", "Druckbehaelter", [vertical_cylinder_solid(f, 0.5, 3.5, 0.0, 0.28, 1.0, segments=16)], keys=("i-018-druckerhohungsanlage",), predefined_type="PRESSUREVESSEL")
    s.add("IfcPipeSegment", "DEA-Sammler", [pipe_solid(f, (0.5, 1.7, 1.15), (0.5, 3.5, 1.15), 0.05)])

    # Chlorine dosing: dosing tank, wall pump, injection line.
    s.add(
        "IfcTank",
        "Chlor-Dosierbehaelter",
        [vertical_cylinder_solid(f, 2.0, 3.6, 0.0, 0.25, 0.8, segments=16)],
        keys=("i-016-chlordosierungsanlage",),
        predefined_type="STORAGE",
    )
    s.add("IfcPump", "Dosierpumpe", [box_solid(f, 1.85, 3.25, 0.8, 2.15, 3.45, 1.0)], keys=("i-016-chlordosierungsanlage",))
    return s


# ---------------------------------------------------------------------------
# Lueftungszentrale
# ---------------------------------------------------------------------------

def air_handling_room() -> Scene:
    """Air handling unit opened into sections; ducts with elbows, silencers and flexible connectors."""
    s = corner_room("Lueftungszentrale")
    f = s.ifc_file
    y0, y1, z1 = 0.25, 1.35, 1.6

    # Air flows from the intake (+X, near the outdoor-air wall duct) to the outlet at the side wall.
    sections = (
        ("IfcBuildingElementProxy", "Ausblaskammer", 0.3, 0.95, None, {"object_type": "Ausblaskammer"}),
        ("IfcFan", "Ventilator", 0.95, 1.95, None, {"predefined_type": "CENTRIFUGALFORWARDCURVED"}),
        ("IfcCoil", "Kuehler", 1.95, 2.4, "register-heiz-kuhlregister", {"predefined_type": "WATERCOOLINGCOIL"}),
        ("IfcCoil", "Erhitzer", 2.4, 2.85, "register-heiz-kuhlregister", {"predefined_type": "HYDRONICCOIL"}),
        ("IfcFilter", "Filter", 2.85, 3.4, "filter", {"predefined_type": "AIRPARTICLEFILTER"}),
        ("IfcBuildingElementProxy", "Ansaugkammer", 3.4, 4.1, None, {"object_type": "Ansaugkammer"}),
    )
    for ifc_class, name, xa, xb, key, extra in sections:
        s.add(ifc_class, name, [box_solid(f, xa, y0, 0.0, xb, y1, z1)], keys=(key,) if key else (), **extra)

    ym = (y0 + y1) * 0.5

    def riser(prefix: str, x: float, z_bend: float, width: float, silencer: bool) -> None:
        hw, hd = width * 0.5, 0.25
        s.add("IfcDuctFitting", f"Segeltuchstutzen-{prefix}", [box_solid(f, x - hw, ym - hd, z1, x + hw, ym + hd, z1 + 0.14)], keys=("luftkanalzubehor",), object_type="Flexibler Stutzen")
        z = z1 + 0.14
        if silencer:
            s.add("IfcDuctSilencer", f"Schalldaempfer-{prefix}", [box_solid(f, x - hw - 0.08, ym - hd - 0.08, z, x + hw + 0.08, ym + hd + 0.08, z_bend)], keys=("schalldampfer",), predefined_type="RECTANGULAR")
        else:
            s.add("IfcDuctSegment", f"Steigkanal-{prefix}", [duct_solid(f, (x, ym, z), (x, ym, z_bend), width, 0.5)])
        s.add("IfcDuctFitting", f"Bogen-{prefix}", [box_solid(f, x - hw, ym - hd, z_bend, x + hw, ym + hd, z_bend + 0.45)], keys=("luftkanalformteil",), predefined_type="BEND")
        s.add("IfcDuctSegment", f"Wandkanal-{prefix}", [duct_solid(f, (x, ym - hd, z_bend + 0.22), (x, 0.0, z_bend + 0.22), width, 0.4)])

    riser("ZU", 0.62, 2.35, 0.55, silencer=True)
    riser("AUL", 3.75, 1.85, 0.55, silencer=False)
    return s


# ---------------------------------------------------------------------------
# Hauptverteilung
# ---------------------------------------------------------------------------

def _open_cabinet(s: Scene, name: str, x0: float, width: float, height: float = 2.0, depth: float = 0.5, keys=()) -> None:
    """Switchboard field with the front door removed: back plate, sides, top."""
    f = s.ifc_file
    x1 = x0 + width
    solids = [
        box_solid(f, x0, 0.0, 0.0, x1, 0.05, height),
        box_solid(f, x0, 0.0, 0.0, x0 + 0.04, depth, height),
        box_solid(f, x1 - 0.04, 0.0, 0.0, x1, depth, height),
        box_solid(f, x0, 0.0, height - 0.06, x1, depth, height),
        box_solid(f, x0, 0.0, 0.0, x1, depth, 0.1),
    ]
    s.add("IfcElectricDistributionBoard", name, solids, keys=keys, predefined_type="SWITCHBOARD")


def switchboard_room() -> Scene:
    """Main LV switchboard opened (breakers + trip units), MV switchgear, compensation, metering, CO2."""
    s = corner_room("Hauptverteilung")
    f = s.ifc_file

    # Cable tray loop along the walls with bends; cables drop into the open fields.
    tray_z = 2.45
    s.add("IfcCableCarrierSegment", "Trasse-Rueckwand", [duct_solid(f, (0.45, 0.6, tray_z), (4.4, 0.6, tray_z), 0.4, 0.08)])
    s.add("IfcCableCarrierSegment", "Trasse-Seitenwand", [duct_solid(f, (0.4, 0.95, tray_z), (0.4, 3.6, tray_z), 0.4, 0.08)])
    s.add(
        "IfcCableCarrierFitting",
        "Trassenbogen",
        [box_solid(f, 0.2, 0.4, tray_z - 0.04, 0.6, 0.95, tray_z + 0.04), box_solid(f, 4.4, 0.4, tray_z - 0.04, 4.8, 0.8, tray_z + 0.04)],
        keys=("kabeltrassen-formteil",),
        predefined_type="BEND",
    )

    # LV main distribution: three open fields with breaker rows.
    for i, x0 in enumerate((0.4, 1.15, 1.9)):
        _open_cabinet(s, f"HV-Feld-{i + 1}", x0, 0.7)
        breakers, trips = [], []
        for row, z in enumerate((0.45, 0.85, 1.25, 1.6)):
            for col in range(3):
                bx = x0 + 0.1 + col * 0.18
                breakers.append(box_solid(f, bx, 0.05, z, bx + 0.14, 0.3, z + 0.28))
                trips.append(box_solid(f, bx + 0.02, 0.3, z + 0.08, bx + 0.12, 0.36, z + 0.2))
        s.add("IfcProtectiveDevice", f"Leistungsschalter-{i + 1}", breakers, keys=("schutzeinrichtung",), predefined_type="CIRCUITBREAKER")
        s.add("IfcProtectiveDeviceTrippingUnit", f"Ausloeser-{i + 1}", trips, keys=("ausloseeinheit",), predefined_type="ELECTRONIC")
        xc = x0 + 0.35
        s.add(
            "IfcCableSegment",
            f"Kabel-{i + 1}",
            [pipe_solid(f, (xc + dx, 0.3, 2.0), (xc + dx, 0.6, tray_z - 0.04), 0.025, segments=6) for dx in (-0.12, 0.0, 0.12)]
            + [pipe_solid(f, (xc + dx, 0.3, 1.9), (xc + dx, 0.3, 2.0), 0.025, segments=6) for dx in (-0.12, 0.0, 0.12)],
            keys=("kabel",),
            predefined_type="CABLESEGMENT",
            thin=True,
        )
        s.add(
            "IfcCableFitting",
            f"Kabelverschraubung-{i + 1}",
            [vertical_cylinder_solid(f, xc + dx, 0.3, 1.86, 0.045, 0.08, segments=8) for dx in (-0.12, 0.0, 0.12)],
            keys=("kabel-formteil",),
            predefined_type="ENTRY",
        )

    # Compensation cabinet and feed-in meter cabinet on the back wall.
    s.add("IfcElectricFlowStorageDevice", "Kompensation", [box_solid(f, 2.75, 0.0, 0.0, 3.55, 0.6, 2.0)], keys=("i-015-blindstromkompensation",), predefined_type="CAPACITORBANK")
    s.add("IfcFlowMeter", "Einspeisezaehler", [box_solid(f, 3.75, 0.0, 0.8, 4.35, 0.3, 1.7)], keys=("i-020-einspeisezahler",), predefined_type="ENERGYMETER")

    # MV switchgear along the side wall.
    s.add(
        "IfcSwitchingDevice",
        "MS-Schaltanlage",
        [box_solid(f, 0.0, y0, 0.0, 0.9, y0 + 0.55, 2.1) for y0 in (1.3, 1.9, 2.5)],
        keys=("i-032-hs-schaltanlage",),
        predefined_type="SWITCHDISCONNECTOR",
    )

    # CO2 extinguishing: cylinder bank in the front corner, pipe with ceiling nozzles.
    s.add(
        "IfcFireSuppressionTerminal",
        "CO2-Batterie",
        [vertical_cylinder_solid(f, 5.4 + (i % 3) * 0.32, 3.6 + (i // 3) * 0.32, 0.0, 0.13, 1.5, segments=12) for i in range(6)],
        keys=("i-017-co2-loschanlage",),
        object_type="CO2-Flaschenbatterie",
    )
    s.add("IfcPipeSegment", "CO2-Steig", [pipe_solid(f, (5.7, 3.75, 1.5), (5.7, 3.75, 2.75), 0.03)])
    s.add("IfcPipeSegment", "CO2-Verteilung", [pipe_solid(f, (5.7, 3.75, 2.75), (2.0, 3.75, 2.75), 0.03)])
    s.add(
        "IfcFireSuppressionTerminal",
        "CO2-Duesen",
        [vertical_cylinder_solid(f, x, 3.75, 2.55, 0.05, 0.2, segments=10) for x in (2.5, 3.7, 4.9)],
        keys=("i-017-co2-loschanlage",),
        predefined_type="SPRINKLER",
    )
    return s
