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
