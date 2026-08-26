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

## SOLVED 2026-08-26 - the transform is frame 0 of the animation track

`ms2_reader.py` was **skipping** it:

```python
d_count = struct.unpack_from('<i', data, offset)[0]
offset += 4
offset += d_count * 12 + d_count * 16        # <- the node transform, skipped
```

Every node carries a fixed-length animation track:

```
d_count x 12 bytes    position keyframes (vec3)
d_count x 16 bytes    rotation keyframes (quaternion, W FIRST)
d_count == 161        in every vehicle seen. 161*28+4 = 4512 bytes, which is
                      exactly the "fallback block" size earlier notes recorded
                      without ever identifying it.
```

**Frame 0 is the rest pose** - measured, not assumed: 199 of the King Tiger's
220 nodes sit at identity rotation on frame 0, more than any other frame.

The tracks read exactly as a tank should:

```
WheelLeftMain1   position FIXED, quaternion SPINS   1.0 -> 0.977 -> 0.909
WheelLeftMain2   position (0.0059, -0.0263, -0.5175)  - a different wheel station
Weapon_A         position SLIDES 2.6446 -> 2.3446 -> 2.0446, quat fixed  = 0.3 m RECOIL
Turret_A         position FIXED, quaternion 0.7071 = 90 degrees of TRAVERSE
```

### Verified on four vehicles from both builds

```
                imported     real vehicle
King Tiger      10.21 m      10.29 m     
Tiger I          8.34 m       8.45 m     
Panther D        9.31 m       8.66 m      (stowage and tow cables in the bounds)
T-34/85          7.32 m       height 2.45 -> 2.71 as the turret seated
```

### The fix

`ms2_reader.py` now decodes `rest_pos` / `rest_quat` / `has_rest` on `Ms2Node`.
`__init__.py` applies them after parenting, with
`matrix_parent_inverse = Matrix.Identity(4)` so each node's local transform
composes down the chain.

### TWO TRAPS that cost time here, both about the instrument not the code

**1. Blender loads an INSTALLED copy of the addon, not the repo one.**

```
repo      C:\Users\Jeff\t34-vs-tiger-docs\Tools\MS2Format\blender_addon\ms2_importer\
INSTALLED C:\Users\Jeff\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\ms2_importer\
```

Editing the repo copy changes nothing until it is copied across and
`__pycache__` deleted. The installed copy was 8 days stale.

**2. `matrix_world` is stale until the depsgraph updates.** Measuring bounds
straight after `import_ms2` reported the OLD unassembled size and made a working
fix look like a failed one. Call `bpy.context.view_layer.update()` first.

### And a wrong turn recorded so it is not repeated

The `other_count` records were named as the "strongest candidate" for the
transform. **They are not.** `other_count` is 1, not 4 - the 4 came from the old
`ms2_probe.py`, which desyncs on real vehicles - and those 16 bytes are a
vertex-count echo. The earlier dump that looked like attachment points was
landing inside the animation block by accident.


---

# SOLVED 2026-08-26: material assignment

The 16-byte record the reader skipped as `other_count * 16` is:

```
(packed, 0, vcount, 0)          where   packed = (icount << 16) | material_index
```

The **low 16 bits are an index into the companion `.script`'s ModelSkin
`Materials` array**; the high 16 bits are just the node's index count again.

Verified against every textured part of the King Tiger:

```
WheelLeftMain1 -> 12  RdWhls1_Yel      Turret_A      -> 19  Turret_Yel
TrackLeft      -> 24  Track_Lft_1      Copula        -> 19  Turret_Yel
TrackRight     -> 25  Track_RT_1       Cupola_Hatch  -> 19  Turret_Yel
Top_Hull_K     ->  5  Hull1_Yellow1    K_RINGS       -> 20  K_Rings_00
AFender_L      ->  5  Hull1_Yellow1    Numbers       -> 21  Number_00
Body_commander ->  0  TankerUniform    Flag          -> 22  Flag
```

**138 of 138 geometry nodes get a material index**, resolving to 19 distinct
materials on this model.

## Textures

`.tex` files are **plain DDS** (DXT1, `44 44 53 20` magic). Rename and they open
anywhere. Materials, texture paths and alpha modes are plain text in
`Models\<name>.script`'s `CModelMaterial` entries.

**Alpha matters:** materials carry an alpha mode of `DISABLE` or `NORMAL`.
Markings, unit numbers, the flag and the barrel kill rings are `NORMAL` and
alpha-keyed - render them opaque and they appear as **black rectangles** on the
hull and turret.

## A wrong turn worth recording

A first attempt assigned textures by grouping node NAMES - turret subtree gets
the turret sheet, `Wheel*` the wheels, and so on. It looked plausible and was
wrong: the user spotted **turret-ring artwork painted across the mudguards, and
engine vents in the wrong place.** The cause is a shared parts sheet,
`Pnz_Assy1.tex` (material 11, `Panzer_Assets`), used by fenders, tools, vents
and exhausts - which a name heuristic cannot know about.

**The mapping is in the file. Do not guess it from names.**
