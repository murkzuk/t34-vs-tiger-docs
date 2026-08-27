# Penetration tables — REDUX vs ZW, and the realism question

Measured 2026-08-26 from each build's `Scripts/Common/Piercing.script`.

## REDUX's numbers are the real historical figures

```
                    100m   500m  1000m  1500m   drop
Tiger I 88 KwK 36    120    110    100     93    22%
T-34/85 85mm         115    105    100     92    20%
Pak 40 75mm          135    135    120    100    26%
Panzer IV 75mm        98     91     82     72    27%
T-34/76 76mm          80     70     63     58    28%
ZiS-3 76mm            80     70     60     50    38%
```

The real 8.8 cm KwK 36 firing PzGr 39 at 30 degrees is **120 / 110 / 100 / 91**.
REDUX reads 120 / 110 / 100 / 93. **Somebody typed in real data.** Every gun
tapers 20-55%, and APCR falls faster than standard AP — correct, since
sub-calibre sheds velocity quickly.

## ZW's model: big guns don't lose power

```
                    100m   500m  1000m  1500m   drop
Pak 43 88 L/71       247    247    247    247     0%
Pak 43 APCR          267    267    267    267     0%
Tiger I 88           175    175    175      -     0%
Panther 75           165    165    160    156     5%
T-34/85              145    145    143    136     6%
-----------------------------------------------------
Pak 40                95     85     63     55    42%
Panzer IV 75          95     85     63     55    42%
Panzer III L60        50     50     40     29    42%
T-34/76               65     60     43     23    65%
```

## It is NOT a nationality bias - checked

```
                heavy (>=140mm)        light
German          10% drop  (n=11)       45% drop  (n=9)
Soviet          14% drop  (n=4)        55% drop  (n=6)
```

German and Soviet heavies are both flat; German and Soviet lights both fall off
a cliff. The German Pak 40, StuG 40, Panzer IV and Panzer III drop 42-67%, as
steeply as anything Soviet. **The split is by gun size, applied fairly evenly.**
Recorded because "ZW favoured the Germans" is the natural assumption and the
data does not support it.

## ZW is not only missing falloff - its close-range values are inflated

```
                    ZW           REDUX / real
Tiger I 88          175 flat     120 -> 110 -> 100 -> 93
T-34/85             145 -> 136   115 -> 105 -> 100 -> 92
Panzer IV 75         95 ->  55    98 ->  91 ->  82 -> 72
```

Heavies are **25-45% high at 100 m** in ZW. So "add realistic falloff" and "make
it realistic" are different jobs.

## THE DECISION (open - user wants realism, route not yet chosen)

**Option A - adopt REDUX's tables** for every gun in both builds. Genuinely
realistic, internally consistent, numbers already proven in play. But ZW's
Tiger 88 drops 175 -> 120 at point blank and every engagement in that build
changes.

**Option B - keep ZW's power levels, add realistic decay.** Far less
disruptive; range starts mattering and nothing suddenly becomes weak. Still
unrealistic up close.

**ZW-only guns need sourcing either way** - Pak 43, Flak 88, Panther 75 L/70,
KV-85, KV-1, KV-1S, SU-122, SU-152, sIG 33, Nashorn, Hummel, Wespe, Marder II,
StuG F8, Sturm-Haubitze, Pz II, Pz III L24. No REDUX equivalent exists, so these
need historical figures found and shown before anything is applied.

## Consequence for the King Tiger

Its gun is `GunHvyPaK43`, which is flat. **Do not fix that one gun alone** - it
would make the King Tiger the only heavy in ZW that weakens with range, in a
build where the Tiger I's 88 does not. Either leave it flat (consistent with its
siblings) or change the whole table as part of a considered pass.

See `TvT_Unshipped_Content.md` for the King Tiger itself.

---

# CORRECTION 2026-08-26: ZW's bias is REAL — it is in handling and gunnery

An earlier section of this document said the flat penetration tables were "not a
nationality bias" and that the user's read was unsupported. **That conclusion was
drawn from the penetration table alone and was wrong about the wider picture.**

The user maintained ZeeWolf had a bias. Compared class-for-class against the
**untouched 2001 original**, they are right and it is not subtle.

## The control: REDUX *is* the original

On these fields REDUX is the 2001 release essentially untouched — the only
difference found across three tanks is the Tiger's `MaxPower`, 1600 -> 1500,
which is a REDUX *nerf* to the Tiger. So "REDUX vs ZW" is genuinely
"original vs ZW".

## AI main-gun accuracy (`FireDeviation`, lower = more accurate)

```
                    ORIGINAL      ZW
Tiger  AI gun         1.2    ->  0.05      24x MORE accurate
T-34/85 AI gun        1.25   ->  1.55      24% LESS accurate
T-34/76 AI gun        1.5    ->  1.6        7% LESS accurate
```

## Player main gun

```
Tiger  player gun     0.005  ->  0.005     unchanged - still pinpoint
T-34/85 player gun    0.005  ->  0.15      30x LESS accurate
```

