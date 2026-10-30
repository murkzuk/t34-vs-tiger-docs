# Atmosphere — is it live-drivable? (WYSIWYG feasibility)

2026-08-30. Question: can the mission's atmosphere (sun/fog/wind) be changed WHILE
the game/editor is running and have the renderer update immediately — i.e. is a
WYSIWYG sun/fog editor possible?

## Finding: YES, it has native setters and is very likely live-drivable

### The atmosphere class hierarchy (scripts)

- `Scripts\Common\BaseAtmosphere.script` → `class CBaseAtmosphere extends CEditable`
- `Scripts\Common\Atmosphere.script` → `class CCommonAtmosphere`
- `Scripts\Editor\Atmosphere.script` → `class CMissionEditorAtmosphere extends CCommonAtmosphere`
- `Scripts\Editor\BaseAssetViewer.script` → `class CAssetViewerAtmosphere`

### The setters are NATIVE (declared fields in script, methods not defined in script)

`CBaseAtmosphere::SetProperties()` calls a long list of setters that are NOT
implemented in the `.script` — they are native engine methods:

`SetIsLightEnabled`, `SetIsShadowEnabled`, `SetSunDirection`, `SetSunColor`,
`SetBlindColor`, `SetSunSpecularColor`, `SetDistanceToSun`, `SetHorizontPos`,
`SetAmbientLight`, `SetFogMode`, `SetFogNear`, `SetFogFar`, `SetFogFarMax`,
`SetFogDensity`, `SetFogColorXPos/XNeg/YPos/YNeg`, `SetShadowColor`,
`SetStencilShadowColor`, `SetShadowFar`, `SetIsSunVisible`,
`SetEnableHorizontAdjustment`, `SetCenterHeight`, `SetAntiSunColor`,
`SetAntiSunSpecularColor`, `SetIsAntiSunEnabled`, `SetAntiSunDirectionAngle`,
`SetAntiSunDirectionHorAngle`, `SetTreeLightKoef`, `SetSunShines`,
`SetTreeShadowLodDistance`.

(The atmosphere object is native `#Atmosphere<T>`; the script class only carries
the editable field defaults and the `GetDefaultProperties`/`SetProperties` glue.)

### Evidence it updates live

1. The asset viewer drives it live: `BaseAssetViewer.script` line 1591 calls
   `GetMission().GetAtmosphere().SetAmbientLight(new Color(Factor, Factor, Factor, 1.0))`
   to change the preview ambient light **as the user adjusts a slider** — and the
   asset-viewer preview is visibly live. That proves the native `#Atmosphere`
   setters propagate to the renderer immediately, not just at load.
2. The mission exposes the atmosphere via `GetMission().GetAtmosphere()`, and
   `Mission.script` line 237 does `(new #EffectsArray()).SetWind(m_MissionAtmosphere)`
   — so the mission's live atmosphere object is reachable and used at runtime.

### Extra atmosphere fields beyond what we hand-edited

`CBaseAtmosphere` exposes more than our `Content.script` edits touched:
- `AntiSun` (anti-sun colour/intensity/angle — a second sun for glare),
- `BlindColor`, `SunSpecularIntensity`, `AntiSunSpecularIntensity`,
- `ShadowColor`, `StencilShadowColor`, `ShadowFar`, `TreeLightKoef`, `SunShines`,
  `TreeShadowLodDistance`, `HorizontPos` (an array `[300, 2000]`), `CenterHeight`.

So the atmosphere system is richer than our fog/sun edits used.

## What this means

A **WYSIWYG sun/fog editor is feasible**: call the native setters on the live
`GetAtmosphere()` object while the game runs, and the renderer updates the
sky/fog/lighting immediately.

### How to drive it (three options, cheapest first)

1. **Console / script command** — if the in-game `Console` can evaluate script,
   type `GetAtmosphere().SetSunDirection(...)` and watch it change live.
2. **Injected keybinds** — a small DLL (same injection we already use) that maps
   keys to `SetSunDirection` / `SetFogNear` / `SetAmbientLight` etc., giving
   drag-style live editing.
3. **External panel** — extend the existing state-bridge (injected hook ↔
   external tool) with a web/socket panel so you can drag sliders and push
   values into the live atmosphere.

### Definitive next test

A tiny read-only probe that, once in a mission, calls
`GetAtmosphere().SetSunDirection(...)` (or `SetAmbientLight`) with a visible
change, to confirm the mission (not just the asset-viewer preview) re-renders
live. That is the one measurement that turns "very likely" into "confirmed".

---

# CONFIRMED 2026-08-30 — live WYSIWYG sun editing works

**FINAL: ALL options confirmed live and stable (2026-08-30).** Sun position,
sun colour, ambient, fog distance (near/far/density) and fog colour all change
the running engine instantly with no crash. The fog colour is written to the
cached blend (+0x178) directly, NOT via `ComputeFogColor` — that recompute
normalises a direction arg and crashes on a degenerate (overhead) direction, so
it is avoided for the equal-colour case.

