# "Operation Citadel: Berezov" — Panzer Elite Mission Recreation Scoping (2026-07-03)

Scoping pass for recreating one of the user's favorite Panzer Elite (Wings Simulations) missions inside TvT. This document is the full picture gathered today, meant to pick up work later without re-deriving any of it. Source material: `Berezov.zip` (user-provided, on Desktop), containing `Berezov-ger.scn`, `Berezov-us.SCN`, `Berezov.bmp`, and English/German briefing text files for both sides.

## What the mission actually is

"Operation Citadel: Berezov" — a dual-perspective mission set on the historically real first day of the Battle of Kursk (5 July 1943, 08:20 start, 2-hour duration, 31°C, light clouds). German side spearheads a breakthrough with the player's own platoon (`Zug Falke`) leading, `KG Kaiser` (panzers + grenadiers) following behind, punching through three villages in sequence along one road — **Berezov → Gremuchi → Gonki** — against a Soviet defense-in-depth. The Soviet side (not being built yet, see "Build order" below) plays the mirror: hold the line, and specifically flank rather than trade shots at range — their own briefing says "close in... attack them from behind," a real, deliberate asymmetry given the German side's gun-range advantage.

## File format — confirmed plain text, no reverse-engineering needed

`.scn` files are **plain text** (99.95%+ printable ASCII, confirmed by direct byte inspection), using a `[Chunk:TypeName(N)] ... key:value ... [ChunkEnd]` structure. Fully human-readable with the `Read`/`Grep` tools directly — no binary parsing required, unlike TvT's own `.ms2` format. Chunk types found in `Berezov-ger.scn` (131KB): `Globalsettings`, `Node(0-412)` (map reference points), `Area(N)` (named zones, e.g. `BEREZOV`/`GREMUCHI`/`GONKI`/`Rakovo`/`Visloe`, each linked to 2 boundary `Node`s), `PathNode(0-333)` + `Path(0-27)` (AI movement routes), `PreDefPos(0-7)` (predefined positions, likely tied to the named briefing markers), `ArtAirStrikes` (artillery/air support config), `CombatGroup(N)` + nested `Unit(N)` (the order of battle — 64 individual units across ~19 named platoons/groups), `CombatScript(N)` + `ScriptRow(N)` (the event/trigger system), `BehaviourSetNew(N)` (AI engagement-range profiles: `_Ignore all`, `_Low/Medium/Long Range Fight`), `UserDefGroup(N)`.

