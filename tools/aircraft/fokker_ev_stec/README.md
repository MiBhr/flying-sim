# fokker_ev_stec: Fokker E.V (D.VIII) no. 001, Stefan Stec, Polish colours

Class label (free text, never a code path): WWI single-seat **parasol monoplane** fighter.

This directory is the complete, self-contained development pipeline of this one aircraft. It
produces two files and nothing else reaches the simulator:

```
public/models/fokker_ev_stec/fokker_ev_stec.glb             visual model, extras, no COL_*
public/models/fokker_ev_stec/fokker_ev_stec_colliders.glb   COL_* only
```

The application reads them through `src/aircraft/fokker_ev_stec/model.ts` (contract check, nodes
by name). Nothing in `src/` or `public/` refers to this directory. No code here is shared with any
other aircraft or with any other project; a new aircraft starts as a deliberate copy.

## Rebuild

Blender 4.5.9 LTS (its own Python and numpy; no pip packages, no Docker), Node 24 for the check.

```sh
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
$BLENDER -b --factory-startup -P tools/aircraft/fokker_ev_stec/build.py     # out/fokker_ev_stec.blend
$BLENDER -b tools/aircraft/fokker_ev_stec/out/fokker_ev_stec.blend -P tools/aircraft/fokker_ev_stec/export.py
npm run model:check                                                         # validate.mjs
```

| file | role |
|---|---|
| `geom.py` | all dimensions and the geometry of the exterior, engine, undercarriage, armament; node, mass-budget, control and collider registries |
| `cockpit.py` | cockpit structure, seat, controls, instruments |
| `textures.py`, `lib/texgen.py` | procedural textures (fixed seeds), atlas rectangles |
| `lib/meshkit.py` | mesh primitives (pure Python) |
| `lib/measure.py` | planform rasteriser, mass properties (the numbers in `extras.fsim`) |
| `build.py` | Blender objects, materials, UVs, modifiers, LODs, colliders, `extras.fsim` -> `out/*.blend`, `out/build_extras.json` |
| `export.py` | plain `.glb` export (no Draco, no meshopt), extras written into the JSON chunk, copy to `public/` |
| `validate.mjs` | `npm run model:check` |
| `reference/` | the plan and the photos; `profile_kagero_cover.png` (colour profile of 001 on the cover of T. J. Kowalski, "Fokker E.V/D.VIII", Kagero) and `photo_museum_replica_001.png` (museum replica) and `profile_arma_hobby_4view.webp` (colour 4-view of 187/18 "001", M. Ciepierski, Arma Hobby 2017) serve the livery and the tail cut-out only |

The build is deterministic: two consecutive builds give byte-identical `.glb` files, so
`colliders_sha256` in the visual file's extras identifies the colliders file.

## Conventions

- Units: metres, kilograms, degrees, seconds.
- File frame: nose **-Z**, right wing **+X**, up **+Y** (authoring frame in Blender: nose +Y,
  right +X, up +Z). The aircraft at identity orientation flies north; no per-model yaw.
- **Origin = centre of mass at the reference loading (605 kg).** The authoring datum is the front
  face of the propeller hub on the thrust line; `frame.datum_offset_m` gives it relative to the CG.
- Root node `Aircraft`, `extras.fsim` = JSON **string**, `"domain": "aircraft"`,
  `"id": "fokker_ev_stec"`, `"schema": 1` (counted for this aircraft only).
- Groups: `Exterior`, `Cockpit`, `Engine_Bay` (no `Gear_Wells`: the undercarriage is fixed).
  Every mesh node is under exactly one group.
