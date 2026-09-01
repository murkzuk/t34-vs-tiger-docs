# Dust see-through (tank-shaped hole in wheat) — investigation + proposed fix

Status: **investigated end-to-end** 2026-08-28. Fix **NOT found** — confirmed render-order/sorting bug. Additive + ZWRITE-off + UP-hook all tried, all failed; game restored.

## ✋ Handoff to Claude

This one is yours now (DeepSeek handing off, 2026-08-28). Your 2026-08-27 read was
right: **it's render-order work, not a tweak.** Diagnosis is complete; fix is not.

**To do:** sort the transparent pass (wheat + dust together) back-to-front and
re-issue the draws through the D3D9 hook. Real work, no shortcut found.

**Key facts (full detail below):**
- Wheat writes depth while alpha-blended (`WZAT`, blend 5,6), drawn last each frame.
- Dust does NOT write depth (`-ZAT`); draws before the wheat.
- Tried and failed: force ZWRITE=0 on alpha draws · hook UP draw calls · additive dust.
  All reverted; game is clean.

**Artifacts:** `K:\TvTDeepseek\dustfix\dustfix.cpp` (D3D9 probe) + `dustfix.log`
(1.7M-draw per-texture state dump + draw-order ring buffer). Launcher has a
"Dust fix" toggle; note fogfix and dustfix both patch `Direct3DCreate9` and are
currently mutually exclusive — merging into one DLL is on the table if/when both
need to run together.

## Built (2026-08-28)

- `K:\TvTDeepseek\dustfix\dustfix.dll` (x86) — hooks SetRenderState + Draw* and
  forces `ZWRITEENABLE=0` for alpha-blended draws; logs
  `K:\TvTDeepseek\dustfix\dustfix.log` (counters: draws / alpha draws / forced).
- Launcher toggle "Dust fix" added to `K:\tvt_los\TvT_Launcher.ps1`.
- **fogfix and dustfix both patch `Direct3DCreate9`, so they cannot run together.**
  The launcher makes the Fog and Dust toggles mutually exclusive for now. Merging
  the two fixes into one DLL is the follow-up if both are wanted at once.
- Backup: `K:\TvTDeepseek\rollback\TvT_Launcher_2026-08-28_pre_dusttoggle.ps1`.
Claude's 2026-08-27 confirmation stands: the see-through IS the dust (stop the tank,
no dust, artefact gone).

## Confirmed from the scripts

- **Dust** = `CForestUnitDustTraceEffect` (`Scripts/Common/Effects.script:1924`)
  extends `CAnimatedParticleGenerator` (`EffectsBase.script:18`).
  - base alpha **0.3**, fade 0.0→0.4, 9 particles, `EPPID_BILLBOARD_PLANE`.
  - skin `CGroundDustEffectSkin` = `Textures/Effect_01.tex`, Transparency
    **"NORMAL"** (alpha-blend filter — NOT additive).
- **Grass / wheat** = `CGrassType2 // wheat` (`BaseGrass.script:80`), billboard
  grass, alpha-blended.
- `CBaseEffect.m_SortByZ = true` — effects sort by Z **within the effects layer
  only**. Grass lives on a different (vegetation) layer, so dust vs grass are
  never depth-sorted against each other.
- The engine has **only two** transparency modes — `"NORMAL"` (alpha-blend) and
  `"ADDITIVE"`. There is **no script-level "no depth write" mode**, so the fix
  cannot be a one-line material edit; it has to be D3D9-level.

## Mechanism — CONFIRMED by D3D9 probe (2026-08-28)

The probe (`dustfix.dll` rebuilt as a pure logger: SetRenderState + SetTexture +
DrawIndexedPrimitive, 1.7M draws captured) showed:

- **Wheat/grass** = flags `WZAT` (ZWRITE=1, ZENABLE=1, ALPHABLEND=1, ALPHATEST=1),
  blend `SRCALPHA/INVSRCALPHA` (5,6), ALPHAREF=0, ALPHAFUNC=GREATER (cutout).
  Drawn in a tight loop **last** in the frame. **It writes depth while
  alpha-blended** — the anti-pattern.
- **Dust/effects** = flags `-ZAT` (ZWRITE=0, no depth write), blend 5,6 normal or
  5,2 additive. **It does NOT write depth.**

So the original hypothesis was **backwards**: the *dust* never wrote depth; the
*wheat* does. The wheat draws after the dust and is semi-transparent, so the dust
shows through it — but the exact mechanism that makes it read as a clean "hole"
(not just brighter) is not fully pinned without a dust-in-order capture.

## What was tried (all failed to fix it)

