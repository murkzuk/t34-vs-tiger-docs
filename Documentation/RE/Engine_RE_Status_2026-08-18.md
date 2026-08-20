# TvT probe — status as of 2026-08-18 05:00

Working notes for picking this up cold. Everything here is verified unless marked
otherwise.

## What works

- **Injection.** `tvt_inject.exe` starts the sandbox game suspended, injects
  `tvt_probe.dll` via `CreateRemoteThread(LoadLibraryA)`, resumes. Reliable across
  ~6 runs. Refuses any target outside `M:\TvT_INJECT_SANDBOX`.
- **Runtime class location.** Engine DLLs relocate massively (`Behavior.dll` has
  landed +237MB, +252MB, +234MB on different runs). Always resolve as
  `GetModuleHandleA("Behavior.dll") + static RVA`. Never hardcode.
- **Live object census.** Scan committed memory for primary-vtable pointers
  (`this_offset == 0` in RTTI). Reads real objects: counts are exact and stable,
  and differ correctly between classes.

## The big finding

**TvT runs the OLDER generation of every engine subsystem.** Census during a live
mission — 25 classes, 489 objects:

    CVehicleBehavior 20   CHumanBehavior 25   CRouter@router 48
    CUnitGroup 11         CMover/CPathStack/CExactPathLayer/
                          CNetSyncData/CNetOrder 45 each (= 20+25)

Absent entirely: `CUnitRadar2`, `CVehicleBehavior3`, `CRouter3`,
`CTaskScheduler2`, `CFuzzyStateMachine2`.

