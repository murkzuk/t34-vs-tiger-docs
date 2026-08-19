# Line of sight for TvT

*2026-08-19. The model, why it has the shape it does, and what it measures on
the game's own missions. The engine side is in
`Documentation/RE/TvT_Vision_Model_Decoded.md`; this is the maths, and it runs
today in `Tools/LineOfSight/canopy_los.py` without touching the game.*

## Two effects, one march

**Terrain.** The heightfield is exact and unambiguous. If the sight line passes
below the ground anywhere between observer and target, a crest blocks it. This
is what produces hull-down positions, dead ground and reverse slopes — none of
which currently exist in TvT.

**Vegetation — deliberately not a height ceiling.** A canopy-top test alone
says that anyone standing inside a wood is blind in every direction, which is
plainly wrong: you can see out of a wood along the ground, just not far. So
foliage accumulates **optical depth**. Every metre through a vegetation cell
spends part of a sight budget, and the line is lost when the budget runs out.
Stand 20 m inside a wood and you see about 20 m — that falls out of the model
rather than being special-cased.

**What couples them** is the canopy height: a vegetation cell costs nothing
unless the sight ray is *below* the treetops there. A gunner on a ridge looking
down over a wood in the valley at a target beyond it has a clear line over the
crowns, and the model gives him one.

```
for each step along the 2D line:
    if ray_z < ground        -> blocked by terrain
    if ray_z < ground + canopy_height:
        budget -= step / sight_through
        if budget <= 0       -> blocked by foliage
```

Roughly 20–50 lookups per test. No GPU, no ray-triangle work, no render passes,
no async readback. Cached and staggered on top of the vision model's existing
distance and angle gates, the cost effectively vanishes.

## Where the numbers come from

Canopy heights are the game's own, not invented.

Every stock `Terrain.script` — all twelve campaign missions, identically —
calls:

```
RegisterVerticalForest([ZMC_Forest01], "textures\foreststripe.tex", [0.8], 17.0f);
```

**17 m** is the engine's own forest wall height, and `Forest01` is the only zone
that gets one. The forest render layers sit at `[0.0, 8.0, 11.0, 13.0, 14.0]` m.

Everything else is the weighted mean of `TreeSize` in `Common\BaseSTTree.script`
over that zone's species mix in `Common\BaseForest.script`:

| zone | code | template | canopy | sight | mix |
|---|---|---|---|---|---|
| Forest01 | 11 | `CMiddleForest` | 17.0 | 45 m | firs + scotch pine, 90% occupied |
| Forest02 | 12 | `CLightForest` | 4.6 | 160 m | scrub — **a Tiger at 3.0 m stands proud of it** |
| Forest03 | 13 | `CLiveOakForest` | 17.0 | 120 m | single live oak |
| Forest04 | 14 | `CLargeForest` | 23.9 | 90 m | tall, but half `NullTree` — see-through |
| RoadForest | 20 | roadside line | 28.0 | 200 m | three trees, you see between the trunks |
| Shrubbery | 49/50/51 | bushes | 5.0/3.5/3.0 | 70/90/100 m | |
| LongAloneTree | 52 | one fir | 28.0 | 400 m | |
| VillagePlanting | 60/61/62 | lindens, apples | 8.0/8.0/7.5 | 120/120/130 m | |

The canopy column is data. **The sight column is the one tuned quantity** —
seeded from each template's occupancy (how much of the mix is `NullTree`) and
meant to be adjusted against play.

## Geometry, re-validated

Each of these cost a debugging session earlier in the project, so they are
re-checked here rather than trusted:

- `hmap.raw` is 2049×2049 uint16 LE stored **flipped** — row 0 is world
  *y = MAX* — and `Z = raw × 0.07`. Checked against 46 hand-placed
  `GameObject`s in Campaign_1/Mission_2: **mean −1.12 m, RMS 1.27 m**. The
  other seven orientations give RMS 6.6 to 33. Re-run across all twelve
  campaign missions, flipped wins every time.
