# HANDOVER — 2026-10-31 — the in-mission LOD problem

Read this first. It is written for a session with **no memory of the previous one**.

> **UPDATE, later the same day — the problem in this handover is SOLVED. Read
> `project_tvt_ms2_lod_wrapped_levels_2026-10-31.md` before doing anything described below.**
>
> - The ladder's level meshes were never unreachable. A part's level meshes must hang off an
>   **empty** node that carries the **part's own** transform, with the geometry and the levels on
>   identity tracks. Wrapped that way, 95 parts switch in mission and the tank coarsens as one.
> - Phase 0, 1a and 1b below are therefore obsolete. So is the "explicit `_LOD0` name" idea: no
>   binary contains the string `_LOD`, so the engine never reads node names.
> - `SetLods` does **not** select by distance in the player's unit path. What selects is the
>   *number* of entries (`level = min(entries, levels - 1)`); no call at all gives level 0. So
>   ZeeWolf's four `SetLods([0])` calls must not ship with the ladder - they pin the tank to the
>   coarse mesh at every range.
> - The mission tests no longer need eyes at the keyboard: `ms2_tool/edrive.py` drives the game
>   and captures frames, so a test is unattended and takes ~2 minutes.

---

## 1. The task

**T-34 vs Tiger** (2001, G5 Software) preservation and modding. Three lines of work exist; this
handover is about the third:

1. Gameplay and visuals modding — `t34-vs-tiger-docs/notes/THE_PLAN.md`, Phase 2 in progress.
2. A 64-bit port — `K:\TvTDeepseek\decomp`, **PAUSED 2026-10-29 waiting for a second reviewer.
   Do not resume without the user saying so.** Its parked next step is in
   `decomp/notes/FUN_1001a890_TAKES_THREE_ARGUMENTS_2026-10-30.md` — analysis only, not applied.
3. **This thread: levels of detail (LOD) for the game's `.ms2` models**, so that a hi-poly
   vehicle stops being drawn in full at every distance.

### The specific goal

ZeeWolf's Tiger I (`u_veh_TIGER_E1_Early_Playable.ms2`) has ~68,000 triangles and **no LOD
meshes**, unlike G5's own tanks. We can already *build* a LOD ladder for it that is structurally
correct and verifiable. **The open problem is that the engine does not draw it in a mission.**

Broader context: this build of the engine is **CPU-bound with the GPU idle** (~0.1% of frame time
waiting on the GPU), so polygon count is not where the frames are — see
`Documentation/TvT_Performance.md`. LOD is a modding capability and a long-distance win, not a
framerate rescue. Judge it accordingly.

---

## 2. Current state — everything is stock and pushed

### Game install: `M:\T34vsTiger_ZW2015` (ZeeWolf's mod). Restored to stock, verified by hash.

```
Models\u_veh_TIGER_E1_Early_Playable.ms2        50ef1f9c306e0b4f   9,017,330 bytes   900... stock
Models\u_veh_TIGER_E1_AI.ms2                    6a6175558eca97f2  13,569,072 bytes   stock
Scripts\Units\TankPzVITigerE1_EarlyUnit.script   7014ed12553b82fe   SetLods([0]) x4   stock
Cache\Scripts.cache                             deleted, rebuilds on next launch
```

Originals for restoration live in `K:\TvTDeepseek\ms2_tool\out\_backup\`:

```
ZW_tiger_E1_Early_PLAYABLE_ORIGINAL.ms2
ZW_TIGER_E1_AI_ORIGINAL.ms2
TankPzVITigerE1_EarlyUnit.script.ORIGINAL
```

`python restore_zw_stock.py` puts all three back, deletes the cache, and verifies each hash.

Other installs: `M:\T34vsTiger` (live G5/REDUX, treat as read-only) and
`M:\TvT_INJECT_SANDBOX` (scratch copy, safe to write).

### Repositories

```
K:\TvTDeepseek\t34-vs-tiger-docs   public   branch deepseek/atmosphere-dawn-fog   d8e8bbf  pushed
K:\TvTDeepseek\ms2_tool             private  main                                  2e71d04  pushed
K:\TvTDeepseek\decomp               private  main                                  5df7840  pushed, PAUSED
```

GitHub: `murkzuk`. The `gh` CLI is authenticated (keyring, scopes repo/gist/read:org), so repo
operations need no login dance. **`gh auth login` was done this session — if it expires, the
device-code flow works.**

A release is live with the Blender add-on:
`https://github.com/murkzuk/t34-vs-tiger-docs/releases/tag/ms2-importer-v1.5.2`
(`ms2_importer.zip`, 31,556 bytes). The repo README's front page links to it.

