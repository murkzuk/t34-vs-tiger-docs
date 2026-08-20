# What TvT's AI decides with, and what it ignores

*2026-08-19. Two findings from the same session as the line-of-sight work, both
established by experiment rather than reading. The first settles who the vision
hook actually governs; the second is a design flaw the game's own data is
already equipped to fix.*

Companion to [TvT_Line_Of_Sight.md](TvT_Line_Of_Sight.md) and
[RE/TvT_Vision_Model_Decoded.md](RE/TvT_Vision_Model_Decoded.md).

---

## 1. The player's crew is not the AI

### The experiment

Occlusion was denying 74% of the engine's positive sightings on
Campaign_2/Mission_5, and the game still looked stock from the cockpit. Three
explanations were chased and all three were wrong:

- **The visibility cache has a third reader** outside the vision function, at
  `0x100cacb5`. It looked like a bypass. It writes `0xBF800000` — that is
  `-1.0f`, a cache *invalidate*. Not it.
- **Intermittent denial**, where a target refused 74% of the time is still
  spotted within ten seconds. Also not it: **177 of 207 observer/target pairs
  were denied every single time**, and three quarters of denials were total.
- **Tuning.** No.

So the hook was set to `deny_far` with `deny_beyond = 1` — refuse every sighting
past one metre. Total blindness, no model, one question.

### The result

```
mode = deny_far
  will refuse every sighting beyond 1 m
--- 10000 calls, 7448 seen, 7448 denied by LOS
```

**Every AI unit fell silent. The player's own gunner carried on firing
normally.**

### Why

The player's tank appears in the hook's log **53 times as a target and never
once as an observer**. `FUN_100c9e50` governs AI units looking at things. The
player's crew does not use it at all — it runs on `CAutoShooter` and
`CAutoCommander` in `Scripts\Common\`, which carry their own radar:

```
CAutoShooter     RadarMaxDistance = 3000.0f   RadarUpdateTime = 2.0f
CAutoCommander   RadarMaxDistance = 1500.0f   RadarUpdateTime = 1.0f
```

**Two separate vision systems.** Every observation about "the AI" from the
cockpit has to say which one it means. A report that occlusion changed nothing
may be a correct observation about the wrong crew — which is exactly what
happened here, twice, before the blindness test settled it.

The lesson generalises: when a change is measurably taking effect and visibly
doing nothing, stop reasoning and build the crudest experiment that can only
have two outcomes.

---

## 2. `RadarMaxDistance` is the wrong question

The AI's engagement gate today is a distance:

```
is the target within RadarMaxDistance?
```

It has no relationship to whether the shot can accomplish anything. The
question a gunner actually asks is:

```
at this range, with this ammo, against the facet it is showing me,
can I get through?
```

**TvT can already answer that.** Both halves have been in the files since 2001:

| file | holds |
|---|---|
| `Common\Piercing.script` | penetration vs range, per ammo type, per gun |
| `Common\Armour.script` | armour thickness per facet, per vehicle |

Penetration is stored as a normalised curve times a power:

```
TankPzVIAusfECalibrePenetrationPower      = 120.0 / 100.0
TankPzVIAusfECalibrePenetrationByDistance = [[100, 120/120, 2000, 84/120],
                                             [[500, 110/120], [1000, 100/120],
                                              [1500, 93/120]]]
