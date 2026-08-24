# Trees don't cast shadows onto tanks — engine limitation (2026-08-24)

## Observation

Trees/vegetation cast visible shadows onto the **terrain**, but a tank parked
under a tree stays fully lit — the tree's shadow stops at the ground and never
falls on the hull/turret.

## Root cause — two separate shadow systems

The G5 engine does **not** use one shadow pass for everything.

1. **Stencil shadows (object → object).** These are the only shadows that can
   fall *onto another object* (a tank). They are cast only by objects flagged in
   `StencilShadowSettings`:

   - `Scripts\Common\Settings.script` L64:

   ```
   StencilShadowSettings = [
       [ [], [CLASSIFICATOR_SHADOW] ],
       [ [], ["INVENTORY_ITEM"]  ],
       [ [], ["INVENTORY_ITEM"]  ],
       [ [], ["INVENTORY_ITEM"]  ],
       [ [], ["INVENTORY_ITEM"]  ]
   ];
   ```

   That list is tanks, guns, buildings (and inventory items). **Trees are not in
   it.**

2. **Vegetation/terrain shadows (tree → ground).** Trees are classified as
   terrain (`CLASSIFICATOR_TERRAINFOREST`, seen in `Scripts\Common\BaseFence.script`
   L358 / L584), and their shadows are drawn **only onto the terrain** by a
   separate vegetation shadow pass:

   - `Scripts\Common\BaseAtmosphere.script` L58–60:
     - `TreeLightKoef` — tree lighting smooth koef
     - `TreeShadowLodDistance` — default `500` (how far tree→ground shadows draw)

So a tree shadow is terrain-only by design. It has no way to project onto a
dynamic mesh.

## Trees are SpeedTreeRT (confirmed 2026-08-24)

Local files prove the vegetation is **IDV SpeedTree (first version,
SpeedTreeRT)**:

- `SpeedTreeRT.dll` + `STTree.dll` sit in the game root.
- `Models\Trees\*.spt` — SpeedTree compiled trees: AppleTree, Birch,
  BulfordHolly, FirScotch, Fir_short, Fir_tall, Fir_tall_bend, Linden, LiveOak
  (6–15 KB each = procedural tree *definitions*; the geometry is generated at
  runtime, not baked in).
- `Textures\Trees\` shows the classic SpeedTree texture set, per species:
  - `*Bark.tex` → **3D trunk / branch geometry**
  - `*Frond*.tex` / `*Leaves_*.tex` / `*Needles_*.tex` → **billboard leaves / fronds**
  - `*_Billboard.tex` → **full-tree billboard impostor** (the distant LOD)

So "mesh or billboard" is **both**: a 3D trunk + billboard leaves, plus a full
billboard impostor at distance. There *is* real 3D geometry (trunk/branches) to
cast a shadow from — but SpeedTreeRT v1 renders its **own projected ground
shadow** (terrain-only, gated by `TreeShadowLodDistance`), separate from the
engine's stencil pass. That separation is why tree shadows never reach tanks.

**Procedural trees = per-client layout (multiplayer desync).** Because the
geometry is generated at runtime, every client generated its **own** tree
positions. In multiplayer that meant one player drove through a forest avoiding
the trees *they* saw, while another player — whose client had placed those trees
differently — heard and saw trees falling where the first saw none. The tree
layout was never synchronised between clients; shipping it that way was widely
ridiculed.

## Conclusion

- **Not script-fixable.** The shadow pass lives in the compiled renderer (`.fxo`
  shaders / exe), not in any `.script`.
- **Injection is the path.** We already hook the D3D9 device vtable
  (`K:\TvTDeepseek\fog_probe\`), so the renderer *is* reachable — tree→tank
  shadows are therefore not off the table. But it is a **different order of
  problem** than the fog probe: fog_probe only *observes* state, whereas this
  means *modifying* the render pipeline (a new shadow pass, or a shader patch),
  not flipping a render state.
- **The only script lever** is `TreeShadowLodDistance`, which controls how far
  tree→**ground** shadows draw — it has no effect on tree→tank.

## Injection path — feasibility (updated 2026-08-24)

1. **Are trees meshes or billboards? — ANSWERED: both.** 3D trunk/branches +
   billboard leaves, full billboard impostor at distance (see SpeedTree section).
2. **Why are trees excluded from the stencil pass?** They render through
   SpeedTreeRT (its own middleware, `STTree.dll`), not through the engine's
   object/stencil pipeline — so they never enter `StencilShadowSettings`.
3. **How are tree→ground shadows made?** SpeedTreeRT's own projected ground
   shadow (terrain-only, gated by `TreeShadowLodDistance`).
4. **What a fix requires:** reach *SpeedTreeRT's* renderer (hook `STTree.dll` /
   `SpeedTreeRT.dll`, not just the D3D9 device), then either redirect its shadow
   onto object geometry or inject a shadow-map pass that tank shaders sample.
   This is a middleware-level job, larger than the fog probe.

The existing `fog_probe` still flags the engine's shadow pass
(`D3DRS_COLORWRITEENABLE == 0`) and keeps per-shader shadow-draw counts, so it
is the right starting point to extend — but the tree side needs new hooks into
the SpeedTree DLLs.

## Related: `TreeShadowLodDistance` (tree→ground shadow distance)

- `BaseAtmosphere` default is `500`, but **campaign / quick missions deliberately
  override it to 20 / 25 / 35** — so `25` is the normal value, not an anomaly.
  Missions that omit the key (most `MyMission/*` quick missions, and
  C1M5 / C1M6 / C2M5) fall back to the 500 default.
- It controls how far tree→**ground** shadows draw. Raising it (e.g. to 500)
  makes tree shadows visible much further out — a visual win, at a performance
  cost. It does **not** affect tree→tank shadows (the limitation above).

## Editing rules (reminder)

- `.script` = CP1251; byte-level edits only; verify EF BF BD count stays 0.
- Delete `Cache\Scripts.cache` after any script edit (cold rebuild ~2 min).
- Backups stay in `K:\TvTDeepseek\rollback\`, never inside the game folders.