Built `K:\TvTDeepseek\atmos_wysiwyg\atmos_wysiwyg.dll` (key-driven) and the user
confirmed **"yes the sun changes position"** live, in the running editor, with no
reload. The WYSIWYG path is real.

## Tool
- `atmos_wysiwyg.cpp/.dll`, `build_atmos.bat`, `play_atmos.bat` (game),
  `play_atmos_editor.bat` (editor), allow-list.
- F6 = 25° morning, F7 = overhead, F8 = 45° afternoon.
- Injects into `Objects.dll`, hooks `SetSunDirection`'s helper, captures the live
  `CAtmosphere` object, and calls the full setter sequence on keypress.

## Reverse-engineered facts (so nothing is lost)
- Class: **`CAtmosphere`** (RTTI `.?AVCAtmosphere@@`), 10 vtables (multiple
  inheritance). The setters are **NOT vtable methods** — they are J5Script
  native-method wrappers registered by name.
- `SetSunDirection` = **three calls** (all `__thiscall`, `this` in ECX):
  1. helper `Objects.dll+0x5CFA0` — `void(this, const float* vec3)`; stores
     vec3 into `this+0x70`, normalizes, and **clamps elevation** (logs
     `Incorrect sun direction` and corrects if |z| < ~0.35, i.e. below ~20°).
  2. `Objects.dll+0x5B5A0` — `void(this)` — sky recompute.
  3. `Objects.dll+0x5BE50` — `void(this)` — lighting/shadow recompute.
  The J5Script thunk is at `0x5E8A0` (SEH prologue, typed-value arg); the five
  other setters are inlined in their thunks.
- **CAtmosphere member offsets:** SunDirection +0x70 (vec3), AmbientLight +0x90
  (RGBA), SunColor +0xA0 (RGBA), FogNear +0x104 (float), FogFar +0x108,
  FogFarMax +0x10C, FogDensity +0x110.
- Other setter thunks (for future keys): SetAmbientLight `0x5F190`,
  SetSunColor `0x5EA40`, SetFogNear `0x5F430`, SetFogFar `0x5F500`,
  SetFogDensity `0x5F5D0`.

## Gotchas learned (cost real debugging)
1. Calling only the helper stores the value but does NOT re-render — the two
   recompute calls are mandatory.
2. The engine enforces a ~20° minimum sun elevation and silently corrects
   lower suns, logging `Incorrect sun direction - '%g %g %g', make to - ...`.
3. The editor's `Command:` box is a script-expression evaluator, not a
   command-name dispatcher (and rejects complex expressions with a parse
   error) — the console was a dead end; injection is the right tool.

## Next (expand the tool)
- Nudge keys (arrow keys) for continuous sun azimuth/elevation.
- Fog near/far/density keys (thunks above + recompute after each).
- Ambient / sun-colour keys.
- A slider panel via the state-bridge (external UI → injected DLL).

---

# FOG map + live panel (2026-08-30)

Built the web slider panel (`atmos_panel.html` + `atmos_server.py` + the DLL
polling `atmos_state.txt`). Confirmed live: **sun position, sun colour, ambient**.
Fog needed one more reverse-engineering pass.

## Fog functions (Objects.dll)
| RVA | role |
|---|---|
| 0x5B4A0/B0/C0 | GetFogNear/Far/Density (read live each frame) |
| 0x5B490 | GetFogColorPtr |
| **0x5BBB0** | **CAtmosphere::ComputeFogColor** — the fog COLOUR recompute. `__thiscall`, 3 float args (view direction x,y,z), `ret 0xC`; reads FogColor XPos/XNeg/YPos/YNeg (+0x114/+0x124/+0x134/+0x144), writes the blended colour to +0x178. |
| 0x5F430/500/5D0/6A0 | SetFogNear/Far/Density/FarMax (write members, no recompute) |
| 0x5F770/860/950/A40 | SetFogColorXPos/XNeg/YPos/YNeg (write members) |

Key facts:
- **Fog near/far/density are read live** — writing the members is enough (no
  recompute). The renderer consumes them via the getters each frame.
- **Fog COLOUR is directional** (blends N/S/E/W by view direction) and is CACHED
  at +0x178 — so after writing the 4 colour members you must call `0x5BBB0` to
  refresh the cached colour.
- No Objects.dll function reads the fog scalars AND calls D3D9 SetRenderState;
  the D3D9 fog-state constants (34/35/36/37/38; FOGENABLE=28) appear only in a
  shader-effect loader, not in CAtmosphere. So the fog path is: members → getters
  → renderer (read live), with only the colour cached via 0x5BBB0.

## Panel architecture
`atmos_panel.html` (sliders) → `atmos_server.py` (writes `atmos_state.txt`,
version counter) → `atmos_wysiwyg.dll` (polls the file ~10x/s, applies on version
change). State file is simple `key=value` lines. No wind (wind is a separate
`CWind` class, not in CAtmosphere).

