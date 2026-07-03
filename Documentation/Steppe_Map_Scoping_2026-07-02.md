# Large Open Steppe Mission — Scoping Notes (2026-07-02)

Scoping pass for a new mission concept: a large, mostly-open steppe map with few trees, deliberately sidestepping the confirmed-unfixable "AI sees through trees" gap (see `TODO.md`) rather than trying to solve it. This document is the full picture gathered today, meant to pick up work tomorrow without re-deriving any of it.

## Origin

User proposed a steppe map (few trees) as a way around the tree-LOS AI limitation, with the requirement that it stay historically grounded. Investigation of a separate, older paid mod install (`M:\T34vsTiger_ZW2015`, "ZeeWolf mod" / ZW — kept strictly distinct from the REDUX0.001 codebase throughout) turned up real prior art: ZW shipped 4 "Kursk" custom missions at much larger map sizes than anything in REDUX, which turned out to reveal a reusable technique rather than requiring genuinely new large-scale terrain content.

## Confirmed: large maps are cheap, not expensive

- Engine binaries are **byte-identical** between REDUX and ZW (`Engine.dll`, same size/date) — large-scale maps aren't a ZW-specific engine variant, REDUX can do the same thing.
- Every mission in both REDUX and ZW uses the same **standard terrain image resolution**: heightmap 2049×2049, terrain-zone 1024×1024 (or 2048, mission-dependent), router-zone 2048×2048, regardless of the mission's physical size.
- ZW's `KurskMission2`/`3`/`4` prove the actual technique: declare a much bigger `MatrixWidth`/`MatrixHeight` (36000 or 18000 vs REDUX's typical 9000) in `WorldMatricies.script`, while leaving the terrain image resolution at the standard size — the engine just stretches the same pixel data over a larger physical area. This is **directly evidenced in their code**, not inferred: `ImageWidth = 2049; // 4097;` — the bigger value was tried and abandoned in favor of stretching the standard one, for every terrain layer (heightmap, terrain-zone, router-zone, micro-texture), confirmed via the same commented-out-larger-value pattern in all of them.
- Hash-checked Kursk's heightmap content against every other ZW mission heightmap — no match outside its own Kursk siblings, so the terrain *shapes* were custom-drawn (at standard resolution), not literally copied from an existing mission. The *technique* (stretch a standard-resolution image over a bigger matrix) is what's reused, not specific artwork.
- **REDUX's own `Mission1` already uses this exact standard resolution family** (2049 heightmap, 1024 terrain-zone, 2048 router-zone) at `MatrixWidth = 9000`. We can apply the same stretch technique directly to REDUX's own existing terrain files — no need to touch or reference ZW content at all, fully sidesteps any IP concern.
- Net effect: making the map physically bigger just means the same elevation detail gets spread over more ground (broader, gentler hills) — that's not a compromise, it's exactly the flat/open steppe look being aimed for.

## Confirmed: tree/forest density is a paint job, not object placement

- Trees are **not** individually placed objects in `Content.script` (searched both REDUX and ZW Content.scripts for tree/forest class names — zero matches).
- Forest is registered per terrain-zone code in `Terrain.script`'s `CreateForesRegions()`: `RegisterForestRegion([ZMC_Forest01], Materials, "forest_XXX.tex", [LOD layers], [distances])`. The engine procedurally scatters tree instances (via a texture atlas) across whatever area of the map is painted with that zone code in the `TerrainZone` bitmap.
- Consequence: controlling tree density for the steppe look is a matter of (a) how much of the `TerrainZone` bitmap gets painted with the forest zone-code, and (b) the density/distance parameters passed to `RegisterForestRegion`/`RegisterVerticalForest` — not hand-placing thousands of tree objects. Very tractable.
- ZW's Kursk missions still register `ZMC_Forest01` with their own `forest_Kursk.tex` skin, so the "sparse steppe" look there also comes from how little of their zone bitmap was painted, not from omitting the forest system entirely.

## Historical framing — DECIDED 2026-07-02

