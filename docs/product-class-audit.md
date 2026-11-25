# Product class audit: mixed construction systems

Audit of the 201 product class data sheets in `products/` for [issue #171](https://github.com/pragmaticBIM/pragmaticBIM-reference/issues/171).

## Rubric

| Status | Meaning |
| --- | --- |
| `single` | One construction system. Material grade, mounting, fixing or laying of the same build-up stays an attribute. |
| `mixed` | The data sheet combines systems that differ in build-up layers, trade or production process (in-situ or precast, bonded or ventilated, direct or suspended), or that are separately certified assemblies (fire-rated doors). A contractor prices them as separate positions. |

Each `mixed` class is deprecated and replaced by successor classes; ids and codes of existing classes keep their meaning. Successors are defined in the data contract and described in `products/`.

## Summary

| Status | Count |
| --- | ---: |
| single | 171 |
| mixed | 30 |
| **total** | **201** |

The 30 mixed classes are replaced by 68 new classes. `FaCP-RETROFIT-OVERCLADDING` and part of `SWP-BLT` are taken over by existing classes.

## Table

| id | name | status | systems found | proposed split |
| --- | --- | --- | --- | --- |
| `pragmaticbim:product/bmp-oth` | Other or unknown beam | single |  |  |
| `pragmaticbim:product/bmp-rc` | Reinforced concrete beam | mixed | In-situ concrete beam; Precast concrete beam | Family: Reinforced concrete beam (Stahlbetonträger). Deprecate `BMP-RC`, replaced by `BMP-RC-INSITU`, `BMP-RC-PRECAST`. In-situ casting with formwork and precast production with crane erection are different production processes and price lines. |
| `pragmaticbim:product/bmp-steel` | Steel beam | single |  |  |
| `pragmaticbim:product/bmp-timber` | Timber beam | single |  | Solid, glulam, and engineered timber are material grades of one prefabricated beam system; keep as attribute. |
| `pragmaticbim:product/ccp-gypsum-board` | Gypsum board ceiling | mixed | Direct-fixed gypsum board ceiling; Suspended gypsum board ceiling | Family: Gypsum board ceiling (Gipsplattendecke). Deprecate `CCP-GYPSUM-BOARD`, replaced by `CCP-GYPSUM-DIRECT`, `CCP-GYPSUM-SUSPENDED`. A lining fixed directly to the slab and a suspended ceiling with hangers and a service void differ in build-up layers and price logic. |
| `pragmaticbim:product/ccp-metal-grid` | Metal grid ceiling | single |  |  |
| `pragmaticbim:product/ccp-metal-panel` | Metal panel ceiling | single |  |  |
| `pragmaticbim:product/ccp-metal-sheet` | Metal sheet ceiling | single |  |  |
| `pragmaticbim:product/ccp-mineral-fibre` | Mineral-fibre acoustic ceiling | single |  |  |
| `pragmaticbim:product/ccp-oth` | Other / unknown ceiling covering | single |  |  |
| `pragmaticbim:product/ccp-synthetic` | Synthetic ceiling lining | mixed | Synthetic panel ceiling; Stretch membrane ceiling | Family: Synthetic ceiling (Kunststoffdecke). Deprecate `CCP-SYNTHETIC`, replaced by `CCP-SYNTHETIC-PANEL`, `CCP-STRETCH-MEMBRANE`. Panel ceilings on a substructure and tensioned membrane ceilings in perimeter profiles are different systems and trades. |
| `pragmaticbim:product/ccp-wood` | Wood ceiling lining | single |  | Material, format, and fixing variants of one wood lining; attributes. |
| `pragmaticbim:product/clp-oth` | Other or unknown column | single |  |  |
| `pragmaticbim:product/clp-rc` | Reinforced concrete column | mixed | In-situ concrete column; Precast concrete column | Family: Reinforced concrete column (Stahlbetonstütze). Deprecate `CLP-RC`, replaced by `CLP-RC-INSITU`, `CLP-RC-PRECAST`. In-situ casting with formwork and precast production with crane erection are different production processes and price lines. |
| `pragmaticbim:product/clp-steel` | Steel column | single |  |  |
| `pragmaticbim:product/clp-timber` | Timber column | single |  | Solid, glulam, and engineered timber are material grades of one prefabricated column system; keep as attribute. |
| `pragmaticbim:product/dcp-gate` | Gate / industrial door | mixed | Sectional gate; Rolling gate; Sliding gate; Folding gate; Up-and-over gate | Family: Gate (Tor). Deprecate `DCP-GATE`, replaced by `DCP-GATE-SECTIONAL`, `DCP-GATE-ROLLING`, `DCP-GATE-SLIDING`, `DCP-GATE-FOLDING`, `DCP-GATE-UP-OVER`. Sectional, rolling, sliding, folding and up-and-over gates are separate product systems with different mechanics, space needs, and prices. |
| `pragmaticbim:product/dcp-glass` | Glazed door system | mixed | Frameless glass door; Framed glazed door; Automatic glazed door system | Family: Glazed door (Glastür). Deprecate `DCP-GLASS`, replaced by `DCP-GLASS-FRAMELESS`, `DCP-GLASS-FRAMED`, `DCP-GLASS-AUTOMATIC`. Frameless all-glass doors, framed glazed doors and automatic door systems differ in fittings, drive, safety devices, and price logic. |
| `pragmaticbim:product/dcp-metal` | Metal door system | single |  |  |
| `pragmaticbim:product/dcp-oth` | Other / unknown door | single |  |  |
| `pragmaticbim:product/dcp-pvc` | Plastic / PVC door system | single |  |  |
| `pragmaticbim:product/dcp-special` | Special door system | single |  | Catch-all for rare special doors by design, like the *-OTH classes. |
| `pragmaticbim:product/dcp-wood` | Wood door system | mixed | Interior wood door; Fire, smoke or acoustic rated wood door; Wood entrance door | Family: Wood door (Holztür). Deprecate `DCP-WOOD`, replaced by `DCP-WOOD-INTERIOR`, `DCP-WOOD-RATED`, `DCP-WOOD-ENTRANCE`. A standard interior door, a certified fire, smoke or acoustic door and an entrance door exposed to outdoor climate are different certified assemblies with different price logic. |
| `pragmaticbim:product/dcp-wood-metal` | Wood–metal composite door | single |  |  |
| `pragmaticbim:product/fcp-artificial-stone` | Artificial stone flooring | single |  | Thick- vs. thin-bed is the laying method of the same covering on screed; attribute. |
| `pragmaticbim:product/fcp-carpet` | Textile carpet | single |  | Broadloom vs. tiles and adhered vs. loose-laid are format and laying of one covering; attributes. |
| `pragmaticbim:product/fcp-ceramic-tile` | Ceramic / porcelain tile floor | single |  |  |
| `pragmaticbim:product/fcp-laminate` | Laminate flooring | single |  |  |
| `pragmaticbim:product/fcp-linolium` | Linoleum | single |  |  |
| `pragmaticbim:product/fcp-lvt` | Vinyl / LVT floor | single |  | Adhered vs. click floating is the laying method of the same covering; attribute. |
| `pragmaticbim:product/fcp-natural-stone` | Natural stone flooring | single |  | Thick- vs. thin-bed is the laying method of the same covering on screed; attribute. |
| `pragmaticbim:product/fcp-oth` | Other / unknown floor covering | single |  |  |
| `pragmaticbim:product/fcp-parquet` | Parquet / engineered wood floor | single |  | Solid vs. engineered is the material grade of one wood floor; laying method is an attribute. |
| `pragmaticbim:product/fcp-raised-floor` | Raised / access floor | mixed | Access floor; Cavity floor | Family: Raised floor system (Systemboden). Deprecate `FCP-RAISED-FLOOR`, replaced by `FCP-ACCESS-FLOOR`, `FCP-CAVITY-FLOOR`. Access floors on pedestals (Doppelboden) and self-supporting cavity floors (Hohlboden) are different systems with different access, build-up, and price logic. |
| `pragmaticbim:product/fcp-seamless-resin` | Seamless resin floor | single |  |  |
| `pragmaticbim:product/fcp-subfloor` | Subfloor / leveling layer | mixed | Bonded screed; Floating screed; Heated screed | Family: Screed (Unterlagsboden). Deprecate `FCP-SUBFLOOR`, replaced by `FCP-SCREED-BONDED`, `FCP-SCREED-FLOATING`, `FCP-SCREED-HEATED`. Bonded, floating and heated screed differ in build-up layers (separation and impact-sound layers, heating pipes) and are priced as separate positions. |
| `pragmaticbim:product/fdp-drainage` | Foundation drainage and protection | single |  |  |
| `pragmaticbim:product/fdp-micro-pile` | Micropile / ground improvement | mixed | Micropile; Ground injection; Soil replacement | Family: Micropile and ground improvement (Mikropfahl und Baugrundverbesserung). Deprecate `FDP-MICRO-PILE`, replaced by `FDP-MICRO-PILE-GROUTED`, `FDP-GROUND-INJECTION`, `FDP-SOIL-REPLACEMENT`. Micropiles, grout injection and soil replacement are separate ground-engineering methods with different equipment and price logic. |
| `pragmaticbim:product/fdp-oth` | Other / unknown foundation | single |  |  |
| `pragmaticbim:product/fdp-pad` | Pad / isolated footing | single |  |  |
| `pragmaticbim:product/fdp-pile` | Driven / bored pile foundation | mixed | Driven pile; Bored pile | Family: Pile foundation (Pfahlfundation). Deprecate `FDP-PILE`, replaced by `FDP-PILE-DRIVEN`, `FDP-PILE-BORED`. Driven precast piles and bored cast-in-place piles use different equipment, process, and price logic. |
| `pragmaticbim:product/fdp-raft` | Raft / base slab foundation | single |  |  |
| `pragmaticbim:product/fdp-retaining` | Basement / retaining foundation wall | mixed | In-situ basement wall; Precast basement wall; Permanent excavation support wall | Family: Basement and retaining wall (Untergeschoss- und Stützwand). Deprecate `FDP-RETAINING`, replaced by `FDP-RETAINING-INSITU`, `FDP-RETAINING-PRECAST`, `FDP-RETAINING-SHORING`. In-situ concrete walls, precast wall elements and permanent excavation support walls use different processes, trades, and price logic. |
| `pragmaticbim:product/fdp-strip` | Strip footing foundation | single |  |  |
| `pragmaticbim:product/fdp-waterproof` | Foundation waterproofing / tanking | mixed | Membrane tanking; Watertight concrete construction | Family: Below-grade waterproofing (Abdichtung erdberührter Bauteile). Deprecate `FDP-WATERPROOF`, replaced by `FDP-WATERPROOF-MEMBRANE`, `FDP-WATERPROOF-CONCRETE`. Membrane tanking is a separate sealing trade; watertight concrete is a structural design and execution concept. Different trades and price logic. |
| `pragmaticbim:product/facp-bipv-integrated` | Building-integrated photovoltaic facade | single |  |  |
| `pragmaticbim:product/facp-brick-slip` | Brick slip / tile-hung ventilated facade | mixed | Ventilated brick slip facade; Brick slips bonded on ETICS | Family: Brick slip facade (Klinkerriemchenfassade). Deprecate `FaCP-BRICK-SLIP`, replaced by `FaCP-BRICK-SLIP-VENTILATED`, `FaCP-BRICK-SLIP-BONDED`. Brick slips hung on a ventilated sub-frame and brick slips bonded onto an insulation and render carrier are different build-ups (with or without cavity) and trades. |
| `pragmaticbim:product/facp-ceramic-ventilated` | Ventilated ceramic tile system | single |  |  |
| `pragmaticbim:product/facp-exterior-paint-coating` | Exterior paint / protective coating finish | single |  |  |
| `pragmaticbim:product/facp-fiber-cement-board` | Fibre-cement board facade | single |  |  |
| `pragmaticbim:product/facp-hpl-panel` | HPL / compact laminate facade panel | single |  | Visible vs. concealed fixing of the same rainscreen; attribute. |
| `pragmaticbim:product/facp-metal-composite-panel` | Metal composite facade panel (ACP) | single |  |  |
| `pragmaticbim:product/facp-metal-sheet-standing-seam` | Metal sheet standing-seam facade | single |  |  |
| `pragmaticbim:product/facp-natural-stone-ventilated` | Ventilated natural stone cladding | single |  |  |
| `pragmaticbim:product/facp-other` | Other / unknown facade covering | single |  |  |
| `pragmaticbim:product/facp-prefab-modular-metal` | Prefabricated modular metal facade system | single |  |  |
| `pragmaticbim:product/facp-prefab-modular-timber` | Prefabricated modular timber facade system | single |  |  |
| `pragmaticbim:product/facp-render-etics-wdvs` | Render / ETICS facade system | single |  |  |
| `pragmaticbim:product/facp-retrofit-overcladding` | Retrofit overcladding system (composite) | mixed | covered by existing `FaCP-RENDER-ETICS-WDVS`, `FaCP-FIBER-CEMENT-BOARD`, `FaCP-TIMBER-VENTILATED`, `FaCP-METAL-COMPOSITE-PANEL` | Family: Facade retrofit (Fassadensanierung). Deprecate `FaCP-RETROFIT-OVERCLADDING`, replaced by `FaCP-RENDER-ETICS-WDVS`, `FaCP-FIBER-CEMENT-BOARD`, `FaCP-TIMBER-VENTILATED`, `FaCP-METAL-COMPOSITE-PANEL`. The bonded variant is a render/ETICS system and the ventilated variant is a ventilated cladding. Both already exist as classes; the retrofit situation becomes an attribute of the facade, not a product class. |
| `pragmaticbim:product/facp-synthetic-ventilated` | Synthetic ventilated facade panel | single |  |  |
| `pragmaticbim:product/facp-timber-ventilated` | Timber ventilated facade system | single |  |  |
| `pragmaticbim:product/mtp-cool-chilled-ceiling` | Chilled ceiling / beam | mixed | Chilled ceiling; Chilled beam | Family: Chilled ceiling and beam (Kühldecke und Kühlbalken). Deprecate `MTP-COOL-CHILLED-CEILING`, replaced by `MTP-COOL-CEILING-PANEL`, `MTP-COOL-CHILLED-BEAM`. Radiant chilled ceiling panels and convective chilled beams (often with primary air) are separate products with different integration and price logic. |
| `pragmaticbim:product/mtp-cool-fan-coil` | Fan coil (cooling mode) | single |  | Mounting and coil medium are attributes of one terminal type. |
| `pragmaticbim:product/mtp-data-data-outlet` | Data outlet | single |  |  |
| `pragmaticbim:product/mtp-data-sensor-actuator` | Sensor / actuator (KNX / BACnet) | single |  |  |
| `pragmaticbim:product/mtp-data-wifi-ap` | WiFi access point | single |  |  |
| `pragmaticbim:product/mtp-elec-light` | Light fixture | single |  | Mounting type of one product group; attribute. |
| `pragmaticbim:product/mtp-elec-socket` | Socket outlet | single |  |  |
| `pragmaticbim:product/mtp-elec-switch` | Switch | single |  |  |
| `pragmaticbim:product/mtp-fire-fire-damper` | Fire damper | single |  |  |
| `pragmaticbim:product/mtp-fire-fire-damper-actuator` | Fire damper actuator | single |  |  |
| `pragmaticbim:product/mtp-fire-smoke-detector` | Smoke detector | single |  |  |
| `pragmaticbim:product/mtp-fw-shower` | Shower | single |  |  |
| `pragmaticbim:product/mtp-fw-tap` | Tap / faucet | single |  |  |
| `pragmaticbim:product/mtp-fw-wc-flush` | WC flush valve | single |  |  |
| `pragmaticbim:product/mtp-heat-fan-coil` | Fan coil (heating mode) | single |  | Mounting variants; attribute. |
| `pragmaticbim:product/mtp-heat-radiator` | Radiator | single |  |  |
| `pragmaticbim:product/mtp-heat-ufh-manifold` | Underfloor heating manifold | single |  |  |
| `pragmaticbim:product/mtp-sm-gas-outlet` | Gas outlet valve | single |  |  |
| `pragmaticbim:product/mtp-sm-hose-reel` | Hose reel | single |  |  |
| `pragmaticbim:product/mtp-sm-sprinkler-head` | Sprinkler head | single |  |  |
| `pragmaticbim:product/mtp-vent-air-valve` | Supply / extract air valve or diffuser | single |  | Valves and diffusers are terminal types of one product group; attribute. |
| `pragmaticbim:product/mtp-vent-grille` | Grille | single |  |  |
| `pragmaticbim:product/mtp-ww-floor-drain` | Floor drain | single |  |  |
| `pragmaticbim:product/mtp-ww-sink-drain` | Sink drain | single |  |  |
| `pragmaticbim:product/mtp-ww-wc-outlet` | WC outlet | single |  |  |
| `pragmaticbim:product/mup-cool-chiller` | Chiller | single |  | Indoor vs. outdoor placement of one plant type; attribute. |
| `pragmaticbim:product/mup-cool-free-cooler` | Free cooler | single |  |  |
| `pragmaticbim:product/mup-data-network-switch` | Network switch / rack | single |  |  |
| `pragmaticbim:product/mup-data-patch-panel` | Patch panel | single |  |  |
| `pragmaticbim:product/mup-data-server` | Server | single |  |  |
| `pragmaticbim:product/mup-elec-generator` | Backup generator | single |  |  |
| `pragmaticbim:product/mup-elec-main-dist-board` | Main distribution board | single |  |  |
| `pragmaticbim:product/mup-elec-sub-dist-board` | Sub-distribution board | single |  |  |
| `pragmaticbim:product/mup-elec-transformer` | Transformer | single |  |  |
| `pragmaticbim:product/mup-elec-ups` | Uninterruptible power supply | single |  |  |
| `pragmaticbim:product/mup-fw-pressure-booster` | Pressure booster | single |  |  |
| `pragmaticbim:product/mup-fw-water-heater` | Water heater / DHW boiler | single |  |  |
| `pragmaticbim:product/mup-heat-boiler` | Boiler | single |  |  |
| `pragmaticbim:product/mup-heat-district-heat-substation` | District heat substation | single |  |  |
| `pragmaticbim:product/mup-heat-heat-pump` | Heat pump | mixed | Air-source heat pump; Ground-source heat pump; Water-source heat pump | Family: Heat pump (Wärmepumpe). Deprecate `MUP-HEAT-HEAT-PUMP`, replaced by `MUP-HEAT-HP-AIR`, `MUP-HEAT-HP-GROUND`, `MUP-HEAT-HP-WATER`. Air, ground and water sources need different source installations (outdoor unit, boreholes, wells or waste-heat circuits) with very different price logic. |
| `pragmaticbim:product/mup-sm-compressor` | Compressed air compressor | single |  |  |
| `pragmaticbim:product/mup-sm-fire-pump` | Fire pump | single |  |  |
| `pragmaticbim:product/mup-sm-gas-regulator` | Gas pressure regulator | single |  |  |
| `pragmaticbim:product/mup-vent-ahu` | Air handling unit / monoblock | single |  | Monoblock vs. modular is a delivery form of the same plant; attribute. |
| `pragmaticbim:product/mup-vent-fan` | Fan | single |  |  |
| `pragmaticbim:product/mup-ww-grease-separator` | Grease separator | single |  | Indoor vs. buried is placement of one product; attribute. |
| `pragmaticbim:product/mup-ww-lifting-station` | Lifting station | single |  |  |
| `pragmaticbim:product/rap-baluster` | Metal baluster railing | single |  |  |
| `pragmaticbim:product/rap-cable-mesh` | Cable or mesh infill railing | single |  | Cable vs. mesh infill are variants of one tensioned infill railing; attribute. |
| `pragmaticbim:product/rap-glass-framed` | Framed laminated glass railing | single |  |  |
| `pragmaticbim:product/rap-glass-point` | Point-fixed structural glass railing | single |  |  |
| `pragmaticbim:product/rap-handrail` | Handrail only | single |  |  |
| `pragmaticbim:product/rap-oth` | Other or unknown railing | single |  |  |
| `pragmaticbim:product/rap-parapet-solid` | Solid parapet | mixed | In-situ concrete parapet; Precast parapet; Masonry parapet | Family: Solid parapet (Massive Brüstung). Deprecate `RAP-PARAPET-SOLID`, replaced by `RAP-PARAPET-INSITU`, `RAP-PARAPET-PRECAST`, `RAP-PARAPET-MASONRY`. In-situ concrete, precast and masonry parapets are built by different trades and processes with different price logic. |
| `pragmaticbim:product/rap-perforated-metal` | Perforated or expanded metal railing | single |  |  |
| `pragmaticbim:product/rap-timber` | Timber railing | single |  |  |
| `pragmaticbim:product/rcp-flat-bitumen` | Built-up / bitumen flat roof | single |  |  |
| `pragmaticbim:product/rcp-flat-liquid` | Liquid-applied flat roof | single |  |  |
| `pragmaticbim:product/rcp-flat-single-ply` | Single-ply membrane flat roof | single |  | Ballasted, mechanically fixed, or adhered is the fixing of one membrane system; attribute. |
| `pragmaticbim:product/rcp-green-extensive` | Extensive green roof | single |  |  |
| `pragmaticbim:product/rcp-green-intensive` | Intensive green roof | single |  |  |
| `pragmaticbim:product/rcp-metal-sheet` | Metal sheet roof | single |  |  |
| `pragmaticbim:product/rcp-oth` | Other / unknown roof covering | single |  |  |
| `pragmaticbim:product/rcp-pv-roof` | Roof-mounted photovoltaic system | mixed | Rack-mounted roof photovoltaic system; Roof-integrated photovoltaic system | Family: Roof photovoltaics (Photovoltaik auf dem Dach). Deprecate `RCP-PV-ROOF`, replaced by `RCP-PV-MOUNTED`, `RCP-PV-INTEGRATED`. Modules mounted above an existing covering and modules that form the weatherproof roof layer differ in build-up, warranty, and price logic. |
| `pragmaticbim:product/rcp-slate` | Natural slate roof | single |  |  |
| `pragmaticbim:product/rcp-tile-clay` | Clay tile roof | single |  |  |
| `pragmaticbim:product/rcp-tile-concrete` | Concrete tile roof | single |  |  |
| `pragmaticbim:product/rcp-wood-shingle` | Wood shingle / shake roof | single |  | Shingle, shake, and board are formats of one pitched timber covering; attribute. |
| `pragmaticbim:product/sfp-batch-plant` | Concrete batching plant | single |  |  |
| `pragmaticbim:product/sfp-break-room` | Break room | single |  |  |
| `pragmaticbim:product/sfp-buffer` | Intermediate storage | single |  |  |
| `pragmaticbim:product/sfp-canopy` | Protective canopy | single |  |  |
| `pragmaticbim:product/sfp-container` | Site container | single |  | Generic placeholder that points to more specific site facility classes. |
| `pragmaticbim:product/sfp-crane` | Crane | single |  |  |
| `pragmaticbim:product/sfp-crane-foundation` | Crane foundation | single |  |  |
| `pragmaticbim:product/sfp-crane-pad` | Crane set-up pad | single |  |  |
| `pragmaticbim:product/sfp-crane-swing` | Crane swing envelope | single |  |  |
| `pragmaticbim:product/sfp-fence` | Site fence | single |  |  |
| `pragmaticbim:product/sfp-gate` | Gate | single |  | Gate operating type is an attribute of the site gate. |
| `pragmaticbim:product/sfp-haul-road` | Haul road | single |  |  |
| `pragmaticbim:product/sfp-hoist` | Construction hoist | single |  |  |
| `pragmaticbim:product/sfp-office` | Site office | single |  |  |
| `pragmaticbim:product/sfp-oth` | Other / unknown site facility | single |  |  |
| `pragmaticbim:product/sfp-parking` | Parking area | single |  |  |
| `pragmaticbim:product/sfp-power-dist` | Site power distribution board | single |  |  |
| `pragmaticbim:product/sfp-pump` | Concrete pump | single |  |  |
| `pragmaticbim:product/sfp-ramp` | Ramp | single |  |  |
| `pragmaticbim:product/sfp-sanitary` | Sanitary facility | single |  |  |
| `pragmaticbim:product/sfp-scaffold` | Scaffold | single |  |  |
| `pragmaticbim:product/sfp-silo` | Silo | single |  |  |
| `pragmaticbim:product/sfp-skip-bay` | Skip bay | single |  |  |
| `pragmaticbim:product/sfp-storage` | Storage area | single |  |  |
| `pragmaticbim:product/sfp-store` | Site store | single |  |  |
| `pragmaticbim:product/sfp-transfer` | Transfer area | single |  |  |
| `pragmaticbim:product/sfp-turning` | Turning area | single |  |  |
| `pragmaticbim:product/sfp-water-conn` | Site water connection | single |  |  |
| `pragmaticbim:product/sfp-wheel-wash` | Wheel wash | single |  |  |
| `pragmaticbim:product/srp-oth` | Other or unknown stair | single |  |  |
| `pragmaticbim:product/srp-rc` | Reinforced concrete stair | mixed | In-situ concrete stair; Precast concrete stair | Family: Reinforced concrete stair (Stahlbetontreppe). Deprecate `SRP-RC`, replaced by `SRP-RC-INSITU`, `SRP-RC-PRECAST`. In-situ casting with formwork and precast flights set on acoustic bearings are different production processes and price lines. |
| `pragmaticbim:product/srp-steel` | Steel stair | single |  |  |
| `pragmaticbim:product/srp-timber` | Timber stair | single |  |  |
| `pragmaticbim:product/ssp-clt` | Cross-laminated timber (CLT) slab | single |  |  |
| `pragmaticbim:product/ssp-hbv` | Timber–concrete composite slab (HBV) | mixed | In-situ timber-concrete composite slab; Precast timber-concrete composite element | Family: Timber-concrete composite slab (Holz-Beton-Verbunddecke). Deprecate `SSP-HBV`, replaced by `SSP-HBV-INSITU`, `SSP-HBV-PRECAST`. Casting the concrete topping on site and laying prefabricated composite elements differ in process, drying time, and price logic. |
| `pragmaticbim:product/ssp-holz-lehm` | Timber–clay slab / deck | single |  | Niche system priced per project; prefab vs. site-filled stays an attribute. |
| `pragmaticbim:product/ssp-insitu` | In-situ concrete slab | single |  |  |
| `pragmaticbim:product/ssp-lightweight` | Lightweight slab system | single |  |  |
| `pragmaticbim:product/ssp-oth` | Other / unknown slab separator | single |  |  |
| `pragmaticbim:product/ssp-prefab-conc` | Prefabricated concrete slab | single |  | Hollow-core, double-tee, and flat elements are element types of one precast slab system; attribute. |
| `pragmaticbim:product/ssp-steel-composite` | Steel deck / composite slab | mixed | Composite slab on steel decking; Composite beam slab | Family: Steel-concrete composite slab (Stahl-Beton-Verbunddecke). Deprecate `SSP-STEEL-COMPOSITE`, replaced by `SSP-COMPOSITE-DECK`, `SSP-COMPOSITE-BEAM`. Composite slabs on profiled steel decking and solid slabs acting compositely with steel beams differ in formwork, production, and price logic. |
| `pragmaticbim:product/ssp-timber` | Timber slab / deck | single |  | Joist and rib decks are one timber-frame floor system. Tender text narrowed to joists and ribs; solid CLT plates belong to `SSP-CLT`, as the contract definition already states. |
| `pragmaticbim:product/swp-blt` | Lightweight concrete panel (BLT) wall | mixed | Lightweight concrete panel wall; covered by existing `SWP-MASONRY` | Family: Lightweight concrete wall (Leichtbetonwand). Deprecate `SWP-BLT`, replaced by `SWP-BLT-PANEL`, `SWP-MASONRY`. Lightweight concrete blocks are laid as masonry (already SWP-MASONRY); storey-height panels are set by crane. Different trades and price logic. |
| `pragmaticbim:product/swp-curtain-wall` | Curtain wall / facade system | mixed | Stick curtain wall; Unitised curtain wall | Family: Curtain wall (Vorhangfassade). Deprecate `SWP-CURTAIN-WALL`, replaced by `SWP-CURTAIN-WALL-STICK`, `SWP-CURTAIN-WALL-UNITISED`. Stick systems assembled on site and unitised systems prefabricated as storey-high elements differ in production, erection, and price logic. |
| `pragmaticbim:product/swp-element-wall` | Drywall / element partition wall | mixed | Stud drywall partition; Demountable system partition | Family: Lightweight partition (Leichte Trennwand). Deprecate `SWP-ELEMENT-WALL`, replaced by `SWP-DRYWALL`, `SWP-SYSTEM-PARTITION`. Site-built stud drywall partitions and demountable system partitions are different trades with different price logic and reuse. |
| `pragmaticbim:product/swp-leichtbau` | Lightweight construction wall | single |  | One framed lightweight wall system. Tender text narrowed to walls beyond a standard drywall partition; those belong to `SWP-DRYWALL`, which the contract definition already excludes. |
| `pragmaticbim:product/swp-masonry` | Masonry wall | single |  | Insulating blocks are a material grade of laid masonry; attribute. |
| `pragmaticbim:product/swp-ortbeton` | In-situ concrete wall | single |  |  |
| `pragmaticbim:product/swp-oth` | Other / unknown wall separator | single |  |  |
| `pragmaticbim:product/swp-prefab-conc` | Prefabricated concrete wall | single |  |  |
| `pragmaticbim:product/swp-rammed-earth` | Rammed earth wall | single |  |  |
| `pragmaticbim:product/swp-steel` | Steel frame wall | single |  |  |
| `pragmaticbim:product/swp-timber` | Timber frame wall | mixed | Timber stud frame wall; Solid timber wall | Family: Timber wall (Holzwand). Deprecate `SWP-TIMBER`, replaced by `SWP-TIMBER-FRAME`, `SWP-TIMBER-SOLID`. Timber frame (stud) walls and solid timber panel walls are different construction systems with different production and price logic. |
| `pragmaticbim:product/wcp-artificial-stone` | Artificial stone wall cladding | mixed | Bonded artificial stone wall cladding; Anchored artificial stone wall cladding | Family: Artificial stone wall cladding (Kunststeinwandbekleidung). Deprecate `WCP-ARTIFICIAL-STONE`, replaced by `WCP-ARTIFICIAL-STONE-BONDED`, `WCP-ARTIFICIAL-STONE-ANCHORED`. Adhered slabs and mechanically fixed large formats differ in build-up, trade, and price logic, as for natural stone. |
| `pragmaticbim:product/wcp-ceramic-tile` | Ceramic / porcelain wall tile | single |  |  |
| `pragmaticbim:product/wcp-natural-stone` | Natural stone wall cladding | mixed | Bonded natural stone wall cladding; Anchored natural stone wall cladding | Family: Natural stone wall cladding (Natursteinwandbekleidung). Deprecate `WCP-NATURAL-STONE`, replaced by `WCP-NATURAL-STONE-BONDED`, `WCP-NATURAL-STONE-ANCHORED`. Thin stone adhered to the wall and heavy slabs mechanically anchored in front of a cavity differ in build-up, trade, and price logic. |
| `pragmaticbim:product/wcp-oth` | Other / unknown wall covering | single |  |  |
| `pragmaticbim:product/wcp-paint` | Interior paint finish | single |  |  |
| `pragmaticbim:product/wcp-seamless-coating` | Seamless wall coating | single |  |  |
| `pragmaticbim:product/wcp-synthetic-panel` | Synthetic wall panel | single |  | Adhered vs. mechanically fixed is the fixing of the same panels; attribute. |
| `pragmaticbim:product/wcp-textile` | Textile wall covering | mixed | Bonded textile wall covering; Stretched fabric wall system | Family: Textile wall covering (Textile Wandbekleidung). Deprecate `WCP-TEXTILE`, replaced by `WCP-TEXTILE-BONDED`, `WCP-FABRIC-STRETCHED`. Fully bonded wall textiles are a wallcovering trade; stretched fabric panels with acoustic backing on a substructure are an interior-fitting system with different price logic. |
| `pragmaticbim:product/wcp-wallpaper` | Wallpaper | single |  |  |
| `pragmaticbim:product/wcp-wood-panel` | Wood wall panel | single |  |  |
| `pragmaticbim:product/wicp-aluminium` | Aluminium window system | single |  |  |
| `pragmaticbim:product/wicp-facade-unit` | Facade glazing unit | single |  |  |
| `pragmaticbim:product/wicp-oth` | Other / unknown window | single |  |  |
| `pragmaticbim:product/wicp-pvc` | Plastic / PVC window system | single |  |  |
| `pragmaticbim:product/wicp-skylight` | Roof window / skylight | mixed | Pitched roof window; Flat-roof dome; Continuous rooflight | Family: Roof glazing (Dachverglasung). Deprecate `WICP-SKYLIGHT`, replaced by `WICP-ROOF-WINDOW`, `WICP-ROOF-DOME`, `WICP-ROOFLIGHT-BAND`. Pitched roof windows, flat-roof domes and continuous rooflight bands are separate product systems with different installation and price logic. |
| `pragmaticbim:product/wicp-special` | Special transparent opening | single |  | Catch-all for rare special openings by design, like the *-OTH classes. |
| `pragmaticbim:product/wicp-steel` | Steel window system | single |  |  |
| `pragmaticbim:product/wicp-wood` | Wood window system | single |  |  |
| `pragmaticbim:product/wicp-wood-metal` | Wood–metal composite window | single |  |  |

## Successor classes

| replaces | code | de | en |
| --- | --- | --- | --- |
| `FCP-SUBFLOOR` | `FCP-SCREED-BONDED` | Verbundener Unterlagsboden | Bonded screed |
| `FCP-SUBFLOOR` | `FCP-SCREED-FLOATING` | Schwimmender Unterlagsboden | Floating screed |
| `FCP-SUBFLOOR` | `FCP-SCREED-HEATED` | Heizunterlagsboden | Heated screed |
| `DCP-WOOD` | `DCP-WOOD-INTERIOR` | Holz-Innentür | Interior wood door |
| `DCP-WOOD` | `DCP-WOOD-RATED` | Holztür mit Brand-, Rauch- oder Schallschutz | Fire, smoke or acoustic rated wood door |
| `DCP-WOOD` | `DCP-WOOD-ENTRANCE` | Holz-Eingangstür | Wood entrance door |
| `BMP-RC` | `BMP-RC-INSITU` | Ortbeton-Unterzug | In-situ concrete beam |
| `BMP-RC` | `BMP-RC-PRECAST` | Fertigteil-Unterzug | Precast concrete beam |
| `CLP-RC` | `CLP-RC-INSITU` | Ortbetonstütze | In-situ concrete column |
| `CLP-RC` | `CLP-RC-PRECAST` | Fertigteilstütze | Precast concrete column |
| `SRP-RC` | `SRP-RC-INSITU` | Ortbetontreppe | In-situ concrete stair |
| `SRP-RC` | `SRP-RC-PRECAST` | Fertigteiltreppe | Precast concrete stair |
| `FDP-PILE` | `FDP-PILE-DRIVEN` | Rammpfahl | Driven pile |
| `FDP-PILE` | `FDP-PILE-BORED` | Bohrpfahl | Bored pile |
| `FDP-RETAINING` | `FDP-RETAINING-INSITU` | Ortbeton-Untergeschosswand | In-situ basement wall |
| `FDP-RETAINING` | `FDP-RETAINING-PRECAST` | Fertigteil-Untergeschosswand | Precast basement wall |
| `FDP-RETAINING` | `FDP-RETAINING-SHORING` | Definitiver Baugrubenabschluss | Permanent excavation support wall |
| `FDP-WATERPROOF` | `FDP-WATERPROOF-MEMBRANE` | Abdichtung mit Bahnen | Membrane tanking |
| `FDP-WATERPROOF` | `FDP-WATERPROOF-CONCRETE` | Wasserdichte Betonkonstruktion | Watertight concrete construction |
| `FDP-MICRO-PILE` | `FDP-MICRO-PILE-GROUTED` | Mikropfahl | Micropile |
| `FDP-MICRO-PILE` | `FDP-GROUND-INJECTION` | Baugrundinjektion | Ground injection |
| `FDP-MICRO-PILE` | `FDP-SOIL-REPLACEMENT` | Bodenersatz | Soil replacement |
| `DCP-GATE` | `DCP-GATE-SECTIONAL` | Sektionaltor | Sectional gate |
| `DCP-GATE` | `DCP-GATE-ROLLING` | Rolltor | Rolling gate |
| `DCP-GATE` | `DCP-GATE-SLIDING` | Schiebetor | Sliding gate |
| `DCP-GATE` | `DCP-GATE-FOLDING` | Falttor | Folding gate |
| `DCP-GATE` | `DCP-GATE-UP-OVER` | Schwingtor | Up-and-over gate |
| `DCP-GLASS` | `DCP-GLASS-FRAMELESS` | Ganzglastür | Frameless glass door |
| `DCP-GLASS` | `DCP-GLASS-FRAMED` | Glasrahmentür | Framed glazed door |
| `DCP-GLASS` | `DCP-GLASS-AUTOMATIC` | Automatische Glastüranlage | Automatic glazed door system |
| `FaCP-BRICK-SLIP` | `FaCP-BRICK-SLIP-VENTILATED` | Hinterlüftete Riemchenfassade | Ventilated brick slip facade |
| `FaCP-BRICK-SLIP` | `FaCP-BRICK-SLIP-BONDED` | Verklebte Riemchenfassade auf Wärmedämmverbundsystem | Brick slips bonded on ETICS |
| `RCP-PV-ROOF` | `RCP-PV-MOUNTED` | Aufdach-Photovoltaikanlage | Rack-mounted roof photovoltaic system |
| `RCP-PV-ROOF` | `RCP-PV-INTEGRATED` | Indach-Photovoltaikanlage | Roof-integrated photovoltaic system |
| `WICP-SKYLIGHT` | `WICP-ROOF-WINDOW` | Dachflächenfenster | Pitched roof window |
| `WICP-SKYLIGHT` | `WICP-ROOF-DOME` | Lichtkuppel | Flat-roof dome |
| `WICP-SKYLIGHT` | `WICP-ROOFLIGHT-BAND` | Lichtband | Continuous rooflight |
| `CCP-GYPSUM-BOARD` | `CCP-GYPSUM-DIRECT` | Direkt befestigte Gipsplattendecke | Direct-fixed gypsum board ceiling |
| `CCP-GYPSUM-BOARD` | `CCP-GYPSUM-SUSPENDED` | Abgehängte Gipsplattendecke | Suspended gypsum board ceiling |
| `CCP-SYNTHETIC` | `CCP-SYNTHETIC-PANEL` | Kunststoffpaneeldecke | Synthetic panel ceiling |
| `CCP-SYNTHETIC` | `CCP-STRETCH-MEMBRANE` | Spanndecke | Stretch membrane ceiling |
| `WCP-NATURAL-STONE` | `WCP-NATURAL-STONE-BONDED` | Geklebte Natursteinwandbekleidung | Bonded natural stone wall cladding |
| `WCP-NATURAL-STONE` | `WCP-NATURAL-STONE-ANCHORED` | Verankerte Natursteinwandbekleidung | Anchored natural stone wall cladding |
| `WCP-TEXTILE` | `WCP-TEXTILE-BONDED` | Geklebter Textilwandbelag | Bonded textile wall covering |
| `WCP-TEXTILE` | `WCP-FABRIC-STRETCHED` | Gespannte Stoffwandbekleidung | Stretched fabric wall system |
| `WCP-ARTIFICIAL-STONE` | `WCP-ARTIFICIAL-STONE-BONDED` | Geklebte Kunststeinwandbekleidung | Bonded artificial stone wall cladding |
| `WCP-ARTIFICIAL-STONE` | `WCP-ARTIFICIAL-STONE-ANCHORED` | Verankerte Kunststeinwandbekleidung | Anchored artificial stone wall cladding |
| `MTP-COOL-CHILLED-CEILING` | `MTP-COOL-CEILING-PANEL` | Kühldecke | Chilled ceiling |
| `MTP-COOL-CHILLED-CEILING` | `MTP-COOL-CHILLED-BEAM` | Kühlbalken | Chilled beam |
| `MUP-HEAT-HEAT-PUMP` | `MUP-HEAT-HP-AIR` | Luft-Wasser-Wärmepumpe | Air-source heat pump |
| `MUP-HEAT-HEAT-PUMP` | `MUP-HEAT-HP-GROUND` | Sole-Wasser-Wärmepumpe | Ground-source heat pump |
| `MUP-HEAT-HEAT-PUMP` | `MUP-HEAT-HP-WATER` | Wasser-Wasser-Wärmepumpe | Water-source heat pump |
| `SWP-TIMBER` | `SWP-TIMBER-FRAME` | Holzrahmenbauwand | Timber stud frame wall |
| `SWP-TIMBER` | `SWP-TIMBER-SOLID` | Holzmassivwand | Solid timber wall |
| `RAP-PARAPET-SOLID` | `RAP-PARAPET-INSITU` | Ortbetonbrüstung | In-situ concrete parapet |
| `RAP-PARAPET-SOLID` | `RAP-PARAPET-PRECAST` | Fertigteilbrüstung | Precast parapet |
| `RAP-PARAPET-SOLID` | `RAP-PARAPET-MASONRY` | Gemauerte Brüstung | Masonry parapet |
| `FCP-RAISED-FLOOR` | `FCP-ACCESS-FLOOR` | Doppelboden | Access floor |
| `FCP-RAISED-FLOOR` | `FCP-CAVITY-FLOOR` | Hohlboden | Cavity floor |
| `SWP-BLT` | `SWP-BLT-PANEL` | Leichtbeton-Elementwand | Lightweight concrete panel wall |
| `SWP-ELEMENT-WALL` | `SWP-DRYWALL` | Ständerwand in Trockenbau | Stud drywall partition |
| `SWP-ELEMENT-WALL` | `SWP-SYSTEM-PARTITION` | Systemtrennwand | Demountable system partition |
| `SSP-STEEL-COMPOSITE` | `SSP-COMPOSITE-DECK` | Profilblech-Verbunddecke | Composite slab on steel decking |
| `SSP-STEEL-COMPOSITE` | `SSP-COMPOSITE-BEAM` | Verbundträgerdecke | Composite beam slab |
| `SSP-HBV` | `SSP-HBV-INSITU` | Holz-Beton-Verbunddecke mit Ortbeton | In-situ timber-concrete composite slab |
| `SSP-HBV` | `SSP-HBV-PRECAST` | Holz-Beton-Verbundelement | Precast timber-concrete composite element |
| `SWP-CURTAIN-WALL` | `SWP-CURTAIN-WALL-STICK` | Pfosten-Riegel-Fassade | Stick curtain wall |
| `SWP-CURTAIN-WALL` | `SWP-CURTAIN-WALL-UNITISED` | Elementfassade | Unitised curtain wall |

## Open points for the maintainer

- The retrofit situation of `FaCP-RETROFIT-OVERCLADDING` (new or existing substrate) has no attribute yet.
- Laying, fixing and mounting variants marked as attributes above have no attributes yet.

