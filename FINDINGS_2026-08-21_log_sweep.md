# FINDINGS — 2026-08-21 log sweep (2 play sessions)

Source: read-only analysis by a separate DeepSeek agent working from its own copy at
`K:\TvTDeepseek\t34-vs-tiger-docs`. Nothing in any game install or this repo was
modified. All claims cross-checked against the live files on `M:\` and/or the docs
mirror. Backlog status verified by full sweep of `TODO.md` + `CHANGELOG.md`.

## Scope

- Session A: `M:\T34vsTiger\execution.log` (21/08/2026 08:48, REDUX v0.260821,
  Campaign 1 Mission 2 "Securing Kurtenki").
- Session B: `M:\T34vsTiger_ZW2015\execution.log` (21/08/2026 16:44, ZW KurskMission).
- Both ran with `tvt_los_hook` attached. Neither session hard-crashed.

## 1. CC1M2 infantry-group infinite recursion (Session A) — CRITICAL

- **6,451×** `Possible stack overflow in function X, stack depth N` (depth 101 → 1391),
  log lines 21,556 → 29,941 (end of file). No hard crash; the group's AI loop spun
  until the session ended.
- **Root cause:** `CC1M2Gr_NGerman_Infantry2::OnPathEndReached()` override at
  `Missions\Campaign_1\Mission_2\MissionTasks.script:483-491` unconditionally re-arms
  `ActivateRadar(true)` + `SetOrder_Attack(KillList, ERT_AGGRESSIVE)` + `ActivateFire(true)`
  on every patrol end. Each synchronously fans `OnRadarUpdate` into every unit task
  (`Scripts\Common\UnitGroup.script:1437-1447`) → `OnEnemyTargeted` → `SetOrder_Attack`
  → `ContinueOrder` (UnitGroup.script:1024) → `RepeatOrder` → patrol → path end →
  `OnPathEndReached`… all on one call stack, with an empty target
  (`[CONTINUE] ... attacking unit ID = ` blank) and an empty order stack
  (`[ALARM] No orders in group` ×237).
- The 2026-08-18 engine fix for the order-stack leak (UnitGroup.script:1039-1045 guard)
  IS in the live install but does not stop this re-entry loop.
- **Pattern is systemic** (same override shape): C1M1, C1M3, C2M4, C2M6, Berezov.
- **Fix candidate (mission level):** guard the override — only re-arm once (flag), or
  skip when no living targets remain.
- Docs: `TvT_Mission_Authoring_Verified.md` §4b documents the three engine order bugs
  (bug 1: `OnOrderFulfilled` destroys an order it cannot restore; bug 2: static groups
  stranding; bug 3: order-stack leak via `SetOrder_Attack([], ERT_AGGRESSIVE)`). This
  specific recursion is NOT tracked in TODO.md/CHANGELOG.md.

## 2. `ActivateMove` typo (Session A) — confirmed bug

- `Missions\Campaign_1\Mission_2\MissionTasks.script:658` —
  `CC1M2Gr_EGerman_BTRs::Init()` calls `ActivateMove(false);`. No such member exists
  anywhere (REDUX, WoV, ZW concatenated). Real member:
  `ActivateMovement(boolean)` (`Scripts\Common\UnitGroup.script:1432`).
- Same typo at `Campaign_2\Mission_3\MissionTasks.script:932`.
- **Fix candidate:** rename to `ActivateMovement(false)`.

## 3. Menu SetText failure (Session A) — stale mission entry

- Log L256-259: `Static variable MissionName not found in class CKurtenki2Mission_Strings`
  + `Failed to invoke host function SetText with 1 arguments`
  (`Scripts\Menus\MissionsMenu.script:176`).
- **Root cause:** `MissionsMenu.script:31` (live install) has a 7th `USSR_Missions`
  entry `"CKurtenki2Mission"` — no such class exists. Real classes:
  `CC1M2Mission` (`Mission.script:10`) and `CC1M2Mission_Strings`
  (`MissionC1M2Strings.script:13`, already uses `getLocalized` — the fixed pattern).
- Docs rule (Mission_File_Schema doc): the strings class must be named
  `<MissionClass>_Strings`; literal `WString` fields are invisible to
  `getStaticClassMember` (TODO:384; CHANGELOG 2026-07-03 briefing-menu fix).
- **Fix candidate:** remove the `"CKurtenki2Mission"` entry (or point it at a real
  class). `MissionKurtenki2.rsr` exists in the tree — possibly a planned custom
  mission that never got its script class.

## 4. FH18 howitzer animator failures ×36 (Session B)

- `M:\T34vsTiger_ZW2015\Scripts\Units\GunHvyFH18_150mm_Unit.script:40` —
  `//  String TurnSpeedAnim = "turret_a";` is **commented out**. The engine's
  `MovementAnimator` requires the member → `Variable TurnSpeedAnim not found` →
  `[MovementAnimator] Invalid animator initialization parameters` →
  `Failed to load component MovementAnimator` ×36 → `_Animator` cascade
  (`Scripts\Common\Object.script:1374`).
