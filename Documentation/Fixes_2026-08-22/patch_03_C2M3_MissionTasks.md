# PATCH 03 — Campaign 2 Mission 3: same misspelled command

**File (live install):** `M:\T34vsTiger\Missions\Campaign_2\Mission_3\MissionTasks.script`
**Plain words:** same typo as patch_02a, in a different mission's tank group setup.

### OLD (line 932)

```c
      ActivateMove(true);
```

### NEW

```c
      ActivateMovement(true);
```

## Apply byte-safely

- Read with `[System.Text.Encoding]::GetEncoding(1252)`; replace exact OLD; write back
  same encoding. Backup: pristine copy already at
  `K:\TvTDeepseek\rollback\REDUX_2026-08-22\C2M3_MissionTasks.script`. Do NOT create a
  `.bak` inside the game folder — TvT reads every file regardless of extension. If an
  in-folder backup is ever needed, zip it.
- After: grep for `\xef\xbf\xbd` (zero hits) → delete `M:\T34vsTiger\Cache\Scripts.cache`.

## Verify

- No `ActivateMove` left in this file; no `[ScriptManager]` `ActivateMove` error in
  `execution.log` when C2M3 loads.
