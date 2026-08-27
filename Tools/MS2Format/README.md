# T-34 vs Tiger `.ms2` model tools

Open T-34 vs Tiger's vehicle, building and terrain models in Blender — and write
them back out in a form the game engine accepts.

`.ms2` is the model format used by G5 Software's "G5/Napalm" engine (T-34 vs
Tiger, 2001, and Whirlwind over Vietnam). There is no published spec and no
source; everything here was worked out by reading the files.

---

## Install the Blender add-on

**Download:** [`blender_addon/ms2_importer.zip`](blender_addon/ms2_importer.zip)
— use the **Download raw file** button on GitHub. Don't unzip it.

Then, in Blender:

1. **Edit → Preferences → Add-ons**
2. The **▾ dropdown** at the top-right of that panel → **Install from Disk…**
3. Pick `ms2_importer.zip`
4. Tick the checkbox next to **T34 vs Tiger .ms2 Importer** to enable it

Blender 2.80 or newer. Developed and tested against **5.2.1 LTS**.

> On Blender 4.2+ this installs as a legacy add-on, which is fine and fully
> supported — it just isn't in the Extensions list. Use *Install from Disk*, not
> *Get Extensions*.

## Use it

**File → Import → TvT Model (.ms2)**

Point it at any `.ms2` in the game's `Models\` folder. You get the whole vehicle,
assembled and textured, in one step.

It reads the companion `Models\<name>.script` beside the model for materials and
texture names, and loads the `.tex` files those name. Keep the model where it
lives in the game install and this is automatic. Open a `.ms2` on its own,
somewhere else, and you'll get untextured grey geometry — that's the missing
`.script`, not a broken import.

### Options (the Redo panel, bottom-left after importing, or press F9)

| Option | What it does |
| --- | --- |
| **Hide variants** | Hides `_LOD1/2/4`, `_Crashed` and `_CM` nodes. They sit in the same place as the real part, so showing everything stacks the intact, wrecked and low-detail versions on top of each other. Nothing is discarded — just hidden. |
| **Skip degenerate** | Drops zero-area triangles. |
| **Shading** | `Authored` uses the file's own normals (what the game does — the default). `Smooth` derives them from topology. `Flat` disables smoothing. This is a diagnostic: **if an artifact survives Flat shading it is not a normals problem**, it's real geometry, because flat shading can't misread a normal it never uses. |

### Things worth knowing

- Some nodes are **crew and module hit boxes** (`HullDriver`, `HullEngine`,
  `HullGunlayer`) and **fake-shadow duplicates** (`*_FakeShadow`). They are real
  parts of the file and are imported visible. Hide them if they're in your way.
- UVs are DirectX-style; the importer flips V for you. Values outside 0..1 are
  legitimate tiling (tracks run to 8.0, once per link).
- `.tex` files are plain DDS. Renaming one to `.dds` opens it in anything.

---

## Writing models back out

`ms2_writer.py` edits a file in place. It copies the original byte-for-byte and
substitutes **only** the geometry, because several blocks in the format are of
known size but unknown meaning — this preserves them verbatim rather than
inventing them. Confirmed in the engine: the game's own Editor renders files
written this way.

```python
import ms2_writer

def edit(node):
    if node.name != "Body":
        return False
    node.positions = [(x * 1.1, y, z) for (x, y, z) in node.positions]
    return True          # return True if you changed anything

ms2_writer.rewrite("u_veh_Hummel.ms2", "u_veh_Hummel_edited.ms2", edit)
```

**Hard limit: vertex and index counts must not change.** Moving vertices,
rescaling and rewriting UVs are safe. Adding or removing geometry is not
supported yet — it needs the vertex-count-sized blocks (and the bounding box and
sphere) regenerated first.

An unedited rewrite is byte-identical to its source on all 249 models in both
builds tested.

---

## What's in this folder

| File | |
| --- | --- |
| `blender_addon/ms2_importer.zip` | **the installable add-on** |
| `blender_addon/ms2_importer/` | its source |
| `ms2_reader.py` | the format decoder, standalone. `python ms2_reader.py <file>` prints the node tree |
| `ms2_writer.py` | in-place editing, as above |
| `ms2_skin.py` | skin-weight helpers |
| `ms2_probe.py` | **superseded** — kept only as the record of how the format was first worked out. Two of its answers are wrong; see its header |
| `ms2_import_blender.py`, `ms2_parser.py` | earlier standalone scripts, superseded by the add-on |

`ms2_reader.py` here and the copy inside `blender_addon/ms2_importer/` **must
stay identical**. They silently diverged for eight weeks once, which cost a
session.

## Format notes

The decode is written up in the code comments, which carry the evidence for each
field, and in `../../CHANGELOG.md`. The two entries worth reading first are *the
.ms2 model format, fully decoded* and *the submesh descriptor*.

Still unidentified: a `vertex_count * 24` block (6 floats per vertex) gated by
flag `0x40000`, almost certainly tangent and binormal. That block is the one
thing standing between "reshape what exists" and "add new geometry".
