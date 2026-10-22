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

from dataschema.geometry import frustum, prism
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


def polyline_solids(f, points, r: float, segments: int = 6):
    return [pipe_solid(f, a, b, r, segments=segments) for a, b in zip(points, points[1:])]


def bend_solid(f, start, d_in, d_out, radius: float, sweep: float, r: float):
    """Pipe bend (torus section) from ``start`` heading ``d_in``, turning ``sweep`` degrees
    towards ``d_out``; ``d_in`` and ``d_out`` are perpendicular unit vectors."""
    centre = [float(s + radius * o) for s, o in zip(start, d_out)]
    profile = f.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Position=f.create_entity("IfcAxis2Placement2D", Location=f.create_entity("IfcCartesianPoint", (float(radius), 0.0))),
        Radius=float(r),
    )
    placement = f.create_entity(
        "IfcAxis2Placement3D",
        Location=f.create_entity("IfcCartesianPoint", centre),
        Axis=f.create_entity("IfcDirection", tuple(-float(d) for d in d_in)),
        RefDirection=f.create_entity("IfcDirection", tuple(-float(o) for o in d_out)),
    )
    axis = f.create_entity(
        "IfcAxis1Placement",
        Location=f.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0)),
        Axis=f.create_entity("IfcDirection", (0.0, 1.0, 0.0)),
    )
    return f.create_entity("IfcRevolvedAreaSolid", SweptArea=profile, Position=placement, Axis=axis, Angle=float(sweep))


# ---------------------------------------------------------------------------
# Heizraum
# ---------------------------------------------------------------------------

HEAT_SAFETY = "d05-02-008-regel-und-sicherheitsorgan"
HEAT_FLUE_FILTER = "d05-02-009-rauchgasreinigung"
HEAT_SCRUBBER = "d05-02-010-nassabscheider-heizung"
HEAT_FLUE_MEASUREMENT = "d05-02-012-lrv-abgasmessung"
HEAT_ELECTRIC_STORAGE = "d05-02-016-elektrospeicherheizung-zentral"
HEAT_CHIP_STORE = "d05-02-021-holzschnitzellager"
HEAT_PELLET_STORE = "d05-02-022-pelettlager"
HEAT_SUBDISTRIBUTION = "d05-04-006-warmeunterverteilung"


def heating_room(fuel: str = "gas", gas_detection: bool = False, extra: str | None = None) -> Scene:
    """Boiler + burner, header with pump groups, meters, controls, CHP, hydronic accessories.

    ``fuel``: ``gas`` (oil/gas boiler), ``log``, ``pellet`` or ``chip``.
    ``gas_detection`` adds the gas detection system (key ``gasmeldeanlage``).
    ``extra`` adds one heating component tagged with that key (one of the ``HEAT_*`` ids);
    components that need the front of the room replace the CHP unit.
    """
    s = corner_room("Heizraum")
    f = s.ifc_file
    gen = ("i-029-heiz-warmeerzeugung", "heat-gen")
    flue_top = 2.55 if extra == HEAT_SCRUBBER else WALL_HEIGHT

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
        s.add("IfcPipeSegment", "Brennstoffleitung", [pipe_solid(f, (0.7, 1.1, 0.75), (0.0, 1.1, 0.75), 0.03)], serves=("brenner",))
    s.add("IfcChimney", "Abgasrohr", [vertical_cylinder_solid(f, 0.9, 0.5, 1.5, 0.12, flue_top - 1.5, segments=10)])

    if fuel in ("pellet", "chip"):
        store_h = 2.2 if fuel == "pellet" else 2.6
        store = ("heat-gen", *((extra,) if extra in (HEAT_CHIP_STORE, HEAT_PELLET_STORE) else ()))
        s.add(
            "IfcTank",
            "Brennstofflager",
            [box_solid(f, 0.2, 2.6, 0.0, 2.6, 4.4, store_h)],
            keys=store,
            predefined_type="STORAGE",
        )
        s.add(
            "IfcBuildingElementProxy",
            "Foerderschnecke",
            [duct_solid(f, (0.9, 2.6, 0.35), (0.9, 0.95, 0.35), 0.22, 0.22)],
            keys=store,
            object_type="Foerderschnecke",
        )
        if extra == HEAT_PELLET_STORE:
            s.add(
                "IfcPipeSegment",
                "Einblasstutzen",
                [pipe_solid(f, (-0.2, y, store_h - 0.3), (0.35, y, store_h - 0.3), 0.06, segments=12) for y in (3.1, 3.9)],
                keys=store,
                predefined_type="RIGIDSEGMENT",
            )
        elif extra == HEAT_CHIP_STORE:
            s.add(
                "IfcBuildingElementProxy",
                "Raumaustragung",
                [vertical_cylinder_solid(f, 1.4, 3.5, 0.0, 0.8, 0.12, segments=24)],
                keys=store,
                object_type="Federkernruehrwerk",
            )

    # Header pair along the back wall.
    # Fittings are drawn slightly fatter than the pipe so they read as separate parts.
    fit_r, elbow_r, riser_x = 1.4 * _PIPE_R, 0.12, 1.65
    for name, z, x0 in (("Verteiler-VL", _FLOW_Z, riser_x + elbow_r), ("Verteiler-RL", _RETURN_Z, 1.7)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (x0, _HEADER_Y, z), (4.25, _HEADER_Y, z), _PIPE_R)])
    s.add("IfcPipeSegment", "WE-VL", [pipe_solid(f, (1.4, _HEADER_Y, 1.2), (riser_x - elbow_r, _HEADER_Y, 1.2), _PIPE_R)], serves=gen)
    s.add("IfcPipeSegment", "WE-Steig", [pipe_solid(f, (riser_x, _HEADER_Y, 1.2 + elbow_r), (riser_x, _HEADER_Y, _FLOW_Z - elbow_r), _PIPE_R)], serves=gen)

    # 90° elbows at the foot and head of the generator riser.
    s.add(
        "IfcPipeFitting",
        "Formteile-WE",
        [
            bend_solid(f, (riser_x - elbow_r, _HEADER_Y, 1.2), (1, 0, 0), (0, 0, 1), elbow_r, 90, fit_r),
            bend_solid(f, (riser_x, _HEADER_Y, _FLOW_Z - elbow_r), (0, 0, 1), (1, 0, 0), elbow_r, 90, fit_r),
        ],
        keys=("rohrformteil",),
        predefined_type="BEND",
        serves=gen,
    )
    # Tees where the circuits branch off the flow header: sleeve on the header plus a spigot down.
    tees = []
    for x in (2.3, 3.0, 3.7):
        tees.append(pipe_solid(f, (x - 0.1, _HEADER_Y, _FLOW_Z), (x + 0.1, _HEADER_Y, _FLOW_Z), fit_r, segments=28))
        tees.append(pipe_solid(f, (x, _HEADER_Y, _FLOW_Z), (x, _HEADER_Y, _FLOW_Z - 0.14), fit_r, segments=28))
    s.add("IfcPipeFitting", "T-Stuecke", tees, keys=("rohrformteil",), predefined_type="JUNCTION")
    # 180° return bend closing flow and return header at the far end.
    u_r = (_RETURN_Z - _FLOW_Z) / 2
    s.add(
        "IfcPipeFitting",
        "U-Bogen",
        [bend_solid(f, (4.25, _HEADER_Y, _FLOW_Z), (1, 0, 0), (0, 0, 1), u_r, 180, fit_r)],
        keys=("rohrformteil",),
        predefined_type="BEND",
    )

    # Three pump groups: pump on the riser, motor in front, coupling between.
    for i, x in enumerate((2.3, 3.0, 3.7)):
        s.add(
            "IfcPipeSegment",
            f"Heizgruppe-{i + 1}",
            [pipe_solid(f, (x, _HEADER_Y, 0.0), (x, _HEADER_Y, _FLOW_Z - 0.08), _PIPE_R)],
            serves=("durchflussmesser",) if i == 2 else (),
        )
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
    for name, x0, x1, system in (
        ("Anschluss-MAG", 4.28, 5.35, "i-078-warmevert-expansion"),
        ("Anschluss-Entgasung", 5.35, 6.1, "i-077-warmevert-entgasung"),
    ):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (x0, _HEADER_Y, 1.25), (x1, _HEADER_Y, 1.25), 0.03)], serves=(system,))

    # Controls and metering on the side wall.
    s.add("IfcController", "Regler-Heizung", [box_solid(f, 0.0, 1.5, 1.0, 0.3, 2.1, 1.9)], keys=("regler", "i-027-gebaudeleitsystem-gebaudeautomation"))
    s.add("IfcFlowMeter", "Elektrozaehler", [box_solid(f, 0.0, 2.25, 1.25, 0.18, 2.55, 1.7)], keys=("i-021-energiemanagement",), predefined_type="ENERGYMETER")
    s.add("IfcController", "Energiemanager", [box_solid(f, 0.0, 2.65, 1.25, 0.15, 2.9, 1.6)], keys=("i-021-energiemanagement",))

    # Combined heat and power unit: engine coupled to a generator on a plinth.
    if fuel in ("gas",) and extra != HEAT_ELECTRIC_STORAGE:
        s.add("IfcBuildingElementProxy", "Sockel-BHKW", [box_solid(f, 3.4, 2.5, 0.0, 6.0, 3.8, 0.12)], object_type="Sockel")
        s.add(
            "IfcEngine",
            "BHKW-Motor",
            [box_solid(f, 3.55, 2.65, 0.12, 4.9, 3.65, 1.25), vertical_cylinder_solid(f, 4.2, 3.15, 1.25, 0.09, WALL_HEIGHT - 1.25, segments=8)],
            keys=("verbrennungsmotor",),
        )
        s.add("IfcElectricGenerator", "BHKW-Generator", [box_solid(f, 4.95, 2.75, 0.12, 5.85, 3.55, 1.05)], serves=("verbrennungsmotor",))
    if gas_detection:
        _gas_detection(s)
    if extra in _HEATING_EXTRAS:
        _HEATING_EXTRAS[extra](s, extra)
    return s