---

## 3. What is proven, and what is not

Everything below was **measured in the running engine** in KurskMission4. Full write-up with the
test table: `t34-vs-tiger-docs/notes/project_tvt_ms2_lod_in_mission_2026-10-31.md`.

| established | evidence |
|---|---|
| importing and exporting any model untouched is byte-identical | **184/184** ZeeWolf, **133/133** G5+sandbox |
| **appending a node to a model is safe** | a duplicate hull rendered 6 m up in mission |
| a 285-node ladder with 95 level nodes does not break the mission | the player's tank rendered normally |
| `SetLods([0])` draws **level 0** | raising the LOD1 hull 3 m produced no float |
| **no array ever made the engine draw our level-1 parts** | `[0]`, `[150,60]`, `[5,2]`, with both the patched and stock exe |
| **our appended `_LOD1` nodes are never drawn** | raising all 95 by 30 m left the sky empty |
| **G5's own level nodes ARE drawn** | raising the AI Tiger's `_LOD4` floated every AI hull |
| AI units set distances via `SetupMesh(model, [distances])`, not `SetLods` | AI Tiger `[0,80,60,40,30]`, T-34/76 `[300,100,50,5]`, Pz IV G AI `[360,180,120,80]` |

**Not established:** whether this build selects a level by distance at all. The G5 test above
had a confound — displacing a node also moves its bounding sphere, so "floating even up close"
may have been the test measuring a farther object. That is Phase 0 below.

**Also unexplained:** on 2026-10-30 the same ladder with `SetLods([150,60])` made the player's
tank vanish twice in third-person view; it did not reproduce on 2026-10-31. Possibly a load or
streaming state.

### The two layout differences that matter

```
G5's AI Tiger (the engine DRAWS these levels)
  Body_Hull          empty, v=0
    Body_Hull_LOD0   the real geometry
    Body_Hull_LOD1   ... LOD4 - adjacent, in order

our ladder (the engine NEVER draws these levels)
  Body_Hull          holds the geometry itself
    (200 nodes of other parts)
    Body_Hull_LOD1   ... LOD4 - appended at end of file
```

1. **No explicit `_LOD0`** — G5's finest geometry is a node named `_LOD0` under an empty parent.
2. **Not adjacent** — G5's levels sit next to their base; ours are appended at EOF.

---

## 4. The plan, in order

### Phase 0 — clear the confound first (15 min)

Install G5's AI Tiger with only `_LOD4` raised **2 m** (not 30), and look from ~10 m with the
editor's free camera.

- Floats at 2 m → the engine *does* select by distance; the earlier result was the displacement
  changing the measured distance. LOD is real; the problem is our layout. Go to Phase 1.
- Still floats → this build draws every level it recognises regardless of distance. Then adding
  levels makes performance *worse*, and the work stops here (Phase 3).

### Phase 1 — find the layout rule, one variable at a time

**1a. Explicit `_LOD0`, no reordering.** For ONE part only (`Body_Hull`): rename it
`Body_Hull_LOD0`, give it an empty parent named `Body_Hull`, leave the appended `_LOD1` where it
is, raise that `_LOD1` by 2 m.
- Draws → the fix is mechanical for all 95 parts, **no reordering risk**.
- Doesn't draw → go to 1b.

**1b. Adjacency.** Same part, insert `_LOD1` immediately after `_LOD0`. This is a genuine
reordering; a large permutation previously produced **render spikes** (see
`project_tvt_ms2_lod_level_field_2026-10-30.md`), so prove it on one part in a scratch file.

### Phase 2 — only after a layout demonstrably draws

Regenerate the full ladder in the winning shape; run `probe_oracle_all.py` and
`probe_lod1_complete.py`; re-run both sweeps; then tune distances. Note `SetLods([0])` draws
level 0, so real settings look like `[far, ..., near]`.

