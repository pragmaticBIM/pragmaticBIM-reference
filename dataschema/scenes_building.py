"""Building vignettes: corridor, wall strip, kitchen, office ceiling, roof, hall, site."""

from __future__ import annotations

import math

from generators.covering import add_covering
from generators.mep_parts import box_solid, duct_solid, pipe_solid, vertical_cylinder_solid
from generators.mep_wall_devices import ELECTRO_WALL_LENGTH, generate_mep_wall_electro
from generators.parts import rect_polyline
from generators.roofing import DEFAULT_SLAB_THICKNESS, generate_roofing
from generators.slab import add_slab
from generators.structural_core import extrude_with_voids
from generators.wall import add_opening_filling, add_opening_in_wall, add_wall

from dataschema.geometry import annular_sector, frustum, octahedron, prism, tilted_panel
from dataschema.scene import Scene
from dataschema.scenes_rooms import corner_room, horizontal_cylinder


def framed_opening(
    s: Scene,
    host,
    name: str,
    *,
    wall_origin: tuple[float, float, float],
    wall_thickness: float,
    along: float,
    sill: float,
    width: float,
    height: float,
    ifc_class: str = "IfcDoor",
    predefined_type: str = "DOOR",
    direction_xy: tuple[float, float] = (1.0, 0.0),
):
    opening = add_opening_in_wall(
        s.ifc_file,
        host=host,
        name=f"{name}-Oeffnung",
        body_context=s.body_context,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=wall_thickness,
        wall_origin=wall_origin,
        direction_xy=direction_xy,
    )
    return add_opening_filling(
        s.ifc_file,
        opening=opening,
        name=name,
        body_context=s.body_context,
        storey=s.storey,
        along=along,
        sill=sill,
        clear_width=width,
        clear_height=height,
        wall_thickness=wall_thickness,
        wall_origin=wall_origin,
        direction_xy=direction_xy,
        ifc_class=ifc_class,
        predefined_type=predefined_type,
    )


def _floor(s: Scene, x0: float, y0: float, x1: float, y1: float, thickness: float = 0.25) -> None:
    add_slab(
        s.ifc_file,
        name="Bodenplatte",
        body_context=s.body_context,
        storey=s.storey,
        polyline=rect_polyline(x0, y0, x1, y1),
        thickness=thickness,
        z_bottom=-thickness,
    )


def _wall(s: Scene, name: str, origin, length: float, height: float, thickness: float, direction=(1.0, 0.0), predefined="SOLIDWALL"):
    return add_wall(
        s.ifc_file,
        name=name,
        body_context=s.body_context,
        storey=s.storey,
        origin=origin,
        length=length,
        height=height,
        thickness=thickness,
        direction_xy=direction,
        predefined_type=predefined,
    )


# ---------------------------------------------------------------------------
# Korridor: safety and security devices
# ---------------------------------------------------------------------------

CORRIDOR_LENGTH = 9.0
CORRIDOR_WIDTH = 2.4
CORRIDOR_HEIGHT = 3.0


def _wall_camera(f, base, *, normal, aim, pitch_deg: float = 15.0) -> list:
    """Bullet camera: wall plate, arm and a housing hung from the arm tip, pitched down along ``aim``.

    ``base`` is the arm axis on the wall face; ``normal`` points into the room.
    """
    x, y, z = base
    nx, ny = normal
    length = math.hypot(*aim)
    pitch = math.radians(pitch_deg)
    d = (aim[0] / length * math.cos(pitch), aim[1] / length * math.cos(pitch), -math.sin(pitch))
    arm, housing_w, housing_h, housing_l = 0.06, 0.13, 0.12, 0.30

    def out(dist: float) -> tuple[float, float, float]:
        return (x + nx * dist, y + ny * dist, z)

    hx, hy, _ = out(0.11)
    back = (hx, hy, z - arm * 0.5 - housing_h * 0.5 * math.cos(pitch))
    front = tuple(b + v * housing_l for b, v in zip(back, d))
    lens = tuple(p + v * 0.02 for p, v in zip(front, d))
    return [
        duct_solid(f, out(0.0), out(0.03), 0.12, 0.16),
        duct_solid(f, out(0.03), out(0.13), arm, arm),
        duct_solid(f, back, front, housing_w, housing_h),
        pipe_solid(f, front, lens, 0.04, segments=16),
    ]


def corridor(system: str | None = None) -> Scene:
    """Corridor with two doors; ``system`` limits the devices to that one system (default: all)."""

    def show(key: str) -> bool:
        return system is None or system == key

    s = Scene.new("Korridor")
    f = s.ifc_file
    t = 0.2
    _floor(s, -t, -t, CORRIDOR_LENGTH, CORRIDOR_WIDTH)
    origin = (-t, -t, 0.0)
    back = _wall(s, "Rueckwand", origin, CORRIDOR_LENGTH + t, CORRIDOR_HEIGHT, t)
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), CORRIDOR_WIDTH, CORRIDOR_HEIGHT, t, direction=(0.0, 1.0))

    door_1 = framed_opening(s, back, "Brandschutztuer", wall_origin=origin, wall_thickness=t, along=1.2, sill=0.0, width=1.0, height=2.1)
    s.tag(door_1, ("i-014-abschlusse", "i-079-el-zutrittskontrolle"))
    door_2 = framed_opening(s, back, "Zutrittstuer", wall_origin=origin, wall_thickness=t, along=5.2, sill=0.0, width=1.0, height=2.1)
    s.tag(door_2, ("i-079-el-zutrittskontrolle",))

    def wall_box(x0: float, z0: float, w: float, h: float, d: float = 0.06):
        return box_solid(f, x0, 0.0, z0, x0 + w, d, z0 + h)

    if show("i-014-abschlusse"):
        # Fire curtain housing under the slab plus guide rails on both walls.
        s.add(
            "IfcBuildingElementProxy",
            "Brandschutzvorhang",
            [box_solid(f, 3.6, 0.0, 2.65, 3.9, CORRIDOR_WIDTH, 2.95), box_solid(f, 3.65, 0.0, 0.0, 3.85, 0.06, 2.65)],
            keys=("i-014-abschlusse",),
            object_type="Brandschutzvorhang",
        )
    if show("i-002-notlichtanlage"):
        # Exit signs above both doors + emergency luminaires.
        s.add(
            "IfcLightFixture",
            "Fluchtwegkennzeichnung",
            [wall_box(1.45, 2.2, 0.5, 0.2, 0.08), wall_box(5.45, 2.2, 0.5, 0.2, 0.08)],
            keys=("i-002-notlichtanlage",),
            predefined_type="SECURITYLIGHTING",
        )
        s.add(
            "IfcLightFixture",
            "Notleuchte",
            [wall_box(3.0, 2.55, 0.35, 0.12, 0.1), box_solid(f, 0.0, 1.6, 2.55, 0.1, 1.95, 2.67)],
            keys=("i-002-notlichtanlage",),
            predefined_type="SECURITYLIGHTING",
        )
    if show("i-010-videouberwachung"):
        # Video cameras on brackets.
        s.add(
            "IfcAudioVisualAppliance",
            "Kamera",
            [
                *_wall_camera(f, (4.6, 0.0, 2.55), normal=(0.0, 1.0), aim=(-0.5, 1.0)),
                *_wall_camera(f, (0.0, 0.4, 2.55), normal=(1.0, 0.0), aim=(1.0, 0.3)),
            ],
            keys=("i-010-videouberwachung",),
            predefined_type="CAMERA",
            thin=True,
        )
    if show("i-025-evakuationsanlage"):
        s.add(
            "IfcAudioVisualAppliance",
            "Lautsprecher",
            [wall_box(2.6, 2.0, 0.25, 0.25, 0.1), wall_box(6.8, 2.0, 0.25, 0.25, 0.1)],
            keys=("i-025-evakuationsanlage",),
            predefined_type="SPEAKER",
        )
    if show("i-079-el-zutrittskontrolle"):
        s.add("IfcSensor", "Kartenleser", [wall_box(6.35, 1.05, 0.09, 0.14, 0.04)], keys=("i-079-el-zutrittskontrolle",), predefined_type="IDENTIFIERSENSOR")
    if show("d01-11-004-ruf-such-und-sprechanlage"):
        # Central unit with paging transmitter on the side wall; cable along the back wall to the
        # call/intercom stations beside the doors and two round speakers.
        paging = ("d01-11-004-ruf-such-und-sprechanlage",)
        cable_z, r = 2.75, 0.012
        s.add(
            "IfcCommunicationsAppliance",
            "Rufzentrale",
            [box_solid(f, 0.0, 1.0, 1.1, 0.14, 1.55, 1.8)],
            keys=paging,
            object_type="Rufzentrale",
        )
        s.add(
            "IfcCommunicationsAppliance",
            "Personensuchsender",
            [vertical_cylinder_solid(f, 0.07, 1.45, 1.8, 0.012, 0.3, segments=8)],
            keys=paging,
            predefined_type="ANTENNA",
            thin=True,
        )
        station_x = (2.33, 6.33)
        speaker_x = (3.5, 7.6)
        for i, x in enumerate(station_x, start=1):
            s.add(
                "IfcCommunicationsAppliance",
                f"Sprechstelle-{i}",
                [wall_box(x - 0.08, 1.2, 0.16, 0.26, 0.04)],
                keys=paging,
                object_type="Ruf- und Sprechstelle",
            )
        for i, x in enumerate(speaker_x, start=1):
            s.add(
                "IfcAudioVisualAppliance",
                f"Lautsprecher-{i}",
                [pipe_solid(f, (x, 0.0, 2.35), (x, 0.07, 2.35), 0.16, segments=32)],
                keys=paging,
                predefined_type="SPEAKER",
            )
        s.add(
            "IfcCableSegment",
            "Rufkabel",
            [
                pipe_solid(f, (0.08, 1.1, 1.8), (0.08, 1.1, cable_z), r, segments=6),
                pipe_solid(f, (0.08, 1.1, cable_z), (0.08, r, cable_z), r, segments=6),
                pipe_solid(f, (0.08, r, cable_z), (speaker_x[-1], r, cable_z), r, segments=6),
                *(pipe_solid(f, (x, r, cable_z), (x, r, 1.46), r, segments=6) for x in station_x),
                *(pipe_solid(f, (x, r, cable_z), (x, r, 2.51), r, segments=6) for x in speaker_x),
            ],
            predefined_type="CABLESEGMENT",
            thin=True,
            serves=paging,
        )
    if show("d01-11-005-lichtrufanlage"):
        # Nurse call: central unit on the side wall; cable along the back wall to a call light
        # above each room door and a call/reset button beside it.
        nurse_call = ("d01-11-005-lichtrufanlage",)
        cable_z, r = 2.75, 0.012
        s.add(
            "IfcCommunicationsAppliance",
            "Lichtrufzentrale",
            [box_solid(f, 0.0, 0.95, 1.2, 0.12, 1.45, 1.7)],
            keys=nurse_call,
            object_type="Lichtrufzentrale",
        )
        door_x = (1.5, 5.5)
        button_x = (2.27, 6.27)
        for i, (light, button) in enumerate(zip(door_x, button_x), start=1):
            s.add(
                "IfcAlarm",
                f"Zimmersignalleuchte-{i}",
                [wall_box(light - 0.14, 2.3, 0.28, 0.13, 0.1)],
                keys=nurse_call,
                predefined_type="LIGHT",
            )
            s.add(
                "IfcSwitchingDevice",
                f"Ruftaster-{i}",
                [wall_box(button - 0.05, 1.25, 0.1, 0.14, 0.035)],
                keys=nurse_call,
                predefined_type="MOMENTARYSWITCH",
            )
        s.add(
            "IfcCableSegment",
            "Lichtrufkabel",
            [
                pipe_solid(f, (0.06, 1.1, 1.7), (0.06, 1.1, cable_z), r, segments=6),
                pipe_solid(f, (0.06, 1.1, cable_z), (0.06, r, cable_z), r, segments=6),
                pipe_solid(f, (0.06, r, cable_z), (button_x[-1], r, cable_z), r, segments=6),
                *(pipe_solid(f, (x, r, cable_z), (x, r, 2.43), r, segments=6) for x in door_x),
                *(pipe_solid(f, (x, r, cable_z), (x, r, 1.39), r, segments=6) for x in button_x),
            ],
            predefined_type="CABLESEGMENT",
            thin=True,
            serves=nurse_call,
        )
    if show("d04-03-002-nassloschposten"):
        # Hose-reel cabinet, door closed with a glazed window so the reel and nozzle stay visible;
        # water-filled pipe through the side wall, along the back wall and down into the cabinet.
        hose = ("d04-03-002-nassloschposten",)
        x0, x1, z0, z1, depth, sheet = 3.0, 3.8, 0.9, 1.9, 0.25, 0.02
        wx0, wx1, wz0, wz1 = x0 + 0.08, x1 - 0.08, z0 + 0.1, z1 - 0.1
        door_y = depth + sheet
        reel_x, reel_z, pipe_z = (x0 + x1) / 2, 1.42, 2.7
        s.add(
            "IfcFireSuppressionTerminal",
            "Nassloeschposten",
            [
                box_solid(f, x0, 0.0, z0, x1, sheet, z1),
                box_solid(f, x0, 0.0, z0, x0 + sheet, depth, z1),
                box_solid(f, x1 - sheet, 0.0, z0, x1, depth, z1),
                box_solid(f, x0, 0.0, z0, x1, depth, z0 + sheet),
                box_solid(f, x0, 0.0, z1 - sheet, x1, depth, z1),
                box_solid(f, x0, depth, z0, wx0, door_y, z1),
                box_solid(f, wx1, depth, z0, x1, door_y, z1),
                box_solid(f, wx0, depth, z0, wx1, door_y, wz0),
                box_solid(f, wx0, depth, wz1, wx1, door_y, z1),
                box_solid(f, x1 - 0.06, door_y, 1.3, x1 - 0.035, door_y + 0.03, 1.5),
                pipe_solid(f, (reel_x, sheet, reel_z), (reel_x, 0.15, reel_z), 0.3, segments=32),
            ],
            keys=hose,
            predefined_type="HOSEREEL",
        )
        s.add(
            "IfcPlate",
            "Sichtfenster",
            [box_solid(f, wx0, depth + 0.008, wz0, wx1, door_y - 0.008, wz1)],
            dotted=True,
        )
        s.add(
            "IfcFireSuppressionTerminal",
            "Strahlrohr",
            [pipe_solid(f, (reel_x + 0.2, 0.2, 0.98), (reel_x + 0.2, 0.2, 1.3), 0.035, segments=32)],
            keys=hose,
            object_type="Strahlrohr",
            thin=True,
        )
        s.add(
            "IfcPipeSegment",
            "Loeschwasserleitung",
            [
                pipe_solid(f, (0.0, 0.08, pipe_z), (reel_x, 0.08, pipe_z), 0.03, segments=12),
                pipe_solid(f, (reel_x, 0.08, pipe_z), (reel_x, 0.08, z1), 0.03, segments=12),
            ],
            predefined_type="RIGIDSEGMENT",
            thin=True,
            serves=hose,
        )
    if show("d01-11-003-telefon-anlagen"):
        # PBX on the side wall; cable along the back wall to two wall phones, each above its outlet.
        phone = ("d01-11-003-telefon-anlagen",)
        cable_z, r = 2.75, 0.012
        s.add(
            "IfcCommunicationsAppliance",
            "Telefonzentrale",
            [box_solid(f, 0.0, 0.85, 1.2, 0.16, 1.45, 1.95)],
            keys=phone,
            object_type="Telefonzentrale",
        )
        phone_x = (3.3, 7.1)
        for i, x in enumerate(phone_x, start=1):
            s.add(
                "IfcAudioVisualAppliance",
                f"Wandtelefon-{i}",
                [
                    wall_box(x - 0.12, 1.2, 0.24, 0.36, 0.06),
                    box_solid(f, x - 0.04, 0.06, 1.24, x + 0.04, 0.1, 1.52),
                    box_solid(f, x - 0.065, 0.06, 1.22, x + 0.065, 0.13, 1.3),
                    box_solid(f, x - 0.065, 0.06, 1.46, x + 0.065, 0.13, 1.54),
                ],
                keys=phone,
                predefined_type="TELEPHONE",
            )
            s.add("IfcOutlet", f"Telefonsteckdose-{i}", [wall_box(x - 0.05, 0.95, 0.1, 0.1, 0.03)], keys=phone, predefined_type="TELEPHONEOUTLET")
        s.add(
            "IfcCableSegment",
            "Telefonkabel",
            [
                pipe_solid(f, (0.08, 1.15, 1.95), (0.08, 1.15, cable_z), r, segments=6),
                pipe_solid(f, (0.08, 1.15, cable_z), (0.08, r, cable_z), r, segments=6),
                pipe_solid(f, (0.08, r, cable_z), (phone_x[-1], r, cable_z), r, segments=6),
                *(pipe_solid(f, (x, r, cable_z), (x, r, 1.05), r, segments=6) for x in phone_x),
            ],
            predefined_type="CABLESEGMENT",
            thin=True,
            serves=phone,
        )
    if show("i-012-alarmmanagement"):
        # Alarm panel and flashing beacon on the side wall.
        s.add("IfcController", "Alarmzentrale", [box_solid(f, 0.0, 1.0, 1.1, 0.12, 1.5, 1.8)], keys=("i-012-alarmmanagement",))
        s.add("IfcAlarm", "Blitzleuchte", [vertical_cylinder_solid(f, 0.08, 1.25, 2.1, 0.07, 0.15, segments=12)], keys=("i-012-alarmmanagement",), predefined_type="LIGHT")
    if system is not None and system in _CORRIDOR_EXTRAS:
        _CORRIDOR_EXTRAS[system](s, (system,), (door_1, door_2))
    if show("i-009-personenvereinzelungsanlage"):
        # Turnstiles across the corridor end.
        turnstiles = []
        for y in (0.15, 0.95, 1.75):
            turnstiles.append(box_solid(f, 7.6, y, 0.0, 8.6, y + 0.22, 1.0))
            turnstiles.append(box_solid(f, 8.0, y + 0.22, 0.85, 8.05, y + 0.62, 0.9))
        s.add("IfcBuildingElementProxy", "Drehsperren", turnstiles, keys=("i-009-personenvereinzelungsanlage",), object_type="Personenvereinzelung")
    return s


