# Tree height-only scaling (GetGeometry Y-scale) — PLAN (REDUX first)

Status: **planned** 2026-08-29. Not built yet. Supersedes the parked SetTreeSize
approach (`project_tvt_settreesize_hook_spec.md` has the Phase 0/1 results).

## Goal

Stretch **Birch** (CBirch `TreeSize 4.0`, CSmallBirch `3.0`) and **Linden** on the
**height (Y) axis only** — keep stock width — to fix "correct width but too short",
with **no "redwood" uniform bloat**. **REDUX first**, then ZW.

## Why SetTreeSize is dead

`STTree.dll` calls `SetTreeSize(width=TreeSize, height=0)`; SpeedTreeRT scales
proportionally only, so any height override fattens the whole tree (Phase 1 proved
it). The engine pulls triangles through ONE seam — `CSpeedTreeRT::GetGeometry` —
so that's the hook point.

## Plan

1. **Reverse-engineer `SGeometry`** — disassemble
   `?GetGeometry@CSpeedTreeRT@@QAEXAAUSGeometry@1@KFFF@Z` (prologue `55 8B EC 6A FF`)
   in `SpeedTreeRT.dll` to find the vertex-position array offset + stride inside the
   `SGeometry` struct.
2. **Build `tree_yscale.dll`** — hook `GetGeometry` (loader-notification, same as
   `tree_size_probe`), identify `Birch.spt` / `Linden.spt` by filename, and scale
   each vertex's Y around the tree base by factor **K** for those species only.
3. **Pick K** — A/B test K = 1.5 then 2.0 by eye (birch/linden are currently too
   short; target a natural height, not redwoods).
4. **Test REDUX** — birch/linden taller, width unchanged; check for LOD pop at range
   (geometry-Y doesn't feed `SetTreeSize`'s LOD box), collision/knockdown
   (`TreeRadius`/`FallEnergy` unchanged), and root decal.
5. **Then ZW** — same DLL; first confirm ZW's Birch/Linden `TreeSize` values and
   whether ZW has the same "too short" symptom.

## Risks (from the spec note)

- LOD box is driven by `SetTreeSize`, not the geometry → a taller tree may pop when
  the LOD switches. Verify and note if acceptable.
- Knockdown/collision uses script-side `TreeRadius`/`FallEnergy` → a visually-taller
  tree slightly exceeds its collision box. Minor.
- Root-system decal (`RootSystemSize`) is separate and unaffected.

## Tooling

- `K:\TvTDeepseek\tree_probe\` — `tree_size_probe.{cpp,dll}` (logger, keep),
  `tree_stretch.{cpp,dll}` (superseded, do not ship), `build.bat`, allow-list.
- New: `tree_yscale.{cpp,dll}` in the same folder, build.bat adapted.
