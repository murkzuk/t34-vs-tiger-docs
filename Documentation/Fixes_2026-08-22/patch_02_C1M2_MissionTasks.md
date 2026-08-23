# PATCH 02 — Mission 2: misspelled command + "only once" guard

**File (live install):** `M:\T34vsTiger\Missions\Campaign_1\Mission_2\MissionTasks.script`
Two separate edits in this one file.

## Edit 2a — misspelled command (line 658)

**Plain words:** the half-track (BTR) group's setup calls a command that doesn't exist
(`ActivateMove`). The real command is `ActivateMovement`. So the engine logs an error
every time. Renaming fixes it. (Same typo exists in Campaign 2 Mission 3 — see patch_03.)

### OLD (line 658, inside `CC1M2Gr_EGerman_BTRs::Init()`)

```c
    ActivateMove(false);
```

### NEW

```c
    ActivateMovement(false);
```

## Edit 2b — "only do this once" guard (lines 483-491)

**Plain words:** the German infantry group re-arms its radar + attack order every time it
finishes its road, which (with patch_01's context) is the trigger for the loop. This adds
a one-time switch: arm once, then never again. Belt-and-braces on top of patch_01.

Also add the switch itself next to the class's existing flag (line 466).

### OLD (line 466)

```c
  boolean Funss = false;
```

### NEW

```c
  boolean Funss = false;
  boolean RadarArmed = false;
```

### OLD (lines 483-491, `CC1M2Gr_NGerman_Infantry2::OnPathEndReached()`)

```c
  void OnPathEndReached()
  {
    CBaseUnitGroup::OnPathEndReached();
    ActivateRadar(true);
    SetOrder_Attack(KillList, ERT_AGGRESSIVE);
    ActivateFire(true);
    RefreshUnitsList();
    fireEvent(0.0,  [], "AttackGermanInfantry2", [m_Units]);
  }
```

### NEW

```c
  void OnPathEndReached()
  {
    CBaseUnitGroup::OnPathEndReached();
    if (!RadarArmed)
    {
      RadarArmed = true;
      ActivateRadar(true);
      SetOrder_Attack(KillList, ERT_AGGRESSIVE);
      ActivateFire(true);
      RefreshUnitsList();
      fireEvent(0.0,  [], "AttackGermanInfantry2", [m_Units]);
    }
  }
```

## Apply byte-safely

- Read with `[System.Text.Encoding]::GetEncoding(1252)`; replace the exact OLD blocks
  (preserve CRLF); write back same encoding. No editor.
- Backup: the pristine copy already exists at `K:\TvTDeepseek\rollback\REDUX_2026-08-22\C1M2_MissionTasks.script`.
  Do NOT create a `.bak` inside the game folder — TvT reads every file regardless of
  extension, so a stray copy = "Duplicate Class" errors. If an in-folder backup is ever
  needed, zip it.
- After: grep for `\xef\xbf\xbd` (zero hits) → delete `M:\T34vsTiger\Cache\Scripts.cache`.

## Verify

- `ActivateMove` no longer appears in this file; `ActivateMovement(false)` does.
- `RadarArmed` appears exactly 3 times (declaration + `if (!RadarArmed)` + `RadarArmed = true;`).
- In-game: Mission 2, the loop must not start; the `[ScriptManager]` `ActivateMove` error
  must be gone from `execution.log`.