def _corridor_cable(s: Scene, name: str, keys, *points: tuple[float, float, float], r: float = 0.012) -> None:
    f = s.ifc_file
    s.add("IfcCableSegment", name, [pipe_solid(f, a, b, r, segments=6) for a, b in zip(points, points[1:])], predefined_type="CABLESEGMENT", thin=True, serves=keys)


def _corridor_audiovisual(s: Scene, keys, doors) -> None:
    """Information display between the doors, two round speakers and a dome camera."""
    f = s.ifc_file
    s.add(
        "IfcAudioVisualAppliance",
        "Informationsbildschirm",
        [box_solid(f, 3.0, 0.0, 1.3, 4.3, 0.06, 2.05), box_solid(f, 3.55, 0.0, 1.1, 3.75, 0.04, 1.3)],
        keys=keys,
        predefined_type="DISPLAY",
    )
    s.add(
        "IfcAudioVisualAppliance",
        "Deckenlautsprecher",
        [pipe_solid(f, (x, 0.0, 2.45), (x, 0.08, 2.45), 0.15, segments=32) for x in (2.6, 7.4)],
        keys=keys,
        predefined_type="SPEAKER",
    )
    s.add(
        "IfcAudioVisualAppliance",
        "Domkamera",
        [box_solid(f, 0.0, 1.05, 2.5, 0.08, 1.25, 2.62), pipe_solid(f, (0.08, 1.15, 2.56), (0.22, 1.15, 2.56), 0.08, segments=20)],
        keys=keys,
        predefined_type="CAMERA",
    )


def _corridor_intercom(s: Scene, keys, doors) -> None:
    """Door stations beside both doors, electric strikes in the frames, indoor station and power supply on the side wall."""
    f = s.ifc_file
    cable_z = 2.75
    for i, x in enumerate((2.15, 6.15), start=1):
        s.add(
            "IfcCommunicationsAppliance",
            f"Tuerstation-{i}",
            [box_solid(f, x, 0.0, 1.2, x + 0.16, 0.04, 1.55), pipe_solid(f, (x + 0.08, 0.04, 1.45), (x + 0.08, 0.05, 1.45), 0.035, segments=16)],
            keys=keys,
            object_type="Gegensprechstelle",
        )
        s.add("IfcActuator", f"Tueroeffner-{i}", [box_solid(f, x - 0.2, 0.0, 1.0, x - 0.15, 0.04, 1.15)], keys=keys, predefined_type="ELECTRICACTUATOR")
    s.add(
        "IfcCommunicationsAppliance",
        "Innensprechstelle",
        [box_solid(f, 0.0, 1.0, 1.25, 0.05, 1.22, 1.6), box_solid(f, 0.05, 1.04, 1.3, 0.09, 1.1, 1.55)],
        keys=keys,
        object_type="Innensprechstelle",
    )
    s.add("IfcCommunicationsAppliance", "Sprechanlagenzentrale", [box_solid(f, 0.0, 1.6, 1.9, 0.12, 1.95, 2.3)], keys=keys, object_type="Gegensprechzentrale")
    _corridor_cable(
        s,
        "Sprechleitung",
        keys,
        (0.06, 1.75, 2.3),
        (0.06, 1.75, cable_z),
        (0.06, 0.012, cable_z),
        (6.23, 0.012, cable_z),
        (6.23, 0.012, 1.55),
    )
    _corridor_cable(s, "Sprechleitung-1", keys, (2.23, 0.012, cable_z), (2.23, 0.012, 1.55))
    _corridor_cable(s, "Innenstelle", keys, (0.03, 1.1, cable_z), (0.03, 1.1, 1.6))


def _corridor_security_control(s: Scene, keys, doors) -> None:
    """Security control panel with display on the side wall; door contacts, card reader, motion detector and camera on one bus."""
    f = s.ifc_file
    cable_z = 2.75
    s.add(
        "IfcUnitaryControlElement",
        "Sicherheitsleitstelle",
        [box_solid(f, 0.0, 0.8, 1.1, 0.15, 1.6, 1.9), box_solid(f, 0.15, 0.9, 1.45, 0.17, 1.5, 1.8)],
        keys=keys,
        predefined_type="CONTROLPANEL",
    )
    s.add(
        "IfcSensor",
        "Tuerkontakte",
        [box_solid(f, x - 0.08, 0.0, 2.13, x + 0.08, 0.04, 2.19) for x in (1.5, 5.5)],
        keys=keys,
        predefined_type="CONTACTSENSOR",
    )
    s.add("IfcSensor", "Badgeleser", [box_solid(f, 6.3, 0.0, 1.05, 6.39, 0.04, 1.19)], keys=keys, predefined_type="IDENTIFIERSENSOR")
    s.add("IfcSensor", "Bewegungsmelder", [box_solid(f, 8.6, 0.0, 2.4, 8.75, 0.1, 2.55)], keys=keys, predefined_type="MOVEMENTSENSOR")
    s.add(
        "IfcAudioVisualAppliance",
        "Kamera",
        _wall_camera(f, (4.6, 0.0, 2.55), normal=(0.0, 1.0), aim=(-0.5, 1.0)),
        keys=keys,
        predefined_type="CAMERA",
        thin=True,
    )
    _corridor_cable(s, "Sicherheitsbus", keys, (0.06, 1.2, 1.9), (0.06, 1.2, cable_z), (0.06, 0.012, cable_z), (8.68, 0.012, cable_z), (8.68, 0.012, 2.55))
    for i, (x, z) in enumerate(((1.5, 2.19), (5.5, 2.19), (6.345, 1.19), (4.6, 2.62)), start=1):
        _corridor_cable(s, f"Stich-{i}", keys, (x, 0.012, cable_z), (x, 0.012, z))


def _corridor_key_depot(s: Scene, keys, doors) -> None:
    """Closed electronic key depot: wall cabinet with a handle on its door and a display / PIN pad on the front."""
    f = s.ifc_file
    x0, x1, z0, z1, d = 3.2, 4.0, 0.95, 1.85, 0.15
    xc = (x0 + x1) * 0.5
    body = [
        box_solid(f, x0, 0.0, z0, x1, d, z1),
        box_solid(f, x0 + 0.02, d, z0 + 0.02, x1 - 0.02, d + 0.015, z1 - 0.02),
        box_solid(f, x0 + 0.06, d + 0.015, 1.25, x0 + 0.09, d + 0.05, 1.5),
    ]
    s.add("IfcBuildingElementProxy", "Schluesseldepot", body, keys=keys, object_type="Schluesseldepot elektronisch")
    s.add(
        "IfcSensor",
        "PIN-Leser",
        [box_solid(f, xc - 0.18, d + 0.015, 1.63, xc + 0.18, d + 0.035, 1.73), box_solid(f, xc - 0.06, d + 0.015, 1.3, xc + 0.06, d + 0.035, 1.45)],
        keys=keys,
        predefined_type="IDENTIFIERSENSOR",
    )
    _corridor_cable(s, "Depotleitung", keys, (xc, 0.012, z1), (xc, 0.012, 2.75), (0.06, 0.012, 2.75), (0.06, 0.012, 2.95))


def _corridor_extinguishers(s: Scene, keys, doors) -> None:
    """Two portable extinguishers on wall brackets, each with its sign above."""
    f = s.ifc_file
    for i, x in enumerate((3.4, 7.4), start=1):
        s.add(
            "IfcFireSuppressionTerminal",
            f"Handfeuerloescher-{i}",
            [
                vertical_cylinder_solid(f, x, 0.13, 0.55, 0.09, 0.55, segments=20),
                vertical_cylinder_solid(f, x, 0.13, 1.1, 0.03, 0.08, segments=10),
                box_solid(f, x - 0.02, 0.13, 1.14, x + 0.12, 0.17, 1.17),
                pipe_solid(f, (x + 0.06, 0.2, 1.1), (x + 0.12, 0.2, 0.75), 0.012, segments=6),
            ],
            keys=keys,
            predefined_type="USERDEFINED",
            object_type="Handfeuerloescher",
        )
        s.add("IfcBuildingElementProxy", f"Halterung-{i}", [box_solid(f, x - 0.05, 0.0, 0.9, x + 0.05, 0.05, 1.08)], keys=keys, object_type="Wandhalterung")
        s.add("IfcBuildingElementProxy", f"Kennzeichnung-{i}", [box_solid(f, x - 0.13, 0.0, 1.6, x + 0.13, 0.02, 1.86)], keys=keys, object_type="Brandschutzzeichen")


def _corridor_fire_door(s: Scene, keys, doors) -> None:
    """Fire door in the back wall."""
    s.tag(doors[0], keys)


def _corridor_locking(s: Scene, keys, doors) -> None:
    """Both doors with their locking cylinders, lever handles and escutcheons; key cabinet on the side wall."""
    f = s.ifc_file
    for door in doors:
        s.tag(door, keys)
    for i, x in enumerate((1.85, 5.85), start=1):
        s.add(
            "IfcDiscreteAccessory",
            f"Schliesszylinder-{i}",
            [
                box_solid(f, x - 0.025, 0.0, 0.85, x + 0.025, 0.03, 1.15),
                pipe_solid(f, (x, 0.0, 0.92), (x, 0.05, 0.92), 0.02, segments=14),
                box_solid(f, x - 0.15, 0.04, 1.03, x + 0.01, 0.07, 1.06),
            ],
            keys=keys,
            predefined_type="USERDEFINED",
            object_type="Schliesszylinder",
        )
    s.add("IfcBuildingElementProxy", "Schluesselschrank", [box_solid(f, 0.0, 0.9, 1.2, 0.12, 1.4, 1.75)], keys=keys, object_type="Schluesselschrank")


