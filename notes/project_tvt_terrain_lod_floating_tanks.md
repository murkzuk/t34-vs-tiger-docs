# Terrain LOD — distant tanks float above ground (worse in REDUX)

Status: **identified, plan recorded** 2026-08-29. Not fixed yet. **Corrected** from an
earlier draft that wrongly blamed ZW's MegaTerrain.

## Symptom

- In **FPS view**, distant tanks float above the terrain; in **bino/gun view** they
  sit correctly ON the terrain. View-dependent terrain LOD.
- **More noticeable in REDUX than ZW.**

## Finding (corrected)

- The terrain geometry detail knobs are **identical across both builds and both
  terrain systems**:
  - `BaseTerrain.script` (REDUX) and `BaseTerrain.script` (ZW) and
    `BaseMegaTerrain.script` (ZW) all carry:
    - `MinimumResolution = 1.0` (range 2–6)
    - `DesiredResolution = 1.0` (range 12–24)
  - `OnTerrainDetailChanged()` maps `TerrainDetail` (0–1) → these ranges;
    `GameSettings.TerrainDetail = 1.0` in both, so **detail is already at max.**
- So this is **not** a ZW MegaTerrain thing, and **not** a simple resolution
  setting — it's the terrain LOD *distance falloff* (the chunked/patch LOD at
  range), which is engine-level.
- Why REDUX shows it more: REDUX's camera is wider (FOV 1.5708 / 90°) and its
  `ZFar = 500`, so the distant-terrain LOD transitions sit inside the view and are
  more obvious; ZW's narrower FOV + `ZFar = 6437` hides it more.

## Headroom

- Engine is CPU-bound, GPU mostly idle. Raising distant terrain detail should be
  nearly free visually — "spend idle GPU, not CPU".

## Plan

1. Find the terrain LOD distance falloff — where the engine coarsens distant
   terrain patches. Likely engine-side (native), but check `BaseTerrain.script`
   / `BaseMegaTerrain.script` for any distance/cell/patch params first, and the
   mission `Terrain.script` + `WorldMatricies.script` (cell size / heightmap
   resolution) second.
2. Identify the lever that raises *distant* terrain detail (not just near), or the
   camera/LOD tie that makes the bino/gun view correct but FPS view wrong.
3. Propose a change — backup-first, A/B test (same discipline as the camera port).
4. A/B test: distant tanks sit ON the terrain in FPS view; check FPS.
5. Scope: applies to both builds if the mechanism is shared; verify REDUX first
   (it's the worse case).

## Notes

- Same *family* as the dust/tree transparency issues (rendering quirks), but a
  **separate root cause**: terrain mesh LOD at distance, not alpha-blend sort.
- Related: camera diff (`ZFar`/FOV) was rolled back; REDUX's camera values are the
  "tuned" ones (FOV 90°, ZFar 500) and are untouched.
