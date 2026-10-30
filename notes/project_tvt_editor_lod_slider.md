# The Asset Viewer has an LOD slider (found 2026-10-30, late)

## Why this matters

`HANDOFF_2026-10-30_ms2_tool.md` §7 says "The Asset View always draws LOD0. Needs an
in-mission look at distance." **That is wrong** — the asset viewer has a first-party LOD
control, so the LOD question needs no mission, no unit class and no script edit.

## Where it is

G5's own debug asset viewer, `Scripts\Editor\BaseAssetViewer.script`, class
`CModelViewerUI`. Two sliders on the bottom edge, created in the constructor:

```
1511  CreateLabel("AmbientLightLabel", L"Ambient Light", 0.22, 0.92, 0.15, 0.03);
1512  CreateSlider("AmbientLight",                     0.22, 0.96, 0.15, 0.02);
1518  CreateLabel("LODLabel", L"LOD",                    0.38, 0.92, 0.15, 0.03);
1519  CreateSlider("LOD",                               0.38, 0.96, 0.15, 0.02);
```

Identical in `M:\TvT_INJECT_SANDBOX` and `M:\T34vsTiger_ZW2015` — this is G5's code,
not something added here.

## What it does

```
1595    // Update LOD
1596    float LOD = GetSlider("LOD").GetValue();
1597    if (LOD != m_LOD)
1598    {
1599      GetMission().GetCamera().LockLOD(0.99 * LOD);
1600      m_LOD = LOD;
1601    }
```

`Camera.LockLOD()` takes a **normalised LOD position in 0..1** and overrides the
distance-based choice. The 0.99 avoids sampling the very end of the range.

```
  slider 0.0  ->  LockLOD(0.00)  finest   (base mesh, e.g. Body_Hull 19,704 v)
  slider ~0.5 ->  mid levels
  slider ~1.0 ->  LockLOD(0.99)  coarsest (Body_Hull_LOD4 1,152 v)
```

## The consequence for the SetLods question

**LOD 0 is the FINEST level.** A single normalised scalar running 0 -> finest to
1 -> coarsest only makes sense that way, and it matches the measured ladders:

- G5 Tiger I `u_veh_PzVI_LATE.ms2`: 335 nodes, 165 LOD nodes, base > `_LOD1` >
  `_LOD2` > `_LOD3` (verts 426 > 385 > 194; 3276 > 1811 > 608).
- G5 T-34/85 `u_veh_t34_85_44_2.ms2`: base > `_LOD1` > `_LOD2`.

So `notes/project_tvt_lod_distances.md` (2026-08-23), which states "**LOD 0 =
COARSEST**. So `[0]` (single element) = 'LOD 0 always' = the tank renders at its
lowest-detail mesh at every distance", has the index **backwards**. That note should be
corrected rather than cited.

Reconciled with `TankPzVI_KingTigerIIUnit.script` (which is right): `SetLods([0])` on a
mesh with **no** LOD nodes renders full detail at every range, because there is only one
level to select.

**Still open, and only matters in-mission:** what `SetLods([0])` does on a mesh that
*does* have LOD nodes. ZeeWolf's four playable Tiger variants all call it
(`TankPzVITigerE1_EarlyUnit.script` lines 1301/1871/2437/3007, each with `// ,120,80,60,40`;
plus `TankPzVITigerE1Unit.script` line 1296 with `// ,80,60,40,20`). If a one-element
array clamps to the coarsest level, the staged Tiger would draw `Body_Hull_LOD1` (30.3 %)
at every distance including point blank. The editor slider cannot answer this — it
bypasses `SetLods` via `LockLOD`.

## The slider test, and how to read it

Asset Viewer on `Cu_veh_TIGER_E1_Early_PlayableModel` (the model script is present in
the sandbox, 31,172 B, so the staged mesh is selectable):

| observation | conclusion |
|---|---|
| hull visibly coarsens 0 -> 1, ends at a ~1,152-vert shell | LOD nodes are live; naming, parent index and the welded-then-decimated ladder are all correct |
| hull never changes | the engine is not using the nodes — investigate naming/ordering, not parenting (handoff §8.2) |
| only some parts switch | per-part ladder gaps; hull and the other 116 geometry nodes were never given LOD siblings |
| seams smear at mid values but not at 0 | the weld, not the LOD plumbing — rebuild without welding (handoff §8.1) |

Bonus: `m_LOD` is `static`, and `LockLOD` is only called when the value *changes*, so
the lock persists when you select another asset. Drag to ~1 and browse the library to
see every model's coarsest level back to back.

## Control protocol (run this before judging any new ladder)

The slider is only meaningful if it visibly moves a **known-good G5 ladder**. Two
controls, best first. Both are already in the sandbox asset browser.

### Control A — G5's Tiger I (`Cu_veh_PzVI_LATEModel`, `u_veh_PzVI_LATE.ms2`)

Measured with `probe_lod_ladders.py`, base -> LOD1..LOD4 in verts:

```
Body              3965 -> 2024 -> 1335 -> 586 -> 266
Turret_A          6223 -> 6251 -> 1638 -> 425 -> 110
Turret_A_Crashed  7709 -> 7092 -> 2380 -> 717 -> 202
Body_Crashed      5538 -> 3026 -> 1485 -> 609 -> 370
TrackLeft_Crashed 7349 -> 3276 -> 1811 -> 608
GearRightMain     2636 -> 2284 -> 1244 -> 496
```

Drag **LOD** to maximum: the hull should fall to a 266-vertex shell and the turret to
110. That is a plaster-model collapse, unmistakable if it happens.

### Control B — a soldier (`Chum_GermanTankmanModel`)

`Body` 640 verts, `Body_LOD4` 32 verts hanging off `ROOT` — a 20:1 drop, the most
sensitive test in either install. Use it if the Tiger change is too subtle to read.

### Reading it

| Control A / B | meaning |
|---|---|
| visibly coarsens | `LockLOD` + slider work, the asset viewer honours LODs, and our Tiger's silence is a REAL finding about our file |
| nothing happens | the slider is inert in the Asset View (the code calls `GetMission().GetCamera()`, which may not be the preview camera) — no conclusion about any model can be drawn here, and the LOD question needs a mission |

Caution: `m_LOD` is `static` and `LockLOD` only fires when the slider value *changes*, so
move it deliberately rather than relying on the starting position.

## Probes written for this

- `ms2_tool/probe_lod_adjacency.py` — is a part's LOD run adjacent to its base? G5: 774
  groups, 3 exceptions (2 are `ROOT`-parented soldiers, 1 is a single stray node), so
  adjacency is *nearly* invariant but **not required** — do not treat placement alone as
  the cause.
- `ms2_tool/probe_lod_counts.py` — ZW: 47 of 184 files carry LOD groups (874 levels), 137
  carry none; his playable Tiger E1 Early/Mid1 and KingTiger are all zero. G5: 40 of 66.
- `ms2_tool/probe_lod_ladders.py` — per-part base -> LOD chain in verts.

## Two shipped ladder patterns (both real)

```
G5 u_veh_PzVI_LATE      base has geometry, ladder LOD1..LOD4
ZW u_veh_TIGER_E1_AI    base EMPTY (v=0), ladder LOD0..LOD4, LOD0 = 20296 verts (finest)
```

So a Tiger hull carrying `Body_Hull_LOD*` siblings is a shipped, legitimate shape. Our
staged ladder follows the first pattern, which is also legitimate; the only deviations are
placement (appended at EOF, six nodes past `Body_Hull`) and order (finest-first instead of
coarsest-first).

## Not done here

- No script was edited. The `SetLods` sites are untouched.
- Nothing committed.
