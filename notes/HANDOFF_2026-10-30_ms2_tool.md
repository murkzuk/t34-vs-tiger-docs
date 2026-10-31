# HANDOFF — 2026-10-30 — .ms2 Blender import/export, and ZeeWolf's library

Written because this session is long and the next one starts cold. Read this top to bottom
before touching anything.

---

## 1. WHAT THIS IS

T-34 vs Tiger (2001, G5 Software) preservation/modding. Three separate lines of work exist;
this session was almost entirely the third:

1. **Gameplay & visuals modding** (atmosphere/TOD, fog, AI, performance) — the 5-phase plan in
   `t34-vs-tiger-docs/notes/THE_PLAN.md`. Phase 1 (framerate) complete, Phase 2 in progress.
2. **A 64-bit port** — `K:\TvTDeepseek\decomp`, **PAUSED on 2026-10-29 waiting for a second
   reviewer**. Do not resume without the user saying so. Its one-line next step is parked in
   `decomp/notes/FUN_1001a890_TAKES_THREE_ARGUMENTS_2026-10-30.md` — **analysis only, not
   applied; do not edit translate.py or build the tree.**
3. **A Blender import/export tool for the game's `.ms2` models** — what this session built
   and what this handoff is mostly about.

---

## 2. PATHS (all of them)

### Game installs
    M:\T34vsTiger                      live G5/REDUX install — READ ONLY for this work
    M:\TvT_INJECT_SANDBOX              the sandbox — ALL writes go here
    M:\T34vsTiger_ZW2015               ZeeWolf's mod, 184 models — READ ONLY
    M:\TvT 2024 working folder         Ghidra 11.1, jdk-21-portable, misc

### Repositories
    K:\TvTDeepseek\t34-vs-tiger-docs   docs + the Blender add-on + the zip (branch
                                        deepseek/atmosphere-dawn-fog, pushed to GitHub)
    K:\TvTDeepseek\ms2_tool            TODAY'S WORK — isolated workspace, its own git repo
    K:\TvTDeepseek\decomp              the 64-bit port (paused)
    K:\TvTDeepseek\notes               workspace notes checkout (newest DISCORD_LOG lives here)
    K:\TvTDeepseek\scratch             1.3 GB of older sessions — not ours to gut

### Blender
    G:\SteamLibrary\steamapps\common\Blender\blender.exe     5.2.3 LTS (only version present)
    %APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\ms2_importer\   installed add-on
    Delete the STRAY %APPDATA%\...\5.2\scripts\addons\ms2_reader.py (9,831 B, 2026-08-17) —
      Blender warns about it every start, and it is a second module named ms2_reader.
    The 4.5 add-on "g5_engine_ms2" is a FABRICATED format — its exporter writes "MS2\0" +
      version + flags and its importer guesses at vertex counts. Ignore it entirely.

### Ghidra (both work now)
    K:\ghidra_12.1.2_PUBLIC                                        needs JDK 21+
    M:\TvT 2024 working folder\ghidra_11.1_PUBLIC_20240607\ghidra_11.1_PUBLIC   runs on a JRE
    M:\TvT 2024 working folder\jdk-21-portable                     Temurin 21.0.11 WITH javac

`JAVA_HOME` is globally `jre-8` (too old) and `java` on PATH is a JRE 25. Set it per call:

    $env:JAVA_HOME   = 'M:\TvT 2024 working folder\jdk-21-portable'
    $env:USERPROFILE = 'K:\TvTDeepseek\scratch\ghidra_home'    # sandbox denies %APPDATA%
    $env:APPDATA     = "$env:USERPROFILE\AppData\Roaming"
    & '<ghidra>\support\analyzeHeadless.bat' <proj_dir> <proj> -import <bin> \
        -scriptPath <dir> -postScript <script.py>

Write post-scripts in **Jython 2.7** (Java scripts now compile too, but nothing needs them).
Recipe and findings: `decomp/notes/GHIDRA_HEADLESS_RUNS_HERE_2026-10-30.md`.

---

## 3. THE .ms2 FORMAT — fully mapped

Header: int32 version (always 0), int32 node_count. Then per node:

    name (len-prefixed) · bbox 6f · sphere 4f · counts 4i (lod_level, vcount, icount, other_count)
             *** the first int32 is the LOD LEVEL, not a flag — see section 10 ***
    positions 3f×vcount · normals 3f×vcount · uvs 2f×vcount · indices uint16×icount
    submesh records 4×uint32×other_count   ((icount<<16)|material, index_start, vcount, vertex_start)
    node_id (parent index) · flags_bitmask · d_count (low 16 bits) · anim track d_count×28
    flag-gated blocks, in this order:
        0x800   vcount*8       (rare; duplicates UVs where present)
        0x10    vcount*20      skin: 4 float weights + 4 byte joints
        0x40    4 + n*52  [+ n*8 in newer-exporter files]
        0x200   4 + n*112 · 0x400 4 + n*92 · 0x10000 4 + n*80 · 0x4000 4
        0x40000 vcount*24      TANGENTS then BITANGENTS (solved today)

