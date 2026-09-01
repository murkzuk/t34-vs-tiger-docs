# C2M1 "Tigers Shake Kurtenki" — Historical TOD

Status: **applied to ZW build only** on 2026-08-28 (golden dawn). REDUX C2M1 is
NOT the same mission — "Securing Kurtenki REDUX by Murkz" (July 1943, a different
scenario the user has tinkered with). Do NOT mirror the 1944 dawn to it; leave it
alone per user.
Backup: `K:\TvTDeepseek\rollback\C2M1_ZW_2026-08-28_pre_goldendawn\`

## Historical determination

- **Place:** Kurtenki (Куртёнки) is a real village in **Lioznensky district, Vitebsk
  Oblast, Belarus** (~55.02° N, 30.80° E), east of Vitebsk on the old Smolensk road.
- **Event:** The mission is a German Tiger rearguard during **Operation Bagration**,
  specifically the **Vitebsk–Orsha offensive (22–28 June 1944)**. Vitebsk fell 26 June;
  the region west of it (Liozno → Lepel) was fought over 25–28 June. Heavy Tiger
  battalions did exactly this kind of delaying action with 4. Armee in June '44.
- **Date/time anchor:** dawn rearguard ambush, **late June 1944** (sun is effectively
  identical across the 24–28 June window — near solstice). Sunrise ≈ 04:45 Moscow time
  (UTC+3), azimuth ~47° (NE).

The mission is a dramatisation — the "ambush" itself is the game's invention — but the
place and the campaign window are real.

## Computed sun (solar declination ≈ 23.34°, EoT ≈ −2.8 min)

| Moscow time | Sun elevation | Azimuth (from N) |
|---|---|---|
| 05:20 | 5° | 56° |
| **05:55** | **10°** | **64°** |
| 06:25 | 15° | 69° |

Late-June sun at 55°N rises well north of east and climbs fast.

## Applied settings (golden dawn, sun 10°)

Game convention: SunDirection = light direction; +X South, +Y East, +Z up.
Light = (cosE·cosA, −cosE·sinA, −sinE), A = azimuth from North, E = elevation.

```
SunDirection  = (0.431711, -0.885139, -0.173648)   // sun ENE (64°), 10° up
SunColor      = (1.000000, 0.749020, 0.294118)      // warm dawn amber
AmbientLight  = (0.156863, 0.203922, 0.243137)      // cool pre-dawn blue
FogMode       = "Exp"
FogDensity    = 0.0013                              // morning mist
FogNear       = 10
FogFar        = 450
SunIntensity  = 1.0
```

Edited **both** layers for consistency:
- `Content.script` Atmosphere block (the effective override layer) — 8 fields.
- `Atmosphere.script` class — SunDirection, SunColor, AmbientLight, FogDensity/Near/Far.

## Before → after (key fields)

| Field | Stock | Now |
|---|---|---|
| SunDirection | (−0.006, −0.156, −0.305) — 63° high, grey | (0.432, −0.885, −0.174) — ENE dawn |
| SunColor | grey (0.753) | warm amber |
| AmbientLight | bright grey (0.455) | cool dawn blue |
| Fog | Linear 1000–1200 | Exp, density 0.0013 |

## Sources

- Kurtenki — Mapcarta: https://mapcarta.com/28906230
- Куртёнки — globustut.by: https://www.globustut.by/by/Куртёнки
- Kurtenki, Belarus — fallingrain: http://fallingrain.com/world/BO/07/Kurtenki.html
- Куртенки, Лиозненский район (postal index): http://bel-index.by/vitebskaya/lioznenskiy/kurtenki/centralynaya-2267
- T-34 monument, Liozno: https://planetabelarus.by/sights/pamyatnik-tank-t-34/
- Operation Bagration (5th Stalin blow): https://topwar.ru/159695-pjatyj-stalinskij-udar-kak-krasnaja-armija-osvobodila-belorussiju.html
- s.Pz.Abt. 505 with 4. Armee, June '44 (forum): https://www.forum-der-wehrmacht.de/index.php?thread/10121-schw-pz-abt-505-im-bereich-der-4-armee-juni-44/
- Lepel liberated 28 June 1944 (regional timeline): https://lepel.vitebsk-region.gov.by/news/novosti_rajona-news-ru/28-ijunja-2019-goda-75-let-osvobozhdenija-lepelja-ot-nemetsko-fashistskix-zaxvatchikov-17822/

## Rollback

Restore the three files in
`K:\TvTDeepseek\rollback\C2M1_ZW_2026-08-28_pre_goldendawn\` back into
`M:\T34vsTiger_ZW2015\Missions\Campaign_2\Mission_1\` to undo.