def _corridor_tube_post(s: Scene, keys, doors) -> None:
    """Pneumatic tube station on the back wall; tube up under the slab, through a diverter and off at the corridor end."""
    f = s.ifc_file
    x0, x1, z0, z1, d = 3.0, 3.55, 0.8, 1.55, 0.35
    xc = (x0 + x1) * 0.5
    tube_y, tube_z, r = 0.15, 2.7, 0.055
    s.add(
        "IfcBuildingElementProxy",
        "Rohrpoststation",
        [box_solid(f, x0, 0.0, z0, x1, d, z1), box_solid(f, x0 + 0.08, d, z0 + 0.1, x1 - 0.08, d + 0.04, z0 + 0.25), box_solid(f, x0 + 0.1, d, z1 - 0.25, x1 - 0.1, d + 0.02, z1 - 0.12)],
        keys=keys,
        object_type="Rohrpoststation",
    )
    s.add("IfcBuildingElementProxy", "Rohrpostbuechse", [horizontal_cylinder(f, xc - 0.12, xc + 0.12, d + 0.12, z0 + 0.06, 0.05, segments=14)], keys=keys, object_type="Rohrpostbuechse")
    s.add(
        "IfcPipeSegment",
        "Fahrrohr",
        [
            pipe_solid(f, (xc, tube_y, z1), (xc, tube_y, tube_z), r, segments=14),
            pipe_solid(f, (xc, tube_y, tube_z), (6.4, tube_y, tube_z), r, segments=14),
            pipe_solid(f, (6.8, tube_y, tube_z), (CORRIDOR_LENGTH, tube_y, tube_z), r, segments=14),
            pipe_solid(f, (6.6, tube_y, tube_z + 0.2), (6.6, tube_y, CORRIDOR_HEIGHT), r, segments=14),
        ],
        thin=True,
        serves=keys,
    )
    s.add(
        "IfcPipeFitting",
        "Rohrweiche",
        [box_solid(f, 6.4, tube_y - 0.1, tube_z - 0.1, 6.8, tube_y + 0.1, tube_z + 0.2)],
        keys=keys,
        predefined_type="JUNCTION",
    )


_CORRIDOR_EXTRAS = {
    "audiovisuelles-gerat": _corridor_audiovisual,
    "d01-11-031-gegensprechanlagen": _corridor_intercom,
    "d03-02-002-sicherheitsleitsysteme": _corridor_security_control,
    "d03-02-004-schlusseldepot-elektronisch": _corridor_key_depot,
    "d04-05-001-handfeuerloscher": _corridor_extinguishers,
    "g05-07-001-schliessanlage": _corridor_locking,
    "g05-07-002-sicherheits-und-brandschutzturen-mit-elektr-alarmkomponenten": _corridor_fire_door,
    "g05-07-016-brandschutzturen-tore-ohne-elektr-alarmkomponenten": _corridor_fire_door,
    "d12-02-003-rohrpostanlage": _corridor_tube_post,
}


# ---------------------------------------------------------------------------
# Gebaeudeeingang: security airlock in the facade
# ---------------------------------------------------------------------------

ENTRY_WIDTH = 7.0
ENTRY_DEPTH = 4.0
ENTRY_HEIGHT = 3.4
AIRLOCK_RADIUS = 0.9
AIRLOCK_HEIGHT = 2.6


def building_entry(key: str = "g05-07-008-schleusen-automatisch") -> Scene:
    """Facade seen from the forecourt with a round security airlock (one person at a time) and an escape door.

    The airlock is shown in the entry state: outer door slid open, inner door closed.
    """
    s = Scene.new("Gebaeudeeingang")
    f = s.ifc_file
    t = 0.3
    w, d, h = ENTRY_WIDTH, ENTRY_DEPTH, ENTRY_HEIGHT
    _floor(s, 0.0, -d, w + 1.0, 3.2)
    origin = (0.0, -t, 0.0)
    facade = _wall(s, "Fassade", origin, w, h, t)
    _wall(s, "Seitenwand", (w, -d, 0.0), d - t, h, t, direction=(0.0, 1.0))
    add_slab(f, name="Dach", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, -d, w, 0.0), thickness=0.25, z_bottom=h, predefined_type="ROOF")
    framed_opening(s, facade, "Fenster", wall_origin=origin, wall_thickness=t, along=0.5, sill=0.9, width=1.0, height=1.4, ifc_class="IfcWindow", predefined_type="WINDOW")
    framed_opening(s, facade, "Fluchttuer", wall_origin=origin, wall_thickness=t, along=5.2, sill=0.0, width=1.0, height=2.2)

    cx, cy, r = 3.4, 0.15, AIRLOCK_RADIUS
    add_opening_in_wall(
        f,
        host=facade,
        name="Schleuse-Oeffnung",
        body_context=s.body_context,
        along=cx - 0.89,
        sill=0.0,
        clear_width=1.78,
        clear_height=AIRLOCK_HEIGHT,
        wall_thickness=t,
        wall_origin=origin,
    )
    keys = (key,)
    leaf_top = AIRLOCK_HEIGHT - 0.3
    # Fixed shells left and right; door openings face the forecourt (90°) and the building (270°).
    s.add(
        "IfcBuildingElementProxy",
        "Rundschleuse",
        [
            vertical_cylinder_solid(f, cx, cy, 0.0, r + 0.02, 0.04, segments=32),
            vertical_cylinder_solid(f, cx, cy, leaf_top, r + 0.02, AIRLOCK_HEIGHT - leaf_top, segments=32),
            annular_sector(f, cx, cy, 0.04, leaf_top, r - 0.04, r, -45.0, 45.0),
            annular_sector(f, cx, cy, 0.04, leaf_top, r - 0.04, r, 135.0, 225.0),
        ],
        keys=keys,
        object_type="Personenschleuse",
    )
    s.add(
        "IfcDoor",
        "Schleusentuer-aussen",
        [annular_sector(f, cx, cy, 0.04, leaf_top, r - 0.09, r - 0.06, 140.0, 225.0)],
        keys=keys,
        predefined_type="DOOR",
    )
    s.add(
        "IfcDoor",
        "Schleusentuer-innen",
        [annular_sector(f, cx, cy, 0.04, leaf_top, r - 0.09, r - 0.06, 220.0, 320.0)],
        keys=keys,
        predefined_type="DOOR",
    )
    s.add("IfcSensor", "Ausweisleser", [box_solid(f, 4.6, 0.0, 1.0, 4.72, 0.05, 1.18)], keys=keys, predefined_type="IDENTIFIERSENSOR")
    return s


# ---------------------------------------------------------------------------
# Hallenfassade: automatic sectional gate for vehicles
# ---------------------------------------------------------------------------

GATE_FACADE_WIDTH = 12.0
GATE_FACADE_DEPTH = 6.0
GATE_FACADE_HEIGHT = 6.0
EXTERIOR_GATE = "e03-03-001-aussenwandtore-automatisch"


def gate_facade(key: str = EXTERIOR_GATE) -> Scene:
    """Hall facade seen from the forecourt with a large automatic sectional gate for vehicles.

    ``key`` tags the gate leaf, its drive and control inside, the photocells at the jambs,
    the warning light above, the induction loop in the driveway and the keypad post; the cables serve it.
    A personnel door and a window beside the gate give the scale.
    """
    s = Scene.new("Hallenfassade")
    f = s.ifc_file
    t = 0.3
    w, d, h = GATE_FACADE_WIDTH, GATE_FACADE_DEPTH, GATE_FACADE_HEIGHT
    _floor(s, 0.0, -d, w + 1.0, 6.5)
    origin = (0.0, -t, 0.0)
    facade = _wall(s, "Fassade", origin, w, h, t)
    _wall(s, "Seitenwand", (w, -d, 0.0), d - t, h, t, direction=(0.0, 1.0))
    add_slab(f, name="Dach", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, -d, w, 0.0), thickness=0.3, z_bottom=h, predefined_type="ROOF")
    framed_opening(s, facade, "Personentuer", wall_origin=origin, wall_thickness=t, along=8.2, sill=0.0, width=1.0, height=2.2)
    framed_opening(s, facade, "Fenster", wall_origin=origin, wall_thickness=t, along=9.9, sill=1.0, width=1.4, height=1.4, ifc_class="IfcWindow", predefined_type="WINDOW")

    gx0, gw, gh = 1.5, 5.0, 4.5
    gx1 = gx0 + gw
    add_opening_in_wall(f, host=facade, name="Tor-Oeffnung", body_context=s.body_context, along=gx0, sill=0.0, clear_width=gw, clear_height=gh, wall_thickness=t, wall_origin=origin)
    s.add("IfcBuildingElementProxy", "Zufahrt", [box_solid(f, gx0 - 0.3, 0.0, 0.0, gx1 + 0.3, 6.5, 0.02)], object_type="Zufahrt")

    keys = (key,)
    panel = gh / 6
    s.add(
        "IfcDoor",
        "Sektionaltor",
        [box_solid(f, gx0, -0.14, i * panel, gx1, -0.1, (i + 1) * panel - 0.03) for i in range(6)],
        keys=keys,
        predefined_type="GATE",
    )
    s.add(
        "IfcSensor",
        "Lichtschranken",
        [box_solid(f, x - 0.06, 0.0, 0.35, x + 0.06, 0.1, 0.6) for x in (gx0 - 0.2, gx1 + 0.2)],
        keys=keys,
        predefined_type="MOVEMENTSENSOR",
    )
    s.add(
        "IfcAlarm",
        "Warnleuchte",
        [box_solid(f, gx1 + 0.15, 0.0, gh + 0.2, gx1 + 0.45, 0.12, gh + 0.35), vertical_cylinder_solid(f, gx1 + 0.3, 0.12, gh + 0.35, 0.09, 0.2, segments=24)],
        keys=keys,
        predefined_type="LIGHT",
    )
    loop_x0, loop_x1, loop_y0, loop_y1, bar = gx0 + 0.8, gx1 - 0.8, 1.6, 4.0, 0.15
    s.add(
        "IfcSensor",
        "Induktionsschleife",
        [
            box_solid(f, loop_x0, loop_y0, 0.02, loop_x1, loop_y0 + bar, 0.035),
            box_solid(f, loop_x0, loop_y1 - bar, 0.02, loop_x1, loop_y1, 0.035),
            box_solid(f, loop_x0, loop_y0, 0.02, loop_x0 + bar, loop_y1, 0.035),
            box_solid(f, loop_x1 - bar, loop_y0, 0.02, loop_x1, loop_y1, 0.035),
        ],
        keys=keys,
        object_type="Induktionsschleife",
    )
    px, py = gx1 + 0.9, 3.5
    s.add(
        "IfcSwitchingDevice",
        "Codetaster",
        [box_solid(f, px - 0.06, py - 0.06, 0.0, px + 0.06, py + 0.06, 1.0), box_solid(f, px - 0.12, py - 0.1, 1.0, px + 0.12, py + 0.1, 1.35)],
        keys=keys,
        predefined_type="KEYPAD",
    )

    # Drive and control inside: shaft drive at the jamb, control box beside the gate.
    yi = -t
    s.add("IfcActuator", "Torantrieb", [box_solid(f, gx1 + 0.1, yi - 0.35, gh + 0.05, gx1 + 0.45, yi - 0.05, gh + 0.6)], keys=keys, predefined_type="ELECTRICACTUATOR")
    s.add("IfcController", "Torsteuerung", [box_solid(f, gx1 + 0.6, yi - 0.18, 1.2, gx1 + 1.1, yi, 1.9)], keys=keys)
    s.add(
        "IfcCableSegment",
        "Kabel-Torantrieb",
        [pipe_solid(f, (gx1 + 0.85, yi - 0.03, 1.9), (gx1 + 0.85, yi - 0.03, gh + 0.3), 0.02, segments=6), pipe_solid(f, (gx1 + 0.85, yi - 0.03, gh + 0.3), (gx1 + 0.45, yi - 0.03, gh + 0.3), 0.02, segments=6)],
        predefined_type="CABLESEGMENT",
        thin=True,
        serves=keys,
    )
    return s


# ---------------------------------------------------------------------------
# Zwei Raeume: automatic interior doors / gates
# ---------------------------------------------------------------------------

INTERIOR_DOOR = "g01-05-001-innenturen-automatisch"
INTERIOR_GATE = "g01-06-001-innentore-automatisch"


