# New geometry from Blender, in a mission - and the alpha trap that hid it

2026-10-30, continued from `project_tvt_ms2_new_geometry_works_2026-10-30.md`. The export
path now takes geometry that did not exist before, straight out of Blender.

## Where it stands

`File > Export > TvT Model (.ms2)` decides **per node**:

* **counts unchanged** - patch the existing bytes in place, so authored normals, UVs and
  every unmapped block survive exactly (this is what keeps an unmodified export
  byte-identical: 165 geometry nodes, five models, zero differences);
* **vertex count changed** - rebuild that node from the mesh: positions, normals, UVs,
  uint16 indices, one submesh record, recomputed bbox and sphere, `0x40000` tangents
  regenerated from `dP/du` and `dP/dv`, the `0x40` shadow volume copied verbatim, `0x800`
  dropped, `0x10` skin refused rather than silently mangled.

Verified in the engine twice: a cube plus a pyramid in the Asset View, and pyramids on all
58 palisade fences in Campaign 1 Mission 1 - **with shadows**.

## THE ALPHA TRAP - read this before adding geometry

A pyramid was added to `fence_Palisade` and it cast a shadow but was **not drawn**. Not a
format problem, not a winding problem, not a normals problem:

    material     fence_Palisade = KEYCOLOR        (4MeterBox = DISABLE, and it worked)
    texture      Fence_Wire.tex, 256x256 DXT1
                 70% of texels are mid grey (120-175)  <- keys away
                  7.9% are bright (>200)              <- what the fence itself samples
    our first UV (131,129,131) - a keyed grey

**The shadow pass does not alpha-test; the visible pass does.** So geometry left on a keyed
texel draws its shadow and nothing else, which is a spectacularly confusing way to fail.

The first fix attempt was "copy a UV from an existing face" - and it failed, because the
donor face happened to be a *gap* in the wire, i.e. exactly the transparency it was meant to
avoid. **Copying a neighbouring UV is not the same as picking an opaque one.**

The rule for anyone using this tool:

> **UV-map new geometry onto an opaque part of the material's texture.** Do not leave it at
> UV (0,0), and do not assume a neighbouring face's UV is safe. Materials with
> `KEYCOLOR` or `NORMAL` alpha are the ones that will bite: the fences, the wicker, the
> sandbag wall, most aircraft. `DISABLE` materials (most buildings, the vehicles) will
> draw anything.

## What the day cost, and what it bought

Four engine tests, each a different wrong answer before the right one: edge-on triangle,
untouched LOD sibling, cached running editor, keyed texel. None of them were format
problems, and every one of them would have been reported as "the exporter is broken".

Bought: the tool can now open a model, edit it, add to it, and hand back a file the game
loads - with shadows - and a written list of the four ways a change can look like it
failed when it did not.
