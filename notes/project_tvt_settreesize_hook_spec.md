# Tree height-only scaling — spec + Phase 0/1 results (scale geometry Y)

## Goal

Stretch specific trees (silver birch, small birch, linden) on the **height** axis
only, keeping the stock width, to fix "correct base dimensions but too short" —
without the uniform-scale "redwood" bloat.

## Why this is hard: SpeedTreeRT scales proportionally only

`BaseSTTree.script` exposes **one** `TreeSize` per species, passed to SpeedTreeRT
as width (`height = 0`). SpeedTreeRT has **no anisotropic (per-axis) scaling** —
trees are always scaled proportionally from a fixed `.spt` aspect ratio. So
raising `TreeSize` grows the tree fatter *and* taller together (the "redwood").

## Target

- **DLL:** `SpeedTreeRT.dll`
- **Function of interest:** `CSpeedTreeRT::GetGeometry(SGeometry&, …)` — the single
  function through which the engine pulls tree triangles (confirmed in `STTree.dll`'s
  import table):
  ```
  ?GetGeometry@CSpeedTreeRT@@QAEXAAUSGeometry@1@KFFF@Z
  ```
- **Prologue pattern:** SpeedTreeRT exports open with `55 8B EC 6A FF` (a clean
  5-byte boundary), so the 5-byte JMP trampoline is safe.

## Phase 0 result (read-only probe, confirmed)

`STTree.dll` calls **`SetTreeSize(width = TreeSize, height = 0.0)`** — every
call, every species. `0.0` = "don't set height" (height comes from the `.spt`).

```
LoadTree this=… file=Models/Trees/Birch.spt
SetTreeSize this=… w=4.000 h=0.000 Models/Trees/Birch.spt
```

## Phase 1 result (tree_stretch.dll, tested — SUPERSEDED)

Tried overriding `height` (`h=0 → width×K`) in the `SetTreeSize` hook. The hook
fired correctly (`STRETCH Birch.spt w=4 h=0 -> h=8`) but the **whole tree scaled
up, not just the height**. Conclusion:

> `SetTreeSize(width, height)` is **uniform-only** — it scales proportionally,
> using height as the master dimension. It cannot stretch one axis independently.

So the "pass a height" approach is dead. `tree_stretch.dll` (K=2.0) is **not a
usable fix** — do not ship it. Keep `tree_size_probe.dll` (Phase 0) as the logger.

## The new path: scale geometry Y

The engine pulls tree triangles through **one** function, `GetGeometry`. The plan
is to hook it and scale the returned vertices' **Y** (around the tree's base) for
the target species — a true height-only stretch.

**Open work (next):** reverse-engineer the `SGeometry` struct layout (disassemble
`GetGeometry`) to locate the vertex-position array and its stride, then scale Y.

## Tree identification (resolved)

`LoadTree` → instance map works; several classes share one `.spt`, so width is
the real species discriminator:

| `.spt` | widths → class |
|---|---|
| Birch.spt | 4.0 = CBirch, 3.0 = CSmallBirch |
| FirScotch.spt | 25.0 = CFirScotch, 20.0 = CFirScotchSmall |
| BulfordHolly.spt | 3.0 = bush, 5.0 = large bush |
| AppleTree.spt | 7.5 = CAppleTree, 6.2 = CSmallAppleTree |

Identify by **filename** (`Birch.spt` / `Linden.spt`).

## Injection timing (resolved)

`SpeedTreeRT.dll` is **runtime-loaded** (the EXE / Engine.dll / Objects.dll do
not import it; `STTree.dll` statically imports it). The loader-notification
approach (`fog_probe`'s) works — patched on load, confirmed live.

## Execution-log findings (2026-08-24)

The hook runs **clean** — no new error lines in `M:\T34vsTiger\execution.log`
(the only "error" lines are four pre-existing stock script warnings).

- `[STTreeReadonlyMesh] Create Models/Trees/*.spt tree` — the engine's tree
  class is **native** (not in any `.script`) and named "read-only": it renders
  SpeedTreeRT's geometry, never edits it. Confirms the seam is the `GetGeometry`
  call out of that class.
- `[STForest] 45329 trees generated` — a mission spawns ~45,000 trees, which is
  why raising `ModelLOD` cost so much framerate.

## Risks / side effects

- **LOD coupling:** scaling geometry Y does NOT feed SpeedTreeRT's LOD (LOD uses
  `SetTreeSize`'s bounding box), so LOD is unaffected — a tree taller than its LOD
  box may pop at range; verify.
- **Collision/knockdown** uses `CTreeDescriptor`'s `TreeRadius` / `FallEnergy`
  (script side), NOT the geometry — a visually-taller tree may exceed its
  collision box slightly. Minor.
- **Root-system decal** (`RootSystemSize`) is separate and unaffected.

## Tooling

- Phase 0 (logger): `K:\TvTDeepseek\tree_probe\tree_size_probe.{cpp,dll}`
- Phase 1 (superseded): `K:\TvTDeepseek\tree_probe\tree_stretch.{cpp,dll}`
- Allow-list: `K:\TvTDeepseek\tree_probe\tvt_los_allow.txt` (beside the DLL)

## Relationship to other notes

Same injection machinery and DLL as `project_tvt_speedtree_harvest.md`. The
`GetGeometry` hook is also the natural seam for the "harvest" plan (that note
already identifies `GetGeometry` as the geometry hand-off point).
