"""Picture sources for arma-master-bestandsaufnahme elements whose id differs from a picture source id.

A source is a data-schema card id (rendered), a data-schema reuse id, or a
Reference image slug (copied). Ids equal to a source id need no entry:
``projekt``, ``planungsperimeter-projektperimeter``, ``gebaude-bauwerke``,
``geschoss-stockwerk``, ``sicherheitszone-schutzzonen`` and
``modelleinfugepunkt-disziplin`` are data-schema cards, ``geschossvolumen``
is a reuse id, and the hoch / mitte / tief detail levels are
``dataschema.scenes_lod.LOD_CARDS``. Innenraum keeps the arma-elementplan-data
picture on every level.
"""

from __future__ import annotations

BESTAND_SOURCES: dict[str, str] = {
    "aussenraum-2": "aussenraum",
    "d01-11-007-evakuationsanlage": "i-025-evakuationsanlage",
    "innenraum-hoch": "innenraum",
    "innenraum-mitte": "innenraum",
    "innenraum-tief": "innenraum",
}
