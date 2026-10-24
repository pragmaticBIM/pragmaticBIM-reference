# pragmaticBIM Reference

The public data of the [pragmaticBIM](https://pragmaticbim.ch) Reference: what a building has to do, what a project has to know, and which data designers deliver, from use through to the verifiable order.

This repository is the single source of truth. Edit it directly: there is no upstream copy and no sync step.

## Problem

BIM requirements usually arrive as wishlists: long Excel sheets and 300-page manuals that nobody can check against a model. Every project reinvents the list, modelers guess which parameters matter, and owners cannot verify what they ordered.

## Solution

Requirements are treated like code. Project goals activate workflows, workflows name the elements and attributes they need, and the same source becomes contract Excel, PDF reports, and machine-readable IDS.

Configure intensity per project goal instead of ticking a use-case checklist. Only order data with a clear benefit. See the [visual tour](https://pragmaticbim.ch/en/how-to/elementplan-visual-tour) for how owners and BIM managers use the same artifact end to end.

Open it in the [web application](https://elementplan.pragmaticbim.ch), or read, fork, or copy it into your own project.

## What is in this repository

| Folder | Role |
| --- | --- |
| `project_goals/` | Project goals and boundary conditions (kickoff configurator) |
| `workflows/` | Use-case classification and project workflows |
| `domains/` | Deliverable disciplines |
| `elements/` | IFC entities, attributes, property sets, and phases |
| `values/` | Allowed-value sets |
| `phases/` | Phase catalogues (SIA, HOAI, RIBA, …) and SIA mappings |
| `models/` | Standard partial models (linked to a domain) |
| `documents/` | Standard documents (plans, schematics, contracts) |
| `uses/` | Building uses |
| `usage_scenarios/` | Usage scenarios and their options |
| `room_types/` | Functional rooms and container types composed with `contains`; configurations order `equipment` and `openings` |
| `components/` | Parametric templates for fixtures, built-in and loose furniture, doors, windows and clearances |
| `schema/` | JSON Schema for components and the room type `equipment` / `openings` extension |
| `catalog/` / `generators/` / `render/` / `runner.py` | IFC and isometric PNG sample generation ([generators/README.md](generators/README.md)) |
| `media/` | Published catalogue images and IFC attachments |
| `tests/` | Consistency checks for the data |

Workflows follow the [abstract use case classification](https://schema.pragmaticbim.ch/classification/usecase.html). Several lean on [abstractBIM](https://www.abstractbim.com/), which derives walls, slabs, and quantities from correctly modelled spaces and openings.

This is a starting point, not a Swiss standard. It does not replace KBOB or federal authority templates.

## Components, equipment and openings

Three levels stay apart so a generator can furnish a room from its outline:

| Level | Answers | Where |
| --- | --- | --- |
| Element | Which IFC entity and attributes are ordered? | `elements/` |
| Component | What size is it, what must stay clear, where does it connect? | `components/` |
| Equipment / opening | What does a room of this type contain, and how is it reached and lit? | `room_types/` → `configurations[].equipment` / `.openings` |

A component references one element and adds parameters (metres; `width` runs along the host wall), clearances, placement rules and connections. Clearance names come from the movement clearance value list, so placed clearances pass the same checks as hand-modelled ones.

Equipment and openings reference components and leave position to the generator. When several components are listed, the generator picks one per item. `when` and `unless` switch an item by project goal level or scenario option. Openings are declared by the room they lead into; `connects_to: {relationships: incoming}` takes the neighbours from the `room_relationships` of the selected scenario options.

A quantity can scale with the room: `quantity: {min: 1, per: {quantity: net_floor_area, divisor: 6}}` asks for one item per 6 m² of net floor area, at least one. Repeated fixtures such as urinals and showers carry `placement.axis_spacing_min`.

Circulation, voids, parking and outdoor room types carry no equipment; the rooms they lead into declare their doors.

Dimensions marked "Planungswert" or "SIA 500" in a `comment` still need professional confirmation before release.

## Contributing

Found a mistake or missing requirement? Open an issue or a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Checks

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest
```

## Schema

Entities follow the [pragmaticBIM Elementplan schema](https://github.com/pragmaticBIM/elementplan-data-schema). IDs use the `pragmaticbim:` prefix.

## License

[PragmaticBIM Standard License](LICENSE): use, copy, share, and adapt in projects, including commercial work, with attribution. Selling the Reference itself as a product is not allowed.
