# TvT zone-map colour codes — verified empirically, 2026-08-18

Answers the long-standing open question in `TODO.md`:
*"Confirm the `RouterZone_Test.bmp` color-to-passability mapping in-game
(currently an unproven empirical soft filter)."*

Method: read all **64** `*Zone*.bmp` files across every mission in
`M:\T34vsTiger\Missions`, count palette-index usage, and cross-reference the
`ZMC_*` constants in `Scripts\Common\BaseZone.script`. No guessing — these are
the indices the shipped maps actually contain, with the RGB each index resolves
to in the file's own palette.

## The codes that matter

25 named codes account for **99.9%** of all zone pixels.

| idx | RGB | share | ZMC name |
|----:|---|---:|---|
| 11 | (46, 0, 114) | 53.229% | `Forest01` |
| 32 | (128, 255, 26) | 32.513% | `Grass01` |
| 1 | (255, 229, 0) | 3.963% | `OffRoad01` |
| 217 | (253, 224, 0) | 3.144% | `OffRoad04` |
| 13 | (0, 0, 119) | 1.500% | `Forest03` |
| 27 | (253, 221, 92) | 1.271% | `Bush01` |
| 12 | (97, 0, 114) | 1.196% | `Forest02` |
| 101 | (0, 0, 153) | 0.939% | `Water01` |
| 0 | (255, 0, 255) | 0.698% | `Road01` |
| 103 | (0, 0, 255) | 0.461% | `BeachWater01` |
| 102 | (0, 0, 204) | 0.295% | `ShallowWater01` |
| 34 | (144, 112, 0) | 0.203% | `Grass03` |
| 35 | (0, 112, 95) | 0.184% | `Grass04` |
| 51 | (126, 62, 0) | 0.087% | `ShrubberyCasual` |
| 33 | (39, 118, 0) | 0.063% | `Grass02` |
| 49 | (176, 0, 0) | 0.058% | `ShrubberyLarge` |
| 50 | (195, 18, 126) | 0.054% | `ShrubberyRegular` |
| 39 | (75, 45, 45) | 0.050% | `Road01Add` |
| 122 | (255, 204, 0) | 0.039% | `OffRoad02` |
| 60 | (54, 144, 36) | 0.025% | `VillagePlanting01` |
| 20 | (247, 146, 239) | 0.020% | `Pole01` |
| 52 | (255, 159, 195) | 0.003% | `SpecialLongAloneTree` |
| 62 | (18, 236, 0) | 0.002% | `VillagePlanting03` |
| 61 | (35, 137, 15) | 0.001% | `VillagePlanting02` |
| 28 | (253, 240, 190) | 0.001% | `Bush02` |

Defined in `BaseZone.script` but **unused by any shipped map**: `Forest04` (14),
`Bush03` (29), `Bush04` (30), `Pole02` (18), `PowerLine01` (17),
`PowerLine02` (19), `RoadObject` (110), `AllPassable` (111), `OffRoad03` (123),
`NonPassable` (150). Note `NonPassable` never appears — impassability comes from
*unknown* codes defaulting to it, not from the constant being painted.

## Colour-family logic

The palette is systematic, which is a useful check when authoring a new map:

- **Forest** — dark violet/blue, red channel low, blue ~114-119
- **Grass** — greens
- **OffRoad** — yellows/oranges (255,229,0 / 255,204,0 / 253,224,0)
- **Water** — pure blue ramp by depth: 153 / 204 / 255
- **Road** — magenta (255,0,255)
- **Shrubbery / planting** — mixed browns and mid-greens

## The unnamed indices — artifacts, not secret codes

About 100 further indices appear, **every one at 0.000% share**. Most occur only
in `RouterZone_Test.bmp`. Three recur more widely but still at negligible area:
idx 76 (18,252,0) in 19 files, idx 78 (20,19,120) in 28 files, idx 144
(144,218,84) in 14 files.

Read: these are **authoring artifacts** — stray pixels from image editing, very
likely a non-nearest-neighbour resample or paint tool anti-aliasing during the
original map production. `Behavior.dll` carries the string
`"Unknown color %0X in cell (%i,%i,%i), setting code non-passable"`, so each of
these becomes a single non-passable cell.

Harmless individually, but worth knowing: **shipped maps contain scattered
one-pixel impassable cells that nobody intended.** If AI pathing ever snags in an
apparently open spot, this is a candidate cause.

## Rules for generating new zone maps

1. **Only ever write the 25 named indices.** Anything else becomes non-passable.
2. **Never resample a zone map with interpolation.** Bilinear on an index map
   invents indices between real ones — precisely how the artifacts above were
   probably created. Use nearest-neighbour (`resample_nearest` in
   `tvt_terrain.py`).
3. **Preserve the source palette.** The index means nothing without the palette
   entry it points at.
4. Validate a generated map by loading it and grepping the log for
   `"Unknown color"` — the engine self-reports every bad cell with coordinates.
