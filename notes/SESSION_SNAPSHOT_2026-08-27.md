# START HERE — snapshot, 2026-08-27 (early hours)

Replaces every earlier snapshot. The project is **TvTPP — the T-34 vs Tiger
Preservation Project**.

# TODAY'S HEADLINE: the gunsight went 19.6 -> 76.9 fps

The T-34 gunsight ran at ~20 fps against ~100 external, same direction. The user
could not aim and quit a session over it. **3.9x, from two changes in ZW:**

```
tree wind CPU -> GPU (BaseSTTree.script)   ~30 fps    +50%
FogFarMax 3000 -> 1500 (C1M2 Content)      76.9 fps   +156% on top
```

**Cause:** a magnified view extends draw distance toward `FogFarMax`. At 3000 m
against an external `FogFar` of 500 m that is **36x the area**. The drawcall
probe showed it: draw calls **261 -> 2105 (8.1x)** while triangles only went
3.1x - many more cheap objects, i.e. seeing FURTHER, not in more detail.

**`FogFarMax` is set in `Content.script`, which WINS over `Atmosphere.script`.**

## STILL OPEN on this - the user says it looks worse

- [ ] **`FogFarMax` 1500 -> 2000.** Area scales with r^2, so 2000 buys back a
  third of the view distance and should still leave ~45 fps. 77 is more than
  needed to aim.
- [ ] **`FogFar = 3.0` in that Content.script looks like a typo** - the
  Atmosphere.script copy says 500. If FogFar is where haze reaches full density,
  3 metres would explain the washed-out look. **This may be the real fix for
  the appearance, and it costs no frames.**
- [ ] **REDUX almost certainly has the same gunsight cost** - never checked.
- [ ] **"Forest distance" is a real Video-menu slider sitting at half** and has
  never been touched. Next lever if more is needed.

## THREE WRONG ANSWERS FIRST - all inferred from a setting's NAME

1. `ModelLOD` [40,60,120,480] -> [40,70,180,250]: no effect. LOD uses TRUE
   distance, which magnification does not change.
2. **`FOVDistPower` DOES NOTHING.** Every reference is inside the video options
   menu, which reads it, shows it, writes it back. Nothing consumes it; it is
   not in the engine's settings dump. A Whirlwind over Vietnam leftover. Kept in
   the launcher as `Zoom detail *` with a tooltip saying so, deliberately, so
   nobody rediscovers it.
3. The fix came from **the drawcall probe**, not from reasoning.

---

# ZW's BIAS: 48 values changed, and the first pass missed the point

**The user was right that ZeeWolf had a bias. It is in HANDLING and GUNNERY,
not penetration.** An earlier pass checked only the penetration table and
wrongly dismissed the claim.

**The control that removes doubt:** StuG III and SU-85 are the same class of
vehicle and G5 set both to exactly **1.2**. ZW made the StuG **0.02** and left
the SU-85 at 1.2 - 60x apart from an identical start.

```
pass 1   23 values reverted to G5 (accuracy, traverse, mass, speed, fire period)
pass 2    3 sensor ranges equalised (T-34s 1650/800 -> 2600 detection)
pass 3   21 ZW-ONLY units mapped to G5 counterparts
pass 4    1 Panzer IV deceleration 2.5 -> 1.5
```

## The lesson: CHECK WHAT THE MISSIONS ACTUALLY FIELD

Pass 1 fixed the stock units. **The missions field ZeeWolf's own variants** -
`CTankPzVI_E1_AI_Unit`, `CTankPnzIV_G_AIUnit`, `CTankT34_76_42AIUnit` - which
pass 1 could not touch because they have no 2001 original to diff against. The
**Tiger E1 was on FireDeviation 0.001 against G5's 1.2 - twelve hundred times
more accurate.** One grep of `execution.log` for instantiated unit classes would
have shown this immediately.

**REDUX is the 2001 original on these fields**, so all of it was a revert with no
design judgement - unlike the penetration question, which is still open.

Backups: `ZW_Units_2026-08-27_pre_revert\` and `..._pre_zwonly\`.

---

# VERTICAL MOUSE AIM - a G5 bug fixed after 25 years

`SetMouseSensitivity` takes **separate** horizontal and vertical values and the
game passed the **same** one to both. A 16:9 monitor's vertical FOV is 1.78x
smaller, so the gun moves faster vertically. Present in the 2001 original,
REDUX and ZW.

New `MouseVerticalScale` in `GameSettings.script`, default **0.5625**
(1080/1920), applied at all three call sites in **both builds**. Exposed in the
launcher beside the mouse speed box.

**The user found this by feel** - "about correct laterally but faster
vertically" is an exact description of a 1.78x ratio.

---

# THE LAUNCHER

`K:\tvt_los\TvT_Launcher.ps1` — **run it with `K:\tvt_los\TvT.bat`.**
`cmd /c launcher.ps1` does NOT work; cmd cannot execute a .ps1 and just prints
the source.

Engine tuning section, six registry settings the game never exposes:

```
Zoom detail *   INERT, labelled      Max lights       real
Forest anim     real (confirmed)     Texture LOD      real, unlikely to help
Shadow detail   real, CPU-bound      Forest density   real, blunt
```

Plus separate **vertical** mouse scale. All tooltips carry the measured numbers.

---

# CRITICAL: EDIT GAME FILES AS BYTES

```python
d = open(p,'rb').read();  open(p,'wb').write(d.replace(old,new,1))
```

Python text mode silently converts CRLF -> LF. On 2026-08-27 that damaged **31
ZW script files** before it was caught - only because one file shrank 2,773
bytes. **Check the file size after every write.** `grep -c $'\r'` does NOT
detect it; count `d.count(b'\r\n')` instead.

Both builds are uniformly CRLF (ZW 418/419, REDUX 287/295), so any pure-LF
`.script` is damage. **REDUX still has 7 pure-LF files** from earlier sessions -
flagged, not touched, user's call.

Also: `\t` in a Python bytes literal keeps eating `\tvt_los` paths. **Use forward
slashes.**

---

# TOMORROW'S LIST

1. **FogFarMax 1500 -> 2000, and investigate `FogFar = 3.0`** (above).
2. **The King Tiger unit class** - ~1,800 lines from the Tiger E1 template. 14
   class names already dictated by the shared files; all constants exist. The
   `.ms2` format is solved both ways so the model side is no obstacle.
3. **Penetration realism** - route still unchosen, a design decision. REDUX's
   tables ARE the real historical figures; leave REDUX alone.
4. **The ambient pass** across the other 11 campaign missions.
5. **ZW performance** - 36-60 fps external and view-dependent.

# FACTS NOT TO RELEARN

- **TvT is CPU-bound, GPU idle (~24%).** Never a GPU problem.
- **Noise floor +/-4%.**
- **native D3D9 == DXVK** (50 vs 48 fps with F9 on both). Closed.
- **Only F9 reads fps on every renderer.** ReShade does NOT attach on native.
- **The drawcall probe's own fps was once inflated 2.3x** - its clock is now
  confirmed correct (QPC vs GetTickCount agree each block).
- **Anti-aliasing BREAKS rendering** (no terrain, invisible tanks, silently) and
  persists to the registry. Left disabled.
- **`.ms2` is solved both ways** - importer builds finished vehicles, exporter
  confirmed accepted by the engine. Counts must not change.
