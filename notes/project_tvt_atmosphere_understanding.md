# TvT Atmosphere — Working Reference

Clean reference of what we know and what's still open about lighting/atmosphere/TOD/fog
in the G5 engine (T-34 vs. Tiger REDUX). Distilled from the C2M2 test-bed work, 2026-08-23.
The full experiment trail is in `project_tvt_atmosphere_lighting_plan.md`.

## The three-layer model (how a value gets decided)

Every atmosphere parameter resolves in this order:

1. **Content.script** — the `"Atmosphere"` object block (`["Key", value]` pairs). Wins for any key it lists. **This is the runtime data.**
2. **Atmosphere.script** — the mission's class (`CC2M2Atmosphere extends CCommonAtmosphere extends CBaseAtmosphere`). Its field values win for any key Content.script *doesn't* list.
3. **BaseAtmosphere defaults** — `Scripts\Common\BaseAtmosphere.script` (`GetDefaultProperties()`, ~33 keys). Wins for anything neither lists.

> Practical rule: to change a value, edit **Content.script** first (it wins). Only touch Atmosphere.script for keys not present in Content.script.

## The dials (parameters that matter)

| Area | Keys | Notes |
|---|---|---|
| Sun | `SunDirection`, `SunColor`, `SunIntensity`, `SunSpecularIntensity`, `DistanceToSun` | `SunDirection` = unit vector (direction the light travels, z negative = sun up) |
| Shade | `AmbientLight` | flat shade fill |
| Anti-sun (sky fill) | `AntiSunColor`, `AntiSunIntensity`, `AntiSunSpecularIntensity`, `AntiSunEnabled`, `AntiSunAngle`, `AntiSunHorAngle` | second directional light, aimed by two angles |
| Fog | `FogMode`, `FogNear`, `FogFar`, `FogFarMax`, `FogDensity`, `FogColorXPos/XNeg/YPos/YNeg` (S/N/E/W) | `FogFar` is the working lever; see gaps |
| Shadows | `ShadowColor`, `StencilShadowColor`, `ShadowFar` | |
| Weather-ish | `WindVector` | |
| Flags | `IsSunVisible`, `IsLightEnabled`, `IsIllumination` | night behaviour unknown |

## The locked dawn recipe (C2M2, user-approved "better than stock")

- Sun: warm orange `SunColor (1.0, 0.749, 0.294)`, `SunIntensity 0.35`, low unit vector `(0.8156, -0.5520, -0.1736)`
- Shade: **cool** `AmbientLight (0.157, 0.204, 0.243)`
- Anti-sun: **muted** `AntiSunColor (0.498, 0.522, 0.608)`, intensity 0.25
- Fog: `FogFar 450`, warm→grey-blue colours, `FogMode "Exp"`
- Shadows: warm `(0.345, 0.420, 0.467)`

**The principle in one line: warm sun + warm fog + cool ambient + muted anti-sun.**

## Neutral-white effects (track marks, dust, exhaust)

These are tinted by **both** `AmbientLight` AND `AntiSunColor`. To keep them clean:

- `AmbientLight` → cool (not warm)
- `AntiSunColor` → muted (not bright blue — bright blue over-lights them)

Track-mark *brightness/colour* itself is `SetBaseColor(...)` in `Scripts\Common\EffectsBase.script:587` (ground), `Effects.script:1483` (road), `Effects.script:1531` (forest). **Global, not per-mission.**

## Knowns (solid, tested)

- ✅ The 3-layer model (above).
- ✅ `SunDirection` is read from Content.script; the engine normalises and logs a "make to" warning (cosmetic).
- ✅ A **non-unit** sun is a **real visual bug** (sun glare + invisible sun disc) — not cosmetic, contrary to the changelog. User-verified: fixing it made the sun visible for the first time.
- ✅ Lighting principle: warm highlights + cool shade + muted anti-sun.
- ✅ `FogFar` drives the terrain haze (proven by the mist experiment); `FogDensity` changes nothing (Exp likely broken).
- ✅ Fog is baked into every visible-geometry shader (terrain, static `SceneMesh`, skinned `SkinMesh` units, planar shadows).
- ✅ WoV (`G:\WoV`) is the finished-engine reference: unit sun vector `(0.172, 0.907, -0.384)`, clean `/255` colours, one consistent daylight preset.

## Gaps (open, all investigable)

1. **AntiSunAngle / AntiSunHorAngle convention** — elevation vs zenith, what 0° azimuth means. Native (binary-side); needs an in-game test or RE.
2. **The engine's fixed "make-to" sun elevation** — the warning always asks for `(0.7758, -0.525, -0.35)` regardless of input. Source unknown (not in scripts/binary literals).
3. **Fog-on-objects** — tanks stay sharp while terrain hazes. Shader capability exists; it's a renderer-pass issue. Likely a **D3D9 hook** (like the LOS hook).
4. **`FogMode "Exp"` vs `"Linear"`** — is Exp actually implemented? (`FogDensity` did nothing.)
5. **Night / `IsIllumination` / `IsSunVisible`** — never tested; unknown if night is supported.

## Process rules (never change)

- `.script` files are **CP1251** — never UTF-8 round-trip; edit byte-level; check for `\xef\xbf\xbd` before/after.
- **Delete `Cache\Scripts.cache`** after any script edit.
- Backups live **outside** game folders (rollback kit); never leave stray files in a game folder (TvT reads every file regardless of extension).
- One change at a time; user is the last gate.

