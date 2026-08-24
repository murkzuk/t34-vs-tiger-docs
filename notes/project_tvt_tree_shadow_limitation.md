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

## Conclusion

- **Not script-fixable.** The shadow pass lives in the compiled renderer (`.fxo`
  shaders / exe), not in any `.script`. Making tree shadows fall on tanks would
  require reverse-engineering the render pipeline.
- **The only script lever** is `TreeShadowLodDistance`, which controls how far
  tree→**ground** shadows draw — it has no effect on tree→tank.

## Related (separate) observation

C1M3 sets `TreeShadowLodDistance = 25` (vs the default 500), so on that map tree
shadows only draw within 25 m. That's a distance/quality knob, unrelated to the
tree→tank limitation above.

## Editing rules (reminder)

- `.script` = CP1251; byte-level edits only; verify EF BF BD count stays 0.
- Delete `Cache\Scripts.cache` after any script edit (cold rebuild ~2 min).
- Backups stay in `K:\TvTDeepseek\rollback\`, never inside the game folders.
