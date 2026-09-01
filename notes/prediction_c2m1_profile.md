# Prediction, written BEFORE the C2M1 profile run — 2026-08-26

C1M1 was profiled; C2M1 never was. C2M1 is a village:

```
C1M1   190 draw calls   ~100 fps
C2M1   459 draw calls    52.6 fps    GPU 24%
```

## What I expect

1. **C2M1's hot list will look more like ZW's than C1M1's.** ZW's profile is
   objects/collision (`CAbstractObject`, `CAbstractJoint`, `CCylinderShape`,
   `CDynamicIntersector`); C1M1's is vegetation (`CGrass`, `CSTForest`,
   `CTreeKiller`). A village is objects, not foliage.
2. **`Objects.dll` stays the dominant module** at 50-60%.
3. **The map lookup at `+0x17DAB0` will NOT be top** — it is already cached at
   67% hit rate, so its remaining cost should be roughly a third of what it was.

## What would falsify this

If C2M1's hot pages are still `CGrass`/`CSTForest`, then draw-call count is
not tracking the real cost and the village theory is wrong — the fps
difference would be foliage density, not object count.

## Noise floor

+/- 4%. Anything smaller is not a result.
