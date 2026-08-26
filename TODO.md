# TODO / Backlog — t34-vs-tiger-docs

Running list of things flagged during work sessions, not yet done. Newest first within each section. See `CHANGELOG.md` for what's already been done.

---

## Lighting - the commander is SETTLED, the ambient pass is not (2026-08-26)

```
REDUX   34 missions, ambient luminance   0.092 .. 0.210
ZW      40 missions, ambient luminance   0.120 .. 0.609
```

Every REDUX mission sits at or below ZW's dimmest.

- [x] **C2M1 relit** - ambient lum 0.120 -> 0.318, anti-sun brought to ZW's
  shape (lum 0.455 / intensity 0.200 / angle 45, was 0.820 / 0.400 / 10).
- [x] **The commander/self-shadow trade is DECIDED.** `PlanarShadow = false`
  in `Models\u_veh_PzVI_LATE.script` - the user chose self-shadowing and a
  dark commander, "the less of 2 options". **Do not flip without asking.**
  Unexplained: ZW ships `true` and still looks shaded. See
  `TvT_Mission_Authoring_Verified.md` section 14b.
- [ ] **A considered ambient pass across the other 11 campaign missions.**
  Still the highest-value open lighting job. ZW's brightest run
  `SunIntensity` 0.7-0.9, not 1.0 - if a mission washes out, lower the sun
  rather than dropping ambient. **Include `AntiSunAngle`** - it is a contrast
  control, and a low angle rakes a vehicle's shaded flanks.
- [ ] **Shadow consistency**: 1M1, 1M3, 1M4, 2M3, 2M4, 2M6 still need
  `StencilShadowColor` (five never set it). Note ZW runs stencil *brighter*
  than `ShadowColor`, so "they must match" is a default, not a rule.

---

## Model tooling - the .ms2 format is SOLVED (2026-08-26)

- [x] **UVs, transforms and material indices all decoded.** The importer now
  produces assembled, correctly skinned vehicles. See
  `Documentation/MS2_Node_Transforms_SOLVED.md`.
- [x] **Export WORKS and is confirmed in the engine.** `ms2_writer.py`; the
  Editor rendered a file we wrote. Round-trip verified on 249 models
  (248 byte-identical). **Limit: vertex/index counts must not change.**
- [ ] **Identify the `vcount * 24` block** — 6 floats per vertex on every
  textured node, gated by flag `0x40000`. Almost certainly tangent + binormal,
  and computable from positions/UVs/normals if so. **This is the one thing
  between "reshape what exists" and "add geometry"**, which is what the King
  Tiger vision-port idea would need.
- [ ] Test the writer on a **skinned** mesh — the confirmed test was a static
  box. Bind poses (80 bytes x count) and 20-byte-per-vertex weights are
  preserved verbatim, but untested.
- [ ] Check whether a shape change needs the companion **`.rmap`** regenerating
  (pathfinding/collision footprint). That format is untouched.
- [x] **File > Import now produces a finished vehicle in one step.** The addon
  parses the companion `.script` itself, loads `.tex` as the DDS it is, honours
  alpha mode, and auto-hides armour/collision facets. Tested on four vehicles
  across both builds.
- [x] **`ms2_probe.py` marked SUPERSEDED** with a header naming its two wrong
  answers (it desyncs on real vehicles; its `other_count` of 4 is really 1, and
  that bad number cost a later session real time). Kept rather than deleted -
  it is the record of how the format was first worked out.

## TOMORROW'S LIST (2026-08-26 — in rough priority order)

### 1. ZW's handling & gunnery bias — REVERT TO ORIGINAL (do this before penetration)
- [ ] **The user was right that ZeeWolf had a bias, and it is in handling and
  gunnery, not penetration.** Compared class-for-class against the untouched
  2001 original:
  - AI Tiger gun `FireDeviation` **1.2 -> 0.05** (24x MORE accurate); AI T-34s
    made *less* accurate.
  - **Player** Tiger gun unchanged at 0.005; **player T-34/85 0.005 -> 0.15**,
    thirty times worse.
  - Tiger: +24% speed, 29% lighter (56 t -> 40 t), sees 1500 -> 2600 m, engages
    1000 -> 2600 m, fires every 12 s -> 7 s.
  - T-34/85 turret traverse **halved** (17 -> 8); T-34/76 **cut 5x** (36 -> 7).
- [ ] **This is a REVERT, not a rebalance** — REDUX is the 2001 original on these
  fields (one exception: Tiger `MaxPower` 1600 -> 1500, a REDUX nerf). So there
  is no design judgement to make, unlike the penetration question.
- **Compare PER CLASS.** A unit file has separate AI and player gun classes
  (`CTankT34_85_44Gun` vs `...PlayerGun`); grepping the first match gives
  contradictory answers. This trap produced two opposite wrong readings.
- [ ] Sweep the rest of ZW's roster the same way — only three tanks were checked.

### 2. Ballistic realism pass on ZW — route not yet chosen
- [ ] **Pick a route first, it is a design decision.** **A:** adopt REDUX's
  tables wholesale (genuinely real numbers, but ZW's Tiger 88 goes 175 -> 120 at
  point blank and every engagement changes). **B:** keep ZW's power levels and
  add realistic decay (far less disruptive, range starts mattering, still
  unrealistic up close).
- [ ] **Source historical figures for the ZW-only guns** — Pak 43, Flak 88,
  Panther 75 L/70, KV-85, KV-1, KV-1S, SU-122, SU-152, sIG 33, Nashorn, Hummel,
  Wespe, Marder II, StuG F8, Sturm-Haubitze, Pz II, Pz III L24. No REDUX
  equivalent, so these need finding and **showing before applying**.
- **Do NOT fix the Pak 43 alone** — see `TvT_Penetration_Tables.md`.
- **REDUX needs nothing here.** Its tables are already the real figures.

### 3. The King Tiger unit class
- [ ] ~1,800 lines, adapted from `TankPzVITigerE1Unit.script` (1,772 lines,
  70 classes). **14 class names are already dictated** by the shared files, and
  all armour/hitpoint constants exist. Point the mesh at `Cu_veh_KingTigerModel`,
  use `GunHvyPaK43`, uncomment `Editor/MenuConfig.script:229-230`, clear cache.
- [ ] Fill `Turret_A_NormalSet` in the model script — it names only
  `Body_commander`; the turret, gun, hatches and crew hands all exist in the mesh
  (confirmed 2026-08-26) but are not grouped, so the turret will not swap to its
  damaged state.

### 4. MS2 — the gate to ADDING geometry
- [ ] **Identify the `vcount * 24` block** (flag `0x40000`, 6 floats/vertex,
  almost certainly tangent+binormal). This is what stands between "reshape
  existing geometry" and "add geometry" — i.e. the King Tiger vision-port idea.
- [ ] Test the writer on a **skinned** mesh; the confirmed test was a static box.
- [ ] Does a shape change need the companion **`.rmap`** regenerating?

### 5. Lighting
- [ ] The **ambient pass** across the other 11 campaign missions — still the
  biggest open quality job. Include `AntiSunAngle`; it is a contrast control.
- [ ] **Shadow consistency**: 1M1, 1M3, 1M4, 2M3, 2M4, 2M6 need
  `StencilShadowColor`.

### 6. Performance
- [ ] **ZW is 36-60 fps and VIEW-DEPENDENT** — that points at frustum content,
  not per-unit cost. Profile the worst view against the best and diff.
- [ ] `Engine.dll` is 28.5% of the frame and has never been broken down.

## Ammunition scarcity - nothing in TvT models it (2026-08-26)