def automatic_interior_doors(key: str = INTERIOR_DOOR, gate: bool = False) -> Scene:
    """Two rooms side by side, each with an automatic bi-parting sliding door in the back wall.

    Leaves are shown half open in front of the wall; ``key`` tags the leaves, the drive header,
    the motion sensor and the push button (gates: also the warning light) of both doors.
    ``gate`` scales rooms and openings up to vehicle gates.
    """
    s = Scene.new("Innentore" if gate else "Innentueren")
    f = s.ifc_file
    if gate:
        room_w, d, h, t, tp = 8.5, 6.5, 5.5, 0.25, 0.2
        clear_w, clear_h, leaf_t, header_h = 3.6, 4.0, 0.08, 0.4
    else:
        room_w, d, h, t, tp = 4.0, 4.5, 3.0, 0.2, 0.12
        clear_w, clear_h, leaf_t, header_h = 1.4, 2.2, 0.04, 0.22
    w = 2 * room_w
    _floor(s, -t, -t, w, d)
    origin = (-t, -t, 0.0)
    back = _wall(s, "Rueckwand", origin, w + t, h, t)
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), d, h, t, direction=(0.0, 1.0))
    _wall(s, "Trennwand", (room_w + tp / 2, 0.0, 0.0), d, h, tp, direction=(0.0, 1.0), predefined="PARTITIONING")

    keys = (key,)
    half = clear_w / 2
    leaf_w = half + 0.05
    shift = 0.45 * half
    travel = half + leaf_w
    y0 = 0.03
    y1 = y0 + leaf_t
    # Doors sit at the low-x end of each room so the partition does not hide the second one.
    for i, room_x0 in enumerate((0.0, room_w), start=1):
        cx = room_x0 + travel + 0.3
        x0 = cx - half
        add_opening_in_wall(
            f,
            host=back,
            name=f"{'Tor' if gate else 'Tuer'}-{i}-Oeffnung",
            body_context=s.body_context,
            along=x0 - origin[0],
            sill=0.0,
            clear_width=clear_w,
            clear_height=clear_h,
            wall_thickness=t,
            wall_origin=origin,
        )
        if gate:
            panel = clear_h / 5
            leaves = [
                box_solid(f, lx0, y0, j * panel, lx0 + leaf_w, y1, (j + 1) * panel - 0.03)
                for lx0 in (cx - leaf_w - shift, cx + shift)
                for j in range(5)
            ]
        else:
            leaves = [box_solid(f, lx0, y0, 0.0, lx0 + leaf_w, y1, clear_h) for lx0 in (cx - leaf_w - shift, cx + shift)]
        s.add(
            "IfcDoor",
            f"{'Schiebetor' if gate else 'Schiebetuer'}-{i}",
            leaves,
            keys=keys,
            predefined_type="GATE" if gate else "DOOR",
        )
        header_d = y1 + 0.1
        s.add(
            "IfcActuator",
            f"{'Torantrieb' if gate else 'Tuerantrieb'}-{i}",
            [box_solid(f, cx - travel, 0.0, clear_h + 0.02, cx + travel, header_d, clear_h + 0.02 + header_h)],
            keys=keys,
            predefined_type="ELECTRICACTUATOR",
        )
        sensor = 0.18 if gate else 0.12
        s.add(
            "IfcSensor",
            f"Bewegungsmelder-{i}",
            [box_solid(f, cx - sensor, header_d, clear_h + 0.06, cx + sensor, header_d + 0.06, clear_h + 0.06 + sensor)],
            keys=keys,
            predefined_type="MOVEMENTSENSOR",
        )
        button = 0.2 if gate else 0.12
        bx = cx + travel + 0.25
        s.add(
            "IfcSwitchingDevice",
            f"Taster-{i}",
            [box_solid(f, bx, 0.0, 1.0, bx + button, 0.04, 1.0 + button * 1.4)],
            keys=keys,
            predefined_type="MOMENTARYSWITCH",
        )
        if gate:
            s.add(
                "IfcAlarm",
                f"Warnleuchte-{i}",
                [
                    box_solid(f, bx, 0.0, clear_h + 0.2, bx + 0.3, 0.12, clear_h + 0.35),
                    vertical_cylinder_solid(f, bx + 0.15, 0.12, clear_h + 0.35, 0.09, 0.2, segments=24),
                ],
                keys=keys,
                predefined_type="LIGHT",
            )
    return s


# ---------------------------------------------------------------------------
# Brandabschnitt: fire diamond in a fire compartment
# ---------------------------------------------------------------------------

COMPARTMENT_WIDTH = 6.0
COMPARTMENT_DEPTH = 4.5
COMPARTMENT_HEIGHT = 3.0


def fire_compartment(fire_object: bool = False) -> Scene:
    """Compartment with fire door, wall hydrant and extinguisher; dashed compartment volume, fire diamond inside.

    ``fire_object`` adds the Feuerwehr-Objekt cube (FireHydrant) next to the door.
    """
    s = Scene.new("Brandabschnitt")
    f = s.ifc_file
    t = 0.2
    w, d, h = COMPARTMENT_WIDTH, COMPARTMENT_DEPTH, COMPARTMENT_HEIGHT
    _floor(s, -t, -t, w, d)
    origin = (-t, -t, 0.0)
    back = _wall(s, "Rueckwand", origin, w + t, h, t)
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), d, h, t, direction=(0.0, 1.0))
    framed_opening(s, back, "Brandschutztuer", wall_origin=origin, wall_thickness=t, along=4.4, sill=0.0, width=1.0, height=2.1)

    s.add("IfcFireSuppressionTerminal", "Wandhydrant", [box_solid(f, 0.9, 0.0, 0.7, 1.7, 0.25, 1.9)], predefined_type="HOSEREEL")
    s.add(
        "IfcFireSuppressionTerminal",
        "Handfeuerloescher",
        [vertical_cylinder_solid(f, 0.12, 2.6, 0.6, 0.09, 0.55, segments=12), box_solid(f, 0.0, 2.55, 1.15, 0.05, 2.65, 1.3)],
        object_type="Handfeuerloescher",
    )
    s.add("IfcSpace", "Brandabschnitt", [box_solid(f, 0.0, 0.0, 0.0, w, d, h)], dotted=True)

    diamond = s.add("IfcSpace", "Feuer-Diamant", [octahedron(f, 3.3, 2.5, 1.5, 0.75, 1.0)], keys=("feuer-diamant",), predefined_type="USERDEFINED")
    diamond.ObjectType = "FIREDIAMOND"
    s.solid("feuer-diamant")

    if fire_object:
        s.add(
            "IfcBuildingElementProxy",
            "Feuerhydrant",
            [box_solid(f, 5.35, 0.05, 0.0, 5.85, 0.55, 0.5)],
            keys=("feuerwehr-objekt",),
            object_type="FEUERWEHROBJEKT",
        )
    return s


# ---------------------------------------------------------------------------
# Einsatzplan Feuerwehr: building on its site with fire-brigade areas
# ---------------------------------------------------------------------------

FIRE_BRIGADE_AREA_HEIGHT = 1.0


def fire_brigade_site(element: str) -> Scene:
    """Terrain, building volume and access road; ``element`` adds the 1 m clearance area or the assembly point."""
    s = Scene.new("Einsatzplan-Feuerwehr", storey_name="Terrain")
    f = s.ifc_file
    h = FIRE_BRIGADE_AREA_HEIGHT
    add_slab(f, name="Terrain", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, 0.0, 34.0, 26.0), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")
    s.add("IfcBuildingElementProxy", "Gebaeude", [box_solid(f, 3.0, 3.0, 0.0, 19.0, 13.0, 9.0)], object_type="Gebaeude")
    s.add("IfcBuildingElementProxy", "Zufahrt", [box_solid(f, 0.0, 20.0, 0.0, 34.0, 24.0, 0.05)], object_type="Strasse")

    if element == "freihalteflache-feuerwehr":
        s.add(
            "IfcBuildingElementProxy",
            "Freihaltefläche Feuerwehr",
            [box_solid(f, 5.0, 14.0, 0.0, 17.0, 20.0, h)],
            keys=("freihalteflache-feuerwehr",),
            object_type="FIREBRIGADE-DeploymentArea",
        )
        s.volume("freihalteflache-feuerwehr")
    elif element == "sammelplatz":
        point = s.add("IfcSpace", "Sammelplatz", [box_solid(f, 25.0, 6.0, 0.0, 31.0, 12.0, h)], keys=("sammelplatz",), predefined_type="USERDEFINED")
        point.ObjectType = "SAMMELPLATZ"
    elif element == "feuerwehr-zugang":
        # Entrance doors on the street facade; an arrow in front of each points at the door.
        for i, x in enumerate((7.0, 15.0), start=1):
            s.add("IfcDoor", f"Eingang-{i}", [box_solid(f, x - 0.6, 13.0, 0.0, x + 0.6, 13.15, 2.4)], predefined_type="DOOR")
            arrow = [(x, 13.5), (x + 1.0, 15.2), (x + 0.35, 15.2), (x + 0.35, 18.0), (x - 0.35, 18.0), (x - 0.35, 15.2), (x - 1.0, 15.2)]
            s.add(
                "IfcBuildingElementProxy",
                f"Feuerwehrzugang-{i}",
                [prism(f, arrow, 0.0, 0.5)],
                keys=("feuerwehr-zugang",),
                predefined_type="USERDEFINED",
                object_type="FEUERWEHRZUGANG",
            )
    else:
        raise ValueError(f"unknown fire-brigade element {element!r}")
    return s


# ---------------------------------------------------------------------------
# Wandabschnitt Elektro: home automation and junction box
# ---------------------------------------------------------------------------

def electro_wall(room_unit: bool = False) -> Scene:
    """Partition with door; switch, sockets, room controller, presence sensor, junction box.

    ``room_unit`` adds a room operating unit with temperature / CO2 sensor (key ``einheitsregler``).
    """
    s = Scene.new("Wandabschnitt-Elektro")
    f = s.ifc_file
    t, length, height = 0.12, 3.0, 2.6
    _floor(s, 0.0, -t, length, 1.1, thickness=0.2)
    origin = (0.0, -t, 0.0)
    wall = _wall(s, "Trennwand", origin, length, height, t, predefined="PARTITIONING")
    framed_opening(s, wall, "Innentuer", wall_origin=origin, wall_thickness=t, along=0.2, sill=0.0, width=0.9, height=2.1)

    def dev(x0: float, z0: float, w: float, h: float, d: float = 0.025):
        return box_solid(f, x0, 0.0, z0, x0 + w, d, z0 + h)

    x = 1.28
    s.add("IfcSwitchingDevice", "Taster", [dev(x, 1.0, 0.1, 0.1)], keys=("i-080-domotik",), predefined_type="MOMENTARYSWITCH")
    s.add("IfcOutlet", "Steckdosen", [dev(x, 0.25, 0.1, 0.1), dev(x + 0.1, 0.25, 0.1, 0.1)], predefined_type="POWEROUTLET")
    s.add("IfcController", "Raumcontroller", [dev(x - 0.02, 1.35, 0.14, 0.2, 0.03)], keys=("i-080-domotik",), predefined_type="PROGRAMMABLE")
    s.add("IfcSensor", "Praesenzmelder", [dev(x - 0.02, 2.15, 0.14, 0.14, 0.05)], keys=("i-080-domotik",), predefined_type="MOVEMENTSENSOR")
    s.add("IfcActuator", "Storenantrieb", [dev(0.3, 2.3, 0.18, 0.12, 0.05)], keys=("i-080-domotik",), predefined_type="ELECTRICACTUATOR")
    s.add("IfcJunctionBox", "Abzweigdose", [dev(0.85, 2.3, 0.12, 0.12, 0.04)], keys=("abzweigdose",), predefined_type="POWER")
    if room_unit:
        s.add(
            "IfcUnitaryControlElement",
            "Raumbediengeraet",
            [dev(2.0, 1.3, 0.16, 0.2, 0.03), box_solid(f, 2.03, 0.03, 1.4, 2.13, 0.035, 1.46), pipe_solid(f, (2.08, 0.03, 1.35), (2.08, 0.045, 1.35), 0.018, segments=12)],
            keys=("einheitsregler",),
            predefined_type="THERMOSTAT",
        )
    return s


def detector_line_wall() -> Scene:
    """Einbruchmeldeanlage wall (Reference ``mep-sensor`` system) with a junction box on the detector line.

    The line runs up from the detector into the box; from there one cable
    continues to the ceiling and a branch runs sideways along the wall.
    """
    ifc_file, _primary, _dotted, thin = generate_mep_wall_electro(
        {"project_name": "Wandabschnitt-Elektro", "highlight": "mep-sensor", "system": True}
    )
    s = Scene.wrap(ifc_file)
    s.thin.extend(thin)
    f = s.ifc_file
    # Detector line axis in generate_mep_wall_electro.
    line_x, line_y = 1.33, 0.012
    size, z0 = 0.12, 2.1
    s.add(
        "IfcJunctionBox",
        "Abzweigdose",
        [box_solid(f, line_x - size / 2, 0.0, z0, line_x + size / 2, 0.04, z0 + size)],
        keys=("abzweigdose",),
        predefined_type="POWER",
    )
    branch_z = z0 + size / 2
    s.add(
        "IfcCableSegment",
        "Abzweigleitung",
        [pipe_solid(f, (line_x + size / 2, line_y, branch_z), (ELECTRO_WALL_LENGTH, line_y, branch_z), 0.012, segments=6)],
        predefined_type="CABLESEGMENT",
        thin=True,
    )
    return s


# ---------------------------------------------------------------------------
# Kueche: electrical appliances and a fluid terminal
# ---------------------------------------------------------------------------

