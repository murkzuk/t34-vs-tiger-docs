# Dust see-through (tank-shaped hole in wheat) — investigation + proposed fix

Status: **investigated end-to-end** 2026-08-28. Fix **NOT found** — confirmed render-order/sorting bug. Additive + ZWRITE-off + UP-hook all tried, all failed; game restored.

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