## ZW snow mission - winter overcast (Option A) + stub (2026-08-23)

CWinterMission1 (ZW, M:\T34vsTiger_ZW2015\Missions\CustomMissions\CWinterMission1) is now
the SECOND reference recipe (winter overcast, opposite of C2M2 dawn). User-approved
"looks cooler (temperature)". Changes applied:
- Content.script: sun normalised (-0.69,0.87,-0.45 -> -0.576,0.726,-0.376) - same glare fix.
- Atmosphere.script: reconciled 17 fields to match Content's bright overcast values
  (bright ambient 0.59, pale blue-white fog, soft shadows).
- Atmosphere.script: added interface-silencer stub
  `void SetIsCameraAdjustEnabled(boolean value) { }` - fixes base-class call failing
  every load (same precedent as CC2M2Atmosphere). Harmless no-op; removes a log-spam line.
Backups: K:\TvTDeepseek\rollback\zw_cwinterm1_scripts_2026-08-23.zip (original) +
Atmosphere.script.pre_stub_2026-08-23.
## Compass + sun-direction convention (2026-08-23)

The map orientation is FIXED and GLOBAL - written in BaseAtmosphere.script (identical in
REDUX/ZW/WoV) via the directional fog colour comments:
  FogColorXPos = // S  ->  +X = SOUTH
  FogColorXNeg = // N  ->  -X = NORTH
  FogColorYPos = // E  ->  +Y = EAST
  FogColorYNeg = // W  ->  -Y = WEST
(+Z = up). Every mission uses the same compass; "east" is ALWAYS +Y - not per-mission.

SunDirection = LIGHT direction (rays from sun down to ground - z always negative). The sun
sits OPPOSITE the vector's horizontal part. So a morning/east sun = light heading WEST
(strong -Y), z small negative (low), unit-length.

DAWN FORMULA (any mission): SunDirection horizontal points WEST (-Y dominant), z small and
negative (low sun), unit length. Example clean east-dawn: (-0.2, -0.95, -0.24) ~14 deg up.

CORRECTION: earlier "each mission faces a different direction" was WRONG - the compass is
global. C2M2's dawn sun (light SW -> sun NE) is slightly off true-east; a true east sunrise
needs the westward vector.
## Stub sweep complete (2026-08-23)

SetIsCameraAdjustEnabled is a ZW-ONLY issue: ZW BaseAtmosphere.script:140 CALLS it, but
REDUX BaseAtmosphere does NOT - so REDUX needs no stub. Fixed at the COMMON level:
added `void SetIsCameraAdjustEnabled(boolean value) { }` to ZW Scripts\Common\Atmosphere.script
(CCommonAtmosphere), so ALL ZW missions inherit it. The two mission-level stubs already
present (CC2M2Atmosphere, CWinterM1Atmosphere) are now redundant-but-harmless overrides.
Backup: K:\TvTDeepseek\rollback\zw_Common_Atmosphere.script.bak_2026-08-23.
## Winter rollout complete (2026-08-23)

All 4 ZW winter missions now share the winter-overcast treatment (each kept its OWN
palette - not forced to one value; sun normalised to fix glare; Atmosphere.script
reconciled to match Content.script's runtime values):
- CWinterMission1 - done earlier (bright overcast, stub added)
- CWinterMission2 - sun normalised + 18 fields reconciled
- CWinterMission3 - sun normalised + 18 fields reconciled
- CLeningrad43_M1 - sun normalised + 19 fields reconciled (uniform grey fog, SunColor
  alpha 0 = invisible sun - true overcast, DefaultFogMode Exp->Exp2)
Backups: rollback\zw_cwinterm2_scripts, zw_cwinterm3_scripts, zw_cleningrad43m1_scripts
(each 2026-08-23.zip). Stub sweep (SetIsCameraAdjustEnabled) already covered all via
CCommonAtmosphere.
## Leningrad verified: true overcast (2026-08-23, user-approved, leave as-is)

User played CLeningrad43_M1 ("Operation Spark") - verdict: bright ground + grey sky is
CORRECT, not a bug. It is the one mission the original devs got fully right as a TRUE
overcast: uniform grey fog (all 4 FogColor = 0.447,0.459,0.565), SunColor alpha 0
(invisible sun disc), FogMode "Exp2". Bright ground = snow reflecting diffuse light; grey
sky = cloud layer; no sun = overcast. My only edit was sun-normalisation (no visible
effect here, since the sun is already invisible). LEAVE IT AS-IS - it is the reference
for "true overcast". Remaining Leningrad log lines are cosmetic (missing str_NavPointRedArmy
locale string) - pre-existing, not atmosphere.
## FOG-TEST BED (2026-08-23)

Use "Zitadelle Attack" (folder: ZW CustomMissions\KurskMission, class KurskM1Mission/
KurskM1Atmosphere, rsr "ZITADELLEEE: M1, Attack!") as the fog-on-objects test mission.
Why ideal: 36,000 m map (MatrixWidth 36000), FogFar 4000, DISTANT FRIENDLY tanks visible
at spawn (safe to observe). Test: at spawn, look at the distant friendly tanks - if they
are SHARP/DARK while the ground hazes = fog-on-objects bug clearly demonstrated (the
screenshot/observation needed to scope the D3D9 hook fix). If they haze like the ground
= fog already reaches units.