Key facts, all measured:
* `0x40000` is **vcount tangents followed by vcount bitangents, sequential** (NOT interleaved).
  They match derived dP/du and dP/dv at 0.996–1.000 over 72k+ vertices. The old note "ruled
  out as tangent+binormal, mean |dot| 0.51" was a pairing error.
* **Which blocks survive a vertex-count change**: `0x800` and `0x10` are sized by vcount and
  cannot be copied; `0x40000` must be regenerated; **`0x40` is sized by a STORED count and can
  be copied verbatim** (stale but tolerated).
* Frame counts are **per model**, not fixed: 66 / 81 / 86 / 151 / 161 seen. ZW's files also use
  `d_count = 1`. `d_count = 0` is still untested.
* Rigging: node animation (every moving part is a node with a baked track) plus skinning on
  tracks, road wheels and crew only. Hull, turret and gun are **not** skinned.
* ZW's node names are NOT G5's: `Body`, `GearR`, `Corner_LR`, `HullGunner` — no `Turret_A`.
  Anything that addresses nodes by name will silently attach to nothing.
* LOD convention (G5 and ZW both): `<Base>` plus `<Base>_LOD1..N`, each LOD's **parent index =
  the base node's index**. Verified in `u_veh_PzVI_MAIN` and `u_veh_t34_85_44_2`.

---

## 4. THE TOOL — state

