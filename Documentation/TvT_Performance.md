# TvT performance — verified reference

Consolidated 2026-08-26 from work done 2026-08-25/26. Everything here was
**measured**, not reasoned — six plausible hypotheses died in one day, and the
ones that survived are the ones with numbers behind them.

**Read this before optimising anything.** Most of a day was spent on
explanations that a ninety-second measurement disproved.

---

## The one fact everything else follows from

**TvT is CPU-bound with the GPU sitting idle.** Measured every run:

```
inside Present()   0.1%     <- the CPU waiting for the GPU
inside Lock()      0.0%     <- waiting for a vertex buffer
everything else   99.8%     <- ~14 ms/frame of pure CPU work
```

322,000 triangles a frame at ~68 fps is roughly 20M triangles/sec. Nothing to a
modern GPU.

**Never treat a TvT framerate problem as a GPU problem.**

### Consequences that close old arguments

- **DXVK vs dgVoodoo is irrelevant.** The D3D9 wrapper is **0.0%** of
  steady-state frame time.
- **The `.script` interpreter is not a bottleneck.** `J5Script.dll` is ~2%.
  Optimising script files for speed is wasted effort.
- **The AI is free.** `Behavior.dll` is ~0.5%, *including* the injected
  line-of-sight and occlusion work. Never hold back an AI feature for
  performance reasons.

---

## The noise floor is ±4%

Three runs in identical conditions gave **66.8 / 69.5 / 68.4 fps**.

**Anything below ~4% is not a result.** Say so rather than reporting it. This
figure retroactively settled two arguments the same day it was established.

---

## The two builds have completely different problems

Only "CPU-bound with the GPU idle" transfers between them.

| | REDUX | ZW |
|---|---|---|
| top hot page | a `std::map` lookup, **20.4% of module** | `CAbstractObject`, 7.8% |
| vegetation | ~15% (grass + trees) | **absent from the top 20** |
| objects / joints / collision | not in the top 20 | **~40%** |
| that map lookup | 20.4% | 2.9% |
| 50% of the module fits in | 11 KB | 11 KB — but eleven *different* KB |

The component census the engine prints at shutdown explains it:

```
component                  REDUX      ZW    ratio
AbstractObject                57     496     8.7x
ObjectPhysicsController       58     493     8.5x
Weapon                        62     455     7.3x
CylinderShape                146     926     6.3x
AbstractJoint                550    2536     4.6x
TreeObject                   380      30     0.1x   <-- ZW has FEWER trees
TOTAL COMPONENTS          26,298  84,143     3.2x
```

ZeeWolf built grandiose set-piece battles; REDUX's missions are smaller and
wooded. **REDUX = vegetation. ZW = objects and collision.** `CDynamicIntersector`
appearing beside `CCylinderShape` in ZW means collision testing — hundreds of
moving objects checked against each other every frame.

---

## What each thing actually costs (REDUX)

| | cost | how it was measured |
|---|---|---|
| the `std::map` lookup | **7.59% of frame** | 64-byte profiler histogram |
| grass | **1.8 ms (12%)** at power 5 | grass slider A/B, same scene |
| tree *rendering* | **~0** | forest slider removed 24% of draw calls, frame time unchanged |
| Tiger shadow bug | **~0** | confirmed by reverting the fix deliberately |
| GPU / fill rate | 0.1% | excluded |
| buffer lock stalls | 0.0% | excluded |

**Tree rendering being free is the surprise.** At forest MINIMUM a quarter of all
draw calls and 27% of buffer traffic vanish and the frame time does not move.
The slider changes what is *drawn*; it changes nothing about what is *computed*.

---

## The map lookup, and the cache that fixed it

`Objects.dll+0x17DAB0` — 128 bytes, MSVC `std::map::lower_bound`, a red-black
tree descent. **41,000 calls per frame.** Expensive because every node hop is a
pointer chase into cold memory, not because eight instructions are slow.

