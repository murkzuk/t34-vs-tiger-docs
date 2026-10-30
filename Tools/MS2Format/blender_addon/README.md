# TvT .ms2 Blender Tool — import **and** export

Open T-34 vs Tiger's models in Blender, edit them, put them back in the game.
No Maya 5, no export plugin.

**Download:** [`ms2_importer.zip`](./ms2_importer.zip) — use **Download raw file** if you are
viewing it on GitHub.
**Version:** 1.5.0 · **Blender:** 2.80 or newer (developed and tested against 5.2)

---

## Install

1. Download `ms2_importer.zip`
2. In Blender: `Edit > Preferences > Add-ons`
3. Top-right ▾ menu → **Install from Disk**, pick the zip, tick the box
4. `File > Import > TvT Model (.ms2)` and `File > Export > TvT Model (.ms2)` now exist

Upgrading from an older copy: install over it and **delete
`scripts/addons/ms2_importer/__pycache__`** — Blender loads the installed copy, and a stale
byte-code cache will keep running the old version while the files on disk look correct.

## Import

`File > Import > TvT Model (.ms2)`. The model arrives assembled and textured: geometry,
rest transforms, submeshes, materials and textures (the `.tex` files are plain DDS), and
skin weights as vertex groups.

Options in the Redo panel (F9) are diagnostics, not just preferences — `Shading: Flat`
tells you instantly whether an artefact is a normals problem (it survives flat shading ⇒ it
is real geometry).

## Editing — two rules

**1. Edit the MESH, not the object transform.** Tab into Edit Mode and move vertices. The
importer puts each node's rest transform on the object, because that is where the file keeps
it; moving the object as a whole has nowhere to go and is ignored on export.

**2. UV-map anything you add.** Do not leave new faces at UV (0,0). On materials with
`KEYCOLOR` or `NORMAL` alpha — the fences, the wicker, the sandbag wall, most aircraft —
a keyed texel makes geometry **invisible in the normal pass while still casting a shadow**.
If a new part casts a shadow you cannot see, that is what happened. Pick a UV point that is
opaque on the texture (for a fence: a bright texel, not a hole in the wire).
`DISABLE` materials — most buildings and vehicles — will draw anything.

## Export

`File > Export > TvT Model (.ms2)`.

- **Source .ms2** fills itself in from the imported objects. It is the file everything you did
  not edit is copied from, so it must be the model you imported.
- Write to a **new file** — the tool refuses to overwrite its own source. Check the result in
  the game, then copy it over the original.
- An export with **no edits is byte-identical** to the original file. That is the guarantee
  that nothing is silently damaged on the way through.

## Testing before it goes anywhere near a mission

Copy the exported `.ms2` into the install's `Models\` folder and open it in the **Level
Editor's Asset View**. Two things worth knowing:

- **A running editor keeps the model it loaded.** Close it fully before checking a change,
  or you will be looking at the old one.
- Models have **LOD siblings** (`CenterSection` and `CenterSection_LOD1`). A change made to
  one node disappears at distance unless the sibling is edited too.

## What works

- import: every model in both builds
- edit existing geometry and export it
- **add new geometry** and export it — including into a mission, with shadows
- untouched geometry round-trips byte for byte

Checked by machine, not by hand-picking examples:

    re-export every model untouched     131 of 131 files byte-identical, 0 errors
                                        (both installs, the whole library)
    add a pyramid to an unskinned node   65 of 66 models produce a file that parses
                                        (the 66th, Landscape_test, has no unskinned node)

What that does *not* cover: seeing all of them in the game. Two models have been looked at
in the engine — one building and one vehicle. The rest is verified at the file level.

## What does not work yet

- **skinned nodes cannot grow** — tracks, wheels and crew figures carry weights against a
  joint table we have not mapped, so they refuse rather than produce something wrong
- **new nodes** (an entirely new part) are not supported — add to an existing node instead
- **multi-material** new geometry collapses to a single material
- **shadow volumes** for new geometry are preserved-but-stale: new triangles cast through the
  game's projected shadow, but the model's own shadow-volume block does not know about them
- no animation authoring

## Troubleshooting — the five ways it "didn't work" but did

**I added something and it isn't in the Asset View.**
The editor keeps the model it loaded. Close it completely and relaunch; then check again.
This one catches everybody, including us, twice.

**My new part casts a shadow but I can't see it.**
It is on a keyed texel. The visible pass alpha-tests and the shadow pass does not, so the
geometry draws its shadow and nothing else. UV-map the new faces onto an opaque point of the
texture — on a fence or wicker texture that means a bright texel, not a hole in the wire.

**It shows in the Asset View but vanishes in a mission, or at distance.**
LOD siblings. `CenterSection` and `CenterSection_LOD1` are separate nodes; a change made to
one is drawn only within that node's LOD range. Edit the siblings too.

**The export refuses, saying the node is skinned.**
That node carries skin weights — tracks, road wheels, crew figures. Their weights index a
joint table we have not mapped, so the tool refuses rather than writing something wrong. Add
your geometry to an unskinned node instead: hulls, turrets, guns, buildings and props are all
fine.

**Everything I added came out as one material.**
Correct for now. A rebuilt node is written with a single submesh record, so new geometry takes
the node's original material. Multi-material new geometry is on the list.

## Credits

Format reverse-engineered from `MayaExp.mll` and the game's own files, with DeepSeek and
Claude. Report what breaks — especially if a model looks wrong in the game but right in
Blender, which is the only way these last few unknowns get closed.