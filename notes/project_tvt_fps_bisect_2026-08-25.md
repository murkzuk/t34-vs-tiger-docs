# Framerate bisect — REDUX C1M2, 2026-08-25

The user reported ~26 fps and could not say when it dropped. Bisected one
variable at a time, same mission, same spot. **Ended at 36-40 with the dawn
look kept.**

## The measurements

| build | fps | change |
|---|---|---|
| as found (this week's work in place) | **26** | — |
| trees `ModelLOD` 720 m → 250 m | **34** | **+8** |
| shadows `ShadowFar` 1050 → 560 | **36** | +2 |
| atmosphere fully reverted to stock | 40 | +4, **but unplayable** |
| **dawn restored, `FogDensity` 0.002** | **36-40** | the keeper |

## What each one actually is

**Trees — the big one, keep it.** `ModelLOD` in `Common\BaseSTTree.script`
governs how far trees are drawn in full 3D before switching to billboards.
DeepSeek raised REDUX's `[40,70,180,250]` to the dev original
`[160,280,480,720]` on 08-24. The mission generates **77,888 trees**; drawing
them in 3D out to 720 m instead of 250 m costs 8 frames. Reverted.

**Shadows — small but free, keep it.** `ShadowFar` 1050 → 560 in C1M2, C1M3 and
C2M2. Two frames. I had flagged 1050 as a likely cost earlier and it was mostly
wrong: it is real but minor.

**Fog — the only one with a genuine trade.**

```
stock  FogDensity 0.003     dawn 0.0013     chosen 0.002
```

Thicker fog draws fewer objects, so stock is *faster* — but at 0.003 visibility
is **5% at 1 km**, and the run proved it: every sight line was under 711 m,
median 683, and **the AI gunner never engaged once**. Unplayable at tank ranges.

At 0.002 the same mission gave **median 867 m, max 1049 m**, and 14 target
acquisitions. About 340 m of engagement range recovered over stock, at a couple
of frames.

**`FogDensity` is a DIAL.** Lower = see further, cost frames. Higher = reverse.
One number per mission in its `Content.script`.

## Applied where

C1M2 only for the fog. **C1M3, C2M2 and C2M4 still carry `FogDensity 0.0013`**
and will run heavier — rolling 0.002 out to them is DeepSeek's call, since the
dawn/sunset recipes are its work.

Trees and shadows are global and already everywhere.

## The part that is NOT explained

DeepSeek measured REDUX at **72 fps** with these same tree settings. Every
change from this week has now been reverted or tuned, and only about half the
gap is recovered. **So a substantial part of the drop predates this week.**

Bisecting further is guessing. The honest next step is a **sampling profiler** —
the same injection machinery, interrupting the game ~1000 times a second to
record where it actually is. That turns a years-old "why is it slow" into a
ranked list. Not started.

## Method note worth keeping

Two runs nearly wasted because the **script cache was still locked by a running
game**, so the edit under test was not the build being measured. Always confirm
`Cache\Scripts.cache` was rebuilt AFTER the edit — compare timestamps, do not
assume.
