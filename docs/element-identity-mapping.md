# Element identity mapping

SHACL rules in this repository always target **pragmaticBIM-reference element URIs**
(for example `https://pragmaticbim.ch/id/element/mep-light-fixture`). Filters match
`pbs:classifications` / `pbs:classification_uri` with `STRENDS(…, "/{element-id}")`.

Other schemes (IFC entity and PredefinedType, later Uniclass, and so on) map **into**
those Reference IDs. The data-contract converter `classify()` already writes the
Reference classification onto each converted object; rules do not embed foreign IRIs
(Uniclass, IFC class IRIs, …) in SHACL filters.

## Seed mappings (VKF 17-15 package)

| Reference element | External identity (maps into the Reference ID) |
| --- | --- |
| `mep-light-fixture` | `IfcLightFixture` (safety-luminaire subset: PredefinedType `SECURITYLIGHTING` plus `ePset_SafetyLighting` performance keys) |
| `mep-escape-sign` | Proxy path today (`IfcBuildingElementProxy` + escape-sign ObjectType); `IfcSign` when the contract mapping adopts it |

Safety performance keys (`SafetyRatedDuration`, `SafetyFloorIlluminance`, …) select the
safety-luminaire **subset** of light fixtures; they are not a substitute for the
element classification.
