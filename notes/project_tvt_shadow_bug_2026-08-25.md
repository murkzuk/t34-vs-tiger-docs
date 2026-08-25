# The Tiger shadow bug — one undeclared line, ~28 fps

2026-08-25. Found while checking `execution.log` after a routine play session.
**Pending one confirmation run** (see the bottom) — the mechanism is proven, the
exact fps attribution is not yet.

## The error nobody read

```
[ScriptManager] "Scripts\Common\ShadowHide.script", 45(7): invalid LValue in assignment
```

One line in a log full of harmless WoV-era noise. It had presumably been there
since the file was written.

## What it actually meant

`ShadowHide.script:45` sets the late-model Tiger's shadow cutoff:

```
Cu_veh_PzVI_LATEModel::LodForShadowHide = 2.6;
```

But `Models\u_veh_PzVI_LATE.script` **never declared that field**. It is the
only model file of the whole set that omits it — every other one has it in the
same place, right after `LodForShadowChange`. So the assignment failed silently
and the class kept the engine default from `BaseModel.script`:

```
final static float   DefaultLodForShadowHide = 9999.0f;
```

**9999 means never hide the shadow.**

And the model is not a special case. `Scripts\Units\TankPzVIAusfEUnit.script`:

```
String getMeshObjectName()
{
  return "Cu_veh_PzVI_LATEModel";
}
```

Unconditional — the `MAIN` variant is commented out on the next line. **Every
Tiger in the game uses the LATE model.** So every Tiger cast a full shadow at
unlimited range, at every LOD, every frame, while every other tank correctly
stopped at 2.0-3.0.

## The fix

Three lines added to `Models\u_veh_PzVI_LATE.script`, matching its sibling
`u_veh_PzVI_MAIN.script` exactly:

```
  static float   LodForShadowHide      = CBaseModel::DefaultLodForShadowHide;
```

The `ShadowHide` error is gone from `execution.log` (0 occurrences after).
Backup: `K:\TvTDeepseek\rollback\shadowhide_2026-08-25\`.

**ZeeWolf's copy already had the line.** ZW is correct here and REDUX was the
odd one out — which is also how the intended form was confirmed before editing.

## What it appears to be worth

Location controlled by the user (same mission, same spot, same facing):

| | fps |
|---|---|
| grass max, **before** the fix | 36-40 |
| grass max, **after** the fix | 66.8 |
| grass off, after the fix | 76.3 |

So **the shadow bug ≈ 28 fps, and grass ≈ 10 fps.**

### Why it costs CPU rather than GPU

The draw-call probe measured the game as CPU-bound with the GPU idle
(`Present` 0.1%). This is a stencil-shadow-era engine, and stencil shadow
volumes compute silhouette edges **on the CPU**, per model, per frame. A
full-detail Tiger mesh at unlimited range is exactly that cost, and it is
exactly the kind of work that leaves a modern GPU doing nothing.

## The bug class is now closed

A static sweep of every `Class::Field = value` assignment in both installs,
checking whether the field is actually declared on the class or any ancestor:

```
REDUX (2390 classes indexed):  none
ZeeWolf (4957 classes):        none
```

The tool was validated first by feeding it the pre-fix model file — it flags
exactly the known bug — so "none" is a real negative, not a broken script.
(First version of the sweep produced three false positives because its
declaration regex was missing `WString`; the type list now comes from counting
every declaration keyword actually used in the tree.)

Script: `lvalue_sweep2.py` in the session scratchpad. Cheap to recreate; it only
reads `.script` files, decoding CP1251 explicitly.

## STILL TO CONFIRM

The mechanism is certain. The **28 fps attribution is not**, because the same
edit also cleared `Cache\Scripts.cache`, and a stale cache could have been
holding back other pending script edits.

**The test:** revert the one line, clear the cache, run the same spot. If it
drops back to ~38, it is proven. Then put it straight back. Five minutes.

Worth doing before this goes in the changelog as fact — two other hypotheses
died today when they were finally measured.
