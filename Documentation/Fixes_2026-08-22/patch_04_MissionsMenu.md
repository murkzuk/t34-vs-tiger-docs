# PATCH 04 — Remove the ghost menu entry ("Kurtenki 2")

**File (live install):** `M:\T34vsTiger\Scripts\Menus\MissionsMenu.script`
**Plain words:** the Soviet mission list has a 7th entry pointing at a mission class that
was never built ("Kurtenki 2" — only its `.rsr` text file exists). The menu tries to read
its title, fails, and logs errors every launch. Deleting the entry fixes it; the menu
shows the 6 real missions.

**APPLIED 2026-08-22 — and then corrected.** The first attempt deleted only the ghost line
and left a **trailing comma** after `"CC1M6Mission",`, which the G5 parser rejects at the
closing bracket (`parse error ... line 32, char 13`). Correct application removes the comma
too. Current verified state of the array:

```c
  final static Array USSR_Missions = [
                "CC1M1Mission",
                "CC1M2Mission",
                "CC1M3Mission",
                "CC1M4Mission",
                "CC1M5Mission",
                "CC1M6Mission"
            ];
```

### Correct edit (if ever re-applied from scratch): OLD

```c
                "CC1M6Mission",
                "CKurtenki2Mission"
```

### NEW

```c
                "CC1M6Mission"
```

(delete the ghost line AND the comma after the previous entry — no trailing comma before `]`.)