```

— 120 mm at 100 m falling to 84 mm at 2000 m. Armour is `[thickness_mm, …]` per
facet, separately for turret and hull, front / rear / left / right / top /
bottom.

### What the data says, unprompted

`Tools/LineOfSight/can_i_kill.py` reads both files and subtracts. Positive
means it goes through; negative means it bounces.

**T-34/76 vs Tiger** — the defining matchup of the game's own title:

| facet | 100 m | 500 m | 1000 m | 2000 m |
|---|---|---|---|---|
| front 108 mm | −28 | −38 | −45 | −55 |
| **flank 72 mm** | **+8** | −2 | −9 | −19 |
| rear 82 mm | −2 | −12 | −19 | −29 |

A T-34/76 can kill a Tiger in exactly one circumstance: a side shot inside
roughly 300 m. Not the rear, not at range, never from the front. That is why
Soviet crews closed to knife range, and nobody tuned these numbers to say so.

**T-34/85 vs Tiger** — front impenetrable past 100 m, flank good at 1000 m.

**Tiger vs T-34/85** — turret front out to about 1500 m, everything else at any
range.

**PzIV vs T-34/85** — turret front only inside 500 m; hull and flanks
throughout.

### Why it matters more than a tuning change

`RadarMaxDistance = 3000` tells a T-34/76 to engage a Tiger at two kilometres,
where the armour tables guarantee it cannot achieve anything. Replace the cap
with the penetration question and the behaviour that falls out is the historical
one: T-34s closing hard and working for flanks, Tigers content to stand off.

**Nobody has to script that.** It emerges from numbers already in the files —
the same shape as the line-of-sight work, where the fix was a multiplier the
designers never wrote rather than a system that had to be invented.

### What it would take

The arithmetic is done and runs today. The missing input is **which facet is
presented**, i.e. the relative angle between shooter and target. The engine has
it; the script layer's `CAutoCommander.PreferedTargets` weights only by
classificator and distance:

```
[ [ ["TANK"], [] ], [ [1000.0, 100.0], [0.0, 1000.0] ] ]
```

So this is the same job as the vision hook: find where target selection
happens and give it the penetration question in place of a range test. That
technique is now proven, and both crews' entry points are known — `FUN_100c9e50`
for AI units, `CAutoShooter`/`CAutoCommander` for the player's.

### Provenance

The *idea* is Panzer Elite's: engagement decided by whether the round can defeat
the armour, not by a visibility radius. The *data* is entirely TvT's. Nothing
transfers between the two but the design — they share no engine, no format and
no code.

---

## 3. The player's crew now has line of sight too

*2026-08-20. Section 1 established that the player's crew is a separate vision
system the AI hook never touched. This closes it.*

### The classes, and the offsets that had to be measured

The RTTI names carry a `Component` suffix, which is why an earlier search found
nothing:

| script class | native class | primary vtable RVA |
|---|---|---|
| `CAutoShooter` | `CAutoShooterComponent` | 0x249258 |
| `CAutoCommander` | `CAutoCommanderComponent` | 0x248D98 |

Its per-tick update is **vtable slot 7, RVA 0x4B1E0** — 1283 bytes,
`void __fastcall(this, edx, arg)`, `ret 4`.

Field offsets **measured on a live object**, after being deduced wrongly twice:

| offset | value | |
|---|---|---|
| +0x154 | 3000.0 | `RadarMaxDistance` |
| +0x158 | 0.2094 | `ViewAngle`, 12 deg in radians |
| +0x1CC | 1500.0 | the commander's radar, on the same object |

Not +0x144/+0x148. Those come from the property loader, whose writes go through
EDI — and that same function writes `CWeaponDescriptor`'s vtable to `[EDI]`.
EDI is a descriptor the component holds, not the component. Searching the live
object for values the script sets found the truth in one run.

### The gate

```asm
1004B3FC  lea ecx, [esp+0x38]     ; delta to the candidate
1004B400  call 0x1000ef80         ; length(delta)
1004B405  fstp [esp+0x1c]
1004B409  fld  [esi+0x154]        ; RadarMaxDistance
1004B40F  fcomp [esp+0x1c]
1004B418  jne  ...                ; too far -> candidate skipped
```

The whole of the player gunner's target acceptance: one distance comparison, no
geometry.

**It is gated on a UI flag.** The update only reaches that code when a virtual
on the `CTankAutoThingControl` at `[esi+0x5c]` returns true — and that virtual,
in `UI.dll`, is nothing but:

```asm
mov al, byte ptr [ecx+0x9cd]
ret
```

One boolean, which reads true when the commander has given the gunner a target.
Four hypotheses about that flag were wrong (a timer, the auto-gunner, the
auto-commander, the seat) before it was simply read.

### The fix: redirect the call site, not the function

`0x1000EF80` is a generic 3D vector length with **80 callers**, so hooking it
was out. Redirecting the single `call` at `0x1004B400` touches five bytes at one
address and nothing else in the engine.

The filter runs the march and returns a huge length when the line is blocked;
the engine's own comparison then discards the candidate. No new logic in the
engine at all.

**Finding the endpoints without hardcoding stack offsets.** The observer and
target sit in the caller's frame as plain world coordinates. Rather than assume
their offsets — deduced offsets had already been wrong four times on this
problem — the filter searches a window of that frame for the pair whose
difference equals the delta it was handed. Self-validating: no wrong pair can
satisfy the arithmetic.

### Measured

```
--- gate: 6000 checks, 4069 refused, 0 unmatched
[GATE] REFUSED (4706.7,3264.5) -> (4562.5,3808.2) at 562 m, foliage, 83% masked
```

**68% refused, and the endpoint search never failed once in 6000 checks.** No
access violations; the AI hook ran alongside unaffected.

### What it is and is not worth

In the commander's seat you can only designate what you can already see, so this
does not change acquisition. What it changes is **retention**: the line is
re-tested every tick, so a target that moves behind a crest is now lost instead
of being tracked through it.

Acquisition through terrain belongs to `CAutoCommanderComponent`, which does the
designating whenever the player is *not* in the commander's seat. That is the
next target, and its vtable is already known.

## Wingmen: Follow and Formation are issued together and must agree

`CWingmanTask::Wingman_Follow()` in `Common\BaseTasks.script` issues **two
movement orders on the same tick**:

```
SetOrder_Follow   (leader, FOLLOW_DISTANCE_MIN/OPT/MAX, ...)
setOrder_Formation(leader, GetFormationVector(),
                   FORMATION_DISTANCE_OPT/MAX, ...)
