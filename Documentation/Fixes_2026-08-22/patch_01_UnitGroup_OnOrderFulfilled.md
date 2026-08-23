# PATCH 01 — Stop the endless infantry-group loop (the big one)

**File (live install):** `M:\T34vsTiger\Scripts\Common\UnitGroup.script`
**Function:** `OnOrderFulfilled()` — currently lines 668-700, change is lines 682-687.
**Plain words:** when a group's order finishes, the game tries to put it back on patrol —
but if the patrol was already finished, this restarts a loop forever. This change says
"only resume the patrol if there is still road left; otherwise park the group."
**Why now:** the 2026-08-18 REDUX fix here is what (accidentally) lets the loop happen.
This keeps that fix's benefit (resume after a mid-patrol attack) and removes the loop.
**Risk:** touches shared code used by every mission. Test that groups still resume patrol
after a normal attack, and that static (dug-in) groups just hold position. **Apply this one
alone first, on its own test run.**

## OLD (replace exactly this block, lines 682-687)

```c
      if (!m_CurrentOrder.m_PatrolPath.isEmpty())
      {
        m_CurrentOrder.m_Order = "Patrol";
        RepeatOrder();
        return;
      }
```

## NEW

```c
      if (!m_CurrentOrder.m_PatrolPath.isEmpty()
          && m_CurrentOrder.m_NextPatrolPoint < m_CurrentOrder.m_PatrolPath.size())
      {
        m_CurrentOrder.m_Order = "Patrol";
        RepeatOrder();
        return;
      }
```

## Apply byte-safely

- Read the file with `[System.Text.Encoding]::GetEncoding(1252)`; do a **string replace of
  the exact OLD block above** (preserve CRLF line endings); write back with the same
  encoding. Do NOT open in an editor.
- Backup: the pristine copy already exists at `K:\TvTDeepseek\rollback\REDUX_2026-08-22\UnitGroup.script`.
  Do NOT create a `.bak` inside the game folder — TvT reads every file regardless of
  extension, so a stray copy = "Duplicate Class" errors. If an in-folder backup is ever
  needed, zip it.
- After: grep the file for `\xef\xbf\xbd` — must be zero hits. Then delete
  `M:\T34vsTiger\Cache\Scripts.cache`.

## Verify (matches the findings doc item 1, V4 Pro review)

- Re-entry fixed point: `OrderUnitToAttack` → `OnOrderFulfilled` → restore "Patrol" →
  `RepeatOrder` at end-of-path (`m_NextPatrolPoint == size`) → `OnPathEndReached` →
  mission override re-arms attack → `ContinueOrder` → … With the guard, an exhausted
  patrol falls into the existing static-group branch below (clear + `SetOrder_Stop()`),
  which does not re-enter `RepeatOrder()`.
- Regression watch: a group attacked **mid-patrol** must still resume the patrol at the
  next point (that was the 2026-08-18 fix's purpose; `SetOrder_Attack` never touches
  `m_PatrolPath`/`m_NextPatrolPoint`, so they survive).