- Moving part = empty pivot `<Name>` with identity rest rotation + child `<Name>_Mesh`.
- **Hinged surfaces have one more node:** `<Name>_Hinge` (static) -> `<Name>` (pivot) ->
  `<Name>_Mesh`. The hinge frame carries the direction of the hinge line (the rudder's is vertical,
  the ailerons' follow the tapered wing), so the pivot keeps an identity rest pose **and** its
  local +X is the hinge axis. Rotate `<Name>.rotation.x`; never touch `<Name>_Hinge`.
- A glTF node with several materials loads in Three.js as a `Group` named like the node, holding
  one mesh per material. Address nodes by name and transform the pivot, not the mesh.
- `extras.lod` on every mesh node: 0, 1 or 2. `<Node>_LOD1` / `<Node>_LOD2` are siblings of the
  LOD0 mesh. Show one level at a time (a plain glTF viewer shows all three superimposed).
  `Cockpit_LOD1` is the single reduced cockpit mesh for views from outside.
- `extras.hidden = true` (`Prop_1_Disc`): hidden until the application shows it.
- Markings are separate meshes 3 to 4 mm above the skin (`*_Markings`, alpha mask).

### Sign conventions

| node | positive rotation about local +X | range (deg) |
|---|---|---|
| `Aileron_R`, `Aileron_L` | trailing edge **down** (each node); a positive roll command is `angle = command * command_sign` with `command_sign` +1 right, -1 left | -20 .. +20 |
| `Elevator_L`, `Elevator_R` | trailing edge **down** | -25 .. +20 |
| `Rudder` | trailing edge **left** (nose yaws right) | -25 .. +25 |

| node | axis (file frame, local) | positive |
|---|---|---|
| `Prop_1`, `Engine_1` | Z (thrust axis) | counter-clockwise seen from the cockpit; the engine turns **clockwise from the cockpit**, so `spin_sign = -1`. The rotary engine turns with the propeller: drive both nodes with the same angle |
| `Wheel_Main_L/R` | X (axle) | |
| `Gear_Axle` | translation +Y, 0 .. 0.07 m | bungee-sprung axle moves up with both wheels |
| `Tail_Skid` | X, 0 .. 12 | tip up |
| `Ctl_Stick` | X: -18 .. 18 stick aft; Z: -18 .. 18 stick left | |
| `Ctl_Rudder_Bar` | Y, -22 .. 22 | right foot forward |
| `Ctl_Throttle`, `Ctl_Mixture` | X, -50 .. 0 | lever aft (0 = closed / lean end) |
| `Ctl_Air_Pump` | translation +Z, 0 .. 0.12 m | pulled aft |
| instrument needles | Z (dial normal, towards the pilot) | scale in `extras.instrument.scale` (clockwise needles have negative angles) |
| `Instr_Compass_Card` | Y | angle = heading, wraps |

## Node list (LOD0)

Static: `Fuselage`, `Fuselage_Markings`, `Cockpit_Coaming`, `Wing_L/R`, `Wing_L/R_Markings`,
`Stab_H_L/R`, `Stab_V`, `Cabane_L/R`, `Gear_Legs_L/R`, `Gear_Bracing_Wires`, `Axle_Fairing`,
`Gun_L/R`, `Gun_Sight`, `Windscreen_Glass`, `Windscreen_Frame`, `Fuel_Filler_Cap`, `Side_Ports`,
`Step_Stirrup`, `Lifting_Handles`, `Belly_Fitting`, `Cowl_Drain`, `Aileron_Cables_L/R`,
`Tail_Control_Cables`; engine bay: `Cowling`, `Engine_Mount`, `Firewall`, `Tank_Fuel_Oil`;
cockpit: `Cockpit_Frame`, `Cockpit_Floor`, `Cockpit_Rear_Bulkhead`, `Seat`, `Seat_Cushion`,
`Seat_Supports`, `Seat_Lap_Belt`, `Control_Torque_Tube`, `Rudder_Bar_Pedestal`,
`Throttle_Quadrant`, `Air_Pump_Body`, `Instrument_Board`, `Placard_Data`, `Ammo_Boxes`,
`Instr_RPM`, `Instr_Altimeter`, `Instr_FuelPress`, `Instr_Compass`, `Sw_Magneto_Plate`,
`Knob_Fuel_Cock_Plate`.

Pivots (each with `_Mesh`): `Aileron_L/R` (+ `_Hinge`, `_Horn`, `_Markings`), `Elevator_L/R`
(+ `_Hinge`, `_Horn`), `Rudder` (+ `_Hinge`, `_Horn`), `Prop_1` (+ `Prop_1_Disc`),
`Engine_1`, `Gear_Axle`, `Wheel_Main_L/R` (children of `Gear_Axle`), `Tail_Skid`, `Ctl_Stick`
(children: `Btn_Trigger_L/R`, `Btn_Blip`), `Ctl_Rudder_Bar`, `Ctl_Throttle`, `Ctl_Mixture`,
`Ctl_Air_Pump`, `Sw_Magneto`, `Knob_Fuel_Cock`, `Instr_RPM_Needle`, `Instr_Altimeter_Needle`,
`Instr_FuelPress_Needle`, `Instr_Compass_Card`.

Points: `Pt_Eye`, `Pt_Head_Pivot`, `Pt_Hand_L/R`, `Pt_Thrust_1`, `Pt_Exhaust_1`, `Pt_AC_Wing`,
`Pt_AC_Stab_H`, `Pt_AC_Stab_V`, `Pt_Gear_Contact_Main_L/R`, `Pt_Gear_Contact_Tail`,
`Pt_Muzzle_L/R`, `Pt_Cam_Chase`, `Pt_Cam_Tail`, `Pt_Cam_Wing_L/R`.

Dropped from the generic contract because this aircraft has no such part: flaps, trim, spoilers,
slats, airbrake, canopy, nose gear, gear doors, retraction, pedals (it has a rudder bar), lights,
lamps, hardpoints, `Gear_Wells`. Added: `<Name>_Hinge`, `Engine_1`, `Gear_Axle`, `Tail_Skid`,
`Ctl_Rudder_Bar`, `Ctl_Air_Pump`, `Btn_*`, `Pt_Muzzle_*`.

## extras.fsim (schema 1 of this aircraft)

`schema, domain, id, name, frame{forward,right,up,units,datum,datum_offset_m}`,
`mass{empty_kg, reference_kg, max_takeoff_kg, cg_m, cg_percent_mac, inertia_kgm2{Ixx..Iyz},
inertia_products, budget[{part,kg,cg_m,box_m}]}`,
`dimensions{length_m, span_m, height_m, height_level_m, wing_area_m2, mac_m, aspect_ratio}`,
`surfaces[{name,kind,area_m2,span_m,mac_m,root_chord_m,tip_chord_m,incidence_deg,dihedral_deg,sweep_le_deg,ac_m}]`,
`controls[{node,kind,axis,positive,command_sign,min_deg,max_deg,rest_deg,hinge_m[2],area_m2,chord_ratio,surface}]`,
`sign_convention`, `engines[{node,kind,type,thrust_point,thrust_dir,prop_diameter_m,blades,spin,spin_axis,spin_sign,rotating_nodes,disc}]`,
`gear{retractable,configuration,legs[],track_m,wheelbase_m,static_pitch_deg}`, `eye`,
`cockpit{group,instruments[],controls[],switches[],lamps[]}`, `groups`, `coverage_table`,
`budgets{tris{},texture_mb,file_mb,limits{}}`, `bounds_m`, `colliders_file`, `colliders_sha256`,
`colliders{hull,hull_tolerance_m,bounds,primitives[]}`, `lods[]`, `lod_rule`, `hidden_rule`.

Inertia: full tensor about the CG in file axes; products are `Ixy = sum(m*x*y)` (the tensor's
off-diagonal elements are `-Ixy`). Per-panel `span_m` is the semi-span. `tip_chord_m` is the chord
at 95 % of the panel span, `root_chord_m` the largest chord in the inner 15 %.

Collision file: `COL_Hull` (convex hull, 144 vertices, encloses every visual vertex within
`hull_tolerance_m` = 0.02 m), `COL_Bounds_box`, and the primitive compound
`COL_Fuselage_capsule`, `COL_Wing_L_box`, `COL_Wing_R_box`, `COL_StabH_box`, `COL_StabV_box`,
`COL_Nose_sphere`, `COL_Gear_box`. Each primitive's extras are USF `ColliderData` (`shape`,
`size`, `offset`) plus `orientation_deg` and `parent`. Gear contact is not a collider: use the
`Pt_Gear_Contact_*` points and their `extras.gear`.

