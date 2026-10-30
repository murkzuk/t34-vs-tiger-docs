# ZW and REDUX have completely different performance problems

2026-08-26. Profiled ZeeWolf 2015 the same way REDUX was profiled the day
before. **The conclusions do not transfer.** Only "CPU-bound with the GPU idle"
is common to both.

## Where each build's frame actually goes

| | REDUX | ZW |
|---|---|---|
| top page | the `std::map` lookup, **20.4% of module** | `CAbstractObject`, 7.8% |
| vegetation | ~15% (grass + trees) | **absent from the top 20** |
| objects / joints / collision | not in the top 20 | **~40%** |
| the map lookup | 20.4% | 2.9% |
| concentration (50% of module) | 11 KB | 11 KB — but eleven *different* KB |

ZW's hot pages, by RTTI class:

```
+0x017000   7.77%   CAbstractObject
+0x0C1800   7.66%   CCylinderShape / CBaseConvexShape / CDynamicIntersector
+0x002400   7.16%   CAbstractJoint
+0x0C1C00   4.72%   CCylinderShape / CDynamicIntersector
+0x01E400   4.28%   CAbstractObject
+0x002800   3.33%   CAbstractJoint
+0x014800   3.28%   CAbstractObject
```

`CDynamicIntersector` sitting alongside `CCylinderShape` means **collision
testing** — hundreds of moving objects checked against each other every frame.

## Why: the component census

The engine prints one at shutdown. Same two builds:

```
component                  REDUX      ZW    ratio
AbstractObject                57     496     8.7x
AnimatedObject                56     495     8.8x
ObjectPhysicsController       58     493     8.5x
Weapon                        62     455     7.3x
CylinderShape                146     926     6.3x
BoxShape                     134     778     5.8x
AbstractJoint                550    2536     4.6x
ScriptHost                  1224    3916     3.2x

TreeObject                   380      30     0.1x   <-- ZW has FEWER trees
TOTAL COMPONENTS          26,298  84,143     3.2x
```

**ZW missions carry roughly nine times the objects and one thirteenth the
trees.** ZeeWolf built grandiose set-piece battles; REDUX's missions are
smaller and wooded.

## The grass question, answered properly

ZW *has* grass, yet grass is a far smaller load. Measured:

```
grass-range samples as a share of ALL frame time
   REDUX   8.84%
   ZW      1.22%      = 7.3x difference
```

**Two independent causes, and they multiply.**

### 1. ZeeWolf tuned the grass down (3.35x less planted)

`BaseGrass.script`:

```
              max distance      falloff power
REDUX          20 -> 150 m            5
ZW             10 -> 120 m            8
```

Effective planted area is `2*pi*R^2 / ((p+1)(p+2))`:

```
REDUX   R=150, p=5  ->  3,366 m2
ZW      R=120, p=8  ->  1,005 m2      3.35x less
```

**`MaxVisDistPower` is the big lever, not the distance.** Going from 5 to 8
thins distant grass dramatically while barely touching what is near the tank.

### 2. ZW's frame is longer, so the same cost is a smaller slice (2.2x)

With 496 objects and 2,536 joints, ZW spends far more per frame on everything
else. Grass keeps its absolute cost and shrinks as a percentage.

```
3.35x (less grass) x 2.2x (longer frame) = 7.4x     observed 7.3x
```

Accounting for it almost exactly is a good sign the explanation is right rather
than merely convenient.

## What follows from this

- **"Faster trees" (the map cache) is near-pointless in ZW.** The function it
  accelerates is 2.9% there against 20.4% in REDUX. Tick it for REDUX.
- **Do not tune ZW's grass.** ZeeWolf already did, and did it well.
- **UNPULLED LEVER FOR REDUX: `MaxVisDistPower` 5 -> 8.** Would cut REDUX's
  grass cost roughly 3x while shortening the *apparent* distance far less than
  the number suggests, because near grass barely changes. Not tried. Measure it
  the usual way — predict first, use the self-A/B or a slider A/B.
- **The two builds need separate performance thinking from here on.**
  REDUX = vegetation. ZW = objects and collision.

## Method note: a reading error worth not repeating

The concentration line initially looked broken — it claimed 50% of the module in
11 KB while the visible top pages summed to only 32%. The tool was right;
`tail -30` had silently cut the top four entries out of view. With the full
block, the top 11 sum to 51%.

**Print the whole report block, never a tail of it**, before concluding the
tooling is wrong.

---

## REDUX grass retuned, 2026-08-26 — the lever pulled

`MaxVisDistPower` was the unpulled lever noted above. Applied ZW's settings to
REDUX, found power 8 too abrupt, settled on **6**.

```
                        R      p    effective area
G5 stock              150      5      3366 m2    1.00x
ZW                    120      8      1005 m2    3.35x less   (tried, too abrupt)
REDUX now             120      6      1616 m2    2.08x less   <- KEPT, user approved
```

**Measured in C1M1** by toggling the in-game grass slider mid-run — same scene,
same session, so no cross-mission confound:

```
                SEGMENT 1   SEGMENT 2 (grass off)   change
fps                  93.0                 103.7    +11.5%
triangles         339,913               326,566     -3.9%
CPU ms/frame        10.71                  9.61    -10.3%

grass now costs 13,347 triangles and 1.10 ms/frame
```

**The model held.** At power 5 in C1M2 grass was **33,751 triangles**; at power
6 with the shorter distance it is **13,347** — a 2.5x cut against the 2.08x the
area formula predicted. Close enough that
`area = 2*pi*R^2 / ((p+1)(p+2))` can be trusted for future tuning.

Grass still takes ~10% of the frame, but that is because C1M1 is a lighter
mission overall (93 fps vs C1M2's 68) and grassier terrain - a smaller absolute
cost is a similar slice of a shorter frame.

**User verdict on the look at power 6: fine.** Power 8 was not tested visually
to a conclusion; 6 was chosen as the safer falloff and approved.

### A comparison that was nearly reported and should NOT have been

The first drawcall run after the change appeared to show **+24.4% fps**. It was
worthless: the baseline was yesterday's **C1M2** and the new run was **C1M1**.
The tell was in the data - draw calls **+31%** and triangles **+25%**, when
cutting grass cannot possibly increase either. Different scene, not a result.

**Check that the before and after are the same mission before reporting any
delta.** The in-run slider toggle is the way to avoid it entirely.
