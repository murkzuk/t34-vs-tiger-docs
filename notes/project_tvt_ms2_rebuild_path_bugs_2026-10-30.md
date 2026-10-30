# The white Tiger hull: two silent bugs in the rebuild path

2026-10-30. Found because Jeff looked at a texture, not because any test caught it. Worth
writing down twice over: for what the bugs were, and for why the existing gate could not see
them.

## The symptom

ZeeWolf's Tiger I (`u_veh_TIGER_E1_Early_Playable.ms2`) round-tripped byte-identically, took a
pyramid on `Body_Hull`, and loaded. Turret, tracks, wheels and markings all textured. **The
hull was flat white.**

## It was not his data

    hull material assignment   identical in his file and ours: material 3, one submesh,
                               indices 0..40086 vs 0..40089
    his texture                Textures/u_veh_Tiger_E1_P3.tex present in BOTH installs
    all 22 usable textures     present in both (one, u_veh_Tiger_E1_1_SPEC.tex, is missing
                               from his own install as well)

Comparing the rebuilt node against his original, vertex by vertex, put it beyond doubt:

    component     mismatching components (of 59,112 unless noted)
    positions     0
    normals      26,958
    uvs          39,408 of 39,408   <- every UV in the node was (0,0)

## Bug 1 - one orphaned vertex cost the node every UV

The importer creates every vertex in the file, including vertices no surviving face
references (Blender discarded degenerate faces on import). The per-vertex UV builder left
those slots empty, and the caller's rule was "if any vertex has no UV, discard the whole array
and fall back to zeros". A handful of unused vertices therefore zeroed 19,704 UVs, and every
triangle sampled one texel.

Fix: holes are filled from a real UV taken from the same node, and the fill is **opt-in** -
the patch path keeps its old behaviour, because that path falls back to the file's own UVs and
is what the byte-identical gate rests on.

## Bug 2 - a rebuilt node re-shaded the whole tank to add a pyramid

The rebuild path took normals from Blender instead of the authored ones the importer stashes.
On one hull that replaced **26,958 of 59,112 normal components**. The model would have looked
subtly wrong forever, with no visible cause.

Fix: keep the authored normal where the attribute still has data, use Blender's only for
vertices the edit added.

## After the fixes

    positions  0 wrong of 59,112
    normals    0 wrong of 59,112
    uvs        6 wrong of 39,408      <- the orphaned vertices, which no triangle uses

## Why the gate could not see either bug, and what to do about it

The byte-identical gate exports files **untouched**, which uses the patch path. Both bugs live
only in the **rebuild** path, which no gate exercises. That is a real blind spot: the most
confident number in this project says nothing about the code path that modders will actually
use.

What caught it was a different oracle, and it should become a standing one: **compare the
rebuilt node's arrays against the source node's arrays, per vertex.** Positions, normals and
UVs should match exactly for every vertex that existed before the edit. That check is cheap,
needs no engine, and would have caught both bugs the moment they were introduced.

## And a scheduling near-miss, same afternoon

Two sweeps were run concurrently and both wrote to the same temporary file. The result: one
reported a model that "differed" as 1,896,451 bytes in and 26,677 out - a truncation that
looked exactly like a catastrophic writer bug, caused entirely by two processes racing. Re-run
serially with per-process temp files: **133 of 133 and 184 of 184 byte-identical.**

The lesson is the same one this project keeps relearning: **a red result from broken
instrumentation is as misleading as a green one.**