**67.2% of calls repeat the key of the call immediately before** — steady to
within half a percent across 23 reporting blocks. So the caller loops over
things sharing a key and re-walks the tree for each one.

A **one-entry cache** in front of it turns that into a single walk per group —
hoisting the lookup out of the loop from outside the engine.

```
CACHE     124.2  126.5  123.9  116.6      median 124.2
BYPASS    117.1  117.1  115.6  116.5      median 116.8
                                          +7.4 fps   +6.3%
```

Record: **~3.6 billion calls across four sessions and two game builds, zero
mismatches.** Shipped as the launcher's "Faster trees" option.

**It is near-pointless in ZW** — the same function is 2.9% there.

### It beat its own arithmetic, and that is reusable

7.59% × 67% hit rate = **5.1% theoretical maximum**. Measured **6.3%**.

Skipping 27 million tree walks a second does not only save those walks, it stops
them evicting everything else from cache. **For pointer-chasing work the direct
arithmetic is a floor, not a ceiling.**

---

## Tuning that is available without code

### Grass — `MaxVisDistPower` is the real lever

`Scripts\Common\BaseGrass.script`. Effective planted area is

```
area = 2*pi*R^2 / ((p+1)(p+2))       R = MaxVisDist max, p = MaxVisDistPower
```

```
G5 stock       R=150  p=5     3366 m2    1.00x
ZW             R=120  p=8     1005 m2    3.35x less
REDUX now      R=120  p=6     1616 m2    2.08x less   <- kept, user-approved
```

