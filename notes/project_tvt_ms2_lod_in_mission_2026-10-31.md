# LOD in mission: what six tests actually showed (2026-10-31)

The question was simple: we built a level-1 ladder for ZeeWolf's Tiger, it works in the
editor's asset viewer, so does the engine use it during play? It does not - but the reason is
not the one anyone expected, and three of the tests below exist because earlier tests were
measuring the wrong thing.

Everything here is measured in the running engine, in KurskMission4, and every install was
restored to stock afterwards (hashes at the foot).

## Two method notes that cost real time

**Moving a node's animation track does not move its geometry.** A duplicate hull given +6 in
its track position imported with vertices identical to the original's and rendered in the same
place. To displace a part for a test you must move the **position array**, and the bbox and
sphere with it, or the node lies about itself. `ms2_tool/ms2_move.py` does this.

**Test in the editor's mission runner, not the game.** The editor has a free camera, no grass
covering the vehicle, and no full mission load. Every game-side test today was made harder by
grass and by not being sure which tank on screen was the player's.

## The tests

| # | installed | what happened | conclusion |
|---|---|---|---|
| 1 | his original + **one** duplicate hull, raised 6 m | tank rendered, duplicate hull visible 6 m up | **appending a node is safe** |
| 2 | our 285-node ladder, `SetLods([0])` | tank rendered normally | the ladder does not break the mission path |
| 3 | same ladder, but the LOD1 hull raised 3 m | tank rendered, nothing floating | `SetLods([0])` draws **level 0** |
| 4 | same, `SetLods([5, 2])` | nothing floating at any distance | no array made it draw level 1 |
| 5 | same, all 95 level-1 parts raised **30 m** | sky stayed empty | our appended `_LOD1` nodes are **never drawn** |
| 6 | G5's AI Tiger, its own `_LOD4` nodes raised 30 m | **every AI hull floated, including up close** | the engine draws G5's level nodes - and does not select by distance |

Test 6 was run twice. The first run moved *all* of G5's levels including `_LOD0`, which is a
confounded test: that model's base node `Body_Hull` is empty and its real geometry lives in
`_LOD0`, so the hull floats whatever the engine selects. It proved only that authored
`_LOD0` nodes are drawn. Moving **only** `_LOD4` removed the confound - and the hulls still
floated at close range.

## What that means

**Our ladder and G5's are not the same shape, and the engine only draws G5's shape.**

G5's AI Tiger (`u_veh_TIGER_E1_AI.ms2`):

```
Body_Hull          empty (v=0)
  Body_Hull_LOD0   the actual full-detail geometry   <- drawn
  Body_Hull_LOD1   ... LOD4, adjacent, in order      <- drawn
```

Ours (`tiger_lod1_full.ms2`):

```
Body_Hull          the full-detail geometry itself
  ... 6 other nodes ...
  Body_Hull_LOD1   appended at the end of the file, two hundred nodes later
```

Two differences, either of which could be the cause:

1. **No explicit `_LOD0`.** In G5's layout the finest geometry is a node *named* `_LOD0` and
   the parent is empty. Ours starts the ladder at `_LOD1` with the base carrying geometry.
2. **Not adjacent.** G5's levels sit immediately after their base; ours are appended at EOF.

The engine is not refusing appended nodes in general - test 1's duplicate was appended and drew
happily. It specifically does not draw our appended **`_LOD1`** nodes.

**SetLods semantics, corrected again.** `SetLods([0])` draws level 0, not the coarsest level.
`notes/project_tvt_lod_distances.md`'s "LOD 0 = COARSEST" is wrong, and the earlier reading in
`project_tvt_ms2_lod_level_field_2026-10-30.md` that `[0]` selects the coarsest is also wrong.
Measured: level 0.

**AI units use a different call.** They do not call `SetLods`; they pass distances as the second
argument to `SetupMesh`:

```
AI Tiger    SetupMesh(new #AnimatedObject<Cu_veh_TIGER_E1_AIModel>(), [0, 80, 60, 40, 30])
T-34/76                                            [300, 100, 50, 5]
Pz IV G AI                                         [360, 180, 120, 80]  // "[0,60,80,120,180] was too aggressive"
```

That comment is evidence these arrays do something to somebody. It is also why "the AI units
never set LODs" - an earlier conclusion of mine today - was wrong.

**And yet nothing appears to select by distance.** G5's level-4 meshes drew at close range in
test 6. Either this build draws every level it recognises and no distance table applies, or the
selection happens somewhere we have not found. That question is open.

## Unresolved: the one that started it

Yesterday the same ladder with `SetLods([150, 60])` made the player's tank vanish in
third-person view, twice. Today the same mesh and the same array rendered it normally. Not
reproduced, cause unknown. It may have been a load or streaming state rather than LOD.

## Next step, if anyone picks this up

Rebuild the ladder in G5's shape: rename the 95 base parts to `<name>_LOD0`, give each an empty
parent with the original name, and place `_LOD1` immediately after it. That is a node
**reordering**, not an append - and a large permutation previously produced render spikes
(`project_tvt_ms2_lod_in_mission` note 2, 2026-10-30), so it needs care: test the reordering on
one part before doing 95.

## State after these tests

```
Models\u_veh_TIGER_E1_Early_Playable.ms2     50ef1f9c306e0b4f   stock
Models\u_veh_TIGER_E1_AI.ms2                 6a6175558eca97f2   stock
Scripts\Units\TankPzVITigerE1_EarlyUnit.script  7014ed12553b82fe   stock, SetLods([0]) x4
Cache\Scripts.cache                          deleted, rebuilds on next launch
```

Originals kept in `ms2_tool/out/_backup/`: `ZW_tiger_E1_Early_PLAYABLE_ORIGINAL.ms2`,
`ZW_TIGER_E1_AI_ORIGINAL.ms2`, `TankPzVITigerE1_EarlyUnit.script.ORIGINAL`.