def kitchen(hood: str | None = None) -> Scene:
    """Kitchen wall with window, counter, fridge, oven, dishwasher, hob and gas outlet.

    ``hood`` adds the kitchen ventilation tagged with that key: extract hood over the hob, fan and
    duct through the outer wall to a weather grille, motorised make-up air flap in the wall.
    """
    s = Scene.new("Kueche")
    f = s.ifc_file
    t, ts, length, depth, height = 0.3, 0.12, 3.6, 2.6, 2.6
    _floor(s, -ts, -t, length, depth, thickness=0.2)
    origin = (-ts, -t, 0.0)
    wall = _wall(s, "Aussenwand", origin, length + ts, height, t)
    framed_opening(s, wall, "Fenster", wall_origin=origin, wall_thickness=t, along=ts + 1.6, sill=1.1, width=1.0, height=1.1, ifc_class="IfcWindow", predefined_type="WINDOW")
    _wall(s, "Seitenwand", (0.0, 0.0, 0.0), depth, height, ts, direction=(0.0, 1.0), predefined="PARTITIONING")

    s.add("IfcFurniture", "Kuechenzeile", [box_solid(f, 0.65, 0.0, 0.0, 3.5, 0.62, 0.9)], predefined_type="USERDEFINED", object_type="Einbaumöbel")
    s.add(
        "IfcElectricAppliance",
        "Haushaltgeraete",
        [
            box_solid(f, 0.0, 0.0, 0.0, 0.62, 0.65, 1.95),
            box_solid(f, 0.75, 0.62, 0.1, 1.35, 0.66, 0.72),
            box_solid(f, 2.85, 0.62, 0.1, 3.45, 0.66, 0.72),
            box_solid(f, 0.8, 0.05, 0.9, 1.3, 0.55, 0.93),
        ],
        keys=("elektrisches-gerat",),
        predefined_type="REFRIGERATOR",
    )
    s.add("IfcFlowTerminal", "Gasanschluss", [box_solid(f, 2.2, 0.0, 0.95, 2.42, 0.07, 1.15)], keys=("endgerat-fluid",))
    if hood:
        keys = (hood,)
        s.add(
            "IfcAirTerminal",
            "Dunstabzugshaube",
            [frustum(f, 1.05, 0.27, 1.85, 1.6, (0.2, 0.15), (0.32, 0.27)), box_solid(f, 0.9, 0.0, 1.85, 1.2, 0.27, 2.25)],
            keys=keys,
            predefined_type="USERDEFINED",
            object_type="Dunstabzugshaube",
        )
        s.add("IfcFan", "Abluftventilator", [box_solid(f, 0.85, 0.0, 2.25, 1.25, 0.32, 2.5)], keys=keys, predefined_type="CENTRIFUGALBACKWARDINCLINEDCURVED")
        s.add("IfcDuctSegment", "Fortluftkanal", [duct_solid(f, (1.05, 0.0, 2.4), (1.05, -t - 0.05, 2.4), 0.2, 0.16)], keys=keys, predefined_type="RIGIDSEGMENT")
        s.add("IfcAirTerminal", "Wetterschutzgitter", [box_solid(f, 0.9, -t - 0.08, 2.28, 1.2, -t - 0.02, 2.52)], keys=keys, predefined_type="GRILLE")
        s.add(
            "IfcDamper",
            "Nachstroemklappe",
            [box_solid(f, 3.0, 0.0, 2.1, 3.4, 0.06, 2.4)] + [box_solid(f, 3.0, 0.06, z, 3.4, 0.08, z + 0.03) for z in (2.15, 2.23, 2.31)],
            keys=keys,
            predefined_type="CONTROLDAMPER",
        )
        s.add("IfcActuator", "Klappenantrieb", [box_solid(f, 3.45, 0.0, 2.15, 3.55, 0.08, 2.35)], keys=keys, predefined_type="ELECTRICACTUATOR")
    return s


# ---------------------------------------------------------------------------
# Buero mit Abhangdecke: lamps and light distribution
# ---------------------------------------------------------------------------

def office_lighting(ghost_fixtures: bool = False, bus: str | None = None) -> Scene:
    """Dotted suspended ceiling with recessed luminaires; lamps and light cones below.

    ``ghost_fixtures`` draws the luminaire housings dotted so the lamps inside stay visible.
    ``bus`` adds a lighting bus tagged with that key: luminaires, bus line above the ceiling,
    bus controller, push button and presence sensor.
    """
    s = corner_room("Buero-Licht", width=5.0, depth=4.0)
    f = s.ifc_file
    ceiling_bottom = 2.62
    ceiling = add_covering(
        f,
        name="Abhangdecke",
        body_context=s.body_context,
        storey=s.storey,
        polyline=rect_polyline(0.0, 0.0, 5.0, 4.0),
        thickness=0.04,
        z_bottom=ceiling_bottom,
        predefined_type="CEILING",
    )
    s.dotted.append(ceiling)
    s.add("IfcFurniture", "Tisch", [box_solid(f, 1.2, 1.4, 0.7, 3.4, 2.4, 0.75)], predefined_type="TABLE")
    for x in (1.4, 3.2):
        s.add("IfcBuildingElementProxy", f"Tischbein-{x}", [box_solid(f, x - 0.03, 1.45, 0.0, x + 0.03, 2.35, 0.7)], object_type="Tischbein")

    bus_keys = (bus,) if bus else ()
    for cx, cy in ((1.6, 1.9), (3.4, 1.9)):
        s.add(
            "IfcLightFixture",
            f"Leuchte-{cx}",
            [box_solid(f, cx - 0.6, cy - 0.15, ceiling_bottom - 0.04, cx + 0.6, cy + 0.15, ceiling_bottom + 0.1)],
            keys=bus_keys,
            predefined_type="DIRECTIONSOURCE",
            dotted=ghost_fixtures,
        )
        s.add(
            "IfcLamp",
            f"Lampe-{cx}",
            [horizontal_cylinder(f, cx - 0.55, cx + 0.55, cy + dy, ceiling_bottom - 0.08, 0.035, segments=32) for dy in (-0.07, 0.07)],
            keys=("lampe",),
            predefined_type="FLUORESCENT",
        )
        s.add(
            "IfcBuildingElementProxy",
            f"Lichtkegel-{cx}",
            [frustum(f, cx, cy, ceiling_bottom - 0.1, 0.76, (0.55, 0.12), (0.95, 0.6))],
            keys=("lichtquelle",),
            object_type="Lichtquelle",
        )
    s.volume("lichtquelle")
    if bus:
        bus_z = ceiling_bottom + 0.2
        s.add("IfcController", "Bus-Controller", [box_solid(f, 4.1, 0.0, 1.5, 4.5, 0.1, 1.95)], keys=bus_keys, predefined_type="PROGRAMMABLE")
        s.add("IfcSwitchingDevice", "Bus-Taster", [box_solid(f, 4.25, 0.0, 1.05, 4.35, 0.025, 1.15)], keys=bus_keys, predefined_type="MOMENTARYSWITCH")
        s.add("IfcSensor", "Praesenzmelder", [vertical_cylinder_solid(f, 2.5, 1.0, ceiling_bottom - 0.05, 0.06, 0.05, segments=16)], keys=bus_keys, predefined_type="MOVEMENTSENSOR")
        line = [
            (4.3, 0.03, 1.95),
            (4.3, 0.03, bus_z),
            (4.3, 1.9, bus_z),
            (1.6, 1.9, bus_z),
        ]
        segments = [pipe_solid(f, a, b, 0.012, segments=6) for a, b in zip(line, line[1:])]
        segments += [pipe_solid(f, (x, 1.9, bus_z), (x, 1.9, ceiling_bottom + 0.1), 0.012, segments=6) for x in (1.6, 3.4)]
        segments += [pipe_solid(f, (2.5, 1.9, bus_z), (2.5, 1.0, bus_z), 0.012, segments=6), pipe_solid(f, (2.5, 1.0, bus_z), (2.5, 1.0, ceiling_bottom), 0.012, segments=6)]
        segments += [pipe_solid(f, (4.3, 0.03, 1.5), (4.3, 0.03, 1.15), 0.012, segments=6)]
        s.add("IfcCableSegment", "Busleitung", segments, predefined_type="CABLESEGMENT", thin=True, serves=bus_keys)
    return s


# ---------------------------------------------------------------------------
# Buero: mobile evaporative cooler
# ---------------------------------------------------------------------------

def mobile_cooler(key: str = "verdunstungskuhler") -> Scene:
    """Office with desk and chair; a mobile evaporative cooler on castors.

    The cooler stands free in the room, louvres facing the open corner.
    """
    s = corner_room("Buero-Kuehler", width=4.5, depth=3.5)
    f = s.ifc_file
    s.add("IfcFurniture", "Tisch", [box_solid(f, 0.3, 0.3, 0.7, 2.3, 1.1, 0.75)], predefined_type="TABLE")
    for x in (0.4, 2.2):
        s.add("IfcBuildingElementProxy", f"Tischbein-{x}", [box_solid(f, x - 0.03, 0.35, 0.0, x + 0.03, 1.05, 0.7)], object_type="Tischbein")
    s.add(
        "IfcFurniture",
        "Stuhl",
        [box_solid(f, 1.05, 1.35, 0.42, 1.55, 1.85, 0.47), box_solid(f, 1.05, 1.8, 0.47, 1.55, 1.85, 0.95), vertical_cylinder_solid(f, 1.3, 1.6, 0.0, 0.03, 0.42, segments=8)],
        predefined_type="CHAIR",
    )

    keys = (key,)
    x0, x1, y0, y1, zb, zt = 3.2, 3.65, 2.0, 2.35, 0.1, 1.1
    louvres = [box_solid(f, x0 + 0.06, y1, z, x1 - 0.06, y1 + 0.03, z + 0.03) for z in (0.6, 0.67, 0.74, 0.81, 0.88, 0.95)]
    castors = [vertical_cylinder_solid(f, x, y, 0.0, 0.035, zb, segments=10) for x in (x0 + 0.05, x1 - 0.05) for y in (y0 + 0.05, y1 - 0.05)]
    s.add(
        "IfcEvaporativeCooler",
        "Verdunstungskuehler",
        [
            box_solid(f, x0 - 0.02, y0 - 0.02, zb, x1 + 0.02, y1 + 0.02, 0.45),
            box_solid(f, x0, y0, 0.45, x1, y1, zt),
            box_solid(f, x0 + 0.1, y0 + 0.08, zt, x1 - 0.1, y1 - 0.08, zt + 0.03),
            *louvres,
            *castors,
            pipe_solid(f, (x0 + 0.06, y0 - 0.06, zt - 0.05), (x1 - 0.06, y0 - 0.06, zt - 0.05), 0.015, segments=8),
            box_solid(f, x0 + 0.04, y0 - 0.07, zt - 0.08, x0 + 0.07, y0, zt - 0.02),
            box_solid(f, x1 - 0.07, y0 - 0.07, zt - 0.08, x1 - 0.04, y0, zt - 0.02),
        ],
        keys=keys,
        predefined_type="DIRECTEVAPORATIVERIGIDMEDIAAIRCOOLER",
    )
    return s


# ---------------------------------------------------------------------------
# Dach: PV, solar thermal, flue terminal
# ---------------------------------------------------------------------------

ROOF_WIDTH = 7.0
ROOF_DEPTH = 5.0


def roof_energy() -> Scene:
    """Flat roof with PV rows and inverter, solar collectors with storage, chimney with flue terminal."""
    ifc_file, _roofing = generate_roofing({"project_name": "Dach-Energie", "slab_width": ROOF_WIDTH, "slab_depth": ROOF_DEPTH})
    s = Scene.wrap(ifc_file)
    f = ifc_file
    z0 = DEFAULT_SLAB_THICKNESS + 0.36

    # PV: three south-facing rows (left half, seen from the camera).
    for i, y in enumerate((1.4, 2.6, 3.8)):
        s.add("IfcBuildingElementProxy", f"Ballast-PV-{i}", [box_solid(f, 3.8, y - 0.9, DEFAULT_SLAB_THICKNESS, 6.6, y - 0.75, z0)], object_type="Unterkonstruktion")
        s.add(
            "IfcSolarDevice",
            f"PV-Reihe-{i + 1}",
            [tilted_panel(f, 3.8, 6.6, y, 0.9, z0, 0.35)],
            keys=("solargerat", "i-037-photovoltaikanlage"),
            predefined_type="SOLARPANEL",
        )
    s.add("IfcElectricFlowStorageDevice", "Wechselrichter", [box_solid(f, 6.2, 4.2, z0, 6.7, 4.5, z0 + 0.6)], keys=("i-037-photovoltaikanlage",), object_type="Wechselrichter")
    s.add(
        "IfcCableSegment",
        "DC-Kabel",
        [pipe_solid(f, (6.6, 0.5, z0 + 0.05), (6.6, 4.2, z0 + 0.05), 0.025, segments=6)],
        predefined_type="CABLESEGMENT",
        thin=True,
        serves=("i-037-photovoltaikanlage",),
    )
    # Solar thermal: two steeper collectors and a small storage tank.
    for i, y in enumerate((1.6, 3.0)):
        s.add("IfcBuildingElementProxy", f"Ballast-ST-{i}", [box_solid(f, 0.6, y - 1.0, DEFAULT_SLAB_THICKNESS, 2.6, y - 0.85, z0)], object_type="Unterkonstruktion")
        s.add(
            "IfcSolarDevice",
            f"Kollektor-{i + 1}",
            [tilted_panel(f, 0.6, 2.6, y, 0.9, z0, 0.7, thickness=0.09)],
            keys=("i-074-warmeerz-solar",),
            predefined_type="SOLARCOLLECTOR",
        )
    s.add("IfcPipeSegment", "Solarleitung", [pipe_solid(f, (2.6, 2.6, z0 + 0.2), (2.6, 4.2, z0 + 0.2), 0.03)], serves=("i-074-warmeerz-solar",))
    s.add("IfcTank", "Solarspeicher", [horizontal_cylinder(f, 0.6, 2.4, 4.3, z0 + 0.3, 0.3, segments=16)], keys=("i-074-warmeerz-solar",), predefined_type="STORAGE")
    # Chimney with flue terminal.
    s.add("IfcChimney", "Kamin", [box_solid(f, 3.05, 0.4, DEFAULT_SLAB_THICKNESS, 3.45, 0.8, 1.6)])
    s.add(
        "IfcStackTerminal",
        "Abgasterminal",
        [vertical_cylinder_solid(f, 3.25, 0.6, 1.6, 0.13, 0.35, segments=12), vertical_cylinder_solid(f, 3.25, 0.6, 1.95, 0.24, 0.05, segments=12)],
        keys=("dach-abgasterminal",),
        predefined_type="COWL",
    )
    return s


# ---------------------------------------------------------------------------
# Dach: radio mast
# ---------------------------------------------------------------------------