def _safety_devices(s: Scene, key: str) -> None:
    """Safety valve with blow-off line to a tundish, temperature limiter and pressure switch on the boiler;
    motorised three-way mixing valve on the boiler riser."""
    f = s.ifc_file
    keys = (key,)
    s.add(
        "IfcValve",
        "Sicherheitsventil",
        [vertical_cylinder_solid(f, 1.2, 0.3, 1.5, 0.04, 0.12, segments=12), box_solid(f, 1.14, 0.24, 1.62, 1.26, 0.36, 1.78)],
        keys=keys,
        predefined_type="PRESSURERELIEF",
    )
    s.add(
        "IfcPipeSegment",
        "Ausblaseleitung",
        polyline_solids(f, [(1.26, 0.3, 1.7), (1.5, 0.3, 1.7), (1.5, 0.3, 0.45)], 0.025, segments=10),
        keys=keys,
        thin=True,
    )
    s.add("IfcWasteTerminal", "Ablauftrichter", [frustum(f, 1.5, 0.3, 0.45, 0.3, (0.1, 0.1), (0.04, 0.04))], keys=keys, predefined_type="FLOORTRAP")
    s.add(
        "IfcSensor",
        "Sicherheitstemperaturbegrenzer",
        [box_solid(f, 0.5, 0.75, 1.5, 0.7, 0.9, 1.65)],
        keys=keys,
        predefined_type="TEMPERATURESENSOR",
    )
    s.add(
        "IfcSensor",
        "Druckwaechter",
        [vertical_cylinder_solid(f, 0.8, 0.3, 1.5, 0.025, 0.1, segments=8), pipe_solid(f, (0.8, 0.3, 1.66), (0.8, 0.38, 1.66), 0.07, segments=16)],
        keys=keys,
        predefined_type="PRESSURESENSOR",
    )
    s.add(
        "IfcValve",
        "Mischventil",
        [box_solid(f, 1.57, _HEADER_Y - 0.1, 1.45, 1.73, _HEADER_Y + 0.1, 1.65), pipe_solid(f, (1.65, _HEADER_Y + 0.1, 1.55), (1.65, _HEADER_Y + 0.22, 1.55), 0.03, segments=10)],
        keys=keys,
        predefined_type="MIXING",
    )
    s.add("IfcActuator", "Mischventilantrieb", [box_solid(f, 1.55, _HEADER_Y + 0.22, 1.45, 1.75, _HEADER_Y + 0.4, 1.68)], keys=keys, predefined_type="ELECTRICACTUATOR")


def _flue_measurement(s: Scene, key: str) -> None:
    """Measuring port on the flue with the probe of a flue gas analyser on a tripod."""
    f = s.ifc_file
    keys = (key,)
    z = 2.15
    s.add(
        "IfcBuildingElementProxy",
        "Messoeffnung",
        [pipe_solid(f, (0.9, 0.6, z), (0.9, 0.72, z), 0.035, segments=12), pipe_solid(f, (0.9, 0.72, z), (0.9, 0.75, z), 0.05, segments=12)],
        keys=keys,
        object_type="Messoeffnung",
    )
    s.add(
        "IfcSensor",
        "Abgassonde",
        [pipe_solid(f, (0.9, 0.42, z), (0.9, 0.95, z), 0.012, segments=8), box_solid(f, 0.85, 0.95, z - 0.05, 0.95, 1.1, z + 0.05)],
        keys=keys,
        predefined_type="GASSENSOR",
    )
    ax, ay, top = 2.0, 1.6, 1.0
    s.add(
        "IfcFlowInstrument",
        "Abgasmessgeraet",
        [
            box_solid(f, ax - 0.2, ay - 0.15, top, ax + 0.2, ay + 0.15, top + 0.3),
            *(pipe_solid(f, (ax + dx, ay + dy, 0.0), (ax, ay, top), 0.015, segments=6) for dx, dy in ((0.3, 0.0), (-0.15, 0.26), (-0.15, -0.26))),
        ],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Abgasmessgeraet",
        thin=True,
    )
    s.add(
        "IfcCableSegment",
        "Messschlauch",
        polyline_solids(f, [(0.9, 1.1, z), (0.9, 1.45, z - 0.3), (ax - 0.2, ay, top + 0.2)], 0.015),
        keys=keys,
        thin=True,
    )


def _electric_storage(s: Scene, key: str) -> None:
    """Central electric storage heater: insulated core block with contactor box, power feed from the
    back wall and flow / return to the header."""
    f = s.ifc_file
    keys = (key,)
    x0, y0, x1, y1, top = 3.5, 2.6, 5.7, 3.9, 1.7
    s.add("IfcBuildingElementProxy", "Sockel-Speicher", [box_solid(f, x0 - 0.05, y0 - 0.05, 0.0, x1 + 0.05, y1 + 0.05, 0.1)], object_type="Sockel")
    s.add(
        "IfcElectricFlowStorageDevice",
        "Zentralspeicher",
        [box_solid(f, x0, y0, 0.1, x1, y1, top), box_solid(f, x0 + 0.1, y0 - 0.06, 0.4, x0 + 0.7, y0, 1.3)],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Elektro-Zentralspeicher",
    )
    s.add("IfcElectricDistributionBoard", "Schuetzkasten", [box_solid(f, x1 - 0.6, y0 - 0.15, 0.9, x1 - 0.1, y0, 1.5)], keys=keys, predefined_type="SWITCHBOARD")
    s.add(
        "IfcCableSegment",
        "Speicherzuleitung",
        polyline_solids(f, [(x1 - 0.35, y0 - 0.08, 1.5), (x1 - 0.35, y0 - 0.08, 2.7), (x1 - 0.35, 0.05, 2.7), (x1 - 0.35, 0.05, 2.9)], 0.02),
        predefined_type="CABLESEGMENT",
        thin=True,
        serves=keys,
    )
    for name, x, z in (("Speicher-VL", 4.0, _FLOW_Z), ("Speicher-RL", 4.15, _RETURN_Z)):
        s.add(
            "IfcPipeSegment",
            name,
            polyline_solids(f, [(x, 3.0, top), (x, 3.0, 2.6), (x, _HEADER_Y, 2.6), (x, _HEADER_Y, z + 0.05)], 0.04, segments=10),
            thin=True,
            serves=keys,
        )


def _subdistribution(s: Scene, key: str) -> None:
    """Secondary manifold on the side wall: flow / return bars with circuit valves; fed from the header."""
    f = s.ifc_file
    keys = (key,)
    y0, y1, x = 3.0, 4.3, 0.2
    for name, z in (("Unterverteiler-VL", 1.75), ("Unterverteiler-RL", 1.45)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (x, y0, z), (x, y1, z), 0.045, segments=12)], keys=keys, predefined_type="RIGIDSEGMENT", thin=True)
    valves = []
    for y in (3.25, 3.65, 4.05):
        for z in (1.45, 1.75):
            valves += [box_solid(f, x - 0.06, y - 0.06, z - 0.12, x + 0.06, y + 0.06, z - 0.02), vertical_cylinder_solid(f, x, y, z + 0.05, 0.03, 0.08, segments=10)]
    s.add("IfcValve", "Strangventile", valves, keys=keys, predefined_type="REGULATING")
    s.add(
        "IfcPipeSegment",
        "Heizkreise",
        [pipe_solid(f, (x, y, z - 0.12), (x, y, 0.0), 0.025, segments=8) for y in (3.25, 3.65, 4.05) for z in (1.45, 1.75)],
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcPipeSegment",
        "Zuleitung-Unterverteiler",
        polyline_solids(f, [(x, y0, 1.75), (x, 2.95, 1.75), (x, 2.95, 2.6), (x, 0.4, 2.6), (1.75, 0.4, 2.6), (1.75, _HEADER_Y, 2.6), (1.75, _HEADER_Y, _RETURN_Z + 0.05)], 0.04, segments=10),
        thin=True,
        serves=keys,
    )
    s.add("IfcPump", "Gruppenpumpe", [pipe_solid(f, (x, 2.95, 2.1), (x, 2.95, 2.4), 0.11, segments=14)], keys=keys)


def _flue_filter(s: Scene, key: str) -> None:
    """Electrostatic precipitator in the flue: housing with hopper and ash bin, high-voltage unit beside it."""
    f = s.ifc_file
    keys = (key,)
    cx, cy = 0.9, 0.5
    s.add(
        "IfcFilter",
        "Elektrofilter",
        [box_solid(f, cx - 0.3, cy - 0.3, 2.0, cx + 0.3, cy + 0.3, 2.7), frustum(f, cx, cy, 2.0, 1.8, (0.3, 0.3), (0.12, 0.12))],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Elektrofilter",
    )
    s.add("IfcBuildingElementProxy", "Aschebehaelter", [box_solid(f, cx + 0.35, cy + 0.45, 0.0, cx + 0.75, cy + 0.85, 0.45)], keys=keys, object_type="Aschebehaelter")
    s.add("IfcPipeSegment", "Ascheaustrag", polyline_solids(f, [(cx, cy, 1.8), (cx, cy + 0.3, 1.8), (cx + 0.55, cy + 0.65, 0.45)], 0.05, segments=10), keys=keys)
    s.add("IfcElectricDistributionBoard", "Hochspannungsteil", [box_solid(f, 0.0, 1.0, 2.1, 0.2, 1.45, 2.6)], keys=keys, predefined_type="SWITCHBOARD")
    s.add(
        "IfcCableSegment",
        "HV-Kabel",
        polyline_solids(f, [(0.1, 1.0, 2.4), (0.1, 0.5, 2.4), (cx - 0.3, 0.5, 2.4)], 0.015),
        predefined_type="CABLESEGMENT",
        thin=True,
        serves=keys,
    )


def _wet_scrubber(s: Scene, key: str) -> None:
    """Wet scrubber column beside the boiler: flue in at the top, clean gas stack up, sump tank and circulation pump."""
    f = s.ifc_file
    keys = (key,)
    cx, cy = 1.0, 2.0
    s.add(
        "IfcFilter",
        "Nassabscheider",
        [vertical_cylinder_solid(f, cx, cy, 0.5, 0.32, 1.9, segments=20), frustum(f, cx, cy, 0.5, 0.25, (0.22, 0.22), (0.1, 0.1))],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Nassabscheider",
    )
    s.add("IfcPipeSegment", "Rohgas", polyline_solids(f, [(0.9, 0.5, 2.55), (0.9, cy, 2.55), (0.9, cy, 2.4)], 0.11, segments=12), keys=keys)
    s.add("IfcChimney", "Reingas", [vertical_cylinder_solid(f, cx + 0.15, cy + 0.1, 2.4, 0.1, WALL_HEIGHT - 2.4, segments=12)], keys=keys)
    s.add("IfcTank", "Waschwasserbehaelter", [box_solid(f, cx - 0.35, cy - 0.3, 0.0, cx + 0.35, cy + 0.3, 0.25)], keys=keys, predefined_type="STORAGE")
    s.add("IfcPump", "Umwaelzpumpe", [box_solid(f, cx + 0.45, cy - 0.15, 0.0, cx + 0.75, cy + 0.15, 0.3)], keys=keys)
    s.add(
        "IfcPipeSegment",
        "Waschwasser",
        polyline_solids(f, [(cx + 0.6, cy, 0.3), (cx + 0.6, cy, 2.2), (cx + 0.3, cy, 2.2)], 0.025, segments=8),
        keys=keys,
        thin=True,
    )


