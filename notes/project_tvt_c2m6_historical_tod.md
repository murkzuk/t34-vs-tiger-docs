# C2M6 "Tiger Break Out!" — Historical TOD

Status: **applied to ZW build** on 2026-08-29 (dawn breakout). REDUX untouched.
Backup: `K:\TvTDeepseek\rollback\C2M6_ZW_2026-08-29_pre_dawn\`

## Historical determination

- **Mission:** German Tigers escort an unarmed convoy **north** through Soviet
  roadblocks, breaking out before the encirclement closes — "the enemy is slowly
  closing off the only route up north!" (time pressure → a first-light breakout).
- Same Lioznensky/Vitebsk theatre, late June 1944 (Bagration), ~55°N.
- **Briefing gives no time** — chose **dawn** (user-approved): the classic
  first-light breakout, matching C2M1's rearguard dawn in the same theatre.

## What was wrong before

C2M6 was a **half-finished** state: a placeholder sun at 16° / **34° azimuth** (the
old generic dawn recipe, not the real late-June sun) plus mixed lighting — dawn-blue
class ambient overridden by a bright daytime block. Redone properly here.

## Applied settings (real dawn, same as C2M1)

```
SunDirection  = (0.431711, -0.885139, -0.173648)   // sun 10° up, ENE (64°)
SunColor      = (1.000000, 0.750000, 0.300000)      // warm amber dawn
AmbientLight  = (0.156863, 0.203922, 0.243137)      // cool pre-dawn blue
SunIntensity  = 1.0
Fog           = Exp, density 0.0013 (morning mist)
```

Edited both layers (class SunDirection + SunColor; block Ambient/SunColor/Fog).

## Before → after (key fields)

| Field | Before | Now |
|---|---|---|
| SunDirection | (0.990, −0.670, −0.350) — 16°, 34° (generic) | (0.432, −0.885, −0.174) — 10°, 64° ENE (real) |
| SunColor | warm white | warm amber |
| AmbientLight | bright (0.416…) | dawn blue (0.157…) |
| Fog | Linear 1200–4000 | Exp, density 0.0013 |

## Rollback

Restore `Content.script` + `Atmosphere.script` from
`K:\TvTDeepseek\rollback\C2M6_ZW_2026-08-29_pre_dawn\` back into
`M:\T34vsTiger_ZW2015\Missions\Campaign_2\Mission_6\` to undo.
