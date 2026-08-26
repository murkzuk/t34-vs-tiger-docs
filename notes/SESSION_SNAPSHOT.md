# START HERE — snapshot, end of 2026-08-26

Replaces every earlier snapshot. Read this first.

# THE HEADLINE: the LOS hook was costing 55% of the framerate. FIXED.

```
REDUX   LOS on   51 -> 120 fps     the hook is now FREE
ZW      LOS on   36-60 fps         same fix, but ZW has a different bottleneck
```

**This was the answer to the long-standing "70-90 fps feels bad".** Not the 2001
engine - our own hook, default-on in the launcher.

`readable()` in `K:\tvt_los\hook.cpp` is a `VirtualQuery`, i.e. a **syscall**:

- `find_endpoints()` called it up to **16,512 times per vision check**, to
  validate a window only **520 bytes** wide. Now one call.
- `CrewHook()` ran a **256-field sweep every crew tick, ungated** - RE
  scaffolding hunting offsets that are now named constants. Now behind
  `g_diag_sweep`, default false.
- The periodic `[CTRL]`/`[CREW]`/`[CMDR]` dumps were **3,788 of 5,252 log lines**
  in one ZW session, and `llog()` `fflush()`es every line. Also gated. ZW's log
  went 5,252 -> 732 lines.

**`g_diag_sweep` must never ship true.**

## MS2: THE EXPORTER WORKS - CONFIRMED IN THE ENGINE 2026-08-26

**The G5 Level Editor loaded and rendered a `.ms2` written by our own code.**
That was the open question; it is closed.

Test: `Models/4MeterBox.ms2` (original G5 file, Dec 2005, used by no mission,
appears in the Editor as "Dartboard 4 meters"). Every Z tripled -> Asset View
showed a 3x tall rectangle, console clean. Original restored, md5 verified.

**Step 1 is why it worked first time:** all 249 models in both builds read and
rewritten UNEDITED - **248 byte-identical, 0 differ**, 1 pre-existing reader
failure. **Round-trip before you edit.**

`Tools/MS2Format/ms2_writer.py` copies the original byte-for-byte and swaps only
the geometry span, so unknown-but-sized blocks are preserved, not invented.

```
SAFE      move vertices, rescale, rewrite UVs, reshape existing geometry
NOT YET   add/remove geometry - identify the vcount*24 block first
          (6 floats/vertex, likely tangent+binormal, computable)
UNTESTED  skinned meshes (the test was a static box)
UNTESTED  collision / .rmap after a shape change
HARD LIMIT: vertex and index COUNTS must not change
```

### TEST-BED RULES - two runs were lost to these

