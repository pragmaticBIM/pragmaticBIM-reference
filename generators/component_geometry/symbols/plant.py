"""Plant-room, laundry, electrical device, and clearance plan_symbol recipes."""

from __future__ import annotations

from typing import Sequence

import ifcopenshell

from generators.component_geometry import svg as svg_mod
from generators.component_geometry.bodies import local_box
from generators.component_geometry.types import GeometryContext, SvgPath


class PlantUnitRecipe:
    """Generic plant equipment: block body + service-face hatch in plan."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#d8dde5"),
            svg_mod.line(0.0, 0.0, w, d, stroke="#666666", stroke_width=0.008),
            svg_mod.line(w, 0.0, 0.0, d, stroke="#666666", stroke_width=0.008),
        ]


class CylinderPlantRecipe(PlantUnitRecipe):
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        # Approximate cylinder as square footprint extrusion (planning LOD)
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        r = min(w, d) * 0.45
        return [
            svg_mod.circle(w / 2, d / 2, r, fill="#d8dde5", stroke="#1a1a1a", stroke_width=0.015),
            svg_mod.circle(w / 2, d / 2, r * 0.35, fill="none", stroke="#666666", stroke_width=0.008),
        ]


class PumpRecipe(PlantUnitRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#cfd6e0"),
            svg_mod.circle(w / 2, d / 2, min(w, d) * 0.28, fill="#ffffff", stroke="#1a1a1a", stroke_width=0.012),
        ]


class BoardRecipe(PlantUnitRecipe):
    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=min(ctx.depth, 0.35), height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#2b3038"),
            svg_mod.line(0.1 * w, 0.2 * d, 0.9 * w, 0.2 * d, stroke="#88aacc", stroke_width=0.008),
            svg_mod.line(0.1 * w, 0.5 * d, 0.9 * w, 0.5 * d, stroke="#88aacc", stroke_width=0.008),
            svg_mod.line(0.1 * w, 0.8 * d, 0.9 * w, 0.8 * d, stroke="#88aacc", stroke_width=0.008),
        ]


class ApplianceRecipe(PlantUnitRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e4e4e8"),
            svg_mod.circle(w * 0.5, d * 0.45, min(w, d) * 0.22, fill="none", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.rect(w * 0.15, d * 0.78, w * 0.7, d * 0.12, fill="#cccccc", stroke="#1a1a1a", stroke_width=0.008),
        ]


class WasherDryerRecipe(ApplianceRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e4e4e8"),
            svg_mod.circle(w * 0.5, d * 0.35, min(w, d) * 0.18, fill="none", stroke="#1a1a1a", stroke_width=0.012),
            svg_mod.circle(w * 0.5, d * 0.72, min(w, d) * 0.18, fill="none", stroke="#1a1a1a", stroke_width=0.012),
        ]


class WallDeviceRecipe:
    """Small wall-mounted electrical devices."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [
            local_box(
                ifc_file,
                x0=0.0,
                y0=0.0,
                z0=0.0,
                x1=ctx.width,
                y1=max(ctx.depth, 0.04),
                height=max(ctx.height, 0.08),
            )
        ]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = max(ctx.width, 0.08)
        return [
            svg_mod.rect(0.0, 0.0, w, 0.06, fill="#f5e6a0", stroke="#1a1a1a", stroke_width=0.01),
        ]


