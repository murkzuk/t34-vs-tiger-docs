# T-34 vs. Tiger REDUX — Log-Sweep Findings (FINAL, 2026-08-22)

**Authoritative record.** Merges the 2026-08-21 analysis of the two play-session logs with
the 2026-08-22 independent DeepSeek V4 Pro review. History version (original + corrections
appendix) lives in the analyzer's workspace. All claims verified against live files on
`M:\` and/or the docs mirror.

**STATUS 2026-08-22: REDUX fixes APPLIED then REVERTED the same day, on user request.**
Patches 01-04 were applied byte-safely; a patch-04 trailing comma caused a transient
parse error; the abort left a corrupt 4-byte `Cache\Scripts.cache` that blocked loading.
User asked for a full revert — all four files restored to pristine (byte-identical to the
rollback kit), cache cleared, LOS hook verified intact (never touched). The game is back
to its pre-change state. **Do NOT re-apply patches 01-04 without fresh user consent.**
ZW items (4-6) remain NOT applied. Fix candidates stand as recorded; the revert is about
process trust, not about the fixes' validity (Pro-audited clean before the revert).

---

## Paste-this-to-Claude (when tokens renew)

> This is the T-34 vs Tiger REDUX project. First read
> `C:\Users\Jeff\t34-vs-tiger-docs\FINDINGS_2026-08-21_log_sweep.md` (same content is in
> your memory folder as `project_tvt_2026-08-21_log_sweep_findings.md`), then `HANDOFF.md`.
> Current state (2026-08-22): a log-sweep of two play sessions root-caused 6 issues with
> verified fixes (CC1M2 Infantry2 recursion, `ActivateMove` typo x2, `CKurtenki2Mission`
> menu entry, ZW gun animators `TurnSpeedAnim` commented out, redundant `C_StG_A/B/C`
> Stuka lines, `KurskM1Atmosphere` silencer). They were APPLIED then REVERTED on the
> user's request after a parse-error scare — the game is back to stock, so **do NOT
> re-apply anything without the user's explicit go-ahead.** Patch cards + rollback kit
> live at `K:\TvTDeepseek\patches\REDUX_2026-08-22\` (the menu patch there is already
> comma-corrected). The LOS hook went missing earlier today — root-caused to
> `K:\tvt_los\build.bat` missing `user32.lib` — that is now FIXED (build.bat links
> `user32.lib`) and the hook DLL rebuilt + working. New finding: C1M2's two Tigers are
> `ERT_PASSIVE` by original 2008 design (a reserve wave, not a bug) — see the memory note
> `project_tvt_c1m2_tigers_passive_by_design.md`. Rules that never change: `.script` files
> are CP1251 (never let one make a UTF-8 round trip); delete `Cache\Scripts.cache` after
> any script edit; never place any file inside a game folder (TvT reads every file
> regardless of extension — zip it if a backup must live there). Tell me what you
> understand before changing anything.

---

## Summary

| # | Issue (session) | Final root cause | Final fix candidate |
|---|---|---|---|
| 1 | CC1M2 Infantry2 recursion, 6,451 stack-overflow warnings (REDUX) | `OnPathEndReached` override + 2026-08-18 `OnOrderFulfilled` "restore Patrol" change = re-entry fixed point | Base-class guard + one-shot mission flag (below) |
| 2 | `ActivateMove` not exist on BTR group (REDUX) | Typo; real member is `ActivateMovement` | Rename in 2 files |
| 3 | Menu `SetText` fail, `CKurtenki2Mission_Strings` (REDUX) | Stale 7th `USSR_Missions` entry, class doesn't exist | Remove/fix entry |
| 4 | 36× MovementAnimator load failures (ZW) | `TurnSpeedAnim` commented out in 5 ZW gun animators | Uncomment (or `= "";`) |
| 5 | `C_StG_A/B/C` `ActivateBehavior`/`ShowUnit` errors (ZW) | Invalid group-level calls — but redundant with `ActivateGroup(false)` | Delete the lines |
| 6 | `SetIsCameraAdjustEnabled` on `KurskM1Atmosphere` (ZW) | Missing interface member | Silencer stub (base class preferred) |
| 7 | 447× `can not move to` + 178× Router warnings (ZW) | A* 20000-step budget; mission-authoring issues on the 36 km map | Single-point legs, navpoint spacing |
| 8 | `GroundLevel` joints, locale, `268455937` | Documented mechanisms; `268455937` sender unknown | RE hunt for the sender |

---

## 1. CC1M2 infantry-group recursion — FINAL mechanism

Group: `CC1M2Gr_NGerman_Infantry2` (Campaign 1 Mission 2 "Securing Kurtenki", rated Broken).
Log A lines 21,556 → 29,941: 6,451× `Possible stack overflow in function X, stack depth N`
(depth 101 → 1391). No hard crash; AI loop spun until session end.

**The loop (verified, DeepSeek V4 Pro re-derived):**
1. `ContinueOrder` Attack branch (`Scripts\Common\UnitGroup.script:579-593`) logs
   `[CONTINUE] ... attacking unit ID = ` (blank) at `:582`, then
   `OrderUnitToAttack("_everybody_")` (`:592`).
2. The engine builtin finds nothing engageable → **synchronously fires
   `OnOrderFulfilled`**.
3. `OnOrderFulfilled` (`:668-700`, the REDUX 2026-08-18 version): stack empty but patrol
   path survives → restores `"Patrol"` and calls `RepeatOrder()` (`:682-686`).
4. `RepeatOrder` Patrol branch (`:444-480`): `m_NextPatrolPoint` still == path size
   (never advanced) → clears the order → calls `OnPathEndReached()` again.
5. Mission override `CC1M2Gr_NGerman_Infantry2::OnPathEndReached()` (`Missions\Campaign_1\
   Mission_2\MissionTasks.script:483-491`) re-arms `ActivateRadar(true)` +
   `SetOrder_Attack(KillList, ERT_AGGRESSIVE)` + `ActivateFire(true)` → `ContinueOrder`
   → back to step 1. Fixed point.

**Key facts:**
- The mission override is the **trigger**; the 2026-08-18 `OnOrderFulfilled` "restore
  Patrol" change is the **missing ingredient** making it unbounded (ZW's original
  `OnOrderFulfilled` just clears the order → `[ALARM]`, no recursion).
- The blank `attacking unit ID = ` is a **diagnostic signature, not the cause** — the
  attack goes through the enemy *array* (`SetEnemiesArray`), not `m_TargetObjectID`.
- `[ALARM] No orders in group` ×237 total (232 = Infantry2).
- Other missions with `OnPathEndReached` + `ActivateRadar(true)` overrides: **C1M1**
  (BaseInfantry:341), **C1M2** (Tanks1:241, Tanks2:301, Infantry1:432, Infantry2:483),
  **C1M4** (StugG40:281 — `SetOrder_Attack` already commented out), **C2M4**
  (HiddenForce:826 via `StartAttack()`). NOT C1M3/C2M6/Berezov. Only C1M2 Infantry2
  issues `SetOrder_Attack` inside `OnPathEndReached`.

**Fix (two layers):**
- **Base/systemic:** in `OnOrderFulfilled` (`:668-700`), only restore `"Patrol"` if it can
  advance (`m_NextPatrolPoint < m_PatrolPath.size()`); otherwise clear + hold
  (`SetOrder_Stop()`). Preserves the 2026-08-18 intent (resume after a *mid-patrol*
  attack) while breaking the end-of-path fixed point. **Global change — regression-test
  patrol-resume and static groups.**
- **Mission (defense-in-depth):** one-shot flag in `CC1M2Gr_NGerman_Infantry2::
  OnPathEndReached()` (existing `m_Active`/`Funss` idiom) and/or skip `SetOrder_Attack`
  when no living `KillList` targets remain.

## 2. `ActivateMove` typo

`ActivateMove` exists nowhere (REDUX, WoW, ZW). Real member: `ActivateMovement(boolean)`
(`UnitGroup.script:1474`). Two typo sites: `Missions\Campaign_1\Mission_2\
MissionTasks.script:658` (`ActivateMove(false)` in `CC1M2Gr_EGerman_BTRs::Init()`) and
`Campaign_2\Mission_3\MissionTasks.script:932` (`ActivateMove(true)`).
**Fix:** rename to `ActivateMovement(...)`. CONFIRMED.

## 3. Menu `SetText` failure

Log A L256-259: `Static variable MissionName not found in class CKurtenki2Mission_Strings`
+ `Failed to invoke host function SetText with 1 arguments`
(`Scripts\Menus\MissionsMenu.script:176`). Root cause: `MissionsMenu.script:31` has a 7th
`USSR_Missions` entry `"CKurtenki2Mission"` — no such class exists anywhere. Real classes:
`CC1M2Mission` (`Mission.script:10`) and `CC1M2Mission_Strings`
(`MissionC1M2Strings.script:13`, already uses the fixed `getLocalized()` pattern).
`MissionKurtenki2.rsr` exists in the tree (a mission that never got its script class).
Docs rule: strings class must be named `<MissionClass>_Strings`; literal `WString` fields
are invisible to `getStaticClassMember`. **Fix:** remove the 7th entry or point it at a
real class. CONFIRMED.

## 4. ZW gun animators — commented-out `TurnSpeedAnim`

Log B: 36× `Variable TurnSpeedAnim not found` → `[MovementAnimator] Invalid animator
initialization parameters` → `Failed to load component MovementAnimator` (+ `_Animator`
cascade at `Scripts\Common\Object.script:1374`). **Only 15 of 36 are the FH18**
(`CGunFH18_150mmMovementAnimator`, `Scripts\Units\GunHvyFH18_150mm_Unit.script:37-46`,
line 40 `//  String TurnSpeedAnim = "turret_a";`); the other 21 are ML20_152mmFake ×13,
RK27_76mm ×5, LeFh18_105mm ×2, RK27_76mmLB ×1 — same commented-out line. Working
contrast: `CGunML19_122mm` / `CGunHvyPaK43` keep it active; tanks use `= "";`.
**Fix:** uncomment `String TurnSpeedAnim = "turret_a";` (or `= "";`) in the 5 animator
classes. FH18 model `turret_a` channel: consistent but not verifiable from `.script`
alone. CONFIRMED (count corrected).

