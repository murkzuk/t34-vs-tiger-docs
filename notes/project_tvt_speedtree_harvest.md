# SpeedTree "harvest" plan — capture tree geometry for real shadows (2026-08-24)

## Key finding: SpeedTreeRT v1 is a geometry factory, not a renderer

Dumping the shipped DLL exports (`dumpbin /exports`):

- `STTree.dll` — only **2 exports**: `GrGetInstance`, `GrForceLibrariesRelease`.
  It is the engine's thin handle into the middleware.
- `SpeedTreeRT.dll` — the full `CSpeedTreeRT` API: `LoadTree(.spt)`, `Compute()`,
  `GetBranchGeometry` / `GetFrondGeometry` / `GetLeafGeometry` /
  `Get*BillboardGeometry`, `Get*TriangleCount`, LOD (`SetLodLevel`,
  `ComputeLodLevel`), wind (`ComputeWindEffects`, `SetWindStrength`), collision
  (`GetCollisionObject*`), and shadow projection (`ParseShadowProjectionInfo`).

Crucially there is **no `Render` / `Draw` method**. SpeedTreeRT hands the game
triangle geometry; the game (via `STTree.dll`) performs the D3D9 drawing. So the
full 3D tree geometry is computed by SpeedTreeRT and drawn through the engine's
own draw calls — it is simply **discarded for shadowing** (trees use
`ParseShadowProjectionInfo` = a terrain-only blob instead).

## Three paths evaluated

1. **Scrap SpeedTree → bake `.ms2`.** Generate trees with an open-source tool
   (ngPlant / Arbaro / TreeGen / Blender Sapling), bake to the engine's native
   `.ms2`, replace procedural scatter with deterministic placement. Fixes
   shadows + desync + modernises art, but is multi-week: reverse-engineer
   `.ms2`, re-author LODs, wind, knock-down. Big.
2. **Upgrade SpeedTree.** Trap. Still proprietary (fails "open source if
   possible"); not drop-in (API / mangled names changed; `.spt` v1 won't load);
   the game is a 32-bit process vs modern 64-bit SDKs. Worst of both worlds.
3. **Harvest (chosen).** Hook `STTree.dll`'s render path, capture the tree
   geometry it already receives, and submit it to the engine's stencil-shadow
   pass. Keeps SpeedTree (wind / LOD / billboards / knock-down all intact),
   fixes tree→tank shadows, open-source by construction. Smallest path by far.

## Recommendation & next step

Harvest. First concrete step: a **read-only probe into `STTree.dll`** to confirm
how it pulls geometry from `SpeedTreeRT` and where its render loop sits, so we
know exactly where to hook the shadow submission.

## Scope note

Harvest fixes **tree→tank shadows** only. It does not fix multiplayer desync
(per-client procedural tree positions) or modernise the tree art — neither is a
driver for single-player play.