**The power, not the distance, does the work** — it thins distant grass
dramatically while barely touching what is near the tank. Power 8 (ZW's value)
was judged too abrupt for REDUX.

Measured after the change, by toggling the in-game grass slider mid-run:
grass fell from 33,751 triangles to **13,347**, against the 2.08x the formula
predicted. **The formula can be trusted for future tuning.**

`Density` is bushes per square metre and **a bush is two crossed billboards**.

### Trees

`ModelLOD` in `BaseSTTree.script`. Pulling the distances back was worth **8 fps**
— REDUX runs `[40, 70, 180, 250]`; a previous experiment at `[160, 280, 480, 720]`
cost that 8 fps. ZW runs `[40, 60, 120, 480]`, which is deliberate tuning rather
than a defect.

### Shadows

`ShadowFar` was worth ~2 fps. Note `LodForShadowHide` defaults to `9999` meaning
"never hide" — a model that fails to declare the field silently keeps that. See
the mission authoring reference, section 14.

---

## The tools, and how to use them

All source mirrored in `Tools/`.

| tool | answers |
|---|---|
| `drawcall_probe` | **CPU or GPU?** Times `Present` and `Lock`, counts draw calls, triangles, buffer locks. One run. |
| `tvt_prof` (sampling profiler) | **which code?** 200 Hz, per-module, per-4KB-page, plus a 64-byte fine histogram and a full-module concentration curve |
| RTTI extraction | **which class?** `pefile` + `capstone`, no Ghidra needed |

### RTTI survives in every shipped DLL

| | named virtual functions | classes |
|---|---|---|
| Objects.dll | **4778** | 300 |
| Controls.dll | 4784 | 287 |
| Engine.dll | 2703 | 281 |

Real names — `CAnyComponentNE@g5`, `IPositionable@g5`. **This is what turns
"Objects.dll is 48% of the frame" into "`CGrass` and `CSTForest` are".** Use it
before decompiling anything.

### Self-A/B is the measurement technique to reuse

The in-game fps counter costs frames of its own, and comparing two separate runs
cannot rule out standing somewhere slightly different or ±3 fps of drift.

**Have the injected DLL count its own frames and toggle its own change every 10
seconds**, reporting each phase. Same scene, same session, seconds apart — one
variable. Position, drift and observer overhead all cancel, and you get a control
column you can look at to judge whether the measurement is sound.

The `BYPASS` control in the cache measurement spanned 115.6-117.1 across four
phases. That tightness is the reason to believe the rest.

---

## Method — every one of these cost a real session

**Predict the number before the run**, so the hypothesis can fail. Six died on
2026-08-25; two were killed by the user's own observation rather than by
analysis.

**A 4 KB profiler page holds ~17 functions.** Never attribute a page to a
function without the 64-byte fine histogram. `+0x17DD00` was named as the target
on exactly that mistake; it runs *once per frame*.

**Check the before and after are the same mission.** A comparison showed +24.4%
and was worthless — the baseline was C1M2 and the run was C1M1. The tell was in
the data: draw calls and triangles both went *up* after a change that could only
reduce them.

**Print the whole report block, never a tail of it.** A `tail -30` cut the top
four entries off a listing and made a correct tool look broken.

**Count braces excluding comments.** Raw counts are unbalanced in the originals
too, because the files contain commented-out code.

**Profiler counters are cumulative since injection.** The first headline figures
included mission load and were wrong; per-window deltas give the true steady
state.

**Measure the texture before blaming the lighting.** Four rounds of lighting
changes went into a commander who is dark because his texture is 22% luminance
against a 62% hull.

---

## Still open

- **~12 ms/frame of the CPU frame is unlocated.** Grass is 1.8, tree management
  ~1.5, the rest has not been found. Everything obvious is excluded.
- **A multi-entry cache.** The current one holds a single entry; the top 16 keys
  cover up to 51% of lookups, so a 4- or 8-entry direct-mapped table should push
  the hit rate past 67%.
- **ZW's collision cost** — 926 cylinder shapes plus `CDynamicIntersector`,
  entirely unexamined.
- **`MaxVisDistPower` on ZW** — do not touch. ZeeWolf already tuned it well.


---

## The frame's biggest single item: waiting on DXVK (measured 2026-08-26)

**~19% of every frame is the game thread blocked on a lock inside DXVK.**
This had never been seen because nobody had profiled the renderer the user
actually plays on.

### First: the install runs DXVK, not native D3D9

```
d3d9.dll                        4.1 MB   = DXVK
d3d9.dll.dgvoodoo                        = dgVoodoo, renamed aside
TvsT_fullLOD_HARD_4GB.dxvk-cache
nvoglv32.dll in the profile              = NVIDIA's VULKAN ICD, not OpenGL
```

Every earlier conclusion about "the D3D9 path" was drawn on a renderer the
user was not running. Check this before any graphics-side reasoning.

### The measurement chain

Page-level profiling could only say "a syscall": a 4 KB page of ntdll holds
**256** syscall stubs, since each `Nt*`/`Zw*` thunk is exactly 16 bytes. Going
to 16-byte buckets names them, and a stack scan names the caller.

```
NtWaitForAlertByThreadId   21.06% of the whole frame   (72% of all syscall time)
registry (OpenKey/OpenKeyEx/QueryKey)   2.66%
file opens (CreateFile/OpenFile/QueryAttributes)   0.90%

WHO CALLS THEM (first non-ntdll, non-KERNELBASE frame)
  D3D9.DLL      64.69%      <- DXVK
  Engine.dll     4.72%
  dinput8.dll    4.55%
  advapi32.dll   4.20%      <- the registry traffic
  dsound.dll     2.97%

  D3D9.DLL +0x099000   36.01%   one page, a third of all syscall time
```

`NtWaitForAlertByThreadId` is the Windows 10 futex - the primitive under SRW
locks, modern critical sections and `std::mutex`.

### Why this is consistent with the drawcall probe, not contradicted by it

The probe measured `Present` at **0.02 ms/frame** and `Lock` at **0.00**. So
these waits are not present-pacing and not buffer locks - they are inside the
draw submission path, which is what a backed-up DXVK command-stream queue
looks like. Two instruments, same story.

### The open question

**DXVK earns its overhead on games issuing thousands of draw calls. TvT issues
454.** Native D3D9 handles that trivially, so DXVK may be paying a threading
cost for a benefit this engine never collects.

A/B switch: `K:\TvTDeepseek
enderer_ab.bat` (`native` / `dxvk` / `status`) -
it only renames `d3d9.dll` and renames it back. Measure with the **drawcall
probe**, which reports fps on either renderer; the DXVK HUD does not exist on
native.

Baseline to beat: **112-118 fps, C2M1**, eight consecutive 5 s windows.

### Method notes from this hunt

- **`GetThreadTimes` is tick-based (~15.6 ms) and under-reports threads that
  block and wake often.** It said the game thread used only 23-59% of a core,
  which suggested blocking; the drawcall probe's wall-clock measurement said
  99.6% compute. The probe was right. Do not draw conclusions from thread CPU
  time alone.
- **A 4 KB profiler page is not a function, and in ntdll it is 256 syscalls.**
- **`KERNELBASE`/`kernel32` are never the answer** to "who called this" - every
  `WaitForSingleObject`, `RegOpenKeyEx` and `CreateFile` passes through them,
  so they are the first non-ntdll frame on every stack. Skip them.
- The launch scripts had **no fps readout at all** until `DXVK_HUD` was added
  on 2026-08-26 - every scripted run before that was unmeasurable by eye.


### Measuring fps: three instruments, each with a catch

| instrument | works on | catch |
|---|---|---|
| **DXVK HUD** (`DXVK_HUD=fps,frametimes,drawcalls,gpuload`) | DXVK only | invisible on native D3D9 or dgVoodoo |
| **F9 - the engine's own render stats** | any renderer | **costs fps while displayed** (user, 2026-08-26). Usable for an A/B only if left on in BOTH halves |
| **drawcall probe** | any renderer | had a real bug until 2026-08-26, see below |

`F9` toggles `CTLCMD_SHOW_STATISTICS` (`Scripts/Common/Game.script:418`). The
key binding itself is inside `Controls.dll` and is not scriptable.

### PROBE BUG, fixed 2026-08-26: it hooked only the FIRST device

`drawcall_probe.cpp` guarded its device hooks with `!g_device_vt`, so it
patched one vtable and never looked again.

**Under DXVK every device shares one vtable, so this was invisible for weeks.**
On native D3D9 the game releases its device and creates another
(`execution.log`: `m_pDirect3DDevice->Release()`, `Device release counter 1`),
and the replacement can sit on a *different* vtable - pure vs non-pure,
hardware vs software vertex processing. The hooks went dead and the probe
logged `16 vertex buffers created` and then nothing, twice in a row, while the
game played a full mission.

Now it re-hooks on every new device vtable, and `patch_slot` refuses to record
its own hook as the "original" (that would be infinite recursion the moment a
second vtable is patched).

**The general lesson: a tool validated on one renderer is not validated.** The
failure looked like "native D3D9 does not work" and was actually "the
measuring instrument does not work on native D3D9".


---

## CLOSED DOOR: native D3D9 is the same speed as DXVK (2026-08-26)

**Tested, not reasoned. Do not re-open this.**

```
                frame     draw calls   triangles    fps (8 x 5 s windows)
DXVK           8.55 ms       454        365k        112 - 119   avg 115.5
native D3D9    8.38 ms       466        392k        115 - 119   avg 117.7
                                                    -----------------------
                                                    +1.9%  (noise floor +/-4%)
```

**Prediction was 130-140 fps. Result was 117.7. The prediction was wrong.**

### What that means for the 19% lock wait

The attribution was right - DXVK really is where the waiting happens - but the
inference drawn from it was wrong. **A wait being large does not make it
recoverable.** Native D3D9 pays an equivalent cost through a different lock.
Submitting ~460 draw calls through the D3D9 API on a modern driver stack costs
what it costs.

**So DXVK is free.** It brings the HUD, the shader cache and Vulkan
translation at no measured framerate cost. That is now measured rather than
assumed.

Switch if ever needed: `K:\TvTDeepseek
enderer_ab.bat` (`native` / `dxvk` /
`status`) - it only renames `d3d9.dll`, nothing is deleted.

## Baseline framerates - and the mission that has never been profiled

```
C2M1 (village)     ~117 fps    466 draw calls   392k tris
C1M1               92 - 104    190 draw calls   340k tris
```

**The original complaint was 70-90 fps. Neither profiled mission is anywhere
near that.** An entire afternoon went into profiling missions that are not
slow. **Before any further performance work, establish WHICH mission or scene
actually drops to 70** - that is where the frame time is, and nothing measured
so far has been looking at it.

### Method lessons banked from this session

- **Profile the thing that is slow.** Obvious, and it was skipped. Ask for the
  slow case before instrumenting anything.
- **A tool validated on one renderer is not validated.** The drawcall probe
  hooked only the first device; under DXVK all devices share a vtable so the
  bug was invisible for weeks. On native it went silent and looked exactly
  like "native D3D9 does not work".
- **When two mechanism-specific fixes both miss, stop guessing the mechanism.**
  A watchdog that re-checks the hooks once a second fixed it without ever
  identifying what wiped them (it fired 3 times per startup).
- **`GetThreadTimes` is tick-based (~15.6 ms) and under-reports blocking
  threads.** It suggested the game thread was only 23-59% busy; wall-clock
  measurement said 99.6% compute. Do not conclude from thread CPU time.
- **A HUD snapshot is not a measurement.** One 52.6 fps screenshot sent the
  session chasing a 2x discrepancy that did not exist - the probe's 5-second
  averages showed a steady 114.


---

## CORRECTION, later on 2026-08-26: the real framerate is ~50, not ~117

Three independent instruments agreed, against the drawcall probe:

```
DXVK HUD    52.6
F9          48
ReShade     52
------------------
drawcall probe   114 - 119     <- the outlier
```

**The probe's fps is inflated by about 2.3x and must not be trusted.** Its
timing code is textbook-correct (QPC, real frequency, counter reset per block)
and `g_frames` increments exactly once per `Present`, so either the game
presents ~2.3x per displayed frame or the QPC arithmetic is wrong. A
`CLOCK CHECK` line was added to the probe on 2026-08-26 to settle which -
it prints QPC seconds against `GetTickCount` seconds each block.

**What this voids:** every per-frame figure the probe printed. `8.55 ms/frame`
is really ~20 ms. `454 draw calls per frame` is only correct if the frame COUNT
is right and the clock is wrong - unknown until the clock check runs.

**What survives:** the `Present` / `Lock` percentages, because they are ratios
of times measured the same way. `Present 0.2%`, `Lock 0.0%`, `everything else
99.6%` still holds. **TvT is still CPU-bound.**

### The A/B conclusion survives too, re-measured properly

```
DXVK   + F9  =  48
native + F9  =  50      = +4%, at the noise floor
```

One instrument, both renderers, LOS on in both. **Native and DXVK are the same
speed.** The probe reached the same verdict (+1.9%) from wrong absolute
numbers - a broken instrument can still give a valid ratio, but that is luck,
not method.

### And the "wrong mission" claim is withdrawn

C2M1 really does run at ~50 fps. It IS a slow mission. The profiler data
collected on it - `Engine.dll` 28.5%, `Objects.dll` 25.8%, `ntdll` 23.2%, the
map lookup at 22.5% of its module - was gathered on exactly the right target
and stands.

## ANTI-ALIASING: enabled, tested, BROKE RENDERING, reverted

`Scripts/Menus/VideoOptionsMenuBase.script` disables AA on any adapter whose
name contains `"NVIDIA"` - a 2001 workaround still firing on modern cards.

**Enabling it let AntiAliasing reach 3, which produced no terrain and invisible
tanks.** DXVK logged nothing at all; the failure is silent. So the original
workaround was right about the engine's MSAA path, not merely about
GeForce-era hardware.

**The trap that cost the most time:** the value persists to
`HKCU\Software\G5 Software\T34`. Greying the control out again left the game
permanently broken with no way to reach the setting - it took re-opening the
row to undo. **Never gate a persistent setting behind a switch with no way
back.**

ReShade is already loaded here with SMAA and FXAA, which are a better AA route
for this game.

### ReShade does NOT attach on native D3D9

Claimed otherwise on the basis of `wrapper.bat`'s comment about the global
injector. In practice `ReShade.log` recorded nothing for the native run.
**F9 is the only fps readout that works on every renderer.**


---

# THE BIG ONE: the LOS hook was costing 55% of the framerate (FIXED 2026-08-26)

```
BEFORE    LOS on   51 fps        LOS off  115 fps      the hook cost ~10.9 ms/frame
AFTER     LOS on  120 fps                              the hook is now FREE
```

**2.35x.** This is the answer to the long-standing "70-90 fps feels bad"
complaint. It was never the 2001 engine - it was our own hook.

## The cause: two VirtualQuery storms

`readable()` in `hook.cpp` is a `VirtualQuery`, i.e. an `NtQueryVirtualMemory`
**syscall**. Two places called it in loops:

```
find_endpoints()   up to 128 + 128*128 = 16,512 syscalls PER VISION CHECK
CrewHook() sweep              256 syscalls PER CREW TICK, ungated
```

`g_crew_calls` reached **125,185 in a single session**, so the second one alone
was ~32 million syscalls.

### Fix 1 - find_endpoints

The scan window is 128 floats from `base`, so **520 bytes**. One `VirtualQuery`
covers all of it. Now: one whole-window check, with a fallback to the original
per-element path if the window straddles a region boundary (behaviour
unchanged, only the cost). Candidates are also collected once into an array
rather than re-validated 128 times inside the inner loop.

### Fix 2 - the CrewHook sweep

Pure reverse-engineering scaffolding: *"sweep this component for object-shaped
fields that change DURING PLAY"* - written to discover which offset moved when
the gunner slewed. **That question was answered long ago**; the offsets are the
named `CREW_*` constants. It was never switched off. Now behind
`g_diag_sweep`, default `false`.

## The method failure that hid this for a whole day

**At 11:40 the evidence was already in hand and was read backwards.** Checking
why a fast run differed from a slow one, the absence of a LOS log in the fast
run was noted - and the conclusion drawn was *"so LOS wasn't the difference"*.
Its absence WAS the difference. The rest of the day went into renderers,
syscall attribution and a native-vs-DXVK A/B, all downstream of that misreading.

**Rules banked:**

- **When two runs differ, diff the CONFIGURATIONS first** - which hooks, which
  wrapper, which overlay - before profiling either one. Presence/absence of an
  injected DLL is the biggest variable there is.
- **Instrumentation you add during RE must be gated before it ships.** A
  discovery sweep is not a feature. Both storms here were debug code that
  outlived its question.
- **`VirtualQuery` is a syscall.** Never call it per element in a loop. Validate
  the whole span once.
- **A user-visible number beats your own instrument.** Three readings said ~50
  while the probe said ~117; the probe was eventually vindicated, but only
  because the ~50 readings were a REAL slowdown the probe never had (it does not
  load LOS). Both numbers were true - of different configurations.

## Still open after this

The profiler data from 2026-08-26 was gathered **without** LOS loaded, so it
remains valid for the base engine: `Engine.dll` 28.5%, `Objects.dll` 25.8%,
`ntdll` 23.2%, the map lookup at 22.5% of its module.

Next cheapest win: the `[CTRL]`/`[CREW]` debug dumps still fire every 128 crew
ticks and wrote **1,800 of 2,300 log lines** in one session, each a file write
on the game thread. Small next to the storms, but the same category of leftover.
