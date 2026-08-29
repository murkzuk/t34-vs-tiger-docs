# Terrain LOD — distant tanks float above ground in FPS view (ZW)

Status: **identified, plan recorded** 2026-08-29. Not fixed yet.

## Symptom

- In **FPS view**, distant tanks float above the terrain.
- In **binocular/gunsight view**, the same tanks sit correctly ON the terrain.
- View-dependent → it's a terrain-LOD bug, not a tank-position bug.

## Finding

- ZW uses a **custom terrain system REDUX does not have**:
  `Scripts/Common/BaseMegaTerrain.script` ("MegaTerrain", for ZeeWolf's huge
  9–36 km maps). REDUX uses plain `BaseTerrain.script`.
- The terrain geometry detail lives in `BaseMegaTerrain.script`:
  - `MinimumResolution = 1.0`   (range 2–6)
  - `DesiredResolution = 1.0`   (range 12–24)
  - `TerrainDetail = 1.0` in `GameSettings.script` (drives shoreline detail etc.)
- At distance the coarse LOD tessellates the ground *below* the tank's true
  height → the tank floats. The zoomed bino/gun view uses a finer LOD → correct.

## Headroom

- The engine is CPU-bound; the GPU is mostly idle. Raising terrain detail should
  be nearly free visually, so this is a "spend idle GPU, don't touch CPU" fix.

## Plan

1. Read `BaseMegaTerrain.script` in full — work out how
   `MinimumResolution` / `DesiredResolution` / `TerrainDetail` drive the terrain
   mesh LOD, and which one controls the *distance* falloff (that's the one that
   fixes floating, not just near detail).
2. Identify the single value to raise (and by how much) so distant terrain keeps
   the tank's true height, without a big CPU cost.
3. Propose it — backup-first, A/B test (same discipline as the camera port).
4. A/B test: distant tanks should sit ON the terrain in FPS view; check FPS.
5. Decide scope: MegaTerrain is ZW-only, so this is ZW-only unless REDUX's
   `BaseTerrain.script` has the same LOD behaviour (check it).

## Notes

- Same *family* as the dust/tree transparency issues (ZW-specific rendering
  quirks), but a **separate root cause**: terrain mesh LOD, not alpha-blend sort.
- Related already-recorded work: camera diff (`ZFar`/FOV/momentum) rolled back;
  dust render-order bug (handed to Claude).