### Phase 3 — if Phase 0 says no selection exists

Stop and document. The ladder remains valid asset work (it works in the editor's asset viewer and
would work in any future engine), but LOD would be dead weight in this build.

### Rules for every test

- **Test in the editor's mission runner, not the game.** Free camera, no grass, no mission load.
  `Editor.exe` in the sandbox or ZW install; it has free camera / player-unit / look-down modes.
- **One variable per install.** Restore to stock between tests.
- **Displace by 2 m, not 30** — large displacements change what is being measured.
- **Never raise `_LOD0`** in a switching test, or the result is meaningless.

---

## 5. Environment

### Blender — available and working

```
G:\SteamLibrary\steamapps\common\Blender\blender.exe      5.2.3 LTS (the only version)
%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\ms2_importer   installed, v1.5.2
```

Run headless with `& '<blender>' --background --python <script.py> -- <args>`.

**After ANY add-on edit, run `python pack_addon.py`** — it rebuilds `ms2_importer.zip`, installs
to `%APPDATA%`, and clears the installed `__pycache__`. Blender loads the *installed* copy at
startup, so `sys.path` does not override it. `bl_addon_guard.py` hard-fails any Blender script
whose loaded add-on differs from the repo copy (**content**, not bytes — a `git checkout` on
Windows rewrites CRLF and used to trip it).

### Ghidra — available and working

```
K:\ghidra_12.1.2_PUBLIC                                         12.1.2, needs JDK 21+
M:\TvT 2024 working folder\ghidra_11.1_PUBLIC_20240607\ghidra_11.1_PUBLIC   11.1, runs on a JRE
M:\TvT 2024 working folder\jdk-21-portable                      Temurin 21.0.11, has javac
```

`JAVA_HOME` on the machine is a JRE 8 (too old) and `java` on PATH is a JRE 25, so **set it per
call**, and redirect the profile because the sandbox denies `%APPDATA%`:

```powershell
$env:JAVA_HOME   = 'M:\TvT 2024 working folder\jdk-21-portable'
$env:USERPROFILE = 'K:\TvTDeepseek\scratch\ghidra_home'
$env:APPDATA     = "$env:USERPROFILE\AppData\Roaming"
& '<ghidra>\support\analyzeHeadless.bat' <proj_dir> <proj> -import <bin> -scriptPath <dir> -postScript <x.py>
```

Post-scripts must be **Jython 2.7**. Recipe: `decomp/notes/GHIDRA_HEADLESS_RUNS_HERE_2026-10-30.md`.

**If the LOD work needs the engine's own selection code**, this is how to read it: the D3D9 engine
is `Engine.dll` / `Objects.dll` in each install, and the project already has a Ghidra workflow for
it. That is the fallback for Phase 3.

---

## 6. The tools, in `K:\TvTDeepseek\ms2_tool`

### Gates — after ANY add-on change

```powershell
python pack_addon.py                                              # install first
blender --background --python bl_sweep_all.py                     # expect 133/133
blender --background --python bl_sweep_zw.py -- 'M:\T34vsTiger_ZW2015\Models' out\zw.tsv   # 184/184
```
Run sweeps **serially** — two at once previously shared a temp file and faked a truncation.

### Format tools

```
ms2_inspect.py    walk a file, per-node spans, --verify a folder
ms2_oracle.py     compare <src> <out> <node> | newnode <file> <node> <parent>
ms2_clone.py      append a node: --clone <idx>=<name>[:<parent>] --move dx,dy,dz  (vertex offset)
ms2_move.py       displace an existing node's POSITIONS: --node <idx|a-b|lod1|re:PATTERN> --move
ms2_setlevel.py   set the header LOD level from the _LOD<n> name suffix
ms2_reorder.py    permute nodes with parent remapping - DIAGNOSTIC ONLY, reordering renders spikes
ms2_layout.py / ms2_writer.py    layout walker and byte-level writer used by the add-on
```

### LOD build and test