- The zone bitmaps are the **opposite**: row 0 is world *y = 0*, no flip,
  despite a positive BMP height field.
- World is 9000 × 9000 m (`CWorldMatrices::MatrixWidth`), so a 1024 zone cell is
  8.789 m and a 2049 height sample is 4.395 m.
- Ground is sampled **bilinearly**. Nearest-neighbour on a 4.4 m grid builds
  staircase ridges that block lines which are actually open.
- Endpoints are taken from the heightfield, not from the object's authored Z.
  Those disagree by up to 0.9 m in Campaign_1/Mission_2 — enough to start a
  sight line below its own ground and self-occlude in the first few metres,
  which reads as a terrain block and is not one.

## What it measures

Random sight lines across each map, observer eye 2.2 m, target hull 1.3 m.
**The shipped engine sees 100% of every row below.**

| mission | 200 m | 400 m | 800 m | 1500 m |
|---|---|---|---|---|
| C1M1 | 17.1% | 7.7% | 2.8% | 0.7% |
| C1M2 | 16.9% | 7.5% | 2.8% | 0.6% |
| C1M6 | 20.8% | 10.8% | 3.5% | 0.8% |
| C2M2 | 25.0% | 12.2% | 5.0% | 2.2% |
| C2M4 | 21.3% | 10.5% | 3.7% | 1.3% |
| **Kursk steppe (generated)** | **63.6%** | **38.6%** | **21.3%** | **11.9%** |

The stock campaign maps are 45–68% forest; the generated Kursk maps are ~9%.
The steppe maps are three times as open at 200 m and blocked mostly by ground
rather than trees — which is exactly the character a Kursk map should have, and
exactly the distinction the engine currently cannot make.

Hostile pairs actually placed in the missions, at 1000 m:

| mission | pairs | visible under real LOS |
|---|---|---|
| C1M1 | 26 | 0 |
| C1M2 | 49 | 14 |
| C1M3 | 17 | 0 |
| C2M1 | 11 | 4 |
| C2M4 | 53 | 0 |

Those zeroes are not a bug. A worked profile from C2M4, `MainPlayerUnit` to the
nearest enemy at 852 m, shows a 2.7 m crest at 85 m and a longer rise between
680 and 770 m. Real dead ground, twice over. Under real LOS those engagements
begin only once someone moves — which is the point.

## Using it

```
python canopy_los.py <mission_dir>                  # hostile pairs
python canopy_los.py map <mission_dir>              # random lines across the map
python canopy_los.py profile <mission_dir> ax ay bx by   # ground vs ray, step by step
```

`profile` is the one to reach for when a verdict looks wrong. It shows whether a
block came from a real crest or an artefact, and no amount of reasoning
substitutes for looking at the ground.

## Incidental finding

`BerezovKursk`, `Kursk02`, `Kursk03` and `Kursk04` share one `hmap.raw` and one
`TerrainZone` bitmap — byte-identical. Variety in the generated set comes from
routes and order of battle, not terrain. Worth knowing before reading anything
into their identical LOS numbers.

## Measured against the live engine (2026-08-19)

The watcher was run on Campaign_1/Mission_2 and its captured calls replayed
through this model. This is the engine's own traffic, at positions the game
chose, not random sampling.

**Call rate: 5000 calls in 156 s — 31 per second, with `dt` between 3.0 and
89.2 s.** The vision check is a slow AI tick, not a per-frame poll. A 20-50
lookup march at that rate is roughly 1,200 lookups a second. **The performance
constraint that shaped this whole plan is gone.** Caching and staggering remain
worth doing as insurance, but nothing depends on them.

**Of the engine's positive sightings, 70% are through solid ground or woodland**
(30 of 43 sampled). A further 29 were correctly missed, and 7 were misses the
dice caused where the ground was actually clear.