- Same commented-out pattern in 6 other ZW gun animators (ML20, RK27, sIG33, LeFh18).
  Working contrast: `CGunML19_122mmMovementAnimator` / `CGunHvyPaK43MovementAnimator`
  keep it active. The FH18 model exports a `turret_a` channel.
- **Fix candidate:** uncomment line 40. (ZW install is a separate build; ZW scripts
  are payware-preserved — treat with care.)

## 5. `C_StG_A/B/C` Stuka group errors (Session B)

- **NOTE:** `C_StG_A` is a STUKA dive-bomber group (Stukageschwader), NOT the StuG
  assault gun (that's `CSAUStuG40Unit`). See
  `TVT_Mission_Script_Format_Complete_Reference GOLD.md:344-351`.
- ZW `Missions\CustomMissions\KurskMission\MissionTasks.script` calls
  `ActivateBehavior(false)` and `ShowUnit(false)` **directly on the group classes** at
  796/798 (C_StG_A), 847/849 (C_StG_B), 899/901 (C_StG_C). Both are unit-task members,
  not group members: `ShowUnit` at `Scripts\Common\BaseTasks.script:1166`;
  `ActivateBehavior` is dispatched via `ForEachUnitTask` (UnitGroup.script:1453).
  Groups use `ShowGroup`.
- **Fix candidate:** `ForEachUnitTask("ActivateBehavior", [false]);` /
  `ForEachUnitTask("ShowUnit", [false]);`.
- That file was modified 20/08/2026 17:59 — recent work (WMTrace cleanup per TODO:447).
  Check for in-flight changes before editing.

## 6. `KurskM1Atmosphere` `SetIsCameraAdjustEnabled` (Session B)

- `Scripts\Common\BaseAtmosphere.script` (~140) calls `SetIsCameraAdjustEnabled`, which
  `KurskM1Atmosphere` lacks.
- **Documented fix recipe:** interface-silencer stub —
  `ZeeWolf Mod REDUX Technical Fix Documentation.md:37-51` (CC2M2Atmosphere
  precedent): add `void SetIsCameraAdjustEnabled(boolean value) { }`.

## 7. Pathfinding: 447× can-not-move + 178× Router warnings (Session B)

- Documented machinery: engine A* budget **20000 steps**
  (`TvT_Mission_Authoring_Verified.md`; `Tools\MissionEditor\server.py`
  `ENGINE_ASTAR_BUDGET = 20000`). Destination must be *routable*, not just passable.
  Navpoint spacing ~150-180 world units. Multi-point `SetOrder_MoveToEx` arrays trip
  the `"MoveToEx"` queue tag (Berezov doc; fixed by splitting into single-point calls).
  ZW Kursk `C_StG_*` groups use 3-point arrays (MissionTasks.script:779-788).
- ZW Kursk is 36 km / 4097² heightfield → router cells ~17.6 m — the hardest regime.
- Berezov's fixes are documented but not applied to ZW Kursk. TODO:360 (RouterZone
  color→passability mapping) still open.

## 8. Minor / benign

- **102× `Invalid joint name GroundLevel`:** default `LandingJoints = ["GroundLevel"]`
  (`Object.script:77`) vs models lacking that joint; engine substitutes the mesh —
  graceful fallback, no action needed.
- **Locale warnings:** duplicate `[Section]` headers (merge procedure in the
  Messages.rsr doc); ghost `str_Death*` keys (TODO:397).
- **`Unsupported command in game script: 268455937`** (13× REDUX, 1× ZW):
  `0x10005001` — unknown command id, emitted at `Scripts\Common\Game.script:487`.
  Content-side command-enum mismatch; the sender is unidentified — needs RE.
- **LOS hook logs healthy:** Session A 5000 calls / 67.1% seen / 25 calls/s;
  Session B ran with `crew = watch` debug mode (CTankAutoThingControl +0x9CD gate dumps).

## Process rules (already in HANDOFF.md — repeated for safety)

- `.script`/`.txt` are **CP1251** — never let one round-trip UTF-8 (destroys Cyrillic).
  Edit byte-level; grep for `\xef\xbf\xbd` before and after.
- **Delete `Cache\Scripts.cache`** after any script edit.
- Live install: `M:\T34vsTiger` (NOT `M:\T34vsTiger - REDUX0.001`).
- Verify the artefact, not the success message: clear cache → launch
  `TvsT_fullLOD_HARD_4GB.exe` → read `execution.log` (or `editor.log`).
- **Mirror drift:** `TvT\Common\UnitGroup.script` in the docs repo is OUT OF SYNC with
  live (live has the 2026-08-19 `[PATROL]`/`[CONTINUE]` instrumentation + the
  2026-08-18 order-stack fix; the mirror does not). C1M2 `MissionTasks.script` IS
  identical (MD5 `DC01179B1B06E575C46FC92CAE3CF317` both sides).