class OutletRecipe(WallDeviceRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w = max(ctx.width, 0.08)
        return [
            svg_mod.rect(0.0, 0.0, w, 0.05, fill="#f5e6a0", stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.circle(w * 0.35, 0.025, 0.008, fill="#1a1a1a", stroke="#1a1a1a", stroke_width=0.004),
            svg_mod.circle(w * 0.65, 0.025, 0.008, fill="#1a1a1a", stroke="#1a1a1a", stroke_width=0.004),
        ]


class VolumeProxyRecipe:
    """Translucent clearance / device-space proxy."""

    def body_solids(
        self, ifc_file: ifcopenshell.file, ctx: GeometryContext
    ) -> Sequence[ifcopenshell.entity_instance]:
        return [local_box(ifc_file, x0=0.0, y0=0.0, z0=0.0, x1=ctx.width, y1=ctx.depth, height=ctx.height)]

    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        return [
            svg_mod.rect(
                0.0,
                0.0,
                ctx.width,
                ctx.depth,
                fill="#ffe8cc",
                stroke="#cc6600",
                stroke_width=0.02,
                stroke_dasharray="0.06 0.04",
            )
        ]


class DeviceSpaceRecipe(VolumeProxyRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.rect(
                0.0,
                0.0,
                w,
                d,
                fill="#ffe8cc",
                stroke="#cc6600",
                stroke_width=0.02,
                stroke_dasharray="0.06 0.04",
            ),
            svg_mod.rect(w * 0.15, d * 0.15, w * 0.7, d * 0.7, fill="#ffffff", stroke="#cc6600", stroke_width=0.01),
        ]


class LabBenchRecipe(PlantUnitRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e8f0e8"),
            svg_mod.rect(0.05, 0.05, w - 0.1, d - 0.1, fill="none", stroke="#4a7a4a", stroke_width=0.01),
        ]


class LabBenchIslandRecipe(LabBenchRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#e8f0e8"),
            svg_mod.line(w * 0.5, 0.0, w * 0.5, d, stroke="#4a7a4a", stroke_width=0.01),
        ]


class FumeCupboardRecipe(PlantUnitRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#dce8dc"),
            svg_mod.rect(0.0, 0.0, w, d * 0.25, fill="#b8d0b8", stroke="#1a1a1a", stroke_width=0.01),
            svg_mod.path(
                f"M {w * 0.2:.4f} {d * 0.4:.4f} L {w * 0.5:.4f} {d * 0.85:.4f} L {w * 0.8:.4f} {d * 0.4:.4f}",
                fill="none",
                stroke="#1a1a1a",
                stroke_width=0.012,
            ),
        ]


class SafetyCabinetRecipe(PlantUnitRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        return [
            svg_mod.footprint_rect(w, d, fill="#f5e0e0"),
            svg_mod.line(0.0, 0.0, w, d, stroke="#aa3333", stroke_width=0.012),
            svg_mod.line(w, 0.0, 0.0, d, stroke="#aa3333", stroke_width=0.012),
        ]


class ServerRackRecipe(PlantUnitRecipe):
    def plan(self, ctx: GeometryContext) -> list[SvgPath]:
        w, d = ctx.width, ctx.depth
        paths = [svg_mod.footprint_rect(w, d, fill="#2a2a32")]
        for y in (0.2 * d, 0.4 * d, 0.6 * d, 0.8 * d):
            paths.append(svg_mod.line(0.1 * w, y, 0.9 * w, y, stroke="#66aadd", stroke_width=0.006))
        return paths


PLANT_RECIPES = {
    "boiler": PlantUnitRecipe(),
    "chiller": PlantUnitRecipe(),
    "air_handler": PlantUnitRecipe(),
    "pump": PumpRecipe(),
    "tank": CylinderPlantRecipe(),
    "transformer": PlantUnitRecipe(),
    "generator": PlantUnitRecipe(),
    "ups": PlantUnitRecipe(),
    "switchboard": BoardRecipe(),
    "distribution_board": BoardRecipe(),
    "washing_machine": ApplianceRecipe(),
    "tumble_dryer": ApplianceRecipe(),
    "washer_dryer": WasherDryerRecipe(),
    "light_switch": WallDeviceRecipe(),
    "power_outlet": OutletRecipe(),
    "power_outlet_outdoor": OutletRecipe(),
    "manoeuvring_area": VolumeProxyRecipe(),
    "turning_area": VolumeProxyRecipe(),
    "device_imaging": DeviceSpaceRecipe(),
    "device_cooling": DeviceSpaceRecipe(),
    "device_machine": DeviceSpaceRecipe(),
    "device_medical": DeviceSpaceRecipe(),
    "device_operating_table": DeviceSpaceRecipe(),
    "server_rack": ServerRackRecipe(),
    "fume_cupboard": FumeCupboardRecipe(),
    "lab_bench": LabBenchRecipe(),
    "lab_bench_island": LabBenchIslandRecipe(),
    "safety_cabinet": SafetyCabinetRecipe(),
}
