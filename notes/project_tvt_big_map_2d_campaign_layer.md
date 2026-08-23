# Big-map 2D campaign layer idea (PARKED — record only, 2026-08-22)

The user's design ambition for the one-map dynamic campaign ("Falcon-4 bubble"):
a **2D tabletop-wargame-style layer** that simulates the campaign (map, orders of
battle, logistics) and **carries battle outcomes into the 3D game** (TvT/G5) — so the
player fights key battles in 3D while the rest of the front resolves in 2D.

**Status: PARKED.** Recorded 2026-08-22 at the user's request ("don't want to get ahead
of myself, but good to know and record"). NOT started. Do NOT begin work without the
user explicitly asking.

## Validated: this is a proven architecture

Strategic (2D) + tactical (3D) with carryover is exactly how X-COM, Total War, and
Falcon 4 work. Not exotic — standard military-sim pattern. "Tabletop wargaming" is the
right name for the 2D layer.

## Open-source candidates (repos)

- OpenXcom — github.com/OpenXcom/OpenXcom (C++); actively-modded fork:
  OpenXcom Extended (OXCE) — github.com/OpenXcom/OpenXcomExtended.
  Best ARCHITECTURE match: geoscape (2D) + tactical battles + carryover.
- TripleA — github.com/triplea-game/triplea (Java). Axis & Allies engine — WW2 theme,
  army-scale abstraction, not tank-vs-tank.
- UFO: Alien Invasion (UFOAI) — same X-COM pattern, fully open.
- VASSAL — tabletop engine, manual play only (no AI) — not a simulator.
- MegaMek (BattleTech tabletop sim) / Open General (Panzer General remake) — closest
  unit-level tabletop wargame engines (not yet deep-researched).

## The honest engineering truth (decides everything)

- G5 has NO external API. "Carry outcome into 3D" = write it in a language the game
  reads: generate/modify mission `.script` files + read state back (execution.log,
  settings.xml, persistence machinery).
- The pieces already exist: missions CAN share one terrain (proven), the engine sees
  every death (dynamic campaign "~5 lines away" per handoff), and the ballistics data
  (Piercing.script / Armour.script / can_i_kill.py) can power a 2D auto-resolve.