_HEATING_EXTRAS = {
    HEAT_SAFETY: _safety_devices,
    HEAT_FLUE_MEASUREMENT: _flue_measurement,
    HEAT_ELECTRIC_STORAGE: _electric_storage,
    HEAT_SUBDISTRIBUTION: _subdistribution,
    HEAT_FLUE_FILTER: _flue_filter,
    HEAT_SCRUBBER: _wet_scrubber,
}


def _gas_detection(s: Scene) -> None:
    """Gas detectors under the ceiling (natural gas rises), warning panel, siren, shut-off valve on the gas line."""
    f = s.ifc_file
    gas = ("gasmeldeanlage",)
    cable_z = 2.82

    detectors = []
    for x, y, on_back_wall in ((2.9, 0.0, True), (0.0, 2.4, False)):
        if on_back_wall:
            detectors += [
                box_solid(f, x - 0.12, 0.0, 2.48, x + 0.12, 0.12, 2.75),
                vertical_cylinder_solid(f, x, 0.07, 2.4, 0.05, 0.08, segments=12),
            ]
        else:
            detectors += [
                box_solid(f, 0.0, y - 0.12, 2.48, 0.12, y + 0.12, 2.75),
                vertical_cylinder_solid(f, 0.07, y, 2.4, 0.05, 0.08, segments=12),
            ]
    s.add("IfcSensor", "Gasmelder", detectors, keys=gas, predefined_type="GASSENSOR")
    s.add("IfcUnitaryControlElement", "Gaswarnzentrale", [box_solid(f, 0.0, 3.3, 1.2, 0.14, 3.75, 1.75)], keys=gas, predefined_type="ALARMPANEL")
    s.add(
        "IfcAlarm",
        "Hupe-Blitzleuchte",
        [box_solid(f, 0.0, 3.9, 2.3, 0.08, 4.1, 2.5), pipe_solid(f, (0.08, 4.0, 2.4), (0.2, 4.0, 2.4), 0.08, segments=14)],
        keys=gas,
        predefined_type="SIREN",
    )
    s.add(
        "IfcValve",
        "Gas-Absperrventil",
        [box_solid(f, 0.22, 1.03, 0.68, 0.38, 1.17, 0.82), vertical_cylinder_solid(f, 0.3, 1.1, 0.82, 0.055, 0.12, segments=12)],
        keys=gas,
        predefined_type="ISOLATING",
    )

    def cable(name: str, *points: tuple[float, float, float]) -> None:
        segments = [pipe_solid(f, a, b, 0.018, segments=6) for a, b in zip(points, points[1:])]
        s.add("IfcCableSegment", name, segments, predefined_type="CABLESEGMENT", thin=True, serves=gas)

    cable("Melderkabel-Rueckwand", (2.9, 0.03, 2.75), (2.9, 0.03, cable_z), (0.03, 0.03, cable_z))
    cable("Melderkabel-Seitenwand", (0.03, 0.03, cable_z), (0.03, 4.0, cable_z))
    cable("Melderkabel-Melder", (0.03, 2.4, 2.75), (0.03, 2.4, cable_z))
    cable("Kabel-Zentrale", (0.03, 3.5, cable_z), (0.03, 3.5, 1.75))
    cable("Kabel-Hupe", (0.03, 4.0, cable_z), (0.03, 4.0, 2.5))
    cable("Kabel-Ventil", (0.3, 1.1, 0.94), (0.3, 1.1, 1.0), (0.03, 1.1, 1.0), (0.03, 1.1, cable_z))


# ---------------------------------------------------------------------------
# Kaeltezentrale
# ---------------------------------------------------------------------------

TUBE_BUNDLE = "rohrbundel"
GAS_ENGINE_HEAT_PUMP = "d05-02-018-warmepumpe-gasmotor"


def chiller_room(extra: str | None = None) -> Scene:
    """Opened water chiller (evaporator, condenser, compressor) and a brine heat pump with buffer.

    ``extra``: ``TUBE_BUNDLE`` draws the evaporator shell dotted with its tube bundle inside;
    ``GAS_ENGINE_HEAT_PUMP`` adds a gas-engine heat pump in the free front of the room.
    """
    s = corner_room("Kaeltezentrale")
    f = s.ifc_file

    # Chiller frame along the back wall: evaporator below, condenser above.
    s.add("IfcBuildingElementProxy", "Rahmen-KM", [box_solid(f, 0.4, 0.15, 0.0, 3.6, 1.15, 0.12)], object_type="Rahmen")
    s.add(
        "IfcEvaporator",
        "Verdampfer",
        [horizontal_cylinder(f, 0.6, 3.4, 0.65, 0.5, 0.32)],
        keys=("verdampfer",),
        predefined_type="FLOODEDSHELLANDTUBE",
        dotted=extra == TUBE_BUNDLE,
    )
    if extra == TUBE_BUNDLE:
        tubes = [horizontal_cylinder(f, 0.62, 3.38, 0.65 + dy, 0.5 + dz, 0.035, segments=10) for dy in (-0.16, 0.0, 0.16) for dz in (-0.14, 0.0, 0.14)]
        tubes += [horizontal_cylinder(f, x, x + 0.04, 0.65, 0.5, 0.26, segments=24) for x in (0.7, 2.0, 3.26)]
        s.add("IfcTubeBundle", "Rohrbuendel", tubes, keys=(TUBE_BUNDLE,), predefined_type="USERDEFINED", object_type="Glattrohrbuendel")
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
    heat_pump = ("i-073-warmeerz-warmepumpen",)
    for name, z in (("WP-VL", 1.1), ("WP-RL", 0.4)):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (1.3, 2.8, z), (1.65, 2.8, z), 0.05)], serves=heat_pump)
    s.add("IfcPipeSegment", "Sole", [pipe_solid(f, (0.0, 2.6, 0.3), (0.3, 2.6, 0.3), 0.05)], serves=heat_pump)
    if extra == GAS_ENGINE_HEAT_PUMP:
        _gas_engine_heat_pump(s, extra)
    return s


def _gas_engine_heat_pump(s: Scene, key: str) -> None:
    """Gas engine driving an open compressor on a common frame, exhaust heat exchanger, gas line and stack."""
    f = s.ifc_file
    keys = (key,)
    y0, y1 = 2.7, 3.7
    s.add("IfcBuildingElementProxy", "Grundrahmen-GWP", [box_solid(f, 3.3, y0, 0.0, 6.2, y1, 0.15)], keys=keys, object_type="Grundrahmen")
    s.add("IfcEngine", "Gasmotor", [box_solid(f, 3.4, y0 + 0.1, 0.15, 4.6, y1 - 0.1, 1.2), box_solid(f, 3.6, y0 + 0.25, 1.2, 4.4, y1 - 0.25, 1.45)], keys=keys, predefined_type="INTERNALCOMBUSTION")
    s.add("IfcBuildingElementProxy", "Kupplung", [horizontal_cylinder(f, 4.6, 4.85, 3.2, 0.7, 0.12, segments=14)], keys=keys, object_type="Kupplung")
    s.add("IfcCompressor", "Verdichter-GWP", [horizontal_cylinder(f, 4.85, 5.45, 3.2, 0.7, 0.3, segments=18)], keys=keys, predefined_type="OPENTYPE")
    s.add("IfcHeatExchanger", "Abgaswaermetauscher", [box_solid(f, 5.6, y0 + 0.15, 0.15, 6.1, y1 - 0.15, 1.4)], keys=keys, predefined_type="SHELLANDTUBE")
    s.add("IfcChimney", "Abgas-GWP", [pipe_solid(f, (3.7, 3.2, 1.45), (3.7, 3.2, WALL_HEIGHT), 0.08, segments=12)], keys=keys)
    s.add(
        "IfcPipeSegment",
        "Gasleitung-GWP",
        polyline_solids(f, [(4.2, 0.0, 2.6), (4.2, 3.0, 2.6), (4.2, 3.0, 1.45)], 0.03, segments=10),
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcPipeSegment",
        "Heizwasser-GWP",
        polyline_solids(f, [(5.85, y0 + 0.15, 1.1), (5.85, 2.8, 1.1), (2.55, 2.8, 1.1)], 0.05, segments=10),
        serves=keys,
    )


# ---------------------------------------------------------------------------
# Wasserzentrale
# ---------------------------------------------------------------------------

WATER_TREATMENT = "i05-05-001-wasseraufbereitungsanlagen"
WATER_FILTER = "d08-02-005-filteranlage"
WATER_NEUTRALISATION = "d08-02-003-neutralisation-entgiftung"
DRAIN_NEUTRALISATION = "d09-02-007-neutralisationseinrichtung"