### The object origin is not ground contact

Height of a unit's origin above the sampled heightfield, from live positions:

| class | calls | offset | spread |
|---|---|---|---|
| `CTankT34_76_42Unit` | 38 | +1.41 m | 0.04 |
| `CTankT34_85_44Unit` | 19 | +1.39 m | 0.00 |
| `CTankPzVIAusfEUnit` | 12 | +1.65 m | 0.00 |
| `CTankPzIVGUnit` | 6 | +1.44 m | 0.00 |
| `CSovietSoldierRifleUnit` | 17 (authored) | +0.85 m | 0.01 |

The offset scales with model height — roughly half of it — so origins sit near
mid-model. That is a convention, **not** a bias in the heightfield: a sampling
error would shift every class equally. Seventeen soldiers agreeing to within a
centimetre is the strongest check the heightfield has had.

**Consequence:** take both endpoints as absolute heights above sampled ground
and ignore the engine's Z. Adding an eye height on top of a Z that is already
mid-model puts the gunner a metre and a half too high and quietly makes
everything look more visible. Doing exactly that gave 60% instead of 70%.

### A worked block, checked by hand

Call 3329, a T-34/85 at 833 m from its target:

```
   0 m  ground 599.96  ray 602.11
  40 m  ground 601.26  ray 601.43
  60 m  ground 601.24  ray 601.09   blocked by 0.15 m
 120 m  ground 601.25  ray 600.07   blocked by 1.19 m
 200 m  ground 601.07  ray 598.70   blocked by 2.37 m
```

The tank sits in a hollow; the ground rises about 1.3 m within 40 m and then
runs flat for hundreds of metres, while the target is 13 m lower and far away.
A classic turret-down position. Drive forward 40 m and the shot opens. The
engine currently takes it from where it stands.

### Partial cover falls out for free

Several blocks begin marginally — 0.15 to 0.5 m of intervening ground, which is
inside the fuzz of a 4.4 m heightfield. Rather than pick a tolerance, note that
the engine's model **multiplies** visibility by each modifier's factor. So the
right answer is not a binary block at all: mask a third of the target's height
and return 0.6, mask all of it and return 0. Hull-down becomes harder to spot
rather than impossible, which is both more realistic and more forgiving of
heightfield noise — and it costs nothing extra, because the architecture already
wanted a float.

## It works (2026-08-19)

First run with the march enforcing, Campaign_1/Mission_2:

```
read 306 object loads from execution.log, 198 distinct names used
mission match: 179/198 names, runner-up 90  ->  Campaign_1\Mission_2
fit check over 8 observer positions: offsets +0.60..+1.71 m
--- 5000 calls, 2912 seen, 2161 denied by LOS, 175 s, 28 calls/s
```

**2161 sightings refused — 74% of the engine's positives**, against 70%
predicted offline from the previous run's captured traffic. No access
violations; the engine took it without complaint.

Where the effect lands:

| range | allowed | denied | denied share |
|---|---|---|---|
| 200–400 m | 3 | 0 | 0% |
| 400–600 m | 5 | 1 | 17% |
| 600–800 m | 29 | 6 | 17% |
| 800–1000 m | 9 | 107 | **92%** |
| 1000 m+ | 1 | 40 | **98%** |

Close fighting is untouched. The cliff at 800 m is not arbitrary: in this
mission the Germans sit at 601–606 m and the Soviets at 586–589 m with a crest
between them, about 900 m apart across dead ground. Every one of those long
shots was going through a hill.

**The user's verdict: "the game was good it felt more tactical (slower paced)".**

That pacing change is the point, and it is worth being explicit about why it
happens. Tanks that cannot see across a valley have to move to a position where
they can. Manoeuvre takes time. The engagement no longer opens the instant two
forces are within gun range, so the mission acquires an approach phase it never
had — which is most of what a tank sim is for.
