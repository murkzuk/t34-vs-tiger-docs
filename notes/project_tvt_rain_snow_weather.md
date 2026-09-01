# Rain & Snow Weather (WoV mod) — REDUX vs ZW

Status: INVESTIGATED (2026-08-30). NOT ported — awaiting user go-ahead (user is last gate).

## The user's claim — CONFIRMED
"ZW used WoV rain, REDUX never did." → TRUE, and it is bigger than rain: it is a
WoV-origin weather mod pack (**Rain Mod 1.1** + **Snow Mod 1.1**, author
republicthunderbolt9@gmail.com) that ZeeWolf bundled into ZW. REDUX has none of it.

## What the feature actually is
Two J5Script classes, both extend `CNatureElements` (a shared base in `Nature.script`):

1. **CRainManager** (`Scripts\Common\BaseRain.script`, 667 lines)
   - Rain particles (billboard streaks), 3 intensities (Light/Normal/Hard) + a
     binocular variant (Rain2) for looking through optics.
   - Lightning: 4 flash billboards + `CLightEclair` (a point light that briefly
     re-tints the atmosphere fog color) + 3 thunder sounds.
   - Looping rain sound (`Sounds\rain.wav`).
   - Wind angle/orientation sway for the rain streaks.
2. **CSnowManager** (`Scripts\Common\BaseSnow.script`, 335 lines)
   - Snow particles (slow drift), 3 intensities + binocular variant. `isSnow = true`.
   - (Calls `Mission().GetObjects(["WEM"],[])` — only logged, does not gate the effect.)

Shared base `CNatureElements` (`Scripts\Common\Nature.script`):
- `SetEffect()` (spawns the particle ring), `SetStringEffect()` (switch intensity/
  binocular mode), `WindAngle()/WindOrientation()` (streak sway), `SetWindSequence()`.

## How it is spawned in a ZW mission
Per-mission `Missions\...\Content.script` has a plain "GameObject" block. Example
(`ZW\Missions\CustomMissions\Panther_M1\Content.script` lines 86–107):

```
[
  "RainManager",            // object name
  "GameObject",             // object type
  "CRainManager",           // class from BaseRain.script
  new Matrix(...),          // position/orientation (centered near the action)
  [
    ["EclairMode", "Light"],      // lightning: Light | Normal | Hard | None
    ["RainMode",    "Normal"],    // (legacy; real intensity key is EffectMode)
    ["WindAngle",             30.0],
    ["WindOrientation",       30.0],
    ["WindEtape",             20.0],
    ["WindOrientationTolerance", 60.0],
    ["WindOrientationEtape",  20.0],
    ["WindDefaultAngle",       0.1],
    ["EffectMode", "Normal"]        // rain intensity: Light | Normal | Hard
  ]
]
```
Snow is the same shape but class `CSnowManager` and object name `SnowManager`.

## REDUX vs ZW — exact gap
REDUX (`M:\T34vsTiger`) is MISSING everything:

| Item | ZW | REDUX |
|---|---|---|
| `Scripts\Common\Nature.script` | present | MISSING |
| `Scripts\Common\BaseRain.script` | present | MISSING |
| `Scripts\Common\BaseSnow.script` | present | MISSING |
| `EffectsArray.script` Rain/Snow skins | present | MISSING (no Rain/Snow/Nature refs) |
| `PlayerUnit.script` GetRainManager() | present | MISSING |
| `Textures\Rainbase.tex` | present (32 KB) | MISSING |
| `Textures\eclair.tex` | present (390 KB) | MISSING |
| `Textures\SnowBase.tex` | present (0.7 KB) | MISSING |
| `Sounds\rain.wav` | present (63 KB) | MISSING |
| `Sounds\eclair1..3.wav` | present | MISSING |

REDUX's only "rain" hook is `BaseTerrain.script::SetRainyWeather()` — it ONLY sets
water-ripple settings (RipplesTextureScale/WavePeriod/Brightness). It does NOT spawn
any precipitation. Same stub exists in ZW's BaseTerrain/BaseWinterTerrain/BaseMegaTerrain.

## Port recipe (to enable rain/snow in REDUX) — NOT DONE, needs go-ahead
1. Copy 3 scripts ZW → REDUX `Scripts\Common\`: `Nature.script`, `BaseRain.script`,
   `BaseSnow.script`.
2. Add the Rain/Snow skin statics to REDUX `Scripts\Common\EffectsArray.script`
   (`static Component RainSkin/SnowSkin = null;` + `new #MaterialManager<...>()` lines,
   mirroring ZW's EffectsArray lines ~50/91/99).
3. Copy 7 assets ZW → REDUX: 3 textures (`Rainbase`, `eclair`, `SnowBase`) +
   4 sounds (`rain.wav`, `eclair1/2/3.wav`).
4. (Optional, ZW parity) add `GetRainManager()` + the `SetStringEffect` binocular
   switches to REDUX `PlayerUnit.script`.
5. Per mission: paste a `RainManager` (or `SnowManager`) GameObject block into the
   mission `Content.script` and set EclairMode/EffectMode per the weather wanted.
   + BACKUP the mission + scripts first (standing rule: rollback before any edit).

## Risks / caveats
- Same G5 engine on both sides, so the script API (CBaseEffect, CBaseLightEmitter,
  CEngineSound, DynamicEffect, MaterialManager, EffectsArray) is shared. The REDUX
  EffectsArray already registers hundreds of the same effect types, so the framework
  is present. Confidence: high, but NOT user-verified yet.
- Rain mod's `WriteLog` writes `rain.log` via loadStringFromFile/saveStringToFile —
  harmless.
- Snow's `WEM` object lookup is ZW-specific and only logged; snow still spawns.

## Tie-in to the current atmosphere/weather work
- Winter War (Jan 1940) preset → SNOW is the natural companion.
- Bagration (late Jun 1944) had rain/overcast at the start → RAIN is the natural
  companion for the overcast/grey preset.
- Later option: add a rain/snow ON/OFF + intensity toggle to the WYSIWYG panel
  (separate from CAtmosphere — it is a mission GameObject, not an atmosphere field).