An existing PE mission-analysis toolkit already exists at `L:\2025\PE\PE Mission Reader CMD\` (built earlier by the user with prior AI assistance) — focused on the binary `.dat` terrain/object format, not needed here since `.scn` turned out to be plain text.

## Mission-goal system — directly comparable to TvT's own

`Globalsettings` has explicit, semicolon-delimited goal definitions:
```
MissionGoal0:Take GONKI;primary;Clear;90;area;GONKI;;
MissionGoal1:Destroy Soviet HQ;primary;Destroy;100;cg;Soviet HQ;;
MissionGoal2:Destroy Plt.Samsonov;secondary;Destroy;100;cg;Plt.Samsonov;;
MissionGoal3:Take BEREZOV;Secondary;Clear;90;area;BEREZOV;;
MissionGoal4:GONKI;bonus;Arrive;40;cg;Zug Falke;area;GONKI
```
Format: `Name;PrimaryOrSecondaryOrBonus;Verb;Threshold;TargetKind;TargetName;AreaKind;AreaName`. This maps cleanly onto TvT's own primary/secondary/bonus `m_MissionObjectives` tuple system — no new mission-goal mechanism needed on the TvT side.

## Trigger/event system — same shape as work already done this session

`CombatScript` chunks fire on `Always` (unconditional) or `CG State` events (a named combat group arrives at a named area, is "under attack," or is "destroyed"), each driving a chain of `ScriptRow` actions (`move` to a road/area, `Wait` a timer, `American`/artillery call, trigger a numbered briefing message). Example: a `CombatScript` on `KG Kaiser` triggers a `move` `ScriptRow` toward `BEREZOV` that also sends message #2 ("KG Kaiser is moving out towards Berezov now.") — directly matching the numbered `[Messages]` list in the briefing `.txt` files. This is functionally the same pattern already used this session for the steppe mission's Soviet group AI (state-triggered task classes reacting to combat/arrival events) — PE just expresses it as a data table instead of script code. No new TvT capability needed, just the same kind of per-group Task-class scripting already proven.

## Roster — real discrepancy found and resolved

**Important**: the bundled `Berezov-ger.scn`'s actual unit data uses **Panzer III/IV** for the German side (`Zug Falke` = 5× `Pz4H2`, `KG Kaiser` = mixed `Pz3M`/`Pz3L`/`Pz3J`), **not** the "14 Tigers... 8th Kp./SS Pz Rgt. 2" described in the bundled English briefing text. Soviet side: T-34/76 (`T3476-0/1/2`, several 3-4-unit platoons: `Plt.Samsonov`, `Plt.Kutuzov`, `Plt.Popov`, `Plt.Oleshev`), KV-1 heavies (`KV176-0`, `Plt.Voronov` — 3 units, despite the briefing describing this position as a "T-34 concentration"), SU-152 heavy assault guns (`Plt.Stepichev`, `Plt.Kotin`), 76mm AT guns + crews (`Plt.Berzina`, `Plt.Rhyzov`), `Soviet HQ` (SU-76M + truck + infantry, the primary-objective "destroy HQ" target), plus recon/light units (`Plt.Zhilin`: armored car + 2× T-70). This is likely an earlier/base-game roster revision; the Tiger-equipped version the user actually played is a variant not included in this particular file.

**Decided (user confirmed from memory of actual play)**: build the **Tiger version** — `Zug Falke` = **1× Tiger (player) + 4× Panzer IV (AI wingmen)**, `KG Kaiser` stays Panzer III × 4 (AI support column) exactly as authored. This is how the user actually played it ("just me... the rest of the zug had 4's") — PE lets a player freely pick their own personal vehicle within a platoon (constrained by period-correctness/supply in PE's career mode), independent of the squad's default equipment; that meta vehicle-choice/supply system itself is explicitly **out of scope** — a separate, much bigger feature TvT doesn't have and isn't being built here. For this mission, the Tiger-for-`Zug Falke`-only substitution is simply a fixed roster choice, no new engine capability required (TvT already supports mixed-vehicle-type platoons with one player slot).

No direct TvT equivalents exist for KV-1, SU-152, or Panzer III — the Soviet-side build (see below) will need stand-ins or an adapted roster when it's tackled.

## Scale — comfortably within TvT's proven budget

64 individual units across ~19 combat groups (platoon-sized, 2-5 units each), well within the unit-count budget already proven this session for TvT missions (`Campaign_2\Mission_5` runs 60fps with a comparable count).

## Terrain — real distances extracted, SteppeTemplate confirmed as the build target

**Decided**: reuse `Missions\MyMission\SteppeTemplate\` (already built and tested this session — 18000×18000 world units, sparse forest, 125fps) rather than build new terrain from scratch. Confirmed TvT's world units and PE's map units are both meters-scale (PE's `Berezov.bmp` is exactly 1/5th of `ScenarioWidth`/`ScenarioHeight` — 5920÷1184 = 4920÷984 = 5.0 precisely, confirming consistent real map units), so the real village-to-village distances can be used directly with no scaling or distortion needed.

**Extracted real distances** (from each `Area`'s two boundary `Node` positions, midpoint-to-midpoint):
- Rakovo → Berezov: ~945 units
- Berezov → Gremuchi: ~1,346 units
- Gremuchi → Gonki: ~1,983 units
- Total Berezov-to-Gonki advance corridor: ~3,310 units

A ~4.2km (Rakovo-to-Gonki) corridor fits comfortably inside `SteppeTemplate`'s 18km×18km space, using well under a quarter of its width.

**Still open / not yet done**:
- The road isn't straight — the briefing map shows it jogging at each village. Needs tracing from the map image and either finding/extending `SteppeTemplate`'s existing road or adding one.
- `SteppeTemplate` currently has zero buildings — the three village clusters are real new authoring work (though existing TvT missions with village prop clusters can be used as a pattern reference, not built from nothing).

## Anchor point selection — DONE 2026-07-03

Loaded `SteppeTemplate`'s actual `hmap.raw` (2049×2049, 16-bit, confirmed matches `MatrixWidth=18000` at 8.789 m/pixel) and `hwater.raw` (a single constant water-level value, 7785 - water only appears where the heightmap itself dips below that, not a separate per-pixel bitmap). Scanned every horizontal band of the heightmap for the flattest, driest run of the required ~4.2km length, with a safety margin from the map edges. Found a genuinely excellent candidate at heightmap row 720 (world Y=6328): zero water crossings and only ~36 units of elevation variation (out of a ~3276-unit total map range) across the whole span - essentially dead flat.

Cross-checked the pixel-to-world coordinate conversion against the existing `MainPlayerUnit` spawn already in `SteppeTemplate`'s `Content.script` (confirmed it lands on dry ground at the expected height) before trusting the mapping.

**Final anchor**: Berezov at world (2150, 6328). Gremuchi and Gonki placed using the *real* Berezov→Gremuchi (1346m, bearing 89.5°) and Gremuchi→Gonki (1983m, bearing 101.8°) vectors from the original file - preserving the actual road jog (bends slightly south-of-east past Gremuchi) rather than flattening everything onto one artificial straight line. Every one of the 19 combat groups was then placed at its real distance/bearing from the Berezov anchor and individually checked against the heightmap - **all 19 land on dry, in-bounds terrain**, no exceptions needed. Full world coordinates (villages + every combat group) saved to `tvt_world_placement` in `Documentation/Berezov_OOB_positions_2026-07-03.json`.

**Still open**: the road's exact traced shape (we have the right bend angles now, but not a pixel-traced path to lay an actual road mesh/texture along) - downgraded to purely cosmetic, see below.

## Road system reconsidered — it's a ground texture, not an object/zone system

Investigated how TvT actually represents roads by checking a real campaign mission's (`Campaign_2\Mission_6`) `Terrain.script`/`Content.script`: no road object class, no `RegisterRoadRegion`-equivalent zone system - the only road-adjacent thing found was `ZMC_RoadForest` (a tree-placement pattern for lining a road with trees, not a road surface itself). The actual ground appearance comes entirely from `lnd_*.tex`, the terrain's single base texture set via `SetupTerrainMainMaterial` - meaning a visible road would need to be painted directly into that texture. This is purely cosmetic and has zero effect on AI movement, which runs on TvT's own separate NavPoint/waypoint system. **Reprioritized**: treated as a later cosmetic pass, not a blocker - moved straight to village construction and unit placement instead.

## Mission folder created and registered — DONE 2026-07-03

Set up `Missions\MyMission\Berezov\` following the exact pattern already proven twice this session (`Mission1`→`QuickMission`, `SteppeTemplate`→`SteppeQuickMission`): copied `SteppeTemplate`'s terrain files verbatim (all 7 binary files checksum-verified byte-identical), renamed every class/path identifier from `SteppeTemplate`/`Berezov` throughout `Content.script`/`Mission.script`/`Terrain.script`/`WorldMatricies.script`/`Atmosphere.script`/`MissionTestStrings.script`, and registered `"Operation Citadel: Berezov"` in `Scripts\Editor\MenuConfig.script`'s `MissionLoadList`. Gave it its own dedicated locale section (`[MissionBerezov]` in `Locale\eng.locale`) with real briefing text adapted from the original Panzer Elite mission's Tiger-version briefing, rather than inheriting the shared `[MissionTest]` placeholder tutorial text every other custom mission uses. Also fixed the same non-unit-length `SunDirection` bug (inherited unchanged from `SteppeTemplate`) found and fixed elsewhere tonight.

**Also confirmed while investigating**: TvT's German campaign (`Campaign_2`) and Soviet campaign (`Campaign_1`) each already have a full, real 6 missions - there is no vacant "6th slot" to drop this into (an earlier assumption of mine was wrong). Staying standalone as planned; extending the real campaign to a 7th mission would be a much bigger, more sensitive change touching shared progression systems, and wasn't pursued.

## Villages built and full order of battle placed — DONE 2026-07-03

**Unit roster mapping** (PE name → real TvT `Units\` class, cross-checked against actual class declarations, not guessed): `Pz4H2`/`Pz3M`/`Pz3L`/`Pz3J` → `CTankPzIVGUnit`; the player's own first `Zug Falke` unit → `CTankPzVIAusfEUnit` (the Tiger); `PakCrew` → `CGunPak40Unit`; `SdKfz71`/`SPW2511`/`SPW251MG`/`SPW2509` → `CBtrHanomag251AusfCUnit`; `GInf43` → `CGermanSoldierRifleUnit`; `T3476-*` → `CTankT34_76_42Unit`; `ATRGun76`/`76Net` → `CGunZis3Unit`; `SOVinf` → `CSovietSoldierRifleUnit`; `Truck4` → `CTruckZis5Unit`. `GunCrew` entries (4 total) are dropped - bundled into the gun unit itself in TvT, not separately placed.

**Three substitutions needed, no direct TvT equivalent exists** (flagging honestly, not hiding): `KV176-0` (`Plt.Voronov`'s 3 KV-1 heavies) → `CTankT34_76_42Unit` - loses the "heavy tank" flavor but avoids inventing an anachronism, since a real KV-1 replacement doesn't exist in TvT at all. `SU152-0`/`SU76M` (Soviet assault guns/SPGs, `Plt.Stepichev`/`Plt.Kotin`/`Plt.Berzina`/`Soviet HQ`) → `CSAUSU85Unit` - the closest available Soviet SPG in role/silhouette, though SU-85 is a ~2-month anachronism for this mission's exact 5 July 1943 date (same tradeoff already accepted for the broader steppe-mission project's looser framing). `BA20`+`T70A-0` (`Plt.Zhilin`'s light recon platoon, armored car + 2 light tanks) → `CTankT34_76_42Unit` - loses the "light recon" flavor since neither vehicle type exists in TvT.

**Position translation**: every unit's real position was translated from the original PE file's own coordinate space onto our TvT anchor via a pure translation (found and fixed a real bug here - initially used the raw PE coordinates directly without translating them, which would have placed every unit in the wrong spot; caught it by checking the generated positions against the already-validated group-level placement before finalizing). Re-verified all 60 individual unit positions land in-bounds and on dry ground after the fix, not just the group-level anchors.

**Villages**: built using the real village-construction pattern found in an existing TvT mission (`DM3Mission`'s "Vysochany" village - houses/sheds/fences grouped, `SurfaceControl:"PutonGroundUpright"`/`"PutonGround"` auto-conforming to terrain height so exact Z doesn't need to be hand-computed). Each of Berezov/Gremuchi/Gonki got a simple street-style cluster: 4 houses (`CUSRHouseWoodUnit`) alternating sides of the road axis, 2 sheds (`CUSRShedWoodUnit`/`CUSRShedWood02Unit`), a well (`CWaterWell_1Unit`), and 4 fence segments (`CFenceWickerUnit`/`CFencePoleUnit`) - 33 village objects total.

**Result**: `Content.script`'s inherited `SteppeTemplate` placeholder content (the tutorial's generic player unit, 8 generic buildings, 2 generic Pak 40s, 12 generic `envr_` scenery objects, one enemy Panzer IV oddly named `"tiger"`, and its own NavPoint) was fully replaced with 94 real objects: 60 combat units + 33 village props + 1 `NavPoint` at Gonki (the "Take Gonki" objective marker). Verified the resulting `Content.script` is structurally sound (balanced brackets, no duplicate object IDs among 95 total entries) and every placed object's X/Y falls within the map bounds.

**Still open / not yet done**: unit facing/rotation only uses a simple default heading (German units facing east, Soviet facing west) rather than tactically-appropriate individual facings; `Mission.script`/`MissionTasks.script` still have no real trigger logic wired up (the `CombatScript`/`ScriptRow` event system from the original file hasn't been translated into TvT's own Task-class scripting yet); the actual `MissionGoal0-4` objectives (Take Gonki, Destroy Soviet HQ, Destroy Plt.Samsonov, Take Berezov, bonus Zug Falke reaches Gonki) aren't wired into TvT's own mission-goal system yet.

## First in-Editor test — real bug found and fixed 2026-07-03

User tested it in the Level Editor and shared `editor.log`. Overwhelmingly good news: all 60 combat units and all 33 village props loaded successfully by name (confirmed individually in the log), forest generation and router-map generation both completed normally, no crash.

**One real bug found**: the log showed `[Missin] CreatePlayerObject0` firing and creating a *second* player unit as `CTankT34_85_44Unit` (a T-34/85) - confirmed for real by the end-of-session component tally (`CPlayerUnit 2`, `CTankT34_85_44Unit 1`), not a log fluke. Traced the cause in `Scripts\Common\Mission.script`: the engine's player-detection logic doesn't scan `Content.script` for `IsPlayer:true` - it looks for an object with one *specific, hardcoded name* (`GetMainPlayerObjectID()`, which resolves to the literal name every mission's player object must use). Since our Tiger was named `"Berezov_ZugFalke_1"` instead, the engine found no match, assumed no player existed, and spawned a default fallback vehicle (`CGameSettings::PlayerUnitScript`) instead.

Confirmed the required convention by checking a real shipped mission: `Campaign_2\Mission_6`'s own player object (also a Tiger, `CTankPzVIAusfEUnit`) is literally named `"MainPlayerUnit"` - matching what every mission built this session used before (`Mission1`, `QuickMission`, `SteppeTemplate`, etc.), which is why this only surfaced now that a hand-authored, non-generator mission finally used a different naming scheme for its player object.

**Fix**: renamed the object back to `"MainPlayerUnit"` in `Content.script` (only the ID changed - position/class/properties untouched). Synced to the docs repo.

## Second in-Editor test — player-unit fix confirmed, but "had no clue where to go"

User re-tested. `editor.log` confirmed the fix worked completely: exactly one `CPlayerUnit`/`TankVehicle`, `MainPlayerUnit` loaded cleanly, no more phantom T-34/85, no new errors, same ~5.1s load time. But the user reported having no idea where to go in-game - a real, separate gap: placing a `NavPoint` object in `Content.script` doesn't automatically make it show up on the player's compass/map, and nothing was tracking mission objectives at all yet.

**Root cause, found by comparing against a real working mission** (`Campaign_2\Mission_6`): `Mission.script`'s `m_NavpointsForPlayerMap` array (which controls what actually renders on the player's cockpit map) was empty - inherited unchanged from `SteppeTemplate`, which also leaves it empty. Also found `CockpitMapAccessBox` (the bounding box the cockpit map is allowed to display/scroll within) was still set to `SteppeTemplate`'s own quick-mission-generator anchor area (X:5484-14484, Y:3550-13100) - nowhere near our actual Berezov corridor (X:266-6336, Y:4004-6939) - a second, compounding reason nothing useful showed on the map.

**Real objective/kill-tracking system built**, by studying exactly how `Campaign_2\Mission_6` wires up its own objectives (found the actual pattern: each "destroy X" objective has a `KillList` array of expected-to-die unit IDs, decremented in an `event void OnObjectDestroyed(String _ObjectID)` handler, calling `SetObjectiveStatus(index, MOSID_Completed)` when a list empties):
- Registered `GonkiObjective` in `m_NavpointsForPlayerMap` and fixed `CockpitMapAccessBox` to actually bound our real mission area.
- Built 3 real, working objectives in `m_MissionObjectives` (TvT's own system only has Primary/Secondary tiers, no Bonus - folded the original mission's bonus "Zug Falke reaches Gonki" into the primary Take-Gonki objective, since reaching the `NavPoint` already ends the mission): **Take Gonki** (primary, completes via `OnObjectEnterNavPoint` when `MainPlayerUnit` reaches `GonkiObjective`), **Destroy Soviet HQ** (primary, `KillList_SovietHQ` = the 3 `Berezov_SovietHQ_*` unit IDs), **Destroy Plt. Samsonov** (secondary, `KillList_PltSamsonov` = the 4 `Berezov_PltSamsonov_*` unit IDs).
- Rewrote the `[MissionBerezov]` locale text to match these 3 real objectives exactly, rather than the earlier, more aspirational 4-objective draft (dropped "Take Berezov" - a genuine "clear this area" objective needs a zone-tracking mechanism this pass didn't build; being honest that it's not implemented rather than faking it with a mismatched proxy).
- Confirmed `OnObjectDestroyed` needed to call `CMission::OnObjectDestroyed(_ObjectID)` first (checked the real mission does this) before its own logic.

Verified `Mission.script`'s braces/brackets/parens are all balanced. Synced to the docs repo. Not yet tested - needs another Editor pass to confirm the compass/map now shows Gonki and the two kill-objectives actually complete on the real units dying.

**Still open**: "Take Berezov" (a genuine area-clear objective) isn't implemented - would need a zone-tracking mechanism not built yet.

## Third in-Editor test — rotation matrix convention was wrong, fixed for every unit

User tested again: objectives/map fix confirmed working, but reported Berezov sitting at "3 o'clock" relative to the direction the player spawns facing - i.e. off to the right, not ahead. That's a precise, diagnostic detail: exactly a 90-degree rotation error.

**Root cause found and confirmed mathematically before touching anything**: the original rotation-matrix formula assumed the engine reads a placed object's **row1** as its forward-facing vector (with row0 as "right"). Checked this assumption directly: at heading 90° (intended to face east, roughly toward Berezov), the old formula's **row0** - not row1 - evaluates to `(0, -1)`, which is north, not east. If the engine actually reads row0 as forward (the opposite of what was assumed), a vehicle told to face "east" would actually face north - and the real target (east) would then appear 90° to its right. That's exactly "3 o'clock." The math confirmed the bug before any blind trial-and-error.

**Fix**: rewrote the rotation matrix formula so row0 carries the forward vector and row1 carries the right vector (swapped from before), using the same bearing convention (0°=north, 90°=east) throughout. Regenerated the rotation for **all 94 objects** - not just the player - since every unit and village prop shared the same buggy formula and would have been similarly misoriented. Also had to make sure regenerating didn't quietly undo the earlier `MainPlayerUnit` rename fix (the source data still had the old `Berezov_ZugFalke_1` id) - fixed the id in the source data first, then verified after re-splicing that `MainPlayerUnit` appears exactly once and the old id doesn't appear at all.

Verified bracket/paren balance again after the regeneration. Synced to the docs repo.

## Fourth in-Editor test — heading still slightly off; real fix taken from the user's own correction; Hanomag friendly-fire found and fixed

User manually rotated `MainPlayerUnit` in the Editor to the actual correct direction and saved it, rather than describing the error - a much more reliable ground truth than another round of guessing. Read the resulting matrix back out of the live file and solved for the exact heading it represents: **43.46°** (bearing convention, 0°=north/90°=east) - notably different from the 90° "face east" assumption used everywhere else. Applied this same corrected heading to all 14 other German ("Axis") unit entries, leaving the user's own `MainPlayerUnit` matrix completely untouched.

**Second issue reported in the same message**: one Hanomag half-track was "constantly firing at the one in front of it" - real friendly fire, not a data typo (double-checked: all 4 Hanomag entries are correctly marked `Affiliation:"FRIEND"`, and the `DefaultMask`/`Mask` arrays in `Mission.script` turned out to be vestigial, never actually wired to weapon targeting - not the cause). Traced the likely real cause geometrically: under the old 90° heading, `Zug Lex`'s two Hanomags were positioned almost exactly one directly behind the other, both facing the same way - a classic "shoot the friendly vehicle sitting in my own forward arc" setup regardless of the exact native AI logic involved (which can't be inspected directly without an engine disassembly, well beyond this pass's scope).

**A real mistake made and caught in the same pass**: first attempt added a perpendicular offset to spread the two Hanomags apart, but got the sign/reasoning wrong - checked the math afterward and found it had *cancelled out* their existing natural separation instead of increasing it (from 51 units of perpendicular separation down to just 1.1° off dead-ahead, worse than before). Caught this by explicitly computing the forward/right decomposition of their relative position before committing to anything further, found the *original* (pre-offset) positions already had a reasonable 51-unit perpendicular gap once the corrected heading was applied (only ~39° off pure "dead ahead", not aligned at all) - so the fix was simply to revert to the original positions with only the heading corrected, no added offset needed. Verified the final result numerically (80.6 units apart, 39.4° off the forward axis) before syncing.

Both fixes applied to the same `Content.script`, verified balanced, synced to the docs repo.

## AI activation for all 19 combat groups — the "nothing else moves" gap

User noted no unit other than the player moves - correctly anticipating this was already-known territory from earlier tonight's `Campaign_2\Mission_5` fixes: in this engine, placed AI units sit **completely inert** by default until their behavior is explicitly activated - simply having a `Task` property in `Content.script` isn't enough. Confirmed `MissionTasks.script` was still empty boilerplate (never touched since the `SteppeTemplate` copy).

**Built the real activation wiring**, following the exact `UnitGroup`/`CBaseUnitGroup` pattern found in `Campaign_2\Mission_5` (checked the actual working code rather than guessing): each combat group needs (1) a `"UnitGroup"`-type entry in `Content.script` listing its member unit IDs via a `["Units", [...]]` property, and (2) a matching class in `MissionTasks.script` extending `CBaseUnitGroup` with an `Init()` that calls `ForEachUnitTask("ActivateBehavior", [true])`, `ActivateRadar(true)`, and sets `m_EnemyReactionType == ERT_AGGRESSIVE` (kept the `==` exactly as found in the real, confirmed-working source rather than "fixing" it to `=` - not worth the risk of guessing at this DSL's exact grammar when the working reference uses `==`).

Generated all **19 group wrappers** programmatically from the same OOB data used throughout this build, correctly **excluding the player from `Zug Falke`'s AI group** (`MainPlayerUnit` stays out, the other 4 Panzer IVs get the AI wrapper) so activating AI behavior doesn't interfere with manual player control. Verified bracket balance in both files after the additions (19 `UnitGroup` entries in `Content.script`, 19 matching classes in `MissionTasks.script`, both structurally sound).

**Honest scope note**: this activates *combat reactivity* (targeting, shooting, turning to face threats) for every group - a large, real improvement over total inertness - but it does **not** give German units autonomous movement orders to advance along the road toward Gremuchi/Gonki. That would need explicit `NavPoint`-following movement scripting (the same kind of pattern seen in `Campaign_2\Mission_5`'s `StartFirstAdvance`-style events), which is a further, separate piece of work not included in this pass.

**Also seen in the log, judged benign/pre-existing, not touched**: `[Locale] There is no section [MissionBerezov]` warnings appear early in the log alongside identical warnings for `[QuickMissionGenerated]`/`[SteppeMissionGenerated]` (sections confirmed to genuinely exist in `eng.locale`) - looks like a harmless startup-ordering quirk (mission-list generation querying names before the locale file is fully loaded) affecting every custom mission equally, not something introduced by this work. Repeated `[AbstractJoint] Invalid rotation of collision mesh` warnings tie to loading a new instance of the human/infantry rig for the first time (identical quaternion values every occurrence, no longer appearing once that mesh is cached) - a pre-existing content quirk in the base infantry models, unrelated to Berezov specifically.

## Full order-of-battle position extraction — DONE 2026-07-03

Extracted all 19 combat groups / 64 units with exact positions, saved to `Documentation/Berezov_OOB_positions_2026-07-03.json` (group + per-unit `PositionX`/`PositionY`, distance and compass bearing from the Berezov anchor). German groups: `Zug Falke` (player Tiger + 4 AI, dist 1725/bearing 252° from Berezov), `HQ` (Pak crew + halftrack, 1641/251°), `KG Kaiser` (4 tanks, 1725/250°, now Panzer IV per the roster decision above), `Zug Lex` (2 halftracks, 1791/252°), `Zug Weidinger` (infantry + halftrack, 1309/255°) — all clustered west of Berezov, consistent with staging just behind the front line before the push.

Soviet groups span a genuine defense-in-depth, not a flat line — real tactical variety worth preserving in the build:
- Close-in, right on top of Berezov: `Plt.Voronov` (3× KV-1, dist 399/bearing 83°), `Plt.Rhyzov` (AT guns + infantry, 181/286°), `Plt.Zhadov` (AT gun + infantry, 93/189°), `Plt.Zhilin` (armored car + 2 recon tanks, 601/290°).
- Mid-depth, around/behind Gremuchi: `Plt.Samsonov` (4× T-34/76, 1137/92°), `Plt.Sytnik` (5× T-34/76, 1150/64°), `Plt.Kotin` (SU-152 + infantry, 1336/89°).
- Deep reserve, toward/behind Gonki: `Plt.Kutuzov` (4× T-34/76, 2128/79°), `Plt.Stepichev` (SU-152 + infantry, 2295/95°), `Plt.Berzina` (AT gun + SU-152, 2597/95°), `Soviet HQ` (SU-76M + truck + infantry, 3281/98°, the primary "destroy HQ" objective), `Plt.Markov` (AT gun, 3257/97°), `Plt.Oleshev` (4× T-34/76, farthest at 4036/91°, near/past Gonki).
- **Genuine flanking ambush, confirmed real (not a data glitch — checked every individual unit position)**: `Plt.Popov` (4× T-34/76, 2225 units out but at bearing 12° — almost due north of Berezov, off the main east-west corridor entirely) sits far off the line as a flank threat, exactly matching the briefing's own warning about "any tanks attempting an attack from this direction."

## Build order — DECIDED 2026-07-03

1. **Build now**: German attack side only — player as Tiger, `Zug Falke` (4× Panzer IV AI wingmen), `KG Kaiser` (Panzer IV × 4 AI support column — changed from Panzer III, which doesn't exist in TvT at all, confirmed via `ls` on both `Models\` and `Scripts\Units\`) — pushing Berezov → Gremuchi → Gonki against the Soviet defense-in-depth (Soviet roster/positions as authored, pending stand-ins for KV-1/SU-152/etc.).
2. **After testing**: the Soviet defense side, reusing the same underlying battle setup (per the user's own observation, PE's AI is genuinely bilateral — both sides fight for real regardless of which is player-controlled, which is already how TvT's own AI works, not a new feature to build).

## Next mechanical step (not started)

Extract the complete position/unit dataset (all ~64 units across all combat groups) relative to the village anchor points, so the full authored tactical layout (AT gun positions, ambush platoons, reserve lines) is in hand before touching `SteppeTemplate` itself.

## Real movement orders ported from the actual PE mission file

User confirmed after playing that the AI-activation pass above was only half the fix: every group reacts if engaged, but nothing actually *advances* - matching the honest scope note already on record above ("does not give German units autonomous movement orders").

Rather than invent plausible-looking waypoints, parsed the real `Berezov-ger.scn`'s own AI scripting chunks to find the actual, designer-authored movement logic: `CombatGroup` chunks (20 groups) each have a `FirstCombatScript` pointing into a `CombatScript` chunk chain (linked via `NextScript`), and each `CombatScript` has a `BehaviourSet` (fight-range profile) plus an optional `FirstScriptRow` chain (linked via `NextRow`) of actual `Command`s: `move`/`Move` (with `Parm1`=style: `Road`/`Normal`/`Step by Step`, `Parm2`=target - either a named `Area` like `GONKI`/`BEREZOV`, or another `CombatGroup`'s name, meaning "converge on wherever that group currently is"), `Wait` (relative `*HH:MM:SS` delay), `engage`/`defend`, and `American` (an off-map artillery-call command, out of scope for this pass). `Event:Always` scripts fire unconditionally at mission start; `Event:CG State` scripts fire when a named group reaches a named area, is destroyed, or comes under attack - a real, fairly elegant event-driven state machine, not scripted-scripted waypoint choreography.

**Ported for this pass** (`Missions\MyMission\Berezov\MissionTasks.script` + `Mission.script`), using only API calls already proven working elsewhere in this codebase (`SetOrder_MoveToEx` from `Common\UnitGroup.script`, the self-targeting `sendEvent(delay, getIdentificator(this), "Method", [])` delayed-dispatch pattern used throughout `Common\*.script`, and `GetMission().GetObject(id)` / `getPosition(obj).origin` confirmed in exactly this MissionTasks-class context by `Campaign_2\Mission_5`'s own working code):

- **KG Kaiser** - unconditional, 60s after mission start: road-march Berezov → Gonki (the German main advance column; two-point `SetOrder_MoveToEx` queues both legs in one call).
- **Zug Weidinger** - unconditional, 55s: moves directly to Gonki.
- **Plt.Popov** and **Plt.Zhilin** - unconditional (180s / 35s): converge on `MainPlayerUnit`'s position at the moment the timer fires, matching the real mission's "move to Zug Falke" order (a one-shot position sample, not continuous homing - consistent with how the original command almost certainly worked too).
- **Zug Lex** - moves to Gonki 90s after **Plt.Samsonov** is fully destroyed. Reused the existing `KillList_PltSamsonov` (already tracked for Objective 2) and added a call to `GetObject("BerezovZugLex").TriggerAdvance()` right after the objective completes.
- **Plt.Oleshev** - reinforces to Berezov 570s after **Plt.Kutuzov** is fully destroyed. This needed a brand-new `KillList_PltKutuzov` in `Mission.script` (not an objective, purely an internal trigger) wired into `OnObjectDestroyed` the same way.

**Deliberately not ported this pass** (documented gap, not silently dropped): the real mission's "under attack" reactive triggers (`Plt.Kutuzov` moves to Zug Falke when `Plt.Stepichev` is attacked; `Plt.Voronov` does the same when `Plt.Rhyzov` is attacked) and its "CG State: Zug Falke reaches BEREZOV" area-entry triggers (`Plt.Samsonov` and `Plt.Sytnik` both converge once the player's platoon is detected at Berezov). Both need machinery not yet built: an `OnUnitHitByEnemy`-per-source-group hook (real precedent exists in `Campaign_2\Mission_5`, just not wired up here yet) and an area-entry detector for a non-objective area (currently only `GonkiObjective` has entry detection, via the existing `NavPoint`). These groups still fight back if directly engaged (the `ERT_AGGRESSIVE`/`ActivateBehavior` wiring from the prior pass covers that) - they just won't proactively reinforce toward the player the way the real mission's designer intended, yet.

Verified brace/paren/bracket balance on both edited files after the changes (`MissionTasks.script`: 46/46, 117/117, 31/31; `Mission.script`: 13/13, 72/72, 25/25) and mirrored both to the docs repo. Not yet playtested - that's the user's next step.

## Fifth in-Editor test — real root cause of "nobody moves at all" found: empty router zone

User played again after the movement-order pass above and reported everyone was *still* stationary - both German and Soviet, not just the six groups touched in that pass. That asymmetry (uniform, total stationariness rather than a partial one) pointed away from a scripting bug in the new order code and toward something map-wide.

Found direct evidence in the fresh `editor.log`: a Soviet unit's own ordinary combat-AI repositioning (unrelated to any of this session's new code - standard reactive movement from the earlier `ActivateBehavior` pass) failed with `[CBaseAITask::OnUnreacheable] Unit with ID=Berezov_PltZhilin_2 can not move to _Destination=...` - a genuine router/pathfinding failure, not a script error (no compile/runtime errors were found anywhere in the log for `MissionTasks.script` or `Mission.script`).

Root cause: `Mission.script`'s `RouterWorkingZones` was an **empty array** (`[]`), copied unchanged from `SteppeTemplate`. Checked a known-working real mission (`Campaign_2\Mission_5`) for comparison and found it sets `RouterWorkingZones = [[40000.0, 40000.0, 60000.0, 60000.0]]` - a bounding box telling the router system where it's even allowed to compute paths at all. With an empty zone list, the router has zero coverage anywhere on the map, so *no* `SetOrder_MoveTo`/`SetOrder_MoveToEx` call - old reactive-AI repositioning or this session's new scripted advances alike - can produce actual movement, regardless of which group or target. This fully explains the totally uniform "nobody moves" symptom in a way a per-group scripting bug never could.

**Fix**: populated `RouterWorkingZones` with a single zone `[[0.0, 3000.0, 8000.0, 8000.0]]` covering the whole Berezov battle area - reusing the exact same bounds already established for `CockpitMapAccessBox` earlier in this build, since that box was already confirmed to bound the real mission area correctly.

Verified brace/paren/bracket balance (13/13, 73/73, 26/26) and mirrored to the docs repo. This is the most likely real fix for the movement issue; not yet re-tested by the user.