Location: `K:\TvTDeepseek\t34-vs-tiger-docs\Tools\MS2Format\blender_addon\`

    README.md              modder-facing guide (install, edit rules, export, troubleshooting)
    ms2_importer.zip       built by ms2_tool/pack_addon.py — ships the README inside
    ms2_importer/
        __init__.py        import + export operators (v1.5.0), importer stashes ms2_normals
        ms2_reader.py      the proven reader (24 KB)
        ms2_layout.py      NEW — locates every block of every node (validated: 319 nodes, the
                           block sizes sum exactly to file length, zero gaps)
        ms2_export.py      NEW — patch path, rebuild path, new-node path, tangent regeneration
        ms2_writer.py      byte-substitution writer (still used by verify_roundtrip.py)

**Three export paths, chosen per node:**
1. **patch** — counts unchanged: overwrite positions/normals/uvs in place, keep every other
   byte. Recomputes bbox/sphere **only if positions moved** (unconditional recompute was 1 ULP
   off G5's own sphere radius).
2. **rebuild** — vertex count changed: emit the node from the mesh; regenerate bbox, sphere,
   submesh record and `0x40000` tangents; copy `0x40` verbatim; drop `0x800`; refuse `0x10`.
   Keeps authored normals and UVs for the vertices that already existed.
3. **new node** — objects carrying Blender custom property `ms2_new_node = <donor index>` are
   appended after the last node with parent = donor and node_count bumped. This is how the LODs
   were added. **Its first customer is LODs; it is the general "add a part" capability.**

### Gates (run these after ANY change to the exporter)
    cd K:\TvTDeepseek\ms2_tool
    # byte-identical round trip, whole library — the main regression gate
    blender --background --python bl_sweep_all.py        # G5 + sandbox   -> expect 133/133
    blender --background --python bl_sweep_zw.py -- 'M:\T34vsTiger_ZW2015\Models' out\sweep_zw_roundtrip.tsv
                                                          # ZW             -> expect 184/184
    # the oracle — the check the gate CANNOT do, because the gate only exercises the patch path
    python ms2_oracle.py compare <src.ms2> <out.ms2> <node>
    python ms2_oracle.py newnode <out.ms2> <node> <parent>
    # structural: does a file walk to its own last byte
    python ms2_inspect.py --verify <folder>

**Run the sweeps SERIALLY.** Running two at once shared one temp file and produced a fake
"truncation" that looked like a catastrophic writer bug.

---

## 5. WHAT IS PROVEN, AND HOW

| claim | evidence |
|---|---|
| import every model in both builds | 131 of 131 walk to exact EOF |
| unmodified export is byte-identical | **133/133** (G5 + sandbox) and **184/184** (ZW) |
| ZW's whole library survives | 184 files, 502 MB, zero bytes moved |
| engine accepts a reshaped model | Z-scaled box drawn in the Asset View |
| engine accepts NEW geometry | pyramids on 58 fences in C1M1, **with shadows** |
| engine accepts a whole edited vehicle | his T-34/85 with pyramids on Body + Body_LOD1 |
| engine accepts a model G5 never shipped | his `bld_BermPlacement` as `Cbld_BermPlacementModel` |
| engine accepts his Tiger I | `Cu_veh_TIGER_E1_Early_PlayableModel`, textured |
| new nodes can be created | 4 LOD nodes appended, file parses, each passes the oracle |

---

## 6. THE FIVE HARD-WON LESSONS (do not relearn them)

1. **A green result from the wrong input is the recurring failure.** A copied sweep script kept
   its old folder list and reported "131 of 131 identical" — the wrong corpus. Two concurrent
   sweeps sharing a temp file produced a fake truncation. Print and check the population.
2. **The byte-identical gate cannot see the rebuild or new-node paths** — it only exports files
   untouched. That is how two silent bugs survived: every UV in a hull became (0,0) because one
   orphaned vertex made the caller discard the whole array, and 26,958 of 59,112 authored normal
   components were replaced by Blender's. Both found only because the user looked at a white
   hull. `ms2_oracle.py` is the answer; use it.
3. **"Copy everything unknown verbatim" is wrong for anything sized by vcount.** It is right for
   `0x40`.
4. **A lone triangle is invisible edge-on; a LOD sibling left untouched hides a change at
   distance; a running editor keeps the model it loaded.** Three of the four "it didn't work"
   reports were these.
5. **KEYCOLOR / NORMAL alpha materials discard geometry on keyed texels while still casting its
   shadow.** New geometry MUST be UV-mapped to an opaque texel. Copying a neighbouring face's UV
   is not safe — the donor may be a hole in the wire.

---

## 7. WHERE THE LOD WORK STANDS (the live thread)

ZeeWolf's Tiger I `u_veh_TIGER_E1_Early_Playable.ms2`: 190 nodes, 120 with geometry,
hull `Body_Hull` 19,704 verts, and **zero LOD nodes** (G5's Tiger has 165 LOD-suffixed nodes;
his own T-34/85 has 50). Without LODs every distance draws the whole hull.

Built and staged: `M:\TvT_INJECT_SANDBOX\Models\u_veh_TIGER_E1_Early_Playable.ms2`,
sha256 `5B69F2193E080B6B`, 9,917,350 bytes, **194 nodes**:

    Body_Hull         19,704 verts   100%
    Body_Hull_LOD1     5,966          30.3%   parent 183
    Body_Hull_LOD2     4,082          20.7%   parent 183
    Body_Hull_LOD3     2,036          10.3%   parent 183
    Body_Hull_LOD4     1,152           5.8%   parent 183

Parenting matches the convention (LOD parent = base index). **ANSWERED 2026-10-30 — see §10.**
The engine does use LOD nodes, and the Asset View does *not* "always draw LOD0": it has an LOD
slider wired to `Camera.LockLOD()`. What stopped these four from being used was the node-header
LOD level field, which the exporter wrote as 0 on every added node. The staged file has been
re-leveled to 1–4 (`64E86B06BF45546D`) and awaits a visual confirm.

Two content caveats, both measured:
* G5's ladder is 51/34/15/7% of LOD0, but hitting 51% was **impossible**: his hull is 19,704
  verts for 13,358 triangles, and welding gives only 7,217 unique positions — the format stores
  ONE UV per vertex, so every seam duplicates a vertex. The staged ladder was welded then
  decimated, which risks texture-seam distortion **on the hull**; the alternative (decimate
  without welding) only reaches 41% at LOD4.
* A rebuilt node has the same geometry in a **different triangle order** (Blender polygon order)
  and drops degenerate triangles plus duplicate faces. Both render as nothing; the oracle names
  them rather than failing on them.

---

## 8. IMMEDIATE NEXT STEPS, in order

1. **Look at the staged Tiger in a mission at distance** and answer: does the LOD switch happen,
   and do the hull's texture seams survive the weld? (If seams smear: rebuild the ladder without
   welding and accept 69/58/46/41%.)
2. If the engine ignores the LODs, the suspicion is naming/ordering, not parenting — test by
   renaming to match G5's exact form and by re-ordering the nodes.
3. Then the standing backlog: skin weights for new vertices (the 0..255 joint table is
   still unmapped), regenerated shadow volumes, and using the new-node path to add ordinary
   parts rather than only LODs.

---

## 9. HOUSEKEEPING

* Sandbox restores (both currently pristine except the Tiger and the berm asset):
      rollback\4MeterBox_sandbox_ORIGINAL_2026-10-30.ms2          4CB9E46BEE3F14BA
      rollback\fence_Palisade_sandbox_ORIGINAL_2026-10-30.ms2     17A0C8EC555DF261
      rollback\u_veh_t34_85_44_2_sandbox_G5_2026-10-30.ms2        6076D2C39EB6018B
* Added to the sandbox and removable: `Models\bld_BermPlacement.*`,
  `Textures\BermPlacement1*.tex`, `Models\u_veh_TIGER_E1_Early_Playable.*` and its textures.
* Git: the docs repo pushes fine with `$env:GIT_TERMINAL_PROMPT='0'`; it is on branch
  `deepseek/atmosphere-dawn-fog`, now well ahead of `origin/main`, still unmerged.
* Discord drafts written this session: `notes/DISCORD_POST_new_geometry_2026-10-30.txt` and
  `notes/DISCORD_POST_zeewolf_models_2026-10-30.txt`.
* Notes written today (docs repo `notes/`): `project_tvt_ms2_0x40000_is_tangent_space.md`,
  `project_tvt_ms2_export_v1.md`, `project_tvt_ms2_add_geometry_from_blender_2026-10-30.md`,
  `project_tvt_ms2_new_geometry_works_2026-10-30.md`,
  `project_tvt_ms2_zeewolf_corpus_2026-10-30.md`,
  `project_tvt_ms2_rebuild_path_bugs_2026-10-30.md`.
* `ms2_tool/PLAN.md` (the staged route to a working tool) and `ms2_tool/PLAN_ZW.md`
  (the ZW corpus plan and its results) are the two planning documents.
## 10. LOD levels: the field nobody had named (added 2026-10-30, late)

> **STATUS 2026-10-31: measured in the running engine. The ladder still does not switch in
> mission, but not for the reason assumed - see
> `notes/project_tvt_ms2_lod_in_mission_2026-10-31.md` for six tests and what each proved.**
>
> In short: appending nodes is safe; `SetLods([0])` draws **level 0** (not the coarsest); no
> array ever made the engine draw our level-1 parts; and G5's own level nodes in the AI Tiger
> *are* drawn - even at close range, which suggests this build does not select by distance at
> all. Our ladder differs from G5's working shape in two ways: levels appended at the end of the
> file instead of adjacent, and no explicit `_LOD0` under an empty parent. The ZW install is
> restored to stock; the format work below stands.


The first of the four int32s after the bounding sphere — documented since 2026-07-03 as
"flag, always 0" — **is the LOD level**. `0` = the base mesh, `n` = a node named `_LODn`.
Measured: 95.1% of 3,708 shipped LOD nodes match their suffix, 96.4% of all other nodes are 0,
and `u_veh_PzVI_LATE.ms2` matches on every node. **Level 0 is the FINEST mesh**, so
`project_tvt_lod_distances.md`'s "LOD 0 = COARSEST" is backwards and is now marked superseded.

`ms2_export.py` used to write `struct.pack("<4i", 0, vc, ic, 1)` for every rebuilt and every new
node. That is why the four hull LODs appended to ZeeWolf's Tiger did nothing: all four declared
level 0, so the engine saw one level. Fixed 2026-10-30 — added nodes take the level from the name,
plain rebuilds keep the donor's own value. `ms2_setlevel.py` repairs files already written.

Two further facts, both learned the hard way:

- **Node order is load-bearing.** A correctly-remapped permutation (`ms2_reorder.py`) renders
  exploded, with spikes — geometry stretched between the wrong joints. Append nodes; never
  insert or move them.
- **The byte-identical gate cannot see any of this.** It exercises the patch path only. Rebuild
  and new-node output needs `ms2_oracle.py` plus a level-field check.

Two more traps, both live when found:

- **Blender loads the INSTALLED add-on, not the repo copy.** `sys.path.insert` cannot override a
  package already imported at startup from `%APPDATA%`. A stale install silently ran both
  sweeps and reported 133/133 on code that did not contain the fix. Run `python pack_addon.py`
  after any add-on edit; `bl_addon_guard.py` now hard-fails the scripts otherwise.
- **`export_ms2` compared its output node count to the source count**, so appending a node wrote
  a correct file and then raised. Now compares to `source + extras`. The append path needed
  this fix as well as the level fix.

Full write-up: `t34-vs-tiger-docs/notes/project_tvt_ms2_lod_level_field_2026-10-30.md`.
The editor's LOD slider (the fastest way to see any of it) is in
`t34-vs-tiger-docs/notes/project_tvt_editor_lod_slider.md`.
