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
