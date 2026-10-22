"""Scene builder: products tagged with keys; a card accents the products of its keys."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import ifcopenshell
from ifcopenshell.api.aggregate import assign_object
from ifcopenshell.api.geometry import assign_representation, edit_object_placement
from ifcopenshell.api.root import create_entity

from generators.base import create_project_shell, get_body_context
from generators.mep_parts import add_solid_product
from generators.parts import create_body_representation, translation_matrix

ACCENT_VOLUME = (1.0, 0.45, 0.1, 0.38)
CONTEXT_SOLID = (0.96, 0.96, 0.96, 1.0)

# Graded oranges for cards that accent several groups at once (light → deep).
GRADE_COLORS: tuple[tuple[float, float, float, float], ...] = (
    (1.00, 0.80, 0.45, 1.0),
    (1.00, 0.62, 0.25, 1.0),
    (1.00, 0.45, 0.10, 1.0),
    (0.90, 0.32, 0.02, 1.0),
    (0.75, 0.24, 0.00, 1.0),
    (0.60, 0.16, 0.00, 1.0),
)


@dataclass
class SceneResult:
    ifc_file: ifcopenshell.file
    primary: list[ifcopenshell.entity_instance]
    dotted: list[ifcopenshell.entity_instance]
    thin: list[ifcopenshell.entity_instance]
    colors: dict[str, Sequence[float]]


@dataclass
class Scene:
    ifc_file: ifcopenshell.file
    body_context: ifcopenshell.entity_instance
    storey: ifcopenshell.entity_instance
    groups: dict[str, list[ifcopenshell.entity_instance]] = field(default_factory=dict)
    dotted: list[ifcopenshell.entity_instance] = field(default_factory=list)
    thin: list[ifcopenshell.entity_instance] = field(default_factory=list)
    volumes: set[str] = field(default_factory=set)
    solids: set[str] = field(default_factory=set)
    served: dict[str, list[ifcopenshell.entity_instance]] = field(default_factory=dict)

    @classmethod
    def new(cls, name: str, storey_name: str = "EG") -> "Scene":
        ifc_file, _project, _site, _building, storey, body_context = create_project_shell(
            name, storey_name=storey_name
        )
        return cls(ifc_file, get_body_context(ifc_file) or body_context, storey)

    @classmethod
    def wrap(cls, ifc_file: ifcopenshell.file) -> "Scene":
        storey = ifc_file.by_type("IfcBuildingStorey")[0]
        return cls(ifc_file, get_body_context(ifc_file), storey)

    def add(
        self,
        ifc_class: str,
        name: str,
        solids: Sequence[ifcopenshell.entity_instance],
        *,
        keys: Iterable[str] = (),
        predefined_type: str | None = None,
        object_type: str | None = None,
        dotted: bool = False,
        thin: bool = False,
        serves: Iterable[str] = (),
    ) -> ifcopenshell.entity_instance:
        """``serves``: keys whose system pictures accent this product too (pipes, cables, trays)."""
        if object_type is not None and predefined_type is None:
            predefined_type = "USERDEFINED"
        if ifc_class == "IfcSpace":
            product = self._add_space(name, solids)
        else:
            product = add_solid_product(
                self.ifc_file,
                ifc_class=ifc_class,
                name=name,
                body_context=self.body_context,
                storey=self.storey,
                solids=solids,
                object_type=object_type,
            )
        if predefined_type and hasattr(product, "PredefinedType"):
            product.PredefinedType = predefined_type
        self.tag(product, keys)
        for key in serves:
            self.served.setdefault(key, []).append(product)
        if dotted:
            self.dotted.append(product)
        if thin:
            self.thin.append(product)
        return product

    def _add_space(self, name: str, solids: Sequence[ifcopenshell.entity_instance]) -> ifcopenshell.entity_instance:
        """Spaces are aggregated under the storey, not contained in it."""
        space = create_entity(self.ifc_file, ifc_class="IfcSpace", name=name)
        assign_object(self.ifc_file, products=[space], relating_object=self.storey)
        edit_object_placement(self.ifc_file, product=space, matrix=translation_matrix())
        representation = create_body_representation(self.ifc_file, self.body_context, list(solids))
        assign_representation(self.ifc_file, product=space, representation=representation)
        return space

    def tag(self, product: ifcopenshell.entity_instance, keys: Iterable[str]) -> None:
        for key in keys:
            self.groups.setdefault(key, []).append(product)

    def volume(self, *keys: str) -> None:
        """Render these keys as translucent accent volumes."""
        self.volumes.update(keys)

    def solid(self, *keys: str) -> None:
        """Render these keys opaque even when they are IfcSpace symbols (white when not accented)."""
        self.solids.update(keys)

    def result(self, highlight: str | Sequence[str], system: bool = False) -> SceneResult:
        """Accent the products of ``highlight``; a list of keys gets graded oranges.

        ``system`` also accents the products that serve the keys.
        """
        keys = [highlight] if isinstance(highlight, str) else list(highlight)
        primary: list[ifcopenshell.entity_instance] = []
        colors: dict[str, Sequence[float]] = {}
        for index, key in enumerate(keys):
            products = self.groups.get(key)
            if not products:
                raise ValueError(f"scene has no products for key {key!r}")
            if system:
                products = [*products, *self.served.get(key, ())]
            for product in products:
                if product in primary:
                    continue
                primary.append(product)
                grade = GRADE_COLORS[index % len(GRADE_COLORS)]
                if key in self.volumes:
                    colors[product.GlobalId] = (*grade[:3], ACCENT_VOLUME[3]) if len(keys) > 1 else ACCENT_VOLUME
                elif len(keys) > 1:
                    colors[product.GlobalId] = grade
                elif key in self.solids:
                    colors[product.GlobalId] = GRADE_COLORS[2]
        # The renderer only honours colours for primary products.
        for key in self.solids.difference(keys):
            for product in self.groups.get(key, ()):
                if product not in primary:
                    primary.append(product)
                    colors[product.GlobalId] = CONTEXT_SOLID
        context_volumes = [p for key in self.volumes for p in self.groups.get(key, ())]
        dotted = [p for p in [*self.dotted, *context_volumes] if p not in primary]
        return SceneResult(self.ifc_file, primary, dotted, list(self.thin), colors)
