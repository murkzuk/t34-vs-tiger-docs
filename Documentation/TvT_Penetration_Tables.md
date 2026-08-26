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
