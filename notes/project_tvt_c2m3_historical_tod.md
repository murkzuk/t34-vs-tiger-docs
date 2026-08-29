# C2M3 "Hold Simashkovo" — Historical TOD

Status: **applied to ZW build** on 2026-08-29 (sunset). REDUX untouched.
Backup: `K:\TvTDeepseek\rollback\C2M3_ZW_2026-08-29_pre_sunset\`

## Historical determination

- **Mission:** German Tigers + Panzer IVs defending **Simashkovo** — the German
  side of the same battle the Soviet C1M4 "Simashkovo Recon" set up (C1M4 recons at
  10:00 clear). Same Lioznensky district, Vitebsk, ~55°N, late June 1944 (Bagration).
- **Briefing gives no time.** Chose a **sunset** (user-approved): a rearguard "hold
  the village" against the Soviet attack arriving in the fading light — the attack
  follows the morning recon, so end-of-day is the plausible frame.

## Computed sun (late June, 55°N)

| Time | Elevation | Azimuth |
|---|---|---|
| 19:30 | 15° | 290° |
| **20:00** | **11°** | **295° WNW** |
| 20:30 | 7° | 301° |

## Applied settings

```
SunDirection  = (0.422900, 0.886600, -0.187380)   // sun 11° up, WNW (295°)
SunColor      = (1.000000, 0.750000, 0.300000)    // warm amber sunset
AmbientLight  = (0.160000, 0.200000, 0.240000)    // dusk blue
SunIntensity  = 1.0
Fog           = Exp, density 0.0005 (light, clear evening)
```

Edited both layers (Content block + Atmosphere class), same as C1M1/C1M4/C2M1.

## Before → after (key fields)

| Field | Stock | Now |
|---|---|---|
| SunDirection | (−0.006, −0.156, −0.305) — 63° high grey | (0.423, 0.887, −0.187) — 11° WNW sunset |
| SunColor | grey (0.753) | warm amber (1.0, 0.75, 0.30) |
| AmbientLight | grey (0.455) | dusk blue (0.16, 0.20, 0.24) |
| Fog | Linear 100–1200 | Exp, density 0.0005 |

## Rollback

Restore `Content.script` + `Atmosphere.script` from
`K:\TvTDeepseek\rollback\C2M3_ZW_2026-08-29_pre_sunset\` back into
`M:\T34vsTiger_ZW2015\Missions\Campaign_2\Mission_3\` to undo.