- [ ] **`AmmoQty` is used by ZERO missions.** The engine supports per-placement
  shell counts (`Object.script:351`, set from a mission's `Content.script`), but
  no vehicle in the game has a loadout. Historically the T-34/85 carried ~36 HE,
  14 AP and only **5 sub-calibre** - scarce tungsten held back for the worst
  targets. That constraint shaped real gunnery and is entirely absent here, for
  the player and the AI. Per-mission, so it can be tried on one mission first.
  **First check what the engine does when `AmmoQty` is unset** - unlimited, or a
  built-in default? Unverified. See `TvT_Mission_Authoring_Verified.md` s.16.
- [ ] **T-34/85 APCR looks generous.** REDUX gives 153.7 mm at 500 m where the
  usual figure is 138-140, and keeps it useful to 2000 m where real APCR fell
  off badly past ~1000. May be deliberate balance - check before changing.

## PERFORMANCE - next step is a QUESTION, not an experiment (2026-08-26)

- [x] **SOLVED: the 70-90 fps complaint was the LOS HOOK.** It cost ~10.9 ms a
  frame - 51 fps with it on, 115 with it off. Two `VirtualQuery` (= syscall)
  storms in `K:\tvt_los\hook.cpp`: `find_endpoints` ran up to 16,512 per vision
  check, and an ungated `CrewHook` sweep ran 256 per crew tick. **Fixed
  2026-08-26: LOS on now gives 120 fps, so the hook is free.** See
  `TvT_Performance.md`.
- [ ] **Switch off the `[CTRL]`/`[CREW]` debug dumps** in the LOS hook. They
  fire every 128 crew ticks and wrote 1,800 of 2,300 log lines in one session,
  each a file write on the game thread. Same category of leftover, much smaller.
- [x] **Map-lookup cache stays an OPT-IN CHECKBOX.** User's decision,
  2026-08-26, asked and answered. +6.3%, verified over 42 million calls with
  0 mismatches - but it is a live patch to a hot code path, and 6% does not
  justify injected code in the default play path. **Do not re-propose
  defaulting it.**
- [ ] Multi-entry map cache (4-8 entries vs the current 1). Hit rate is 67%;
  headroom is ~2%, below the +/-4% noise floor, so probably not worth it alone.
- [ ] **`Engine.dll` is 28.5% of the frame and has never been broken down.**
  Hot pages `+0x229000`, `+0x185000`, `+0x17D000`, `+0x168000`. The only large
  unexplored block left.
- [x] **CLOSED: native D3D9 vs DXVK.** +1.9%, inside noise. DXVK is free. Do
  not re-open.
- [x] **CLOSED: the 19-21% `NtWaitForAlertByThreadId` lock wait.** Real, and
  not recoverable - native pays the same through a different lock.

---

## SOLVED: tank commanders rendered black — `PlanarShadow` (2026-08-26)

Written up in `Documentation/TvT_Mission_Authoring_Verified.md` section 15.
**Not solved.** Seven candidates eliminated by test - texture, material, mesh,
scene ambient, stencil shadow colour, config-set name, lightmaps. It is
something in the skinned-mesh render path.

- [x] **FIXED.** `PlanarShadow = true` (plus `FakeShadow = true`,
  `FakeShadowScale = 0.1`) on `u_veh_PzVI_LATE.script` - **ported from ZW, where
  the commanders are not black.** ~50% improvement, confirmed in game. Found by
  DIFFING the two builds after the user observed ZW's were better, not by
  reasoning: same mesh, same DLLs, three model fields different.
- [ ] **Untested: do the other vehicles need it?** ZeeWolf enabled it on the two
  Tiger models ONLY - every other vehicle is DEFAULT in both builds, so there is
  no precedent for a blanket sweep. Test one (PzIVG or a T-34) before applying
  widely.
- [x] **Recorded: skinned meshes are missing 64 shader variants.** `SceneMesh`
  has 150, `SkinMesh1`/`SkinMesh4` have 86 each, and the 64 missing differ in
  exactly one character - position 4 `L` instead of `N`. A rendering feature
  (lightmapping, given `LightMap.fxo` sits alongside) that bone-animated geometry
  simply cannot use. Not the cause here, but a permanent capability gap.

**Measuring trap recorded:** the texture was first "measured" by averaging DXT1
endpoint colours across the whole file - 22% against the hull's 62% - and
reported as the cause. Meaningless: most of a character sheet is dark background
around the UV islands. The user opened the image and saw it was fine. **Sample
the region you care about, or just look.**

---

## Knowledge-base audit — findings that never reached a reference doc (2026-08-26)

The user's point: *"I should not have to prompt you to add this, it ought to be
automatic as I am sure we have missed a lot of findings over the last 2 weeks."*
Correct, and the audit confirms it.

**The structural problem:** `notes/` is session-scoped and dated
(`SESSION_2026-08-25`, `project_tvt_*_2026-08-25`). `Documentation/` is the
durable reference. Findings land in the first and are never promoted to the
second. **23 of 24 project notes are referenced from no reference doc at all.**

- [x] **`Documentation/TvT_Performance.md` created.** An entire domain had no
  reference doc - two days of profiling, disassembly, the map cache, the tools
  and the method lessons existed only in dated notes.
- [x] **Tree-shadow knowledge folded into authoring section 14.** Proof of the
  problem: `project_tvt_tree_shadow_limitation.md` documented
  `StencilShadowSettings` (`Settings.script` L64) two days before section 14 was
  written, and section 14 was written without consulting it.
- [ ] **Promote the rest.** Candidates, by destination:
  - authoring doc: `atmosphere_understanding`, `atmosphere_lighting_plan`,
    `dawn_rollout`, `c1m2_tigers_passive_by_design`, `pz4g_full_unit_swap`
  - performance doc: `lod_distances`, `tree_lod_tuning`, `speedtree_harvest`,
    `settreesize_hook_spec`, `resolution_finding`
  - engine/lineage: `wov_disabled_features`
  - **status, not reference - leave in notes:** `commercial_question`,
    `pb_campaign_reference`, `big_map_2d_campaign_layer`, `acquisition_parked`,
    the `SESSION_*` and `fps_bisect` files
- [ ] **Sweep the fortnight before 2026-08-25** for findings that never landed
  anywhere. The audit above only covers what is *in* notes; work discussed in
  session and never written down at all will not show up this way.

**The discipline, going forward:** a finding is not recorded until it is in a
`Documentation/*.md` reference. A dated note is a working file, not a record.

---

## Shadow consistency across missions (2026-08-26)

Model written up in `Documentation/TvT_Mission_Authoring_Verified.md` section 14.
**Three separate shadow systems**, plus `AmbientLight` which is not a shadow
setting at all but produces what players call one.

**THE RULE: `ShadowColor` and `StencilShadowColor` must match within a mission.**
They are the same physical shadow drawn by two different renderers - terrain and
buildings use the first, vehicles the second. The two missions anyone actually
finished (C1M2, C2M2) have them identical; every mismatch is an unfinished one.

- [x] **C2M1 harmonised.** Both now `(0.560, 0.580, 0.630)`, blue-tinted.
  `AmbientLight` also raised `0.120 -> 0.210` - C2M1 had the harshest
  ambient/sun ratio in the game (8.3:1), pairing the lowest ambient with the
  highest `SunIntensity`.
- [ ] **Six missions still need it: 1M1, 1M3, 1M4, 2M3, 2M4, 2M6.** Five never
  set `StencilShadowColor` at all, so vehicle shadows fall back to
  `BaseAtmosphere`'s `(0.3, 0.3, 0.3)` - the darkest value in the game and dead
  neutral grey. **1M3 is mismatched by 0.30** (`0.2` vs `0.5`).
  1M5/1M6/2M5 are within 0.03 and correctly near-white for overcast.
- [ ] **No Tiger gets a fake shadow.** `FakeShadows.script` sets
  `Cu_veh_PzVI_MAINModel::FakeShadow = true` but every Tiger uses
  `Cu_veh_PzVI_LATEModel` - `LATE` appears zero times in that file. Same shape
  as the `LodForShadowHide` bug. **This class does not appear in any log** - it
  is a valid assignment to a class nothing instantiates. One line to fix; left
  alone while other lighting variables were in flight.

### Not a bug: the commander is meant to be dark

`hum_German_Tankman.tex` is **22% average luminance** against the hull's 62%.
German panzer crews wore black. Light multiplies texture, so no ambient value
will make him bright without washing out everything else. Four rounds of
lighting changes were spent before measuring the texture - **measure the texture
first**.

---

## C2M1 second Tiger now follows the player (2026-08-26)

Findings written up in `Documentation/TvT_Mission_Authoring_Verified.md`
sections 10-13.

- [x] **Move it to the player's spawn in column.** Was 1,352 m away; now 40 m
  dead astern, same heading, `SurfaceControl PutonGround`. Position derived from
  the player's own matrix - **`xvec` (row 1) is the FORWARD axis**, proven by
  `FreePlayerCamera.script` placing the chase camera at `xvec * -20`.
- [x] **Make it follow.** `Formation()` on the TASK (groups only have an
  *internal* formation property), `(0,-40)` = dead astern, cruise
  `0.15 * GetMaxSpeed()`, re-issued every 8 s.
- [x] **Neutralise the five competing orders.** This is why previous attempts
  failed: `ActivateMovement(false)`, a delayed `Patrol` order, a
  don't-overtake distance gate issuing its own 4-navpoint route, and three combat
  phases each issuing `SetOrder_Move`. Radar / fire / aggressive reaction kept.
- [ ] **Play-test.** Does it keep up at speed? Is 40 m the right spacing? Both
  are one number. Its kill-list membership, bombing event and position watchers
  were left untouched and should still work.

### Found in passing, not fixed

- [ ] `BaseTasks.script` six-arg `SetOrder_Formation` (~line 1320) passes
  `_Displacement` / `_DistanceOptimum` / `_DistanceMax` - the parameter names of
  a *different* function. Its own are `_FormationVector` / `_PosDistanceOptimum`
  / `_PosDistanceMax`. Route around it via the eight-arg `Formation()`.
- [ ] REDUX's `CWingmanTask` still carries Whirlwind-over-Vietnam constants -
  200 m spacing with `z = 30`, which is *altitude*. ZW's were retuned; REDUX's
  were not.
- [ ] C1M4's sun X component has opposite signs in `Atmosphere.script` and
  `Content.script`, and has since 2001. `Content.script` wins, so harmless.

---

## ZW and REDUX have different performance problems (2026-08-26)

Write-up: `notes/project_tvt_zw_vs_redux_profile.md`. Only "CPU-bound with the
GPU idle" transfers between the builds; nothing else does.

- [x] **Profile ZW.** Its frame is `CAbstractObject` / `CAbstractJoint` /
  `CCylinderShape`+`CDynamicIntersector` (collision) at ~40%. **No vegetation
  page in the top 20.** REDUX's frame is vegetation at ~15% plus the map lookup
  at 20.4%; in ZW that same lookup is 2.9%.
- [x] **Why: the component census.** ZW carries 8.7x the objects (496 vs 57),
  4.6x the joints (2536 vs 550), 6.3x the cylinder shapes - and **one
  thirteenth the trees** (30 vs 380). Total components 84,143 vs 26,298.
- [x] **Why ZW's grass costs less, quantified.** 8.84% of frame in REDUX vs
  1.22% in ZW. Two causes that multiply: ZeeWolf tuned grass down (`MaxVisDist`
  150->120 and **`MaxVisDistPower` 5->8**, giving 3.35x less planted area), and
  ZW's longer frame dilutes the share a further 2.2x. 3.35 x 2.2 = 7.4x against
  7.3x observed.
- [ ] **UNPULLED LEVER: REDUX `MaxVisDistPower` 5 -> 8.** Should cut REDUX's
  grass cost ~3x while shortening apparent distance far less than the number
  suggests - near grass barely changes. **Not tried.** Predict the number first.
- [ ] ZW's collision cost (926 cylinder shapes + `CDynamicIntersector`) is
  unexamined. Its own thread, not today's.

### Assessed and rejected: "kill the stencil shadows for free performance"

From a shared Gemini conversation, 2026-08-26. Its structural model of the engine
was independently correct, but its performance claim is **measurably wrong**: no
shadow class appears in either build's profiler hot pages, and `ShadowFar` tuning
was worth ~2 fps. Emptying `StencilShadowSettings` would delete every vehicle
shadow and buy close to nothing.

- [ ] **Worth something instead: screen-space directional shadows.** Raymarch the
  depth buffer toward the sun so foliage can shade a tank - a capability the
  engine fundamentally lacks. **Not started.** If pursued: ReShade already does
  the hard part (readable D3D9 depth needs INTZ/DF24 vendor formats, and
  `ReShade32.dll` is already loaded here with depth confirmed working), while our
  DLL supplies the sun vector and matrices - we already hook
  `SetVertexShaderConstantF`. A full internal CSM means rendering the scene twice
  on the single core that is already the bottleneck: wrong trade.

**Do NOT tune ZW's grass** - ZeeWolf already did, and did it well.
**"Faster trees" is near-pointless in ZW** - tick it for REDUX only.

---

## C1M2 crash-to-desktop — FIXED (2026-08-25)

Write-up: `notes/project_tvt_c1m2_recursion_fixed.md`. A real CTD, diagnosed
2026-08-21, patch written 2026-08-22, **parked and never applied** — then it
crashed a live play session on the 25th.

```
Possible stack overflow warnings   6,451  ->  0
max stack depth                    1,391  ->  none
CC1M2Gr_NGerman_Infantry2 lines    1,395  ->  11
[ALARM] No orders in group           143  ->  4 (unrelated tank groups)
outcome                     crash to desktop -> clean exit, mission completed
```

- [x] **Patch 01 — `Scripts\Common\UnitGroup.script`, `OnOrderFulfilled()`.**
  One added condition: only resume a patrol if there is road left
  (`m_NextPatrolPoint < m_PatrolPath.size()`). An exhausted patrol now falls
  into the static-group branch, which calls `SetOrder_Stop()` and does not
  re-enter `RepeatOrder()`. Applied and confirmed **alone**, on its own test
  run, because this file is shared by every mission.
- [x] **Regression ruled out.** The risk was leaving groups inert after a fight,
  undoing the 2026-08-18 resume-after-attack improvement. Measured on the
  confirming run: **80 patrol resumptions, 0 `SetOrder_Stop`**. Groups attacked
  mid-patrol still resume their route.
- [x] **Patch 02 — `Missions\Campaign_1\Mission_2\MissionTasks.script`.**
  `ActivateMove(false)` -> `ActivateMovement(false)` (the misspelled name does
  not exist; `ActivateMovement` was verified real in `BaseTasks.script` rather
  than trusted from the note), plus a `RadarArmed` one-shot guard on
  `CC1M2Gr_NGerman_Infantry2::OnPathEndReached()`. Belt-and-braces — 01 already
  fixed the root cause.
- [ ] **Same `ActivateMove` typo in Campaign 2 Mission 3, line 932**
  (`ActivateMove(true)`) — patch_03 in `K:\TvTDeepseek\patches\REDUX_2026-08-22\`,
  **not yet applied**. Cosmetic (a logged error, not a crash), but it is the
  same one-word fix.
- [ ] **patch_04 (`MissionsMenu`) from the same parked set** — still unreviewed
  here. Note the standing warning about array edits in that file: a dangling
  comma in `MissionsMenu.script` once broke the game load entirely.

### The trap inside patch 02 — read before touching it again

The OLD block for the `RadarArmed` edit is **not unique on its first six
lines**: `CC1M2Gr_NGerman_Infantry1` (line 432) has a near-identical
`OnPathEndReached`, and a careless string replace patches the wrong group. The
full nine-line block including `fireEvent(... "AttackGermanInfantry2" ...)` **is**
unique and is the correct anchor. Verified by counting matches before replacing
and by checking Infantry1 was untouched afterwards.

### The bookkeeping lesson

A diagnosed, written, reviewed fix that is not on the board **does not exist**.
This one sat parked for three days, untracked in both TODO and CHANGELOG, and
cost a crash plus a wasted test session — the crash initially looked like it
might have been caused by an injected performance cache being trialled at the
time, and ruling that out took real work.

---

## Performance — where the frame time actually goes (2026-08-25)

Full write-up: `notes/SESSION_2026-08-25_performance_day.md`. Framerate went
36-40 to 66-76 over the session; the exact cause is **not** established and no
more theories are being built on it.

**The finding everything rests on:** TvT is CPU-bound with the GPU idle —
`Present` 0.1%, `Lock` 0.0%, 99.8% of the frame is CPU. Measured every run.

**Noise floor is ±4%** (three identical runs: 66.8 / 69.5 / 68.4 fps). Anything
below that is not a result. Say so.

- [x] **Build a draw-call probe.** `Tools/drawcall_probe.cpp`, hooks D3D9 and
  answers "CPU or GPU?" in one run. Every vtable slot verified against the SDK
  header before building. Killed the fill-rate hypothesis in ninety seconds.
- [x] **Correct the sampling profiler's numbers.** Its counters are cumulative
  since injection and never reset, so the headline figures included mission
  load. True steady state: Objects.dll 50-54%, Engine.dll 20-24%, J5Script ~2%,
  Behavior.dll ~0.5%, **D3D9 wrapper 0.0%**.
- [x] **Extract RTTI from the shipped DLLs.** 4778 named virtual functions /
  300 classes in Objects.dll, 4784/287 Controls, 2703/281 Engine. Any hot
  address now resolves to a class and vtable slot.
- [x] **Measure grass.** 1.8 ms/frame, 33,751 triangles, ~0 extra draw calls.
  Real but modest. In-game Video Options slider controls it.
- [x] **Measure tree rendering.** NULL RESULT — forest slider at minimum removes
  24% of draw calls and 27% of buffer traffic and changes frame time by 3.6%,
  i.e. nothing.
- [x] **Fix the Tiger shadow bug** (see its own section below). NULL RESULT for
  framerate — confirmed by reverting it deliberately.
- [x] **Trace the callers of `Objects.dll+0x17DD00`.** DONE — and it was **not**
  the target. That function runs **once per frame** (linear code, no loop:
  camera position + radius in, grid-cell range out). The 7.45% belonged to the
  4 KB *page*, which holds seventeen functions.
- [x] **Give the profiler 64-byte resolution.** `prof.cpp` now keeps a fine
  histogram over one configurable range (`FINE_BASE`/`FINE_LEN`, O(1) direct
  index, no scan). It put **89.65% of the whole region in one bucket**.
- [ ] **HOOK `Objects.dll+0x17DAB0` — COUNT CALLS AND DISTINCT KEYS PER FRAME.**
  ← the live target. That 128-byte function is **6.51% of total frame time**,
  about 87% of the hottest page, and it is a red-black-tree descent — textbook
  MSVC `std::map::lower_bound` (children `+8`/`+0xC`, int key `+0x10`). Eight
  instructions; expensive because every hop is a pointer chase, not because the
  instructions are slow. Six call sites: two in the `CSTForest` block (which is
  why tree pages stay hot at forest MINIMUM — the lookups happen per tree
  whatever is drawn), and **two inside the function whose failure path prints
  `"Cache miss"` — that map IS the cache.** The measurement answers which fix
  applies: few distinct keys -> flat array; repeating key -> memoise one result;
  otherwise hoist it out of the per-tree loop. **Measure before patching.**
- [ ] **Account for the remaining ~12 ms/frame.** Grass is 1.8, tree management
  ~1.5, and the rest has not been located. Everything obvious is excluded: GPU,
  lock stalls, draw-call submission, tree rendering, shadows.
- [ ] Consider `MaxVisDist`/`Density` tuning in `BaseGrass.script` if grass's
  1.8 ms is ever worth reclaiming. Low priority — it is small.

### Settings facts worth not relearning

- **`AlphaBlendDistanceFactor` is where the alpha fade BEGINS**, not where cheap
  alpha-test starts. The engine computes `1.0 / (1.0 - factor)` and its own
  hardcoded default is `0.8`. Lower = wider fade band = more transparency AND
  more cost. **Never set it to 1.0 — divide by zero.** Currently `0.9`.
- **DXVK vs dgVoodoo is irrelevant to framerate.** The wrapper is 0.0%.
- **The `.script` interpreter is not a bottleneck** (~2%), and **the AI is free**
  (~0.5%, including the LOS hook). Never hold back an AI feature for
  performance reasons.
- **SpeedTreeRT.dll itself is 0.04%.** The middleware is free; every bit of the
  tree cost is G5's own wrapper (`CSTForest`, `CSTTreesQuadTree`, `CTreeKiller`).


### SHIPPED — in the launcher, confirmed in both builds

- [x] **Injector now accepts up to 8 DLLs.** It took one, which is why Line of
  sight and Profiler were mutually exclusive — and making the cache a third
  exclusive option would have forced a choice between AI line of sight and +6%
  fps. The hooks touch different engine DLLs (`Behavior.dll` vs `Objects.dll`)
  and never meet. Each DLL is allow-checked against the list beside **itself**,
  so the opt-in rail is unchanged. Backup: `K:\tvt_probe\inject.cpp.bak_singledll`.
- [x] **Launcher checkbox: "Faster trees (map cache - about +6% fps)".**
  Combinable with Line of sight; Profiler still clears both, deliberately.
  Backup: `K:\TvTDeepseek\rollback\TvT_Launcher.ps1.before_cache_20260825`.
- [x] **Confirmed live in ZeeWolf 2015 with both hooks at once.** LOS reported
  `enforcement live` and its fit check passed on ZW's own terrain
  (+1.58..+1.59 m, spread 0.01); the cache ran 458,779,776 calls at 66.8% hits,
  **0 mismatches**, clean exit. The hit rate being ~the same in both builds
  (66.8% ZW / 67.2% REDUX) shows the access pattern is a property of the engine,
  not of either mod.
- [ ] **Multi-entry cache.** The current cache is ONE entry. The top 16 keys
  cover up to 51% of lookups, so a 4- or 8-entry direct-mapped table should push
  the hit rate past 67%. Same verify-then-activate safety, same self-A/B to
  measure it. **Predict the number before the run.**

**Cumulative cache record: ~3.6 billion calls, 4 sessions, 2 game builds,
0 mismatches.**

---

## Tiger shadow bug — fixed, and the bug class closed (2026-08-25)

Write-up: `notes/project_tvt_shadow_bug_2026-08-25.md`.

- [x] **Fix `Cu_veh_PzVI_LATEModel::LodForShadowHide`.** `ShadowHide.script:45`
  set it, but `Models\u_veh_PzVI_LATE.script` never declared the field — the
  only model file of the set that omits it. Silent "invalid LValue", so every
  Tiger kept `DefaultLodForShadowHide = 9999` ("never hide") and behaved unlike
  every other tank. `TankPzVIAusfEUnit::getMeshObjectName()` returns that model
  unconditionally, so it was every Tiger in the game. **ZeeWolf's copy already
  had the line.** Worth **zero** framerate — confirmed by reverting it.
- [x] **Sweep for the same bug class.** Every `Class::Field = value` assignment
  in both installs checked against whether the field is declared on the class or
  an ancestor. REDUX (2390 classes): none. ZeeWolf (4957): none. Tool validated
  against the known bug first, so that is a real negative.

---

## MAIN LINE — give the AI line of sight (2026-08-19)

Agreed with the user as the single highest-leverage flaw in TvT as a tank sim.
Everything else is support or polish. Two write-ups:
[the engine side](Documentation/RE/TvT_Vision_Model_Decoded.md) and
[the maths](Documentation/TvT_Line_Of_Sight.md).

- [x] **Decode the vision model.** `Behavior.dll + 0xC9E50` is the whole of it,
  752 bytes: state × angle curve × range curve × modifier list, then
  `rand() < 1 - pow(1 - v, dt)`. Two-component vector maths throughout; the
  observer's Z is passed in and never read. **No ray, no terrain sample, no
  foliage test anywhere in the engine.**
- [x] **Find where occlusion goes.** The function already walks a list of
  0x1c-byte modifiers, each of which may multiply visibility by a factor and
  bail out at zero. Occlusion is one more modifier returning zero — no new
  subsystem, no fight with the architecture.
- [x] **Build the LOS maths and check it against real missions.**
  `Tools/LineOfSight/canopy_los.py`. Terrain from `hmap.raw`, vegetation as
  accumulated optical depth rather than a canopy ceiling (a ceiling wrongly
  blinds anyone standing inside a wood). Canopy heights are the engine's own —
  every stock `Terrain.script` registers a 17 m vertical forest for `Forest01`.
- [x] **Build the watcher.** `Tools/LineOfSight/hook.cpp`. Calls the original,
  returns its answer unchanged, records what was asked and answered. Sandbox
  only, enforced in both the injector and the DLL.
- [x] **Run it.** Done repeatedly. Confirmed working: enforcement live before
  the first vision call, mission auto-identified from the engine's own log, and
  74% of the engine's positive sightings refused on Campaign_2/Mission_5.
- [x] **Influence one decision.** Settled by the blunt version instead - total
  blindness, `deny_far` with `deny_beyond = 1`. 7448 of 7448 positives denied
  and **every AI unit fell silent**, so `FUN_100c9e50` is confirmed as the gate.
- [x] **Port the march into the hook.** Done, `Tools/LineOfSight/terrain.h`,
  checked against the Python offline by `test_terrain.exe` rather than by
  burning game runs.
- [x] **The player's crew now has line of sight too.** It was a SECOND vision
  system that `FUN_100c9e50` never touched, which is why occlusion changed
  nothing visible from the cockpit. `CAutoShooterComponent`'s per-tick update is
  vtable slot 7 at RVA 0x4B1E0; its whole target acceptance is one distance
  comparison against `RadarMaxDistance` (+0x154, measured live) with no
  geometry. Fixed by redirecting the single `call` at 0x1004B400 - the length
  helper it calls has 80 callers and must not be hooked itself. **6000 checks,
  4069 refused, 0 unmatched.** Endpoints found by matching the arithmetic rather
  than hardcoded stack offsets, which never failed once.
- [ ] **`CAutoCommanderComponent` — acquisition, and the best home for
  penetration.** The gunner fix changes RETENTION, not acquisition: in the
  commander's seat you can only designate what you can already see. The AI
  commander designates whenever the player is NOT commander, and it is the class
  holding `PreferedTargets` - so it is both where terrain-blind acquisition
  lives and the natural place for "can I actually hurt it from here". Vtable RVA
  **0x248D98**; same technique as the two hooks already working.
- [ ] **Replace `RadarMaxDistance` with "can I get through?"** TvT already holds
  penetration-vs-range per ammo (`Piercing.script`) and armour per facet
  (`Armour.script`); `Tools/LineOfSight/can_i_kill.py` computes the answer today
  and it comes out historically correct with no tuning - a T-34/76 can only kill
  a Tiger from the side inside ~300 m. The missing input is which facet is
  presented, which the engine has and the script layer does not. Same shape of
  job as the vision hook.
- [ ] **Tune the sight-through distances** against play. Recalibrated twice so
  far; `sight_scale` in the ini moves them all without a rebuild.
- [x] **Run the LOS work on ZW2015 too — DONE 2026-08-20, not yet play-tested.**
  `Behavior.dll`, `Engine.dll` and `UI.dll` are byte-identical to REDUX's
  (SHA-256 checked), so both hooks land on the same addresses and nothing
  needed rebuilding for ZW itself. Enabled by adding `M:\T34vsTiger_ZW2015` to
  `tvt_los_allow.txt`; launch with `K:\tvt_los\play_zw.bat`, settings in
  `M:\T34vsTiger_ZW2015\tvt_los.ini` (its own file, because ZW's woods are
  planted more thickly — same forest classes, denser species mix — and may want
  a lower `sight_scale`).
  1. **DONE — and the premise was wrong in a way worth recording.** ZW's maps
     are not "18000": they run **9000, 12000, 18000, 20002 and 36000**, and
     `MatrixWidth` now comes from each mission's own `WorldMatricies.script`
     rather than any constant. **REDUX was already affected**: `SteppeTemplate`
     and `SteppeQuickMission` are 18000 m, so the shipped tool had been
     silently computing every position on those two at half scale. Verified
     against four maps, C and Python agreeing exactly: Berezov 9000/2049
     (4.395 m), Steppe 18000/2049 (8.789 m), ZW Campaign_2 Mission_1
     18000/2049 with 2048 zones, ZW Kursk **36000/4097** — a larger heightfield
     than TvT itself ever ships. The identified world size is now printed in
     the log as `world NNNN m across`.
  2. **DONE** when LOS shipped live: the rail is an allow list beside the DLL,
     checked independently by the injector and the DLL.
  3. **DONE** at the same time: log, ini and mission-search paths all derive
     from the running executable's folder.
  4. **STILL OPEN, and it is the one thing to watch on the first ZW run.** The
     fit test assumes origin offsets measured on REDUX units (+0.85 m soldier,
     +1.65 m Tiger). ZW has its own models and they may sit differently. If the
     fit check reports offsets far from +1.4..+1.7 m, that is the reason, and
     the DLL will correctly fall back to watch mode rather than enforce against
     a bad fit.

  Worth doing because the exchange already runs both ways: today's near-plane
  fix was REDUX knowledge applied to ZW, and the depth work transfers back the
  same way.

- [ ] **Cache and stagger.** Never ray-test per observer per target per frame.
  Ray-test only pairs that survive the existing distance and angle gates, cache
  the answer, refresh on a stagger. The game is CPU-bound (90 fps, 450 draw
  calls, GPU 29%) — adding raw CPU work is the one way to get this wrong.

**Constraint, do not forget:** `Behavior.dll` relocates ~237 MB from its
preferred base. Resolve addresses at runtime (`GetModuleHandleA` + static RVA).
A hardcoded address is what killed the November 2025 attempt — whose
`tvt_los_hook.dll` (18 Nov 2025) is still sitting unused in the live game root.

**Also worth knowing:** `this+0x1A` is a byte that switches the entire vision
check off — zero means everything is visible, unconditionally.

---

## One-map dynamic campaign (2026-08-19) — the parts exist

The user's long-standing idea: one large terrain, start at one end and advance
across it, where the next mission depends on how the last went. Feasibility
established, see
[Documentation/TvT_Campaign_Scale_And_Persistence.md](Documentation/TvT_Campaign_Scale_And_Persistence.md).

- [x] **Establish the engine's real world size.** WoV ships **81,000 m** maps on
  a **4097** height grid — 81x TvT's area. The 9 km map is a G5 decision, not a
  limit.
- [x] **Establish that one terrain can serve many missions.** WoV's eleven
  Campaign_1 missions all reference `Missions/Campaign_1/hmap_c1.raw`.
- [x] **Establish what carries between missions: nothing.** `Campaigns.rsr` is
  localised names only; `IPersistent` is object-level within a session; no save
  files or registry state in either game.
- [x] **Find the death event.** `Common\Mission.script` handles every object's
  death with `GetLastDamager()` for attribution. The `m_PlayerVictims_*`
  counters are player-only, but the event is not, and `EndMissionMenu.script`
  already reads the totals.
- [x] **PROVEN: a mission can load another mission's terrain.** Tested by
  pointing BerezovKursk's `WorldMatricies.script` at Berezov's `hmap.raw` in the
  sandbox. Loads clean, terrain visibly different, no engine complaint. This was
  the gate on the whole design and it is open.
- [x] **LOS tooling must read the terrain path, not assume the folder — DONE
  2026-08-20.** `find_height_file()` in `terrain.h`, mirrored in
  `canopy_los.py`, reads `ImageFileName` out of the mission's
  `WorldMatricies.script`, resolves it against the game root, and falls back to
  `<folder>\hmap.raw`. This was not only a shared-terrain concern: **ZW names
  its heightfields `hmap1.raw`**, so the old test skipped every such mission
  entirely — including the whole `CustomMissions` set. The mission-candidate
  scan now recognises a mission by the presence of `WorldMatricies.script`
  rather than a file literally called `hmap.raw`. Zone bitmaps are still found
  by globbing `TerrainZone*.bmp`, which works on every mission in both builds;
  reading those from the script too is a tidy-up, not a fix.
- [ ] **Log casualties.** One `logMessage` in that handler, before the
  `Killer == MainPlayerID` test, gives every death on both sides with
  attribution in `execution.log` — a file the tooling already parses.
- [ ] **Build one large Kursk terrain** rather than a 9 km island per mission.
  `K:	vt_terrain\make_map.py` generates them; the work is going bigger and
  siting missions by coordinate. Note the LOS march must read grid and cell size
  rather than assume — range is 4.4 m to 19.8 m cells, 2049 to 4097 grids.
- [ ] **The theatre layer — a Falcon 4 style bubble.** The user's framing, and
  it is the right one: simulate the whole sector, and the mission you play is
  the bubble. Battles outside it resolve abstractly and their outcomes move the
  line you fight on next.

  **Why this is easier here than it was for Falcon.** Falcon had to move units
  in and out of detailed simulation *while running* - a statistic becoming a
  rendered aircraft mid-session, with state handed over cleanly. That is where
  its complexity and most of its bugs lived. Here the mission IS the bubble and
  the boundary is the mission load, so everything outside resolves in Python
  between missions. Most of the payoff, none of the hardest engineering.

  **Two properties make it real rather than cosmetic:**
  - *One terrain means one coordinate space.* A regiment at (34000, 21000) in
    the theatre model is at (34000, 21000) when a mission loads there. No
    translation, no "roughly the same area". The abstract map IS the ground.
  - *The abstract combat can use the same physics.* `can_i_kill.py` already
    computes penetration against armour by range from the game's own tables, so
    an off-bubble battle resolves by exactly the numbers an on-screen one would.
    That is normally where dynamic campaigns feel fake - two different games
    wearing the same skin. Here it is free.

  | piece | status |
  |---|---|
  | Theatre state: units, positions, strength, supply | new, Python |
  | Off-bubble combat resolver | new, built on `can_i_kill.py` |
  | Generate a mission at a chosen contact point | **exists** |
  | Read the outcome back | **~5 lines** + log parsing |

- [ ] **BUILD THIS FIRST, not the theatre.** Two missions, one shared terrain,
  where mission 1's outcome visibly changes mission 2's starting positions.
  That is a weekend, and it proves or kills the whole architecture at once -
  shared coordinate space, outcome capture, state carry, regeneration. If it
  works, going from two missions to a front is content and tuning. If it does
  not, a weekend is lost rather than six months.

  *Every dynamic campaign that died, died from being built middle-out.*

- [ ] **Campaign state in Python.** Read the casualties, work out survivors,
  generate the next mission on the same ground. No engine work.
- [ ] **Open question:** survivors' final positions are not logged, only deaths.
  Either log them from the mission script, or start each mission from planned
  lines rather than exactly where the last stopped.

---

## Issue tracker audit (2026-07-03)

- [x] **German distance-callout voice lines were entirely broken, not just the 100/200 mix-up GitHub issue #11 described — fixed 2026-07-03.** Issue #11 diagnosed `Dialogs.script`'s German distance table as calling `g_200.wav` for both the 100m and 200m callouts. Checked the actual `Resources/` folder: neither `g_100.wav` nor `g_200.wav` (nor any `g_XXX.wav`) exist at all — the real files are named `GDistance100.wav`, `GDistance200.wav`, etc. (original G5 2008-dated assets). So **every single entry** in the table (100 through 1600, 16 entries) pointed at a nonexistent file, not just the one pair the issue caught. Applying the issue's suggested fix verbatim would have just traded one missing file for another. Fixed all 16 entries to reference the real `GDistanceXXX.wav` filenames. No equivalent Soviet-side table exists in this file to check.
- [x] **Shadow settings missing in model headers (GitHub issue #4) — checked 2026-07-03, turns out to be largely already resolved.** Not the same bug as the "shadow visible through terrain ridge" issue from earlier this session (which was fully investigated, 3 attempts tried, fully reverted) - don't conflate the two. Grepped all 75 model scripts in `Models\` for the 7 fields the issue names: every real gameplay model (buildings, units, weapons, vehicles) already has all 7. The only files missing any of them are skyboxes (`Sky_*.script`) and dev/test scaffolding (`Background.script`, `Landscape_test.script`, `Test_House*.script`, `sphere_test.script`, `4MeterBox.script`) - none of which cast shadows, so that's correct, not a gap. The 6 per-model "shadow init" scripts (`Shadows.script`, `PlanarShadows.script`, `PlanarShadowsLodShift.script`, `FakeShadows.script`, `ShadowsChange.script`, `ShadowHide.script`) already carry a "Redux Added Missing Models" comment, i.e. someone already did this completeness pass. **Did find and fix one real bug while checking**: `ShadowHide.script`'s Nebelwerfer entry had a copy-paste typo setting `LodForShadowChange` (redundant, already set in `ShadowsChange.script`) instead of `LodForShadowHide` - meaning its actual `LodForShadowHide` was silently defaulting to `CBaseModel::DefaultLodForShadowHide` (9999.0f, i.e. shadow never drops to a cheaper LOD at distance), unlike its Pak40/Zis-3 static-gun siblings which correctly use 2.5. Fixed. Trucks' `FakeShadow = false` in `FakeShadows.script` is NOT a gap - confirmed deliberate by the earlier ridge-shadow investigation (enabling it broke all model rendering). Recommend closing the GitHub issue with this explanation - not yet done, pending user confirmation (same pattern as the other issue-tracker closures this session).
- [x] **Duplicate T-34/85 MS2 model + Unit script (GitHub issue #7) — scoped and resolved 2026-07-03, no in-game testing needed after all.** Two file sets in `Models\`: `u_veh_t34_85_44.ms2`/`.script` (2007) and `u_veh_t34_85_44_2.ms2`/`.script` (2006). Code evidence alone settled it: the 2007 set is the live model, directly wired into the real playable/AI unit (`Units\T34_85_44.script:1306`, `SetupExtendMesh("Cu_veh_t34_85_44Model", ...)`) and the only one with cockpit-camera/hatch joint wiring (`CockpitCameraDriver`, `Luk_A`) needed for the driver's interior view. The 2006 `_2` set uses nearly identical textures/skin to the 2007 one (same hull/turret/track skins) but has **no cockpit-camera or hatch joints at all** - an old pre-cockpit-support export, not a distinct tank variant, unlike the genuinely-unfinished cut-content roster (`TankPzVI_LATE`, `T34_76_41`) which have real distinct stats waiting to be finished. Confirmed it was never wired to any Unit gameplay class, never placed in any mission, and not in the Editor's placeable-object list - only referenced in 8 generic per-model housekeeping scripts (`Shadows.script`, `FakeShadows.script`, `PlanarShadows.script`, `PlanarShadowsLodShift.script`, `ShadowsChange.script`, `ShadowHide.script`, `Instances.script`, `Intersections.script`, 10 lines total), which were removed. The two orphaned files themselves were moved to `Models\_Removed\` on the live install (not hard-deleted - an auto-mode safety check correctly declined to let a model-derived-target file deletion proceed without the user explicitly naming the files, so they were relocated instead, fully reversible).
- [x] **Intersection script entries missing for models (GitHub issue #8) — scoped and partly fixed 2026-07-03.** Header-completeness half already resolved, same as issue #4: every real gameplay model already declares both `UseBoxForIsection`/`UseShapesAsWalkedMesh` in its header; only skyboxes/dev-test scaffolding lack them, correctly. The real gaps were in `Common\Intersections.script`'s per-model override list: (1) `Cfence_PoleModel` had zero entries at all despite its siblings (`Cfence_WickerModel`/`Cfence_PalisadeModel`) both being set - added `true`/`false` matching the static-prop pattern. (2) Two tanks' `UseBoxForIsection` lines were commented out with a note "creates error in execution log" - turned out to be a genuine typo, not an engine issue: `= fasle;` (misspelled "false", an invalid identifier) instead of `= false;` - confirmed via a full-codebase grep that `fasle` appears nowhere else. Uncommented and corrected both (`Cu_veh_PzIVGModel`, `Cu_veh_t34_76_42Model`), matching every other tank's existing `false`/`true` pattern. **Left alone, flagged as open questions rather than guessed at** (matching Stevan's own "assumption, needs testing" caveat on the whole issue): the two cockpit-interior `_Inside` extend-mesh models (`Cu_veh_PzVI_MAIN_InsideModel`, `Cu_veh_t34_85_44_InsideModel`) have no entries either, but are attached submeshes not standalone collidable objects, likely correctly exempt; and `Chum_GermanTankmanModel`/`Chum_SovietTankmanModel` (real AI Unit classes) are set as "static" (box=true) while the analogous `...SoldierRifleModel` infantry are set as "moving" (walked=true) - could be intentional (fixed hatch pose) or a real inconsistency, genuinely unclear without in-game testing.
- [ ] **Control settings not saving (GitHub issue #3)** — "change ammo"/"load ammo" key bindings don't persist across restart. Not investigated yet.
- [ ] **Compass / heading indicator - PARKED 2026-08-19, reverted, but a real possible.**
  WoV (same engine) has a working compass; TvT ships most of the parts and uses none
  of them. Everything below was measured, so a later attempt does not have to repeat it.

  **What TvT already has:**
  - `Scripts\Common\Navigator.script` defines `CBaseNavigatorScreen` and
    `CNavigatorScreen_Uh1` - near-identical to WoV's, one line apart - including a
    full compass layout (`ElCompassBar`, tiles, azimuth text, N/E/S/W labels).
  - `NavBar` is an engine-native class (`new #NavBar<CNavigatorScreen_Uh1>()`) and the
    string is present in **all four** TvT engine binaries, so this build registers it.
  - `Cockpit.script` has an `OnCompassChange(float)` handler - an **empty stub**.

  **What was tried, and what each attempt proved:**
  1. Created the NavBar in `SetupCockpitUIControls` following TvT's own control idiom.
     **It rendered** - a compass bar with tiles and an azimuth readout appeared. So the
     native class exists and works in this build.
  2. Filled the `OnCompassChange` stub to call `NavBar.SetCompassAngle(_CurrentAngle)`.
     The readout sat at **89**, which is the `CompassAngle = 90.0` default in
     `CNavigatorScreen_Uh1` - i.e. never written.
  3. Registry: `HKCU\Software\G5 Software\T34\IntelligentCompass` is `0`, while WoV's
     is `1`. Setting it to 1 changed nothing - the engine still logged
     `bIntelligentCompass: false`. **The setting is forced off in the TvT build.**
     (Confirmed the engine does read that key: ScreenWidth, RefreshRate and
     CockpitDevicesColor all match the registry exactly.)
  4. Instrumented `OnCompassChange` directly. **Zero calls across two missions.** The
     engine never fires it in TvT. This is the finding that matters.
  5. Re-driven from `OnWeaponDirectionChanged(_HAngle, _VAngle)`, which demonstrably
     does fire (it drives the target pointer). Result: **one call, `HAngle = 0.0`, then
     nothing.** It does not carry a live traverse angle either.

  **Why a fresh attempt is still plausible:** the heading exists somewhere - the engine
  renders the world from it. The remaining routes are (a) find another cockpit event
  that carries orientation, (b) read the player object's matrix directly, which needs
  `getPosition(user).xvec` **and an inverse trig function the .script language does not
  appear to have** - only `sin` and `cos` were found anywhere in the codebase, or
  (c) compute it natively via the injection toolchain (`K:\tvt_probe`), which already
  reads live game memory.

  **Positioning note for whoever retries:** there are TWO bars - `ElCompassBar` (the
  tape) and `ElCompassBar2` (the azimuth readout). Both default to y=0.95833, the
  bottom of the screen, which is where WoV puts it for a helicopter. Move both or they
  end up at opposite edges. The user prefers the default black - it reads well against
  the sky - and the white centre number comes from `CI_LIGHT`, which is off-white in
  all three colour schemes, so blackening it means editing `ColorMap.script` and
  affecting everything else that uses `CI_LIGHT`.

  **The engine DOES have the heading - user's observation, checked and confirmed.**
  Map icons rotate with the tank. `Editor\TerrainMap.script` declares behaviour masks
  `BEH_FIT_MAP` and `BEH_NOT_ROTATE_TEX`, the latter being an opt-OUT - so rotating
  with the object's heading is the DEFAULT, and the player icon (`PLAYER_BEHAVIOR`)
  does not opt out. `OrientationMode` (0/1) in the settings is north-up vs heading-up
  for the whole map.

  This rules out "TvT does not track heading". It tracks it per object per frame. But
  script only hands the map a behaviour *mask* - the native renderer reads each
  object's matrix itself, and no angle is ever passed back. Same wall: the number
  exists only on the C++ side.

  **Best remaining route: the injection toolchain** (`K:	vt_probe`), which already
  reads live game memory and locates objects by RTTI. The player tank's matrix is
  exactly what it was built to find. Cheaper thing to try first: look for a native
  control method that takes an OBJECT rather than an angle - a "track this object"
  mode on NavBar would sidestep the whole problem.

  All changes reverted 2026-08-19: `Cockpit.script`, `Navigator.script`,
  `GameSettings.script` restored from backups, registry key set back to 0.

- [ ] **Gun emplacement geometry - waiting on a hand-placed reference (added 2026-08-19).**
  The user is hand-placing gun positions in one mission in the Editor, to be used as the
  ground truth for what a correct emplacement looks like. **Do not guess at these offsets
  again - measure the user's version and encode it.**

  When it lands:
  1. Find the mission by `Content.script` mtime under `Missions\MyMission\`.
  2. For each gun, compute every attached object's offset in the GUN'S OWN local frame
     (forward / left / up), not in world coordinates - `emplace_guns.py` already has the
     maths for this, and world offsets are meaningless because every gun faces differently.
  3. Compare against the current constants in `Tools/MissionGen/emplace_guns.py`:
     `BARRICADE_FWD 0.8`, `SANDBAG_FWD 2.2`, `SANDBAG_SIDE 2.6`, `CREW_BACK 2.5`,
     `CREW_SIDE 1.3`, `TRUCK_BACK 26.0`, `TRUCK_SIDE 4.0`.
  4. Replace the constants with the measured ones and re-run across all missions.

  **The specific problem to solve:** the gun must be able to fire over its own barricade.
  The user could not clear it until the barricade was lowered. Note that most of the
  apparent height error was the Z bug (`0.0739` unflipped vs the correct
  `flipped_raw * 0.07`, ~32 m), now fixed - so re-measure on corrected content rather than
  assuming the old symptom still applies. There may still be a genuine
  barricade-height-vs-gun-barrel clearance issue underneath it.

  **Stretch goal the user actually asked for:** make a gun position a *self-contained
  unit* that can be placed as a whole, rather than a gun plus five loose objects placed
  by offset. Stock missions carry `ObjectsGroup` entries in `Content.script` (9 in the
  shipped campaigns) which may be exactly this mechanism - worth checking before building
  anything custom.

- [ ] **PARKED 2026-08-18 (user's call - no audience).** An exporter serves people building new
  models for a 2001 game, and that set is empty; the mission generator attacks the real
  complaint ("6 missions per side") instead. The format itself is SOLVED and the Blender
  add-on v1.2.0 is installed and working - see the findings doc. Restart only if a TvT
  community appears. One bug remains open if it is: `Turret_A` renders as a cone from the
  turret body to the barrel tip; four theories already dead; per-joint vertex positions all
  measure sane, so suspect the triangle/index side (the `other_count x 16` block after the
  indices is the best next candidate, possibly a sub-mesh table).
  **G5 Maya Exporter / `.ms2` format reverse-engineering (GitHub issue #12) — Phase 0 (documentation) AND Phase 1 (empirical byte probing) both underway 2026-07-03, real progress made.** Phase 1 findings: `Documentation/MS2_Binary_Format_Findings_2026-07-03.md`. Confirmed (checked against 62/62 sample `.ms2` files, and cross-verified against a known-geometry test case - the exact cube from the tutorial screenshots): a universal 12-byte-plus-name file header (version=0 constant, a node/object count that scales cleanly with model complexity 1→335, then a length-prefixed name string taken verbatim from Maya); a bounding-box + bounding-sphere block immediately after the name (radius exactly matches `halfExtent×√3` for the cube); and - the big one - the **complete vertex position/normal/UV/triangle-index layout for a single-node mesh, closed-loop verified**: 24 vertex positions (matches a hard-edged cube's 4-per-face×6-faces), 24 normals (all exactly 0/±1, the 6 axis-aligned face normals), 24 UV pairs, then 36 uint16 triangle indices (exactly 12 triangles = a cube's 6 quad faces × 2 triangles, every index valid 0-22). Also found: `u_veh_t34_76_41.ms2` (the already-known cut-content T-34/76 variant) has an anomalous root node name (`locator1` not `ROOT`) and far fewer nodes (14 vs 216-335 for finished tanks) - an independent binary-structure confirmation of something already suspected from the separate `.script`-class-usage audit. Also clarified: materials/textures are NOT embedded in `.ms2` at all (searched for the known tutorial texture name, not found anywhere) - they live entirely in the companion `.script` files, which are already fully understood, no RE needed there. **Still open**: ~780 trailing bytes in the sample file (roughly half its size) unidentified; the multi-node record boundary (everything confirmed so far is only for a single-node file); skin/joint/animation layout; the unknown 4-float block right after the bounding sphere. **Continued same day**: examined `Sky.ms2` (2 nodes) and confirmed the multi-node layout is simply a flat `[name][data]` sequence per node, found via the same string-scan technique. `Root` (an empty container node, no mesh of its own) has bbox min/max = exactly `FLT_MAX`/`-FLT_MAX` and sphere radius = `-1.0` - classic "no geometry computed" sentinels, a strong independent confirmation of the bbox/sphere field identification (real values for the cube, recognizable "empty" sentinels for a node with nothing in it). Found a likely parent-node-index field (`-1` for root) and a possible child-count field, tentative. Confirmed the bbox/sphere pattern again on `SkyDome` (a real, asymmetric dome mesh, not just the symmetric cube) - bounding box and sphere both come out as sensible, correctly-asymmetric real-world values. The 4-float "pad" field is zero in 3/3 samples now, looking more like reserved/unused than a per-object pivot. **Next real blocker**: no vertex/triangle count field has been found yet for real mesh nodes (only inferred for the cube because its vertex count was known in advance) - this needs solving before the format can be decoded for arbitrary meshes.

**PHASE 2, same day: ground truth via actual decompilation of `MayaExp.mll`.** User asked to move from empirical byte-probing to real decompilation. Set up Ghidra 11.1 headless (already installed at `M:\TvT 2024 working folder\ghidra_11.1_PUBLIC_20240607` but needed a JDK - none was installed on the machine, only JREs - downloaded the official Eclipse Temurin JDK 21 zip, no installer, extracted to `M:\TvT 2024 working folder\jdk-21-portable`, pointed Ghidra's `launch.properties` `JAVA_HOME_OVERRIDE` at it). Traced the real call chain from `initializePlugin`'s `MFnPlugin::registerFileTranslator`/`registerCommand` calls (confirming the exporter uses Maya's file-translator API, matching the tutorial's own "Files of type: G5 Model Exporter" dropdown) through to the actual `exportG5Resource` command's `doIt()` implementation, which dispatches to a model-export function. That function **fwprintf's the `Models\*.script` Model-class boilerplate line for line** - confirmed, with certainty rather than inference, that the `static int InstancesQty = CBaseModel::DefaultInstancesQty;`-style header lines already known from the issue #4/#8 audits are literally auto-generated by this tool. It then calls the real `.ms2` binary writer, decompiled in full.

**Ground truth structure found** (see `Documentation/MS2_Binary_Format_Findings_2026-07-03.md`'s "Phase 2" section for the complete field-by-field breakdown): confirmed Phase 1's core findings exactly right (name, bbox, sphere, flag, vertex_count, index_count, positions/normals/uvs/indices arrays) - but found real fields Phase 1 completely missed: an always-present `other_count x 16 bytes` block right after the indices (very likely the real explanation for Phase 1's "unexplained leftover bytes" mystery), an always-present `d_count`-driven pair of arrays, a `node_id` field (confirmed via real vehicle data to be **the parent node's index in the file** - Phase 1's "parent_idx" theory was directionally right but wrong about where in the byte stream it sits), and a `flags_bitmask` field gating six further optional data blocks whose byte sizes are known exactly from the decompiled code but not yet validated against real content. Built `Tools\MS2Format\ms2_parser.py` implementing this - **4 of 9 test files parse to an exact byte match with zero leftover** (every file with `flags_bitmask=0`). Tested against a real shipped tank (`u_veh_t34_85_44.ms2`, 219 nodes) and confirmed the `node_id`-as-parent-index theory cleanly against real hierarchy (`Body_2_LOD4`'s `node_id` correctly points to `Body_2`'s own index, etc.) - also confirmed real production content always sets `flags_bitmask != 0`, meaning the six optional blocks genuinely matter and aren't just theoretical. One concrete discrepancy found and documented: the `0x40`-flag block's second array doesn't appear to actually be written, contradicting the naive decompiled prediction. **Next step**: use real vehicle files (which actually exercise the optional blocks) rather than only simple test files to pin down the remaining six flag-gated blocks.

**PHASE 2 CONTINUED, same day: `flags_bitmask` decoded bit-by-bit by tracing the actual Maya-attribute-reading code, not guessing.** Found `FUN_1008d120`, the function referenced by nearly every mesh boolean attribute from Phase 0's `addMeshProperties.mel` list, and decompiled it directly - gives a definitive, named mapping for most of the field (e.g. `IsCollisionMesh`->bit 0x4, `IsWalkMesh`->bit 0x20, `IsHidden`->bit 0x80, `IsSelfLOD`->bit 0x20000, `DoNotCastShadow`->bit 0x400000, etc. - full table in the findings doc). Critically, traced one of the mystery optional-block-gating bits (`0x40`, paired with `0x1000000`) to `HasShadowVolume` - and decompiling the huge function that runs when this is set (`FUN_1004ea70`) confirmed it's a real shadow-volume silhouette-edge/BSP builder (iterates mesh edges, flags non-smooth/hard edges for silhouette extrusion, builds a BSP structure) - conclusively identifying that optional block's PURPOSE (precomputed shadow-volume geometry) even though its exact 52-byte-per-record internal layout isn't pinned down yet. Also found `IsDoorObject` belongs to a completely separate joint/hinge subsystem, not this bitmask at all - a useful negative result. **Still unmapped at that point**: 5 of the 8 block-gating bits had known byte sizes but no traced source attribute - none of Phase 0's known mesh attributes fed them via the attribute-reader function.

**PHASE 2 FINAL PUSH, same day: all 8 block-gating bits now identified.** Rather than keep tracing call graphs by hand, scanned every instruction in the whole binary for an `OR` against each specific remaining bit constant - a handful of direct `OR dword ptr [reg+8], CONST` hits (matching the flags_bitmask struct-field pattern exactly) pinpointed the real setter function for each bit immediately. Decompiling those functions gave real, evidence-based identifications (not guesses) for the remaining bits: `0x10` = bone/joint attachment data (confirmed by an adjacent "Add bone for attach" log message), `0x800` = skin blend-weight data (confirmed by an "incorrect numbers blending informtion" [sic] error message in the exact same code path), `0x4000` = "this joint's mesh is cloned from another joint" (confirmed by a "This joint clone mesh from %i joint" log message), `0x10000` = very likely per-joint bind-pose transform matrices (the setter function initializes each 80-byte record with textbook identity-matrix float patterns), `0x40000` = very likely `ExportTangentSpace` (the setter is a trivial one-line passthrough of a single boolean, and process of elimination against the known `exportG5Resource` parameters points here). `0x200`/`0x400` are confirmed to be real, structured joint/skinning-adjacent data blocks (92 and 112-byte records) but not yet identified by exact purpose. **This closes out the flags_bitmask investigation almost completely** - every bit now has at minimum a confirmed real trigger condition from decompiled code, and 11 of ~15 total bits have a specific, named semantic meaning.

**PHASE 2 CAPSTONE, same day: full production file parses byte-perfect, and the last open discrepancy resolved.** Pulled raw x86 disassembly (not decompiler C, which can miscombine short-circuited expressions) for the `wpn_Bomb.ms2` discrepancy in the `0x40` shadow-volume block - confirmed the code unconditionally does 3 writes once that bit is set, and confirmed via careful Python re-verification that the file's actual `e_count` (132) is read correctly, with `132x52=6864` bytes landing exactly on the file's true end (no room for the documented 3rd write). Resolution: `MayaExp.mll` is dated June 2007, but `wpn_Bomb.ms2` is dated January 2006 - over a year older. The exporter's own behavior almost certainly changed between those dates; this is a real historical version mismatch between an old asset and a newer tool, not a parsing bug. Then ran `ms2_parser.py` against the full real shipped `u_veh_t34_85_44.ms2` (219 nodes, 12.9MB) end to end - **parsed to the exact byte with zero leftover**, the strongest possible validation available, using nearly every documented optional block in real combination across the file. Found one more real, previously-unidentified bit (`0x80000`) that doesn't affect byte layout (not a block-gating bit) but has unknown attribute meaning. **The `.ms2` core format is now considered verified against real production content, not just test files** - remaining open work is narrower: exact internal field layouts for 5 record types whose purpose is known, plus identifying the one new bit.

**PHASE 2, one more round: the `0x10000` bind-matrix record fully decoded field-by-field, with certainty.** Re-examined `FUN_1008d610`'s default-initialization code and found it bulk-copies 16 dwords from a fixed global constant (`DAT_1013ae10`) into each new record - dumped that constant directly from the binary and confirmed it's a literal 4x4 identity matrix (1,0,0,0/0,1,0,0/0,0,1,0/0,0,0,1), no ambiguity. Combined with the surrounding zero-initialized fields, the full 80-byte record is now certain: `[int32 index (4B)][4x4 float matrix (64B)][Vector3 (12B)]`. Tried to repeat this trick for the other four record types (`0x10`/`0x200`/`0x400`/`0x800`) but they're populated through much deeper, more intricate per-triangle/per-vertex processing chains with intermediate collections of different strides - the exact final-array-population code wasn't located in this pass, and would need substantially more dedicated tracing through some of the largest functions in the whole plugin to pin down fully. Honest assessment given to the user: this is a real, bounded remaining task, not a blocker, but needs focused follow-up work rather than a quick pass.

**PHASE 3: a real, working static-mesh Blender importer, built and validated - user asked "how far are we from a working import/exporter" and then asked to build the static-mesh half.** Built `Tools\MS2Format\ms2_reader.py` (pure Python, no dependencies) implementing everything confirmed so far, skipping the still-unmapped optional blocks by their known exact sizes since their content isn't needed for static geometry. Found and fixed one more real issue: `bld_Haystack.ms2` had the exact same "predates the exporter's own build date" version mismatch as `wpn_Bomb.ms2` (confirmed via file date, 2006-10-11 vs the June 2007 exporter) - rather than hardcode a fragile date check, made the reader structurally self-correcting (computes the node's remainder both ways when it hits the ambiguous block, picks whichever leads to a valid next-node-name or exact EOF). **Result: all 62 sample `.ms2` files in the entire game - every model, not a subset - now parse to the exact byte with zero leftover.** Built `Tools\MS2Format\ms2_import_blender.py` on top of this (targets Blender 2.79, the version actually installed on this machine) - creates real Blender mesh objects (via bmesh) with correct positions/authored normals/UVs/triangles and correct parent-child object hierarchy. Tested headlessly (`blender --background --python`): `bld_Haystack.ms2` imports 167/167 vertices and 196/196 triangles exactly; the full real 219-node `u_veh_t34_85_44.ms2` shipped tank imports 84,611/84,611 vertices exactly and 77,172/77,182 triangles (the only 10 missing are exact-duplicate faces in a few collision meshes that Blender's bmesh structurally refuses to create twice - a Blender API limitation, not a format gap). Saved two demo `.blend` files to `M:\TvT 2024 working folder\ms2_blender_import_demo\` (`bld_Haystack_imported.blend`, `t34_85_44_imported.blend`) for direct visual inspection in Blender's UI. **Not yet done**: material/texture assignment (the companion `.script` file's `ModelSkin` texture list is plain text and fully understood, just not wired up to the importer yet - the natural next step) and skin/animation import (needs the still-unmapped record types).

**PHASE 3 FIX, same day: real visual bug found and fixed via user testing.** User opened the generated tank `.blend` in their own Blender and reported scattered dark/faceted patches, concentrated on the damaged "Crashed" variant parts - the simple haystack prop looked perfect. Diagnosed with data, not guessing: wrote a throwaway script comparing each triangle's geometric normal (from its vertex order) against the average of its 3 vertices' authored normals from the file - found **7.17% of all faces (5,531 of 77,182) have winding that disagrees with their own authored normal**, heavily concentrated in `_Crashed` meshes (`Body_Crashed`: 31% of its faces affected) - plausibly because shattered/damaged geometry was processed differently (mirrored fragments, boolean cuts) than clean intact meshes. This exactly explains the artifact: inverted-winding faces render dark from angles where correct neighbors render light. **Fix**: `ms2_import_blender.py` now computes each triangle's geometric normal before creating it and reverses vertex order if it disagrees with the authored normal, using the file's own normal data as ground truth. Verified directly (not just "looks plausible") - disagreements dropped from 5,531 to 2 (likely genuine degenerate slivers, noise-level), and the already-perfect haystack stayed at zero disagreements, confirming the fix doesn't disturb correct data. Regenerated both demo `.blend` files.

**PHASE 3 SECOND FIX, same day: real second bug found, not a repeat of the first.** User re-tested with a brand-new, uniquely-named file (ruling out staleness) and a new mid-complexity model (`u_stat_pak40.ms2`, 36 nodes, picked as a deliberate middle point between the simple haystack and the huge tank) - pak40 looked correct, tank still looked shattered. Checked the actual node hierarchy and found `Body` (intact hull) and `Body_Crashed` (shattered wreck) are siblings with nearly identical bounding boxes, same for every `_LOD1/2/4` variant of both - the importer was creating EVERY node as visible geometry, so intact + wrecked + every LOD copy were all rendering simultaneously, stacked in the same space. Not a normals bug - the earlier winding fix was real and correct, just not the whole story. **Fix**: importer still imports every node (nothing lost) but now hides by default anything matching the game's own `_LODn`/`Crashed`/`_CM` naming convention, confirmed against real shipped content. Verified: 67 of 219 tank nodes now hidden by default, leaving just the intact vehicle visible.

**PHASE 3 THIRD FIX, same day: version-sensitive custom-normals API replaced.** User re-tested with another fresh file and said the turret/barrel specifically still looked wrong ("maybe 50% ok"), hull/wheels fine. Rendered the scene myself headlessly (full shot + turret closeup) - nothing looked obviously broken to me. Checked `Turret_A`'s own vertex data for a genuine outlier vertex (none found - its farthest points are just the real muzzle tip) and re-verified the winding fix has zero remaining disagreements (not just "down to 2" - actually zero when checked correctly post-fix). This ruled out geometry/winding entirely. Key realization: my own testing only ever used Blender 2.79's old internal renderer (same version that authored the files), while the user was viewing the same files in a much newer Blender using Eevee - and the importer was applying authored normals via the comparatively obscure `normals_split_custom_set_from_vertices()`/`use_auto_smooth` API, which is plausible to behave differently once a newer Blender/Eevee auto-upgrades that old-format custom-normal data. **Fix**: replaced this with plain `polygon.use_smooth = True` - a basic, version-stable feature that shades purely from mesh topology (shared vertex indices), which correctly reproduces hard/soft edges since the format already duplicates vertices at hard edges - no dependency on trusting exact stored normal vectors across Blender versions. **Honestly flagged**: this fix could not be independently verified in this environment (only Blender 2.79 is installed, which predates Eevee entirely) - needs the user's own test to confirm.

**PHASE 3 CORRECTION + FOURTH FIX, same day: the winding-disagreement diagnosis was WRONG, retracted, and the real cause found.** User re-tested and reported the turret still breaks "from the commander's hatch forwards," and firmly rejected the standing explanation ("this is a genuine pre-existing inconsistency in how the turret was authored") as "complete rubbish" - they can view the exact same asset correctly in the real TvT Editor, proving the source data is fine by the actual engine's own rules. **Retracted the winding-flip fix entirely** - reverted `ms2_import_blender.py` to trust the file's triangle index order exactly as authored, no correction. Went looking for a defect that doesn't depend on comparing against authored normals at all: checked for genuinely zero-area triangles (repeated indices, or collinear vertices via cross-product area) - a check that can't produce the same false positives since it never references the file's normal data. **Found 70 real degenerate triangles in `Turret_A`**, all at triangle index ≥3513 (of 5,537), clustered in world Z ≈0.05-1.10 - the turret's roof/hatch region, matching the user's own description almost exactly. Same pattern found file-wide in `Body_Crashed` (168), several LOD/CM variants, and `Turret_A_CM` (7) - `Body` itself has zero, consistent with it never showing any complaint. The 26 "edges shared by >2 faces" found earlier turned out to be a subset of these same degenerate triangles' edges - one cause explains both findings. **Mechanism**: a zero-area triangle has an undefined normal; the real engine never recomputes normals from geometry (uses the file's authored per-vertex normals directly), so it's harmless there - but the Phase 3 THIRD FIX's `poly.use_smooth = True` made Blender recompute shading from topology via `bm.normal_update()`, which picks up the degenerate triangles' undefined normals and smears bad shading onto real neighboring faces. This also retroactively explains much of the original (now-retracted) winding-disagreement signal. **Fix**: skip zero-area/repeated-index triangles entirely at import (same treatment as duplicate faces - they render as nothing anyway, so dropping them is unambiguous), and reinstated the file's own authored per-vertex normals via `normals_split_custom_set_from_vertices()` (undoing the THIRD FIX's swap to plain smooth shading), since with the poisoning source removed there's no longer any known reason to distrust the authored normals, and using them is strictly more faithful to the source. Regenerated and rendered `tank_imported_v5.blend` headlessly - clean shading everywhere including the roof/hatch area. Still can't independently confirm under Eevee in this environment, but this fix doesn't depend on any renderer/version assumption the way the retracted one did.

**PHASE 3 UPDATE, same day: degenerate-triangle fix confirmed NOT the cause; switched from generating .blend files to a real installable add-on.** User tested `tank_imported_v5.blend` and reported it "exactly the same as before" - meaning the zero-area-triangle theory is falsified; removing those 70 triangles had no visible effect. Realized a gap in the testing method itself: every demo `.blend` file up to this point was built and saved inside this environment's Blender 2.79, then the user opened it in their own much newer Blender (5.1.2) - meaning the actual mesh/normals data the user sees has already been through Blender's own opaque old-file version-upgrade process, which this importer's own code has zero influence over once the file is saved. Built `Tools\MS2Format\blender_addon\ms2_importer\` - a proper installable Blender add-on (targets Blender 2.80+, matching the user's actual version) with a File > Import > TvT Model (.ms2) menu entry, so the user's own Blender builds the mesh directly via native bpy/bmesh calls, no .blend-file round-trip or version-upgrade step involved. Also exposed three import options as live, in-Blender diagnostics (via the Redo panel): hide LOD/Crashed/CM variants (on by default), skip zero-area triangles (on by default), and a "Shading" mode (Authored/Smooth/Flat) - Flat shading in particular is the single most useful next experiment, since flat-shaded geometry can't misinterpret a normal it never uses, so if the artifact survives under Flat shading it conclusively isn't a normals/shading bug at all. Packaged as `ms2_importer.zip` for one-click install (Edit > Preferences > Add-ons > Install from Disk). Could not test the add-on's Blender-2.80+-specific API calls in this environment (only 2.79 is installed, which lacks `bpy.context.collection`/`hide_viewport`/etc.) - verified only that the bundled `ms2_reader.py` copy still parses all 219 nodes of the real tank file correctly; the add-on's registration/execution path needs the user's own test.

**PHASE 3 ATTEMPTED FIX + REVERT, same day: per-vertex skin weights decoded (real finding), but the "hide unresolved skin geometry" fix was too aggressive and has been reverted.** Traced the turret's spike artifact to a real per-vertex skin-weight block (`flags_bitmask & 0x10`, previously only skipped by size): decoded it as 4x float32 weight + int32 joint index (a plain index into the same file's own node list - confirmed against real node names like `Weapon_A`, `Luk_B`). Cross-referenced the companion `.script` file and found `["gun_a_recoil", ["Weapon_A", 0, 30]]` plus hatch-open channels - confirming these are real animation joints (gun recoil, hatch opening) baked into `Turret_A`'s own mesh. Checked exhaustively for a bind-pose transform for these joints (bbox/sphere fields, every optional block gated by their own flags, the always-present per-node array) and found genuinely nothing anywhere in the `.ms2` or `.script` files - confirmed via a direct comparison against the real TvT Editor's Asset View (shows a normal, correctly-shaped barrel) that a transform this reader has no access to is definitely being applied somewhere outside the file. Implemented a fix that split every node with this weighting into a safe "self-weighted" object and a hidden `_UnresolvedSkin` object for the rest. **User tested this and reported it removed a lot of legitimate geometry** - the self/external split was too coarse and wrongly hid real, correctly-positioned parts along with the genuinely broken barrel/hatch vertices. **Reverted entirely** (`git revert`) back to the pre-split importer - the turret/barrel spike corruption is confirmed still present and unresolved. The skin-weight decoding itself (`node.vertex_joint` in `ms2_reader.py`) was reverted along with it, not kept partially, since the whole fix built on it turned out unusable as designed. Next attempt at fixing this needs a much more precise self/external split (or a different approach entirely) - flagged as open, not attempted again yet.

(Earlier same-day empirical breakthrough, superseded in most details by Phase 2 above but kept for history:) found the real, explicit `vertex_count`/`index_count` fields - they were hiding in plain sight the whole time, but an earlier pass misread them as "always zero padding" because tiny denormalized floats (e.g. int32 `24` reinterpreted as float32 is `3.36e-44`) round to display as `0.0` at low precision. Reading the same bytes as int32 instead of float32 revealed real counts, confirmed exact on `MyFirstModel.ms2`'s known cube (24 vertices, 36 indices = 12 triangles) and cross-validated on `Sky.ms2`'s `SkyDome` (395 vertices - exactly matching an earlier, independently-derived magnitude-scanning estimate). Verified the full vertex/normal/UV/index layout end-to-end on 7 diverse files (cube, bomb, rocket, dome, two spheres) - all bounding boxes come out physically correct for their shapes (e.g. a bomb's box is long and thin). Built a real research tool, `Tools\MS2Format\ms2_probe.py`, implementing this. **Two new problems found while testing further**: (1) a 3-node file (`bld_Haystack.ms2`) breaks the pattern - its own node appears to NOT have the `parent_idx`/`child_count` fields that `SkyDome` had, meaning presence of those fields isn't simply about total node count as first assumed; (2) some files have large unexplained trailing data after all confirmed content (`Sky.ms2`: 48 bytes, plausible footer; `sphere_test.ms2`/`test.ms2`: 15944/59812 bytes, far too much to explain simply). Full write-up in `Documentation/MS2_Binary_Format_Findings_2026-07-03.md`, including an explicit correction note about the earlier float-rounding mistake (documented honestly, not hidden). Recommended next step: compare several more 2-and-3-node files to find the real pattern for when parent/child fields appear, or move to Phase 2 (decompilation) for a ground-truth answer instead of continued guessing. Goal (per user, 2026-07-03): understand the `.ms2` format well enough to eventually build Blender import/export - a big potential community deliverable. Corrected the issue's own premise first: `MayaExp.mll` is a completely standard Windows PE32 DLL (`MZ` header confirmed), not a proprietary encoding needing "unpacking" - the CGNS_MLL link in the issue is an unrelated aerospace/CFD standard that coincidentally shares the "MLL" acronym. Standard decompilation tooling (e.g. Ghidra) applies directly, no special unpacker needed. Phase 0: fully re-verified `T34_vs_Tiger_Maya_Export_Manual(V3).md` (a prior draft, versions 2.0-3.1) against the actual `Tools\Scripts\*.mel` source line-by-line - **found the "verified" v3.1 manual contained real errors**: 4 fabricated mesh attributes not present anywhere in source (`IsShadowMesh`, `IsBillboard`, `CastShadows`, `ReceiveShadows`), 11 real attributes missing (`IsRouterMesh`, `IsBoneNode`, `IsHidden`, `IsNear`, `IsDoorObject`, `TransparentShadows`, `IsSelfLOD`, `DoNotCastShadow`, `DoNotUseInIsection`, `IsNearGeometry`, `OnlyCastShadow`), a wrong collision-mesh naming convention (claimed `_col` prefix, real evidence in `LOD_CM_SCRIPT.mel` shows `_CM` suffix and `_LOD1`-`_LOD4` not `_LOD0`-based), and an entire fabricated "G5Entity marker system" section with no supporting evidence anywhere in the source (real finding: `ClassName` is just a single per-export text field, not a per-object attribute). Corrected all of this to v4.0, and added: 3 previously-undocumented systems (character head/LifeHead swap system via `addHeadProperties.mel`, portal/occlusion-culling system via `createPortal.mel`, a schema-migration utility in `ConvertProp.mel`); the discovery that `exportG5Resource` is called with two different, unreconciled argument counts (12 vs 15) from two different scripts, one of which (`ExportBatch.mel`) hardcodes paths suggesting it may be adapted from a different G5 Software project ("Metro2"); a D3DX9_28.dll hard dependency found in a newer 2024-revision tutorial (from the user's own TvT manuals archive, now added to this repo) not previously captured here - a real clue that the plugin likely calls D3DX utility functions internally. **Still completely unstarted**: the actual `.ms2` binary format itself - this manual only documents the Maya-side authoring metadata schema, not the byte-level format those attributes get serialized into. Proposed phases for the real work: (1) empirical byte-level probing of simple sample `.ms2` files already in `Models\`, (2) Ghidra decompilation of `MayaExp.mll`'s export path and/or whichever engine DLL reads `.ms2` at runtime (not yet identified - no literal ".ms2"/"MS2" string found in `Engine.dll`/`Objects.dll`/`Behavior.dll` via binary search), (3) a Python reader then writer, tested by round-tripping through the Editor. Realistically multi-week-plus, tracked as its own project.


## Stevan Vase contribution audit (2026-07-02)

- [x] **Full audit of stevanvase0-beep's 30 git commits (Jan 8 - Mar 5 2026)** — done 2026-07-02. Systematically diffed every file he touched against the live game install. Findings: (1) his Model/LOD/shadow completeness pass (Feb 3-4, 49 files) is fully integrated and good work; (2) his mission-lighting sweep (Jan 8-9, ~14 missions) was superseded by the user's own later hand-tuning; (3) his Jan 24 Cockpit.script "Distance wav" fix was never applied — fixed now; (4) **his Jan 13 "structure alignment" edit to `TankPzVIAusfEUnit.script` accidentally deleted the `void AddWingman(Component unit) { }` stub** that exists specifically to silence a "function not found" error from `Common\BaseTasks.script`'s wingman-task code path — restored, and also added to `T34_85_44.script`/`T34_76_42.script` (the other 2 player-drivable tanks), since neither of them had ever had the stub either despite being equally exposed. Not yet triggered in any tested mission (wingman feature is dormant), but a real latent bug, not hypothetical.
- [x] **Docs-repo `TvT\` mirror re-synced** — done 2026-07-02. 27 files were stale relative to the live game (7 shadow `Common\` scripts, ~14 Campaign_1/Campaign_2 mission Content/Atmosphere files, plus the 3 tank unit scripts and Cockpit.script from the fixes above). Re-copied from the live install. Note: this sync covered only the files implicated in the Vase audit — there may be more drift elsewhere in the mirror that a full whole-repo diff would catch; not attempted here.
- [x] **Full whole-repo diff pass, done as a separate follow-up** — 2026-07-02. Compared all 601 `.script`/`.rsr`/`.txt`/`.tsv`/`.locale` files in the mirror against the live game (not just the ones Vase's commits touched). 573 matched. Of the 28 that didn't: 21 were pure line-ending/whitespace noise (CRLF vs LF, one missing trailing newline, one missing space in `Weapon.rsr`) — synced for byte-consistency but no real content changed. 4 had genuine content differences, all in the direction "live game is ahead" (same pattern as the Vase audit) — `Common\Instances.script` (live has a much more complete instance-count registration for the full expanded roster), `Common\Mission.script` (see the ghost-roster note below), `Units\SAUSU85Unit.script` (live has 3 cockpit UI-parm lines deliberately commented out across all 3 ammo types — consistent pattern, looks like an intentional WIP fix, not an accident), `Models\bld_Barricade_Pak.script` (same header/shadow-alignment pattern as the Feb 3-4 Vase batch, just never synced). All 4 synced live→docs. Also cleaned up: 7 stray duplicate `Models\`-type scripts that were sitting in `TvT\Units\` (should only hold gameplay Unit scripts; correct copies already existed in `TvT\Models\`), and one empty leftover `zztest.txt`.
- [ ] **Vehicle shadow visible through terrain ridges — still unsolved, 3 attempts tried and fully reverted.** 2026-07-02. Bug: a vehicle's shadow stays visible on the far side of a ridge even after the vehicle itself is out of view (confirmed via screenshot/testing to be an occlusion problem, not a distance one). Tried, in order: (1) tightening `LodForShadowHide`/`LodForShadowChange` ~40% for all 9 tank models — no visible effect, wrong mechanism (that's a distance-based hide, this bug is occlusion-based); (2) re-enabling the real `ShadowMapArray` shadow-map system in `Settings.script` (was commented out, only a simple on/off toggle was active) — no visible effect, no crash; (3) enabling `FakeShadow` for trucks (the one vehicle category that had it `false` while everything else has it `true`) — this one **broke all model rendering entirely**, not just trucks, confirming trucks being the exception is deliberate, not an oversight. After (3) surfaced with a genuinely clean repro (cache cleared, editor never open beforehand) and the user asked to stop, **all three attempts were fully reverted** — confirmed via `git diff` against the exact pre-investigation commit (`7b7311e`) that all 4 touched files (`ShadowHide.script`, `ShadowsChange.script`, `Settings.script`, `FakeShadows.script`) are now byte-identical to before any of this started. Bug is still present, unsolved, at baseline. Do not retry (2) or (3) without new information; searched git history, the user's own manuals/documentation, the ZeeWolf technical fix doc, and the panzersim forum (including full thread reads and several search queries) for a record of how the user fixed this before — found nothing that matches (the closest forum hit, "Stencil Shadow CTD Solved," is a different bug, and its suggested fix is now stale/would break the current codebase if applied).
- [ ] **`Common\Mission.script` references three tank variants with no actual Unit script — re-scoped 2026-07-03, only one of the three is actually worth building.** Originally flagged all three (`TankPzVI_LATE`, `T34_76_41`, `T34_85_44_2`) as "shovel-ready" cut content since their model files exist. Checked each properly this time (user pushed back on the "just wire it up" framing, rightly) - the picture is very different once you actually look at the geometry and stats instead of just confirming the files exist:
  - **`TankPzVI_LATE` (a second Tiger) - dead end, do not build.** Proved `Turret_A` is byte-for-byte identical (positions AND indices) between `u_veh_PzVI_MAIN.ms2` and `u_veh_PzVI_LATE.ms2` - the "MAIN→LATE" 3D model swap already live in-game only ever changed the commander crew-figure rig, never the hull/turret/cupola. Rendered the actual cupola and confirmed (user's own historical knowledge caught this first) it's the early-production **drum-style** cupola, not the late-war Panther-style cast one - so the game's existing Tiger already IS the early variant, whatever the file naming implies. Also checked every `TankPzVI_LATE*` constant in `Piercing.script` against the current Tiger's own `TankPzVIAusfE*` constants - bullet speed, penetration, damage modifiers, all byte-for-byte identical. Building this would produce an invisible, stat-identical duplicate of the tank already in the game. A real distinct late-war Tiger (Panther cupola) would need genuinely new 3D modeling work, not existing-asset wiring.
  - **`T34_85_44_2` - already resolved earlier this session (GitHub issue #7), not a distinct tank at all.** It's an old 2006 pre-cockpit-support export of the same T-34/85, missing the driver's cockpit-camera/hatch joints - moved to `Models\_Removed\` for exactly that reason. See that TODO entry above.
  - **`T34_76_41` - the one genuine candidate, but needs real work, not just a script file.** Its model (`u_veh_t34_76_41.ms2`) has only 14 nodes total vs 216 for its finished `T34_76_42` sibling - **no wheels, no tracks, no suspension, no LOD variants, no damage/wreck state, no hatches, no crew figures** - just a hull + turret + gun blockout with a few never-renamed default Maya part names (`polySurface145` etc.), meaning it was abandoned mid-build, not finished and then hidden. No ballistics/armor stats exist for it anywhere in `Piercing.script` either (unlike `TankPzVI_LATE`, which at least had a full, if duplicate, stat block) - the only trace anywhere in `Scripts\` is the bare name `"CTankT34_76_41Unit"` sitting unused in `Mission.script`'s roster list. **However**, rendered both turrets side by side and confirmed the shape genuinely differs from `T34_76_42` - a rounder, flatter hexagonal turret with a single split hatch and pistol port, vs `T34_76_42`'s more angular wedge-shaped cast turret - real, deliberate, distinct sculpting work, not a discarded duplicate like `T34_85_44_2` turned out to be. **Proposed next step (not started)**: graft `T34_76_42`'s wheels/tracks/suspension/crew rig onto `T34_76_41`'s distinct hull+turret (same WWII-era chassis, historically plausible reuse), and base its ballistics on `T34_76_42`'s own stats as a defensible starting approximation (same gun/armor era) rather than inventing new numbers from nothing. This is real modeling/pipeline work (some of which the `.ms2` reader/Blender add-on built earlier today could help with), not a quick script-only fix.

---

## Quick Mission Generator (`Tools\MissionGenerator\`)

- [x] **Added a GUI** — 2026-07-02. `gui.py` (tkinter, stdlib only, no extra install) wraps `generate_mission.py` as a subprocess rather than duplicating its logic - faction radio buttons, an optional seed field with a "Random" roller, a "Generate Mission" button, and a result box showing the script's own output. "Edit Roster" button opens `roster.json` directly in Notepad. `Quick Mission Generator.bat` launches it via `pythonw` (falls back to `python`) so there's no command prompt at all for normal use - just double-click. Roster editing intentionally stays a plain-text `roster.json` edit for now, not exposed in the GUI - a bigger job for later if wanted. Smoke-tested (launches, stays running, no immediate crash) but not visually reviewed - can't see a GUI window myself.

- [x] Expand `roster.json` with a few more grep-verified unit types — done 2026-07-02. Added SU-85/StuG 40 (self-propelled guns, correct task is `CBaseAISAUTask` not `CBaseAITankTask` - confirmed live in Campaign_2\Mission_4) and German/Soviet riflemen (`CBaseAITask`, confirmed live in Campaign_1\Mission_1/2). Each side now has tank/AT-gun/SAU/infantry. Verified with 40-seed sweeps per faction that every class actually appears.
- [ ] Confirm the `RouterZone_Test.bmp` color-to-passability mapping in-game (currently an unproven empirical soft filter — see `Mission_File_Schema_Verified_2026-07-02.md` §2b/Unresolved).
- [ ] Unit facing/yaw randomization (v1 uses fixed identity rotation, all units face the same compass direction).
- [ ] Consider a second/bigger template mission for more spawn variety — `MyMission\Mission1`'s proven-safe zone is a small ~1300x3000 unit cluster out of the full 9000x9000 map. Real campaign missions were ruled out as templates (too trigger-coupled — see the 2026-07-02 CHANGELOG entry), so this needs either a different low-coupling mission or building a fresh dedicated template mission from scratch.

## From the user's years of playing (2026-07-02)

- [x] **Enemy AI can see through trees/forest** — no foliage line-of-sight occlusion; TvT's `ViewProbabilityByDistance` is a pure distance curve with no occlusion check. Confirmed 2026-07-02 this is a real, known-solvable gap, not an inherent genre limitation: Panzer Elite (1999, same era/genre) has real deterministic LOS via `tfuFIRELINE` (raycast against terrain) + `tfuELEVATIONOK` (ridge/crest check) — see `L:\2025\PE\PE SOURCE\PE AI Source code brains\Spotting_Model.md` (user's own source-grounded analysis of Alan Barber's real PE `VisualAI` source). Scoped 2026-07-02: `Behavior.script`'s `ViewProbabilityByMask` has a real forest-concealment multiplier (`FORESTLANDSCAPE_UNIT = 0.4f`, already user-tuned once from 0.6) but it's completely inert — nothing anywhere in the script layer ever assigns those `*_LANDSCAPE_UNIT` classificator tags to any object, confirmed via a codebase-wide search. `PointCollisionDetector` (a real, working collision primitive, used for kamikaze/parachute/deep-water checks) can't substitute for a raycast either — confirmed `setPositionable()` (its only positioning method) can only track an existing engine object's live position, never an arbitrary world point, so it can't be walked along a line between two units. No genuine LOS/occlusion query exists in TvT's script layer today. Fixing this for real would mean either building a whole new terrain-zone classification system from scratch (feasibility on the engine side unconfirmed) or DLL-level work. Treating as closed/no further script-side avenue unless new information turns up — do not re-investigate blindly.
  **RESOLVED 2026-08-19/20 — done, both crews.** The July scoping was right that no script-side avenue exists and that it would take DLL-level work, and right to close it rather than keep digging. It happened: `FUN_100c9e50` (Behavior.dll + 0xC9E50) is the entire AI vision model - 2D distance x angle x state, then a dice roll, with no ray cast anywhere - and occlusion went in as one more multiplier of the kind it already walks. **74% of the engine's positive sightings were going through solid ground or woodland.** The player's crew turned out to be a SECOND system (`CAutoShooterComponent`) and is now covered too. And the inert `FORESTLANDSCAPE_UNIT = 0.4f` multiplier noted here is exactly the shape the fix took, just applied natively instead. See [Documentation/TvT_Line_Of_Sight.md](Documentation/TvT_Line_Of_Sight.md) and [RE/TvT_Vision_Model_Decoded.md](Documentation/RE/TvT_Vision_Model_Decoded.md).
- [x] **DLL-level LOS hook attempt exists and failed — real prior art, wrong target function.** User built `tvt_los_hook.dll` in Nov 2025 (with minimax AI's help) against the `M:\T34vsTiger_ZW2015` (ZeeWolf mod, a separate paid-mod install, **not** the REDUX0.001 codebase) install, injected via an external DLL injector (`settings.xml` in that folder). Confirmed "made no difference" in-game. Investigated 2026-07-02: original source (`los_injection_dll.cpp`) has been deleted from disk (searched, not found), but debug strings pulled directly from the compiled DLL (via Python + `pefile`, no exports, only imports + embedded strings) show exactly what it targeted - it located `Behavior.dll`/`Objects.dll`/`Engine.dll` at runtime and installed a hardcoded-address inline hook on what it calls the **"Targeting Dispatcher"** in `Behavior.dll`. That's the native equivalent of the *engagement decision* (which already-detected enemy to attack - the same layer this session's script-side `SelectAttackTarget()` fix operates on), not the *detection/visibility* computation that would actually control whether AI can see through foliage. So even a perfectly-working hook here was targeting the wrong pipeline stage - explains "no difference" independent of whether the hook mechanically succeeded. No `los_debug.log` was found anywhere on the system, so it's unknown whether the hook even installed (the DLL has embedded error paths for "Behavior.dll base address not found" - hardcoded addresses are notoriously build/version-fragile). **Next step, if ever pursued**: find the actual native detection/visibility function in `Behavior.dll` or `Objects.dll` (not the targeting dispatcher) - this is real reverse-engineering (disassembly/decompilation of the compiled engine), a fundamentally different and much larger undertaking than anything done in this codebase so far. Not started.
  **RESOLVED 2026-08-19/20.** The diagnosis here was half right and the half that was wrong is worth keeping. Right: the Nov-2025 hook used **hardcoded addresses**, and the engine DLLs relocate by 237-279 MB between runs, so it almost certainly never installed - the new work resolves everything as `GetModuleHandleA` + static RVA and that is precisely why it works. Wrong: the target was not the problem in the way described. The detection function `FUN_100c9e50` was found by disassembly as this entry predicted would be necessary, and it IS in `Behavior.dll`. The "much larger undertaking" turned out to be about a day, because the function is only 752 bytes and does one thing. Note also that the stale `tvt_los_hook.dll` from Nov 2025 still sits in the live game root, unused, sharing a filename with the new one.
- [x] **MG catch-all mask tier let MGs engage tanks, wasting ammo and CPU on rounds that can't hurt armor** — fixed 2026-07-02, follow-up to the two bugs below. After confirming those two bugs were fully gone from the log, FPS was still poor (11.8, worse than the first test) and the user identified the real cause from direct observation: MGs were now firing at tanks, not just the soft targets (trucks/halftracks/infantry) the fix was meant to enable. Root cause: the catch-all `[[],[]]` tier added in the mask fix below (mirrored from the pillbox pattern, where it's a sensible last resort since a pillbox has no other weapon) matches literally any target type when checked in "anyhow" mode, including `TANK`/`HEAVYTANK` - which is exactly what let the newly-fixed masks accidentally open the door to MGs targeting tanks. A tank's MG shouldn't need a last-resort catch-all since the tank always has its main gun for armor. Removed the catch-all tier from all 10 mask blocks across the same 6 files (Tiger, both T-34s, Pz IV, both halftracks), keeping HUMAN/VEHICLE/BTR exactly as added. MGs pull from the tank's shared `AmmoContainer` with burst-fire timing (~2.4s on, 3-5s off) but no separate magazine/reload mechanic - not the bottleneck, the mask was. Not yet re-tested for FPS or correct targeting.
- [x] **FPS dip after the MG mask fix, traced to two pre-existing bugs the fix exposed** — fixed 2026-07-02. User tested the MG fix in-game and saw a noticeable FPS drop plus reported "hull gunner did not engage." Log check found zero errors referencing the fire-mask edit or `BaseTasks.script` itself, but found two unrelated latent bugs firing far more often than before, both triggered by `OnUnitHitByEnemy`-style per-hit event handlers: (1) `Missions\Campaign_2\Mission_5\MissionTasks.script` called a function named `ActivateGroupRadar` that has never existed anywhere in the codebase (confirmed via full-repo search) — every hit-received event triggered a failed call + 2 log lines; fired 151 times in one test session, up from presumably rare before. Almost certainly a typo for `ActivateRadar`, which the exact same file already calls correctly in several other places doing the identical thing — fixed all 3 occurrences (lines 124, 242, 540). (2) `Common\PlayerUnit.script:1519`, `ReportHitByEnemy()`, had `HitPointsdel = _HitPointsDelta/_HitPoints;` with no zero-guard — divides by zero whenever an already-destroyed component takes another hit. Fired 138+ times in the same session (up from ~9 in the prior log). `HitPointsdel` turned out to be write-only dead state (declared, assigned here, never read anywhere in the codebase), so the exact fallback value doesn't matter functionally — added a simple `if (_HitPoints != 0) ... else HitPointsdel = 0.0f;` guard, matching the file's existing if/else style (avoided the C-style ternary operator - no precedent for it anywhere in this codebase, safer not to assume the language supports it). Both bugs were always present; MG fire landing on tanks for the first time (thanks to the mask fix) just multiplied how often each one's hit-triggered code path ran, and the failed-call + logging overhead per hit is the likely FPS cause. Not a flaw in the MG mask fix itself - no compile/script errors reference any of the 6 files changed for that fix. Not yet re-tested for FPS.
- [x] **Coax/hull machine guns never used against vehicles — universal across every tank and halftrack, not just the Tiger's hull MG as first reported** — fixed 2026-07-02. User reported the hull MG "never seems to be used by the AI." Root cause found in every single tank/halftrack unit file (`TankPzVIAusfEUnit`, `T34_76_42`, `T34_85_44`, `TankPzIVGUnit`, `BtrHanomag251AusfCUnit`, `BtrM3A1HalftruckUnit` — 6 files, ~14 mask blocks across all coax + hull MG weapon classes): every single one has `GunSpecificFireMask = [["HUMAN"],[]]` (or with `["AIR"]` excluded too) and nothing else — commented `// low priority mask` as if a higher tier was meant to exist above it and was just never written. `CanAttackPersonally()`'s mask check (`Common\BaseTasks.script`, `CheckGunFireMask`) rejects any target that isn't HUMAN-classified, so these MGs could never even be considered against trucks, halftracks, or tanks — only infantry, which barely appear in most TvT missions. Confirmed this is a real omission, not intentional design, by comparing against the pillbox/bunker MGs (`DotConcreteUnit.script`, `DzotWoodUnit.script`), which correctly implement the full tiered pattern: `[["HUMAN"],[]]` (high priority) → `[["VEHICLE"],[]]` → `[["BTR"],[]]` → `[[],[]]` (catch-all, fire at anything if nothing else fits). Added the same `VEHICLE`/`BTR`/catch-all tiers to all 6 unit files' MG masks, preserving each file's existing `HUMAN` tier exactly as it was (including the Tiger/T-34-85's `AIR` exclude, and Hanomag's commented-out `//[["AIR"],[]]` line). Tanks still won't waste the MG shooting at armor - `CheckWeaponPower()` already gates on `Health`/`Power` match, MG rounds aren't rated against tank-grade health, so this only opens up trucks/halftracks/infantry as viable MG targets, not tanks. Not yet play-tested. Side note, left uninvestigated: the Tiger's hull MG traverse animation (`gun_c_leftup/leftdn/rightup/rightdn`) throws "anim name not found" in the log - a separate, likely cosmetic gap, not chased since the fire mask was clearly the actual gameplay-blocking issue.
- [x] **AI didn't prioritize targets — shot at whatever the radar handed it, ignoring closer/more dangerous threats (including attacking unarmed trucks over real threats)** — fixed 2026-07-02. Root cause: `Common\BaseTasks.script`'s `OnEnemyTargeted()`/`OnRadarUpdate()` handlers (5 call sites across `CBaseAITask`, `CWingmanTask`, `CBaseAISAUTask`, `CBaseAITankTask`, `CBaseAIBtrTask` — i.e. guns/infantry, aircraft wingmen, SPGs, tanks, halftracks) all just grabbed whatever `GetTargetedEnemy()` (a native, opaque radar callback) handed them and locked onto it with `AttackEnemy()` — zero distance comparison, zero armed/unarmed check. Added one new shared method, `SelectAttackTarget()`, to the common `CBaseAITask` base class: walks the full radar contact list via the existing `GetTargetedEnemy()`/`GetNextEnemyUnitOnRadar()` enumeration (already proven safe elsewhere, in the wingman re-target path), filters to armed units only (`EnemyObj.m_WeaponNames.size() > 0` — trucks/unarmed transports never call `SetupWeapon()` so this field stays empty for them, no hardcoded class-name list needed), and picks the nearest via the same `(posA - posB).Magnitude()` idiom already used live in `PlayerUnit.script`. Includes a 15% hysteresis margin (`m_TargetSwitchMargin = 0.85f`) so units don't flicker between two similarly-distant targets every radar tick. Falls back to the native candidate unchanged if no armed unit is visible at all (so an all-truck convoy doesn't stall AI engagement entirely). All 5 call sites now route through this one function instead of duplicating the naive logic. **Deliberately left untouched, separate scope**: (1) the group-level "first spotter's target becomes the whole group's target" behavior in `UnitGroup.script:866` (`OnEnemyTargeted`) — a different mechanism, not what the user described; (2) `CWingmanTask::OnEnemyLost`'s own enemy-reassignment loop (~line 2751) — already does its own enumeration with engagement/personal-attack-capability filters, left as-is to avoid double-filtering; (3) `CBaseManeuveringUnit::DoManeuver`'s `GetTargetedEnemy()` call — that's picking an evasion reference point, not a targeting decision. Not yet play-tested in-game.
- [ ] **Only ~5 real missions per side shipped** vs 6 campaign slots that exist in the menu system - user is already quietly working on adding more. Matches the "new mission content" direction already recommended as top priority.
- [ ] **No real wingman controls** - WoV had them, TvT doesn't. An empty `AddWingman(Component unit) { }` stub already exists (per "ZeeWolf Mod REDUX Technical Fix Documentation.md" in the TvT manuals folder) just to silence a "function not found" error - the hooks exist, nothing real is wired up. `WingmanMenuStyle` in `GameSettings.script` is a related WoV leftover setting.
- [x] **WoV had one large continuous map; TvT has smaller sectioned maps — answered 2026-07-02, 9000x9000 is not a ceiling.** The separate ZW mod install has 4 working "Kursk" missions at 36000x36000 (3 of them) and 18000x18000 (1), using byte-identical engine binaries to REDUX. Turned out to reveal a reusable technique, not just a bigger number — see the new **steppe mission scoping pass** below.
- [ ] **Large open steppe mission — first template built 2026-07-03, not yet tested in-Editor. Full write-up in `Documentation/Steppe_Map_Scoping_2026-07-02.md`.** User's idea: sidestep the unfixable tree-LOS AI gap above by building a mostly-open, historically-grounded steppe battle instead of chasing a fix that doesn't exist. Key findings from scoping: (1) large maps are cheap - confirmed technique is stretching REDUX's own standard-resolution terrain files (2049 heightmap, etc.) over a much bigger `MatrixWidth`/`MatrixHeight`, no new terrain content needed, no ZW assets required; (2) tree density is a `TerrainZone` bitmap paint job via `RegisterForestRegion`/`ZMC_Forest01` in `Terrain.script`, not individually placed objects - easy to keep sparse; (3) `Campaign_2\Mission_6` is REDUX's flattest existing map (elevation std 176.7 vs 440-710 for everything else) - best stretch-source candidate; (4) **decided**: framed as a looser "Ukraine steppe, late 1943-44" battle rather than the specific named Battle of Kursk - makes the entire existing roster (including T-34/85 and SU-85) period-correct with zero new unit development needed; (5) **confirmed as the working budget**: ~45 units/~29 combat vehicles (REDUX's own `Campaign_2\Mission_5`, running at 60fps after today's AI fixes) - start at or under this, don't assume a bigger map means unlimited unit count is free. (6) **decided 2026-07-03**: mission-logic style will reuse and extend the Quick Mission Generator rather than hand-scripting a bespoke battle - build a second, bigger template mission alongside `Mission1`, point `generate_mission.py` at it, same randomize/jitter/validate logic underneath just anchored to a bigger safe zone. This also directly resolves the Quick Mission Generator's own backlog item below about needing a bigger template. All three design decisions (framing, budget, mission style) are now locked in. **Built 2026-07-03**: `Missions\MyMission\SteppeTemplate\` - copied from `Mission1` (not `Campaign_2\Mission_6` - that candidate was rejected after actually rendering its heightmap and finding no real terrain features at all, see the scoping doc), all identifiers renamed, `MatrixWidth`/`MatrixHeight` bumped to 18000 (moderate first step, not ZW's full 36000), registered in `MenuConfig.script` as "Steppe Template (18000x18000)". Forest coverage thinned from 55.7%/4.05% (forest/bush) down to 8.84%/0.67% via 32-pixel block-clustered removal - the stretch technique flattens slope for free but does nothing about forest density, that needed an actual content edit. **First Editor test crashed at ~20% load, root cause found and fixed 2026-07-03**: the thinned `TerrainZone_Test.bmp` was 2 bytes smaller than `Mission1`'s original (1049654 vs 1049656) because PIL's BMP encoder writes a slightly different file structure - the engine is strict about exact byte count and refused to load that layer, cascading into the crash. Fixed by redoing the forest-thinning directly on the raw file bytes (only touching the pixel-data range, keeping header/palette/trailing-bytes identical to the working original) instead of via PIL's array round-trip. All other copied assets were direct byte-copies from the start and were never at risk - checked, all match exactly. Also fixed a harmless but real pre-existing naming quirk inherited from `Mission1` itself (mission-strings class name didn't match what `StartMissionMenu.script` actually looks up). **Retested in-Editor 2026-07-03 - success**: terrain looks right, sparse forest as intended, 125fps, `editor.log` confirms the TerrainZone layer that crashed before now loads cleanly. **Generator extended 2026-07-03**: built `SteppeQuickMission` (same one-time-setup pattern as `QuickMission`/`Mission1`), `generate_mission.py` got a `--target quickmission|steppe` option (`quickmission` still the default), `gui.py` got a matching map selector. Found and fixed a real inconsistency along the way: the reused `RouterZone_Test.bmp` samples a different pixel for the same coordinate depending on `MatrixWidth`, which was desyncing the RNG stream between targets for the same seed - fixed by disabling the (already-unproven) RouterZone soft-filter for the steppe target specifically, rather than leaving it silently unreliable. Verified with a 20-combination sweep (2 targets x 2 factions x 5 seeds) - all passed. Still not attempted: using more of the 18000x18000 map's open space for unit placement (currently still confined to the same small anchor cluster inherited from `Mission1`).
- [ ] **New: recreate "Operation Citadel: Berezov," a favorite Panzer Elite mission — scoped 2026-07-03, not started. Full write-up in `Documentation/Berezov_Kursk_Mission_Scoping_2026-07-03.md`.** User provided the real PE mission files (`Berezov.zip`) for a real Kursk (5 July 1943) breakthrough battle - German spearhead pushes Berezov → Gremuchi → Gonki against a Soviet defense-in-depth. The `.scn` files turned out to be plain text (no reverse-engineering needed) with a genuinely rich, readable structure: named `Area` zones, a semicolon-delimited mission-goal system directly comparable to TvT's own primary/secondary/bonus objectives, and an event/trigger system (`CombatScript`/`ScriptRow`: `Always`/`CG State` events driving move/wait/artillery/message actions) that's the same shape as the state-triggered group-AI work already done this session for the steppe mission. **Real discrepancy found**: the bundled file's actual roster is Panzer III/IV (German) vs T-34/76, KV-1, SU-152, 76mm AT guns (Soviet) - not the "14 Tigers" the bundled briefing text describes; likely an earlier/base-game revision, with the Tiger variant being one the user actually played but that isn't in this file. **Decided (from the user's own memory of play)**: build the Tiger version - `Zug Falke` = 1x Tiger (player) + 4x Panzer IV (AI wingmen), exactly as PE let the user personally pick their own mount within an otherwise-standard platoon; `KG Kaiser` was going to stay Panzer III x4 as authored, but **changed to Panzer IV x4** - confirmed via `ls` that Panzer III doesn't exist anywhere in TvT (no model, no unit script). PE's actual vehicle-choice/supply meta-system (pick any period-correct, in-supply vehicle) is explicitly out of scope - a much bigger, separate feature TvT doesn't have. **Decided**: reuse `SteppeTemplate` as the terrain (not a new map) - confirmed PE's map units and TvT's world units are both meters-scale (PE's briefing bitmap is exactly 1/5 scale of its stated scenario dimensions, confirming real consistent units), and extracted the real village-to-village distances directly from the file's own `Node`/`Area` data (Rakovo→Berezov ~945, Berezov→Gremuchi ~1,346, Gremuchi→Gonki ~1,983 units) - a ~4.2km corridor that fits comfortably inside `SteppeTemplate`'s 18km map with no scaling needed. **Decided**: build the German attack side first, test it, then build the Soviet defense side after (reusing the same underlying battle - PE's bilateral AI, where both sides fight for real regardless of which is player-controlled, is already how TvT's own AI works, nothing new needed there). **Full per-unit position extraction done 2026-07-03**: all 19 combat groups / 64 units, saved to `Documentation/Berezov_OOB_positions_2026-07-03.json` (exact positions plus distance/bearing from the Berezov anchor for every group). Confirmed the Soviet side is a genuine defense-in-depth (close-in AT guns/infantry right at Berezov, T-34/76 and SU-152 platoons at increasing depth toward Gonki) plus a real flanking ambush (`Plt.Popov`, 4x T-34/76 sitting almost due north of Berezov, off the main corridor entirely - checked every individual unit position, not a data glitch) matching the briefing's own flank warning. **Anchor point selected and fully validated 2026-07-03**: loaded `SteppeTemplate`'s actual `hmap.raw`/`hwater.raw`, scanned for the flattest driest ~4.2km band (found one at heightmap row 720/world Y=6328 with only ~36 units of elevation variation and zero water crossings), cross-checked the pixel-to-world conversion against the existing `MainPlayerUnit` spawn to make sure the mapping was right before trusting it. Final anchor: Berezov at world (2150, 6328), with Gremuchi/Gonki placed using the *real* bearing vectors from the original file (preserving the actual road jog, not a straight line) and all 19 combat groups placed at their real distance/bearing from Berezov - every single one individually checked and confirmed to land on dry, in-bounds terrain, no exceptions. Full world coordinates saved to `tvt_world_placement` in `Documentation/Berezov_OOB_positions_2026-07-03.json`. **Road system reconsidered 2026-07-03**: checked how TvT actually renders roads (via a real campaign mission's `Terrain.script`) - it's baked into the single `lnd_*.tex` ground texture, not an object or zone system (only `ZMC_RoadForest`, a tree-lining pattern, exists as a "road" concept). Purely cosmetic, zero effect on AI movement - downgraded to a later nice-to-have instead of a blocker. **Mission folder built and registered 2026-07-03**: `Missions\MyMission\Berezov\`, same copy-and-rename pattern as `QuickMission`/`SteppeQuickMission`, registered as "Operation Citadel: Berezov" in the Editor's mission list, own dedicated locale section with real adapted briefing text. Also confirmed while investigating: both real campaigns already have a full 6 missions each - no vacant slot, staying standalone as decided. **All 60 units and 3 villages placed 2026-07-03**: mapped every PE unit type to a real, verified TvT `Units\` class (3 honest substitutions flagged where no equivalent exists: KV-1→T-34/76, SU-152/SU-76M→SU-85 with a ~2-month anachronism accepted, BA-20+T-70→T-34/76). Found and fixed a real bug before committing - initially placed units using raw, untranslated PE file coordinates. Built 3 village clusters (33 objects) using a real house/shed/fence pattern copied from an existing TvT mission. Replaced all of `SteppeTemplate`'s inherited placeholder content; verified the result is structurally sound (balanced brackets, no duplicate IDs among 95 entries, everything in-bounds). **Still not done**: tactically-appropriate unit facing (currently just a simple default heading per side), the real `Mission.script`/`MissionTasks.script` trigger logic (the original `CombatScript`/`ScriptRow` event system hasn't been translated into TvT's own Task-class scripting), wiring the 5 real `MissionGoal` objectives into TvT's own mission-goal system, and testing that it actually loads in the Editor.

- [x] **Object-position height mismatch found (a floating Pak 40 gun, spotted visually) and fixed 2026-07-03.** Same root cause as the RouterZone bug above, just far more visible: every object's X/Y/Z was copied verbatim from `Mission1`, but stretching `MatrixWidth` to 18000 changes which heightmap pixel a given X/Y samples, so authored Z values no longer matched real terrain height. Confirmed empirically (311 raw elevation units off, a big fraction of the map's ~530-unit std) and fixed by scaling every object's X/Y (not Z) in `SteppeTemplate\Content.script` by 2.0, the same stretch factor - verified this puts every object back on the exact heightmap pixel it was authored for. This same fix also resolved the RouterZone soft-filter issue, so that filter was **re-enabled** for the steppe target (had been disabled as a workaround before the real root cause was known). Re-ran the full 20-combination sweep with it back on - all pass. Retested and confirmed working in-Editor.

- [x] **Player spawn got tracked/spotted immediately - repositioned and reoriented 2026-07-03, per user's fix.** Once the floating-object bug was fixed, the inherited `Mission1` spawn (only 1300-1550m from the Tiger + 2 Pak 40s, with no forest cover on the new sparse-steppe map to screen it) got the player spotted the instant they spawned - the wooded original map had silently protected against this same layout via tree cover the whole time. Fixed by moving the spawn to 2000m from the enemy cluster along the same approach axis, and rotating to face back toward the cluster (rotation convention confirmed empirically from the `envr_*` obstacle objects' clean 2D-rotation matrices before trusting it). Z height for the new spawn location needed a linear fit calibrated from the other 26 correctly-placed objects (`Z = 0.010522*raw_heightmap_value + 523.43`, residuals mostly single-digit to low-teens against a ~40-unit real range) since the exact-pixel-match trick from the floating-gun fix only works when relocating an *existing* correctly-authored point, not placing a genuinely new one - flagged as a statistical estimate, not a guaranteed exact match, worth a visual check. Also widened `CockpitMapAccessBox` slightly to cover the new spawn. Re-ran the full sweep (12 combinations) - all pass. Confirmed visually working in-Editor (`editor.log` clean, same pre-existing benign noise as every other clean check this session).
- [x] **Dynamic mission-briefing text ("scout report") added to the Quick Mission Generator - built 2026-07-03, user's idea.** Both generated mission slots previously showed generic, disconnected placeholder briefing text pulled from a shared `[MissionTest]` locale section (e.g. "Destroy the ZIS-3 battery" regardless of whether that unit type was even in that run's roster) - and that placeholder text was actively misleading, since the real (only) win condition is reaching the marked NavPoint, not destroying anything. `generate_mission.py` now computes a real scout report from the actual randomized layout (enemy composition by type, distance in km, compass bearing from player spawn). `Objective01` now accurately describes the real win condition. Caught and fixed a real grammar bug during testing ("infantrys" - fixed to treat "infantry" as invariant). **Superseded same day, see next entry** - the original delivery mechanism (literal `WString` values written straight into `MissionTestStrings.script`) broke the real in-game briefing menu even though it worked fine in the Editor.
- [x] **"MissionName not found" briefing-menu crash — root cause found and fixed 2026-07-03.** The literal-`WString` delivery mechanism from the entry above loaded fine in the Level Editor but failed in the real in-game briefing menu with `"Static variable MissionName not found in class C...Mission_Strings"`, cascading into a `SetText` failure - and this persisted even after a genuinely clean Editor/cache restart (the user's report of this was what ruled out an initial stale-cache misdiagnosis). Root cause, confirmed via cross-codebase evidence: `getStaticClassMember()`'s reflection does not reliably find literal `WString` static fields, even though literal plain `String` fields work fine via the exact same mechanism (proven precedent: `Common\PassangerAnimator.script`'s `ANIM_HMove` field). Every real, active `WString` field in every mission's Strings class anywhere in the codebase uses `getLocalized(...)` - there's no working precedent for a literal `WString` anywhere, so the earlier entry's citation of `Common\Mission.script:2706` (`WString Result = "BAD ID";`) turned out to be a weaker precedent than first thought - that's a local variable, not a reflected static class field. Fix: `MissionTestStrings.script` is a static file again (not a per-run output), using `getLocalized(LOCALE_SECTION, "Field")` against two new dedicated `eng.locale` sections (`[QuickMissionGenerated]`, `[SteppeMissionGenerated]`) - never the shared `[MissionTest]` section `Mission1` depends on. `generate_mission.py` now rewrites only that one dedicated section each run (`parse_locale_sections`/`render_locale_sections`/`update_locale_section`), with its own safety check that every other locale section stays byte-identical. Verified with a 40-combination sweep - single-section replacement (no duplication), `[MissionTest]` untouched, 0 CP1251 corruption. `Tools\MissionGenerator\README.txt`'s "what it will never touch" section updated to match.
- [ ] **Make the T-34/76 (`CTankT34_76_42Unit`) playable** - currently AI-only, zero cockpit setup in `Scripts\Units\T34_76_42.script`, unlike the playable `T34_85_44Unit.script`. Promising: both resolve to the same shared `CS_T34` cockpit style, suggesting the interior was designed to be reused. Unverified: whether the 76's 3D model actually has the interior geometry/joints needed - same risk category as the Tiger's LATE-model gaps.

- [x] **Metal-hit splash/smoke effect was oversized and fell back to cubes on track/armor hits** — fixed 2026-07-02, confirmed via play-test (the `Material "16"`-`"29"` not-found errors are gone from `execution.log`). `Scripts\Common\EffectsMetal.script`'s `CCalibre7576_85_88BulletMetalHitSplashEffect`/`SmokeEffect` classes (and the `Subcalibre` duplicates) had been edited a while back while chasing spall-effect realism (user's own words: "we now know exactly how these look thanks [to] an ongoing conflict") — every duration, spawn radius, particle size/count, and brightness parameter was multiplied up (2x-5x), with the old values preserved in `// Was X` comments. The smoke effect's particle-count loops fed the same loop counter into `SetFixedMaterial(new String(I))` as the texture-frame index; bumping counts from 12/8/5 to 30/20/15 pushed `I` past the smoke texture set's actual 16 frames, so the engine's missing-material fallback rendered as solid cubes instead of smoke — this is what looked like "massive flames followed by cubes" on track hits. Reverted every parameter to its documented original value in both the Calibre and Subcalibre variants.
- [x] **Added real spall/fragment debris effect (done properly this time)** — 2026-07-02. Built a new `CCalibre7576_85_88BulletMetalHitDebrisEffect` in `EffectsMetal.script`, modeled directly on the existing `CCalibre7576_85_88BulletWoodHitDebrisEffect` (wood splinter) pattern — gravity + tumbling rotation "spray" particles, with the loop bound read from `CEffectsArray::MetalDebrisEffectSkin.Materials.size()` at runtime instead of a hardcoded count, so it can never overrun the texture's actual frame count again. Uses `MetalDebrisEffectSkin`, an asset that was already registered in `EffectsArray.script` (`Common\EffectsArray.script:40,92`) but never wired into any effect until now. Registered as a `#SprayEffect` (matching the wood-debris registration convention) and wired into both `CCalibre7576_85_88BulletMetalHitEffect` and `CSubcalibre7576_85_88BulletMetalHitEffect` in `EffectsComplex.script` — the subcaliber (AP round) chain previously had no fragment/splash component at all, only smoke, despite subcaliber APCR/APDS-style hits being the classic real-world spall case. Play-tested 2026-07-02: not noticeable at normal tank-combat viewing distance with the initial (wood-splinter-scale) tuning. Bumped particle size `0.1→0.35`, speed `6-9→10-16 m/s`, scatter cone `20°→35°`, sample count `24→32` — purely cosmetic tuning, doesn't touch the `Materials.size()` safety mechanism at all. Not yet re-tested.
- [x] **`Cockpit.script` "Invalid this reference" spam — root cause found and fixed** — 2026-07-02, confirmed via play-test (thousands of occurrences down to 0 after the second pass). First pass added `if (X != null)` guards around every `GetObject()`-derived component in `InitializeCockpitMode()`/`ShowCursor()`/`UpdateCursorAndMouse()` (`CommanderPointerRealView`, `CommanderRealView`, `GunnerPointerRealView`, `GunnerRealView`, `WeaponSelector`, `TargetPointer`, `CommanderPointer`, `Cursor`, `CameraLink`) — cut the spam by ~90% but left `m_MFD`/`m_CockpitCameraLink` (persistent class fields, not `GetObject()` lookups) still erroring, proving they're genuinely null in some contexts, not just a cascade artifact as first suspected. Root cause: this file already has an established `if (!m_CockpitExists) return;` guard pattern (used in 16 other places, e.g. `OnCockpitModeChanged`) specifically to stop cockpit methods running on units that never went through `SetupCockpit()` — i.e. AI-driven tanks, which share this same class hierarchy but never get real cockpit UI built. `SetPlayerSit()` in `Cockpit.script` and three direct `InitializeCockpitMode()` calls in `PlayerUnit.script` (`ChangeCommanderState`, `ShakeTank`, `ReturnToBinocular` — all events that legitimately fire for AI tanks too, e.g. being shaken by a nearby explosion) were missing this guard. Added it to all four, matching the existing idiom exactly instead of more scattered null-checks. Incidentally caused (and immediately fixed) a fresh CP1251 corruption in `PlayerUnit.script` during this edit — see [[feedback_cp1251_encoding]] for the process refinement this prompted (pre-edit checks aren't sufficient on their own, need a post-edit check too).
- [x] **Found and fixed unrelated pre-existing CP1251 corruption in `EffectsArray.script`** — 2026-07-02, discovered incidentally while editing the file above (line 358, a dead `//`-commented line describing `m_EffectsExplosionMap`'s column layout, fully baked-in `\xef\xbf\xbd` bytes, zero gameplay impact). Predates this session's edits — confirmed pre-existing, not caused by today's changes. Docs-repo mirror had a different/older version of the file without this exact line, so the original Russian text couldn't be recovered; replaced with an equivalent plain-English comment via safe byte-level write instead of guessing at Cyrillic reconstruction.

- [x] **Per-tank machine gun bullet velocity** — 2026-07-02. Every tank MG in the game (Tiger coax + turret, Pz IV coax + turret, T-34/76 coax + turret, T-34/85 coax + turret, Hanomag) previously shared one generic `InitBulletSpeed = 650.0` from the base `CMachineGun` class. Added named per-unit constants to `Scripts\Common\Piercing.script` (`TankPzVIAusfEMachineGunBulletSpeed`, `TankPzIVAusfGMachineGunBulletSpeed`, `BtrHanomag251AusfCMachineGunBulletSpeed` = `755.0*0.8` for MG34/7.92x57mm; `TankT34_76_42MachineGunBulletSpeed`, `TankT34_85_44MachineGunBulletSpeed` = `840.0*0.8` for DT-29/7.62x54mmR), following the file's existing `real_velocity * 0.8` convention (verified against the Tiger's own 88mm gun, whose in-game `770.0*0.8` matches the real KwK 36's documented ~770 m/s almost exactly — confirms the `*0.8` is a deliberate uniform balance discount, not arbitrary). Added `float InitBulletSpeed = CPiercing::<Constant>;` overrides to all 10 weapon classes across 5 unit files, mirroring the one existing precedent for this pattern (`BtrM3A1HalftruckUnit.script`'s M3 halftrack MG). Result: German MGs end up slightly slower than the old shared default (604 vs 650), Soviet DT-29s slightly faster (672 vs 650) — a real physical difference (DT-29 fires a more powerful cartridge), not just an across-the-board buff. Not yet in-game verified — needs a play-test.
- [x] **Found and fixed more pre-existing CP1251 corruption, incidental to the above** — 2026-07-02. Editing `TankPzVIAusfEUnit.script`, `TankPzIVGUnit.script`, `T34_76_42.script`, and `T34_85_44.script` today surfaced legacy corruption already baked into several comments in each file (predates this session — same category as other pre-existing corruption fixed earlier), unrelated to the actual edits made. All 4 files had usable clean copies in the docs repo mirror (`TvT\Units\`), so exact original Cyrillic text was restored via safe byte-level write rather than guessed. 17 lines total repaired across the 4 files.

- [ ] **Machine gun penetration modeling (abandoned experiment, not just a missing override)** — noted 2026-07-02, not started. `BtrM3A1HalftruckUnit.script`'s `CBtrM3A1HalftruckMachineGunBulletControl` has 3 commented-out lines (`PenetrationPower`, `PenetrationByDistance`, a duplicate `BulletSpeed`) referencing real tuned constants already sitting in `Piercing.script`, unused. Unlike the MG velocity fix, the base `CMachineGunBulletControl` class doesn't structurally support penetration falloff at all — no MG bullet in the game currently models penetration, just flat damage. Extending this would mean building the mechanism for real, not just copying a working pattern to more units. Bigger scope, hold until explicitly requested.
- [ ] **`TankPzVI_LATE` — a second Tiger variant, fully stat-balanced in `Piercing.script`, never built as a unit** — found 2026-07-02 via a systematic scan of every `Piercing.script` constant for zero cross-references (47 of 248 constants are unused; 27 of those are this variant's full Calibre/Subcalibre/HE ballistics + MG damage). No `Units\TankPzVI_LATE*.script` file exists anywhere. Connects to the already-documented Tiger MAIN→LATE 3D model swap and animation gaps.
- [ ] **Known cut content roster (name-only ghosts in `Resources\Messages.rsr`'s death-message table)** — found 2026-07-02, chasing a "did the devs start a Tiger II?" question. `str_DeathKingTiger = "KingTiger II"` exists as a kill-notification string (same table every shipped vehicle has one in) but has zero trace anywhere else — no `Units\` script, no model reference, no `Piercing.script` ballistics (a step less complete than `TankPzVI_LATE` above, which at least got a full stat block). Pulling the full death-message table open showed this isn't just the Tiger II: of 41 entries, only ~15 map to real shipped units (some of those are just AI/player death-label variants of the same tank, not separate units). The other ~25 are pure ghosts, confirmed via `grep` against `Scripts\Units\` (zero files match any of these names):
  - Tiger Ausf.E1 (a second, distinct Tiger E variant beyond the shipped one)
  - Panther Ausf.D
  - KV-85, KV-1S (1943), KV-1 (1942)
  - Wespe, Hummel, Nashorn, SU-122, StuG III Ausf F8 (distinct from the shipped StuG-40), a Sturmhaubitze
  - Pz II Ausf C, Pz III /L24, Pz III /L60
  - Flak 88, Pak 43, FH18 150mm, sFH 105mm, ML-19 122mm, ML-20 152mm, 82mm mortar, 120mm mortar
  Reference/background only — confirms the shipped ~10-12 vehicle roster was cut down from a much bigger original plan. Not actionable unless someone wants to attempt building one of these from scratch (new model + full unit script + Piercing.script wiring, same scope as the T-34/76 playability idea but with no existing asset to lean on).
- [x] **Tiger's own machine gun fire effect missing — fixed** — 2026-07-02. Added `CMachineGunMG34FireEffect` to `EffectsComplex.script` (identical body to the existing `CMachineGunDTFireEffect`, matching the established one-class-per-weapon-family pattern) and registered it as `"MachineGunMG34FireEffect"` in `EffectsArray.script`, right next to the DT one it mirrors.
- [x] **Zis-3 explosion sound missing — fixed, plus found the identical gap on Pak-40** — 2026-07-02. Added `CGunZis3ExplosionSound` to `Sounds.script` using `Sounds/ArmouredItem_Destroy.wav` — an asset that already existed on disk but was never referenced by anything (same "asset built, never wired up" pattern found several times this session). While fixing it, found `GunPak40Unit.script` has the exact same gap (`SoundId = "GunPak40ExplosionSound"`, never registered) — fixed that too since it's the identical one-line pattern in the same file.
- [ ] **Tiger 3D model animation gaps** — missing gun-laying needles, commander hatch, and a few gauges, from the `Cu_veh_PzVI_MAINModel` → `Cu_veh_PzVI_LATEModel` swap (part of earlier "improved LODs" work). Needs actual Maya work, not scripting — `Documentation/T34_vs_Tiger_Maya_Export_Manual(V3).md` and the newer `export manual. Tutorial 1 2024 revision b.pdf` (not yet added to this repo) are the relevant references.
- [x] **Proper AI Task classes for Campaign_2\Mission_5's 3 groups** — done 2026-07-02. Found real functional bugs, not just missing flavor: `CC2M5GroupStug_40`'s 2 units had no `Task` property at all (every other unit in the mission has one) — added `CBaseAISAUTask`. `CC2M5GroupSU85` and `CC2M5GroupStug_40` were bare stubs with no `Init()` — this file's own pattern shows unit behavior starts inactive until a group explicitly calls `ForEachUnitTask("ActivateBehavior", [true])`, so both were likely sitting completely inert; added `Init()` activating behavior/radar/aggressive posture for both (static defensive/ambush groups, matches their in-game positioning). `CC2M5GroupRusSoldiers` had a fully-built, unused 6-point NavPoint advance path in `Content.script` and was never referenced anywhere in `Mission.script` — added a `StartFirstAdvance`/`EndFirstAdvance_Attack` pair mirroring `CC2M5Group01T_34_85`'s exact idiom (passive approach → aggressive at path end) and wired it into `StartCombat()`. Not yet in-game verified — needs a play-test + log check next.
- [ ] **AutoCommander false→float bug** (`Common\BaseTankAutoThingUI.script` area, fires 3x every mission start) — root cause likely compiled `Controls.dll`/`UI.dll`, not `.script` text. Ruled out every script-side theory this session (including one tested-and-reverted placeholder fix). Would need actual DLL disassembly to go further — bigger, riskier undertaking than anything done so far.
- [x] **`Missions\MISSIONS\CF*/DM*`/`MultiplayerTESTMISSION` error sweep — done 2026-07-03 (static analysis, no runtime log available for these specific missions).** Same technique as the campaign-mission sweep, adapted to work without a live `execution.log` for these 11 files (I can't launch the game myself): cross-referenced every `Mission.script` `extends` chain (all resolve cleanly — `CDMMission`/`CMissionStatus` are real base classes, every mission's own `_Strings` class exists) and every `Content.script` object-group reference (all use the real, defined `CObjectsGroup` — these missions have no `MissionTasks.script` at all, so none of the custom AI Task/Group-class bugs found in the campaign missions apply here). **Found and fixed the same non-unit-length `SunDirection` bug already fixed for Campaign_2\Mission_4/CF2Mission/DM2Mission earlier this session, in 10 more files**: `CF1Mission`/`CF4Mission`/`DM5Mission`/`DM6Mission` shared vector `(-0.99, 0.67, -0.35)` (magnitude 1.246); `CF3Mission`/`CF5Mission`/`CF6Mission`/`DM4Mission`/`MultiplayerTESTMISSION` shared `(-0.005952, -0.155542, -0.305348)` (magnitude 0.343); `DM3Mission` had its own unique non-unit vector (magnitude 0.386). No `//jm` hand-tuning comments on any of them, so nothing suggested these were deliberately left non-unit — fixed each to the same direction normalized to length 1 (same lighting, no more `[Atmosphere] Incorrect sun direction` warning), mirroring the exact fix already applied and confirmed working. **Also found, flagged but NOT fixed** (ambiguous, didn't want to guess): `DM5Mission`/`DM6Mission` have their lens-flare line commented out in `Mission.script`, unlike every other CF/DM mission — could be deliberate (maybe caused a real problem before) or an oversight; `DM6Mission` also has an orphaned, unreferenced `DM6LensFlare.script`. Left alone pending user input. `MyMission`/`MyMPMission` were not covered by this pass (`Mission1`/`QuickMission`/`SteppeTemplate`/`SteppeQuickMission` under `MyMission` were already extensively tested earlier this session; `MyMPMission` has only an untouched `BaseFiles` template, nothing built on it yet to sweep).

## Documentation gaps (schema doc's own "Open Questions" section)

- [ ] `IsMissionFullCompleted()` vs `IsMissionCompleted()` — when is the "full" variant actually used?
- [ ] The 5th `m_MissionObjectives` tuple element (`RedTeamObj`/`BlueTeamObj` counting) — looks multiplayer-specific, needs an MP mission example to confirm.
- [ ] `SOID_MissionController`'s full event/method surface — only `"StartRetreat"`/`"CompleteMissionStatus"` traced so far.

---

## Where things stand, end of 2026-08-20

Four things are **built and waiting on one play session** each. None needs any
work first — launch ZW through `K:	vt_los\play_zw.bat`, play Zitadelle M1,
then read the logs.

1. **Commander field scan.** `tvt_los_hook.dll` now walks
   `CAutoCommanderComponent` on its first tick looking for values
   `Common\AutoCommander.script` sets — RadarMaxDistance 3100, RadarUpdateTime
   4.0, FrontDanger 130, BackDanger 120, LastTargetDangerAdd 30. The log line
   `[CMDR] scanning the live object...` gives its field layout, and from there
   the range comparison that needs gating. **This is the next real step on the
   gunner.** Static scanning of the update was tried and found nothing: no
   float member reads, no calls to the distance helper. It calls three nearby
   helpers (`+0x0413A0`, `+0x041680`, `+0x0417D0`) which are the likely
   location.
2. **Wingman cruise speed.** `0.8 * max_speed` → `0.15 * max_speed` in
   `setOrder_Formation`. Measured cause: on station it averaged 1.14 m/s
   against the leader's 0.92 and sat fully stopped in 10% of samples. Untested.
3. **Lighter, sky-tinted shadows** `(122, 140, 156)` in ZW Kursk and REDUX
   BerezovKursk. Verdict never reported.
4. **Wingman LOS calibration** — ZW `sight_scale = 1300`, canopy-depth
   attenuation. Confirmed working on the AI (84–91% of sightings refused); the
   1600 m Pak engagement was never re-tested after the fix.

**Clean up when the wingman is settled:** `WMTrace` and its `sendEvent` in
`CEFM1LAH_WingmanTask::Init()`, both marked `WMTRACE`, in
`KurskMission\MissionTasks.script`. Backups `.bak_wmtrace*`.

**Closed today:** ZW line of sight (map size and terrain path now read per
mission); the fit check that rejected correct ZW terrain; ZW's executable never
being large-address-aware; the wingman micro-stutter mechanism; fog-on-objects
ruled out as an `Atmosphere.script` value.
