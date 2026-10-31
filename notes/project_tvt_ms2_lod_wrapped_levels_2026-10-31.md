# The Tiger's LOD now switches in mission — the layout rule, and what the array really does (2026-10-31)

Follow-up to `project_tvt_ms2_lod_in_mission_2026-10-31.md`, which ended with "the engine draws G5's
level nodes and never ours". That conclusion was right about the result and wrong about the cause,
and the tests behind it could not have told the difference. This note closes it.

## Short version

- Our ladder's level meshes were never unreachable. The **shape** was wrong: a part's level meshes
  must be children of an **empty** node that carries the **part's own** transform, with the geometry
  and every level on an **identity** track.
- Apply that to one part and the engine starts switching it. Apply it to all 95 and the whole tank
  coarsens in mission, in one go, still complete and still in the right place.
- **The distance array is a switch, not a distance table.** What selects the level is the *number*
  of entries, not the numbers: a single threshold of 1,000,000 still draws the coarsest level at
  12 m. No `SetLods` call at all draws level 0.
- Therefore ZeeWolf's `SetLods([0])` must not ship alongside the ladder: it pins the tank to the
  coarse level at every range.

## 1. The rig: missions can be tested from code now

The engine takes injected input (`SendInput`) and GDI screen capture reads it, so a mission test is
unattended and takes about two minutes:

    TvsT_fullLOD_HARD_4GB.exe, working dir = the install
      click 960,252    SINGLEPLAYER
      click 1614,326   Project ZeeWolf
      click 951,348    ZITADELLE: M4, Pokrovka      (= KurskMission4)
      click 1620,992   CONTINUE, then START
      wait ~45 s       mission loads into third person
      click 960,540    starts the mission (Space does not)

`ms2_tool/edrive.py` does capture, keys, held keys and clicks; `shot` writes a PNG that can be
judged directly. Two traps: `ShowWindow(SW_RESTORE)` on the fullscreen window minimises the game
(use `--nofocus` once it is foreground), and the game survives being "closed" - confirm the process
is gone before swapping a model.

The opening frame of a mission is deterministic, which makes A/B comparisons between runs honest.

## 2. Which axis is up

ZeeWolf's playable Tiger, `Body_Hull` bbox: x 6.18 (length), **y 3.23 (width), z 3.04 (height)**.
**Z is up, Y is sideways.** Every earlier "raise it 2 m" test with `--move 0,2,0` displaced the part
two metres *sideways*.

## 3. The layout rule

G5's files:

    Body_Hull          empty, v=0, track = the part's offset
      Body_Hull_LOD0   geometry, level 0, IDENTITY track
      Body_Hull_LOD1   geometry, level 1, IDENTITY track
      ...

A level's vertices live in the **part's local space**, so the node the levels hang off has to carry
the part's offset. Wrapping the other way round - empty group taking the *parent's* offset while the
part keeps its own - applies the offset chain twice: the hull sat 0.63 m low and, as soon as the
engine selected level 1, disappeared.

**Names do not matter.** No binary in the install contains the string `_LOD` (or `LOD0`, `_lod`),
so the engine never parses node names to find levels. What it reads is the level field and the
structure. `<part>_LOD<n>` is a convention for humans and for the Blender importer.

## 4. Building and checking it

    python ms2_wrap_all.py   out/tiger_lod1_full.ms2 out/tiger_lod1_wrapped.ms2       285 -> 380 nodes
    python ms2_verify_wrap.py out/tiger_lod1_full.ms2 out/tiger_lod1_wrapped.ms2     PASS

`ms2_wrap_all.py` appends one empty group per part that carries level meshes (95 here), rewrites two
4-byte parent fields per part, and blanks the part's own anim track. Nothing is reordered - appending
is the only structural edit proven safe in this format.

`ms2_verify_wrap.py` recovers the old tracks from the original file and asserts, per part: group
track == the part's old track; part track is identity; part and every level child are parented to the
group; level tracks are identity; the file walks to EOF.

`out/tiger_lod1_wrapped_up3.ms2` is the same file with every level mesh raised 3 m, which is what
makes a switch visible at a glance.

## 5. Measured in mission

ZITADELLE M4 Pokrovka, player's Tiger, judged from screenshots.

