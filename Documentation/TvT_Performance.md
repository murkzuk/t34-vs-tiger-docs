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
