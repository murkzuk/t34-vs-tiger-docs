# Fog-on-objects — hook scoping plan (2026-08-23)

STATUS: **probe built** (`K:\TvTDeepseek\fog_probe\`); read-only; awaiting a Zitadelle run.

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

## Wrapper consideration (DXVK vs dgVoodoo) — 2026-08-23

The user runs DXVK (has the choice dgVoodoo/DXVK via wrapper.bat). Implications for the hook:
- The hook targets the D3D9 device VTABLE (SetVertexShaderConstantF, DrawIndexedPrimitive,
  etc.) - the SAME API both wrappers implement. So the hook is WRAPPER-INDEPENDENT: it
  works whether d3d9.dll is dgVoodoo or DXVK.
- The fog bug is confirmed in BOTH builds/wrappers (Rendering_And_Framerate.md) -> it is
  ENGINE-side, not wrapper-side. We observe the ENGINE's calls, not the wrapper.
- IMPORTANT: the G5 fog is SHADER-computed (the .fxo files read FogFar/FogDensity and
  compute fog themselves). DXVK/dgVoodoo do NOT decide fog - they just run the shader and
  pass the uniforms through. So there is no wrapper "fog toggle" to flip; the fix is
  entirely about whether the ENGINE sets those uniforms for the unit pass.
- Bonus: DXVK is open-source - its D3D9 source is a reference if we ever need to trace the
  uniform-passing path, but it is not the source of the bug.

## Progress 2026-08-23 — fog_probe (the D3D9 probe)

Built `K:\TvTDeepseek\fog_probe\fog_probe.dll` (x86 MSVC). Hook chain:
`Direct3DCreate9` export -> `IDirect3D9::CreateDevice` (slot 16) -> device slots
57/81/82/94/109 (`SetRenderState` / `DrawPrimitive` / `DrawIndexedPrimitive` /
`SetVertexShaderConstantF` / `SetPixelShaderConstantF`). Logs fog render states,
deduped shader-constant registers, and draw volume. Read-only: pass-through hooks,
append log only.

**Critical finding (dumpbin-verified): `TvsT_fullLOD_HARD_4GB.exe` does NOT
statically import `d3d9.dll`.** Its import table has `LoadLibraryA` +
`GetProcAddress` (plus WINMM/USER32/GDI32/ole32/MSVCR70) but no d3d9. So the game
loads the wrapper (`d3d9.dll` = DXVK/dgVoodoo) **at runtime** and immediately
`GetProcAddress("Direct3DCreate9")` + calls it.

Consequence — three hook-timing attempts, two wrong directions:
- **v1 (polling boot thread + Sleep):** patched too late — the game had already
  created its device (log: patch landed, zero draws, no `Direct3DCreate9(...)`).
- **v2 (synchronous patch in DllMain):** too early — under `CreateRemoteThread`
  injection the main thread is suspended, so the runtime-loaded `d3d9.dll` is not
  yet mapped at attach (log: `d3d9.dll not loaded at attach`).
- **v3 (loader notification, current):** register `LdrRegisterDllNotification`
  (ntdll); its callback fires DURING `d3d9.dll`'s load, before `LoadLibraryA`
  returns, so we patch `Direct3DCreate9` (resolved by walking the PE export
  directory — the callback must NOT call `GetProcAddress`, which takes the loader
  lock) before the game can ever `GetProcAddress` the export. Boot thread kept as
  fallback only.

The LOS hook's own pattern (`K:\tvt_los\hook.cpp`: DllMain -> `Boot` thread ->
`GetModuleHandleA("Behavior.dll")` poll with `Sleep(100)`) is NOT suitable here:
`Behavior.dll` is loaded early and its hooked functions fire during gameplay — a
huge window — whereas `Direct3DCreate9` fires microseconds after a runtime
`LoadLibraryA`.

Next: run Zitadelle with v3, confirm the full chain (attach -> notify -> patch ->
`Direct3DCreate9(31)` -> device -> fog/draw lines).