def water_room(extra: str | None = None) -> Scene:
    """Water treatment line: softener, desalination, reverse osmosis, UV, booster, chlorine dosing.

    The treatment units also carry ``WATER_TREATMENT`` (the whole line). ``extra`` adds pressure
    filters (``WATER_FILTER``), a neutralisation plant (``WATER_NEUTRALISATION``) or a neutralisation
    box at a floor drain (``DRAIN_NEUTRALISATION``) in the free front of the room.
    """
    s = corner_room("Wasserzentrale")
    f = s.ifc_file
    line = (WATER_TREATMENT,)

    s.add("IfcPipeSegment", "Trinkwasser", [pipe_solid(f, (0.0, 0.25, 2.1), (6.2, 0.25, 2.1), 0.05)], serves=line)

    # Softener: two resin columns and a brine tank.
    s.add(
        "IfcFilter",
        "Enthaertung",
        [vertical_cylinder_solid(f, x, 0.45, 0.0, 0.2, 1.5, segments=16) for x in (0.45, 0.95)]
        + [vertical_cylinder_solid(f, 1.55, 0.45, 0.0, 0.28, 0.9, segments=16)],
        keys=("i-022-enthartungsanlage", *line),
        object_type="Enthaertungsanlage",
    )
    # Ion-exchange desalination: two taller columns.
    s.add(
        "IfcFilter",
        "Entsalzung",
        [vertical_cylinder_solid(f, x, 0.45, 0.0, 0.24, 1.8, segments=16) for x in (2.2, 2.75)],
        keys=("i-023-entsalzungsanlage", *line),
        object_type="Entsalzungsanlage",
    )
    # Reverse-osmosis rack: horizontal membrane tubes in a frame.
    rack = [box_solid(f, 3.3, 0.1, 0.0, 3.36, 0.8, 1.7), box_solid(f, 4.9, 0.1, 0.0, 4.96, 0.8, 1.7)]
    rack += [horizontal_cylinder(f, 3.3, 4.96, 0.45, z, 0.1, segments=12) for z in (0.5, 0.85, 1.2, 1.55)]
    s.add("IfcFilter", "Osmose", rack, keys=("i-036-osmoseanlage", *line), object_type="Umkehrosmose")
    # Connections from the treatment units up to the main.
    for name, x, z_top, system in (
        ("Enthaertung-Anschluss", 0.95, 1.5, "i-022-enthartungsanlage"),
        ("Entsalzung-Anschluss", 2.75, 1.8, "i-023-entsalzungsanlage"),
        ("Osmose-Anschluss", 4.1, 1.7, "i-036-osmoseanlage"),
    ):
        s.add("IfcPipeSegment", name, [pipe_solid(f, (x, 0.25, z_top), (x, 0.25, 2.05), 0.04)], serves=(system, *line))
    # UV reactor on the outgoing line (kept low, right of the rack).
    s.add("IfcFilter", "UV-Reaktor", [horizontal_cylinder(f, 5.2, 6.2, 0.35, 1.1, 0.12, segments=14)], keys=("i-065-uv-anlage", *line), object_type="UV-Desinfektion")
    s.add("IfcPipeSegment", "UV-Anschluss", [pipe_solid(f, (5.3, 0.35, 1.1), (5.3, 0.35, 2.05), 0.04)], serves=("i-065-uv-anlage", *line))

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
    booster = ("i-018-druckerhohungsanlage",)
    pump_ys = (1.85, 2.3, 2.75)
    # Suction: drop from the main behind the softener, header behind the pumps.
    s.add(
        "IfcPipeSegment",
        "DEA-Saugleitung",
        polyline_solids(f, [(0.12, 0.25, 2.1), (0.12, 0.25, 0.3), (0.12, pump_ys[-1], 0.3)], 0.05, segments=10)
        + [pipe_solid(f, (0.12, y, 0.3), (0.38, y, 0.3), 0.035, segments=10) for y in pump_ys],
        serves=booster,
    )
    # Discharge: pump outlets into the header, header to the vessel and up to the distribution.
    s.add(
        "IfcPipeSegment",
        "DEA-Sammler",
        [pipe_solid(f, (0.5, 1.6, 1.15), (0.5, 3.5, 1.15), 0.05)]
        + [pipe_solid(f, (0.5, y, 1.0), (0.5, y, 1.15), 0.035, segments=10) for y in pump_ys]
        + [pipe_solid(f, (0.5, 3.5, 1.0), (0.5, 3.5, 1.15), 0.035, segments=10)],
        serves=booster,
    )
    s.add("IfcPipeSegment", "DEA-Druckleitung", [pipe_solid(f, (0.5, 1.6, 1.15), (0.5, 1.6, 3.0), 0.05)], serves=booster)

    # Chlorine dosing: dosing tank, wall pump, injection line.
    s.add(
        "IfcTank",
        "Chlor-Dosierbehaelter",
        [vertical_cylinder_solid(f, 2.0, 3.6, 0.0, 0.25, 0.8, segments=16)],
        keys=("i-016-chlordosierungsanlage",),
        predefined_type="STORAGE",
    )
    s.add("IfcPump", "Dosierpumpe", [box_solid(f, 1.85, 3.25, 0.8, 2.15, 3.45, 1.0)], keys=("i-016-chlordosierungsanlage",))
    s.add(
        "IfcPipeSegment",
        "Impfleitung",
        [
            pipe_solid(f, (2.0, 3.35, 1.0), (2.0, 3.35, 2.1), 0.02),
            pipe_solid(f, (2.0, 3.35, 2.1), (2.0, 0.3, 2.1), 0.02),
        ],
        thin=True,
        serves=("i-016-chlordosierungsanlage",),
    )
    if extra == WATER_FILTER:
        _pressure_filters(s, extra)
    elif extra == WATER_NEUTRALISATION:
        _neutralisation_plant(s, extra)
    elif extra == DRAIN_NEUTRALISATION:
        _drain_neutralisation(s, extra)
    return s


def _pressure_filters(s: Scene, key: str) -> None:
    """Two pressure filter vessels with a front valve manifold, connected up to the main."""
    f = s.ifc_file
    keys = (key,)
    xs, y = (3.7, 4.7), 2.8
    s.add(
        "IfcFilter",
        "Druckfilter",
        [part for x in xs for part in (vertical_cylinder_solid(f, x, y, 0.15, 0.36, 1.65, segments=24), vertical_cylinder_solid(f, x, y, 1.8, 0.22, 0.08, segments=24))]
        + [vertical_cylinder_solid(f, x + dx, y + dy, 0.0, 0.03, 0.15, segments=8) for x in xs for dx, dy in ((0.25, 0.0), (-0.12, 0.22), (-0.12, -0.22))],
        keys=keys,
        predefined_type="WATERFILTER",
    )
    s.add(
        "IfcValve",
        "Filterarmaturen",
        [part for x in xs for z in (0.5, 1.4) for part in (box_solid(f, x - 0.08, y - 0.5, z - 0.08, x + 0.08, y - 0.36, z + 0.08), vertical_cylinder_solid(f, x, y - 0.43, z + 0.08, 0.04, 0.08, segments=10))],
        keys=keys,
        predefined_type="ISOLATING",
    )
    s.add(
        "IfcPipeSegment",
        "Filterleitungen",
        [pipe_solid(f, (x, y - 0.5, z), (x, y - 0.36, z), 0.045, segments=10) for x in xs for z in (0.5, 1.4)]
        + polyline_solids(f, [(xs[0], y - 0.5, 1.4), (xs[0], 1.6, 1.4), (xs[1], 1.6, 1.4)], 0.045, segments=10)
        + polyline_solids(f, [(xs[1], y - 0.5, 1.4), (xs[1], 1.6, 1.4), (xs[1], 1.6, 2.1), (xs[1], 0.3, 2.1)], 0.045, segments=10),
        thin=True,
        serves=keys,
    )


def _neutralisation_plant(s: Scene, key: str) -> None:
    """Neutralisation tank with agitator, pH probe and two dosing stations (acid / lye)."""
    f = s.ifc_file
    keys = (key,)
    cx, cy = 4.2, 2.9
    s.add("IfcTank", "Neutralisationsbehaelter", [vertical_cylinder_solid(f, cx, cy, 0.0, 0.6, 1.4, segments=28)], keys=keys, predefined_type="BASIN")
    s.add(
        "IfcElectricMotor",
        "Ruehrwerk",
        [box_solid(f, cx - 0.5, cy - 0.06, 1.4, cx + 0.5, cy + 0.06, 1.46), vertical_cylinder_solid(f, cx, cy, 1.46, 0.1, 0.3, segments=14)],
        keys=keys,
    )
    s.add("IfcSensor", "pH-Sonde", [vertical_cylinder_solid(f, cx + 0.35, cy - 0.2, 1.0, 0.02, 0.6, segments=8)], keys=keys, predefined_type="PHSENSOR", thin=True)
    for i, x in enumerate((5.4, 6.0)):
        s.add("IfcTank", f"Dosierbehaelter-{i + 1}", [vertical_cylinder_solid(f, x, 3.6, 0.0, 0.22, 0.75, segments=16)], keys=keys, predefined_type="STORAGE")
        s.add("IfcPump", f"Dosierpumpe-N{i + 1}", [box_solid(f, x - 0.12, 3.48, 0.75, x + 0.12, 3.72, 0.95)], keys=keys)
        s.add(
            "IfcPipeSegment",
            f"Dosierleitung-{i + 1}",
            polyline_solids(f, [(x, 3.6, 0.95), (x, 3.6, 1.6), (cx + 0.2 + 0.1 * i, 3.6, 1.6), (cx + 0.2 + 0.1 * i, cy, 1.6), (cx + 0.2 + 0.1 * i, cy, 1.4)], 0.015),
            thin=True,
            serves=keys,
        )
    s.add("IfcController", "Neutralisationssteuerung", [box_solid(f, 5.4, 2.0, 0.9, 6.0, 2.2, 1.6)], keys=keys)
    s.add(
        "IfcPipeSegment",
        "Zulauf-Neutralisation",
        polyline_solids(f, [(4.9, 0.6, 1.2), (4.9, 1.4, 1.2), (cx, 1.4, 1.2), (cx, cy - 0.6, 1.2)], 0.04, segments=10),
        thin=True,
        serves=keys,
    )


def _drain_neutralisation(s: Scene, key: str) -> None:
    """Neutralisation box with granulate between the osmosis concentrate line and a floor drain."""
    f = s.ifc_file
    keys = (key,)
    x0, y0, x1, y1 = 3.6, 2.4, 4.4, 2.8
    s.add(
        "IfcInterceptor",
        "Neutralisationsbox",
        [box_solid(f, x0, y0, 0.0, x1, y1, 0.32), box_solid(f, x0 + 0.05, y0 + 0.05, 0.32, x1 - 0.05, y1 - 0.05, 0.36)],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Neutralisationsbox",
    )
    s.add("IfcWasteTerminal", "Bodenablauf", [box_solid(f, 4.9, 2.45, 0.0, 5.2, 2.75, 0.02)], predefined_type="FLOORTRAP")
    s.add(
        "IfcPipeSegment",
        "Konzentratleitung",
        polyline_solids(f, [(4.6, 0.8, 0.3), (4.6, 1.7, 0.3), (4.0, 1.7, 0.3), (4.0, y0, 0.3)], 0.025, segments=10),
        keys=keys,
        thin=True,
    )
    s.add(
        "IfcPipeSegment",
        "Ablauf-Neutralisation",
        polyline_solids(f, [(x1, 2.6, 0.2), (5.05, 2.6, 0.2), (5.05, 2.6, 0.03)], 0.025, segments=10),
        keys=keys,
        thin=True,
    )


# ---------------------------------------------------------------------------
# Untergeschoss: Rueckstauverschluss
# ---------------------------------------------------------------------------

