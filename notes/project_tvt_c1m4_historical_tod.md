# C1M4 "Simashkovo Recon" — Historical TOD

Status: **applied to ZW build** on 2026-08-29 (10:00 clear late morning). REDUX untouched.
Backup: `K:\TvTDeepseek\rollback\C1M4_ZW_2026-08-29_pre_morning\`

## Historical determination

- **Mission:** Soviet tank brigade continues after the Kurtenki fight (C2M1) toward
  **Simashkovo**, with SU-85s, intercepting a German flanking force from **Bereznyaki**
  — all villages in the Lioznensky district, Vitebsk Oblast (~55°N), same theatre as
  C2M1. "Tigers from Schwere Panzerabteilung 505" = the same fictionalised Bagration
  frame (late June 1944).
- **Briefing gives time + weather directly:** *"You will leave for Simashkovo at
  10:00 under clear skies."* So it's a bright late morning, not a dawn.

## Computed sun (10:00 Moscow time, late June 1944, 55°N)

| Time | Elevation | Azimuth |
|---|---|---|
| 09:30 | 40° | 108° |
| **10:00** | **44°** | **115° ESE** |
| 10:30 | 48° | 124° |

## Applied settings

```
SunDirection  = (-0.305777, -0.648028, -0.697539)   // sun 44° up, ESE (115°)
SunColor      = (1.000000, 0.950000, 0.880000)      // near-white, faintly warm (clear)
AmbientLight  = (0.420000, 0.450000, 0.500000)      // bright clear morning
SunIntensity  = 1.0
Fog           = kept light (Exp, density 0.0005 — clear)
```

Edited both layers (Content block + Atmosphere class), same as C1M1/C2M1.

## Before → after (key fields)

| Field | Stock | Now |
|---|---|---|
| SunDirection | (−0.006, −0.156, −0.305) — 63° high grey | (−0.306, −0.648, −0.698) — 44° ESE morning |
| SunColor | white, alpha 0 (invisible sun) | warm white, alpha 1 |
| AmbientLight | dark grey (0.2) | bright blue (0.42–0.50) |

## Rollback

Restore `Content.script` + `Atmosphere.script` from
`K:\TvTDeepseek\rollback\C1M4_ZW_2026-08-29_pre_morning\` back into
`M:\T34vsTiger_ZW2015\Missions\Campaign_1\Mission_4\` to undo.