**Play the Tiger in ZW and you shoot exactly as G5 intended. Play the T-34/85
and you are thirty times less accurate.**

## Mobility and sensors

```
Tiger      MaxSpeed        2200  ->  2730     +24%
           Mass           56000  -> 40000     29% LIGHTER (real Tiger I is 57 t)
           MaxRadarDistance 1500 ->  2600     sees 1.7x further
           AttackDistanceMax 1000 -> 2600     engages 2.6x further
           FirePeriod      12000 ->  7000     fires 1.7x more often
           FirePeriodRandAdd 8000 -> 2000     far more consistent
T-34/85    DirectionSpeedH    17 ->     8     turret traverse HALVED
           Mass            40000 -> 48000     heavier
T-34/76    DirectionSpeedH    36 ->     7     turret traverse cut 5x
```

## The measurement trap that nearly produced a wrong answer twice

A first pass grepped the **first** `FireDeviation` in each file and reported
T-34/85 going 0.005 -> 0.15. A second pass reported 0.15 -> 0.005. Both were
"right" and both were useless: **a unit file contains separate gun classes for
the AI and the player** (`CTankT34_85_44Gun` vs `CTankT34_85_44PlayerGun`), each
with its own value. Always compare per class.

## What this means for the realism work

The penetration pass is now the *second* priority. **Restoring ZW's handling and
gunnery to the original values is simpler, better evidenced, and fixes the thing
that is actually felt in play** - it is a revert to G5's numbers rather than a
rebalance, so there is no design judgement to make.

## DECIDED 2026-08-26: adopt G5's original accuracy values

The user asked the right question - *is 1.2 accurate, or is this reverting for
the sake of it?* - and then accepted G5's figures. Recording **why** that is
sound, so it is not reopened.

**`FireDeviation` is a GAMEPLAY parameter, not a ballistic one.** Three tells:

1. **Machine guns are 0.15, cannons 1.2-1.5.** Physically backwards - a real MG
   scatters far more than a tank gun. So nobody was modelling dispersion.
2. **Player 0.005 vs AI 1.2 on the SAME weapon.** The player supplies aiming
   error through the sight, so the gun must be near-perfect; the AI aims
   perfectly by definition, so it needs artificial imprecision or it never
   misses. Two problems, two numbers.
3. **The AI tiering is a 20% band** - 1.2 for Tiger / StuG III / SU-85, 1.25 for
   T-34/85, 1.5 for the rest. A modest nod to better platforms and optics.

So **1.2 should not be defended as historically accurate** - it is not that kind
of number. What is defensible is the *relationship*: G5 put all AI gunners
within 20% of each other, with a small edge to the better platforms, which
matches reality (German TZF optics and 1943 crew training were genuinely better,
worth perhaps 10-30% in first-round hit chance - not 31x).

```
G5     Tiger 1.2   vs  T-34/85 1.25      4% apart
ZW     Tiger 0.05  vs  T-34/85 1.55     31x apart
```

ZW's 0.05 is not a tuned AI value at all - it sits in the *player/MG* band. He
promoted the AI Tiger to player-grade accuracy and left the AI T-34s alone.

**Decision: restore G5's values.** They are a designed, shipped, playtested
system. This keeps the work a straight revert with no design judgement.

### Still unmeasured, if rigour is ever wanted

**What 1.2 means in metres.** The units are unknown without engine source. It is
measurable: park an AI tank at a known range, let it fire ~20 rounds at a static
target, record the spread. That would convert this from ratios into "groups X
metres at 1000 m", checkable against Wa Pruef trial data. Not needed for the
revert; needed only if the values are ever to be re-derived from history rather
than inherited.

---

# THE FULL SWEEP, 19 shared units — the bias is systematic

Compared **class-by-class** against the untouched 2001 original, 2026-08-26.
141 fields differ across the 19 units present in both builds.

## AI main-gun accuracy (`FireDeviation`, lower = more accurate)

```
side     unit          class                  ORIGINAL      ZW      change
German   Pak 40        CGunPak40Gun               1.5      0.5      3x better
German   Panzer IV     CTankPzIVGGun              1.5      0.10    15x better
German   Tiger I       CTankPzVIAusfEGun          1.2      0.05    24x better
German   StuG III      CSAUStuG40Gun              1.2      0.02    60x better
Soviet   T-34/76       CTankT34_76_42Gun          1.5      1.6      1.07x WORSE
Soviet   T-34/85       CTankT34_85_44Gun          1.25     1.55     1.24x WORSE
Soviet   SU-85         CSAUSU85Gun                1.2      1.2      untouched
```

## Player guns - ONE change in the entire game

```
Soviet   T-34/85       CTankT34_85_44PlayerGun   0.005     0.15    30x WORSE
```

Every German player gun is untouched.

## THE CONTROL that removes any doubt

The **StuG III and SU-85 are the same class of vehicle** - casemate tank
destroyers, no turret, same role, same era. **G5 set both to exactly 1.2.**