def backflow_basement(key: str = "d09-01-002-ruckstauverschlusse-elektrisch") -> Scene:
    """Basement laundry below the backflow level: sink and washing machine drain into an exposed
    waste pipe that leaves through the side wall past a motorised backflow valve.

    ``key`` tags the valve, its level probe, actuator and control panel; the cables serve it.
    The waste pipe is tagged ``d09-01-001-leitungen``.
    """
    s = corner_room("UG-Waschraum", width=4.2, depth=2.4, height=2.6)
    f = s.ifc_file
    keys = (key,)
    pipe_y, pipe_z, pipe_r = 0.14, 0.3, 0.055

    s.add(
        "IfcElectricAppliance",
        "Waschmaschine",
        [box_solid(f, 2.2, 0.05, 0.0, 2.8, 0.65, 0.85), pipe_solid(f, (2.5, 0.65, 0.45), (2.5, 0.68, 0.45), 0.17, segments=20)],
        predefined_type="WASHINGMACHINE",
    )
    s.add(
        "IfcSanitaryTerminal",
        "Ausgussbecken",
        [
            box_solid(f, 3.1, 0.0, 0.65, 3.8, 0.5, 0.68),
            box_solid(f, 3.1, 0.0, 0.68, 3.14, 0.5, 0.9),
            box_solid(f, 3.76, 0.0, 0.68, 3.8, 0.5, 0.9),
            box_solid(f, 3.1, 0.46, 0.68, 3.8, 0.5, 0.9),
            box_solid(f, 3.1, 0.0, 0.68, 3.8, 0.04, 0.9),
        ],
        predefined_type="SINK",
    )
    s.add(
        "IfcBuildingElementProxy",
        "Untergestell",
        [box_solid(f, x, y, 0.0, x + 0.04, y + 0.04, 0.65) for x in (3.12, 3.74) for y in (0.02, 0.44)],
        object_type="Untergestell",
    )
    s.add(
        "IfcPipeSegment",
        "Abwasser",
        [
            pipe_solid(f, (3.45, pipe_y, 0.65), (3.45, pipe_y, pipe_z), 0.04),
            pipe_solid(f, (2.5, pipe_y, 0.55), (2.5, pipe_y, pipe_z), 0.03),
            pipe_solid(f, (3.45, pipe_y, pipe_z), (1.2, pipe_y, pipe_z), pipe_r, segments=12),
            pipe_solid(f, (0.5, pipe_y, pipe_z), (-0.2, pipe_y, pipe_z), pipe_r, segments=12),
        ],
        keys=("d09-01-001-leitungen",),
        thin=True,
    )

    x0, x1 = 0.5, 1.2
    s.add(
        "IfcValve",
        "Rueckstauverschluss",
        [
            pipe_solid(f, (x0, pipe_y, pipe_z), (x0 + 0.04, pipe_y, pipe_z), 0.11, segments=16),
            pipe_solid(f, (x1 - 0.04, pipe_y, pipe_z), (x1, pipe_y, pipe_z), 0.11, segments=16),
            box_solid(f, x0 + 0.04, pipe_y - 0.14, 0.12, x1 - 0.04, pipe_y + 0.14, 0.48),
            box_solid(f, x0 + 0.1, pipe_y - 0.12, 0.48, x1 - 0.1, pipe_y + 0.12, 0.51),
        ],
        keys=keys,
        predefined_type="CHECK",
    )
    s.add(
        "IfcActuator",
        "Stellmotor",
        [
            box_solid(f, 0.68, pipe_y - 0.09, 0.51, 0.9, pipe_y + 0.09, 0.7),
            pipe_solid(f, (0.79, pipe_y, 0.7), (0.79, pipe_y, 0.74), 0.05, segments=12),
        ],
        keys=keys,
        predefined_type="ELECTRICACTUATOR",
    )
    s.add(
        "IfcSensor",
        "Niveausonde",
        [vertical_cylinder_solid(f, 1.04, pipe_y, 0.51, 0.03, 0.14, segments=10)],
        keys=keys,
        predefined_type="LEVELSENSOR",
    )
    s.add(
        "IfcUnitaryControlElement",
        "Steuerung-RSV",
        [box_solid(f, 0.0, 0.7, 1.25, 0.12, 1.05, 1.7), box_solid(f, 0.12, 0.8, 1.55, 0.14, 0.95, 1.63)],
        keys=keys,
        predefined_type="CONTROLPANEL",
    )

    cable_z = 1.95

    def cable(name: str, *points: tuple[float, float, float]) -> None:
        s.add("IfcCableSegment", name, polyline_solids(f, points, 0.015), predefined_type="CABLESEGMENT", thin=True, serves=keys)

    cable("Kabel-Motor", (0.79, pipe_y, 0.74), (0.79, pipe_y, 0.8), (0.79, 0.03, 0.8), (0.79, 0.03, cable_z), (0.03, 0.03, cable_z))
    cable("Kabel-Sonde", (1.04, pipe_y, 0.65), (1.04, pipe_y, 0.8), (1.04, 0.06, 0.8), (1.04, 0.06, cable_z - 0.04), (0.06, 0.06, cable_z - 0.04))
    cable("Kabel-Steuerung", (0.03, 0.03, cable_z), (0.03, 0.85, cable_z), (0.03, 0.85, 1.7))
    cable("Kabel-Steuerung-Sonde", (0.06, 0.06, cable_z - 0.04), (0.06, 0.9, cable_z - 0.04), (0.06, 0.9, 1.7))
    return s


# ---------------------------------------------------------------------------
# Hausanschlussraum: innerer Blitzschutz
# ---------------------------------------------------------------------------

def internal_lightning_protection(key: str = "d01-04-007-innere-blitzschutzanlagen") -> Scene:
    """Service entrance room: equipotential busbar (PAS) on the back wall, bonded to the pipe
    entries (side wall), the surge protective devices of the main distribution and the SPDs
    of the telecom entry.

    The foundation earth lug feeds the PAS from the floor; it is context, not part of ``key``.
    Bonding conductors run in lanes on the walls so they never cross.
    """
    s = corner_room("Hausanschlussraum", width=3.6, depth=1.8, height=2.6)
    f = s.ifc_file
    keys = (key,)
    wire_r, wall_y = 0.012, 0.03
    pas_top = 0.45

    def conductor(name: str, *points: tuple[float, float, float]) -> None:
        s.add("IfcCableSegment", name, polyline_solids(f, points, wire_r), keys=keys, predefined_type="CONDUCTORSEGMENT", thin=True)

    # Equipotential busbar: housing with a terminal per conductor; earth lug from the floor.
    terminals = {"Wasser": 0.95, "Gas": 1.0, "Heizung": 1.05, "Daten-2": 1.15, "Daten-1": 1.2, "HV": 1.28}
    s.add(
        "IfcElectricDistributionBoard",
        "PAS",
        [box_solid(f, 0.9, 0.0, 0.33, 1.33, 0.08, pas_top)]
        + [vertical_cylinder_solid(f, x, 0.04, pas_top, 0.015, 0.02, segments=8) for x in terminals.values()],
        keys=keys,
        object_type="Potentialausgleichsschiene",
    )
    s.add(
        "IfcBuildingElementProxy",
        "Fundamenterder-Anschlussfahne",
        [box_solid(f, 1.08, 0.0, -0.05, 1.12, 0.015, 0.33)],
        object_type="Anschlussfahne",
    )

    # Pipe entries through the side wall with bonding clamps right behind the wall.
    clamp_x = 0.25
    for name, y, r, lane in (("Wasser", 0.5, 0.045, 0.8), ("Gas", 0.9, 0.035, 0.86), ("Heizung", 1.3, 0.05, 0.92)):
        z = 0.5
        s.add("IfcPipeSegment", name, [pipe_solid(f, (-0.2, y, z), (0.75, y, z), r, segments=10)])
        s.add(
            "IfcValve",
            f"Absperrung-{name}",
            [box_solid(f, 0.42, y - r - 0.02, z - r - 0.02, 0.54, y + r + 0.02, z + r + 0.02), vertical_cylinder_solid(f, 0.48, y, z + r + 0.02, 0.012, 0.08, segments=8)],
            predefined_type="ISOLATING",
        )
        s.add(
            "IfcCableFitting",
            f"Erdungsbandschelle-{name}",
            [
                pipe_solid(f, (clamp_x - 0.02, y, z), (clamp_x + 0.02, y, z), r + 0.012, segments=14),
                box_solid(f, clamp_x - 0.02, y - 0.015, z + r, clamp_x + 0.02, y + 0.015, z + r + 0.03),
            ],
            keys=keys,
            predefined_type="CONNECTOR",
        )
        t = terminals[name]
        conductor(
            f"PA-{name}",
            (clamp_x, y, z + r + 0.03),
            (clamp_x, y, lane),
            (wall_y, y, lane),
            (wall_y, wall_y, lane),
            (t, wall_y, lane),
            (t, wall_y, pas_top + 0.02),
        )

    # Telecom entry: wall sleeve, cables down into small SPD boxes.
    s.add(
        "IfcBuildingElementProxy",
        "Kabeleinfuehrung",
        [pipe_solid(f, (x, 0.0, 1.8), (x, 0.06, 1.8), 0.04, segments=12) for x in (1.65, 1.85)],
        object_type="Kabeleinfuehrung",
    )
    s.add(
        "IfcCableSegment",
        "Telekom",
        [pipe_solid(f, (x, 0.05, 1.8), (x, 0.05, 1.45), 0.015, segments=6) for x in (1.65, 1.85)],
        predefined_type="CABLESEGMENT",
        thin=True,
    )
    s.add(
        "IfcProtectiveDevice",
        "UeSS-Daten",
        [box_solid(f, x - 0.06, 0.0, 1.25, x + 0.06, 0.09, 1.45) for x in (1.65, 1.85)],
        keys=keys,
        predefined_type="VARISTOR",
    )
    for name, x, lane in (("Daten-1", 1.65, 0.72), ("Daten-2", 1.85, 0.64)):
        conductor(f"PA-{name}", (x, wall_y, 1.25), (x, wall_y, lane), (terminals[name], wall_y, lane), (terminals[name], wall_y, pas_top + 0.02))

    # Main distribution, open: main switch, Type 1+2 SPD row on a PE bar, breakers below.
    x0 = 2.3
    _open_cabinet(s, "HV", x0, 0.9)
    s.add("IfcCableSegment", "Hauptzuleitung", [pipe_solid(f, (2.5, 0.25, 2.0), (2.5, 0.25, 2.6), 0.03, segments=8)], predefined_type="CABLESEGMENT", thin=True)
    s.add("IfcSwitchingDevice", "Hauptschalter", [box_solid(f, 2.4, 0.05, 1.3, 2.58, 0.3, 1.65)], predefined_type="SWITCHDISCONNECTOR")
    spd_x = [2.65 + i * 0.1 for i in range(4)]
    s.add(
        "IfcProtectiveDevice",
        "UeSS-T1T2",
        [box_solid(f, x, 0.05, 1.3, x + 0.09, 0.27, 1.6) for x in spd_x]
        + [box_solid(f, x + 0.02, 0.27, 1.5, x + 0.07, 0.29, 1.55) for x in spd_x],
        keys=keys,
        predefined_type="VARISTOR",
    )
    s.add("IfcElectricDistributionBoard", "PE-Schiene", [box_solid(f, 2.4, 0.1, 1.12, 3.1, 0.16, 1.17)], keys=keys, object_type="PE-Schiene")
    for i, x in enumerate(spd_x):
        conductor(f"PE-UeSS-{i + 1}", (x + 0.045, 0.16, 1.3), (x + 0.045, 0.16, 1.17))
    breakers = [
        box_solid(f, 2.45 + col * 0.16, 0.05, z, 2.58 + col * 0.16, 0.3, z + 0.25)
        for z in (0.35, 0.7)
        for col in range(4)
    ]
    s.add("IfcProtectiveDevice", "Leitungsschutzschalter", breakers, predefined_type="CIRCUITBREAKER")
    t = terminals["HV"]
    conductor(
        "PA-HV",
        (2.4, 0.13, 1.14),
        (2.37, 0.13, 1.14),
        (2.37, 0.13, 0.56),
        (2.25, 0.13, 0.56),
        (2.25, wall_y, 0.56),
        (t, wall_y, 0.56),
        (t, wall_y, pas_top + 0.02),
    )
    return s