| installed | arm | result |
|---|---|---|
| wrapped, plain | `[0]` | tank complete, coarse - level 1 |
| wrapped, plain | `[150, 60]` | complete, coarse - level 1 |
| **wrapped up3** | `[100000, 0.001]` | **whole tank lifts 3 m: every wrapped part coarsened at once** |
| wrapped up3 | `[0]`, `[300, 200]`, `[1000000, 900000]`, `[60, 150]`, `[1000000]` | floats 3 m - level 1, every time |
| wrapped up3 | **`SetLods` commented out** | **does not float - level 0** |

The 3 m lift is only a marker. Without it the tank still renders correctly at level 1; with it, the
switch is undeniable and so is the fact that all 95 parts switched together and the composition
stayed whole.

Also measured: **G5's own levels draw.** Raising `_LOD1.._LOD4` of `u_veh_TIGER_E1_AI.ms2` by 2 m
floats the AI Tigers' hull, turret and gun while their tracks and wheels stay on the ground - those
parts have no level meshes, so they keep their level-0 geometry. Level switching is per part.

## 6. The array is a switch, not a distance table

A single threshold of **1,000,000** still selected the coarsest level at a camera distance of about
12 m. Any distance rule would have given level 0 there. Ascending and descending orders behave
identically. What fits every observation is the *count*:

    level = min(number of distance entries, levels present - 1)

    no SetLods call   0 entries -> level 0
    [x]               1 entry   -> level 1
    [x, y]            2 entries -> level 1     (this mesh has levels 0 and 1 only)

This also explains the older "`SetLods([0])` draws level 0" result that three notes carried: with
the unwrapped ladder no level could be drawn at all, so everything looked like level 0. The 2026-08-23
note that `[0]` makes a tank look "rubbish" was describing the coarsest mesh and was right.

**Consequence for the mod.** `Scripts\Units\TankPzVITigerE1_EarlyUnit.script` calls
`GetMeshComponent().SetLods([0])` at four sites (all four playable variants share one mesh file).
With the wrapped ladder installed, that pins the tank to the coarse level permanently. The ladder is
only safe to ship together with a script change, or with those calls removed (which is the "always
full detail" setting - no benefit).

It also means LOD was never going to help the player's *own* tank in third person: the camera sits
about 12 m behind it at all times, so no distance threshold is ever crossed. The value is for AI and
other vehicles, spectator and editor cameras, and any other model - the mechanism is what became
available here.

## 7. Still open

Whether anything in this build selects a level by distance. The player's unit path does not. Two
leads:

1. the AI path, `SetupMesh(model, [distances])` - raise ONLY `_LOD4` of G5's AI Tiger by 2 m and
   compare an AI Tiger at ~40 m with one at ~200 m. Near clean and far floating means the AI path
   selects by distance and the gap is in the unit path, not the engine.
2. the per-frame update that would have to call the same virtual slot `0x150` that `LockLOD` calls
   (`Objects.dll FUN_10029990`: `level = ROUND((maxLevels + bias) * factor)`, then slot +0x150 on
   every renderable in a set). If no such update exists for vehicles, the level is only ever what
   the script or `LockLOD` set.

## 8. Tools added

in `ms2_tool/`:

    ms2_wrap_all.py       wrap every part that has level meshes (append-only)         <- the fix
    ms2_wrap_part.py      wrap ONE part, for single-variable tests
    ms2_verify_wrap.py    structural check of a wrapped file against the original
    edrive.py             screen capture + key/mouse injection (drives the game)
    move_all.py           displace every geometry node (bbox and sphere included)
    pngdiff.py            compare two frames
    node_fields.py        dump level / flags / d_count / submeshes for chosen nodes
    who_parent.py         parent and children of a node, with levels
    axes.py               which axis is up, from the bbox spans
    show_fn.py, fn_of_line.py, parse_reg4.py, stack.ps1   decompiled-C and side-by-side helpers

Artifacts (not committed - `out/` is ignored): `tiger_lod1_wrapped.ms2`,
`tiger_lod1_wrapped_up3.ms2`, `test_wrap2*.ms2`.

## 9. State

ZeeWolf's install is stock and verified:

    Models\u_veh_TIGER_E1_Early_Playable.ms2        50ef1f9c306e0b4f
    Models\u_veh_TIGER_E1_AI.ms2                    6a6175558eca97f2
    Scripts\Units\TankPzVITigerE1_EarlyUnit.script   7014ed12553b82fe   SetLods([0]) x4
    Cache\Scripts.cache                             deleted

Seven wrapped-model mission runs, no crash, no broken mission, nothing left inside the game folder.