- **Always `cd` into the game folder before launching the exe.** TvT resolves
  `Scripts\`, `Models\` and its log path relative to the CURRENT DIRECTORY.
  Launching by full path from elsewhere = grey screen, no log.
  `K:\TvTDeepseek\play_sandbox.bat` does it correctly.
- **`M:\TvT_INJECT_SANDBOX` had drifted** - 25 changed scripts, one that would
  not compile. Refreshed from live 2026-08-26. A broken test bed looks exactly
  like your change failing.
- **The Level Editor is the better test bed** - it loads models directly rather
  than through a mission.

## MS2 MODEL FORMAT: SOLVED 2026-08-26

The importer went from "imports parts" to "imports finished vehicles" in one
evening. **Use the addon reader; `ms2_probe.py` is SUPERSEDED** (it desyncs on
real vehicles, and the "other_count == 4" in older notes came from that desync -
it is 1).

```
UVs           DirectX convention - NEGATE V.  loop.uv = (u, -v)
transforms    frame 0 of each node's 161-frame animation track
materials     low 16 bits of the 16-byte "other" record: (icount<<16)|mat_index
textures      .tex ARE plain DDS. Paths + alpha modes are plain text in .script
alpha         mode NORMAL must be honoured or decals render as BLACK RECTANGLES
armour        a material with NO texture is collision geometry - hide it
```

Verified: the King Tiger imports at **10.21 m against the real 10.29 m**,
assembled and correctly skinned. Tiger I 8.34 m against 8.45 m.

**UVs beyond 1 after flipping are legitimate TILING** - `TrackLeft` runs to 8.0,
once per track-link repeat. Do not clamp.

### Two instrument traps

- **Blender loads the INSTALLED addon**, not the repo copy
  (`AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\ms2_importer\`).
  It was 8 days stale. Copy across and delete `__pycache__`.
- **`matrix_world` is stale until `bpy.context.view_layer.update()`** - measuring
  straight after import reported the OLD size and made a working fix look broken.

### How the UV bug was found

Claude decoded geometry, transforms and materials from bytes, rendered three
times, and **called it correct**. The user opened the UV editor and saw the
island hanging outside the 0-1 square in seconds. **Second time that day the
user's eyes beat the instrument.**

Working files `K:\TvT_KingTiger\` - `KingTiger_final.blend` is the good one.

## TOMORROW'S LIST - in priority order

Full detail in the docs repo `TODO.md`, which now opens with this.

1. **Ballistic realism pass on ZW.** User wants it; **route not chosen and that
   is a design decision, not a technical one.** REDUX's tables are already the
   REAL historical figures - leave REDUX alone. ZW gives heavy guns FLAT
   penetration *and* inflates close range 25-45%. See
   `Documentation/TvT_Penetration_Tables.md`.
   **Do not fix the Pak 43 alone** - it would make the King Tiger the only heavy
   in ZW that weakens with range.
2. **The King Tiger unit class** - ~1,800 lines from the Tiger E1 template. 14
   class names already dictated by the shared files; all constants exist.
3. **MS2: identify the `vcount * 24` block** - the gate between reshaping
   geometry and ADDING it.
4. **The ambient pass** across the other 11 campaign missions.
5. **ZW performance** - 36-60 fps and view-dependent, so profile worst view
   against best and diff.

## Build stamps

```
REDUX   v0.260826
ZW      v0.260826      matching = the two installs are in step
```

`VersionID` in `Scripts\GameSettings.script`, shown bottom-right in game.
**A DLL-only change counts as a ship** - today's whole win was in
`tvt_los_hook.dll` with no script edit, and the stamp is how "does this build
have the fix?" gets answered without opening a log.

## ZW is still 36-60 fps and it is VIEW-DEPENDENT

The user's observation - "depends where I look" - is the diagnostic. A cost that
varies with camera direction is **frustum content**, not per-unit AI or
collision. ZW has 1.57x REDUX's objects (646 vs 412) but runs 2.4x slower, so
count alone does not explain it. **If ZW performance is picked up: profile the
worst view against the best and diff. Do not assume it is REDUX's problem.**

## Closed today - do not re-open

- **native D3D9 == DXVK** (50 vs 48 fps, F9 on both). DXVK is free.
- **The 19-21% `NtWaitForAlertByThreadId` lock wait is NOT recoverable** - native
  pays the same through a different lock.
- **Anti-aliasing**: hard-disabled on NVIDIA by a 2001 string check. Enabling it
  **breaks rendering** - no terrain, invisible tanks, and nothing in any log. It
  also **persists to the registry**, so closing the menu row again left no way
  back. Reverted. ReShade's SMAA/FXAA is the better route.
- **The map cache stays an opt-in checkbox** - user's decision.
- **`PlanarShadow = false`** - user's decision: self-shadowing, dark commander.

## Measuring fps - the traps

- **Only F9 works on every renderer.** The DXVK HUD is DXVK-only, and **ReShade
  does NOT attach on native D3D9** (tested - its log recorded nothing).
- **F9 costs fps**, so it is valid only when used on BOTH halves of an A/B.
- **`DXVK_HUD=drawcalls,gpuload` is expensive.** Now `fps,frametimes` everywhere.
- The **drawcall probe hooked only the first D3D9 device** - invisible under DXVK
  (shared vtable), silent on native. Fixed with a 1 Hz watchdog that fires 3x
  per startup. Its clock is confirmed correct (QPC vs GetTickCount agree).

## The method failure that cost the day

At 11:40 the decisive evidence was in hand and read backwards: the fast run had
no LOS log, and the conclusion drawn was *"so LOS wasn't the difference"*. **Its
absence WAS the difference.** Renderers, syscall attribution and a
native-vs-DXVK A/B all followed, downstream of that.

**When two runs differ, diff the CONFIGURATIONS before profiling either one.**

---


Replaces the 2026-08-25 snapshot. Read this first.

## DECIDED 2026-08-26: the commander/self-shadow trade

**The trade is real. The user tested both values twice and chose.**

```
PlanarShadow = false   tank SELF-SHADOWS + ground shadow, commander DARK   <- LIVE
PlanarShadow = true    commander readable, tank renders FLAT
```

Reason: the tank fills the screen constantly, the commander is a small figure
usually seen from behind. *"The less of 2 options."*
**Do not flip it back without asking.**

### Open and unexplained — do not re-derive

ZW ships `PlanarShadow = true` **and its Tiger still looks shaded**. The model
files are identical apart from turret alpha mode (`KEYCOLOR` vs `NORMAL`), all
22 materials match, and the engine DLLs are byte-identical. So ZW gets both and
REDUX cannot, and we do not know why. Recorded, not solved.

### Dead: the anti-sun theory

Predicted that REDUX's anti-sun — 3.6x stronger than ZW's and at 10 degrees
instead of 60, so raking the tank's shaded flanks — was the flattener.
**Tested. It is not.** User: *"still too light"*.

C2M1 keeps the corrected values anyway (`0.455 lum / 0.200 / 45 deg`) as a
tidy-up. Rollback:
`K:\TvTDeepseek
ollback\C2M1_Content_2026-08-26_preantisun.script`.

**Keep this fact:** `AntiSunAngle` is a contrast control, not decoration. A low
angle rakes shaded flanks. Fold it into the ambient pass over the other
missions.

### Also weakened

The rule "`ShadowColor` and `StencilShadowColor` must match" — ZW runs stencil
**brighter** (0.522 vs 0.424) and its figures read. Match is a default for
missions that never set stencil at all, not a rule.

---

## PERFORMANCE, 2026-08-26 - one closed door, one wrong turn

**The live install runs DXVK, not native D3D9.** Check this before any
graphics reasoning (`d3d9.dll` is 4.1 MB = DXVK; `nvoglv32.dll` in a profile is
NVIDIA's *Vulkan* ICD).

**CLOSED: native D3D9 is the same speed as DXVK.** Do not re-open.

```
DXVK          8.55 ms   454 draw calls   avg 115.5 fps
native D3D9   8.38 ms   466 draw calls   avg 117.7 fps   = +1.9%, inside noise
```

Predicted 130-140. Got 117.7. **DXVK is free** - keep it.

**19-21% of the frame is `NtWaitForAlertByThreadId`** (the Win10 futex), 65% of
it called from DXVK. The attribution is right; the inference was wrong. Native
pays the same through a different lock. **Not recoverable by swapping
renderers.**

### THE MISTAKE WORTH REMEMBERING

```
C2M1   ~117 fps      <- profiled all afternoon
C1M1   92-104 fps    <- profiled yesterday
complaint:  70-90 fps    <- NEVER PROFILED
```

**An entire afternoon went into missions that are not slow.** Before any
further performance work, find out WHICH mission or scene actually drops to 70.

### Tooling fixed today

- **`DXVK_HUD` added to all three launch scripts** - there was no fps readout
  at all on a scripted run before this. `profile.bat`, `play_drawcall.bat`,
  `play_cache.bat`.
- **F9** toggles the engine's own render stats on any renderer, but **costs
  fps** - only valid for an A/B if on in both halves.
- **drawcall probe: real bug fixed.** It hooked only the first D3D9 device;
  invisible under DXVK (shared vtable), silent on native. Now re-patches on
  every `CreateDevice` plus a 1 Hz watchdog that reinstalls wiped hooks - it
  fires **3 times per startup** on native.
- **Profiler** now buckets ntdll at 16 bytes (one syscall per bucket) and does
  caller attribution by stack scan, skipping `KERNELBASE`/`kernel32`.
- `K:\TvTDeepseek
enderer_ab.bat` - `native`/`dxvk`/`status`, rename only.

### UNSHIPPED WIN sitting on the shelf

**The map-lookup cache is +6.3%**, verified over 42 million calls with zero
mismatches, and is still an opt-in launcher checkbox rather than the default.

---

## What was fixed today

- **C2M1's second Tiger now follows the player in column.** Was 1,352 m away and
  inert. `Follow()` not `Formation()` — Formation takes a displacement vector,
  which is a fixed bearing and therefore echelon by construction. Five separate
  scripted orders had to be neutralised first.
- **Sun vectors normalised on all 12 campaign missions**, and 8 given a real
  time of day (32-55 degrees, was 63-67 everywhere).
- **Grass retuned** — `MaxVisDistPower` 5 -> 6 and `MaxVisDist` 150 -> 120.
  2.08x less planted; user approved the look.
- **`ActivateMove` is gone from both builds** — a command that never existed.
- **ZW grass alpha fixed** — its summer map was still on G5's `0.4`.
- **C2M1 relit**: ambient lum 0.120 -> **0.437**, both shadow colours matched at
  0.38/0.40/0.45.

## The single most useful thing learned today

**REDUX's missions are lit far too darkly, across the board.**

```
REDUX   34 missions, ambient luminance   0.092 .. 0.210
ZW      40 missions, ambient luminance   0.120 .. 0.609
```

Every REDUX mission sits at or below ZW's *dimmest*. Claude spent hours
calibrating against REDUX's own "tuned" missions at lum 0.201 and treating that
as the target — it was never the target. **C2M1 is now at 0.437 and the
commander finally reads.** The other 11 campaign missions are untouched.

**That is the highest-value open job: a considered ambient pass across every
mission.** Bigger than the sun elevations were.

---

## Where the phases stand

Phase 1: question answered (fog rollout still open, DeepSeek's).
**Phase 2: 5 of 7** — sun vectors and times of day done; fog-on-objects
(DeepSeek) and tree height still open.

## Facts not to relearn

- **TvT is CPU-bound, GPU idle** (`Present` 0.1%). Never a GPU problem.
- **Noise floor is ±4%.** Below that is not a result.
- **THREE shadow systems** — stencil (vehicles), projected (terrain), fake blob
  (per model) — plus `AmbientLight`, which is not a shadow setting but produces
  what players call one. `ShadowColor` and `StencilShadowColor` must MATCH
  within a mission.
- **The sun is invisible above ~10 degrees elevation** — that is the hard view
  limit. Shadow *length* is what the player actually sees.
- **A 4 KB profiler page holds ~17 functions.** Never attribute a page to a
  function without the 64-byte fine histogram.
- **REDUX and ZW have completely different performance problems.** REDUX =
  vegetation. ZW = objects and collision (496 objects vs 57).
- **Skinned meshes are missing 64 shader variants** rigid geometry has (every
  `*L`). A capability gap, permanent.

## Method lessons that cost real time today

- **When something renders wrong in one build and right in another, DIFF THE
  BUILDS before theorising.** Seven candidates were eliminated over hours; the
  user's observation that ZW's commanders looked better turned it into a
  three-line diff. The engine DLLs are byte-identical, so any difference is
  necessarily in scripts, models or textures.
- **Check what a change COSTS, not just what it fixes.** `PlanarShadow = true`
  fixed the commander and silently removed the tank's self-shadowing. Not
  flagged, and the user found it.
- **Averaging a whole character texture tells you nothing** — most of the sheet
  is dark background. Sample the region, or just look at the image.
- **Check the test is capable of showing the effect** before believing a null
  result.
- Every finding goes into `Documentation/*.md` **as the work happens**. A dated
  note is a working file, not a record.

## Immediate next steps, in order

1. **Settle the commander** — run the `1.0` test, then take the trade.
2. **The ambient pass** across the other 11 missions (see above).
3. **Shadow consistency**: 1M1, 1M3, 1M4, 2M3, 2M4, 2M6 still need
   `StencilShadowColor` — five never set it at all.
4. Phase 2's last items: fog-on-objects (DeepSeek), tree height.
