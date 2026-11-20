"""Plan-symbol recipe registry for all components."""

from __future__ import annotations

from generators.component_geometry.symbols.furniture import FURNITURE_RECIPES
from generators.component_geometry.symbols.kitchen import KITCHEN_RECIPES
from generators.component_geometry.symbols.openings import OPENING_RECIPES
from generators.component_geometry.symbols.plant import PLANT_RECIPES
from generators.component_geometry.symbols.sanitary import SANITARY_RECIPES

RECIPES = {
    **SANITARY_RECIPES,
    **KITCHEN_RECIPES,
    **OPENING_RECIPES,
    **FURNITURE_RECIPES,
    **PLANT_RECIPES,
}

__all__ = ["RECIPES"]