def roof_radio(key: str = "d01-11-006-funkanlage") -> Scene:
    """Flat roof with a ballasted mast carrying rod antennas, a transceiver cabinet and the coax run between them."""
    ifc_file, _roofing = generate_roofing({"project_name": "Dach-Funk", "slab_width": 5.0, "slab_depth": 4.0})
    s = Scene.wrap(ifc_file)
    f = ifc_file
    keys = (key,)
    zs = DEFAULT_SLAB_THICKNESS
    z0 = zs + 0.36
    cx, cy, mast_h, arm, arm_z = 2.4, 1.6, 3.6, 0.6, z0 + 3.2

    s.add("IfcBuildingElementProxy", "Dachausstieg", [box_solid(f, 0.4, 0.4, zs, 1.3, 1.3, z0 + 0.5)], object_type="Dachausstieg")
    # Mast foot: steel cross on four ballast blocks, struts to the mast.
    s.add(
        "IfcBuildingElementProxy",
        "Mastfuss",
        [
            *(box_solid(f, x - 0.2, y - 0.2, zs, x + 0.2, y + 0.2, z0 - 0.1) for x, y in ((cx - 0.8, cy), (cx + 0.8, cy), (cx, cy - 0.8), (cx, cy + 0.8))),
            box_solid(f, cx - 1.0, cy - 0.06, z0 - 0.1, cx + 1.0, cy + 0.06, z0),
            box_solid(f, cx - 0.06, cy - 1.0, z0 - 0.1, cx + 0.06, cy + 1.0, z0),
        ],
        keys=keys,
        object_type="Ballastfuss",
    )
    s.add(
        "IfcMember",
        "Antennenmast",
        [
            vertical_cylinder_solid(f, cx, cy, z0, 0.05, mast_h, segments=12),
            *(pipe_solid(f, (cx + dx, cy + dy, z0), (cx + dx * 0.08, cy + dy * 0.08, z0 + 1.1), 0.02, segments=6) for dx, dy in ((0.8, 0.0), (-0.8, 0.0), (0.0, 0.8), (0.0, -0.8))),
            pipe_solid(f, (cx - arm, cy, arm_z), (cx + arm, cy, arm_z), 0.025, segments=8),
            pipe_solid(f, (cx, cy - arm, arm_z), (cx, cy + arm, arm_z), 0.025, segments=8),
        ],
        keys=keys,
        predefined_type="POST",
        thin=True,
    )
    rods = [vertical_cylinder_solid(f, x, y, arm_z - 0.4, 0.035, 1.3, segments=8) for x, y in ((cx - arm, cy), (cx + arm, cy), (cx, cy - arm), (cx, cy + arm))]
    clamps = [box_solid(f, x - 0.05, y - 0.05, arm_z - 0.06, x + 0.05, y + 0.05, arm_z + 0.06) for x, y in ((cx - arm, cy), (cx + arm, cy), (cx, cy - arm), (cx, cy + arm))]
    s.add(
        "IfcCommunicationsAppliance",
        "Stabantennen",
        [*rods, *clamps, vertical_cylinder_solid(f, cx, cy, z0 + mast_h, 0.03, 1.4, segments=8)],
        keys=keys,
        predefined_type="ANTENNA",
        thin=True,
    )

    # Transceiver cabinet on a plinth; coax along the roof and up the mast.
    x0, x1, y0, y1 = 3.8, 4.5, 0.4, 0.9
    s.add("IfcBuildingElementProxy", "Sockel", [box_solid(f, x0 - 0.05, y0 - 0.05, zs, x1 + 0.05, y1 + 0.05, z0)], keys=keys, object_type="Sockel")
    s.add(
        "IfcCommunicationsAppliance",
        "Funkstation",
        [box_solid(f, x0, y0, z0, x1, y1, z0 + 1.3), box_solid(f, x0 - 0.05, y0 - 0.05, z0 + 1.3, x1 + 0.05, y1 + 0.05, z0 + 1.36)],
        keys=keys,
        object_type="Sende-/Empfangsanlage",
    )
    r, zc, xc = 0.016, z0 + 0.15, cx + 0.08
    yc = (y0 + y1) / 2
    s.add(
        "IfcCableSegment",
        "Koaxkabel",
        [
            pipe_solid(f, (x0, yc, zc), (xc, yc, zc), r, segments=6),
            pipe_solid(f, (xc, yc, zc), (xc, cy, zc), r, segments=6),
            pipe_solid(f, (xc, cy, zc), (xc, cy, arm_z), r, segments=6),
        ],
        predefined_type="CABLESEGMENT",
        thin=True,
        serves=keys,
    )
    return s


# ---------------------------------------------------------------------------
# Dach + Raum: antenna system
# ---------------------------------------------------------------------------

def antenna_system(key: str = "d01-11-007-antennenanlagen") -> Scene:
    """Cutaway: roof slab over the room corner with an antenna mast (Yagi, DAB rod, satellite dish);
    coax through a roof penetration to the amplifier / multiswitch on the back wall, then to TV outlets.
    """
    s = corner_room("Antennenanlage", width=3.6, depth=2.6, height=2.6)
    f = s.ifc_file
    keys = (key,)
    roof_x1, roof_y1, zr = 2.2, 1.6, 2.85
    add_slab(
        f,
        name="Dachplatte",
        body_context=s.body_context,
        storey=s.storey,
        polyline=rect_polyline(-0.2, -0.2, roof_x1, roof_y1),
        thickness=zr - 2.6,
        z_bottom=2.6,
        predefined_type="ROOF",
    )

    mx, my, mast_top = 1.0, 0.7, zr + 2.2
    s.add("IfcBuildingElementProxy", "Mastfuss", [box_solid(f, mx - 0.3, my - 0.3, zr, mx + 0.3, my + 0.3, zr + 0.08)], keys=keys, object_type="Ballastfuss")
    s.add(
        "IfcMember",
        "Antennenmast",
        [vertical_cylinder_solid(f, mx, my, zr + 0.08, 0.04, mast_top - zr - 0.08, segments=10)],
        keys=keys,
        predefined_type="POST",
        thin=True,
    )

    yagi_z = mast_top - 0.25
    yagi = [pipe_solid(f, (mx, my - 0.1, yagi_z), (mx, my + 0.95, yagi_z), 0.02, segments=6)]
    for i in range(6):
        y, half = my + 0.15 + i * 0.16, 0.3 - i * 0.03
        yagi.append(pipe_solid(f, (mx - half, y, yagi_z), (mx + half, y, yagi_z), 0.013, segments=6))
    yagi.append(pipe_solid(f, (mx, my, mast_top), (mx, my, mast_top + 0.45), 0.013, segments=6))
    s.add("IfcCommunicationsAppliance", "Antennen-UKW-DAB-TV", yagi, keys=keys, predefined_type="ANTENNA", thin=True)

    # Dish facing south (+X), so it reads in profile.
    dish_z = zr + 0.95
    n = tuple(v / math.hypot(0.8, -0.25, 0.55) for v in (0.8, -0.25, 0.55))
    up = tuple(u - n[2] * ni for u, ni in zip((0.0, 0.0, 1.0), n))
    up = tuple(u / math.hypot(*up) for u in up)
    c = (mx + 0.3, my - 0.1, dish_z)
    rim = tuple(ci - 0.33 * u for ci, u in zip(c, up))
    focus = tuple(ci + 0.45 * ni for ci, ni in zip(c, n))
    lnb_back = tuple(fi + 0.1 * ni for fi, ni in zip(focus, n))
    s.add(
        "IfcCommunicationsAppliance",
        "Satellitenschuessel",
        [
            pipe_solid(f, (mx, my, dish_z), c, 0.02, segments=8),
            pipe_solid(f, c, tuple(ci + 0.03 * ni for ci, ni in zip(c, n)), 0.4, segments=28),
            pipe_solid(f, rim, focus, 0.01, segments=6),
            pipe_solid(f, focus, lnb_back, 0.035, segments=12),
        ],
        keys=keys,
        predefined_type="ANTENNA",
        thin=True,
    )

    # Roof penetration; coax from the antennas down the mast, through the roof, to the amplifier.
    hood_x, hood_y = 1.9, 0.15
    s.add("IfcBuildingElementProxy", "Dachdurchfuehrung", [vertical_cylinder_solid(f, hood_x, hood_y, zr, 0.07, 0.25, segments=14)], object_type="Dachdurchfuehrung")

    def coax(name: str, *points: tuple[float, float, float]) -> None:
        s.add("IfcCableSegment", name, [pipe_solid(f, a, b, 0.012, segments=6) for a, b in zip(points, points[1:])], predefined_type="CABLESEGMENT", thin=True, serves=keys)

    amp_x0, amp_x1, amp_z0, amp_z1 = 2.4, 2.9, 1.5, 1.85
    for i, (top, dx) in enumerate(((yagi_z, 0.04), (dish_z, -0.04))):
        x = mx + dx
        xa = amp_x0 + 0.15 + i * 0.2
        coax(
            f"Koax-Dach-{i + 1}",
            (x, my + 0.04, top),
            (x, my + 0.04, zr + 0.12),
            (x, hood_y + dx, zr + 0.12),
            (hood_x, hood_y + dx, zr + 0.12),
            (hood_x, hood_y + dx, 2.5),
            (hood_x, 0.03, 2.5),
            (xa, 0.03, 2.5),
            (xa, 0.03, amp_z1),
        )
    s.add(
        "IfcAudioVisualAppliance",
        "Verstaerker-Multischalter",
        [box_solid(f, amp_x0, 0.0, amp_z0, amp_x1, 0.12, amp_z1)],
        keys=keys,
        predefined_type="AMPLIFIER",
    )

    outlet_back, outlet_side = (3.25, 0.35), (2.15, 0.35)
    s.add(
        "IfcOutlet",
        "TV-Anschlussdosen",
        [
            box_solid(f, outlet_back[0] - 0.05, 0.0, outlet_back[1] - 0.05, outlet_back[0] + 0.05, 0.04, outlet_back[1] + 0.05),
            box_solid(f, 0.0, outlet_side[0] - 0.05, outlet_side[1] - 0.05, 0.04, outlet_side[0] + 0.05, outlet_side[1] + 0.05),
        ],
        keys=keys,
        predefined_type="AUDIOVISUALOUTLET",
    )
    coax("Koax-Dose-1", (2.75, 0.03, amp_z0), (2.75, 0.03, 0.6), (outlet_back[0], 0.03, 0.6), (outlet_back[0], 0.03, outlet_back[1] + 0.05))
    coax("Koax-Dose-2", (2.55, 0.03, amp_z0), (2.55, 0.03, 0.15), (0.03, 0.03, 0.15), (0.03, outlet_side[0], 0.15), (0.03, outlet_side[0], outlet_side[1] - 0.05))
    s.add("IfcAudioVisualAppliance", "Fernseher", [box_solid(f, 0.0, 1.6, 0.9, 0.06, 2.5, 1.45)], predefined_type="DISPLAY")
    return s


# ---------------------------------------------------------------------------
# Dach + Raum: mechanical smoke and heat exhaust
# ---------------------------------------------------------------------------

