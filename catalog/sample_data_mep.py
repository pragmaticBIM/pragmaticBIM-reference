"""MEP catalog sample entries — one card per element, grouped by vignette.

Each vignette shows the full equipment set in white; only the card's element
is accented. Ids follow ``{slug}-01`` and attach to ``elements/{slug}.yaml``.
"""

from __future__ import annotations

from typing import Any

# (slug, element_type, extra entry keys)
_MEP_CARDS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    # Technikzentrale: boiler, exchanger, chiller, pump, compressor, gas, tank.
    ("mep-boiler", "MEP-BOILER", {}),
    ("mep-heat-exchanger", "MEP-HEAT-EX", {}),
    ("mep-chiller", "MEP-CHILLER", {}),
    ("mep-pump", "MEP-PUMP", {}),
    ("mep-compressor", "MEP-COMPRESSOR", {}),
    ("mep-gas-regulator", "MEP-GAS-REG", {}),
    ("mep-tank", "MEP-TANK", {}),
    # Same room emptied; only the reserved Erzeugerplatz volume.
    ("mep-schematic-equipment-space", "MEP-SCH-EQUIP", {}),
    # Elektroraum: transformer, switchboard, UPS, generator.
    ("mep-transformer", "MEP-TRANSFORMER", {}),
    ("mep-ups", "MEP-UPS", {}),
    ("mep-electric-distribution-board", "MEP-ELEC-DIST", {}),
    ("mep-electric-generator", "MEP-ELEC-GEN", {}),
    # Dachzentrale on the roofing vignette.
    ("mep-cooling-tower", "MEP-COOL-TOWER", {}),
    ("mep-unitary-equipment", "MEP-UNITARY", {}),
    ("mep-fan", "MEP-FAN", {}),
    # Bürodecke: dotted suspended ceiling, devices in and above it.
    ("mep-air-terminal", "MEP-AIR-TERM", {"camera_padding": 1.35}),
    ("mep-light-fixture", "MEP-LIGHT", {"camera_padding": 1.35}),
    ("mep-alarm", "MEP-ALARM", {"camera_padding": 1.35}),
    ("mep-fire-suppression-terminal", "MEP-FIRE-TERM", {"camera_padding": 1.35}),
    ("mep-cooled-beam", "MEP-COOL-BEAM", {"camera_padding": 1.35}),
    ("mep-air-terminal-box", "MEP-AIR-BOX", {"camera_padding": 1.35}),
    ("mep-damper", "MEP-DAMPER", {"camera_padding": 1.35}),
    ("mep-actuator", "MEP-ACTUATOR", {"camera_padding": 1.35}),
    # Wandabschnitt Elektro: small devices, tighter framing.
    ("mep-switching-device", "MEP-SWITCH", {"camera_padding": 1.3}),
    ("mep-outlet", "MEP-OUTLET", {"camera_padding": 1.3}),
    ("mep-sensor", "MEP-SENSOR", {"camera_padding": 1.3}),
    ("mep-communications-appliance", "MEP-COMMS", {"camera_padding": 1.3}),
    # Wohnraum Aussenwand: radiator, manifold cabinet, kitchen gas outlet.
    ("mep-space-heater", "MEP-SPACE-HEATER", {"camera_padding": 1.4}),
    ("mep-valve", "MEP-VALVE", {"camera_padding": 1.4}),
    ("mep-gas-terminal", "MEP-GAS-TERM", {"camera_padding": 1.4}),
    # Bad: wet-room vignette without clearances.
    ("mep-sanitary-terminal", "MEP-SANITARY", {}),
    ("mep-waste-terminal", "MEP-WASTE", {}),
    # Steigzone on the slab stack.
    ("mep-schematic-pipe", "MEP-SCH-PIPE", {}),
    ("mep-schematic-duct", "MEP-SCH-DUCT", {}),
    ("mep-schematic-tray", "MEP-SCH-TRAY", {}),
    ("mep-downpipe", "MEP-DOWNPIPE", {}),
    ("mep-provision-for-void", "MEP-PROV-VOID", {}),
)

MEP_SAMPLE_CATALOG: list[dict] = [
    {
        "id": f"{slug}-01",
        "element_type": element_type,
        **extra,
        "attach_element": slug,
    }
    for slug, element_type, extra in _MEP_CARDS
]