1. Force `ZWRITEENABLE=0` for all alpha-blended draws (dustfix) — 31,649 forces,
   no change (wheat's depth-write is a no-op, it draws last).
2. Also hook `DrawPrimitiveUP`/`DrawIndexedPrimitiveUP` — dust goes through
   `DrawIndexedPrimitive` (DP 2, DIP 1.5M, DPUP 0), so a red herring.
3. Dust transparency `NORMAL`→`ADDITIVE` (order-independent blend) — dust got
   lighter, hole unchanged. **Reverted.**

## Where this lands

This is the render-order / transparent-pass sorting bug Claude flagged on
2026-08-27 ("render-order work through the D3D9 hook … a project, not a tweak").
The real fix is to sort the transparent pass (wheat + dust together) back-to-front
— buffer and re-issue draw calls — which is real work, not a one-liner. Data
captured below is the hand-off for that effort.

Probe artifacts: `K:\TvTDeepseek\dustfix\dustfix.cpp` (probe) + `dustfix.log`
(per-texture dump + draw-order ring buffer). Game files restored (additive
reverted, cache cleared).

---

# 2026-09-01 (Claude) - the old log CANNOT answer this, and the stated mechanism contradicts itself

## Verified, not assumed

`dustfix.log`'s sequence window contains **ZERO dust draws**. The ring buffer keeps
the last 16384 texture changes, and that is always the wheat loop at the end of the
frame. All six textures in the captured window are wheat (`WZAT`, blend 5,6).

So all three attempted fixes were aimed at a mechanism that had never been observed.
That is why they missed - not because the fix was hard.

## The contradiction

On the data we actually have, the stated mechanism cannot work:

- dust never writes depth (`ZWRITE=0`), and
- dust is said to draw entirely BEFORE the wheat.

Something that writes no depth, drawn before something else, **cannot remove that
something else's pixels**. So at least one of those two facts is wrong.

## Prediction, recorded BEFORE the run

The capture will show one of:

- **(a) the ordering is not what we think** - dust interleaved with, or after, wheat
  within a frame; or
- **(b) a render state set for the dust LEAKS into the wheat draws that follow** -
  most likely `ZFUNC`, `COLORWRITEENABLE` or `ALPHAREF`.

**I lean (b).** Ordering alone cannot explain a clean hole. If it is (b), the fix is
small - restore the state before the wheat pass - and NOT the draw-call sorting
system this note proposed.

**Falsifier:** if the wheat rows after the trigger carry identical state to the wheat
rows before it, AND dust is strictly before all wheat, then both (a) and (b) are dead
and the cause is not D3D state at all (look at grass generation instead).

## The tool

`K:\TvTDeepseek\dust_order\` - `dust_order.cpp` / `.dll` / `build.bat` /
`play_dust_order.bat`. Trigger capture: on a dust-signature draw (ZWRITE=0,
ALPHABLEND=1, ALPHATEST=1) it freezes 64 events before and 224 after, keeping the
first 8 such windows so they survive to the log. Every row carries a **frame number**
(Present is hooked, vtable slot 17) plus ZFUNC / COLORWRITEENABLE / CULLMODE.

Pure observation - changes nothing.

## First run FAILED - and it found three real defects (2026-09-01)

The capture hooked nothing: 0 draws, 0 frames, and a **328 MB log**. All mine, not
the user's. Fixed, then verified WITHOUT the game using `test_gpa.exe`:

1. **The shipped d3d9.dll is PACKED.** `M:\T34vsTiger\d3d9.dll` is a 483 KB
   wrapper (Dec 2025) with blank section names. Its `Direct3DCreate9` export points
   at bytes that read **00 00 00 00 ...** at runtime - it decrypts on demand. No
   prologue byte-pattern can ever match it, which is why the MSVC/GCC check failed.
   (dustfix worked on 08-28 because a GCC-built d3d9 was in place then.)
   **Fix: hook `GetProcAddress` instead.** The game imports NO d3d9 statically
   (checked: not the exe, not Engine/Objects/Controls/Behavior/Service/J5Script/
   STTree) - it resolves dynamically, so patching the IAT slot for GetProcAddress
   catches it with no byte patterns anywhere. Verified: the returned pointer lands
   inside our DLL, and a control export still passes through untouched.

2. **The retry loop spun with no sleep and logged every pass** - that is the 328 MB.
   Now one-shot logging plus `Sleep(50)`.

3. **The loader notification was never unregistered.** After the DLL unloads the
   loader still calls into it - an access violation at process exit, which is
   exactly when the log is written. Caught in probe-only mode, with no d3d9 loaded
   at all. **`dustfix.cpp` has this same defect** and should be fixed if reused.
   The IAT slots are now restored on detach for the same reason.

Verification: `test_gpa.exe` (probe-only and full) both exit 0, interception
confirmed, log 922 bytes. The lesson held - suspect the instrument before the
subject, and validate it off the game rather than on the user's time.

## Second run: the probe WORKED, the trigger was aimed wrong (2026-09-01)

The hook fired properly this time - **2,330,245 draws, 147,222 dust-signature
draws, 34,576 frames, 8 windows**. The GetProcAddress fallback did its job (the
prologue was again unrecognised).

But all 8 windows landed in **frames 2-466** - the menu, 4-6 draws a frame - while
the user played 34,576 frames. The trigger captured the FIRST 8 dust-signature
draws, and those are UI elements, not dust over wheat.

Two fixes:
- **Gameplay gate**: a window only arms inside a frame that actually drew wheat
  (>= 200 alpha-blended depth-writing draws of <= 8 prims in the previous frame).
- **Rolling windows**: later triggers overwrite earlier ones, so the LAST 8
  qualifying captures survive instead of the first 8. Each window now records how
  many wheat draws its frame had.

One real observation did survive from the menu capture, worth re-checking in
gameplay: the dust-signature draw ran `ZENABLE=0` (**depth test off entirely**, not
just depth-write off) and `ZFUNC=LESS` while every neighbouring draw used
`LESSEQ`. The following draw was back to `LESSEQ`, so nothing leaked *there* - but
that was a 4-draw menu frame, not the wheat loop.

### Process failure to not repeat
The log path was fixed, so a throwaway regression run **overwrote the 175 KB
gameplay capture** before its texture dump had been mined. The totals and window
analysis survived only because they had already been read. Logs are now
per-PID (`dust_order_pid<PID>.log`).

# CAPTURE SUCCEEDED 2026-09-01 - and my prediction was WRONG

3,170,491 draws / 158,577 dust-signature draws / 32,798 frames / **1135 triggers
in busy frames, last 8 kept**. Calibration worth keeping: peak wheat was only **18
draws per frame**, so the original ">=200 wheat draws" gate was 11x too high - that
is why it fired zero times.

## (b) STATE LEAK - DISPROVEN

I predicted a render state set for the dust would leak into the wheat draws that
follow, and said I leaned that way. **It does not.** Across all 8 windows the wheat
draws before the trigger and after it are byte-identical in state - same flags,
same `ALPHAREF 00/GREATER`, same `ZFUNC LESSEQ`, same `COLORWRITEENABLE 0F`, same
`CULLMODE`. Nothing leaks. Dead.

## (a) ORDERING - CONFIRMED, and the old model was wrong

"Dust draws entirely before the wheat" is **false**. They interleave. From frame
26403 (window 0), the tail of the frame:

    row 73   11110  prims 14    writes depth
    row 74   00110  prims 12    >>> NO DEPTH TEST AT ALL <<<
    row 75   00110  prims 14    >>> NO DEPTH TEST AT ALL <<<
    row 76   11110  prims 2     WHEAT billboard
    row 77   11110  prims 2     WHEAT billboard
    ...
    row 84   11110  prims 2     WHEAT billboard
    row 85   00110  prims 32    >>> NO DEPTH TEST AT ALL <<<
    row 86   11110  prims 2     WHEAT billboard

## The mechanism that actually fits

`00110` = **ZWRITE=0 AND ZENABLE=0**. Depth testing is off *entirely*, not merely
depth-write. Those draws are alpha-blended and sit **between** the wheat billboards.

A draw with no depth test paints over whatever is already in the framebuffer
regardless of distance. So the dust paints over wheat that was already drawn, no
matter how near that wheat is - which is precisely "the dust shows through the
wheat". Wheat drawn *after* (row 86) still appears normally, so the region reads as
a dust-shaped hole rather than a uniform tint.

**This explains why all three earlier attempts failed.** They targeted the wrong
state: dustfix forced `ZWRITEENABLE=0` on alpha draws (31,649 forces, no change) -
but ZWRITE was already 0. The variable is **ZENABLE**.

It also kills the premise of this note's original plan: sorting the transparent
pass back-to-front cannot fix a draw that ignores depth altogether.

## Next test (one state, one run)

Force `ZENABLE = D3DZB_TRUE` on draws that have ZENABLE=0 with ALPHABLEND=1, and
see whether the wheat stops being overpainted. That is the opposite of what was
tried before, and it is a single render state.

Textures involved in the no-depth-test draws: `1F115E38` (also used as a
depth-writing grass atlas - shared) and `1F116420` (`--AT` in the dump: 5,581
draws, no zwrite, no zenable).