```
bl_build_tiger_lod1.py   build the ladder (env: LOD_WELD=0/1, LOD_RATIO, LOD_ANGLE)
bl_lod_render.py         render what the engine WOULD draw at a level;
                         LOD_SHADE=grey|flat|none   (flat = emission, proves holes vs shading)
probe_lod1_complete.py   does every RENDERED part have a level-1 mesh
probe_oracle_all.py      run the oracle over every appended node
set_lod_arm.py           a -> [150,60] | b -> [10000,9000] | orig -> [0] | force -> [5,2] | any literal array
deploy_to_zw.py          install the ladder + arm the unit script (backs up first)
restore_zw_stock.py      put everything back, verify hashes
```

### Current ladder artifacts (`out/`)

```
tiger_lod1.ms2          281 nodes, 91 decimated parts
tiger_lod1_full.ms2     285 nodes, + 4 verbatim clones for the skinned tracks   <- the real build
test_plus1.ms2          original + ONE appended node (proved appending is safe)
test_ghost2.ms2         + a duplicate hull 6 m up (visible in mission)
test_lod1_sky.ms2       all 95 level-1 parts 30 m up (never drew -> levels ignored)
```

---

## 7. Format facts, measured — do not relearn

- **The first int32 of every part record is the LOD level, not a flag.** 0 = base. 95% of shipped
  level nodes carry their suffix; 96% of other parts carry 0. Writing 0 into an added level makes
  it indistinguishable from the base and silently ignored. Documented for years as "a flag,
  always 0" — that was wrong.
- **A level node carries an identity transform** (pos 0, quat 1,0,0,0) while its base carries the
  real offset. A level hangs off its part, which already holds the offset.
- **Moving a node's animation track does NOT move its geometry.** Measured: a duplicate with +6 in
  its track imported vertex-identical to the original. To displace for a test, move the **position
  array** and the bbox and sphere with it.
- **`SetLods([0])` draws level 0**, not the coarsest. Two older notes claim otherwise; both are
  now marked superseded.
- **Game hulls are split-vertex triangle soup** (a Tiger hull has 19,704 vertices for 13,358
  triangles). Weld-then-decimate destroys UV seams and melts plates; decimate-only to 50% of
  *triangles* is what worked.
- **Authored normals must be carried across with a sanity check**: keep the sampled normal only
  where `dot(sampled, recomputed) > 0.25`, otherwise trust the geometry. Without that, panels
  render unlit and look exactly like holes — an **emission render** (`LOD_SHADE=flat`) is the test
  that separates shading from missing geometry.
- **Hidden variant suffixes**: `_LOD<n>`, `_Crashed`, `_CM`, `_CS`, `_FakeShadow`. The importer
  hides all of them; the engine does not render `_CM`/`_CS`.

---

## 8. Method lessons that cost real time

1. **A green result from the wrong input is the recurring failure here.** Both sweeps once ran
   against a stale installed add-on and reported perfect numbers for code that was not under test.
   The guard exists because of that.
2. **Test with content that is known to work.** When something does not draw, first ask whether
   anyone has ever seen that thing draw.
3. **Big displacements change the measurement.** A node moved 30 m is 30 m farther from the camera.
4. **The editor is the right rig**, the game is not: grass hides vehicles, and in third-person it
   is not obvious which tank is yours.
5. **Restore between tests.** Every install in this session was backed up first and restored
   afterwards, with hashes checked. Do the same.

---

## 9. Where it is written down

```
notes/project_tvt_ms2_lod_in_mission_2026-10-31.md      the six tests, what each proved  <- START HERE
notes/project_tvt_ms2_lod_level_field_2026-10-30.md    the level field, transforms, normals
notes/project_tvt_editor_lod_slider.md                 the asset viewer's LOD slider
notes/project_tvt_lod_distances.md                     old SetLods notes - SUPERSEDED in part
Documentation/MS2_Binary_Format_Findings_2026-07-03.md the canonical format doc (corrected)
Documentation/TvT_Performance.md                       CPU-bound findings, measurement method
notes/HANDOFF_2026-10-30_ms2_tool.md                    the previous handover
```

Published: a blog post (`notes/BLOG_POST_zee_wolf_tiger_lod_2026-10-30.md`), a Discord post
(`notes/DISCORD_POST_zee_wolf_tiger_lod_2026-10-30.txt`) and a forum post on
panzersim.forumotion.com (thread t527). The forum strips external links for guests, so the
download link there only works when logged in.
