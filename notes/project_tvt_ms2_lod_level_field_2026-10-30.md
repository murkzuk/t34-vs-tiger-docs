# The node header's first int32 is the LOD LEVEL, not a flag (2026-10-30)

## The fact

Every node header carries four int32s after the bounding sphere. The second, third and
fourth are `vcount`, `icount` and `other_count`. The **first is the LOD level**:

```
0              the base mesh (no _LOD suffix)
n              a node whose name ends _LODn
```

It has been documented as "flag — always 0 in every sample checked" since 2026-07-03, and the
Blender exporter hard-coded 0 when emitting anything. Both are now corrected.

## The evidence

| measure | result |
|---|---|
| nodes named `*_LOD<n>` across G5's 66 models + ZW's 184 | 3,708 |
| of those, field == n | **3,525 (95.06%)** |
| of the 11,858 nodes that are *not* LOD levels, field == 0 | **11,435 (96.43%)** |
| `u_veh_PzVI_LATE.ms2` — the file the editor's LOD slider demonstrably switches | **100% match, no exceptions** |
| ZW `u_veh_TIGER_E1_AI.ms2` (ladder is `_LOD0.._LOD4` on an empty base) | **100% match, including `_LOD0` → 0** |
| files where the field is off by one | 12, all older assets (`u_veh_PzVI_MAIN`, `M3A1HalfTrack`, `t34_85_44`, `StuG40`, `SU85` …) |

```
Body            3965 verts   level 0   (base, no suffix)
Body_LOD4        266         level 4   <- coarsest, HIGHEST number
Body_LOD3        586         level 3
Body_LOD2       1335         level 2
Body_LOD1       2024         level 1   <- finest addition
```

**Level 0 is the finest mesh.** This is the opposite of what
`project_tvt_lod_distances.md` has claimed since 2026-08-23 ("LOD 0 = COARSEST"), which is now
marked superseded. `Camera.LockLOD()` agrees: normalised 0..1 with 0 = finest.

## How it broke the Tiger

The four hull LODs appended to ZeeWolf's `u_veh_TIGER_E1_Early_Playable.ms2` were written with
the field at 0 — because `ms2_export.py` did this for every rebuilt and every new node:

```
316    out += struct.pack("<4i", 0, vc, ic, 1)
```

So all four declared **level 0**, indistinguishable from `Body_Hull` itself. The engine saw one
level of hull and had nothing to switch to. The file parsed perfectly, walked to its exact EOF,
passed `ms2_inspect --verify`, and round-tripped byte-identically — because the byte-identical
gate cannot see the rebuild or new-node paths at all. Silent, again.

The editor result that proved it: dragging the **LOD** slider on G5's stock Tiger visibly coarsens
it; dragging it on the staged Tiger does nothing.

## The fix

`ms2_export.py`:

- `lod_level(name)` returns `n` for a name ending `_LODn`, else 0.
- An **added** node (`name` argument given) takes its level from the name.
- A plain **rebuild** preserves the donor node's own field, so the 12 legacy off-by-one files keep
  their convention instead of being silently rewritten.

Files already written with the bug are repaired by `ms2_tool/ms2_setlevel.py`, which sets the
field from the name suffix and refuses to write unless the walk reaches EOF:

```
python ms2_setlevel.py in.ms2 out.ms2
```

## Node order is load-bearing — never reorder

While chasing this, an experiment moved one part's LOD run to the end of the node list
(`ms2_reorder.py`, which remaps every parent index correctly and preserves the file size
exactly). The model then rendered **exploded, with spikes** — geometry stretched between the
wrong joints. The engine binds meshes to joints through node ordering, not only through the
parent field, so a correct index permutation is still a corrupted model.

**Append nodes, never insert or move them.** This also means `ms2_reorder.py` is a diagnostic
tool, not a repair tool. The gap/order theory of the LOD failure is dead: the level field was the
whole answer.

## Status

- The pipeline now reproduces the repair exactly: `bl_lod_test.py` run through the fixed exporter
  emits `out/u_veh_TIGER_E1_Early_Playable_lods.ms2`, 190 -> 194 nodes, and it hashes
  **`64E86B06BF45546D`** — byte-for-byte the file `ms2_setlevel.py` produced by patching. Two
  independent routes to the same bytes.
- Staged `M:\TvT_INJECT_SANDBOX\Models\u_veh_TIGER_E1_Early_Playable.ms2` is that file,
  awaiting a visual confirm in the Asset View.
- `ms2_oracle.py newnode` PASSES on all four levels (1, 2, 3, 4) and FAILS on the pre-fix backup,
  so the gate now catches this class of bug instead of blessing it.
- Backup of the pre-fix staged file: `ms2_tool/out/_backup/TIGER_staged_BEFORE_levels.ms2`.
- G5's `u_veh_PzVI_LATE.ms2` in the sandbox was restored to stock (`94C574226DAE164A`); copy kept
  at `ms2_tool/out/_backup/PzVI_LATE_sandbox_ORIGINAL.ms2`.

### Still open

1. Confirm the hull now coarsens in the Asset View, and whether the welded ladder smears seams.
2. `SetLods([0])` in-mission semantics — the editor slider bypasses `SetLods` via `LockLOD`, and
   ZeeWolf's four playable Tiger variants all use `[0]` (with `,120,80,60,40` commented out).
3. Shadow volumes (`0x40`) are not regenerated for added levels; they are copied from the donor.
4. Skin weights for new vertices (the 0..255 joint table is still unmapped).

## Trap 1: Blender was loading the INSTALLED add-on, not the repo copy

Every script here does `sys.path.insert(0, <repo blender_addon>)` then `import ms2_importer`.
That does **not** override a package Blender already imported at startup from
`%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\`. With the add-on enabled in
preferences, `sys.modules["ms2_importer"]` is the installed copy and `sys.path` is never consulted.

Consequence, caught in the act on 2026-10-30: a stale installed copy (so old it had no
`ms2_new_node` code at all) silently ran both sweeps, so "133/133 and 184/184 byte-identical"
was reported for code that did not contain the fix under test. This is lesson 1 of the handoff -
a green result from the wrong input - reproduced by the harness itself.

**The rule now:** after ANY edit to the add-on, run `python pack_addon.py` before any Blender run.
`bl_addon_guard.require_repo()` is called by `bl_sweep_all.py`, `bl_sweep_zw.py` and
`bl_lod_test.py` and raises `SystemExit` unless `ms2_export.__file__` sits under the repo path.

## Trap 2: the exporter refused to trust its own success

`export_ms2` verifies its output before returning:

```
after = R.read_ms2(dst)
if len(after) != len(nodes):          # <- compared against the SOURCE count
    raise ValueError(...)
```

Appending nodes makes `len(after)` legitimately larger, so the new-node path wrote a correct
file and then raised every time. Fixed to compare against `len(nodes) + len(extras)`. This is
why the append path could not have worked with current repo code even with the level field
correct - it needed both fixes.

## Probes that found this

`ms2_tool/probe_lod_level.py` (field vs suffix across both libraries),
`probe_lod_level_files.py` (which files disagree),
`probe_lod_indices.py` (are coarse-LOD indices in range — they all are),
`probe_lod_ladders.py`, `probe_lod_contiguous.py`, `probe_lod_counts.py`,
`probe_lod_materials.py`, `probe_lod_records.py`, `probe_lod_flags.py`.
