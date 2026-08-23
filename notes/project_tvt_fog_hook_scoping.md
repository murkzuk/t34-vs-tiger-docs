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

## RESULT 2026-08-23 — fog DOES NOT reach ~half the unit draws (bug confirmed)

The probe now works end-to-end (loader-notification hook, v3+, then per-draw
tagging v4..v7). Final v7 histogram tags each draw with: bound vertex shader,
fog ON/OFF (`FOGENABLE!=0 && FOGVERTEXMODE!=0`), shadow pass
(`D3DRS_COLORWRITEENABLE==0`), and SKINNED (wrote a bone-array, `vcount>=8`).

**The answer to "does fog reach units": partially — and the missing half is the
bug.** Skinned (unit) shaders split cleanly in two:

- **Fogged** units: ~430k draws, fog ON, receive `FogFar=1000`/`FogDensity=0.0005`
  constants.
- **Unfogged** units: ~477k draws, fog OFF, **never receive fog constants**, and
  `shadow=0` (colour-writes ON) so they are real geometry, NOT stencil shadows.

The unfogged skinned shaders (this run's handles — opaque, re-randomised per run):

| shader | draws | fog | shadow |
|---|---|---|---|
| 242C0930 | 177,049 | OFF | 0 |
| 242C4BE0 | 68,491 | OFF | 0 |
| 242BF700 | 68,491 | OFF | 0 |
| 242C3CB8 | 68,491 | OFF | 0 |
| 207A54F8 | 68,358 | OFF | 0 |
| 207A45D0 | 26,737 | OFF | 0 |

So the engine sets fog uniforms for SOME unit passes and skips others. This is
the **"missing uniforms"** case (scoping-note step 4, first branch), and it
explains "distant tanks stay sharp": the biggest unfogged shader (177k draws) is
almost certainly the tank mesh.

### Root-cause shape (not yet proven which units)
- The unfogged shaders are the SAME kind of skinned mesh as the fogged ones, so
  it is not a capability gap — it is a per-pass wiring gap.
- Two plausible mechanisms, both need the shader→`.fxo` mapping to decide:
  1. **LOD swap**: near tanks use a fogged LOD, distant tanks swap to an unfogged
     LOD (matches "distant" precisely).
  2. **Per-unit-type**: one unit family (e.g. the Tiger, or the T-34) is drawn
     through an unfogged shader while the other is fogged.
- Next step: map the runtime shader handles to the `.fxo` files (hash the shader
  bytecode via a `CreateVertexShader` hook, or correlate fog-constant register
  slots 16/17, 19/20, 25/26, … with the `.fxo` constant tables) to name the
  affected meshes, then fix the engine/script that fails to set fog for them.

### Which units are unfogged — .fxo constant-table analysis (2026-08-23)

Parsed the D3DX `CTAB` constant tables inside every `SkinMesh*.fxo` and matched
each shader's `FogNear`/`FogDensity` register against the registers the engine
actually wrote at runtime (16/17, 19/20, 25/26, 97, 104/105, 110/111, 190/191,
192, 195/196, 226/227). Result — fog is skipped for **specific material
families**, not randomly:

- **`SkinMesh1_K*`** (every K-lighting variant) — ENTIRELY unfogged.
- **`SkinMesh1_NB*` / `SkinMesh1_NP*`** (N-lighting + B/P diffuse) — entirely unfogged.
- **`ANNN`, `MNNN`, `Laser`, `Thermal`** (SkinMesh1 and 4) — unfogged special cases.
- **`C*`, `D*`, `E*`, `M*`, `N*` (M/N diffuse)** — MIXED: some passes fogged, some not.

Key structural fact: each `.fxo` carries BOTH `vs_1_1` passes (FogNear only, no
`FogDensity`/`FogFar`) and `vs_2_0` passes (FogNear + FogDensity; `FogFar` is a
pixel-shader param). The `vs_1_1` passes are the low-detail (distant) renders and
are never fogged. This is the mechanism behind **"distant tanks stay sharp"**:
the near/high-detail LOD gets fog, the distant/low-detail LOD does not.

The material suffix is `[lighting][diffuse][normal/specular][LOD]`, derived by the
engine from each `CModelMaterial` (Models\*.script: texture/bump/specular present,
`LMDL_*` lighting model, `MSID_*` substance). To name the exact tank models still
needs the native `LMDL_*`->letter enum (engine-side, not script), but the affected
group is already precise: the K-lit and N+B/P skinned meshes, plus every distant
`vs_1_1` LOD pass.

### Probe build notes (worth keeping)
- The game exits via `TerminateProcess` (DXVK/Vulkan stuck-in-driver), so
  `DLL_PROCESS_DETACH` does NOT fire — a detach-only summary is lost. v5+ dumps
  the histogram every 100k draws from the draw path instead.
- Killed game processes linger as zombies holding `fog_probe.dll`; the DLL must
  be renamed aside (`fog_probe.locked*.dll`) before rebuilding.