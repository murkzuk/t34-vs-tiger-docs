# LOS hook: "Behavior.dll never loaded" — intermittent failure

**For Claude.** DeepSeek diagnosed this on 2026-08-28. `hook.cpp` was NOT touched.

## Symptom

User: "los hook does not always take." In ZW (`M:\T34vsTiger_ZW2015\tvt_los.log`),
some launches end with:

```
tvt_los_hook attached ...
  (config banner reads fine)
Behavior.dll never loaded
```

When that line appears, **no patches are installed** — no vision hook, no gate, no
crew/commander. The hook attaches and reads its config every run; it just bails
before doing any work.

## Root cause

`K:\tvt_los\hook.cpp` (~lines 1521–1528). The Boot thread polls for `Behavior.dll`
for a **fixed 60 s** (600 × 100 ms) and then gives up:

```c
for (int i = 0; i < 600 && !beh; i++) {
  beh = GetModuleHandleA("Behavior.dll");
  if (!beh) Sleep(100);
}
if (!beh) { llog("Behavior.dll never loaded"); return 0; }
```

But `Behavior.dll` loads at **mission start** (3D sim), not at process launch.
Timeline from the failing run (the script cache had been cleared that session):

| Time | Event |
|---|---|
| 14:14:16 | hook attaches, starts 60 s countdown |
| 14:14:28 | `Scripts.cache` regenerates (cold recompile) |
| 14:15:16 | **hook gives up** — "Behavior.dll never loaded" |
| 14:22:24 | shader caches regenerate = user enters the mission (~8 min after launch) |

So the 60 s window only survives a warm cache + straight into a mission. A cold
start (cache cleared) or menu dawdling > 60 s → hook dies. Confirmed intermittent,
matching the report exactly.

## Proposed fixes

1. **Quick (2 lines):** drop the `600` cap — loop until `Behavior.dll` appears
   (keep `Sleep(100)`; it's a background thread and dies with the process).
2. **Proper:** `LdrRegisterDllNotification` for `"Behavior.dll"` — the event-driven
   approach DeepSeek's fog fix already uses for `d3d9.dll`
   (`K:\TvTDeepseek\fogfix\fogfix.cpp`). Catches the DLL the instant it loads; no
   polling, no race.

## Context — what DeepSeek did this session (2026-08-28)

- Applied golden-dawn TOD + briefing dateline to C2M1 ZW (backups under
  `K:\TvTDeepseek\rollback\C2M1_ZW_2026-08-28_pre_*`).
- Bumped ZW version to `v0.260828b`.
- Cleared `Scripts.cache` / `Effects.cache` (normal edit workflow). That made the
  14:15 launch a slow cold start and exposed the race — the race itself pre-exists
  and is not caused by the cache clear.
