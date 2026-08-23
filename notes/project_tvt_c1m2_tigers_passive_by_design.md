# C1M2 Tigers are ERT_PASSIVE by design — not the LOS hook, not weak AI

Campaign 1 Mission 2 ("Securing Kurtenki", CC1M2) has two Tigers — `EGerman_Tank2_1`
and `EGerman_Tank2_2` — in group `CC1M2Gr_EGerman_Tanks2`, set to
`GroupEnemyReaction = ERT_PASSIVE` with `DelayedOrder = true`.

**This is ORIGINAL 2008 design, not a REDUX/AI change.** `ERT_PASSIVE` is present in the
first git commit of the file (3b88cf1), and the file's MD5 is identical across the live
install (`M:\T34vsTiger`), the repo mirror, and the stale `M:\T34vsTiger - REDUX0.001`.

## What they actually are: a RESERVE wave, not passive-for-fairness

- Wave 1 (the fair fight) = Panzer IVs (`EGerman_Tanks1`) + BTRs + infantry, active first.
- The Tigers hold passive and delayed, patrolling a ~413 m one-way line:
  - `NP_EGerman_Tigers_PP_1` = (5159.8, 3075.3)
  - `NP_EGerman_Tanks2_TigerPoint` = (4766.0, 3198.9)
  - MovingSpeed 6.5, CyclePath false.

## The triggers that flip them ERT_AGGRESSIVE (Mission.script)

1. killing a Tiger in `KillList_TigersA1` (~L214-221), or
2. `KillList_TigersA1.size()==0 || KillList_TigersA2.size()==0` (~L232-239), or
3. `AggrEastGTanks()` — sets both Tanks1 and Tanks2 aggressive (~L437-444).

In both recent play sessions (21/08 and 22/08) `TigersContinue` fired **0 times**, so the
Tigers never activated and just patrolled, never engaging.

## "Why didn't the Tigers take the kill shot?" — three layers

1. **PRIMARY: scripted hold-fire.** The mission never switched them on. Not the LOS
   hook, not weak AI.
2. **SECONDARY: the LOS hook, where it applied.** Some close-range sight-lines were
   terrain-denied (`masked 100%, no vegetation`) — the hook correctly blocked blind
   shots. But position-matching showed the *actual Tigers* (at (4731,3165) and
   (4689,3226), 49-82 m from their route) logged **SEEN**; many of the DENIED
   close-range entries were OTHER units, not the Tigers.
3. **TERTIARY: the old targeting brain** (radar latency ~3-4.5 s, target priority,
   range-not-lethality) — only matters once they are aggressive, which they were not.

## One-word change to make them hunt (do NOT do without the user asking)

`Content.script` C1M2 → `ERT_PASSIVE` → `ERT_AGGRESSIVE` on `CC1M2Gr_EGerman_Tanks2`,
or force `TigersContinue` to fire earlier. Useful if the user ever wants a real test of
the LOS hook, or just a more dangerous mission.

See also: `project_tvt_2026-08-21_log_sweep_findings.md` (the log sweep this came from).
