# Placing objects in a TvT mission — heights, ground contact, gun positions

Measured 2026-08-19. Everything here was established against shipped G5 content,
not inferred.

---

## 1. Let the engine put things on the ground

`["SurfaceControl", <mode>]` decides whether an object is snapped down onto the
terrain or left at its authored Z. Usage across the stock missions:

| mode | uses | what it is for |
|---|---|---|
| `PutonGround` | 946 | most scenery — sandbags, pillboxes |
| `PutonGroundUpright` | 106 | infantry, guns — snapped *and* stood upright |
| `None` | 63 | trust the authored Z exactly |
| `PutonGroundLandingJoints` | 48 | vehicles — settles on tracks/wheels |

**Use a `PutonGround*` mode for anything placed programmatically.** Stock gives
`CBarricadePakUnit` the value `None` because its Z was authored by hand in the
Editor and is exact. A generated Z is not exact, and `None` means the object hangs
wherever you put it — which is how 21 barricades and sandbag walls ended up
floating roughly 20 m above the steppe.

Vehicles hide this problem: they settle under physics. Static scenery has nothing
to settle it, so it is always the fortifications that expose a bad Z.

> The Editor exposes the same thing as a "put on ground" option — which is where
> this was spotted first.

## 2. `hmap.raw` is stored flipped — and the *opposite way* to the zone bitmaps

This is the trap. The two file types disagree, and only measurement separates them:

| file | row order |
|---|---|
| `RouterZone_*.bmp` / `TerrainZone_*.bmp` | **row 0 = world y=0** (no flip) |
| `hmap.raw` | **flipped** (row 0 = world y=MAX) |

Established by fitting `Z = a·raw + b` against **79 hand-placed objects** in
`Campaign_1/Mission_1` under all four sampling orientations:

```
flip=False  swap=False   RMS error 4.31 m
flip=False  swap=True    RMS error 4.11 m
flip=True   swap=False   RMS error 0.78 m   <- correct
flip=True   swap=True    RMS error 4.08 m
```

For that mission the fit is `Z ≈ 0.0669 · raw + 27.07`. Note `WorldMatricies.script`
declares `FloatValueFactor = 0.070000 * 257.0`, and the fitted slope is close to
that leading `0.07` — but the constant offset is real and is **not** captured by a
naive `raw × scale`.

**An earlier scale of `0.0739` with no offset was wrong.** It was derived from a
single Z the engine reported for one navpoint, which is a sample size of one. Every
programmatically-placed Z built on it was out by tens of metres.

**How to apply:** sample `hmap.raw` flipped, fit the scale and offset per mission
against a handful of known-good objects if precision matters, and set
`SurfaceControl` so the engine corrects whatever remains.

## 3. What a gun position actually looks like

From `Campaign_1/Mission_1`, which crews all four of its guns:

```
LeftAntiTank_1              CGunPak40Unit
  _8                        CBarricadePakUnit         0.8m
  LeftAntiTank_1_Gunner_1   CGermanSoldierRifleUnit   2.5m   ["Guncrew", true]
  LeftAntiTank_1_Gunner_2   CGermanSoldierRifleUnit   2.4m   ["Guncrew", true]
  _91                       CBarricadeFenceUnit       8.4m
```

**`["Guncrew", true]`** is the property that binds a soldier to the gun. Without it
a rifleman standing beside a Pak is just a rifleman standing beside a Pak.

Assets available: `CBarricadePakUnit`, `CBarricadeFenceUnit`, `CSandBagsUnit`,
`CDotConcreteUnit`, plus `CZhedgehog.ms2` and `fence_Palisade.ms2` as models.
Prime movers: `CTruckOpelBlitzUnit` (German), `CTruckZis5Unit` (Soviet).

### Guns must be turned to face the threat

An AI-authored mission places guns at arbitrary rotations, and any bodily transform
of the mission rotates them further. Measured on Berezov before this was fixed:

```
HQ_1          151 deg  FACING AWAY
PltBerzina_1  146 deg  FACING AWAY
PltMarkov_2    60 deg  oblique
...            95-108 deg  oblique
```

**Not one of seven guns faced the advance**, and two pointed backwards. This also
matters mechanically for tooling, because crew go *behind* the gun and cover goes
*in front* — get the facing wrong and everything else is mirrored.

The rotation that faces `(fx, fy)` with Z still up:

```
row0 = ( fx, -fy, 0)
row1 = ( fy,  fx, 0)
row2 = (  0,   0, 1)
```

Columns of the matrix are the object's local axes in world space, so column 0 is
its forward direction. Verified against the stock gun matrices, which satisfy this
relation exactly.

## 4. Objects can be transformed clean off the map

A rigid transform that moves a mission onto a new corridor can push units outside
the 9000×9000 world:

```
PltPopov_1   x=3841.6  y=9520.6   OFF-MAP
```

A "nudge onto passable ground" search **cannot** rescue these, because every cell it
probes is out of bounds and reads as blocked — so the units sit off the edge,
invisible and useless, with nothing in the log to say so. Clamp into bounds *before*
searching for passable ground.

## 5. Tooling

`Tools/MissionGen/emplace_guns.py` applies all of the above:

```bash
python emplace_guns.py --mission Kursk03
python emplace_guns.py --mission Berezov --crew 3 --no-trucks
```

Re-faces each gun onto the nearest point of the advance, then places crew, a
barricade, flanking sandbags and a nationality-matched prime mover around the
corrected facing — checking the router map first, because a lorry cannot have
driven somewhere a lorry cannot drive. Idempotent: guns that already have crew are
skipped.

It runs automatically as part of `gen_mission.py`. Note that the generator must
**strip inherited emplacements on clone** — the template is itself emplaced, so a
clone would otherwise arrive with crew positioned for the *template's* corridor,
which the transform then rotates onto the new one.