- Recommendation: borrow the ARCHITECTURE from OpenXcom/TripleA, do NOT bolt a foreign
  engine onto G5 (unit stats won't match — integration hell). Build thin: hex/region
  map + state file + auto-resolve reusing can_i_kill.py. Player's own battles stay in 3D.

## Sequence when pursued (do in this order)

1. Prove 2 missions on one terrain carrying an outcome forward (handoff's "BUILD THIS
   FIRST").
2. Define the STATE-FILE CONTRACT: exactly what crosses the 2D/3D boundary (forces,
   damage, ammo, ground taken, supplies/reinforcements).
3. Only then design the 2D layer against that contract (thin, bespoke; reuse G5 data).
4. Deep research pass on the candidates' mechanics via DeepSeek V4 Pro when the time
   comes (flash shaped it, pro checks it — as with the log findings).

Related memory: project_tvt_shared_terrain_test.md, project_tvt_engine_scale_and_campaign.md
(one-map campaign, "~5 lines away"), project_tvt_penetration_targeting.md (can_i_kill.py).

## Patton's Best — the design twin (recorded 2026-08-22)

The user's friend always rated Patton's Best (Avalon Hill 1987, solitaire) the best game
he played. It turned out to be the clearest description of the whole project goal:

- Patton's Best = one Sherman vs the German army, day by day, carrying damage/ammo/fuel/
  crew forward.
- TvT = one Tiger or T-34 vs the enemy. Same skeleton.

THE ONE-SENTENCE GOAL: **build Patton's Best's shell around TvT's engine.**
- PB's abstract combat charts -> replaced by the real 3D game (better than PB ever had)
- PB's campaign shell (day-by-day map, carryover, escalating German armour) -> the 2D
  layer being planned (map, logistics, carryover)

Use PB as the design reference for the PLAYER'S BATTLE LOOP half of the 2D layer;
OpenXcom/TripleA for the REST-OF-THE-FRONT half.

Resources:
- Wikipedia: https://en.wikipedia.org/?curid=18543988
- BoardGameGeek: https://boardgamegeek.com/boardgame/4556/pattons-best
- Free to try on PC: VASSAL module http://bggames01.blogspot.com/2010/03/pattons-best-module-gamebox.html
- GitHub recreation (the "is there a git" answer): https://github.com/happysulla/PattonsBest
  ("A solo game that recreates WW2 campaign in northern Europe through eyes of tank
  commander"). NOT the official game - no official digital PB exists.
- The user has never played a tabletop game - the VASSAL module is a cheap way to feel
  the design first-hand before we build anything.
## Patton's Best campaign loop — the blueprint (recorded 2026-08-22)

Setting: summer 1944 Normandy breakout. One Sherman + 5-man crew, day after day until the
campaign arc ends. The day-by-day loop (5 beats):

1. THE WAR MOVES - front-line situation updates (US advance / German counterattack),
   driven by map + dice + historical events.
2. GET A MISSION - derived from where the front is (attack a village, hold a crossroads,
   escort a column, breakthrough, ambush defense...).
3. FIGHT IT - on a generated battlefield, real combat tables (range, line of sight,
   gun-vs-armour penetration, hit locations).
4. OUTCOME BITES - crew killed/wounded, tank damage state, ammo and fuel spent.
5. CARRY THE WRECKAGE FORWARD - repairs, resupply (if available), replacements, and the
   crew gets better.

The three things that make it sing:
- ESCALATION: Germans field more Panthers/Tigers as days pass - the Sherman gets
  relatively worse while your crew gets better. It is a race.
- THE SETBACK LOOP: tank destroyed = replacement tank with a GREEN crew - a real loss,
  not a reset.
- THE STORY: your tank, named crew, awards. After a month you are playing a guy, not a counter.

One-to-one mapping to the user's plan:
| Patton's Best | User's big-map plan |
|---|---|
| war-situation map | 2D campaign map |
| mission assignment from the front | which TvT mission you fight next |
| tactical battle (charts) | the real 3D game (better than PB) |
| ammo/fuel/damage/crew carryover | the state-file contract (keystone) |
| escalating German tanks | enemy OOB that hardens as campaign advances |
| replacement tank + green crew | loss + reinforcement logic |

WHAT PB DOESN'T HAVE (the user's addition): force-level logistics. PB tracks one tank's
ammo/fuel only - not supply columns, reinforcements, or a whole front. The big-map plan
takes PB's loop and scales it up to the whole front. PB = blueprint for the "player's
day" loop; OpenXcom/TripleA = the "everyone else's day" layer.

Sources: grognard.com/reviews1/patton1.txt (review), boardgamegeek.com/boardgame/4556,
wargamingincentraloregon.com/?p=1017 (session), wargameacademy.org/PTB/.
## THE HOOK IS THE API — the state bridge (recorded 2026-08-22)

Reframe that upgrades the plan: TvT has no OFFICIAL API, but the LOS hook already proves
we do not need one - the hook IS the interface.

Proof from the LOS work:
1. We can get inside the engine (injected DLL, running in its memory).
2. We can read its brain (the hook watches the AI's vision calls live, unit by unit,
   with positions).
3. We can change its behavior (blocks sightings the game would have allowed).

What this means for the campaign:
- The same hook trick becomes the STATE BRIDGE (previously called the state-file
  contract).
- End of mission: hook grabs the tank's REAL state (damage, ammo left, crew, battle
  result) and writes it to the 2D layer's file. No log-parsing, no guessing.
- The 2D layer reads that file, advances the front (PB's "the war moves" beat), picks
  the next mission.
- Next mission start: the hook (or a generated script) puts the carried-over tank back
  on the battlefield - battered or repaired, with the crew.

The remaining question is measured, not mysterious: "how much state can we read and write
reliably" - a testable number, the same way the vision work was measured.

Updated honest ratings (with hooks counted):
- Keystone proof (2 missions + carryover): ~85% (was ~70%)
- Full campaign layer: ~65% (was ~50%)

Also decided: the "build a new 3D game around PB" direction is DROPPED - not that.
## ROADMAP — the body of work (recorded 2026-08-22, in order of importance)

### PART 1 — GETTING READY FOR PB (foundation)
1. Re-apply the 6 verified fixes, one at a time, play-tested (cards at
   K:\TvTDeepseek\patches\REDUX_2026-08-22\, menu patch comma-corrected). First the
   recursion fix, then the log-spam cleanups (ActivateMove x2, ghost menu entry, ZW
   items). WHY: cannot build a campaign on a game that can freeze.
2. Reconcile the backlog - several fixes live only in docs, not TODO.md/CHANGELOG.md.
   WHY: the record must be true before building on it.
3. Re-sync the TvT\ mirror (UnitGroup.script out of sync with live install).
   WHY: "repo = disk" is a rule needed during campaign work.
4. JUDGE - teach the AI to pick targets it can actually kill (wire can_i_kill.py into
   target choice). WHY: campaign only worth carrying forward if battles are honest fights.
5. DECIDE - finish target acquisition through terrain (open second half of LOS work).
   WHY: completes SEE -> JUDGE -> DECIDE chain.
6. Loose ends - hunt the 268455937 unknown command; ZW fixes (FH18, Stuka lines,
   atmosphere silencer) on the separate build whenever wanted. WHY: independent, can
   run in parallel.

### PART 2 — PUTTING PB IN TVT (campaign layer)
1. KEYSTONE PROOF: two missions, one terrain, outcome carries forward. WHY: decides
   whether the whole idea is 85% or 30%. Everything waits on it.
2. State bridge prototype: hook reads the tank's real end-of-mission state (damage,
   ammo, crew, result) and writes it to a file. WHY: proves "the hook is the API"
   with one measurable number.
3. State-file contract: freeze exactly what crosses 2D/3D. WHY: both layers become
   buildable against one fixed format.
4. The 5-beat day loop (PB's campaign): front map + "the war moves" + mission
   selection. WHY: PB's heart; needs only the contract from #3.
5. Auto-resolver: 2D resolution for battles not fought by the player, reusing
   existing ballistics math. WHY: the "rest of the front" layer; cheap once #3 exists.
6. Force-level logistics: supplies, reinforcements, replacements. WHY: the user's
   addition to PB - what makes it a front, not a tank's diary.
7. Escalation & carryover: crew experience, German tanks getting scarier, loss ->
   replacement with green crew. WHY: the three things that made PB sing.
8. Theatre layer: multiple sectors, dynamic front (Falcon-4 bubble). WHY: the
   horizon. Build only after 1-7 are real.

HEADLINE: Part 1 items 1-3 are weeks, not months (truth + stability). Part 2 items
1-3 are the real "is this possible" gate - after #3 it is construction, not
discovery. Part 1 items 4-5 run in parallel with Part 2's early items.