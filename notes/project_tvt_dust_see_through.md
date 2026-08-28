# Dust see-through (tank-shaped hole in wheat) — investigation + proposed fix

Status: **built + wired** 2026-08-28 (`dustfix.dll` + launcher toggle). Untested in-game.

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

## Mechanism (hypothesis, high confidence)

Two alpha-blended passes (dust on the effects layer, wheat on the vegetation
layer) with **no correct cross-layer sort**, and the dust **writes depth**
(`ZWRITEENABLE = 1`). Where a dust particle overlaps the wheat, the wheat's depth
test then fails → the wheat pixel is dropped → the "tank-shaped hole".

## Proposed fix — same D3D9 hook machinery as fogfix

At `Draw*` time, for **alpha-blended draws** (`ALPHABLENDENABLE == 1`), force
`ZWRITEENABLE = 0`. This is the textbook rule: transparent objects must not write
depth. Ship it as a toggle in a new `dustfix.dll` (or extend fogfix) and A/B test.

Render states to hook/track (D3D9):
`ZENABLE` (7), `ZWRITEENABLE` (14), `ALPHABLENDENABLE` (27), `SRCBLEND` (19),
`DESTBLEND` (20).

Risk to check when testing: **water** is also alpha-blended. If disabling ZWRITE
for all alpha-blended draws breaks water, scope the fix to the effects layer /
`Effect_01.tex` instead of all alpha-blended draws.

## Next steps

1. Build the fix with a live counter (how many alpha-blended draws had ZWRITE=1).
2. A/B test in ZW: drive a tank through wheat; confirm the hole is gone and water
   still looks right.
3. Backup-first before touching `fogfix.cpp` or the game files, per standing rule.
