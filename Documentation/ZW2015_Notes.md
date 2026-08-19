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

## 2. The framerate is unit count, not maps or models

Measured with the DXVK HUD on ZW Campaign_2/Mission_1:

| | ZW2015 | REDUX |
|---|---|---|
| fps | 50 | 90 |
| draw calls | 911 | 450 |
| **GPU load** | **12%** | 29% |

**The GPU is idle.** The high-poly models are not the cost. 911 draw calls is
low enough that the wrapper choice — DXVK or dgVoodoo — barely matters either.

Per frame: 50 fps is 20 ms with the GPU busy for 2.4 ms, so **~17.6 ms of CPU
work that is not drawing**, against roughly 8 ms on REDUX.

The mission holds **116 fighting units, 81 of them infantry** (48 Soviet and 33
German riflemen), against 29 in Campaign_2/Mission_5 and 51 in Berezov. That is
**~2.5× the units for ~2.2× the non-render CPU time** — the two numbers agree,
and neither has anything to do with the 18 km maps or the model fidelity.

Consequences:

- **Graphics settings are free.** At 12% GPU, LOD, draw distance and resolution
  cost essentially nothing.
- **The lever is the order of battle**, particularly the infantry count.
- The grass-overflow fix that was worth ~70 fps on REDUX does **not** apply —
  ZW's log is clean of those warnings.
