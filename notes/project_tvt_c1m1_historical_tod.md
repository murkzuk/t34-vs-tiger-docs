# C1M1 "Seize the Escape Road" — Historical TOD

Status: **applied to ZW build** on 2026-08-28 (06:15 clear summer morning). REDUX untouched.
Backup: `K:\TvTDeepseek\rollback\C1M1_ZW_2026-08-28_pre_morning\`

## Historical determination

- **Mission:** Soviet side — T-34 of the "2nd Tank Brigade", a breakthrough tank
  army. Summer 1944, German Panzers in full retreat → **Operation Bagration**.
- **The briefing specifies the time and weather directly:** *"You will move out at
  6:15h … the weather is clear and the terrain is open."* So unlike C2M1 (where a
  dawn ambush had to be inferred), C1M1 is anchored to a concrete time.
- No named village in the briefing — a representative Soviet spearhead, not a
  specific town. Central Belarus (~54° N, ~28° E), late June 1944.

## Computed sun (declination ≈ 23.34°, EoT ≈ −2.8 min)

| Moscow time | Sun elevation | Azimuth |
|---|---|---|
| sunrise ≈ 04:45 | 0° | ~47° NE |
| **06:15** | **11°** | **65° ENE** |
| 07:00 | 17° | 74° |

At move-out the sun is ~11° up in the ENE — a bright, clear summer morning.

## Applied settings

Game convention: SunDirection = light direction; +X South, +Y East, +Z up.
Light = (cosE·cosA, −cosE·sinA, −sinE), A = azimuth from North, E = elevation.

```
SunDirection  = (0.411893, -0.891095, -0.190511)   // sun 11° up, ENE (65°)
SunColor      = (1.000000, 0.880000, 0.720000)      // golden morning sun
AmbientLight  = (0.300000, 0.340000, 0.420000)      // clear blue morning
SunIntensity  = 1.1                                  // kept (already bright)
Fog           = kept light (clear day): Exp, density ~0.0005
```

Edit points:
- `Atmosphere.script` class — `SunDirection` (the block does NOT override it here).
- `Content.script` Atmosphere block — `SunColor`, `AmbientLight`.

## Before → after (key fields)

| Field | Stock | Now |
|---|---|---|
| SunDirection | (−0.006, −0.156, −0.305) — 63° high grey | (0.412, −0.891, −0.191) — 11° ENE morning |
| SunColor | warm white (0.988, 0.937, 0.780) | golden (1.0, 0.88, 0.72) |
| AmbientLight | grey-blue (0.412, 0.427, 0.455) | clear blue (0.30, 0.34, 0.42) |

## Rollback

Restore `Content.script` + `Atmosphere.script` from
`K:\TvTDeepseek\rollback\C1M1_ZW_2026-08-28_pre_morning\` back into
`M:\T34vsTiger_ZW2015\Missions\Campaign_1\Mission_1\` to undo.
