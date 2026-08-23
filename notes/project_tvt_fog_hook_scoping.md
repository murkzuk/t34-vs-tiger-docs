# Fog-on-objects — hook scoping plan (2026-08-23)

STATUS: **scoping only** (read-only; no game changes; no hook code written yet).

## The question

Does fog actually reach **unit** draw calls, or only terrain? Naked eye on Zitadelle
spawn said "looks the same" — can't tell by eye. This needs measurement, not eyesight.

## What we know (confirmed)

- Fog is **per-shader**: compiled `.fxo` files declare `FogFar` / `FogDensity` params.
- **All** visible-geometry shaders have them: terrain (ChunkedTerrainMesh / Grass /
  ForestStripe), `SceneMesh_*` (static objects), `SkinMesh1/4_*` (skinned units = tanks),
  `PlanarShadow*` (blob shadows). Only `ShadowMesh_ST` / `SkinShadowMesh_ST` (stencil
  volumes) lack fog — and they don't need it.
- **`FogFar` drives the terrain haze** (proven by the mist experiment). `FogDensity` 4×
  did nothing (Exp likely broken/not wired).
- Docs (Rendering_And_Framerate.md §6) flag it: fog "not applied to distant objects" — OPEN.
- The engine's own fog setter is native `SetFogFar`/`SetFogDensity` etc. (called from
  BaseAtmosphere.script `SetProperties`).

## The hypothesis

The engine sets the fog uniforms for the **terrain pass but not the unit/object pass**.
The unit shaders *can* fog (params exist) but never receive the values.

## Hook design (measure, don't guess)

- **Reuse the LOS hook pattern** (`K:\tvt_los\hook.cpp`): inject a DLL, trampoline
  `__fastcall` (dummy 2nd arg = `__thiscall`), resolve addresses at runtime (the engine
  DLLs relocate 237–394 MB — never hardcode absolute addresses).
- **Target the D3D9 layer.** The game's `d3d9.dll` IS the wrapper (dgVoodoo or DXVK); the
  engine calls it, so hooking its exported device methods observes the engine's calls.
- **Log:**
  1. `SetVertexShaderConstantF` / `SetPixelShaderConstantF` — catch the `FogFar` /
     `FogDensity` register writes (what value, and when).
  2. `DrawIndexedPrimitive` / `DrawPrimitive` — count draws, and correlate each with the
     current fog constants + fog render state (`D3DRS_FOGENABLE` / `D3DRS_FOGCOLOR`).
  3. **Which mesh/shader** each draw belongs to (terrain vs unit) — the hard part.
     Options: log the current texture/shader handle, or hook the engine's native
     `SetFog*` and count calls vs draws.

## Risks / unknowns

- `d3d9.dll` is the wrapper, not raw D3D9; the engine may apply fog via the D3DX effect
  framework (`ID3DXEffect::SetFloat`) which sits above the device. Hooking device-level
  `Set*ConstantF` should still catch it, but needs confirming.
- Distinguishing terrain vs unit draw calls is the main challenge.
- 32-bit process → the hook DLL must be **x86** (same as the LOS hook; `build.bat` uses
  `vcvars32`).

## Concrete next steps

1. Confirm which D3D9 calls the engine makes for fog (instrument: log `Set*ConstantF`
   writes carrying fog-like values).
2. Build a minimal x86 probe DLL (adapt `K:\tvt_los\hook.cpp`) that logs those calls.
3. Run **Zitadelle**, capture a trace, answer: do unit draws get fog constants or not?
4. Act on the answer: force fog on units (if they just lack the uniforms) vs patch the
   unit shader pass (if it's a shader-selection issue).

Safety: all of the above is read-only until step 4; backups not needed yet.
