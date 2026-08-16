# Berezov River Ford + Advance Chain — 2026-08-16 (Phase 2, outcome record)

Session record. Testing was paused by the user after this phase — everything below is
BFS-verified on the router data, **not** verified in-game.

## The river problem
- `hwater.raw` is a flat constant 7785 everywhere (2049×2049×2, 16-bit LE). Water exists
  wherever the terrain (`hmap.raw`) is below 7785.
- The wet river network in the Berezov–Gremuchi–Gonki corridor is **one connected component**:
  rows 747–1023 (world y 6565–8991), cols 412–791 (world x 3621–6952), 1,709 cells at 1024
  resolution. It reaches the map's south edge.
- Flood analysis: **Gonki (5437, 6722) is on a river island.** The dry pocket containing
  GonkiObjective, WP28–34 and the village (5,701 cells) has **zero** boundary cells adjacent
  to reachable dry ground — the ring is 100% wet. No bridge exists anywhere on the map.
- Every west→east crossing attempt (4- and 8-neighbor BFS) between WP27 and WP28 failed.

## The ford
- The river's narrowest point is its "west arm" tip: rows 762–778 (y 6697–6838), only ~10
  cells wide, world x ≈ 4563–4640.
- Raised 560 raw heightmap cells (rows 1523–1559, cols 985–1093) to 7820 (35 above water
  level) in `hmap.raw` — applied identically to live `M:\T34vsTiger\...\Berezov\hmap.raw`
  and the repo mirror. The water simply recedes there (dry ground, no visual artifacts).
- Ford cells in the router layer repainted to passable (index 1).

## Router rebuild (wet = blocked)
- All wet cells painted index 217 (blocked, matching the terrain river zone):
  - live 1024×1024: 9,463 cells; file size 1,049,656 B (field + 2 ✓)
  - repo 2048×2048: 27,047 cells; file size 4,195,384 B (field + 2 ✓)
- Gotcha recorded: the wet→217 rebuild must be re-run after any hmap change, and stale 217
  cells that are no longer wet must be repainted (139 live / 431 repo were stale after the ford).

## Waypoint chain reroute (Content.script, live + repo)
| WP | old | new |
|----|-----|-----|
| 22 | 3634, 6473 | 3634, 6411 |
| 23 | 3722, 6622 | 3900, 6411 |
| 24 | 3792, 6781 | 4166, 6411 |
| 25 | 3933, 6904 | 4433, 6411 |
| 26 | 4091, 6939 | 4600, 6411 |
| 27 | 4258, 6939 | 4600, 6840 |

The chain now arcs north of the river at y 6411, descends through the ford at x 4600,
then east/south to Gonki. WP28–34 and GonkiObjective unchanged.

## Verification (BFS, 4-neighbor, on the rebuilt live router)
- All 34 chain legs pass, 0 fails. Spawns all dry + passable.
- Long detour legs noted (reachable, but the A* will march far): WP4→WP5 = 258 cells,
  WP18→WP19 = 241 cells.

## The maneuver bug (why the AI stopped at the first waypoint)
- Second test log: the groups received the full order queue (`SetOrder_MoveToEx` expands to
  one `MoveToEx` order per waypoint, waiter `OnLeaderStopped`), but during the spawn-area
  battle the ERT_PASSIVE groups responded to enemy contact with the group **Maneuver**
  response. When the maneuver ended:
  - `[STOPPED] Group BerezovKGKaiser end maneuvering`
  - `RepeatOrder() : popping order` → `ContinueOrder()` → `[ALARM] No orders in group
    BerezovKGKaiser task script`
- The order stack was empty at `EndManeuver` (script `UnitGroup.script`: `TryToManeuver`
  only pushes when `m_CurrentOrder.m_Order != ""`, and the queue-based chain doesn't keep a
  current order) — so the maneuver permanently eats the waypoint chain.
- Fix: `isManeuver = false;` added at the top of `StartFirstAdvance` in all 4 German advance
  task classes (`MissionTasks.script`, live + repo). `isManeuver` is only ever set true in
  the group's `Init()` (based on the unit tasks' `m_MeneuveringUnit` flag), so this sticks.
- Player unit moved forward 50 m along its facing: (496.0, 6849.5) → (530.4, 6885.7).

## Test session outcome (the "shit show")
- The follow-up editor session **never loaded the mission**: `editor.log` ends at the
  startup script-class dump — no `Start game`, no mission object loads. No in-game data for
  the maneuver fix or the ford.
- First log line: `Can not assign value (error) to typed variable (String)` — appears
  pre-existing at the top of every session log (unconfirmed whether it's fatal).
- Open items: (1) in-game verify the advance end-to-end; (2) the startup crash/session
  abort cause; (3) WP4→WP5 / WP18→WP19 detour legs.

## Files touched (all live + repo mirror)
- `Content.script` — WP22–27 reroute, MainPlayerUnit +50 m
- `MissionTasks.script` — isManeuver = false ×4
- `hmap.raw` — ford raise (560 cells)
- `RouterZone_Test.bmp` — road fix (Phase 1) + wet→217 + ford repaint