# ZeeWolf 2015 — two diagnoses

*2026-08-19. Both established by measurement on a copy of the ZW2015 install.
Its `Behavior.dll` is byte-identical to REDUX's, so everything different about
it is content, script and settings — which is where both of these live.*

---

## 1. White pockets in distant terrain — FIXED

### The symptom

From the F6 external camera, distant terrain is perfect. From the FPS commander
**unbuttoned** view, the same ground shows large white pockets.

### The cause

`Common\Camera.script`, ZW against REDUX:

| | ZNear | ZFar | depth range |
|---|---|---|---|
| REDUX | 1.0 | **500** | 500 : 1 |
| **ZW** | 0.5 | **6437.38** | **12,875 : 1** |

ZW pushed the far plane out **thirteen-fold** for its 18 km maps — reasonable in
itself — and never revisited the near planes, which were tuned when the far
plane was 500 m.

`Common\PlayerUnit.script` then sets a per-view near plane, and the unbuttoned
commander gets the tightest of all:

```
if (UPS_Commander == m_PlayerSit)
  if (m_HatchCommanderOpened)
    Camera.SetZNear(0.15f);        // 6437 / 0.15 = 42,913 : 1
```

against the external camera's `SetZNear(1.5f)` — 4,291 : 1, **ten times
better**. A 24-bit depth buffer cannot resolve distant terrain at 42,913 : 1.
Patches z-fight and lose to the sky, giving sharp-edged bright pockets that
appear only at distance and only from the low view.

### The fix

One line, `PlayerUnit.script` line 976:

```
Camera.SetZNear(0.8f);
```

**8,047 : 1** — a five-fold gain, in the same territory as the camera that
already looked right. Confirmed fixed in play, and no new errors in
`execution.log`.

0.8 m is safe here specifically *because* the hatch is open: the commander's
head is outside the tank, so there is no interior geometry near the eye. The
buttoned-up views still need their tight near planes and are untouched.

**The same reasoning applies to the other cockpit views** — gunner and driver at
0.1–0.15 with the same 6437 far plane — but they look at the world through
optics and vision blocks, so distant terrain is a much smaller part of the
image and the artefact may never have been noticed.

### A wrong turn worth recording

The first hypothesis was a texture fault, and it produced a real finding that
was **not** the cause: `Textures\lnd_micro16.tex` — index 7, Forest, in the
mega-terrain's distant micro-texture tier — ships with **zero mipmaps** where
all fifteen of its siblings carry six.

```
lnd_micro09..15   256x256 DXT1   6 mips   43,808 bytes
lnd_micro16       256x256 DXT1   0 mips   32,896 bytes
```

That is a genuine defect and would cause aliasing at grazing angles, which is
why it looked plausible. It was rebuilt (base level kept byte-identical, only
levels 1–5 generated) and made no difference to the white pockets, so it was
reverted. The fixed copy is kept at `K:\tvt_los\lnd_micro16.tex.withmips` and
the rebuild tool at `Tools/LineOfSight/fix_mipmaps.py`.

The user's objection was the better read: *"if it was texture the problem would
be on both cameras"*. Not strictly true — minification is view-dependent, so a
missing mip chain **can** show on one camera and not another — but the instinct
that a per-camera artefact points at per-camera settings was right, and it
pointed straight at the near plane.

---

## 2. The framerate: a ~20 ms CPU floor, cause not yet identified

*This section was first written after two readings and claimed the answer was
unit count. A third reading broke that, and the correction is more interesting
than the original claim.*

Measured with the DXVK HUD:

| | units | fps | frame | draw calls | GPU | GPU ms | **CPU ms** |
|---|---|---|---|---|---|---|---|
| REDUX C2M5 | 29 | 90 | 11.1 ms | 450 | 29% | 3.2 | **~8** |
| ZW C2M1 | 116 | 50 | 20.0 ms | 911 | 12% | 2.4 | **17.6** |
| ZW KurskMission4 | **426** | 32 | 31.3 ms | 3484 | 36% | 11.3 | **20.0** |

("CPU ms" is frame time minus GPU time — the per-frame cost that is not
drawing.)

### What is solid

**Not GPU-bound, in any scene measured.** 12% and 36%. Even where draw calls
nearly quadrupled the card stayed two-thirds idle. Graphics settings — LOD,
draw distance, resolution — are close to free on this install.

**Not draw-call bound either.** Between the two ZW readings draw calls went up
**3.8×** and CPU time rose **14%**, from 17.6 ms to 20.0 ms. Submission is
cheap. Batching, instancing and state caching are dead ends here.

**There is a floor of roughly 18–20 ms per frame** of CPU work that is not
drawing, and it barely moves between two very different scenes.

### Where the first conclusion was wrong

Two readings gave 2.5× the units for 2.2× the CPU time and that looked
conclusive. The third has **3.7× the units of the second** and costs **14%
more CPU**. If the cost were per-unit, 426 units against 116 would be 65 ms a
frame and about 15 fps. It is 32.

So **the engine is not ticking all 426 units at full rate.** It is almost
certainly culling or staggering distant AI — which is sensible design, and
means ZW's very large orders of battle are considerably cheaper than they look.
KurskMission4 fields **426 fighting units, 306 of them Soviet riflemen**, plus
574 building interiors and 41 object groups.

Unit count is therefore *at most* part of it, and the floor's real cause is
unidentified. Candidates, in no particular order: terrain paging over the 18 km
maps, the interior objects, general object management, or something fixed per
frame that has nothing to do with content at all.

### The measurement that would settle it

Boring and decisive: the same spot in the same mission, once as shipped and
once with most AI groups removed from `Content.script`. **If the ~20 ms floor
does not move, it was never the units** — and the search moves to terrain and
object management.

Until someone runs that, "ZW is slow because of the unit count" is a plausible
story rather than a finding, and this document should not have said otherwise.
