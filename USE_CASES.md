# Use cases

All 135 use cases from `workflows/`, grouped by the 6 top-level categories of the [abstract use case classification](https://schema.pragmaticbim.ch/classification/usecase.html) and by `workflow_group`.

| Category | Code | Use cases |
| --- | --- | --- |
| Ordering (Bestellung) | BES | 31 |
| Quality assurance (Qualitätssicherung) | QAS | 40 |
| Design (Planung) | DES | 44 |
| Construction (Ausführung) | CON | 9 |
| Handover (Übergabe) | HOV | 6 |
| Operation (Betrieb) | OPR | 5 |

## BES – Ordering (Bestellung)

### unternehmen

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| BES-CONCRETE-TENDER | Concrete works tender from model | Ausschreibung Betonarbeiten ab Modell | [`bes-concrete-tender-from-model.yaml`](workflows/bes-concrete-tender-from-model.yaml) |
| BES-FLOORING-TENDER | Provide the basis for the flooring tender | Grundlage für die Bodenbelagsausschreibung liefern | [`bes-flooring-tender-basis.yaml`](workflows/bes-flooring-tender-basis.yaml) |
| BES-FIRESTOP-TENDER | Provide the basis for the firestop tender | Grundlage für die Brandschott-Ausschreibung liefern | [`bes-firestop-tender-basis.yaml`](workflows/bes-firestop-tender-basis.yaml) |
| BES-ELEMENT-TENDER | Prepare the tender from component types and quantities | Ausschreibung aus Bauteiltypen und Mengen erstellen | [`bes-element-based-tendering.yaml`](workflows/bes-element-based-tendering.yaml) |
| BES-WINDOW-TENDER | Provide the basis for the window tender | Grundlage für die Fensterausschreibung liefern | [`bes-window-tender-basis.yaml`](workflows/bes-window-tender-basis.yaml) |
| BES-DOOR-TENDER | Provide the basis for the door tender | Grundlage für die Türausschreibung liefern | [`bes-door-tender-basis.yaml`](workflows/bes-door-tender-basis.yaml) |
| BES-DRYWALL-TENDER | Provide the basis for the drywall tender | Grundlage für die Trockenbauausschreibung liefern | [`bes-drywall-tender-basis.yaml`](workflows/bes-drywall-tender-basis.yaml) |
| BES-TIMBER-CONTRACTOR | Procure the timber contractor early | Holzbauunternehmen vorgezogen beschaffen | [`bes-timber-contractor-procurement.yaml`](workflows/bes-timber-contractor-procurement.yaml) |
| DES-FURNITURE | Plan the furnishing and procure the furniture | Möblierung planen und Möbel beschaffen | [`des-furniture-planning.yaml`](workflows/des-furniture-planning.yaml) |
| BES-ELEVATOR-EARLY | Tender the elevator installation early | Aufzugsanlage vorgezogen ausschreiben | [`bes-elevator-early-procurement.yaml`](workflows/bes-elevator-early-procurement.yaml) |
| BES-MASONRY-TENDER | Provide the basis for the masonry tender | Grundlage für die Mauerwerksausschreibung liefern | [`bes-masonry-tender-basis.yaml`](workflows/bes-masonry-tender-basis.yaml) |
| BES-STEELWORK-TENDER | Provide the basis for steelwork tendering | Grundlage für die Stahlbauausschreibung liefern | [`bes-steelwork-tender-basis.yaml`](workflows/bes-steelwork-tender-basis.yaml) |
| BES-TILING-TENDER | Provide the basis for the tiling tender | Grundlage für die Plattenausschreibung liefern | [`bes-tiling-tender-basis.yaml`](workflows/bes-tiling-tender-basis.yaml) |
| BES-PAINTING-TENDER | Provide the basis for the painting tender | Grundlage für die Malerausschreibung liefern | [`bes-painting-tender-basis.yaml`](workflows/bes-painting-tender-basis.yaml) |
| BES-PLAN-BOX | Procure plan and model stations | Plan- und Modellboxen beschaffen | [`bes-plan-model-box.yaml`](workflows/bes-plan-model-box.yaml) |
| BES-SITE-WLAN | Procure temporary site Wi-Fi | Temporäres Baustellen-WLAN beschaffen | [`bes-site-wlan.yaml`](workflows/bes-site-wlan.yaml) |

### grundlagen-bestand

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| BES-OWNER-CDE | Procure the CDE through the client | CDE durch die Bauherrschaft beschaffen | [`bes-owner-cde-procurement.yaml`](workflows/bes-owner-cde-procurement.yaml) |
| BES-EXISTING-SITE | Procure the spatial reference and terrain | Lagebezug und Gelände beschaffen | [`bes-survey-existing-model-procurement.yaml`](workflows/bes-survey-existing-model-procurement.yaml) |
| BES-EXISTING-POINT-CLOUD | Capture the existing building as a point cloud | Gebäudebestand als Punktwolke aufnehmen | [`bes-existing-building-point-cloud-procurement.yaml`](workflows/bes-existing-building-point-cloud-procurement.yaml) |
| BES-EXISTING-STRUCTURE | Model the building and structural shell for the chosen concept | Gebäudekörper und Rohbau nachmodellieren | [`bes-existing-structure-model-procurement.yaml`](workflows/bes-existing-structure-model-procurement.yaml) |
| BES-EXISTING-BUILDING-MEP | Procure the existing structural shell, fit-out, and MEP model | Bestandsmodell von Rohbau, Ausbau und TGA beschaffen | [`bes-existing-building-mep-model-procurement.yaml`](workflows/bes-existing-building-mep-model-procurement.yaml) |
| BES-EXISTING-CIRCULARITY | Procure existing-condition information for circularity | Kreislaufwirtschaftliche Bestandsinformationen beschaffen | [`bes-existing-circularity-procurement.yaml`](workflows/bes-existing-circularity-procurement.yaml) |
| BES-ROOM-PROGRAM | Formulate the room programme for designer procurement and competition | Raumprogramm für Planerbeschaffung und Wettbewerb formulieren | [`bes-room-program-brief.yaml`](workflows/bes-room-program-brief.yaml) |
| BES-FUNCTIONAL-BRIEF | Clarify operational and functional foundations through test planning | Betriebs- und Funktionsgrundlagen mit Testplanung klären | [`bes-functional-brief-test-planning.yaml`](workflows/bes-functional-brief-test-planning.yaml) |
| QAS-HAZMAT-CHECK | Plan measures for hazardous-material findings | Massnahmen für Schadstoffbefunde planen | [`qas-hazmat-check.yaml`](workflows/qas-hazmat-check.yaml) |

### planungsteam

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| BES-DESIGNER-PROCUREMENT | Procure designers who are capable in their discipline and digitally | Fachlich und digital kompetente Planer beschaffen | [`bes-designer-procurement.yaml`](workflows/bes-designer-procurement.yaml) |
| BES-ABSTRACTBIM-COMP | Evaluate competition entries with a room model | Wettbewerbsbeiträge mit Raummodell auswerten | [`bes-abstractbim-competition-evaluation.yaml`](workflows/bes-abstractbim-competition-evaluation.yaml) |
| BES-DESIGN-BUILD | Procure design-build services with a binding offer | Design-Build-Leistung mit verbindlichem Preis beschaffen | [`bes-design-build-procurement.yaml`](workflows/bes-design-build-procurement.yaml) |
| BES-IPD | Procure IPD services against a functional base reference and reference costs | IPD-Leistung über funktionale Grundreferenz und Referenzkosten beschaffen | [`bes-ipd-procurement.yaml`](workflows/bes-ipd-procurement.yaml) |
| BES-SEISMIC-MEP | Tender installation suspensions as a separate trade | Installationsaufhängungen als eigenes Gewerk ausschreiben | [`bes-mep-seismic-bracing-coordination.yaml`](workflows/bes-mep-seismic-bracing-coordination.yaml) |
| BES-ICE-SESSION | Order an ICE session | ICE-Session bestellen | [`bes-ice-session.yaml`](workflows/bes-ice-session.yaml) |

## QAS – Quality assurance (Qualitätssicherung)

### koordination

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| COM-QR-STAKEHOLDER-INFO | Digital resident information | Digitale Anwohnerinformation | [`qas-qr-stakeholder-info.yaml`](workflows/qas-qr-stakeholder-info.yaml) |
| COM-STAKEHOLDER-DIALOG | Neighbourhood and stakeholder dialogue | Nachbarschafts- und Stakeholderdialog | [`qas-stakeholder-dialog.yaml`](workflows/qas-stakeholder-dialog.yaml) |
| QAS-URBAN-AR | Assess the urban design on site with augmented reality | Städtebau vor Ort mit Augmented Reality beurteilen | [`qas-urban-ar-assessment.yaml`](workflows/qas-urban-ar-assessment.yaml) |
| QAS-COORD-ZONE | Plan coordination zones | Koordinationszonen planen | [`qas-coordination-zone-planning.yaml`](workflows/qas-coordination-zone-planning.yaml) |
| QAS-EARLY-COORD | Coordinate architecture and building services early | Architektur und Gebäudetechnik früh koordinieren | [`qas-early-design-coordination.yaml`](workflows/qas-early-design-coordination.yaml) |
| QAS-MEP-DETAIL | Architecture - building services coordination in late design stages | Koordination Architektur - Gebäudetechnik in späten Entwurfsphasen | [`qas-mep-detail-coordination.yaml`](workflows/qas-mep-detail-coordination.yaml) |
| QAS-ARCH-STRUCT-ADOPT | Adopt structural design in the architecture model | Tragwerksplanung ins Architekturmodell übernehmen | [`qas-arch-structural-adoption.yaml`](workflows/qas-arch-structural-adoption.yaml) |
| DES-ARCH-MEP-COORD | Coordinate architecture and building services | Architektur und Gebäudetechnik koordinieren | [`des-arch-mep-coordination.yaml`](workflows/des-arch-mep-coordination.yaml) |
| QAS-ARCH-STRUCT-COORD | Coordinate architecture and structure | Architektur und Tragwerk koordinieren | [`qas-arch-structural-coordination.yaml`](workflows/qas-arch-structural-coordination.yaml) |
| DES-STRUCT-MEP-OPENINGS | Adopt MEP openings in the structural model | TGA-Aussparungen im Tragwerksmodell übernehmen | [`des-struct-mep-opening-planning.yaml`](workflows/des-struct-mep-opening-planning.yaml) |
| QAS-SPECIAL-ROOM-USER | Align special rooms with the users | Spezialräume mit Nutzenden abstimmen | [`qas-special-room-user-coordination.yaml`](workflows/qas-special-room-user-coordination.yaml) |
| QAS-OUTLET-USER | Obtain user approval for outlet types | Steckdosentypen mit Nutzenden freigeben | [`qas-outlet-user-approval.yaml`](workflows/qas-outlet-user-approval.yaml) |
| QAS-DECISION-VIS | Visualize decisions and their impacts | Entscheide und Auswirkungen visualisieren | [`qas-decision-impact-visualization.yaml`](workflows/qas-decision-impact-visualization.yaml) |
| QAS-INSTALL-PATH | Verify installation access paths | Einbringwege nachweisen | [`qas-installation-path-verification.yaml`](workflows/qas-installation-path-verification.yaml) |
| QAS-MAINT-SPACE | Verify maintenance spaces | Wartungsräume nachweisen | [`qas-maintenance-space-verification.yaml`](workflows/qas-maintenance-space-verification.yaml) |
| QAS-VORSATZ | Verify the area requirement of facing shells | Flächenbedarf von Vorsatzschalen nachweisen | [`qas-facing-shell-area-verification.yaml`](workflows/qas-facing-shell-area-verification.yaml) |
| QAS-FURNISHABILITY | Verify furnishability | Möblierbarkeit nachweisen | [`qas-furnishability-verification.yaml`](workflows/qas-furnishability-verification.yaml) |
| QAS-ROOM-PROGRAM | Reconcile the room programme with the model | Raumprogramm mit dem Modell abgleichen | [`qas-room-program-verification.yaml`](workflows/qas-room-program-verification.yaml) |
| QAS-COST-INTERFACE | Visualize cost interfaces between base building and tenant fit-out | Kostenschnittstellen zwischen Grund- und Mieterausbau visualisieren | [`qas-cost-interface-tenant-fitout.yaml`](workflows/qas-cost-interface-tenant-fitout.yaml) |
| QAS-AWARD-INTERFACE | Visualize award interfaces | Vergabeschnittstellen visualisieren | [`qas-award-interface-visualization.yaml`](workflows/qas-award-interface-visualization.yaml) |
| QAS-SITE-LOGISTICS | Check site logistics across the construction phases | Baustellenlogistik über die Bauphasen prüfen | [`qas-construction-site-logistics.yaml`](workflows/qas-construction-site-logistics.yaml) |
| QAS-FALL-PROTECTION | Assess fall protection | Absturzsicherungen beurteilen | [`qas-fall-protection-verification.yaml`](workflows/qas-fall-protection-verification.yaml) |

### fachpruefung

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| QAS-DET-REF | Locate standard details in the model and check for gaps | Standarddetails im Modell verorten und Lücken prüfen | [`qas-detail-reference-model.yaml`](workflows/qas-detail-reference-model.yaml) |
| QAS-FIRE | Check fire resistance on components | Feuerwiderstand an Bauteilen prüfen | [`qas-fire-protection.yaml`](workflows/qas-fire-protection.yaml) |
| QAS-ACOUSTIC | Check sound and thermal insulation on components | Schall- und Wärmeschutz an Bauteilen prüfen | [`qas-acoustic-building-physics.yaml`](workflows/qas-acoustic-building-physics.yaml) |
| QAS-ELEMENT-PERF | Check component types against performance requirements | Bauteiltypen gegen Leistungsanforderungen prüfen | [`qas-element-type-performance-verification.yaml`](workflows/qas-element-type-performance-verification.yaml) |
| QAS-DESIGN-REVIEW | Carry out the design review at the end of the phase | Designreview am Phasenende durchführen | [`qas-design-review.yaml`](workflows/qas-design-review.yaml) |
| LAN-SPONGE-CITY | Verify the sponge-city principle | Schwammstadtprinzip nachweisen | [`qas-sponge-city.yaml`](workflows/qas-sponge-city.yaml) |
| QAS-ACCESS-SIA500 | Verify accessibility to SIA 500 | Hindernisfreiheit nach SIA 500 nachweisen | [`qas-accessibility-sia500-verification.yaml`](workflows/qas-accessibility-sia500-verification.yaml) |
| QAS-DAYLIGHT | Verify daylight provision using glazed areas | Belichtung über Glasflächen nachweisen | [`qas-daylight-area-verification.yaml`](workflows/qas-daylight-area-verification.yaml) |
| QAS-CONTRACTOR-DESIGN | Verify shop and installation design | Werk- und Montageplanung prüfen | [`qas-contractor-design-verification.yaml`](workflows/qas-contractor-design-verification.yaml) |
| QAS-COST-PLAUS | Component cost plausibility check | Bauteilkosten plausibilisieren | [`qas-component-cost-plausibility.yaml`](workflows/qas-component-cost-plausibility.yaml) |
| QAS-BENCHMARK | Benchmark a project against comparable building tasks | Benchmarking eines Projekts gegen vergleichbare Bauaufgaben | [`qas-project-benchmark.yaml`](workflows/qas-project-benchmark.yaml) |
| QAS-ELEMENT-COST-POSTCALC | Post-calculate component costs and feed unit rates back | Bauteilkosten nachkalkulieren und Einheitspreise zurückführen | [`qas-element-cost-post-calculation.yaml`](workflows/qas-element-cost-post-calculation.yaml) |
| QAS-FUND | Check and verify funding | Fördermittel prüfen und nachweisen | [`qas-funding-verification.yaml`](workflows/qas-funding-verification.yaml) |
| QAS-USAGE-AGREEMENT | Compare usage-agreement requirements with actual values | Nutzungsvereinbarung Soll-Ist abgleichen | [`qas-usage-agreement-verification.yaml`](workflows/qas-usage-agreement-verification.yaml) |
| QAS-BUILD-SEC | Verify building security measures | Gebäudesicherheitsmassnahmen prüfen | [`qas-building-security-verification.yaml`](workflows/qas-building-security-verification.yaml) |
| QAS-FUNCTIONAL-ACCEPTANCE | Verify building functions at handover | Funktionserfüllung des Gebäudes abnehmen | [`qas-functional-building-acceptance.yaml`](workflows/qas-functional-building-acceptance.yaml) |

### rahmenbedingungen

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| QAS-TREE-PRESERVE | Verify tree stock to be preserved | Zu erhaltenden Baumbestand nachweisen | [`qas-tree-preservation-verification.yaml`](workflows/qas-tree-preservation-verification.yaml) |
| QAS-CONSTRAINT | Check the design against planning-relevant constraints | Entwurf gegen planungsrelevante Rahmenbedingungen prüfen | [`qas-planning-constraints.yaml`](workflows/qas-planning-constraints.yaml) |

## DES – Design (Planung)

### arbeitsvorbereitung

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| DES-DRYWALL-REINF | Plan drywall reinforcement | Trockenbauverstärkungen planen | [`des-drywall-reinforcement-planning.yaml`](workflows/des-drywall-reinforcement-planning.yaml) |
| DES-CEILING-MIRROR | Coordinate suspended ceilings | Abhangdecken koordinieren | [`des-ceiling-mirror-planning.yaml`](workflows/des-ceiling-mirror-planning.yaml) |
| DES-FACADE | Maintain the facade in the model | Fassade im Modell führen | [`des-facade-planning.yaml`](workflows/des-facade-planning.yaml) |
| DES-LIGHTING-COORD | Coordinate lighting concept and fixture design | Leuchtenkonzept und Leuchtenplanung koordinieren | [`des-lighting-design-coordination.yaml`](workflows/des-lighting-design-coordination.yaml) |
| DES-BASIC-PIPING | Coordinate drainage and wastewater early | Entwässerung und Abwasser früh koordinieren | [`des-basic-piping-planning.yaml`](workflows/des-basic-piping-planning.yaml) |
| DES-FLOORING | Plan floor build-ups | Bodenaufbauten planen | [`des-flooring-planning.yaml`](workflows/des-flooring-planning.yaml) |
| DES-DOOR | Derive the basis for door planning | Grundlagen für die Türplanung ableiten | [`des-door-planning.yaml`](workflows/des-door-planning.yaml) |
| DES-UNDERFLOOR-HEATING | Provide the basis for underfloor heating | Grundlagen für die Fussbodenheizung bereitstellen | [`des-underfloor-heating-planning.yaml`](workflows/des-underfloor-heating-planning.yaml) |
| DES-SANITARY-FIXTURE-COORD | Coordinate sanitary fixtures | Sanitärobjekte koordinieren | [`des-sanitary-fixture-coordination.yaml`](workflows/des-sanitary-fixture-coordination.yaml) |
| DES-PLANNING-INTERFACE | Visualize design interfaces | Planungsschnittstellen visualisieren | [`des-planning-interface-visualization.yaml`](workflows/des-planning-interface-visualization.yaml) |
| DES-FIRE-MATRIX | Develop the fire cause-and-effect matrix | Erarbeiten Brandfallsteuermatrix | [`des-fire-control-matrix.yaml`](workflows/des-fire-control-matrix.yaml) |
| DES-TERRAIN | Check the terrain and the building connections | Gelände und Gebäudeanschlüsse prüfen | [`des-terrain-design.yaml`](workflows/des-terrain-design.yaml) |
| DES-EMBED-REINF | Coordinate embeds and architectural components with reinforcement | Einlagen und Architekturbauteile mit Bewehrung koordinieren | [`des-embed-reinforcement-coordination.yaml`](workflows/des-embed-reinforcement-coordination.yaml) |
| DES-COMPLEX-ASSEMBLY | Plan complex assemblies and intermediate states | Komplexe Montagen und Zwischenbauzustände planen | [`des-complex-assembly-planning.yaml`](workflows/des-complex-assembly-planning.yaml) |
| DES-STRUCT-MASONRY | Adopt main-contractor masonry in the structural model | Baumeister-Mauerwerk ins Tragwerksmodell übernehmen | [`des-struct-masonry-adoption.yaml`](workflows/des-struct-masonry-adoption.yaml) |

### kosten-mengen

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| DES-ELEMENT-COST-EARLY | Calculate element-based costs in early project phases | Elementbasierte Kostenberechnung in frühen Projektphasen | [`des-element-based-cost-early.yaml`](workflows/des-element-based-cost-early.yaml) |
| DES-ELEMENT-COST-LATE | Calculate element-based costs in late project phases | Elementbasierte Kostenberechnung in späten Projektphasen | [`des-element-based-cost-late.yaml`](workflows/des-element-based-cost-late.yaml) |
| DES-APT-SCHEDULE | Prepare apartment schedule | Wohnungsspiegel erstellen | [`des-apartment-schedule.yaml`](workflows/des-apartment-schedule.yaml) |
| DES-URBAN-MASS | Create the urban design mass study | Städtebauliche Massenstudie erstellen | [`des-urban-design-mass-study.yaml`](workflows/des-urban-design-mass-study.yaml) |
| DES-GFA | Determine storey floor areas | Geschossflächen ermitteln | [`des-floor-area-from-model.yaml`](workflows/des-floor-area-from-model.yaml) |
| DES-KV | Determine the construction volume | Konstruktionsvolumen ermitteln | [`des-construction-volume.yaml`](workflows/des-construction-volume.yaml) |
| DES-SIA416 | Verify areas to SIA 416 | Flächen nach SIA 416 nachweisen | [`des-sia416-area-verification.yaml`](workflows/des-sia416-area-verification.yaml) |
| DES-D0165 | Verify areas to SIA D0165 | Flächen nach SIA D0165 nachweisen | [`des-d0165-area-verification.yaml`](workflows/des-d0165-area-verification.yaml) |
| DES-EBKP-H | Calculate the eBKP-H classification | eBKP-H-Klassifizierung berechnen | [`des-ebkp-h-classification.yaml`](workflows/des-ebkp-h-classification.yaml) |
| DES-HUMUS | Determine humus quantities | Humusmengen ermitteln | [`des-humus-handling.yaml`](workflows/des-humus-handling.yaml) |

### nachhaltigkeit-energie

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| DES-ABSTRACTBIM-BPS | Derive the basis for heating demand verification to SIA 380/1 from the model | Grundlagen für den Heizwärmenachweis nach SIA 380/1 aus dem Modell ableiten | [`des-abstractbim-building-performance-simulation.yaml`](workflows/des-abstractbim-building-performance-simulation.yaml) |
| DES-LCA | Calculate the life-cycle assessment | Ökobilanz berechnen | [`des-full-life-cycle-calculation.yaml`](workflows/des-full-life-cycle-calculation.yaml) |
| DES-MATERIAL-PASS | Create the material passport for urban mining | Materialpass für Urban Mining erstellen | [`des-circularity.yaml`](workflows/des-circularity.yaml) |
| DES-UVP | Develop the environmental impact report | Umweltverträglichkeitsbericht erarbeiten | [`des-environmental-impact-assessment.yaml`](workflows/des-environmental-impact-assessment.yaml) |

### konzept-bewilligung

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| DES-MODEL-VIS | Create visualizations from the model | Visualisierungen aus dem Modell erstellen | [`des-model-based-visualization.yaml`](workflows/des-model-based-visualization.yaml) |
| DES-PARCELS | Make the affected parcels visible | Betroffene Parzellen sichtbar machen | [`des-building-law-parcels.yaml`](workflows/des-building-law-parcels.yaml) |
| DES-LAYOUT | Plan the layout with schematic floor plans | Layout mit schematischen Grundrissen planen | [`des-layout-planning.yaml`](workflows/des-layout-planning.yaml) |
| DES-PARKING | Verify parking spaces | Parkplätze nachweisen | [`des-parking-verification.yaml`](workflows/des-parking-verification.yaml) |
| DES-FIRE-CONCEPT | Create the fire protection requirements model | Brandschutz-Anforderungsmodell erstellen | [`des-fire-protection-concept.yaml`](workflows/des-fire-protection-concept.yaml) |
| DES-PHYSICS | Create the building physics requirements model | Bauphysik-Anforderungsmodell erstellen | [`des-building-physics-concept.yaml`](workflows/des-building-physics-concept.yaml) |
| DES-PERMIT | Prepare the building permit application | Baugesuch erstellen | [`des-building-permit.yaml`](workflows/des-building-permit.yaml) |
| DES-TRAFFIC | Check the requirements from the traffic study | Vorgaben aus dem Verkehrsgutachten prüfen | [`des-traffic-study.yaml`](workflows/des-traffic-study.yaml) |

### fachplanung-koordination

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| DES-USAGE-AGREEMENT | Visualize the structural usage agreement room by room | Nutzungsvereinbarung Tragwerk raumweise visualisieren | [`des-usage-agreement-visualization.yaml`](workflows/des-usage-agreement-visualization.yaml) |
| DES-MEP-USAGE-AGREEMENT | Visualize the MEP usage agreement room by room | Nutzungsvereinbarung Gebäudetechnik raumweise visualisieren | [`des-mep-usage-agreement-visualization.yaml`](workflows/des-mep-usage-agreement-visualization.yaml) |
| DES-DRAWINGS | Derive plans from the model | Pläne aus dem Modell ableiten | [`des-drawing-derivation.yaml`](workflows/des-drawing-derivation.yaml) |
| DES-WALL-REQUIREMENTS | Combine wall requirements from discipline reports | Wandanforderungen aus Fachberichten zusammenführen | [`des-wall-requirements-from-space-use.yaml`](workflows/des-wall-requirements-from-space-use.yaml) |
| DES-MEP-SCHEM | Develop MEP schematics | Erarbeiten TGA-Schemata | [`des-mep-schematics.yaml`](workflows/des-mep-schematics.yaml) |
| QAS-EXCL-ZONE | Define exclusion zones | Sperrzonen definieren | [`qas-structural-exclusion-zone-verification.yaml`](workflows/qas-structural-exclusion-zone-verification.yaml) |
| DES-CRIT-INSERT | Keep critical areas as an insert model | Kritische Bereiche als Einsatzmodell führen | [`des-critical-area-insert-model.yaml`](workflows/des-critical-area-insert-model.yaml) |

## CON – Construction (Ausführung)

### fortschritt-logistik

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| CON-ROOM-LABEL | Manage fit-out room by room with a checklist | Ausbau raumweise mit Checkliste steuern | [`con-logistics-fit-out.yaml`](workflows/con-logistics-fit-out.yaml) |
| CON-PROGRESS-DOC | Document construction progress with 360° captures | Baufortschritt mit 360°-Aufnahmen dokumentieren | [`con-construction-progress-documentation.yaml`](workflows/con-construction-progress-documentation.yaml) |

### produktion-montage

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| CON-REINF-EXEC | Reinforcement execution from model | Ausführung Bewehrung ab Modell | [`con-reinforcement-execution-from-model.yaml`](workflows/con-reinforcement-execution-from-model.yaml) |
| CON-FASTEN-SUSP | Fastening and suspension from model | Befestigung und Aufhängung ab Modell | [`con-fastening-suspension-from-model.yaml`](workflows/con-fastening-suspension-from-model.yaml) |
| CON-PRECAST-ORDER | Precast concrete parts ordering from model | Bestellen von Betonfertigteilen ab Modell | [`con-precast-concrete-ordering-from-model.yaml`](workflows/con-precast-concrete-ordering-from-model.yaml) |
| CON-SHL-BWP | Create formwork and reinforcement plans | Erstellen Schal- und Bewehrungspläne | [`con-formwork-reinforcement-plans.yaml`](workflows/con-formwork-reinforcement-plans.yaml) |
| CON-ROBOT-LAYOUT | Set out the fit-out robotically on the structural slab | Ausbau robotisch auf der Rohdecke abstecken | [`con-robotic-floor-layout.yaml`](workflows/con-robotic-floor-layout.yaml) |

### ausmass-maengel

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| CON-FINAL-MEASUREMENT | Determine final quantities for contractor accounts from the model | Schlussausmass für Unternehmerabrechnungen aus dem Modell ermitteln | [`con-final-measurement-from-model.yaml`](workflows/con-final-measurement-from-model.yaml) |
| CON-DEFECT-MGMT | Capture and manage defects with room QR codes | Mängel mit Raum-QR-Codes erfassen und bearbeiten | [`con-defect-management.yaml`](workflows/con-defect-management.yaml) |

## HOV – Handover (Übergabe)

### produkt-betriebsdaten

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| HOV-FM-MIN | Hand over minimal operational data as lists | Minimale Betriebsdaten als Listen übergeben | [`hov-fm-minimal-data-delivery.yaml`](workflows/hov-fm-minimal-data-delivery.yaml) |
| HOV-FM-3D | Hand over managed objects in the 3D model | Bewirtschaftete Objekte im 3D-Modell übergeben | [`hov-fm-3d-information-delivery.yaml`](workflows/hov-fm-3d-information-delivery.yaml) |
| HOV-COBIE | Hand over operational data in COBie format | Betriebsdaten im COBie-Format übergeben | [`hov-cobie-data-delivery.yaml`](workflows/hov-cobie-data-delivery.yaml) |
| HOV-PRODUCT-PASS-GTIN | Link the product passport via GTIN | Produktpass über GTIN verknüpfen | [`hov-product-pass-gtin.yaml`](workflows/hov-product-pass-gtin.yaml) |
| HOV-PRODUCT-PASS-SERIAL | Link the product passport via serial number | Produktpass über Seriennummer verknüpfen | [`hov-product-pass-serial-number.yaml`](workflows/hov-product-pass-serial-number.yaml) |

### modelle-dokumentation

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| HOV-NATIVE | Hand over native models for long-term use | Native Modelle langfristig nutzbar übergeben | [`hov-native-model-handover.yaml`](workflows/hov-native-model-handover.yaml) |

## OPR – Operation (Betrieb)

### bewirtschaftung

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| OPR-SIGNAGE-ROOM | Managing the signage room number | Signaletik-Raumnummern führen | [`opr-signage-room-number.yaml`](workflows/opr-signage-room-number.yaml) |
| OPR-FM-ARCH | Maintain IFC models during alterations | IFC-Modelle bei Umbauten nachführen | [`opr-facility-management-architecture-model.yaml`](workflows/opr-facility-management-architecture-model.yaml) |
| OPR-FM-PC | FM with a classified point cloud | Klassifizierte Punktwolke im FM nutzen | [`opr-facility-management-point-cloud.yaml`](workflows/opr-facility-management-point-cloud.yaml) |

### optimierung-instandhaltung

| Code | English | Deutsch | File |
| --- | --- | --- | --- |
| OPR-FIRESTOP-MAINT | Manage firestops in operation | Brandschotte im Betrieb managen | [`opr-firestop-maintenance.yaml`](workflows/opr-firestop-maintenance.yaml) |
| OPR-BUILDING-PERFORMANCE | Optimize building operation during the first years | Gebäudebetrieb in den ersten Jahren optimieren | [`opr-building-performance-optimization.yaml`](workflows/opr-building-performance-optimization.yaml) |