## Backlog status (verified 2026-08-21)

- None of items 1-6 is tracked in TODO.md or CHANGELOG.md. All are open.
- Closest documented relatives: `TvT_Mission_Authoring_Verified.md` §4b (order bugs,
  fixed in code, untracked in backlog); Berezov pathfinding saga (fixed, doc-only);
  CHANGELOG 2026-07-03 briefing-menu `MissionName` fix (same family as item 3).

## Suggested next steps

1. REDUX-side, one branch: fix items 2, 3 + a guarded `OnPathEndReached` for item 1.
2. ZW-side (user's call — payware build): items 4, 5, 6.
3. RE hunt for the sender of `268455937` (item 8).
4. Reconcile the backlog: several "fixed" findings live only in Documentation files.

---

## 2026-08-22 — Second opinion (DeepSeek V4 Pro) corrections

An independent pass by DeepSeek V4 Pro re-derived everything from the raw logs/scripts (without seeing this doc), then reviewed it. All mechanical fixes CONFIRMED; the recursion analysis and several details corrected:

1. **Recursion mechanism (item 1) — corrected.** The tight loop is NOT primarily radar-driven. Actual chain: ContinueOrder Attack branch (UnitGroup.script:579-593) -> OrderUnitToAttack("_everybody_") (builtin) finds nothing -> synchronously fires OnOrderFulfilled -> the 2026-08-18 REDUX OnOrderFulfilled (:668-700) restores "Patrol" when the stack is empty but a patrol path survives (:682-686) -> RepeatOrder Patrol branch (:444-480) sees m_NextPatrolPoint == size (never advanced) -> clears order -> OnPathEndReached -> mission override (MissionTasks.script:483-491) re-arms ActivateRadar(true)+SetOrder_Attack -> ContinueOrder -> fixed point. The mission override is the TRIGGER; the 2026-08-18 OnOrderFulfilled "restore Patrol" change is the missing ingredient that makes it unbounded (ZW's original OnOrderFulfilled just clears the order -> ALARM, no recursion).
   - Line refs: ActivateRadar is UnitGroup.script:1485-1489 (not 1437-1447); SetOrder_Attack's ContinueOrder tail is :1066 (not 1024).
2. **"Systemic pattern" list (item 1) — corrected.** OnPathEndReached+ActivateRadar(true) overrides exist in C1M1 (BaseInfantry:341), C1M2 (Tanks1:241, Tanks2:301, Infantry1:432, Infantry2:483), C1M4 (StugG40:281 - SetOrder_Attack already commented out), C2M4 (HiddenForce:826 via StartAttack). NOT C1M3, C2M6, or Berezov. Only C1M2 Infantry2 issues SetOrder_Attack inside OnPathEndReached.
3. **FH18 counts (item 4) — corrected.** Only 15 of the 36 MovementAnimator failures are CGunFH18_150mmMovementAnimator; the other 21 are ML20_152mmFake x13, RK27_76mm x5, LeFh18_105mm x2, RK27_76mmLB x1 (same commented-out TurnSpeedAnim pattern). FH18 fix unchanged (uncomment line 40; equal alternative: String TurnSpeedAnim = ""; per the tank idiom).
4. **Line-number corrections:** ActivateMovement is UnitGroup.script:1474 (not 1432); ShowUnit is BaseTasks.script:1173 (not 1166); ForEachUnitTask("ActivateBehavior",...) is :1495 (not 1453).
5. **C_StG_A fix (item 5) — simplified.** The ActivateBehavior/ShowUnit lines at 796/798, 847/849, 899/901 are REDUNDANT: Stuka*End already calls ActivateGroup(false), which does ShowGroup(false) + ForEachUnitTask("ActivateBehavior",[false]). Cleanest fix: delete the redundant lines (or replace ShowUnit(false) with ShowGroup(false)).
6. **SetIsCameraAdjustEnabled (item 6) — better fix location.** The CC2M2 precedent stub confirmed (C2M2 Atmosphere.script:22); consider fixing in CBaseAtmosphere/CCommonAtmosphere since every non-C2M2 atmosphere trips it.
7. **Recommended recursion fix (two layers):**
   - Engine/base (systemic): in OnOrderFulfilled (:668-700), only restore "Patrol" if it can advance (m_NextPatrolPoint < m_PatrolPath.size()); otherwise clear and hold (SetOrder_Stop()). Preserves the 2026-08-18 intent (resume mid-patrol attack) while breaking the end-of-path fixed point. GLOBAL change - regression-test patrol-resume and static groups.
   - Mission (defense-in-depth): one-shot flag in CC1M2Gr_NGerman_Infantry2::OnPathEndReached() (existing m_Active/Funss idiom) and/or skip SetOrder_Attack when no living KillList targets remain.
8. Item 8's 268455937 = 0x10005001 arithmetic confirmed; minor counts not re-verified. Item 4f (FH18 model exports turret_a) marked UNCERTAIN - not verifiable from .script alone, but consistent with the targeting animator using turret_a.