## 5. `C_StG_A/B/C` Stuka groups

`C_StG_A` is a **Stuka dive-bomber group** (Stukageschwader), NOT the StuG (that's
`CSAUStuG40Unit`). ZW `Missions\CustomMissions\KurskMission\MissionTasks.script`
calls `ActivateBehavior(false)` / `ShowUnit(false)` **on the group classes** at 796/798,
847/849, 899/901 (in `Stuka1End/2End/3End`). Those are unit-task members (`ShowUnit` =
`BaseTasks.script:1173`; `ActivateBehavior` via `ForEachUnitTask` = `UnitGroup.script:1495`;
groups use `ShowGroup` = `:1449`) — hence the "is not exist" errors. **However, the lines
are redundant:** each `Stuka*End` already calls `ActivateGroup(false)`, which does
`ShowGroup(false)` + `ForEachUnitTask("ActivateBehavior", [false])`.
**Fix:** delete the redundant lines (or replace `ShowUnit(false)` with `ShowGroup(false)`).
CONFIRMED. (File mtime 20/08/2026 17:59 — recent WMTrace work; check for in-flight edits.)

## 6. `KurskM1Atmosphere` `SetIsCameraAdjustEnabled`

`Scripts\Common\BaseAtmosphere.script:140` calls `SetIsCameraAdjustEnabled`, which
`KurskM1Atmosphere` (`CustomMissions\KurskMission\Atmosphere.script:10`) lacks — only
`CC2M2Atmosphere` (`Campaign_2\Mission_2\Atmosphere.script:22`) has a stub.
**Fix:** interface-silencer stub `void SetIsCameraAdjustEnabled(boolean value) { }` —
best in `CBaseAtmosphere`/`CCommonAtmosphere` since every non-C2M2 atmosphere trips it.
CONFIRMED (fix location improved).

