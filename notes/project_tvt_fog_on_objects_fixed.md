# Fog on distant objects — FIXED (2026-08-27)

The last big Phase-2 "wow" item is solved: **distant tanks now sit in the haze**
instead of popping out sharp. Live as a launcher toggle, both builds.

## The problem

Distant-LOD tanks rendered with `vs_1.1` shaders had **no fog**, while near-LOD
`vs_2.0` tanks did. A tank at range was a bright, sharp silhouette floating
against a hazed terrain — "black shadow standing out."

## Root cause (proven with probes, not guessed)

1. The engine renders near LOD with `vs_2.0` (fog on) and distant LOD with
   `vs_1.1` (fog off) — **both variants ship per material family**, confirmed by
   a `CreateVertexShader` dump (54 `vs_1.1` + 124 `vs_2.0`).
2. **The wrapper is innocent.** `GetDeviceCaps` reports `VertexShaderVersion 3.0`
   under DXVK — so it is NOT a caps/clamping issue (Claude's "DXVK angle" was
   tested and disproven).
3. **The engine simply switches fog off for distant LOD** — it sets
   `D3DRS_FOGENABLE=0` / `FOGVERTEXMODE=0` before the `vs_1.1` draws.
4. **The `vs_1.1` shader DOES write a fog factor.** A force-fog test (fog forced
   on everywhere) made distant tanks fogged — so the missing piece is the render
   state, not the shader.

## The fix

`K:\TvTDeepseek\fogfix\fogfix.dll` — a D3D9 render-state hook, not a shader swap:

- Hooks `CreateVertexShader` (maps handle → major version), `SetVertexShader`
  (tracks the bound shader), `SetRenderState` (remembers the engine's own fog
  density/colour/mode), and `Draw*`.
- Before each draw, **if the bound shader is `vs_1.x` and fog is off, turn fog
  back on** using the engine's own fog values.
- Everything else (near LOD, UI, sky) is untouched — near LOD already had fog,
  and the UI/sky don't bind `vs_1.x`.

Verified in game: **94,321 fog-on restores** in one session, 488 shaders tracked.

## Launcher toggle

`K:\tvt_los\TvT_Launcher.ps1` gained **"Fog on distant tanks"** — tick it, and it
injects `fogfix.dll` alongside Line-of-sight / Faster trees. Mutually exclusive
with the Profiler (like the others). Form grew 22 px; parses clean.

## Builds

- ✅ REDUX and ✅ ZW — both use the byte-identical DXVK `d3d9.dll`
  (4,124,686 bytes), same `gcc` prologue, same engine bug.
- ✅ DXVK and ✅ native (MSVC prologue). ❌ dgVoodoo (its `55 8B EC 8B 4D`
  prologue isn't in the probe's safe-list yet — fails safe, no harm).

## Tooling

- Fix: `K:\TvTDeepseek\fogfix\fogfix.{cpp,dll}` (build with `build.bat`)
- Test (force-fog everywhere): `K:\TvTDeepseek\fogforce\fogforce.dll`
- Caps/shader dump: `K:\TvTDeepseek\caps_probe\caps_probe.dll`
- Launcher backup: `K:\TvTDeepseek\rollback\TvT_Launcher_2026-08-27_pre_fogtoggle.ps1`

## Related

- Investigation trail: `project_tvt_fog_hook_scoping.md`
- The `vs_1_1` shader-model finding and the earlier (correct) retraction that
  "`vs_1_1` = distant LOD" was the lead into this.