```
                StuG III     SU-85
G5 original       1.2         1.2      IDENTICAL
ZW                0.02        1.2      60x apart
```

Two functionally identical vehicles that the original deliberately set equal;
the German one made 60x more accurate, the Soviet one left alone. There is no
gameplay rationale under which that is a balance pass.

## Net effect across all measured fields

```
German    47 changes better,  9 worse    84% favourable
Soviet    43 changes better, 28 worse    61% favourable
```

(Both sides gained from ZW's across-the-board increases to radar and attack
distances, which is why the Soviet figure is not lower. The accuracy table above
is where the intent shows.)

## Sensors, mobility and rate of fire, German side

```
Tiger      MaxSpeed 2200 -> 2730 (+24%)     Mass 56t -> 40t (29% lighter; real 57t)
           MaxRadarDistance 1500 -> 2600    AttackDistanceMax 1000 -> 2600
           FirePeriod 12000 -> 7000         FirePeriodRandAdd 8000 -> 2000
           gun DirectionSpeedH 4.5 -> 6.5   MG FireDeviation 0.15 -> 0.05
Panzer IV  AttackDistanceMax 1000 -> 2800   MaxRadarDistance 1200 -> 2700
StuG III   AttackDistanceMax 1000 -> 2000   MaxRadarDistance 1200 -> 2000
```

## Soviet side, same fields

```
T-34/85    DirectionSpeedH 17 -> 8 (turret traverse HALVED)   Mass 40t -> 48t
T-34/76    DirectionSpeedH 36 -> 7 (cut 5x)
SU-85      gun DirectionSpeedH 5.0 -> 3.0    FirePeriod 8000 -> 9000 (slower)
ZiS-3      gun DirectionSpeedH 6.0 -> 4.0
```

## Method note - this trap produced two opposite wrong answers

A unit file contains **separate gun classes for the AI and the player**
(`CTankT34_85_44Gun` vs `CTankT34_85_44PlayerGun`), each with its own
`FireDeviation`. Grepping the first match in the file gave "0.005 -> 0.15" on one
pass and "0.15 -> 0.005" on the next. **Always compare per class.**

Similarly, a first side-classifier filed `GermanSoldierRifleUnit` as Soviet
because its match list omitted "German". Check the classifier before trusting
any aggregate.

---

# CORRECTION 2026-08-27: the sensor ranges are NOT even-handed either

The revert deliberately left `MaxRadarDistance` and `AttackDistanceMax` alone,
on the reasoning that ZW raised them for both sides. **That was decided on a
partial sample** - the ZiS-3 (800 -> 3200) and SU-85 (1200 -> 2400) were checked
and looked generous to the Soviets. The T-34s were not checked, because the
filter used to pick "tanks" matched `Tank`/`SAU`/`Gun` and `T34_85_44` contains
none of them.

The full picture:

```
GERMAN TANKS            sees      engages          SOVIET TANKS      sees    engages
  Panzer IV             2700 m    2800 m             SU-85           2400 m   2400 m
  Tiger I               2600 m    2600 m             T-34/85         1650 m   1650 m
  StuG III              2000 m    2000 m             T-34/76          800 m   2600 m
```

**The Tiger detects at 2600 m; the T-34/85 not until 1650 m.** A 950 m window in
which the Tiger engages and the Soviet tank does not know it is there. Against
the Panzer IV it is 2700 vs 1650.

**The T-34/76 is incoherent**: engagement range 2600 m, detection range 800 m -
it will try to shoot at things it cannot see. It is also **the only vehicle in
the game whose detection ZW reduced** (1200 -> 800).

For reference, G5's originals were 1200-1500 m detection for every tank on both
sides, and 900-1000 m engagement.

## First play test after the revert

User, playing Soviet: *"i died pretty quick"* - one run, explicitly not
conclusive, more play needed. But the sensor asymmetry above is the obvious
suspect: the gunnery revert fixed *accuracy* while leaving the German side a
950 m head start on *detection*, which no amount of accuracy helps with.

## OPEN - three options

1. **Revert sensors to G5 too** - everything back to ~1200-1500 m detection.
   Consistent, but loses ZW's genuinely better engagement ranges.
2. **Keep ZW's increases, equalise them** - bring Soviet tanks up to German
   figures (T-34/85 1650 -> 2600, T-34/76 800 -> 2600 detection). Keeps the
   improvement, removes the tilt.
3. **Fix only the incoherent one** - T-34/76 detection 800 -> 2600 so it matches
   its own engagement range. Minimal change.

**Option 2 is the one that matches the stated goal** (keep the modding, remove
the bias), and it is what the earlier decision was *trying* to do.

## Method note

Two classifier bugs in one session produced two wrong aggregates: a side-
classifier that omitted "German" filed German infantry as Soviet, and a unit
filter that matched `Tank`/`SAU`/`Gun` silently dropped both T-34s. **Check what
a filter excludes, not just what it includes** - a partial sample that looks
tidy is more dangerous than an obviously broken one.