# ---------------------------------------------------------------------------
# Schutzanlage: NEMP-Schutzschaltungen
# ---------------------------------------------------------------------------

def nemp_protection(key: str = "d01-04-008-schutzschaltungen-nemp-uberspannungsschutz") -> Scene:
    """Protected installation with 40 cm reinforced concrete walls; all cables enter through one
    steel entry plate with 360° shield glands. Bolted below it: the NEMP filter cabinet (door open,
    power filter cans over fast arresters) and a small filter box for telephone / data / control.

    Wide strips bond the plate and the housings to the bonding bar and to fixed earthing points
    on the wall rebar (dashed), which forms the shield.
    """
    width, depth, height, wall = 3.2, 2.0, 2.6, 0.4
    s = Scene.new("NEMP-Schutzraum", storey_name="UG")
    add_corner_room(s.ifc_file, body_context=s.body_context, storey=s.storey, width=width, depth=depth, wall_height=height, wall_thickness=wall)
    f = s.ifc_file
    keys = (key,)
    face = 0.006

    # Rebar mesh at both faces of the back wall.
    bars = []
    for y in (-0.05, -wall + 0.05):
        bars += [pipe_solid(f, (x, y, 0.0), (x, y, height), 0.008, segments=6) for x in (0.15 + 0.3 * i for i in range(10))]
        bars += [pipe_solid(f, (-wall, y, z), (width, y, z), 0.008, segments=6) for z in (0.15 + 0.3 * i for i in range(8))]
    s.add("IfcReinforcingBar", "Bewehrung-Rueckwand", bars, dotted=True, thin=True)

    # Single cable entry: steel plate with power glands (top row) and signal glands (bottom row).
    plate_x0, plate_x1, plate_z0, plate_z1 = 0.45, 1.7, 1.7, 2.2
    power_x, power_z = (0.6, 0.78, 0.96), 2.06
    signal_x, signal_z = (1.42, 1.5, 1.58), 1.9
    glands = [box_solid(f, plate_x0, 0.0, plate_z0, plate_x1, 0.025, plate_z1)]
    for xs, z, r in ((power_x, power_z, 0.035), (signal_x, signal_z, 0.02)):
        for x in xs:
            glands += [
                pipe_solid(f, (x, 0.025, z), (x, 0.05, z), r + 0.015, segments=12),
                pipe_solid(f, (x, 0.05, z), (x, 0.09, z), r, segments=12),
            ]
    s.add("IfcCableFitting", "Kabeldurchfuehrung", glands, keys=keys, predefined_type="ENTRY")

    # NEMP filter cabinet bolted to the plate: heavy steel housing, door swung open.
    cx0, cx1, cz0, cz1, cd, t = plate_x0, 1.25, 0.55, plate_z0, 0.4, 0.04
    can_y = 0.24
    s.add(
        "IfcElectricDistributionBoard",
        "NEMP-Filterschrank",
        [
            box_solid(f, cx0, 0.0, cz0, cx1, t, cz1),
            box_solid(f, cx0, 0.0, cz0, cx0 + t, cd, cz1),
            box_solid(f, cx1 - t, 0.0, cz0, cx1, cd, cz1),
            box_solid(f, cx0, 0.0, cz1 - t, cx1, cd, cz1),
            box_solid(f, cx0, 0.0, cz0, cx1, cd, cz0 + t),
            box_solid(f, cx0 - t, cd, cz0, cx0, cd + 0.65, cz1),
            box_solid(f, cx0 - t - 0.03, cd + 0.55, 1.05, cx0 - t, cd + 0.58, 1.2),
        ],
        object_type="NEMP-Filterschrank",
    )
    s.add(
        "IfcProtectiveDevice",
        "NEMP-Netzfilter",
        [vertical_cylinder_solid(f, x, can_y, 1.0, 0.07, 0.4, segments=18) for x in power_x]
        + [vertical_cylinder_solid(f, x, can_y, z, 0.018, 0.05, segments=8) for x in power_x for z in (0.95, 1.4)],
        keys=keys,
        object_type="NEMP-Netzfilter",
    )
    s.add(
        "IfcProtectiveDevice",
        "Ableiter",
        [box_solid(f, x - 0.045, t, 0.68, x + 0.045, 0.28, 0.88) for x in power_x],
        keys=keys,
        predefined_type="VARISTOR",
    )

    # Small filter box for telephone, data and control lines.
    sx0, sx1, sz0 = 1.38, 1.62, 1.15
    s.add(
        "IfcElectricDistributionBoard",
        "Signalfilterkasten",
        [
            box_solid(f, sx0, 0.0, sz0, sx1, 0.03, plate_z0),
            box_solid(f, sx0, 0.0, sz0, sx0 + 0.03, 0.14, plate_z0),
            box_solid(f, sx1 - 0.03, 0.0, sz0, sx1, 0.14, plate_z0),
            box_solid(f, sx0, 0.0, sz0, sx1, 0.14, sz0 + 0.03),
            box_solid(f, sx0, 0.0, plate_z0 - 0.03, sx1, 0.14, plate_z0),
        ],
        object_type="NEMP-Signalfilterkasten",
    )
    s.add(
        "IfcProtectiveDevice",
        "NEMP-Signalfilter",
        [box_solid(f, x - 0.035, 0.03, 1.3, x + 0.035, 0.13, 1.5) for x in signal_x],
        keys=keys,
        object_type="NEMP-Signalfilter",
    )

    def cable(name: str, *points: tuple[float, float, float], r: float = 0.015) -> None:
        s.add("IfcCableSegment", name, polyline_solids(f, points, r), predefined_type="CABLESEGMENT", thin=True)

    for i, x in enumerate(power_x):
        cable(f"Netz-{i + 1}", (x, 0.09, power_z), (x, 0.12, power_z), (x, 0.12, 1.55), (x, can_y, 1.55), (x, can_y, 1.45))
        cable(f"Filter-Ableiter-{i + 1}", (x, can_y, 0.95), (x, can_y, 0.88))
        lane_z = 0.64 - i * 0.03
        cable(f"Abgang-{i + 1}", (x, can_y, 0.68), (x, can_y, lane_z), (0.03, can_y, lane_z), (0.03, 1.1 + i * 0.12, lane_z), (0.03, 1.1 + i * 0.12, 0.75))
    for i, x in enumerate(signal_x):
        cable(f"Signal-{i + 1}", (x, 0.09, signal_z), (x, 0.11, signal_z), (x, 0.11, 1.5), r=0.008)
    s.add("IfcElectricDistributionBoard", "Unterverteilung", [box_solid(f, 0.0, 1.0, 0.75, 0.25, 1.5, 1.8)], predefined_type="DISTRIBUTIONBOARD")

    # Bonding: bar, fixed earthing points on the rebar, wide short strips.
    s.add(
        "IfcElectricDistributionBoard",
        "PA-Schiene",
        [box_solid(f, 1.3, 0.02, 0.33, 2.0, 0.05, 0.39)] + [box_solid(f, x, 0.0, 0.34, x + 0.03, 0.02, 0.38) for x in (1.34, 1.93)],
        keys=keys,
        object_type="Potentialausgleichsschiene",
    )
    fixed_points = ((0.2, 1.95), (2.25, 0.36))
    s.add(
        "IfcCableFitting",
        "Erdungsfestpunkt",
        [pipe_solid(f, (x, -0.05, z), (x, 0.02, z), 0.045, segments=14) for x, z in fixed_points],
        keys=keys,
        predefined_type="JUNCTION",
    )

    def strip(name: str, a: tuple[float, float, float], b: tuple[float, float, float]) -> None:
        vertical = a[0] == b[0]
        solid = duct_solid(f, a, b, 0.06, 0.012) if vertical else duct_solid(f, a, b, 0.012, 0.06)
        s.add("IfcCableSegment", name, [solid], keys=keys, predefined_type="CONDUCTORSEGMENT")

    strip("Band-Platte", (plate_x0, face, 1.95), (fixed_points[0][0], face, 1.95))
    strip("Band-Filterschrank-1", (1.2, face, cz0), (1.2, face, 0.33))
    strip("Band-Filterschrank-2", (1.17, face, 0.36), (1.3, face, 0.36))
    strip("Band-Signalfilter", (1.5, face, sz0), (1.5, face, 0.39))
    strip("Band-Bewehrung", (2.0, face, 0.36), (fixed_points[1][0], face, 0.36))
    return s


# ---------------------------------------------------------------------------
# Serverraum: Wassernebelloeschanlage
# ---------------------------------------------------------------------------

def water_mist_room(key: str = "d04-03-003-wassernebelloschanlage") -> Scene:
    """Server room with its water mist system: break tank and high-pressure pump unit by the side wall,
    control panel on the back wall; a high-pressure line with section valve feeds a nozzle row in the
    aisle behind the racks.

    The mist cones below the nozzles are dotted context.
    """
    s = corner_room("Serverraum")
    f = s.ifc_file
    keys = (key,)
    line_z, r, row_y = 2.75, 0.035, 1.2

    s.add(
        "IfcFurniture",
        "Serverschraenke",
        [box_solid(f, 3.0 + i * 0.65, 2.1, 0.0, 3.65 + i * 0.65, 3.1, 2.0) for i in range(5)],
        predefined_type="USERDEFINED",
        object_type="Serverschrank",
    )

    s.add("IfcTank", "Vorlagebehaelter", [vertical_cylinder_solid(f, 0.6, 3.5, 0.0, 0.4, 1.6, segments=20)], keys=keys, predefined_type="BREAKPRESSURE")
    s.add(
        "IfcPump",
        "Hochdruckpumpeneinheit",
        [
            box_solid(f, 0.15, 1.3, 0.0, 1.05, 2.6, 0.12),
            *(horizontal_cylinder(f, 0.25, 0.75, y, 0.4, 0.17, segments=16) for y in (1.65, 2.25)),
            *(box_solid(f, 0.75, y - 0.14, 0.2, 0.98, y + 0.14, 0.6) for y in (1.65, 2.25)),
            pipe_solid(f, (0.9, 1.45, 0.75), (0.9, 2.45, 0.75), 0.05, segments=12),
        ],
        keys=keys,
        predefined_type="SPLITCASE",
    )
    s.add(
        "IfcUnitaryControlElement",
        "Steuerung-Wassernebel",
        [box_solid(f, 1.25, 0.0, 1.0, 1.85, 0.25, 1.9), box_solid(f, 1.4, 0.25, 1.55, 1.7, 0.27, 1.7)],
        keys=keys,
        predefined_type="CONTROLPANEL",
    )

    nozzle_x = (3.3, 4.6, 5.9)
    s.add(
        "IfcPipeSegment",
        "Zulauf",
        polyline_solids(f, [(0.6, 3.1, 0.3), (0.6, 2.75, 0.3), (0.6, 2.75, 0.4), (0.6, 2.6, 0.4)], 0.04, segments=10),
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcPipeSegment",
        "Hochdruckleitung",
        polyline_solids(f, [(0.9, 1.45, 0.75), (0.9, row_y, 0.75), (0.9, row_y, line_z), (6.2, row_y, line_z)], r, segments=10),
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcValve",
        "Bereichsventil",
        [box_solid(f, 0.8, row_y - 0.1, 1.7, 1.0, row_y + 0.1, 1.95), vertical_cylinder_solid(f, 0.9, row_y, 1.95, 0.06, 0.12, segments=12)],
        keys=keys,
        predefined_type="ISOLATING",
    )
    s.add(
        "IfcFireSuppressionTerminal",
        "Duesen",
        [
            part
            for x in nozzle_x
            for part in (
                vertical_cylinder_solid(f, x, row_y, line_z - 0.14, 0.03, 0.14, segments=10),
                vertical_cylinder_solid(f, x, row_y, line_z - 0.24, 0.06, 0.1, segments=12),
            )
        ],
        keys=keys,
        predefined_type="SPRINKLER",
        thin=True,
    )
    s.add(
        "IfcBuildingElementProxy",
        "Spruehnebel",
        [frustum(f, x, row_y, line_z - 0.24, 1.0, (0.06, 0.06), (0.5, 0.5)) for x in nozzle_x],
        object_type="Wassernebel",
        dotted=True,
    )
    return s


