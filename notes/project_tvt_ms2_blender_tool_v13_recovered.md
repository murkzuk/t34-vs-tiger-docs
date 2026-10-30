# The .ms2 Blender tool: two clones, two different tools

Status: **reconciled 2026-10-30** for this clone (`K:\TvTDeepseek\t34-vs-tiger-docs`, branch
`deepseek/atmosphere-dawn-fog`). The format work itself is unchanged.

## What was actually wrong

Not a bug in the tool — a **branch serving a six-week-old copy of it**.

This clone's `Tools/MS2Format/blender_addon/` was the 18 August source and a **2026-07-03**
zip. The source was byte-identical to the pre-fix backups still sitting in
`K:\TvTDeepseek\rollback\ms2_reader_2026-08-26_pre_transform.py` and
`ms2_addon_init_2026-08-26_pre_transform.py`. So every one of the 26 August and September fixes
was missing here:

* DirectX UVs — V runs 0..-1, so `loop[uv].uv = (u, -v)`; without it 104 of the King Tiger's 138
  textured nodes were mirrored;
* the node transform is **frame 0 of an animation track** (`d_count` positions then `d_count`
  quaternions, `d_count == 161`), so turrets, guns and road wheels sat at the origin;
* submeshes — indices relative to each submesh's `vertex_start` (missing it shredded the upper
  hull of 87 of 249 models);
* the packed `(icount << 16) | material_index` record; materials and textures from the companion
  `Models\<name>.script` (the `.tex` files are plain DDS); skin weights as vertex groups;
* `ms2_writer.py` — absent here entirely.

**The working version existed in two other places the whole time**, and I checked the wrong one
first:

1. the second checkout `C:\Users\Jeff\t34-vs-tiger-docs` (`main`), where it is committed —
   `8e6de62` character rigs, `23a9100` guns imported upside down, `1638bfe` sIG33 `Turret_A`
   traverse — with a zip rebuilt 2026-09-01 (18,381 bytes) that already contained all three files;