## Numbers and where each comes from

"plan" = `reference/plan_3view_luranc_1972.webp` (1:50). Measured on the scan at 95.8 px/m; along
the fuselage 95.31 px/m so that the drawn length equals the stated 5.865 m. Scan resolution gives
about +-10 mm per pixel. "model" = measured from the generated geometry by `build.py`.

| quantity | value | source |
|---|---|---|
| length | 5.865 m stated; model 5.861 m | plan, dimension table |
| span | 8.400 m stated; model 8.399 m | plan, dimension table |
| height | **2.600 m**; model 2.625 m (three-point attitude, top of the wing) | plan: the damaged digit reads 6; the three-point height measured from the side view is 2.61 m, so 2.80 is excluded. The stated height is the tail-down height to the wing, without the propeller |
| height, thrust line level | 2.760 m | model |
| propeller diameter | 2.600 m | plan |
| maximum chord | 1.500 m | plan |
| track | 1.765 m | plan |
| wing area | 10.26 m2 | model (planform of the plan's top view, incl. ailerons, minus the cut-out). Commonly cited: 10.7 m2; the plan's planform gives 4 % less |
| MAC / aspect ratio | 1.273 m / 6.87 | model |
| wing leading edge at the centre | 0.769 m aft of the datum, 1.02 m half-width of the constant-chord centre section | plan, top + side view |
| taper | leading edge 0.157 m aft at 3.99 m, trailing edge 0.365 m forward at 3.90 m, rounded tips from 3.60 m | plan, top view |
| trailing-edge cut-out | 0.39 m deep, 0.43 .. 0.76 m wide | plan, top view |
| wing thickness | 0.215 m root, 0.085 m tip, flat upper surface 1.10 m above the thrust line | plan, front + side view |
| airfoil | thick, nearly flat-bottomed section (NACA-type thickness law, camber factor 0.62) | plan, section E-E (shape only; no ordinates on the plan) |
| incidence | 2.0 deg | plan, side view (+-1.5 deg at this scale) |
| dihedral (quarter-chord line) | 1.55 deg, upper surface flat | model, from the thickness taper of the front view |
| leading-edge sweep | 3.0 deg | model |
| ailerons | 2.30 .. 3.91 m from the centreline, chord 0.30 .. 0.22 m, 0.407 m2 each | plan, top view; area from the model |
| tailplane | root leading edge 4.008 m aft of datum, fixed half-span 1.107 m, tip 1.397 m | plan, top view |
| elevator | hinge 5.246 m, trailing edge 5.683 m aft of datum, 0.556 m2 per half; V cut-out for the rudder 0.05 m wide at the hinge, 0.22 m at the trailing edge (half-widths) | plan; cut-out from `reference/profile_arma_hobby_4view.webp` (the plan draws it wider: 0.34 m); area from the model |
| fin / rudder | fin 4.27 .. 5.316 m, top 0.68 m; rudder ellipse 0.88 x 1.00 m, top 1.10 m above thrust line, 0.554 m2 | plan, side view; area from the model |
| fuselage | firewall 0.63 m, stern post 5.316 m aft of datum (0.06 m wide there); width 0.79 m; depth 0.75 m at the front; lines from 8 stations | plan, side + top view, sections A-A .. D-D |
| cowling | radius 0.50 m, flat-cut at the fuselage bottom line | plan, side/front view |
| axle | 0.944 m aft of datum, 1.270 m below the thrust line | plan, side + front view |
| wheel radius | 0.365 m (tyre 0.10 m wide, grey rubber) | plan, side view (real tyre 760 x 100 mm) |
| wheelbase | 4.426 m (wheel contact to skid contact) | model |
| static pitch on the ground | 16.5 deg | model; the plan's ground line is at about 17 deg |
| axle travel | 0.07 m | **assumption** (bungee suspension) |
| control deflections | ailerons +-20, elevator -25/+20, rudder +-25 deg | **assumption** (not on the plan) |
| cockpit, pilot eye | oval opening in the decking, 0.67 m wide and 0.62 m long, 1.99 .. 2.61 m aft of datum; at its sides the edge dips to the longeron line as on the side view; edged with a padded leather roll (plan: oval 0.63 m wide, 1.94 .. 2.60 m incl. the padding); eye 2.30 m aft, 0.80 m above the thrust line | plan top/side view; eye = seat pan + 0.78 m (assumption) |
| empty / loaded mass | 405 kg / 605 kg | published (see below), not on the plan |
| CG | 1.395 m aft of datum, 0.146 m above the thrust line = **44 % MAC** | mass budget (assumed split, see below) |
| inertia (file axes, kg m2) | Ixx 822 (pitch), Iyy 1083 (yaw), Izz 574 (roll), Iyz 69 | mass budget, boxes + parallel-axis theorem |

### Mass budget

Published figures: empty 405 kg, loaded 605 kg, wing area 10.7 m2, Oberursel UR.II 110 hp
(Wikipedia "Fokker D.VIII"; other sources differ: Rise of Flight gives 360 kg empty). The spec
table of the task said about 406 / 586 kg; 405 / 605 kg is used because it is the value the
checked sources agree on. **Only the engine mass (146 kg, Le Rhone 9J type) is a real figure. The
split of the rest is an assumption**, chosen so that the items add up to 405 kg and 605 kg. Each
item is a solid box of its bounding box at its own centre; the list with positions is in
`extras.fsim.mass.budget`.

| item | kg | | item | kg |
|---|---|---|---|---|
| engine | 146 | | tail skid | 3 |
| propeller | 12 | | cabane struts | 8 |
| cowling, mount, firewall | 14 | | tanks, plumbing | 12 |
| guns 2 x LMG 08/15 | 26 | | controls, seat, instruments | 14 |
| fuselage front / rear | 40 / 18 | | **empty** | **405** |
| wing | 63 | | pilot | 85 |
| tailplane + elevators | 9 | | fuel / oil | 55 / 15 |
| fin + rudder | 4 | | ammunition, equipment | 35 / 10 |
| undercarriage | 36 | | **loaded** | **605** |

## Side-profile check against the plan

The model's orthographic side silhouette was laid over the plan's side view at the same scale
(200 px/m). Fuselage top and bottom lines, cowling, wing section and position, cabane struts,
undercarriage, fin, rudder, tailplane line and tail skid coincide within the line width of the
drawing (about 15 mm). Corrected after this check: cockpit cut-out now dips to the longeron line
(parabolic decking, wider oval), guns moved 0.11 .. 0.23 m aft, windscreen made small and arched,
rudder balance edge without a step, tail skid shortened, step moved. Remaining known difference:
the lower edge of the rudder balance area is straight (the plan rounds it, up to 40 mm).
`profile_002_side.webp` and `profile_baczkowski_1985.png` in `reference/` are further side
profiles used for this comparison (shape of the windscreen and of the cockpit cut-out).

## Livery decisions

- Chequerboard: **red/white**. The plan hatches two squares and the photo of the original is
  black-and-white; red/white is the Polish national marking and what the three model photos show.
  Thin outline as in the plan's detail "szachownica na samolocie nr 001".
- Wing: 2 x 2 squares of 0.575 m on the upper surface, 2.47 .. 3.62 m from the centreline, aft-inboard
  and fore-outboard squares red (plan, top view). None under the wing (not on the plan).
- Fuselage: chequerboard 3.32 .. 3.92 m aft of datum with the aft-upper square red.
- Rudder: **upper half red, lower half white**, no chequerboard, as on the colour profile of
  `reference/profile_kagero_cover.png` and the museum replica
  (`reference/photo_museum_replica_001.png`); decided by the owner. The black-and-white photo of
  the original shows a light rudder with a chequerboard, i.e. another state of the same aircraft.
- Tyres: **grey** (natural rubber), as on the Arma Hobby and Kagero profiles; decided by the owner.
- Tailplane: one continuous surface (the two halves `Stab_H_L/R` butt on the centreline with a
  square edge), elevator cut-out narrow as in `reference/profile_arma_hobby_4view.webp`.
- Not taken over from the Arma Hobby profile (not requested): brown-streaked wing tips, the
  violet/blue under surface, the white border of the fuselage chequerboard, no "001" on the
  starboard side.
- Wheels: **uncovered wire-spoked wheels** (same two references; decided by the owner). The plan
  draws the wheels without detail, the black-and-white photo shows fabric covers.
- Number 001 and the S-shaped emblem with the star: positions from the plan's side view.
  **The plan and the photo disagree:** on the photo of the original "001" is behind the cockpit and
  there is no emblem; the plan wins, as instructed. The emblem is drawn from the plan as two
  opposed arcs with a four-point star.
- Fuselage, tailplane, fin: four-colour lozenge fabric (model photos); metal panels and cowling
  dark green; wing upper surface streaked olive green, under surface pale blue. The task text
  says "light wing top surface"; the photo of the original and the models show a dark upper
  surface, which is what was modelled.

## Plan coverage

| item | source | node | status |
|---|---|---|---|
| Fuselage shell, sections A-A to D-D, turtledeck, cockpit opening | plan side/top, sections | `Fuselage` | modelled |
| Oval cockpit opening with padded leather roll and lacing eyelets | plan top view, Arma Hobby 4-view, photo | `Fuselage`, `Cockpit_Coaming` | modelled |
| Wing planform, taper, rounded tips, centre cut-out, section E-E | plan top/front, E-E | `Wing_L`, `Wing_R` | modelled |
| Wing ribs inside section E-E | plan E-E | | omitted(internal structure of a plywood-skinned wing, never visible) |
| Ailerons | plan top view | `Aileron_L`, `Aileron_R` | modelled |
| Aileron horns and cables | plan top/front view | `Aileron_L_Horn`, `Aileron_R_Horn`, `Aileron_Cables_L`, `Aileron_Cables_R` | modelled |
| Wing chequerboards | plan top view | `Wing_L_Markings`, `Wing_R_Markings`, `Aileron_L_Markings`, `Aileron_R_Markings` | modelled |
| Tailplane with rib lines | plan top view | `Stab_H_L`, `Stab_H_R` | modelled |
| Tailplane and elevator rib lines (fabric) | plan top view | | omitted(surface relief is left for a normal-map pass; see limits of this version) |
| Elevator halves with balance horns, narrow rudder cut-out | plan top view, Arma Hobby 4-view | `Elevator_L`, `Elevator_R` | modelled |
| Fin | plan side/top view | `Stab_V` | modelled |
| Rudder | plan side view, photo | `Rudder` | modelled |
| Rudder colours (red over white) | Kagero cover profile, museum replica | `Rudder` | modelled |
| Rudder chequerboard of the plan's detail drawing | plan detail, photo of the original | | omitted(owner decision: rudder red over white as on the colour profile) |
| Elevator and rudder horns | plan top/side view | `Elevator_L_Horn`, `Elevator_R_Horn`, `Rudder_Horn` | modelled |
| Tail control cables and their fuselage exits | plan side/top view | `Tail_Control_Cables` | modelled |
| Cabane struts (front tripod, rear pair, per side) | plan front/side view | `Cabane_L`, `Cabane_R` | modelled |
| Undercarriage V-legs | plan front/side view | `Gear_Legs_L`, `Gear_Legs_R` | modelled |
| Undercarriage cross bracing wires | plan front view | `Gear_Bracing_Wires` | modelled |
| Axle fairing (axle wing) | plan front/top view | `Axle_Fairing` | modelled |
| Axle with bungee cords | plan front view | `Gear_Axle` | modelled |
| Wheels: tyre, rim, wire spokes, hub | plan front/side view, Kagero cover profile, museum replica | `Wheel_Main_L`, `Wheel_Main_R` | modelled |
| Tail skid | plan side view, photo | `Tail_Skid` | modelled |
| Cowling with front plate, shaft opening, two cooling holes, lower opening | plan front/side view | `Cowling` | modelled |
| Rotary engine, 9 cylinders with fins, push rods, induction pipes | plan front view (lower opening) | `Engine_1` | modelled |
| Engine bearer, firewall | plan section A-A | `Engine_Mount`, `Firewall` | modelled |
| Dark fitting under the rear of the cowling | plan side view | `Cowl_Drain` | modelled |
| Propeller, two blades, laminated wood, hub plate | plan (propeller drawing), photos | `Prop_1` | modelled |
| Propeller blur disc | - | `Prop_1_Disc` | modelled |
| Two machine guns with cooling jackets (jacket 0.75 .. 1.45 m, receiver to 1.88 m aft of datum) | plan side/front/top view | `Gun_L`, `Gun_R` | modelled |
| Gun charging handles, feed blocks, ammunition chutes | plan side view (not resolved) | `Gun_L`, `Gun_R` | modelled |
| Ring-and-bead sight | model photos | `Gun_Sight` | modelled |
| Windscreen: small arched pane, 0.20 m wide, 0.16 m high, leaning aft at the front of the cockpit opening | plan side view, profile of no. 002 | `Windscreen_Glass`, `Windscreen_Frame` | modelled |
| Filler cap on the decking | plan top view | `Fuel_Filler_Cap` | modelled |
| Round ports on the fuselage side | plan side view | `Side_Ports` | modelled |
| Step under the fuselage | plan side view | `Step_Stirrup` | modelled |
| Bulge at the lower longeron near the tail (lifting handle) | plan side view | `Lifting_Handles` | modelled |
| Triangular fitting under the cockpit | plan side view | `Belly_Fitting` | modelled |
| Fuselage chequerboard, number 001, emblem | plan side view | `Fuselage_Markings` | modelled |
| Small stencils (weights table) on the fuselage side | plan side view | | omitted(illegible on the scan) |
| Fuel and oil tank | not on the plan (verify) | `Tank_Fuel_Oil` | modelled |
| Cockpit tube frame, floor, rear bulkhead | plan sections C-C, D-D (outline only; verify) | `Cockpit_Frame`, `Cockpit_Floor`, `Cockpit_Rear_Bulkhead` | modelled |
| Seat, cushion, supports, lap belt | plan top view (seat outline; verify) | `Seat`, `Seat_Cushion`, `Seat_Supports`, `Seat_Lap_Belt` | modelled |
| Control column with twin grip, triggers, blip button | not on the plan (verify) | `Ctl_Stick`, `Btn_Trigger_L`, `Btn_Trigger_R`, `Btn_Blip`, `Control_Torque_Tube` | modelled |
| Rudder bar | not on the plan (verify) | `Ctl_Rudder_Bar`, `Rudder_Bar_Pedestal` | modelled |
| Throttle and fine-adjustment levers | not on the plan (verify) | `Ctl_Throttle`, `Ctl_Mixture`, `Throttle_Quadrant` | modelled |
| Hand air pump | not on the plan (verify) | `Ctl_Air_Pump`, `Air_Pump_Body` | modelled |
| Instrument board | not on the plan (verify) | `Instrument_Board` | modelled |
| Tachometer | not on the plan (verify) | `Instr_RPM`, `Instr_RPM_Needle` | modelled |
| Altimeter | not on the plan (verify) | `Instr_Altimeter`, `Instr_Altimeter_Needle` | modelled |
| Tank pressure gauge | not on the plan (verify) | `Instr_FuelPress`, `Instr_FuelPress_Needle` | modelled |
| Compass | not on the plan (verify) | `Instr_Compass`, `Instr_Compass_Card` | modelled |
| Magneto switch, fuel cock | not on the plan (verify) | `Sw_Magneto`, `Sw_Magneto_Plate`, `Knob_Fuel_Cock`, `Knob_Fuel_Cock_Plate` | modelled |
| Data placard | not on the plan (verify) | `Placard_Data` | texture-only |
| Ammunition boxes | not on the plan (verify) | `Ammo_Boxes` | modelled |
| Airspeed indicator | not on the plan, not usual on the type | | omitted(no evidence in any reference) |
| Lights, antennas, pitot probe, hardpoints | none on the plan or photos | | omitted(the aircraft has none) |

## Budgets (actual)

| | LOD0 | LOD1 | LOD2 | limit |
|---|---|---|---|---|
| Exterior triangles | 30 619 | 11 428 | 3 952 | 150 000 |
| Engine bay triangles | 20 968 | 7 352 | 2 116 | 60 000 |
| Cockpit triangles | 6 250 | 760 (`Cockpit_LOD1`) | - | 60 000 |
| Textures, decoded with mips | 28.7 MB | | | 128 MB |
| `fokker_ev_stec.glb` | 4.22 MB | | | 150 MB |

LOD distances (`extras.fsim.lods`): LOD0 to 40 m, LOD1 to 200 m, LOD2 beyond. LOD1/LOD2 are made
with Blender's Decimate modifier (35 % and 10 %); parts smaller than 0.25 m are dropped at LOD2.
Textures (6, all embedded PNG): lozenge 1024, wing paint 512, propeller wood 256, markings atlas
2048 x 1024, dials atlas 2048 x 1024, gun jacket 256. No normal maps in this version.

## Deviations from the task's spec and limits of this version

- Height 2.600 m instead of the suggested 2.80 m (see the table).
- Masses 405 / 605 kg instead of about 406 / 586 kg (see Mass budget).
- Wing area from the plan is 10.26 m2, not 10.7 m2.
- `<Name>_Hinge` nodes were added; without them a vertical rudder hinge cannot be local X of a
  pivot whose rest rotation is identity.
- The rotary engine is its own pivot `Engine_1` under `Engine_Bay` (a node may sit in one group
  only), driven together with `Prop_1`.
- Fixed undercarriage: no retraction data; `Gear_Axle` and `Tail_Skid` carry the suspension travel.
- The cockpit fit is the typical fit of the type, not taken from the plan (the plan shows only the
  outline). All rows marked "verify" in the coverage table need a cockpit reference.
- Triangle counts are far below the proposed limits; the shapes of a fabric-and-tube aircraft of
  1918 need no more. Surface detail (rib tapes, stitching, panel lines, wear) is not baked into
  normal maps yet.
- The collision term "convex hull" (`COL_Hull`) is part of this contract and is the only use of
  that word here.
