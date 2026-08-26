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

## PROVEN: the geometry decode is CORRECT

Do not chase this as an importer bug. Parts rendered in isolation come out at
true dimensions:

```
Turret_A         3.65 x 2.54 x 1.80 m    a Tiger II Henschel turret
Weapon_A         5.56 m long             the 8.8 cm L/71 barrel
WheelLeftMain1   0.79 m                  Tiger II road wheel is 800 mm
Copula           0.95 m                  cupola ring
Body_commander   0.36 x 0.76 x 0.99      a torso
```

`Turret_A` renders as a textbook Henschel turret - sloped sides, flat rear with
escape hatch and pistol ports, cupola and loader hatch openings. **138 correct
meshes stacked at the origin is what makes the scene look like scrap.**

## Where to look next - and what is NOT yet established

The stored bbox is exactly the vertex bounds (delta 0.00 on every part tested),
so it carries no placement information.

`ms2_reader.py:210` does `offset += other_count * 16` with the comment
*"unidentified"*. `other_count == 4` on these nodes, so 64 bytes.

**A first look at that block does NOT obviously contain a matrix**, and this is
recorded as an open question rather than an answer:

```
Weapon_A    2.6446 / 2.3446 / 2.0446 ...  stepping 0.3 m along the barrel axis
Turret_A    (0, -0.6162, 0) repeating
Copula      (0, -1.1793, 0) repeating
```

Evenly spaced points along a gun barrel and repeating single-axis vec3s look
more like **attachment points** (muzzle flash, smoke, hit positions) than a
transform. The ints at the block start also repeat the node's vertex count,
which means the offset arithmetic used for that dump is not fully understood.

**Next step is to instrument `ms2_reader.py` itself** to report the exact file
offset it reaches after indices, rather than re-deriving it by searching for the
index bytes as was done here. Then dump from a known-correct position.

**This is the single thing standing between the importer and a usable model
pipeline.** Without it the tool imports parts; with it, it imports vehicles.

## Why it matters now

The King Tiger is ~90% complete in ZW and needs a unit class plus, if it is to
be playable, a `_PlayableModel`. Being able to open, inspect and eventually
re-export the mesh is what makes that tractable - and it is the first concrete
audience the MS2 work has had. See `TvT_Unshipped_Content.md`.

Working file: `K:\TvT_KingTiger\KingTiger.blend` (Blender 5.2.1).