2. the installed add-on, `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\ms2_importer\`,
   file-for-file identical to (1).

So there was no defect on the main line, and nothing was lost. What was true is that the branch
this clone is on — the one the whole August atmosphere/TOD effort was done in — would have handed
anyone the tool that renders a tank as a heap of parts at the origin.

## Evidence (sha256, first 16)

| file | size | sha256 | where |
|---|---|---|---|
| this clone `__init__.py` (before) | 11,495 | `680c0a7e0b460b46` | == the 08-26 *pre-transform* backup |
| this clone `ms2_reader.py` (before) | 11,570 | `d82f25dbd8fbbb76` | == the 08-26 *pre-transform* backup |
| this clone `ms2_writer.py` (before) | — | — | absent |
| this clone zip (before) | 7,400 | — | built 2026-07-03 14:36 |
| v1.3.0 `__init__.py` | 20,433 | `afd717bf224bd5fb` | main clone + installed Blender → **now here too** |
| `ms2_reader.py` | 24,417 | `dad6853f23a714c5` | main clone + installed Blender → **now here too** |
| `ms2_writer.py` | 3,395 | `119012c983403543` | main clone + installed Blender → **now here**, one import line changed |

Rebuilt `ms2_importer.zip`: 18,435 bytes, containing `__init__.py`, `ms2_reader.py`,
`ms2_writer.py`, no `__pycache__`. Same path, so the forum post's link needs no edit.

## Verification

`Tools/MS2Format/verify_roundtrip.py` (added with this note) runs the reader and writer from the
add-on folder over every model in both installs:

    131 models found (M:\T34vsTiger\Models + M:\TvT_INJECT_SANDBOX\Models)
    parsed        : 131 of 131   (8,614 nodes total)
    round-trip    : 131 byte-identical, 0 differ
    read failures : 0
    write failures: 0
    RESULT: PASS

King Tiger alone: 335 nodes, 187 submeshes, 14 distinct materials.

### And in Blender itself, not just in Python

The recovered copy was then run by the real application — `G:\SteamLibrary\steamapps\common\Blender`,
5.2.3 LTS, `--background --factory-startup`, importing `M:\T34vsTiger\Models\u_veh_PzVI_LATE.ms2`:

    ADDON_VERSION: (1, 3, 0)      BLENDER: 5.2.3 LTS
    Imported ... 335 nodes (150 with geometry, 181 hidden by default as LOD/Crashed/CM variants)
      skin weights: 30 objects given vertex groups
      rest transforms: 335 nodes placed
      materials: 140 textured, 10 armour/collision hidden, 22 distinct
      multi-material nodes: 19 (submesh indices rebased)
    mesh objects 150 total / 33 visible · 102,246 tris · 186 vertex groups · 8 textures (.dds)
    visible bounding box: 8.337 x 3.750 x 2.851 m

Width 3.750 m against a true 3.755 m. The long axis reads 8.337 rather than the 10.29 m quoted for
"gun forward" because frame 0 is the **rest** pose — the format note records the turret sitting at
0.7071, i.e. 90° of traverse — so the barrel is not on the length axis. Worth one measurement with
the gun swung forward the day the height work starts; it is not evidence of anything wrong here.

## The one change made to the recovered copy

`ms2_writer.py` used a flat `import ms2_reader as R`, which only resolves when it is run from
Blender's text editor with that folder on `sys.path`; inside the package it would fail. Now:

    try:
        from . import ms2_reader as R
    except ImportError:  # run from Blender's text editor, outside the package
        import ms2_reader as R

sha256 `e897340d69d0bd54` (was `119012c983403543`). Nothing else in the file was touched.

## Still open — the real limit, unchanged by any of this

**The writer cannot add or remove geometry.** It copies the original file byte-for-byte and
substitutes only the proven-round-trip geometry span, so `vcount`/`icount` must not change.
Moving vertices, rescaling and rewriting UVs are safe; adding a wheel is not. In the way: the
`vcount × 24` block gated by flag `0x40000` — about **49% of every model file**, meaning unknown
(tested and ruled out as tangent+binormal: mean |dot| 0.51 against computed values) — plus the
80-byte bind poses and the 161-frame tracks. The next test is still "zero the block and see
whether the Editor still draws it", and that is still blocked because **the sandbox Editor does
not work**: it dies before writing `editor.log`, and there is no evidence it has ever run there.

Also:

* There is **no export operator** in the add-on. Import is `File > Import > TvT Model (.ms2)`;
  the writer is script-level only.
* `Tools/MS2Format/` still holds the July legacy path — a second `ms2_reader.py` (9,561 bytes)
  and `ms2_import_blender.py` for the Blender 2.79 install. Two readers with the same module name
  in one folder is a trap.

## The bigger thing this turned up: the two clones have diverged

Common ancestor `f718740` ("Wire the two checkouts together"), then:

* `C:\Users\Jeff\t34-vs-tiger-docs` `main` → `ba271e8` — September: the three model fixes
  above, King Tiger made player tank in BerezovKursk, `WHERE_THIS_STANDS.md`;
* this clone's `deepseek/atmosphere-dawn-fog` → 26 commits — 29 August: Phase 1 close-out, the
  fog/REDUX rollout, the stock-noon missions, the tree-height (GetGeometry) plan.

Neither exists in the other. And **neither is on GitHub**: `origin/main` is still at `62e077f`
(v0.260821), local `main` is 36 commits ahead of it and this branch 61. `git ls-remote` from here
fails with `SEC_E_NO_CREDENTIALS` — no credentials in this sandbox, so nothing can be pushed from
this session; it has to be pushed from a shell that has them.

## The lesson

Same shape as "there are two Berezov missions, and the game loads the other one" and as the
stale-`__pycache__` trap from the same week: **the file you are editing and the file that runs are
not necessarily the same file** — and neither are the two clones of the same repo. Hash the copy
you are about to change against the copy you believe is current. "Which checkout" is a question
worth answering before "what is broken".
