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

## Historical framing — open decision

Checked REDUX's 20-unit roster against the real July 1943 Battle of Kursk order of battle:

- **T-34/85 is anachronistic** — didn't enter service until 1944.
- **SU-85 is anachronistic** — entered service autumn 1943, just after Kursk.
- REDUX has **no Panther** (famously debuted at Kursk) and no KV-1/SU-152 — building a Panther would mean an entirely new 3D model, not scriptable (ZW does have a Panther, 3 variants, but importing it raises the same IP question as the terrain — hold off unless explicitly decided otherwise).

Two ways to handle this, not yet decided:
- (a) Call it Kursk anyway, accept the anachronisms (a "what if" or "later stage of the battle" framing).
- (b) Frame it as a **Ukraine steppe battle, late 1943 into 1944** rather than the specific named battle — same terrain, same core T-34-vs-Tiger matchup, but every current REDUX unit becomes period-correct with zero new unit development needed. Leaning toward this, but not settled.

## Terrain source recommendation

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

Campaign_2 Mission_5 — confirmed running at 60 FPS after today's AI-targeting and MG-mask fixes — carries roughly: 7 Tiger, 8 T-34/85, 6 T-34/76, 4 SU-85, 2 StuG 40, 2 Hanomag halftracks, 5 Opel Blitz trucks, 2 IL-2, 9 Soviet riflemen (~45 units total, ~29 of them combat vehicles). Treat this as the known-safe baseline; a bigger, more open map might tolerate more (less scene/forest rendering overhead per the whole point of going open steppe) but that's untested — don't assume a large unit count is free just because the map is bigger.

## Mission-logic design choice — open decision

Not yet decided: a lightly-scripted, randomizable skirmish (safe, low-risk, similar in spirit to the Quick Mission Generator's approach — see `Mission_File_Schema_Verified_2026-07-02.md`) vs. a fully hand-scripted historical battle with real objectives/waves (bigger undertaking, closer to how the real campaign missions are built, more failure-prone given how trigger-coupled those tend to be).

## Recommended path (not yet started)

1. Settle the two open decisions above (historical framing, mission-logic style).
2. In the Level Editor, look at Campaign_2 Mission_6's terrain visually to confirm it's a good steppe candidate before committing.
3. Build a new mission using `Mission1`'s proven-safe, trigger-light `Content.script` structure as the mission-logic base (same precedent as the Quick Mission Generator work), but with Mission_6's terrain files stretched to a larger `MatrixWidth`/`MatrixHeight` via the confirmed technique above.
4. Paint/adapt the `TerrainZone` bitmap for minimal forest coverage, keep `RegisterForestRegion` wired but sparse.
5. Populate with a roster-accurate unit set, starting near or under the ~45-unit/~29-vehicle performance baseline.
6. Test in-Editor before anything else — this is genuinely new territory (nothing this large has been proven to work in REDUX itself yet, only in the separate ZW install).

Nothing has been built yet — this is scoping only, per explicit instruction.