# ---------------------------------------------------------------------------
# Lager brennbare Fluessigkeiten: Schaumloeschanlage
# ---------------------------------------------------------------------------

def foam_room(key: str = "d04-03-004-schaumloschanlage") -> Scene:
    """Store for flammable liquids with its foam system: the water supply passes an alarm valve
    into a proportioner fed from the foam concentrate tank; the foam solution line rises to the
    ceiling and feeds foam pourers above the drums on spill pallets. The tank stands by the side
    wall so it does not hide the alarm valve.

    The foam streams and the foam blanket over the drums are dotted context.
    """
    s = corner_room("Gefahrstofflager")
    f = s.ifc_file
    keys = (key,)
    line_y, line_z, main_y, main_z = 2.7, 2.75, 0.25, 0.9
    mixer_x0, mixer_x1, riser_x = 2.3, 2.8, 2.95
    tank_x, tank_y = 0.55, 1.6

    drums = []
    for px in (3.4, 4.8):
        drums.append(box_solid(f, px, 2.1, 0.0, px + 1.2, 3.3, 0.3))
        drums += [vertical_cylinder_solid(f, px + dx, 2.1 + dy, 0.3, 0.27, 0.88, segments=32) for dx in (0.3, 0.9) for dy in (0.3, 0.9)]
    s.add("IfcBuildingElementProxy", "Gebinde", drums, object_type="Gebinde")

    s.add(
        "IfcValve",
        "Alarmventilstation",
        [vertical_cylinder_solid(f, 0.6, main_y, main_z - 0.2, 0.11, 0.4, segments=16), box_solid(f, 0.71, 0.2, 0.95, 0.84, 0.3, 1.1)],
        keys=keys,
        predefined_type="CHECK",
    )
    s.add(
        "IfcTank",
        "Schaummitteltank",
        [vertical_cylinder_solid(f, tank_x, tank_y, 0.0, 0.4, 1.7, segments=32), vertical_cylinder_solid(f, tank_x, tank_y, 1.7, 0.08, 0.1, segments=32)],
        keys=keys,
        predefined_type="STORAGE",
    )
    s.add(
        "IfcValve",
        "Zumischer",
        [horizontal_cylinder(f, mixer_x0, mixer_x1, main_y, main_z, 0.09, segments=16)],
        keys=keys,
        predefined_type="MIXING",
    )
    s.add(
        "IfcUnitaryControlElement",
        "Steuerung-Schaum",
        [box_solid(f, 3.2, 0.0, 1.0, 3.8, 0.25, 1.9), box_solid(f, 3.38, 0.25, 1.55, 3.62, 0.27, 1.7)],
        keys=keys,
        predefined_type="CONTROLPANEL",
    )

    s.add(
        "IfcPipeSegment",
        "Wasserzulauf",
        [pipe_solid(f, (0.0, main_y, main_z), (mixer_x0, main_y, main_z), 0.05, segments=12)],
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcPipeSegment",
        "Schaummittelleitung",
        polyline_solids(
            f,
            [(tank_x + 0.4, tank_y, 0.3), (2.55, tank_y, 0.3), (2.55, tank_y, main_z), (2.55, main_y + 0.09, main_z)],
            0.025,
            segments=10,
        ),
        thin=True,
        serves=keys,
    )
    pourer_x = (3.7, 4.8, 5.9)
    s.add(
        "IfcPipeSegment",
        "Schaumloesungsleitung",
        polyline_solids(
            f,
            [(mixer_x1, main_y, main_z), (riser_x, main_y, main_z), (riser_x, main_y, line_z), (riser_x, line_y, line_z), (6.2, line_y, line_z)],
            0.045,
            segments=10,
        ),
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcFireSuppressionTerminal",
        "Schaumduesen",
        [
            part
            for x in pourer_x
            for part in (
                vertical_cylinder_solid(f, x, line_y, line_z - 0.15, 0.03, 0.15, segments=10),
                vertical_cylinder_solid(f, x, line_y, line_z - 0.33, 0.08, 0.18, segments=16),
            )
        ],
        keys=keys,
        predefined_type="SPRINKLER",
        thin=True,
    )
    s.add(
        "IfcBuildingElementProxy",
        "Schaumdecke",
        [
            box_solid(f, 3.25, 1.95, 0.0, 6.15, 3.45, 1.4),
            *(frustum(f, x, line_y, line_z - 0.33, 1.4, (0.08, 0.08), (0.35, 0.35)) for x in pourer_x),
        ],
        object_type="Schaum",
        dotted=True,
    )
    return s


# ---------------------------------------------------------------------------
# Lueftungszentrale
# ---------------------------------------------------------------------------

HUMIDIFIER = "befeuchter"
HEAT_RECOVERY = "warmeruckgewinner"
VIBRATION_ISOLATOR = "schwingungsisolator"


def air_handling_room(extra: str | None = None) -> Scene:
    """Air handling unit opened into sections; ducts with elbows, silencers and flexible connectors.

    ``extra``: ``HUMIDIFIER`` inserts a humidifier section fed by a steam generator,
    ``HEAT_RECOVERY`` a heat recovery section, ``VIBRATION_ISOLATOR`` sets the unit on
    spring isolators standing on base rails.
    """
    s = corner_room("Lueftungszentrale")
    f = s.ifc_file
    y0, y1 = 0.25, 1.35
    zb = 0.35 if extra == VIBRATION_ISOLATOR else 0.0
    z1 = zb + 1.6

    # Air flows from the intake (+X, near the outdoor-air wall duct) to the outlet at the side wall.
    sections = [
        ("IfcBuildingElementProxy", "Ausblaskammer", 0.65, None, {"object_type": "Ausblaskammer"}),
        ("IfcFan", "Ventilator", 1.0, None, {"predefined_type": "CENTRIFUGALFORWARDCURVED"}),
        ("IfcCoil", "Kuehler", 0.45, "register-heiz-kuhlregister", {"predefined_type": "WATERCOOLINGCOIL"}),
        ("IfcCoil", "Erhitzer", 0.45, "register-heiz-kuhlregister", {"predefined_type": "HYDRONICCOIL"}),
        ("IfcFilter", "Filter", 0.55, "filter", {"predefined_type": "AIRPARTICLEFILTER"}),
        ("IfcBuildingElementProxy", "Ansaugkammer", 0.7, None, {"object_type": "Ansaugkammer"}),
    ]
    if extra == HUMIDIFIER:
        sections.insert(2, ("IfcHumidifier", "Befeuchter", 0.6, HUMIDIFIER, {"predefined_type": "STEAMINJECTION"}))
    elif extra == HEAT_RECOVERY:
        sections.append(("IfcAirToAirHeatRecovery", "Waermerueckgewinnung", 0.5, HEAT_RECOVERY, {"predefined_type": "ROTARYWHEEL"}))
    spans: dict[str, tuple[float, float]] = {}
    xa = 0.3
    for ifc_class, name, length, key, attrs in sections:
        xb = xa + length
        spans[name] = (xa, xb)
        if ifc_class is not None:
            s.add(ifc_class, name, [box_solid(f, xa, y0, zb, xb, y1, z1)], keys=(key,) if key else (), **attrs)
        xa = xb

    ym = (y0 + y1) * 0.5
    if extra == HUMIDIFIER:
        xa, xb = spans["Befeuchter"]
        xc = (xa + xb) * 0.5
        s.add(
            "IfcHumidifier",
            "Dampferzeuger",
            [box_solid(f, 0.0, 2.3, 0.9, 0.3, 2.9, 1.8)],
            keys=(HUMIDIFIER,),
            predefined_type="ASSISTEDELECTRIC",
        )
        s.add(
            "IfcPipeSegment",
            "Dampfschlauch",
            polyline_solids(f, [(0.15, 2.3, 1.6), (0.15, 1.8, 1.6), (xc, 1.8, 1.6), (xc, y1, 1.2)], 0.03, segments=10),
            keys=(HUMIDIFIER,),
            thin=True,
        )
    elif extra == VIBRATION_ISOLATOR:
        x_end = xa
        s.add(
            "IfcBuildingElementProxy",
            "Grundrahmen",
            [box_solid(f, 0.3, y, 0.0, x_end, y + 0.1, 0.06) for y in (y0, y1 - 0.1)],
            object_type="Grundrahmen",
        )
        count = 6
        for i in range(count):
            x = 0.45 + i * (x_end - 0.6 - 0.45) / (count - 1)
            for j, y in enumerate((y0 + 0.05, y1 - 0.05)):
                spring = [
                    box_solid(f, x - 0.1, y - 0.08, 0.06, x + 0.1, y + 0.08, 0.1),
                    *(vertical_cylinder_solid(f, x, y, z, 0.075, 0.035, segments=16) for z in (0.12, 0.17, 0.22, 0.27)),
                    vertical_cylinder_solid(f, x, y, 0.1, 0.04, 0.21, segments=12),
                    box_solid(f, x - 0.1, y - 0.08, 0.31, x + 0.1, y + 0.08, zb),
                ]
                s.add("IfcVibrationIsolator", f"Federisolator-{i + 1}{'ab'[j]}", spring, keys=(VIBRATION_ISOLATOR,), predefined_type="SPRING")

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

    riser("ZU", sum(spans["Ausblaskammer"]) * 0.5, zb + 2.35, 0.55, silencer=True)
    riser("AUL", sum(spans["Ansaugkammer"]) * 0.5, zb + 1.85, 0.55, silencer=False)
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