## 7. Pathfinding (context for the ZW session)

447× `can not move to` + 178× `[Router] Warning! Path Generated in more than N
iterations` (`AStarSteps = 20000`). Documented machinery: the engine gives up after
**20,000 A* steps**; destinations must be *routable*, not merely passable; navpoint
spacing ~150-180 world units; multi-point `SetOrder_MoveToEx` arrays trip the
`"MoveToEx"` queue tag (Berezov fix = single-point calls; ZW Kursk `C_StG_*` use
3-point arrays at `MissionTasks.script:779-788`). ZW Kursk = 36 km / 4097² heightfield →
router cells ~17.6 m (hardest regime). Berezov's fixes are documented but not applied to
ZW Kursk. TODO:360 (RouterZone color→passability mapping) still open.

## 8. Minor / benign

- **102× `Invalid joint name GroundLevel`:** default `LandingJoints = ["GroundLevel"]`
  (`Object.script:77`) vs models lacking the joint; engine substitutes the mesh — graceful.
- **Locale warnings:** duplicate `[Section]` headers (merge per Messages.rsr doc); ghost
  `str_Death*` keys (TODO:397).
- **`Unsupported command in game script: 268455937`** (13× REDUX, 1× ZW): `0x10005001`
  (arithmetic confirmed) — unknown command id, emitted at `Scripts\Common\Game.script:487`.
  Content-side enum mismatch; **sender unidentified — needs RE**.
