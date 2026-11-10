# IFC catalog sample generators

Python tools that build small IFC vignettes and isometric PNG previews for Elementplan catalog cards (`picture_link` / `attachment_link` under `media/`).

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

OpenGL / OSMesa may be required for `pyrender` isometric renders (exact packages depend on your OS).

## Generate previews

```bash
# All sample catalog entries → output/{id}.ifc + {id}.png + {id}-print.tif
# Entries with attach_element also update media/ and element YAML links
python runner.py --output-dir output

# One entry only
python runner.py --output-dir output --only space-office-01
```

Each entry writes:

| File | Use |
| --- | --- |
| `{id}.png` | Catalog card (1024², brand engraving + watermark) |
| `{id}-print.tif` | Print asset (1200² @ 600 DPI, Device CMYK, no engraving/watermark) |

## Layout

| Path | Role |
| --- | --- |
| `catalog/sample_data.py` | Sample geometry + which element to attach |
| `catalog/mapping.py` | Catalog entry → generator params |
| `catalog/schema.py` | Defaults from `elements/*.yaml` |
| `catalog/attach.py` | Copy PNG/IFC into `media/` and set YAML links |
| `generators/` | IFC builders (space, slab, covering, …) and the room layout generator |
| `checks/` | IFC model checks (placement rules) |
| `render/isometric.py` | PNG isometric render |
| `runner.py` | Batch CLI |
| `media/images/` | Published rasters (`picture_link` PNG / `picture_print_link` TIFF) |
| `media/attachments/` | Published IFCs referenced by `attachment_link` |

## Notes

- Units are metres; Body representation uses Model/Body/MODEL_VIEW.
- Prefer ifcopenshell API helpers over raw entity construction.
- Attribute names and property datatypes come from the element YAML — do not invent IFC fields.

## Room layout and placement rules

Equipment and openings of a room-type configuration may carry
`placement_rules` (schema: `schema/room-type-equipment.schema.json`). The same
rules drive `generators/room_layout.py` (place equipment in a room) and
`checks/placement_rules.py` (check a delivered IFC). All geometry and rule
evaluation lives in `generators/room_rules.py`; generator and checker only
translate their input into its `Layout`.

| Relation | Holds when the item … | Fields |
| --- | --- | --- |
| `next_to` | is within `distance` of the target in plan; with `side`, measured along the wall from that jamb of the door | `distance`, optional `side` |
| `opposite` | stands on the wall facing the target's wall (normals ≥ 135° apart) | – |
| `same_wall_as` | stands on the target's wall | – |
| `not_on_wall_with` | does not stand on the target's wall | – |
| `distance_to` | has its centre within `distance` of the target's centre | `distance` |
| `facing` | turns its front towards the target (≤ 45°) | – |
| `elevation` | has its underside within `value` above finished floor (no target) | `value` |
| `not_in_clearance_of` | stays out of the target's clearances (door swing, chair zone) | – |

- `target` names one of `equipment_function`, `opening_function` or `edge_kind` (`exterior`, `interior`, `party_wall`) in the same room. Positive relations need one matching target; `not_*` relations must hold for all.
- `side` (`latch_side`, `hinge_side`) applies to door targets. The generator writes, and the checker reads, the hinge from the IFC `OperationType`.
- `severity`: `required` rules are hard constraints for the generator, `preferred` rules are scored. The checker reports both.
- `scope: each_target`: every target needs at least one item that meets the rule (one outlet next to each workplace). Default `each_item`: every item meets it.
- `variants` list accepted alternatives; `room_side: outside` lets an item stand in the neighbouring room behind the target opening.
- Rule ids follow `pragmaticbim:placement-rule/<entry-slug>-<name>`. The checker reports each violation with rule id, element GlobalId, severity and measured value.

Example (`room_types/buero.yaml`, light switch):

```yaml
placement_rules:
- id: pragmaticbim:placement-rule/buero-default-lichtschalter-tuer
  relation: next_to
  target:
    opening_function: access
  side: latch_side
  distance:
    max: 0.3
  severity: required
  variants:
  - relation: next_to
    target:
      opening_function: access
    side: latch_side
    distance:
      max: 0.3
    room_side: outside
```

```python
from generators.room_layout import OpeningSpec, generate_room_layout
from checks.placement_rules import check_placement_rules

result = generate_room_layout(
    [(0, 0), (4, 0), (4, 3), (0, 3)],
    [OpeningSpec("access", edge=0, offset=0.7), OpeningSpec("daylight", edge=2, offset=2.0)],
    "buero",
)
result.unplaced, result.issues          # what the generator could not satisfy
check_placement_rules(result.ifc_file)  # [] when every rule holds
```

CLI: `python -m checks.placement_rules model.ifc [--room-type SPACE=buero]`
exits with 1 when a required rule is violated.
