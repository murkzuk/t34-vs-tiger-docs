# .ms2 export v1.4.0: edit a model in Blender and write it back

2026-10-30. The add-on now does both directions. `File > Export > TvT Model (.ms2)`.

## What it writes

    positions   from the Blender mesh, in vertex order
    normals     from the ms2_normals attribute the importer stashes
    uvs         from the UV layer, V negated back to the file convention
    bbox        recomputed - but ONLY when positions actually moved
    sphere      recomputed - same rule
    everything else   copied from the source file byte for byte

**Vertex and index counts never change.** That is the whole design: positions, normals
and UVs are equal-length substitutions, so every block whose meaning is not fully mapped
- shadow volumes (52-byte records), bind poses, the 0..255 joint table, the per-node
animation tracks - is copied through untouched instead of rebuilt. Nothing is invented.

## The gate that makes it trustworthy

Import a stock model, export it untouched, and the output must equal the original byte
for byte. It does:

    model                     geometry nodes   result
    4MeterBox.ms2                     1         byte-identical
    bld_Haystack.ms2                  2         byte-identical
    u_veh_t34_76_41.ms2               9         byte-identical
    bld_BridgeWood.ms2               15         byte-identical
    u_veh_KingTiger.ms2             138         byte-identical   (11,900,688 bytes exact)

165 geometry nodes across five models, zero differences, no eyes required.

**What it caught.** Recomputing the bounding sphere unconditionally produced a radius one
ULP away from G5's own: `0.8660254` reached by two different arithmetic routes, differing
in the low byte of the last float. The rule became "a derived field that has not changed
is not republished". Without it, moving one vertex would silently rewrite every bounding
sphere in a 220-node model with a value 6e-8 wrong - invisible, and later blamed on the
engine.

**Two traps it forestalled.** Blender's normals are *derived* and the file's are
*authored*, so reading normals back from Blender would have replaced them everywhere while
the export still looked right; hence the stashed attribute. And vertex order survives only
because the importer creates every vertex, including ones referenced solely by skipped
faces - the gate would have failed loudly had that been untrue.

## Accepted by the engine (Level Editor, Asset View)

    a hand-written Z x3 box          drew three times taller
    Blender mesh edit, Z x0.25       drew as a flat slab
    the export operator, X x2        bbox -1.0..1.0, 44 bytes changed, length preserved

## How to use it

1. `File > Import > TvT Model (.ms2)` - the model arrives assembled and textured.
2. Edit the **mesh**: tab into Edit Mode, move vertices, scale them. The exported
   geometry is the mesh's local data.
3. `File > Export > TvT Model (.ms2)` - "Source .ms2" is filled in from the imported
   objects; write to a new file.
4. Copy the result into `M:\TvT_INJECT_SANDBOX\Models\` and check it in the Asset View
   before it goes anywhere near a mission.

**Edit the mesh, not the object transform.** The importer puts each node's rest transform
on the object, and the file stores that transform in the node's animation track. An
object-level move has nowhere to go: exporting it would either double the transform or be
ignored. v1 ignores it.

It also refuses to overwrite the source in place - export to a new file, look at it in the
engine, then copy it over.

## Not in v1

Adding or removing geometry (the two unknowns behind that are recorded in
`ms2_tool/PLAN.md` as v2), regenerated shadow volumes, skin weights on new vertices,
authored animation for a new moving part, and writing the companion
`Models/<name>.script`.

## One piece of housekeeping this turned up

`%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\ms2_reader.py` - a stray
standalone copy of the reader (9,831 bytes, 2026-08-17) sitting NEXT TO the add-on package,
not inside it. Blender now warns about it on every start ("add-on missing 'bl_info'"), and
worse, it is a second module called `ms2_reader` on the add-ons path. It is superseded by
`ms2_importer/ms2_reader.py` (24,417 bytes) and should be deleted.
