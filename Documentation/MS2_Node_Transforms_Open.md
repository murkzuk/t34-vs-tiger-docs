# MS2 importer: node transforms are the missing piece

Found 2026-08-26 by importing ZeeWolf's King Tiger, the first real use the MS2
tooling has had since it was parked in August.

## It works, and better than expected

```
u_veh_KingTiger.ms2   220 nodes, 138 with geometry, 86,476 verts, 72,530 faces
```

The **addon reader** (`blender_addon/ms2_importer/ms2_reader.py`) parses the
whole file. The older standalone `ms2_probe.py` does NOT - it desyncs at the
first geometry node because it assumes `other_count == 1` and this file has
`other=4`. **Use the addon reader; the probe is superseded.**

Hierarchy and names import correctly: `Turret_A` -> `Gun_A` -> `Weapon_A`, nine
road wheels each parented to their `joint_WheelLeftMainN_UP`, and a crew
skeleton (`l_Spine`, `l_Shoulder_Left`, `l_Hand`...) with skin weights on three
objects.

## THE GAP: static parts are world-space, animated parts are local-space

Every imported object lands at `(0,0,0)`. The hull still looks correct; the
turret, gun and road wheels collapse into the origin. The reason is visible in
the stored bounding boxes:

```
Copula          z  2.70 .. 2.98     WORLD space (cupola sits ~2.8 m up)
Top_Hull_K      z  1.86 .. 1.97     WORLD space (hull roof)
Weapon_A        x -2.78 .. 2.78     LOCAL - a 5.5 m barrel centred on its pivot
WheelLeftMain1    +/- 0.40          LOCAL - a wheel around its own axle
```

**Parts that never move are baked in world space. Parts that ANIMATE are
authored around their own pivot**, and their placement lives in a node transform
the reader does not decode.

`Ms2Node` currently carries `name, parent_index, bbox_min/max, positions,
normals, uvs, indices, weights, joint_idx` - **no matrix**.

## Where to look next

The stored bbox is exactly the vertex bounds (delta 0.00 on every part tested),
so it carries no placement information - the transform is elsewhere. The
strongest candidate is the `other_count` records: `other == 4` on geometry nodes
here, where the old probe's documented assumption was `1`. Four extra records on
an animated part is suggestive of a transform payload.

**This is the single thing standing between the importer and a usable model
pipeline.** Without it the tool imports parts; with it, it imports vehicles.

## Why it matters now

The King Tiger is ~90% complete in ZW and needs a unit class plus, if it is to
be playable, a `_PlayableModel`. Being able to open, inspect and eventually
re-export the mesh is what makes that tractable - and it is the first concrete
audience the MS2 work has had. See `TvT_Unshipped_Content.md`.

Working file: `K:\TvT_KingTiger\KingTiger.blend` (Blender 5.2.1).