- **LOS hook logs healthy:** Session A 5000 calls / 67.1% seen / 25 calls/s; Session B ran
  with `crew = watch` debug mode.

## Process rules (repeated from HANDOFF.md)

- `.script`/`.txt` are **CP1251** — never let one round-trip UTF-8 (destroys Cyrillic).
  Edit byte-level; grep for `\xef\xbf\xbd` before and after.
- **Delete `Cache\Scripts.cache`** after any script edit.
- **Never place any file inside a game folder** (`.bak`, `.md`, anything) — TvT reads all
  files regardless of extension; a stray copy = "Duplicate Class" errors. Backups live
  outside the folder (rollback kit at `K:\TvTDeepseek\rollback\`); if one must be in-folder,
  zip it first.
- Live install: `M:\T34vsTiger` (NOT `M:\T34vsTiger - REDUX0.001`).
- Verify the artefact, not the success message: clear cache → launch
  `TvsT_fullLOD_HARD_4GB.exe` → read `execution.log` (or `editor.log`).
- **Mirror drift:** `TvT\Common\UnitGroup.script` in the docs repo is OUT OF SYNC with
  live (live has 2026-08-19 instrumentation + 2026-08-18 fixes). C1M2 `MissionTasks.script`
  IS identical (MD5 `DC01179B1B06E575C46FC92CAE3CF317` both sides).

## Backlog status (verified 2026-08-21/22)

- Items 1-6 are **not tracked** in TODO.md/CHANGELOG.md. All open.
- Closest documented relatives: `TvT_Mission_Authoring_Verified.md` §4b (three order-stack
  bugs, fixed in code, untracked); Berezov pathfinding saga (fixed, doc-only);
  CHANGELOG 2026-07-03 briefing-menu `MissionName` fix (same family as item 3).

## Suggested next steps

1. REDUX-side branch: items 2, 3 + the two-layer fix for item 1 (base `OnOrderFulfilled`
   guard first, then the mission flag).
2. ZW-side (user's call — payware build): items 4, 5, 6.
3. RE hunt for the sender of `268455937` (item 8).
4. Reconcile the backlog: several "fixed" findings live only in Documentation files.

---

## Follow-up 2026-08-22 — C1M2 Tigers are passive BY DESIGN (original 2008)

Investigating "why didn't the 2 Tigers take the kill shot" (player in a T-34, CC1M2
"Securing Kurtenki") found the PRIMARY cause is scripted, not the LOS hook:

- Group CC1M2Gr_EGerman_Tanks2 (units EGerman_Tank2_1/_2) is GroupEnemyReaction =
  ERT_PASSIVE, DelayedOrder = true. ORIGINAL design - ERT_PASSIVE present in the first
  git commit (3b88cf1); MD5 identical across live M:\T34vsTiger, repo mirror, and stale
  M:\T34vsTiger - REDUX0.001.
- They are a RESERVE wave (not passive-for-fairness). Wave 1 = PzIVs + BTRs + infantry;
  the Tigers hold passive on a ~413 m patrol (NP_EGerman_Tigers_PP_1 5159.8,3075.3 ->
  NP_EGerman_Tanks2_TigerPoint 4766.0,3198.9).
- Triggers that flip ERT_AGGRESSIVE (Mission.script): kill a KillList_TigersA1 Tiger
  (~L214-221); KillList_TigersA1/A2 empty (~L232-239); AggrEastGTanks() (~L437-444).
- In both recent sessions TigersContinue fired 0 times -> Tigers never activated.
- Position match (tvt_los.log): actual Tigers at (4731,3165) and (4689,3226) - 49-82 m
  from route - logged SEEN; the terrain-DENIED close-range sightings were mostly OTHER
  units, not the Tigers.
- Verdict: not the LOS hook, not weak AI - the mission tells the Tigers to hold fire.
  One-word change to make them hunt: ERT_PASSIVE -> ERT_AGGRESSIVE (or force
  TigersContinue) - do NOT do without the user asking.