def smoke_exhaust(key: str = "d04-06-001-maschinelle-rauch-und-warmeabzugsanlage", natural: bool = False) -> Scene:
    """Cutaway: roof slab over the room corner with a smoke extract fan on an upstand (discharge
    flaps open); smoke detector under the slab edge, RWA control panel with manual trigger,
    motorised supply-air flap low in the side wall for make-up air.

    ``natural`` replaces the fan by a smoke vent hatch, both flaps opened by electric spindle drives.
    """
    height = 3.0
    s = corner_room("MRWA", width=4.2, depth=3.2, height=height)
    f = s.ifc_file
    keys = (key,)
    roof_x1, roof_y1, zr = 2.6, 1.8, height + 0.25
    roof_outline = rect_polyline(-0.2, -0.2, roof_x1, roof_y1)
    fx, fy = 1.3, 0.8
    hw = 0.5
    if natural:
        clear = hw - 0.08
        s.add(
            "IfcSlab",
            "Dachplatte",
            [extrude_with_voids(f, roof_outline, [rect_polyline(fx - clear, fy - clear, fx + clear, fy + clear)], zr - height, z_bottom=height)],
            predefined_type="ROOF",
        )
    else:
        add_slab(
            f,
            name="Dachplatte",
            body_context=s.body_context,
            storey=s.storey,
            polyline=roof_outline,
            thickness=zr - height,
            z_bottom=height,
            predefined_type="ROOF",
        )

    if natural:
        # Smoke vent: upstand frame around the roof opening, two flaps opened by spindle drives.
        z_frame = zr + 0.35
        s.add(
            "IfcBuildingElementProxy",
            "Aufsatzkranz",
            [
                box_solid(f, fx - hw, fy - hw, zr, fx + hw, fy - hw + 0.08, z_frame),
                box_solid(f, fx - hw, fy + hw - 0.08, zr, fx + hw, fy + hw, z_frame),
                box_solid(f, fx - hw, fy - hw, zr, fx - hw + 0.08, fy + hw, z_frame),
                box_solid(f, fx + hw - 0.08, fy - hw, zr, fx + hw, fy + hw, z_frame),
            ],
            keys=keys,
            object_type="Aufsatzkranz",
        )
        flap = hw - 0.02
        s.add(
            "IfcWindow",
            "RWA-Klappe",
            [
                duct_solid(f, (fx, fy - hw, z_frame + 0.02), (fx, fy - hw - flap * 0.5, z_frame + 0.02 + flap * 0.87), 2 * hw, 0.03),
                duct_solid(f, (fx, fy + hw, z_frame + 0.02), (fx, fy + hw + flap * 0.5, z_frame + 0.02 + flap * 0.87), 2 * hw, 0.03),
            ],
            keys=keys,
            predefined_type="SKYLIGHT",
        )
        s.add(
            "IfcActuator",
            "Spindelantriebe",
            [
                pipe_solid(f, (x, fy - hw + 0.08, z_frame - 0.05), (x, fy - hw - flap * 0.3, z_frame + flap * 0.55), 0.03, segments=10)
                for x in (fx - 0.3, fx + 0.3)
            ]
            + [
                pipe_solid(f, (x, fy + hw - 0.08, z_frame - 0.05), (x, fy + hw + flap * 0.3, z_frame + flap * 0.55), 0.03, segments=10)
                for x in (fx - 0.3, fx + 0.3)
            ],
            keys=keys,
            predefined_type="ELECTRICACTUATOR",
        )
    else:
        # Smoke extract fan on an upstand: base plate, housing, open butterfly flaps.
        s.add("IfcBuildingElementProxy", "Aufsatzkranz", [box_solid(f, fx - 0.4, fy - 0.4, zr, fx + 0.4, fy + 0.4, zr + 0.3)], object_type="Aufsatzkranz")
        z_base = zr + 0.3
        z_top = z_base + 0.1 + 0.4
        flap = 0.3
        s.add(
            "IfcFan",
            "Brandgasventilator",
            [
                box_solid(f, fx - 0.45, fy - 0.45, z_base, fx + 0.45, fy + 0.45, z_base + 0.1),
                vertical_cylinder_solid(f, fx, fy, z_base + 0.1, 0.36, 0.4, segments=24),
                vertical_cylinder_solid(f, fx, fy, z_top, 0.38, 0.04, segments=24),
                duct_solid(f, (fx, fy - 0.01, z_top + 0.04), (fx, fy - 0.01 - flap * 0.5, z_top + 0.04 + flap * 0.87), 0.6, 0.012),
                duct_solid(f, (fx, fy + 0.01, z_top + 0.04), (fx, fy + 0.01 + flap * 0.5, z_top + 0.04 + flap * 0.87), 0.6, 0.012),
            ],
            keys=keys,
            predefined_type="VANEAXIAL",
            object_type="Brandgasventilator",
        )

    det_y = roof_y1 - 0.08
    s.add(
        "IfcSensor",
        "Rauchmelder",
        [vertical_cylinder_solid(f, fx, det_y, height - 0.1, 0.07, 0.1, segments=16)],
        keys=keys,
        predefined_type="SMOKESENSOR",
    )

    panel_x0, panel_x1, panel_z0, panel_z1 = 3.0, 3.5, 1.2, 1.8
    s.add("IfcUnitaryControlElement", "RWA-Zentrale", [box_solid(f, panel_x0, 0.0, panel_z0, panel_x1, 0.15, panel_z1)], keys=keys, predefined_type="CONTROLPANEL")
    s.add("IfcAlarm", "RWA-Taster", [box_solid(f, 3.75, 0.0, 1.35, 3.9, 0.06, 1.5)], keys=keys, predefined_type="BREAKGLASSBUTTON")

    # Make-up air: louvred flap with actuator, low in the side wall.
    fy0, fy1, fz0, fz1 = 2.3, 2.9, 0.3, 1.0
    louvre = [box_solid(f, 0.0, fy0, fz0, 0.06, fy1, fz0 + 0.04), box_solid(f, 0.0, fy0, fz1 - 0.04, 0.06, fy1, fz1)]
    louvre += [box_solid(f, 0.0, fy0, z, 0.08, fy1, z + 0.03) for z in (0.42, 0.54, 0.66, 0.78, 0.9)]
    louvre += [box_solid(f, 0.0, y, fz0, 0.06, y + 0.04, fz1) for y in (fy0, fy1 - 0.04)]
    s.add("IfcDamper", "Zuluftklappe", louvre, keys=keys, predefined_type="CONTROLDAMPER", object_type="Zuluftklappe")
    s.add("IfcActuator", "Klappenantrieb", [box_solid(f, 0.0, fy1 + 0.05, 0.55, 0.1, fy1 + 0.25, 0.75)], keys=keys, predefined_type="ELECTRICACTUATOR")

    def cable(name: str, *points: tuple[float, float, float]) -> None:
        s.add("IfcCableSegment", name, [pipe_solid(f, a, b, 0.012, segments=6) for a, b in zip(points, points[1:])], predefined_type="CABLESEGMENT", thin=True, serves=keys)

    cable_z = height - 0.12
    cable("Kabel-Ventilator", (3.2, 0.03, panel_z1), (3.2, 0.03, cable_z), (fx, 0.03, cable_z), (fx, 0.03, height))
    cable("Kabel-Melder", (3.3, 0.06, panel_z1), (3.3, 0.06, cable_z - 0.05), (fx + 0.1, 0.06, cable_z - 0.05), (fx + 0.1, det_y, cable_z - 0.05), (fx + 0.07, det_y, height - 0.1))
    cable("Kabel-Taster", (panel_x1, 0.03, 1.42), (3.75, 0.03, 1.42))
    cable("Kabel-Zuluft", (3.1, 0.03, panel_z0), (3.1, 0.03, 0.15), (0.03, 0.03, 0.15), (0.03, fy1 + 0.15, 0.15), (0.03, fy1 + 0.15, 0.55))
    return s


# ---------------------------------------------------------------------------
# Halle: crane runway and track
# ---------------------------------------------------------------------------

def hall(gate: str | None = None, gate_drive: bool = True) -> Scene:
    """Industrial hall corner with an overhead crane on runways and a rail track through the gate.

    ``gate`` adds a closed acoustic gate in the side wall where the track leaves, tagged with that key;
    ``gate_drive`` gives it a sliding drive with control box, otherwise a hand crank.
    """
    s = corner_room("Halle", width=12.0, depth=8.0, height=6.5)
    f = s.ifc_file
    if gate:
        _acoustic_gate(s, (gate,), gate_drive)
    crane = ("i-003-krananlagen",)
    for x in (2.0, 6.0, 10.0):
        s.add("IfcColumn", f"Stuetze-{x}", [box_solid(f, x - 0.15, 7.2, 0.0, x + 0.15, 7.5, 6.5)], predefined_type="COLUMN")
        s.add("IfcBuildingElementProxy", f"Konsole-{x}", [box_solid(f, x - 0.15, 7.0, 4.6, x + 0.15, 7.2, 4.9)], keys=crane, object_type="Kranbahnkonsole")
        s.add("IfcBuildingElementProxy", f"Wandkonsole-{x}", [box_solid(f, x - 0.15, 0.0, 4.6, x + 0.15, 0.4, 4.9)], keys=crane, object_type="Kranbahnkonsole")
    s.add("IfcBeam", "Kranbahn-1", [box_solid(f, 0.0, 0.15, 4.9, 12.0, 0.4, 5.3)], keys=crane, predefined_type="USERDEFINED", object_type="Kranbahntraeger")
    s.add("IfcBeam", "Kranbahn-2", [box_solid(f, 0.0, 7.0, 4.9, 12.0, 7.25, 5.3)], keys=crane, predefined_type="USERDEFINED", object_type="Kranbahntraeger")
    s.add("IfcBeam", "Kranbruecke", [box_solid(f, 5.0, 0.15, 5.3, 5.5, 7.25, 5.9), box_solid(f, 5.9, 0.15, 5.3, 6.4, 7.25, 5.9)], keys=crane, predefined_type="USERDEFINED", object_type="Kranbruecke")
    s.add("IfcBuildingElementProxy", "Laufkatze", [box_solid(f, 4.9, 3.4, 5.9, 6.5, 4.3, 6.3), pipe_solid(f, (5.7, 3.85, 5.3), (5.7, 3.85, 3.4), 0.03, segments=6)], keys=crane, object_type="Laufkatze")
    s.add("IfcBuildingElementProxy", "Lasthaken", [box_solid(f, 5.55, 3.7, 3.1, 5.85, 4.0, 3.4)], keys=crane, object_type="Lasthaken")

    # Track along X: sleepers + two rails.
    track = ("i-028-gleisanlagen",)
    for i in range(16):
        x = 0.4 + i * 0.75
        s.add("IfcBuildingElementProxy", f"Schwelle-{i}", [box_solid(f, x, 3.0, -0.0, x + 0.25, 5.6, 0.12)], keys=track, object_type="Schwelle")
    rail_x0 = 0.4 if gate else 0.0
    for y in (3.55, 5.05):
        s.add("IfcBuildingElementProxy", f"Schiene-{y}", [box_solid(f, rail_x0, y - 0.04, 0.12, 12.0, y + 0.04, 0.27)], keys=track, object_type="Schiene")
    s.add("IfcBuildingElementProxy", "Gueterwagen", [box_solid(f, 7.5, 3.2, 0.6, 11.5, 5.4, 2.8)], object_type="Gueterwagen")
    return s


def _acoustic_gate(s: Scene, keys, drive: bool) -> None:
    """Thick sliding acoustic gate on the inside of the side wall (x = 0), with seal frame and top track."""
    f = s.ifc_file
    y0, y1, top, thick = 3.0, 5.8, 4.2, 0.3
    panels = [box_solid(f, 0.02, y0 + i * 0.7, 0.0, 0.02 + thick, y0 + (i + 1) * 0.7 - 0.02, top) for i in range(4)]
    s.add("IfcDoor", "Schallschutztor", panels, keys=keys, predefined_type="GATE", object_type="Schallschutztor")
    s.add(
        "IfcBuildingElementProxy",
        "Dichtungsrahmen",
        [
            box_solid(f, 0.0, y0 - 0.15, 0.0, 0.02, y0, top + 0.15),
            box_solid(f, 0.0, y1, 0.0, 0.02, y1 + 0.15, top + 0.15),
            box_solid(f, 0.0, y0 - 0.15, top, 0.02, y1 + 0.15, top + 0.15),
        ],
        keys=keys,
        object_type="Dichtungsrahmen",
    )
    s.add("IfcMember", "Laufschiene", [box_solid(f, 0.0, 0.1, top + 0.15, 0.4, y1 + 0.2, top + 0.35)], keys=keys, predefined_type="MEMBER")
    if drive:
        s.add("IfcElectricMotor", "Torantrieb", [box_solid(f, 0.05, 0.5, top + 0.35, 0.45, 1.2, top + 0.7)], keys=keys)
        s.add("IfcController", "Torsteuerung", [box_solid(f, 0.0, y1 + 0.5, 1.2, 0.15, y1 + 0.9, 1.8)], keys=keys)
        s.add(
            "IfcCableSegment",
            "Kabel-Torantrieb",
            [pipe_solid(f, (0.05, y1 + 0.7, 1.8), (0.05, y1 + 0.7, top + 0.5), 0.02, segments=6), pipe_solid(f, (0.05, y1 + 0.7, top + 0.5), (0.05, 1.2, top + 0.5), 0.02, segments=6)],
            predefined_type="CABLESEGMENT",
            thin=True,
            serves=keys,
        )
    else:
        s.add(
            "IfcBuildingElementProxy",
            "Handkurbel",
            [
                box_solid(f, 0.0, y1 + 0.3, 1.1, 0.15, y1 + 0.6, 1.4),
                pipe_solid(f, (0.15, y1 + 0.45, 1.25), (0.3, y1 + 0.45, 1.25), 0.03, segments=10),
                pipe_solid(f, (0.3, y1 + 0.45, 1.25), (0.34, y1 + 0.45, 1.25), 0.2, segments=24),
                pipe_solid(f, (0.15, y1 + 0.45, 1.4), (0.15, y1 + 0.45, top + 0.15), 0.02, segments=6),
            ],
            keys=keys,
            object_type="Handkurbel",
        )
        s.add(
            "IfcBuildingElementProxy",
            "Torgriffe",
            [box_solid(f, 0.32, y1 - 0.15, 0.9, 0.38, y1 - 0.1, 1.6), box_solid(f, 0.32, y0 + 0.1, 0.9, 0.38, y0 + 0.15, 1.6)],
            keys=keys,
            object_type="Handgriff",
        )


# ---------------------------------------------------------------------------
# Einstellhalle: CO and diesel exhaust monitoring
# ---------------------------------------------------------------------------

def _parking_stacker(s: Scene, key: str, cx: float, y0: float, y1: float, top: float) -> None:
    """Two-level parking stacker: four posts with hydraulic cylinders and a raised upper platform."""
    f = s.ifc_file
    keys = (key,)
    x0, x1, zp = cx - 1.2, cx + 1.2, 1.75
    s.add(
        "IfcTransportElement",
        "Parkierplattform",
        [
            *(box_solid(f, x - 0.08, y - 0.08, 0.0, x + 0.08, y + 0.08, top) for x in (x0, x1) for y in (y0, y1)),
            box_solid(f, x0 + 0.08, y0, zp - 0.1, x1 - 0.08, y1, zp),
            *(box_solid(f, x - 0.04, y0, zp, x + 0.04, y1, zp + 0.1) for x in (x0 + 0.1, x1 - 0.1)),
            *(box_solid(f, x0, y - 0.08, top - 0.12, x1, y + 0.08, top) for y in (y0, y1)),
        ],
        keys=keys,
        predefined_type="USERDEFINED",
        object_type="Parkierplattform",
    )
    s.add(
        "IfcActuator",
        "Hydraulikzylinder",
        [pipe_solid(f, (x, y1 - 0.25, 0.0), (x, y1 - 0.25, zp - 0.1), 0.06, segments=14) for x in (x0 + 0.2, x1 - 0.2)],
        keys=keys,
        predefined_type="HYDRAULICACTUATOR",
    )
    s.add("IfcController", "Bedienpult", [box_solid(f, x0 - 0.6, 0.0, 1.0, x0 - 0.3, 0.15, 1.5)], keys=keys)


