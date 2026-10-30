# C1M2 crash-to-desktop — FIXED, 2026-08-25

A real crash-to-desktop in Campaign 1 Mission 2, diagnosed 2026-08-21, patch
written 2026-08-22, then **parked and never applied**. Rediscovered when it
crashed a play session, applied, and confirmed fixed with a full mission played
to a proper ending.

## The result

| | before | after |
|---|---|---|
| `Possible stack overflow` warnings | **6,451** | **0** |
| max stack depth | 1,391 | none |
| `CC1M2Gr_NGerman_Infantry2` log lines | **1,395** | **11** |
| `[ALARM] No orders in group` | 143 | 4 (unrelated tank groups) |
| outcome | **crash to desktop** | clean exit, mission played to the end |

## What was happening

One AI group — `CC1M2Gr_NGerman_Infantry2` — reached the end of its patrol path
and re-entered its own order handler forever:

```
OrderUnitToAttack -> OnOrderFulfilled -> restore "Patrol" -> RepeatOrder
   -> at end-of-path (m_NextPatrolPoint == size) -> OnPathEndReached
   -> mission override re-arms the attack -> ContinueOrder -> ...
```

The script interpreter warned all the way up (`Possible stack overflow ...
stack depth 1387, 1388, 1389 ...`) and the process died at depth 1391.

The 2026-08-18 REDUX change to `OnOrderFulfilled` — which made groups resume a
patrol after being interrupted by a fight — is what accidentally opened this.
It resumed the patrol **even when the patrol was already finished**.

## The fix

`Scripts\Common\UnitGroup.script`, `OnOrderFulfilled()`, one added condition:

```c
      if (!m_CurrentOrder.m_PatrolPath.isEmpty()
+         && m_CurrentOrder.m_NextPatrolPoint < m_CurrentOrder.m_PatrolPath.size())
      {
        m_CurrentOrder.m_Order = "Patrol";
        RepeatOrder();
        return;
      }
```

"Only resume the patrol if there is road left." An exhausted patrol now falls
through into the static-group branch immediately below, which sets
`SetOrder_Stop()` and deliberately does **not** re-enter `RepeatOrder()`.

This is patch 01 of the parked pair in
`K:\TvTDeepseek\patches\REDUX_2026-08-22\`. It was applied and
confirmed **alone**, on its own test run, because this file is shared by every
mission. Patch 02 followed afterwards — see below.

## The regression that had to be ruled out

`UnitGroup.script` is shared by **every mission**, which is exactly why the
patch's own note said to apply it alone on its own test run. The risk was making
the guard too strict and leaving groups inert after a fight, undoing the
2026-08-18 improvement.

Measured on the confirming run:

```
patrol resumptions (RepeatOrder : Patrol order)   80
groups that went inert (SetOrder_Stop)             0
```

**Groups attacked mid-patrol still resume their route.** The guard only blocks
resumption when the patrol is genuinely exhausted, which is the loop and nothing
else.

## Verification method

Deliberately plain: the game launched **normally** — no injection, no cache, no
probe — so the patch was the only variable. A full mission played to a real
ending (killed by a Tiger), which exercises patrols, combat and the AI order
stack far better than a stationary camera does.

## Applying it byte-safely (for the record)

- Read/write as bytes, exact block replace, CRLF preserved. No editor.
- `grep -c $'\xef\xbf\xbd'` = 0 before **and** after.
- Braces / brackets / parens balanced after the edit (229/229, 247/247, 959/959).
- `m_NextPatrolPoint` confirmed to be a real `int` field (declared line 43)
  rather than assumed.
- Backup **outside** the game folder:
  `K:\TvTDeepseek\rollback\UnitGroup.script.before_patch01_20260825`, and the
  pre-existing pristine copy at `rollback\REDUX_2026-08-22\` was verified
  byte-identical to the live file first.
- `Cache\Scripts.cache` deleted.

## Patch 02 — ALSO APPLIED, same day

Applied after 01 was confirmed. Two edits to
`Missions\Campaign_1\Mission_2\MissionTasks.script`:

1. **`ActivateMove(false)` -> `ActivateMovement(false)`** (line 658). The
   misspelled name does not exist, so the engine logged a `[ScriptManager]`
   error every mission load. `ActivateMovement` was verified to be a real
   command first — it is used throughout `Scripts\Common\BaseTasks.script` —
   rather than trusting the patch note. **The same typo still exists in
   Campaign 2 Mission 3 line 932 (`ActivateMove(true)`), NOT yet fixed.**
2. **A `RadarArmed` one-shot guard** on
   `CC1M2Gr_NGerman_Infantry2::OnPathEndReached()`, so it re-arms its attack
   order once instead of every time. Belt-and-braces: patch 01 already fixed the
   root cause, so this is defence in depth rather than a needed fix.

Verified: `RadarArmed` appears exactly 3 times, `ActivateMove(` 0 times,
0 replacement chars, braces/brackets/parens balanced (93/93, 44/44, 349/349).
Backup at `K:\TvTDeepseek\rollback\C1M2_MissionTasks.before_patch02_20260825`.

### THE TRAP THIS PATCH CONTAINS — worth reading before touching it again

The OLD block for edit 2 is **not unique on its first six lines**.
`CC1M2Gr_NGerman_Infantry1` (line 432) has a near-identical `OnPathEndReached`,
and a careless string replace would silently patch the wrong group.

The full nine-line block including
`fireEvent(... "AttackGermanInfantry2" ...)` **is** unique and is the correct
anchor. Confirmed by counting matches before replacing, and confirmed after by
checking Infantry1 was left untouched.

Infantry1 was never at risk of the loop anyway: its handler only calls
`ActivateRadar(true)` and never re-arms an attack.

## Why this sat unapplied for three days

Unknown. Diagnosed 21st, written and reviewed 22nd, reverted/parked, untracked
in both TODO and CHANGELOG. It then crashed a real play session on the 25th.

**The lesson is about bookkeeping, not code:** a diagnosed, written, reviewed
fix that is not on the board does not exist. It cost a crash and a wasted test
session — the crash initially looked like it might have been caused by an
injected performance cache being trialled at the time, which took real work to
rule out.
