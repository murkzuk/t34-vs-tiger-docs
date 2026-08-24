# Tree LOD tuning — findings & current state (2026-08-24)

## The two-layer tree LOD

Tree detail is governed by TWO independent knobs, in two files:

1. **`ModelLOD`** — `Scripts\Common\BaseSTTree.script`, class `CBaseTree`. The
   far switch distances (full 3D → billboard imposter at range).
   - Original dev value is commented out: `[160, 280, 480, 720]`.
   - REDUX ("jm") had reduced it to `[40, 70, 180, 250]` — the "full detail only
     close up" look.
2. **`TreeSize`** — same file, per species. SpeedTreeRT computes its INTERNAL
   leaf/branch LOD from tree height vs camera distance, so an undersized tree
   LODs at absurdly close range.

## What we tried (all states backed up in `K:\TvTDeepseek\rollback\`)

| State | `ModelLOD` | `TreeSize` (deciduous) | Result |
|---|---|---|---|
| REDUX stock | `[40,70,180,250]` | Birch 4 / SmallBirch 3 / Linden 8 | 72 FPS, LOD popped ~5–10 m |
| B (aggressive) | `[240,400,700,1000]` | stock | looked great, low 30s FPS |
| dev original | `[160,280,480,720]` | stock | FPS ok, but close-up LOD still popped |
| +bigger sizes | `[160,280,480,720]` | Birch 15 / SmallBirch 10 / Linden 20 | birch = "redwoods" (too big) |
| +half sizes | `[160,280,480,720]` | Birch 9.5 / SmallBirch 6.5 / Linden 14 | FPS diving |
| **current** | `[160,280,480,720]` | **stock** (4/3/8) | FPS recovered |

## Key findings

1. **`TreeSize` is coupled** — it scales the DRAWN size AND the LOD distance
   together. You cannot push LOD out without also enlarging the tree. This is a
   fundamental SpeedTree v1 limitation, not a scriptable bug.
2. **`ModelDistance` in `BaseForest.script` is a red herring** for LOD — changing
   it (15→60) had zero visible effect. It's on the forest-placement side.
3. **`TreeShadowLodDistance` is expensive.** Raising C1M3's from 25→500 (20×)
   contributed to the FPS dive; reverted to stock 25.
4. **Raising `ModelLOD` costs real frames.** `[240,400,700,1000]` cost ~2× the
   frame budget (72 → low 30s). `[160,280,480,720]` (dev original) is the sweet
   spot that fixed the far billboard pop while keeping FPS.

## Current state (live, REDUX `M:\T34vsTiger`)

- `ModelLOD` = `[160, 280, 480, 720]` (dev original, kept)
- `TreeSize` = stock (Birch 4 / SmallBirch 3 / Linden 8; firs 20–28)
- `TreeShadowLodDistance` = stock (C1M3 = 25)
- `ModelDistance` = 15 (stock)

## The real fix (future)

This whole episode is the "poor SpeedTree" the user called out: SpeedTree v1
couples tree size to LOD, and its full-geometry path is expensive. The clean
solutions are already documented:

- `project_tvt_speedtree_harvest.md` — reuse SpeedTree geometry for real shadows.
- `project_tvt_tree_shadow_limitation.md` — why tree shadows are terrain-only.
- Scrap/replace SpeedTree → bake trees to `.ms2` (see the harvest note).