def parking_garage(key: str = "d04-02-002-co-und-dieselabgas-uberwachungsanlage", stacker_key: str | None = None) -> Scene:
    """Underground car park: gas sensors at breathing height, alarm panel, warning sign and beacon
    at the gate, and the control line to the exhaust fan.

    ``key`` tags the sensors, the panel and the warning devices; the cables serve it.
    ``stacker_key`` adds a two-level parking stacker tagged with that key (taller garage).
    """
    width, depth = 9.0, 7.5
    height = 3.6 if stacker_key else 2.8
    s = corner_room("Einstellhalle", width=width, depth=depth, height=height)
    f = s.ifc_file
    keys = (key,)
    cable_z = 2.65
    gate_y0, gate_y1, gate_h = 5.2, 7.2, 2.2

    s.add(
        "IfcBuildingElementProxy",
        "Parkfeldmarkierung",
        [box_solid(f, x - 0.05, 0.0, 0.0, x + 0.05, 5.0, 0.005) for x in (0.5, 3.0, 5.5, 8.0)],
        object_type="Bodenmarkierung",
        thin=True,
    )
    if stacker_key:
        _parking_stacker(s, stacker_key, 6.75, 0.3, 4.9, height - 0.3)
    s.add("IfcColumn", "Stuetze", [box_solid(f, 5.3, 5.0, 0.0, 5.7, 5.4, height)], predefined_type="COLUMN")
    s.add(
        "IfcDoor",
        "Garagentor",
        [box_solid(f, 0.0, gate_y0, i * gate_h / 4, 0.06, gate_y1, (i + 1) * gate_h / 4) for i in range(4)],
        predefined_type="GATE",
    )
    s.add(
        "IfcFan",
        "Abluftventilator",
        [
            box_solid(f, 1.35, 0.0, 1.95, 2.15, 0.25, 2.55),
            pipe_solid(f, (1.75, 0.25, 2.25), (1.75, 0.32, 2.25), 0.26, segments=32),
        ],
        predefined_type="PROPELLORAXIAL",
    )

    sensors = []
    for x in (4.25, 8.5):
        sensors += [
            box_solid(f, x - 0.13, 0.0, 1.5, x + 0.13, 0.12, 1.82),
            vertical_cylinder_solid(f, x, 0.07, 1.42, 0.05, 0.08, segments=24),
        ]
    for y in (2.5,):
        sensors += [
            box_solid(f, 0.0, y - 0.13, 1.5, 0.12, y + 0.13, 1.82),
            vertical_cylinder_solid(f, 0.07, y, 1.42, 0.05, 0.08, segments=24),
        ]
    s.add("IfcSensor", "CO-NO2-Melder", sensors, keys=keys, predefined_type="GASSENSOR")
    s.add(
        "IfcUnitaryControlElement",
        "Gaswarnzentrale",
        [box_solid(f, 0.0, 3.7, 1.1, 0.16, 4.3, 1.8), box_solid(f, 0.16, 3.82, 1.5, 0.18, 4.18, 1.68)],
        keys=keys,
        predefined_type="ALARMPANEL",
    )
    s.add("IfcAlarm", "Warntransparent", [box_solid(f, 0.0, 5.65, 2.3, 0.1, 6.65, 2.55)], keys=keys, predefined_type="LIGHT")
    s.add(
        "IfcAlarm",
        "Blitzleuchte",
        [box_solid(f, 0.0, 6.9, 2.3, 0.08, 7.1, 2.45), vertical_cylinder_solid(f, 0.12, 7.0, 2.45, 0.07, 0.14, segments=24)],
        keys=keys,
        predefined_type="SIREN",
    )

    def cable(name: str, *points: tuple[float, float, float]) -> None:
        s.add("IfcCableSegment", name, [pipe_solid(f, a, b, 0.018, segments=6) for a, b in zip(points, points[1:])], predefined_type="CABLESEGMENT", thin=True, serves=keys)

    cable("Melderkabel-Rueckwand", (8.5, 0.03, 1.82), (8.5, 0.03, cable_z), (0.03, 0.03, cable_z))
    cable("Melderkabel-Mitte", (4.25, 0.03, 1.82), (4.25, 0.03, cable_z))
    cable("Kabel-Seitenwand", (0.03, 0.03, cable_z), (0.03, 7.0, cable_z))
    cable("Melderkabel-Seitenwand", (0.03, 2.5, 1.82), (0.03, 2.5, cable_z))
    cable("Kabel-Zentrale", (0.03, 4.0, cable_z), (0.03, 4.0, 1.8))
    cable("Kabel-Warntransparent", (0.03, 6.15, cable_z), (0.03, 6.15, 2.55))
    cable("Kabel-Blitzleuchte", (0.03, 7.0, cable_z), (0.03, 7.0, 2.45))
    cable("Steuerkabel-Ventilator", (1.75, 0.03, cable_z), (1.75, 0.03, 2.55))
    return s


# ---------------------------------------------------------------------------
# Anlieferung: scissor lift in a pit between the yard and the loading dock
# ---------------------------------------------------------------------------

DOCK_WIDTH = 7.6
DOCK_DEPTH = 2.6
DOCK_HEIGHT = 1.2
YARD_DEPTH = 8.0
GROUND = 0.85
PIT_X0, PIT_X1, PIT_LENGTH, PIT_DEPTH = 3.0, 5.6, 3.2, 0.6


def delivery_dock(key: str = "i-013-anpassrampen") -> Scene:
    """Loading dock before a sectional gate; scissor lift in a pit in the yard at the foot of the dock.

    The lift (key ``key``) moves goods between the yard (truck level) and the dock;
    shown raised flush with the dock, its lip resting on the dock edge.
    """
    s = Scene.new("Anlieferung")
    f = s.ifc_file
    t, h = 0.3, 4.0
    x0, x1, length, depth = PIT_X0, PIT_X1, PIT_LENGTH, PIT_DEPTH
    y0, y1 = DOCK_DEPTH, DOCK_DEPTH + length
    keys = (key,)

    add_slab(f, name="Anlieferungsrampe", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(0.0, -t, DOCK_WIDTH, y0), thickness=GROUND + DOCK_HEIGHT, z_bottom=-GROUND)
    add_slab(
        f,
        name="Anlieferungsebene",
        body_context=s.body_context,
        storey=s.storey,
        polyline=[(0.0, y0), (x0, y0), (x0, y1), (x1, y1), (x1, y0), (DOCK_WIDTH, y0), (DOCK_WIDTH, YARD_DEPTH), (0.0, YARD_DEPTH)],
        thickness=GROUND,
        z_bottom=-GROUND,
    )
    add_slab(f, name="Grubensohle", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(x0, y0, x1, y1), thickness=GROUND - depth, z_bottom=-GROUND)
    origin = (0.0, -t, DOCK_HEIGHT)
    facade = _wall(s, "Fassade", origin, DOCK_WIDTH, h, t)

    gate_x, gate_w, gate_h = x0 - 0.1, x1 - x0 + 0.2, 3.0
    add_opening_in_wall(
        f,
        host=facade,
        name="Tor-Oeffnung",
        body_context=s.body_context,
        along=gate_x,
        sill=0.0,
        clear_width=gate_w,
        clear_height=gate_h,
        wall_thickness=t,
        wall_origin=origin,
    )
    panel = gate_h / 6
    s.add(
        "IfcDoor",
        "Sektionaltor",
        [box_solid(f, gate_x, -0.16, DOCK_HEIGHT + i * panel, gate_x + gate_w, -0.12, DOCK_HEIGHT + (i + 1) * panel - 0.02) for i in range(6)],
        predefined_type="GATE",
    )

    # Scissor lift: base frame on the pit floor, two scissor pairs, platform with bridging lip onto the dock.
    zb, zt = -depth + 0.15, DOCK_HEIGHT - 0.12
    ya, yb = y0 + 0.35, y1 - 0.35
    ym, zm = (ya + yb) / 2, (zb + zt) / 2
    scissors = []
    for x in (x0 + 0.3, x1 - 0.3):
        scissors.append(duct_solid(f, (x - 0.06, ya, zb), (x - 0.06, yb, zt), 0.1, 0.1))
        scissors.append(duct_solid(f, (x + 0.06, ya, zt), (x + 0.06, yb, zb), 0.1, 0.1))
    for y, z in ((ya, zb), (yb, zb), (ya, zt), (yb, zt), (ym, zm)):
        scissors.append(horizontal_cylinder(f, x0 + 0.2, x1 - 0.2, y, z, 0.04, segments=10))
    s.add(
        "IfcTransportElement",
        "Scherenhubtisch",
        [
            box_solid(f, x0 + 0.15, y0 + 0.2, -depth, x1 - 0.15, y1 - 0.2, -depth + 0.1),
            *scissors,
            pipe_solid(f, ((x0 + x1) / 2, yb - 0.3, zb), ((x0 + x1) / 2, ym, zm), 0.07, segments=12),
            box_solid(f, x0 + 0.05, y0 + 0.05, DOCK_HEIGHT - 0.12, x1 - 0.05, y1 - 0.05, DOCK_HEIGHT),
            box_solid(f, x0 + 0.15, y0 - 0.4, DOCK_HEIGHT, x1 - 0.15, y0 + 0.1, DOCK_HEIGHT + 0.03),
        ],
        keys=keys,
        predefined_type="LIFTINGGEAR",
    )
    s.add("IfcController", "Bedientableau", [box_solid(f, x1 + 0.6, 0.0, DOCK_HEIGHT + 1.0, x1 + 0.9, 0.12, DOCK_HEIGHT + 1.45)], keys=keys)
    pz = DOCK_HEIGHT
    s.add("IfcBuildingElementProxy", "Palette", [box_solid(f, 3.9, y1 - 1.6, pz, 4.7, y1 - 0.4, pz + 0.15), box_solid(f, 3.95, y1 - 1.55, pz + 0.15, 4.65, y1 - 0.45, pz + 1.0)], object_type="Palette")

    # Stair from the yard up to the dock.
    rise, tread, steps = DOCK_HEIGHT / 6, 0.28, 6
    s.add(
        "IfcStair",
        "Rampentreppe",
        [box_solid(f, 0.4, y0, 0.0, 1.4, y0 + (steps - i) * tread, (i + 1) * rise) for i in range(steps - 1)],
        predefined_type="STRAIGHT_RUN_STAIR",
    )
    return s


# ---------------------------------------------------------------------------
# Gelaende: wind and hydro power
# ---------------------------------------------------------------------------

def site_power(plant: str = "all") -> Scene:
    """Terrain with a farm building, a wind turbine and a small hydro plant on a sunk channel.

    ``plant="hydro"`` leaves out the wind turbine and the farm and crops the site to the channel.
    """
    s = Scene.new("Gelaende", storey_name="Terrain")
    f = s.ifc_file
    hydro_only = plant == "hydro"
    x0, x1, y0 = (6.0, 34.0, 11.0) if hydro_only else (0.0, 40.0, 0.0)
    # Terrain split along the channel so the trough stays open.
    for i, (ya, yb) in enumerate(((y0, 17.0), (22.0, 26.0)), start=1):
        add_slab(f, name=f"Terrain-{i}", body_context=s.body_context, storey=s.storey, polyline=rect_polyline(x0, ya, x1, yb), thickness=0.4, z_bottom=-0.4, predefined_type="BASESLAB")

    if not hydro_only:
        s.add("IfcBuildingElementProxy", "Gebaeude", [box_solid(f, 3.0, 3.0, 0.0, 13.0, 10.0, 6.0)], object_type="Gebaeude")
        wind = ("i-068-windkraftwerke",)
        tx, ty = 30.0, 7.0
        s.add("IfcBuildingElementProxy", "Turm", [vertical_cylinder_solid(f, tx, ty, 0.0, 1.0, 24.0, segments=16)], keys=wind, object_type="Turm")
        s.add("IfcBuildingElementProxy", "Gondel", [box_solid(f, tx - 1.0, ty - 3.0, 24.0, tx + 1.0, ty + 1.5, 26.0)], keys=wind, object_type="Gondel")
        hub = (tx, ty + 1.8, 25.0)
        s.add("IfcBuildingElementProxy", "Nabe", [pipe_solid(f, (tx, ty + 1.5, 25.0), hub, 0.8, segments=12)], keys=wind, object_type="Nabe")
        blades = []
        for angle in (90.0, 210.0, 330.0):
            a = math.radians(angle)
            dx, dz = math.cos(a), math.sin(a)
            blades.append(duct_solid(f, (hub[0] + 0.6 * dx, hub[1], hub[2] + 0.6 * dz), (hub[0] + 11.0 * dx, hub[1], hub[2] + 11.0 * dz), 0.9, 0.25))
        s.add("IfcBuildingElementProxy", "Rotorblaetter", blades, keys=wind, object_type="Rotorblatt")

    # Small hydro: lined channel sunk into the terrain, weir holding the headwater,
    # penstock to a turbine house over the channel, tailrace downstream.
    hydro = ("i-067-wasserkraftwerke",)
    bed_z, head_z, tail_z = -1.6, -0.3, -1.0
    s.add("IfcBuildingElementProxy", "Kanal-Ufer-1", [box_solid(f, x0, 17.0, bed_z, x1, 17.4, 0.3)], object_type="Ufermauer")
    s.add("IfcBuildingElementProxy", "Kanal-Ufer-2", [box_solid(f, x0, 21.6, bed_z, x1, 22.0, 0.3)], object_type="Ufermauer")
    s.add("IfcBuildingElementProxy", "Kanalsohle", [box_solid(f, x0, 17.4, bed_z, x1, 21.6, bed_z + 0.2)], object_type="Kanalsohle")
    s.add(
        "IfcBuildingElementProxy",
        "Wasserspiegel",
        [
            box_solid(f, x0, 17.4, head_z - 0.02, 14.0, 21.6, head_z),
            box_solid(f, 15.0, 17.4, tail_z - 0.02, 22.0, 21.6, tail_z),
            box_solid(f, 27.0, 17.4, tail_z - 0.02, x1, 21.6, tail_z),
        ],
        object_type="Wasser",
    )
    s.add("IfcBuildingElementProxy", "Wehr", [box_solid(f, 14.0, 17.4, bed_z + 0.2, 15.0, 21.6, 0.6)], keys=hydro, object_type="Wehr")
    s.add("IfcPipeSegment", "Druckleitung", [pipe_solid(f, (15.0, 19.5, -0.3), (22.0, 19.5, -0.7), 0.5, segments=14)], keys=hydro, predefined_type="RIGIDSEGMENT")
    s.add("IfcBuildingElementProxy", "Turbinenhaus", [box_solid(f, 22.0, 16.6, bed_z + 0.2, 27.0, 22.4, 4.0)], keys=hydro, object_type="Turbinenhaus")
    return s
