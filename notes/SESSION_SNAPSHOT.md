# START HERE — snapshot, end of 2026-08-26

Replaces the 2026-08-25 snapshot. Read this first.

## ⚠ ONE UNTESTED VALUE IS LIVE IN THE GAME

`Models\u_veh_PzVI_LATE.script`, the commander material (id 6):

```
new Color(1.000000, 1.000000, 1.000000), // ambient
```

**That is a diagnostic value, set and never run.** It was the last thing done
before the session ended. `1.0` is what the sky materials use. Either run it and
judge, or set it back to `0.000000` — do not leave it and forget what it was
for.

---

## THE OPEN QUESTION: the black tank commander

**A real engine trade, not a bug.** Established by test:

```
PlanarShadow = true    commander readable, tank does NOT self-shadow   (ZeeWolf's choice)
PlanarShadow = false   tank self-shadows, commander goes BLACK         (CURRENT STATE)
```

A planar shadow is a flat projection onto the ground and cannot shade the model
by itself. That is the whole trade, and it is in
`Models\u_veh_PzVI_LATE.script`.

**The decision is the user's**, and it is one word. Claude's view: keep `false`
and the self-shadowing — the tank fills the screen constantly, the commander is
a small figure usually seen from behind. ZeeWolf went the other way, which is a
legitimate choice rather than a better one.

### The live lead when the session ended

With `PlanarShadow = false`, material ambient `0.70` on the commander lit **one
tiny triangle on his face** and nothing else. That is informative:

- material ambient **does** reach him, so the avenue is not closed
- either it is too weak against a stencil shadow (**strength**), or that triangle
  is simply the bit poking out above the tank's shadow volume (**coverage**)

`1.0` was set to distinguish those two and never run. **If more of him lights up
it is strength and a usable value exists. If it is still one triangle it is
coverage, no value will work, and the trade above is forced.**

**Important: the earlier "material ambient does nothing" result was an INVALID
test** — it was run while `PlanarShadow` was `true`, so he was not being
stencil-shadowed at all and there was nothing to fill.

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