```

Follow holds a **distance**. Formation holds an **offset vector**. Nothing
reconciles them, so if the vector's length disagrees with
`FOLLOW_DISTANCE_OPT` the unit is dragged between two targets every update.
In play this reads as continuous micro-stuttering, with the spacing settling
near the tighter of the two rather than the one you set.

**Rule when authoring or tuning any wingman:**

- `|GetFormationVector()|` should be about `FOLLOW_DISTANCE_OPT`
- `FORMATION_DISTANCE_OPT` / `_MAX` should match `FOLLOW_DISTANCE_OPT` / `_MAX`
- check the **longest** vector in `FORMATION_VECTORS` against `_MAX`, not the
  first one

### The stock numbers are helicopter numbers

REDUX still carries them untouched, straight from Whirlwind over Vietnam:

```
FOLLOW 180 / 200 / 220
FORMATION_VECTORS = [ new Vector(200, 120, 30), new Vector(200, -120, 30) ]
```

That `z = 30` is **altitude** — wingmen thirty metres up. They at least agreed
with each other (opt 200 against a vector length of 233). Anyone adding a
wingman to REDUX must fix this block and zero the z, or the tank is being told
to fly.

### ZW, found and fixed 2026-08-20

ZeeWolf correctly rewrote the block for tanks but the two orders stopped
matching — an 11 m formation slot against a 10 m minimum follow distance, so
the commanded position sat right on the "too close, brake" threshold.

| | before | after |
|---|---|---|
| follow min / opt / max | 10 / 20 / 60 | 25 / 40 / 110 |
| formation opt / max | 20 / 60 | 40 / 110 |
| slot distance | 11 m | 40 m |

The formation shape was preserved exactly: every vector scaled by the same 3.6.

### Unused, and broken if it were used

`Common\KameradTask.script` (ZW only). `CKamerad2Task::Init()` sends the event
`move2Player`, but that class defines only `move2Player2`, `move2Player3` and
`move2Player4` — so those wingmen would never start following. Referenced only
by `KurskMission2` and `KurskMission3`.