**CORRECTED 2026-08-18 (user's catch): these are probably NOT WoV leftovers.**
WoV predates TvT, so WoV-era code would be the *unnumbered* generation. The
numbered classes are more likely a **newer generation built during TvT's
development and never switched on** — which fits the game being released
unfinished when Lighthouse went bankrupt.

Capability comparison supports this:

| class | virtuals | vtables | geometry interfaces |
|---|---|---|---|
| CRouter@router (live) | 15 | 1 | none |
| **CRouter3** (dead) | **84** | **11** | IRealGeometryUser |
| CTaskScheduler2 (dead) | 89 | 11 | IRealGeometryUser |
| **CUnitRadar2** (dead) | **88** | **11** | IRealGeometryUser + IGeometryGroupUser |

Not uniform though: `CUnitGroup2` (52 vf) and `CRouterMap2` (42 vf) are *simpler*
than their unnumbered counterparts, so "numbered = better" is not a clean rule.

**OPEN AND IMPORTANT:** `CUnitRadar2` is a dedicated vision class holding two
geometry interfaces that the live vision path never uses. If its code performs a
real line-of-sight query, TvT contains an unfinished LOS system that merely needs
activating, rather than one that must be built. **Not yet established** — the
interfaces show intent, not behaviour. A `D3DXVec3Normalize` hit in its call
closure looked promising but is worthless as evidence: that helper has 13 callers
across the DLL and the closure included one level of callees.

**Done 2026-08-18.** 78 vtable entries, 13 real methods (65 thunks/tiny).
Two matter:

- `FUN_10176f40` (+0x176F40) — setup. Stores a pointer at `+0xCC` and
  runtime-validates the geometry interfaces, with these literal error strings:
  `"%s: Self IPositionable is NULL"`,
  `"%s: WorldGeometry interface pointer is NULL"`,
  `"%s: GeometryGroup interface pointer is NULL"`.
  So the class genuinely *holds* those interfaces, not merely declares them.
- `FUN_10178a70` (+0x178A70, 591 bytes) — reads a transform matrix (offsets
  0xc/0x1c/0x2c) and calls **D3DXVec3Normalize** on 3-float vectors. Real 3D
  eye/direction maths, versus the live path's `D3DXVec2Normalize`.

**Still NOT shown:** an actual ray-cast / intersection query against world
geometry. The indirect calls in `FUN_10178a70` go via vtables at `+0x54` and
`-0x18`; neither has been resolved to the geometry pointer at `+0xCC`.

**Next step:** resolve those indirect calls, or set a watchpoint on the
geometry-interface pointer field in a `CUnitRadar2` — except nothing instantiates
the class, so it would have to be constructed artificially or the call sites
traced statically.

### Geometry usage CONFIRMED in CUnitRadar2 (2026-08-18)

Field offsets, from `FUN_10176f40` disassembly (`MOV ESI,ECX` => ESI is this):

| offset | holds |
|---|---|
| +0x78 | Self `IPositionable` |
| **+0x80** | **`WorldGeometry`** |
| **+0x84** | **`GeometryGroup`** |
| +0xCC | pointer stored at setup |

Only two methods touch them: `FUN_10176f40` (setup/validate) and
**`FUN_10180480`** (+0x180480, 1461 bytes) — the scan routine:

    10180501  LEA ECX,[EBX + 0x80]     ; WorldGeometry
    1018050c  CALL 0x100c7180          ; null check
    10180513  JNZ 0x10180a24           ; bail out if null
    10180519  LEA EDI,[EBX + 0x84]     ; GeometryGroup
    1018052d  JNZ 0x10180a24           ; bail out if null
    ...
    10180740  LEA EAX,[EBX + 0x80]     ; &WorldGeometry
    10180746  PUSH EAX                 ; passed as an argument
    10180750  CALL dword ptr [EDX + 0x14]

**It refuses to run without both geometry interfaces, then passes WorldGeometry
into a virtual call.** That is real consumption of world geometry by a vision
class — something the shipped vision path (`FUN_100c9e50`, 2D dice roll) never
does.

**`[EDX+0x14]` RESOLVED 2026-08-18 — and it is NOT an occlusion query.**

`this+0x18` is an embedded member, not the this_offset=24 base I first assumed.
Its vptr is written by the constructor at `1017e1c3`:
`MOV dword ptr [ESI + 0x18],0x102577d4`. Slot[5] of vtable `0x102577D4` is
`FUN_1017F7B0`.

    FUN_10180480 (scan; early-outs unless WorldGeometry + GeometryGroup valid)
      -> slot[5] of 0x102577D4 = FUN_1017F7B0  (bool wrapper, conditional retry)
        -> FUN_1017F470 (727 bytes)            = TYPE-MASK FILTER

`FUN_1017F470` iterates records comparing a ushort type-ID at +4 against an
array, treats `0x1001` as a wildcard, and builds filtered lists. That is
classificator/mask matching — plausibly what `PermanentMaskChecks` governs — not
a ray cast or intersection test.

**So: no occlusion query found.** `&WorldGeometry` is passed into that call, but
the resolved callee does mask comparison. Whether any *other* part of
`CUnitRadar2` performs a geometry trace is still unknown; only the
`FUN_10180480` path has been traced.

Wrong turns on the way, do not repeat: slot[5] of vtable `0x10257844`
(this_offset=24) resolves to `FUN_10005DB0`, a 4-byte `return this+4` accessor
(GetName) — that was the wrong vtable.

### All CUnitRadar2 methods scanned (2026-08-18) — no occlusion test inside

11 methods >= 60 bytes. Zero hits for Intersect / Trace / Ray / sqrt / Height /
Terrain / D3DXPlane. Only `FUN_10178A70` (591 b) has 3D maths — `D3DXVec3Normalize`
on direction vectors from a transform matrix, i.e. orientation, not intersection.

**Conclusion: `CUnitRadar2` is geometry-PLUMBED, not geometry-QUERYING.** It holds
`WorldGeometry`/`GeometryGroup`, guards on them, and passes them onward, but casts
no rays itself.

**Remaining loose end (the right next step):** `WorldGeometry` is an *interface* —
calls through it dispatch into `Objects.dll` (where `CStaticTerrain` lives), which
is invisible from `Behavior.dll`. Import `Objects.dll` into the Ghidra project and
enumerate what `IWorldGeometry` actually offers. If it exposes an
intersect/trace/lineOfSight method, occlusion was reachable; if it only offers
height/terrain lookups, it never was.

### THE MISSING CONNECTION — found 2026-08-18 (user's question)

**The v2/v3 tier is registered and instantiable; nothing creates it because no
script names it.** Selection happens in the `.script` layer, not the engine.

Behavior.dll registers component ids for the whole new tier:
`CID_VehicleBehavior3`, `CID_UnitRadar2`, `CID_Router3`, `CID_TaskScheduler2`,
`CID_RouterMap2`, `CID_UnitGroup2`, `CID_FuzzyStateMachine2`,
`CID_VehicleKinematicController2`.

Script references to each:

| component | refs in Scripts\ |
|---|---|
| `VehicleBehavior` | 18 |
| `HumanBehavior` | 9 |
| `VehicleBehavior3` | **0** |
| `UnitRadar2` | **0** |
| `Router3` | **0** |
| `TaskScheduler2` | **0** |

The selection syntax is `new #<NativeComponent><CScriptParamClass>()`:

    Units\TankPzVIAusfEUnit.script:1378
        SetupBehavior( new #VehicleBehavior<CTankPzVIAusfEBehavior>());

**Switching is a one-word edit** — `#VehicleBehavior3`. 17 unit scripts use
`new #VehicleBehavior<`.

**The mechanism is proven, not theoretical:** TvT's own scripts already
instantiate numbered generations elsewhere —
`Common\Cockpit.script:295 new #MessageBar2<...>` and
`Common\Cockpit.script:391 new #TargetPointer3()`.

**Next experiment (sandbox only, never live):** change the Tiger's line to
`#VehicleBehavior3`, clear `Cache\Scripts.cache`, load a mission, read
`execution.log`. Three possible outcomes, all informative:
 1. loads and behaves -> the new tier runs, and `CUnitRadar2` may come with it
 2. clean script error -> tells us exactly what v3 expects that v1 does not
 3. crash -> v3 needs sibling components (router3 / radar2) wired too

Test on Campaign_1 Mission_2 (67.92% forest) so any vision difference is visible.

### Objects.dll HAS ray intersection — occlusion was always reachable (2026-08-18)

Imported `Objects.dll` and enumerated its geometry vocabulary. It contains a full
ray/shape intersection system:

    CCheckRayIsectionsProc      CStaticIntersector      IShapeIntersector
    CEnumRayIsectionsProc       CDynamicIntersector     IStaticIntersector
    CIsectionWithRayProc        IRealGeometry           IDynamicIntersector
    CIntersectionBoxBox         IRealGeometry2
    CIntersectionBoxCapsule     CID_StaticIntersector   (registered component)
    CIntersectionBoxTriangle    CID_DynamicIntersector  (registered component)
    CIntersectionCapsuleTriangle

**Conclusion: ray-vs-geometry queries exist, are implemented, and are registered
components.** Line-of-sight was never beyond this engine. The shipped vision path
(`FUN_100c9e50`, 2D dice roll) simply never calls any of it, and `CUnitRadar2` —
which holds the `WorldGeometry` pointer that would feed it — is never
instantiated.

So foliage occlusion is a *wiring* problem, not a capability problem. Note also
`IRealGeometry2` exists alongside `IRealGeometry` — the same unfinished-newer-tier
pattern again.

### Version families (RTTI, Behavior.dll)

    CVehicleKinematicController  v1, v2, v3
    CRouter                      v1, v3
    CVehicleBehavior             v1, v3
    CRouterMap                   v1, v2
    CUnitGroup                   v1, v2
    CHumanKinematicController    v1, v2
    CUnitRadar                   v2 ONLY  (no CUnitRadar, no CUnitRadar3)

`CUnitRadar3` appears 0 times in the binary. Vision has exactly one class,
numbered 2 — consistent with it being the extracted replacement for the vision
still embedded inside v1 `CVehicleBehavior`. The unfinished generation looks like
`CVehicleBehavior3` + `CUnitRadar2` + `CRouter3`.

**Balance of evidence:** strongly favours the unfinished-newer-generation reading.
A dedicated vision class that holds world-geometry interfaces and does 3D maths is
what a real LOS system looks like; the shipped one is a 2D dice roll. But
"designed for geometry" is one step short of "performs occlusion" — do not state
the stronger claim publicly until that call is resolved.

**Vision belongs to the behaviour classes.** Proven by call chain: radar-parameter
loader `FUN_100cbfb0` <- `FUN_100cc620` <- `FUN_100334e0`, and `FUN_100334e0`
occupies **slot[5] of the `this_offset=12` vtable** of `CAbstractBehavior`,
`CHumanBehavior`, `CPrimitiveBehavior`, `CVehicleBehavior`, `CVehicleBehavior3`.

## Key addresses (RVA from ImageBase 0x10000000)

| what | RVA |
|---|---|
| `CVehicleBehavior` primary vtable | `0x257F84` |
| `CHumanBehavior` primary vtable | `0x24E73C` |
| `CUnitRadar2` primary vtable (dead) | `0x2578F8` |
| radar-parameter loader | `0x0CBFB0` |
| its caller | `0x0CC620` |
| vtable slot[5] entry point | `0x0334E0` |

Radar fields *within the parameter object*: `PermanentMaskChecks` +0x18,
`ZAxisRadar` +0x19, `SpecVisibilityCheck` +0x1a (all bool, same accessor).

## SOLVED — the radar parameter block

**Base offset `+0x8F4` from the start of a `CVehicleBehavior` / `CHumanBehavior`
object.** Confirmed in-game across five live instances, 2026-08-18.

Derivation: `10033ca7  LEA ECX,[EDI + 0x8e8]` then `CALL FUN_100cc620`, and
`100334fb  MOV EDI,ECX` proves EDI is `this`. But `FUN_100334e0` is dispatched
through the **`this_offset=12`** vtable, so its `this` is `object + 12`. Hence
`object + 12 + 0x8E8 = object + 0x8F4`. Reading at `0x8E8` gives 52 for
SpecVisibilityCheck; reading at `0x8F4` gives 1, which is correct.

| block off | abs off | type | field | verified value |
|---|---|---|---|---|
| +0x00 | +0x8F4 | int/bool | HasRadar | 1 |
| +0x04 | +0x8F8 | float | MaxRadarDistance | 1200.0 (unit override) |
| +0x08 | +0x8FC | float | MinRadarDistance | **5.0 = script** |
| +0x0C | +0x900 | float | MaxRadarAngle | 180.0 (degrees) |
| +0x10 | +0x904 | int | UpdateRadarPeriod | **3000 = script** |
| +0x14 | +0x908 | int | UpdateRadarPeriodRandAdd | **1000 = script** |
| +0x18 | +0x90C | bool | PermanentMaskChecks | **0 = unset in script** |
| +0x19 | +0x90D | bool | ZAxisRadar | 0 |
| +0x1a | +0x90E | bool | SpecVisibilityCheck | **1 = script true** |

Five fields match script values exactly, which is what makes this solid rather
than suggestive.

## ANSWERED — AI vision has no occlusion, and never did

**`FUN_100c9e50` (Behavior.dll +0x0C9E50) is the whole visibility model.** Found
2026-08-18 with a hardware watchpoint on `object+0x90E`: 36 hits, exactly one
reader, at `+0x0C9E6E` (`TEST AL,AL` / `JNZ`), entirely inside Behavior.dll.

    if (*(char *)(param_1 + 0x1a) == ' ')   // SpecVisibilityCheck off
        return 1;                            // always visible, no test

`param_1` is the radar block, confirming the +0x8F4 layout independently.
When the flag is set it computes a probability as the product of:
  - a base from block +0xE0 / +0x110
  - a lookup indexed by a virtual call (target state/type)
  - an angle term via **D3DXVec2Normalize** (2D!)
  - a loop over 28-byte records at +0x104..+0x108
then `pow(1.0 - p, n)` against a random roll (`FUN_1018bc30 / _DAT_10246260`).

**Conclusion: vision = distance x angle x state x mask, then dice.** No ray cast,
no terrain query, no line-of-sight, no foliage. Two independent reasons:
1. The direction maths is **2D** — occlusion is impossible without height.
2. The watchpoint found no reader outside Behavior.dll; `Objects.dll` (where
   CStaticTerrain lives) is never consulted.

This explains why `PermanentMaskChecks` did nothing: there is no occlusion path
for it to switch. `SpecVisibilityCheck` only chooses between "always visible" and
"roll the dice".

**Limit on the claim:** a few virtual calls in that function are unresolved,
e.g. `(**(code **)(*(int *)*unaff_retaddr + 0x1c))()`. Strong evidence, not
formal proof.

**If foliage occlusion is ever wanted it must be BUILT, not fixed** — a new 3D
geometry query injected into this function. That is a feature, not a bug fix.

## Superseded: why the static search could not answer it

The ViewProbability arrays and any geometry/occlusion check are NOT in this
block. `MaxRadarAngle = 180.0` plus the distances are pure cone-and-range inputs;
nothing here references world geometry. The open question is what *consumes*
`SpecVisibilityCheck` (+0x90E) and whether that path touches forest geometry.

**Static offset search: done, negative (2026-08-18).** Searched all 609,460
instructions for the block base `0x8E8` -> exactly one hit, the loader's own
`LEA`. Widened to the whole field window `0x8E8-0x912` -> 25 functions, but only
`FUN_10016b70` belongs to the behaviour classes, and it merely writes a pointer
at `+0x8EC` (sets and nulls it — lifetime management, not vision). The other 24
are offset collisions in unrelated classes.

**Why it cannot work:** a consumer loads the block base into a register once and
then reads `[reg+0x1a]`. That displacement occurs thousands of times and carries
no class information. The distinctive `0x8F4` only ever appears at the single
site that computes the base. There is nothing further for an offset search to
find — do not repeat this search.

**Use a hardware watchpoint instead.** Set a debug-register (DR0-DR3) read
breakpoint on `object + 0x90E` for one live `CVehicleBehavior`, with a vectored
exception handler logging the faulting EIP. Watches an address, so it is immune
to the offset-collision problem. The probe already locates instances, so this is
an increment on existing code.

**Decision criterion:** does the consuming code path call into `Objects.dll`
(where `CStaticTerrain` and the geometry classes live)? If AI vision never
crosses into `Objects.dll`, foliage occlusion was never implemented — which
answers the years-old question, just not favourably.

**Do NOT identify fields by matching known values** — tried and it produced false
positives. `+0x0F0` matched `ViewProbabilityByPreviousStep = 2.0` in a vehicle,
but infantry show `50.0` there while script sets 2.0 for both. Values like 2.0,
12.0, 1000.0 are far too common. Get offsets from disassembly instead.

Observed but unconfirmed: `+0x100` reads `1000.0` in both classes, consistent
with `MaxRadarDistance` — but both inherit 1000 from `CBaseGroundBehavior`, so it
does not discriminate.

## Method notes (mistakes worth not repeating)

1. A multiple-inheritance class has many vtables — `CUnitRadar2` has eleven. Only
   `this_offset == 0` identifies an object's start.
2. Exclude the probe's own thread stack or it matches its own locals.
3. **Always include a control.** A scan that can only report absence cannot tell
   "not there" from "not looking properly". The census was added only after two
   inconclusive runs; it should have been there first.
4. Ghidra headless: multi-line `println` only prefixes the first line, so do not
   filter output with `Select-String` — capture everything to a file.
5. `cmd /c build.bat` hangs when run from the Bash tool; use PowerShell.

## Build

    powershell -c "& cmd /c 'K:\tvt_probe\build.bat'"

x86 MSVC via `L:\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat`.
Must be 32-bit to match the engine. Log goes to
`M:\TvT_INJECT_SANDBOX\tvt_probe.log`.

## Test instrument

Any AI-vision test must run on **Campaign_1 Mission_2** (67.92% forest) or
Campaign_2 Mission_4 (63.94%). Berezov and the steppe maps are 9.17% and cannot
show the effect. The Editor cannot test AI at all — it loads missions but never
runs the behaviour classes.

---

## OUTCOME, 2026-08-20: the intersector was NOT used

The line-of-sight work is finished and did **not** use any of the geometry
system catalogued above. It hooks the live vision function
(`Behavior.dll + 0xC9E50`) and does the geometry itself, marching the mission's
own `hmap.raw` and zone bitmaps.

Neither `CStaticIntersector` nor `CUnitRadar2` is touched, for two reasons:

- `CUnitRadar2` was traced here and found **geometry-plumbed, not
  geometry-querying** - it holds `WorldGeometry`/`GeometryGroup`, guards on them
  and passes them onward, but the path followed ends in classificator/mask
  matching rather than a ray cast. Reaching it would also mean switching the
  whole unit roster to `#VehicleBehavior3`.
- `CStaticIntersector` would still need wiring from scratch, and a heightfield
  march is cheaper than ray-triangle work while covering terrain and foliage in
  one pass.

**The right conclusion from this document is that G5 intended occlusion and ran
out of time - not that the capability was sitting there ready to switch on.**
The earlier framing of "occlusion is a wiring problem, not a missing capability"
was a hypothesis, and it is not what happened.

See `Documentation/TvT_Line_Of_Sight.md` and
`Documentation/RE/TvT_Vision_Model_Decoded.md`.