Checked REDUX's 20-unit roster against the real July 1943 Battle of Kursk order of battle:

- **T-34/85 is anachronistic** — didn't enter service until 1944.
- **SU-85 is anachronistic** — entered service autumn 1943, just after Kursk.
- REDUX has **no Panther** (famously debuted at Kursk) and no KV-1/SU-152 — building a Panther would mean an entirely new 3D model, not scriptable (ZW does have a Panther, 3 variants, but importing it raises the same IP question as the terrain — hold off unless explicitly decided otherwise).

**Decided: option (b)** — framed as a **Ukraine steppe battle, late 1943 into 1944**, not the specific named Battle of Kursk. Every current REDUX unit (including T-34/85 and SU-85) is period-correct under this framing, no new unit development needed, no anachronisms to explain away.

## Build progress (2026-07-03)

**First template built**: `Missions\MyMission\SteppeTemplate\` — copied from `Mission1` (not from `Campaign_2\Mission_6`; see below for why), all class names/paths renamed (`Mission1` → `SteppeTemplate` throughout `Content.script`/`Mission.script`/`WorldMatricies.script`/`Terrain.script`/`Atmosphere.script`/`MissionTestStrings.script`; `MissionTasks.script` copied verbatim, it's empty boilerplate). Registered in `Scripts\Editor\MenuConfig.script` as "Steppe Template (18000x18000)" so it's selectable in the Level Editor. All balance-checked identical to the source file, cache cleared, synced to the docs repo mirror.

**Terrain source decision reversed mid-build**: `Campaign_2\Mission_6` (the statistically-flattest candidate identified earlier) turned out to be a dead end on closer visual inspection — rendered its heightmap as a hillshade image and it showed no large-scale terrain features at all, even after heavy smoothing, unlike `Mission1`'s heightmap which clearly shows a real river valley and rolling hills under the same rendering. Went with **`Mission1`'s own terrain instead, kept exactly as-is** — known good, hand-authored, and it gets flattened "for free" by the stretch itself: keeping the same height values but mapping them over a 2x bigger `MatrixWidth` (9000→18000) halves the effective slope everywhere, confirmed with an actual elevation cross-section plot (same wiggle amplitude, spread over 2x the horizontal distance = 2x gentler rise-over-run). No separate value-scaling step needed.

**Forest density was NOT free** — this took a real content-editing step, not just the stretch. Checked `Mission1`'s own `TerrainZone_Test.bmp` zone-code coverage: **55.7% forest-coded, 4.05% bush-coded** (it's a tutorial map with real scenic tree cover) — stretching that as-is would've made the forest *bigger*, not sparser, since zone coverage is a fixed percentage of the bitmap regardless of physical scale. Thinned it via 32-pixel block-clustered random removal (not per-pixel noise, which would look unnatural) down to **8.84% forest / 0.67% bush** — scattered copses across mostly open ground, confirmed visually. `Mission1`'s original `TerrainZone_Test.bmp` was untouched; only the `SteppeTemplate` copy was modified.

**Chose 18000x18000 for this first build** (2x REDUX's normal 9000, half of ZW's largest Kursk variant at 36000) — a deliberately moderate first step to validate the whole pipeline before going bigger. `CockpitMapAccessBox`/`MinRange`/`MaxRange`/`MarksInitPoint` in `Mission.script` were scaled 2x to match, though these are an untested assumption — may need tuning once seen in-Editor.

**Not yet done**: actually opening this in the Level Editor to confirm it loads and looks right (this is the next real checkpoint — nothing this large has been proven to work in REDUX itself yet). Extending `generate_mission.py`/`roster.json` to target this template instead of/alongside `Mission1` hasn't been started.

## Terrain source recommendation (superseded — kept for the record)

**This recommendation was overturned during the build — see "Build progress" above.** Elevation range/std (a numeric proxy checked before any visual inspection) turned out to be misleading: low std didn't mean "gently rolling," it meant "no real terrain shape at all" once actually rendered. `Mission1`'s own terrain was used instead. Leaving the original numeric comparison below since it's still a real, if incomplete, data point.

Sampled elevation range/std across every REDUX campaign mission's heightmap (all share the same `FloatValueFactor`, so directly comparable in real meters):

| Mission | Elevation range | Std dev |
|---|---|---|
| Campaign_1 Mission_1/2 | ~2342 | ~444 |
| Campaign_1 Mission_3/4 | ~3319 | ~570 |
| Campaign_1 Mission_5/6 | ~3446 | ~700 |
| Campaign_2 Mission_1/2/5 | ~3319 | ~571 |
| Campaign_2 Mission_3 | 3586 | 710 |
| Campaign_2 Mission_4 | 3248 | 526 |
| **Campaign_2 Mission_6** | **1274** | **176.7** |
| MyMission Mission1 | 3276 | 530 |

**Campaign_2 Mission_6 is the flattest by a wide margin** — best raw-material candidate for a stretched-open-steppe map. Its terrain files (`hmap.raw`/`hwater.raw`/zone bitmaps) haven't been inspected visually yet, only statistically — worth a look in the Editor before committing.

## Performance budget reference

Campaign_2 Mission_5 — confirmed running at 60 FPS after today's AI-targeting and MG-mask fixes — carries roughly: 7 Tiger, 8 T-34/85, 6 T-34/76, 4 SU-85, 2 StuG 40, 2 Hanomag halftracks, 5 Opel Blitz trucks, 2 IL-2, 9 Soviet riflemen (~45 units total, ~29 of them combat vehicles).

**Confirmed as the working budget**: treat ~45 units / ~29 combat vehicles as the known-safe starting point for the new mission. A bigger, more open map might tolerate more (less scene/forest rendering overhead per the whole point of going open steppe) but that's untested — a bigger map doesn't automatically mean unlimited unit count is free. Start at or under this baseline and only scale up once proven in-game.

## Mission-logic design choice — DECIDED 2026-07-03

**Decided: reuse and extend the Quick Mission Generator itself**, rather than hand-scripting a bespoke historical battle. Concretely:

- Build a second template mission (working name TBD, e.g. `SteppeTemplate`) alongside the existing `Mission1` — bigger `MatrixWidth`/`MatrixHeight`, terrain stretched per the technique confirmed above, sparse forest zone. `Mission1` stays untouched as the small/safe default.
- `generate_mission.py` gets pointed at whichever template is wanted (either a `--template` flag or a sibling script) — the randomize/jitter/validate logic underneath doesn't need to change, just the safe-zone bounds it jitters within.
- `roster.json` needs little to no change — the "late 1943–44 Ukraine steppe" framing already made every current REDUX unit period-correct, so it's the same roster spread over more ground, not a new one.
- This directly resolves the Quick Mission Generator's own existing backlog item ("consider a second/bigger template mission for more spawn variety") at the same time — one build, two backlog items closed.

## Recommended path

All three design decisions are locked in (historical framing, performance budget, mission-logic style — all above). Build order, with progress:

1. ~~Confirm Campaign_2 Mission_6's terrain~~ — done, rejected (see "Build progress" above). Used `Mission1`'s own terrain instead.
2. **Done**: built `Missions\MyMission\SteppeTemplate\` — stretched to 18000x18000, forest thinned from 55.7%/4.05% (forest/bush) down to 8.84%/0.67%, `Mission1`-style minimal-trigger `Content.script`, registered in `MenuConfig.script`.
3. **Not started**: extend `generate_mission.py`/`roster.json` to target the new template alongside the existing `Mission1` path.
4. **Not started**: populate/test with a roster-accurate unit set, starting at or under the ~45-unit/~29-vehicle performance baseline.
5. **Next concrete step**: open `SteppeTemplate` in the Level Editor and confirm it actually loads and looks right — this is genuinely new territory (nothing this large has been proven to work in REDUX itself yet, only in the separate ZW install). Watch in particular whether `CockpitMapAccessBox` (scaled 2x, untested assumption) actually covers the right area.

Picks up here next session.
