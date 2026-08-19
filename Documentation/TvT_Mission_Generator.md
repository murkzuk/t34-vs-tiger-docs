# TvT mission generator

`Tools/MissionGen/gen_mission.py` — generates complete, playable TvT missions.

Built 2026-08-19. Every technique it uses was proven by hand first; nothing here
is speculative.

```bash
python gen_mission.py --name Kursk04 --seed 42
python gen_mission.py --name Kursk05 --seed 12 --length 6000 --points 34
python gen_mission.py --name Assault1 --title "Prokhorovka: dawn attack"
```

---

## Why it clones instead of emitting templates

A complete mission is roughly **3,850 lines of `.script` across 8 files** plus 5
binary files (heightmap, water, three zone bitmaps, two textures). All of it is
already known-good in the template. Emitting that from scratch means
re-introducing every bug we spent two days finding.

The decision rested on one measurement. `BerezovKursk` uses **exactly one
identifier prefix across all 135 of its names**, and defines **no classes outside
it**:

```
distinct BerezovKursk* identifiers: 135
non-BerezovKursk classes: none
```

So a single prefix rename makes a clone completely unique — 569 textual
replacements per mission — which is what prevents the duplicate-class launch
errors that bite unzipped mission variants. The naming problem solves itself.

## What actually varies between missions

Cloning alone would produce the same battle twice. What changes:

- **The corridor.** A fresh route through the largest connected open region of the
  router bitmap, chosen for straightness.
- **The whole order of battle**, carried onto it by a rigid transform (rotate +
  scale + translate) applied to positions *and* orientations, so column formations
  and defensive depth survive intact. Anything landing on blocked ground is nudged
  to the nearest passable cell.
- **The mission text**, derived from the corridor that was generated — see below.

Measured across three missions from the same template:

```
BerezovKursk   start (7000,7950) -> (3318,4583)   4989 units, bearing -138 deg
Kursk02        start (6614,3898) -> (1349,4162)   5271 units, bearing +177 deg
Kursk03        start (6763,1147) -> (3028,4882)   5283 units, bearing +135 deg
```

Start points 2,755 units apart on different ground with different approach axes.

## The validation that matters

**Every consecutive pair of navpoints is solved with A* capped at 20000 steps —
the engine's own budget.** A route that passes here is one the engine can also
solve.

This is not a nicety. The first hand-built Berezov route sampled as fine at every
navpoint and still failed 34 times in play, because the check only looked at the
endpoints and never at the ground *between* them. The generator refuses to claim
success unless:

```
navpoints on passable ground : 34/34
objects on passable ground   : 60/60
unroutable legs              : 0
worst leg                    : 18-20 A* steps  (budget 20000)
```

Zone-map sampling uses the **measured** row order — pixel row 0 is world y=0, no
flip, despite the positive BMP height that by spec means bottom-up. See the
authoring manual's section 4 for how that was settled.

## Mission text is generated, not copied

The first version renamed class identifiers but left the display strings alone, so
every mission appeared in the menu as *"Operation Citadel: Berezov (Kursk)"* — and
every briefing said *"press east"* on missions advancing west and north-west.
A generator writing misleading briefings is worse than one writing none.

Text is now derived from the route's actual bearing (8-point compass, +X east,
+Y north) and length:

```
Kursk02   "Kursk Steppe - westward advance (Kursk02)"
Kursk03   "Kursk Steppe - north-westward advance (Kursk03)"
```

> Your Tiger spearheads the attack across the Kursk steppe... **The axis of advance
> runs westward for some 5346 metres.** Smash the anti-tank positions and armour
> barring the route, then press on.

The folder name stays in the title deliberately: with many generated missions you
need to know which menu row maps to which folder. Override with `--title`.

## Menu registration

Missions are appended to `Germany_ExtraMissions` / `USSR_ExtraMissions` in
`Scripts\Menus\MissionsMenu.script` — **not** the campaign arrays, which are gated
by `GetUserValue("<X>Campaign")` and would leave a generated mission invisible.
See the authoring manual's section 7.

`Scripts.cache` is deleted automatically; the game rebuilds it on next launch.

## Verified in play

`Kursk03`, fully machine-generated, loaded and ran:

```
125 objects, mission ready in 7.4s
ScriptManager errors : 0
group alarms         : 0
routing failures     : 0
OnUnreacheable       : 0

ZugFalke::RepeatOrder()     : Patrol order to point Kursk03Advance_01
KGKaiser::RepeatOrder()     : Patrol order to point Kursk03Advance_01
ZugLex::RepeatOrder()       : Patrol order to point Kursk03Advance_01
ZugWeidinger::RepeatOrder() : Patrol order to point Kursk03Advance_01
```

All four German groups accepted the generated route.

## Limitations, honestly

- **Terrain is inherited, not generated.** Every clone shares the template's
  heightmap and zone maps, so missions differ by *where* on that map they are
  fought, not by the map itself. `K:\tvt_terrain\make_map.py` can build new
  terrain; wiring it in is the obvious next step.
- **Force composition is fixed.** The order of battle is the template's, moved.
  Varying unit types, counts and defensive posture is the real remaining design
  work — and the part that would most change how a generated mission plays.
- **Objectives are the template's**, so they still name Soviet HQ and Plt.
  Samsonov. Fine while the order of battle is inherited; needs attention when it
  stops being.
- **One player start.** The player always spearheads the German advance.
- Not tested at scale — three missions generated, one played.

## A bug worth recording

The first menu-registration attempt produced malformed array syntax:

```
Germany_ExtraMissions = [,          <- stray leading comma
        "CKursk02Mission"           <- and no separator before the next entry
        "CBerezovKurskMission"
```

The comma belonged *after* the inserted entry, not before it. This would have
broken the entire missions menu on next launch, and it surfaced only because the
output was read back rather than trusting the tool's own "registered" message.
**Verify the artefact, not the log line that says you wrote it.**
