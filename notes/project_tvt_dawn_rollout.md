# Dawn rollout (Phase 2) — progress (2026-08-24)

## Reference dawn recipe (confirmed good, C2M2 & C1M2)

```
SunDirection   = (0.815587, -0.551964, -0.173648)   // low morning sun (NE)
SunColor       = (1.000000, 0.749020, 0.294118, 1.0) // orange dawn
AmbientLight   = (0.156863, 0.203922, 0.243137, 1.0) // cool blue (already correct)
AntiSunColor   = (muted blue, leave as-is)
FogMode        = "Exp"
FogDensity     = 0.0013
FogNear        = 10.0
FogFar         = 450.0
FogFarMax      = 3000.0
```

## Applied

- **C2M2** (German, 07:00 morning low fog) — applied earlier, user confirmed.
- **C1M2** (Soviet, 07:00 dawn, "after the Krinovichi breakthrough") — applied
  2026-08-24, user confirmed "feels very nice / looks good".

### CORRECTION (important)

I earlier flagged C1M2's `FogFar = 3.0` as a "near-zero-visibility bug". **Wrong.**
In `Exp` mode the engine drives fog off `FogDensity`, not `FogFar`, so the old fog
was *working* — a heavy morning mist at `FogDensity 0.003`. The change to
`FogDensity 0.0013` + `FogFar 450` is a **polish** (gentler/clearer), not a bug-fix.
The user: "fog was ok before but better now."

## Historical framing

Soviet campaign is "Summer 1944" (post-Kursk, ~Operation Bagration) per C1M1's
briefing. C1M2 has **no specific day** in the briefing — only "no later than 07:00h"
(hence dawn). Only C2M5 (German) carries a hard date (03 March 1944). Villages and
day-by-day timeline are fictionalised.

## Remaining

- 5 "stock noon" missions (C1M1, C1M4, C2M1, C2M3, C2M6) — refine to proper
  late-morning/noon recipes.
- C1M3 on `Exp2` + `FogFar 1500` (odd for a sunset) — review.
- Other dawn-capable missions: none at 07:00 besides C1M2/C2M2 (both done).
