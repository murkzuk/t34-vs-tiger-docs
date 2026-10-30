# New geometry works in a mission, and it casts a shadow

2026-10-30. The last open question from the export work, answered on a real mission
(Campaign 1, Mission 1 - "USSR 1 - Breakthrough"), not in the asset viewer.

## What was done

`fence_Palisade.ms2` node `CenterSection` and its `CenterSection_LOD1` sibling each grew a
four-face pyramid of 4 vertices and 12 indices. The palisade fences in that mission (58
instances) all stand in the village, so nothing had to be found.

    node                  before -> after        what changed
    CenterSection         197 v / 447 i -> 201 / 459
    CenterSection_LOD1    192 v / 438 i -> 196 / 450
    flags                 unchanged (0x01040040, shadow volume preserved)
    file                  197,160 -> 197,656 bytes, walks to EOF clean

## The result

Pyramids visible on every fence, **and casting shadows on the ground.**

That second half was not predicted. The reasoning behind preserving the `0x40` block was
conservative - keep the model's shadows by keeping the block - and the assumption was that
new geometry would cast nothing because it is not in the shadow volume. It casts anyway.
The likely explanation, and it is worth confirming before relying on it: the game's shadow
on the ground is a **planar projection of the rendered geometry**, so anything that renders
gets a shadow for free, and the shadow-volume block is for something else (its own shadow
mode, or the editor preview). If that holds, an exporter can drop `0x40` and lose nothing
visible - the opposite of what we assumed this morning.

## What the two failed attempts taught us

Neither was a format problem, and both would have been misread as one:

1. **A lone triangle is invisible edge-on.** The first test added a *translate of the
   node's last triangle*, which for this model is a vertical plank face. From the camera it
   had zero area on screen. Any "new geometry" test must add a **closed solid**, which is
   also a winding check: a face wound the wrong way is culled and you see a hole.
2. **LOD swaps hide a change made to one node.** Growing `CenterSection` alone left
   `CenterSection_LOD1` untouched, so the change would vanish with distance. Grow every LOD
   sibling, or accept a near-view-only result.
3. **A running editor holds the old model.** The editor had been open since 05:59; it drew
   the cached original until it was closed and relaunched. Check for a live `Editor`
   process before believing a negative.

## Which blocks survive a vertex-count change - measured

The instinct "copy everything we do not understand verbatim" is wrong, and only for the
blocks sized by vertex count:

    block    size            survives a vcount change?
    0x800    vcount * 8      NO   copying it gave 192 bytes where the parser wanted 216
    0x10     vcount * 20     NO   skin weights scale with the count (out of scope)
    0x40000  vcount * 24     NO   but regenerable from dP/du and dP/dv
    0x40     4 + n * 52      YES  n is a STORED count, not derived from vcount

## Where this leaves the tool

`ms2_grow.py` can do it, but only from a command line: pick a node, add a solid, write the
file. What is missing is the same thing done from **Blender**, where the geometry is
actually authored. That is the next piece of work, and it is now wiring rather than
research - the node builder exists, the block rules are measured, and nothing about the
format is unknown for static, unskinned parts.

Still out of scope, unchanged: skin weights on new vertices (the 0..255 joint table is
unmapped), and brand-new *nodes* rather than geometry added to an existing one.
