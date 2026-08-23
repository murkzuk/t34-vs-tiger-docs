# Patton's Best in TvT — Working Reference

Clean, standalone reference for the campaign idea. Full working trail lives in
`project_tvt_big_map_2d_campaign_layer.md`. Status: **PARKED** (record-only, 2026-08-22) —
do not start without the user asking.

## The one-sentence goal

**Build Patton's Best's shell around TvT's engine.**

## Why Patton's Best (the design twin)

- **Patton's Best** (Avalon Hill 1987, solitaire): one Sherman vs the German army, day by
  day, carrying damage / ammo / fuel / crew forward.
- **TvT**: one Tiger or T-34 vs the enemy. Same skeleton.
- PB's magic is **not** the combat (abstract dice charts) — it's the **campaign shell**
  around the tank. TvT has the opposite: superb 3D combat, no shell.
- So the plan is PB's shell + TvT's engine. Each fills the other's missing half.

## The campaign loop (5 beats per day)

1. **THE WAR MOVES** — front situation updates (advance / counterattack).
2. **GET A MISSION** — derived from where the front is.
3. **FIGHT IT** — in TvT: the real 3D battle (better than PB's charts).
4. **OUTCOME BITES** — casualties, damage, ammo and fuel spent.
5. **CARRY FORWARD** — repairs, resupply, replacements, crew improves.

## The three things that make PB sing

- **ESCALATION** — Germans field better tanks as days pass, while your crew gets better. A race.
- **SETBACK LOOP** — tank lost = replacement with a *green* crew. Real loss, not a reset.
- **STORY** — your tank, named crew, awards. After a month you're playing *a guy*, not a counter.

## One-to-one mapping (PB → TvT plan)

| Patton's Best | TvT big-map plan |
|---|---|
| war-situation map | 2D campaign map |
| mission assignment from the front | which TvT mission you fight next |
| tactical battle (charts) | the real 3D game |
| ammo/fuel/damage/crew carryover | the state-file contract |
| escalating German tanks | enemy OOB hardening as campaign advances |
| replacement tank + green crew | loss + reinforcement logic |

## What PB doesn't have (our addition)

**Force-level logistics.** PB tracks *one tank's* ammo and fuel — not supply columns,
reinforcements, or a whole front. The big-map plan scales PB's loop up to the whole front.
PB = the "player's day"; OpenXcom/TripleA pattern = the "everyone else's day."

## The hook is the API (the state bridge)

- The LOS hook already proves we can get inside the engine (injected DLL) — read its
  brain, change its behaviour.
- **End of mission:** the hook reads the tank's *real* state (damage, ammo, crew, result)
  and writes it to the 2D layer's file. No log-parsing, no guessing.
- **2D layer** reads that file, advances the front, picks the next mission.
- **Next mission:** the hook (or a generated script) puts the carried-over tank back —
  battered or repaired, with its crew.
- Remaining question is measured, not mysterious: *how much state can we read/write
  reliably?* — testable, like the LOS work was.

## Roadmap (in order of importance)

**Part 1 — getting ready (foundation):**
1. Re-apply the 6 verified log-sweep fixes (recursion first), one at a time, play-tested.
2. Reconcile the backlog (doc-only fixes into TODO/CHANGELOG).
3. Re-sync the `TvT\` mirror to the live install.
4. JUDGE — AI picks targets it can actually kill (wire `can_i_kill.py`).
5. DECIDE — finish target acquisition through terrain (LOS second half).
6. Loose ends — `268455937` hunt; ZW fixes.

**Part 2 — PB in TvT (the campaign layer):**
1. **KEYSTONE PROOF:** two missions, one terrain, outcome carries forward.
2. State-bridge prototype (hook reads end-of-mission state).
3. State-file contract (freeze what crosses 2D/3D).
4. The 5-beat day loop (front map + mission selection).
5. Auto-resolver (2D resolution for battles the player doesn't fight).
6. Force-level logistics (supplies, reinforcements, replacements).
7. Escalation + carryover (crew XP, German tanks scarier, green-crew replacements).
8. Theatre layer (multiple sectors, Falcon-4 "bubble") — the horizon.

Headline: Part 1 items 1–3 are weeks; Part 2 items 1–3 are the "is this possible" gate.

## Open-source candidates (repos)

- **OpenXcom** — github.com/OpenXcom/OpenXcom (+ **OXCE** fork OpenXcomExtended) — best
  *architecture* match (geoscape 2D + tactical + carryover).
- **TripleA** — github.com/triplea-game/triplea (Java) — WW2 theme, army-scale.
- **UFO: Alien Invasion** — same X-COM pattern, fully open.
- **VASSAL** — tabletop engine, manual only (no AI).
- **MegaMek** / **Open General** — unit-level tabletop wargame engines.
- **Patton's Best recreation (git)** — github.com/happysulla/PattonsBest (fan, not official).
- Advice: borrow the *architecture*, don't bolt a foreign engine onto G5 (unit stats won't match).

## Status

PARKED, 2026-08-22. Record-only. The user (a non-coder, dyslexic, hyper-pattern-matcher)
generated the core idea and the PB connection; analysis was shaped/verified with AI
assistance. Do not begin work without the user explicitly asking.