OT_NETWORK = "d01-11-030-ot-netzwerke-schnittstellen-gateways"


def switchboard_room(time_switch: bool = False, ot_network: bool = False) -> Scene:
    """Main LV switchboard opened (breakers + trip units), MV switchgear, compensation, metering, CO2.

    ``time_switch`` puts a time switch on a DIN rail in the third row of the third LV field
    (key ``zeitsteuergerat``) in place of two breakers. ``ot_network`` adds an open network rack
    with switch, router and gateways (key ``OT_NETWORK``) and data cables to the field devices.
    """
    s = corner_room("Hauptverteilung")
    f = s.ifc_file

    # Cable tray loop along the walls with bends; cables drop into the open fields.
    tray_z = 2.45
    hs = ("i-032-hs-schaltanlage",)
    # The bend is one L-shaped piece with a chamfered inner corner; both
    # straight trays butt against its ends so no solids overlap.
    s.add(
        "IfcCableCarrierSegment",
        "Trasse-Rueckwand",
        [duct_solid(f, (0.9, 0.6, tray_z), (4.6, 0.6, tray_z), 0.4, 0.08)],
        serves=hs,
    )
    s.add(
        "IfcCableCarrierSegment",
        "Trasse-Seitenwand",
        [duct_solid(f, (0.4, 1.1, tray_z), (0.4, 3.6, tray_z), 0.4, 0.08)],
        serves=hs,
    )
    s.add(
        "IfcCableCarrierFitting",
        "Trassenbogen",
        [prism(f, [(0.2, 0.4), (0.9, 0.4), (0.9, 0.8), (0.75, 0.8), (0.6, 0.95), (0.6, 1.1), (0.2, 1.1)], tray_z - 0.04, tray_z + 0.04)],
        keys=("kabeltrassen-formteil",),
        predefined_type="BEND",
        serves=hs,
    )

    # LV main distribution: three open fields with breaker rows. Each feeder cable leaves
    # its field through a gland in the roof and is laid in the back-wall tray towards the
    # corner bend; every cable has its own lane so the runs never cross.
    cable_r = 0.02
    lay_z = tray_z + 0.04 + cable_r
    for i, x0 in enumerate((0.4, 1.15, 1.9)):
        _open_cabinet(s, f"HV-Feld-{i + 1}", x0, 0.7)
        breakers, trips = [], []
        for row, z in enumerate((0.45, 0.85, 1.25, 1.6)):
            for col in range(3):
                if time_switch and i == 2 and row == 2 and col < 2:
                    continue
                bx = x0 + 0.1 + col * 0.18
                breakers.append(box_solid(f, bx, 0.05, z, bx + 0.14, 0.3, z + 0.28))
                trips.append(box_solid(f, bx + 0.02, 0.3, z + 0.08, bx + 0.12, 0.36, z + 0.2))
        s.add("IfcProtectiveDevice", f"Leistungsschalter-{i + 1}", breakers, keys=("schutzeinrichtung",), predefined_type="CIRCUITBREAKER")
        s.add("IfcProtectiveDeviceTrippingUnit", f"Ausloeser-{i + 1}", trips, keys=("ausloseeinheit",), predefined_type="ELECTRONIC")
        xc = x0 + 0.35
        cables = []
        for j, dx in enumerate((-0.12, 0.0, 0.12)):
            x, lane_y = xc + dx, 0.45 + 0.04 * (3 * i + j)
            cables += polyline_solids(f, [(x, 0.3, 1.85), (x, 0.3, lay_z), (x, lane_y, lay_z), (0.5, lane_y, lay_z)], cable_r)
        s.add("IfcCableSegment", f"Kabel-{i + 1}", cables, keys=("kabel",), predefined_type="CABLESEGMENT", thin=True)
        s.add(
            "IfcCableFitting",
            f"Kabelverschraubung-{i + 1}",
            [
                box_solid(f, xc - 0.22, 0.16, 2.0, xc + 0.22, 0.44, 2.03),
                *(vertical_cylinder_solid(f, xc + dx, 0.3, 2.03, 0.065, 0.14, segments=12) for dx in (-0.12, 0.0, 0.12)),
            ],
            keys=("kabel-formteil",),
            predefined_type="ENTRY",
        )

    if time_switch:
        x0, z = 1.9, 1.25
        s.add("IfcDiscreteAccessory", "Hutschiene", [box_solid(f, x0 + 0.05, 0.05, z + 0.12, x0 + 0.65, 0.08, z + 0.16)], object_type="Hutschiene")
        s.add(
            "IfcElectricTimeControl",
            "Schaltuhr",
            [
                box_solid(f, x0 + 0.1, 0.05, z, x0 + 0.42, 0.34, z + 0.28),
                box_solid(f, x0 + 0.13, 0.34, z + 0.04, x0 + 0.39, 0.4, z + 0.24),
                pipe_solid(f, (x0 + 0.26, 0.4, z + 0.14), (x0 + 0.26, 0.44, z + 0.14), 0.08, segments=16),
            ],
            keys=("zeitsteuergerat",),
            predefined_type="TIMECLOCK",
        )

    # Compensation cabinet and feed-in meter cabinet on the back wall.
    s.add("IfcElectricFlowStorageDevice", "Kompensation", [box_solid(f, 2.75, 0.0, 0.0, 3.55, 0.6, 2.0)], keys=("i-015-blindstromkompensation",), predefined_type="CAPACITORBANK")
    s.add("IfcFlowMeter", "Einspeisezaehler", [box_solid(f, 3.75, 0.0, 0.8, 4.35, 0.3, 1.7)], keys=("i-020-einspeisezahler",), predefined_type="ENERGYMETER")

    # MV switchgear along the side wall.
    ms_fields = (1.3, 1.9, 2.5)
    s.add(
        "IfcSwitchingDevice",
        "MS-Schaltanlage",
        [box_solid(f, 0.0, y0, 0.0, 0.9, y0 + 0.55, 2.1) for y0 in ms_fields],
        keys=("i-032-hs-schaltanlage",),
        predefined_type="SWITCHDISCONNECTOR",
    )

    # Cables from compensation, feed-in meter and MV fields up to the trays.
    for name, solids, system in (
        ("Kabel-Kompensation", polyline_solids(f, [(3.15, 0.3, 2.0), (3.15, 0.3, lay_z), (3.15, 0.6, lay_z)], cable_r), "i-015-blindstromkompensation"),
        ("Kabel-Einspeisung", polyline_solids(f, [(4.05, 0.15, 1.7), (4.05, 0.15, lay_z), (4.05, 0.6, lay_z)], cable_r), "i-020-einspeisezahler"),
        ("Kabel-MS", [pipe_solid(f, (0.45, y0 + 0.275, 2.1), (0.45, y0 + 0.275, tray_z - 0.04), 0.025, segments=6) for y0 in ms_fields], "i-032-hs-schaltanlage"),
    ):
        s.add("IfcCableSegment", name, solids, keys=("kabel",), predefined_type="CABLESEGMENT", thin=True, serves=(system,))

    # CO2 extinguishing: cylinder bank in the front corner, pipe with ceiling nozzles.
    s.add(
        "IfcFireSuppressionTerminal",
        "CO2-Batterie",
        [vertical_cylinder_solid(f, 5.4 + (i % 3) * 0.32, 3.6 + (i // 3) * 0.32, 0.0, 0.13, 1.5, segments=12) for i in range(6)],
        keys=("i-017-co2-loschanlage",),
        object_type="CO2-Flaschenbatterie",
    )
    co2 = ("i-017-co2-loschanlage",)
    s.add("IfcPipeSegment", "CO2-Steig", [pipe_solid(f, (5.7, 3.75, 1.5), (5.7, 3.75, 2.75), 0.03)], serves=co2)
    s.add("IfcPipeSegment", "CO2-Verteilung", [pipe_solid(f, (5.7, 3.75, 2.75), (2.0, 3.75, 2.75), 0.03)], serves=co2)
    s.add(
        "IfcFireSuppressionTerminal",
        "CO2-Duesen",
        [vertical_cylinder_solid(f, x, 3.75, 2.55, 0.05, 0.2, segments=10) for x in (2.5, 3.7, 4.9)],
        keys=("i-017-co2-loschanlage",),
        predefined_type="SPRINKLER",
    )
    if ot_network:
        _ot_network(s, OT_NETWORK)
    return s


def _ot_network(s: Scene, key: str) -> None:
    """Open 19" rack right of the meter cabinet; data cables to the meter, compensation and the third LV field."""
    f = s.ifc_file
    keys = (key,)
    x0, x1, depth, height = 4.7, 5.35, 0.6, 2.0
    frame = [box_solid(f, x0, 0.0, 0.0, x1, 0.04, height), box_solid(f, x0, 0.0, height - 0.05, x1, depth, height), box_solid(f, x0, 0.0, 0.0, x1, depth, 0.08)]
    frame += [box_solid(f, x, depth - 0.05, 0.08, x + 0.05, depth, height - 0.05) for x in (x0, x1 - 0.05)]
    s.add("IfcBuildingElementProxy", "Netzwerkschrank", frame, keys=keys, object_type="19-Zoll-Rack")
    units = (
        ("Switch", 1.55, "NETWORKAPPLIANCE"),
        ("Router", 1.35, "ROUTER"),
        ("Gateway-Modbus", 1.1, "GATEWAY"),
        ("Gateway-BACnet", 0.9, "GATEWAY"),
        ("Firewall", 0.7, "NETWORKAPPLIANCE"),
    )
    for name, z, predefined in units:
        s.add("IfcCommunicationsAppliance", name, [box_solid(f, x0 + 0.06, 0.08, z, x1 - 0.06, depth - 0.06, z + 0.12)], keys=keys, predefined_type=predefined)
    lay_z = 2.6

    def data(name: str, *points: tuple[float, float, float]) -> None:
        s.add("IfcCableSegment", name, polyline_solids(f, points, 0.012), predefined_type="CABLESEGMENT", thin=True, serves=keys)

    data("Datenkabel-Zaehler", (4.85, 0.1, height), (4.85, 0.1, lay_z), (4.1, 0.1, lay_z), (4.1, 0.1, 1.7))
    data("Datenkabel-Kompensation", (4.95, 0.14, height), (4.95, 0.14, lay_z + 0.04), (3.3, 0.14, lay_z + 0.04), (3.3, 0.14, 2.0))
    data("Datenkabel-HV", (5.05, 0.18, height), (5.05, 0.18, lay_z + 0.08), (2.4, 0.18, lay_z + 0.08), (2.4, 0.18, 2.0))
