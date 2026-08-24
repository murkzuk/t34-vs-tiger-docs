# Session snapshot 2026-08-24 — handoff for Claude

Written by the DeepSeek agent at the end of its session, so the returning
Claude agent can pick up without replaying the investigation. Everything below
names a file you can check.

## When / who / where

- **When:** 2026-08-23 → 2026-08-24 (one long session, atmosphere/lighting then
  tree work).
- **This agent's checkout:** `K:\TvTDeepseek\t34-vs-tiger-docs`, branch
  **`deepseek/atmosphere-dawn-fog`**. This is where all commits below live.
- **Claude's checkout:** `C:\Users\Jeff\t34-vs-tiger-docs`, main @ `62e077f`
  (plus an untracked `FINDINGS_2026-08-21_log_sweep.md`). **Not pushed** — no
  network. The two checkouts have diverged; the DeepSeek branch is NOT on main.
- **Notes are mirrored** in two places, keep them in sync:
  - `K:\TvTDeepseek\t34-vs-tiger-docs\notes\` (in-repo, committed)
  - `K:\TvTDeepseek\notes\` (master copy outside the repo)
- **Live install:** `M:\T34vsTiger` (REDUX). Reference: `G:\WoV`. ZW:
  `M:\T34vsTiger_ZW2015`.
- **Rollback kit:** `K:\TvTDeepseek\rollback\` — every game-file edit is backed
  up here (timestamped `.bak` files). Never put backups in the game folder.
- **Injection probes:** `K:\TvTDeepseek\fog_probe\` (D3D9 fog, finished) and
  `K:\TvTDeepseek\tree_probe\` (SpeedTreeRT, this session). Injector:
  `K:\tvt_probe\tvt_inject.exe`.

## What happened this session (roughly in order)

1. **Resolution** — investigated the internal render res. Found it is **already
   native 1920×1080** (registry `HKCU\Software\G5 Software\T34` → ScreenWidth/
   ScreenHeight). No bump available; the `WindowWidth=1024` in GameSettings.script
   is only a first-run fallback. → `project_tvt_resolution_finding.md`.

2. **Dawn/sunset rollout** — **C1M3 (19:30 sunset) is DONE and the user says
   "chef's kiss"**. Recipe in `Missions\Campaign_1\Mission_3\Content.script`:
   SunDirection `(0.815587, 0.551964, -0.173648)`, SunColor `(1.0, 0.749020,
   0.294118)` (warmed), AmbientLight `(0.157, 0.204, 0.243)`, FogMode `Exp`,
   FogDensity `0.0013`, FogNear `10`, FogFar `450`. The earlier C1M2/C2M2 dawns
   were already done. **C2M4 (the other sunset) is still pending.**

3. **Tree shadows** — trees are **SpeedTreeRT v1** (`SpeedTreeRT.dll` +
   `STTree.dll` + `.spt` files). Their shadows are terrain-only; they never fall
   on tanks. → `project_tvt_tree_shadow_limitation.md`,
   `project_tvt_speedtree_harvest.md` (SpeedTreeRT is a *geometry factory*, no
   Render method — the "harvest" plan reuses its geometry).

4. **Tree LOD tuning (a saga — read `project_tvt_tree_lod_tuning.md`)**:
   - `ModelLOD` in `BaseSTTree.script` was `[40,70,180,250]` (REDUX "jm" value),
     dev original is `[160,280,480,720]`.
   - Tried `[240,400,700,1000]` → low 30s FPS. Settled on **`[160,280,480,720]`**
     (dev original) — that is the CURRENT live value.
   - `TreeSize` (per species) drives SpeedTree's *internal* LOD AND the drawn
     size (coupled). Raising it → "redwood". Reverted to stock.
   - `TreeShadowLodDistance` (C1M3) experimented with 500, reverted to **25**.

5. **SetTreeSize height-only stretch (the live front)**:
   - **Phase 0** (read-only) proved `STTree.dll` calls
     `SetTreeSize(width = TreeSize, height = 0.0)` — height 0 means "use the
     `.spt`'s own height". That is why the birch is squat (correct width, too
     short).
   - **Phase 1 built but NOT yet user-tested:** `K:\TvTDeepseek\tree_probe\
     tree_stretch.dll`. Hooks `SetTreeSize`; when `h==0` and the tree is
     `Birch.spt`/`Linden.spt`, passes `h = width × K` (K = `2.0`, a `#define`).
   - Spec + Phase 0 result: `project_tvt_settreesize_hook_spec.md`.

## Current live game state (`M:\T34vsTiger`) — the deltas from stock

- `Missions\Campaign_1\Mission_3\Content.script` — sunset recipe (above),
  TreeShadowLodDistance = 25 (stock).
- `Scripts\Common\BaseSTTree.script` — **ModelLOD = `[160, 280, 480, 720]`**
  (this is the ONE tree change still live); TreeSize all stock.
- `Scripts\Common\BaseForest.script` — ModelDistance = 15 (stock).
- Everything else: untouched this session.

## What's next / pending

1. **Test `tree_stretch.dll` in-game** (user's next action). Command:
   `K:\tvt_probe\tvt_inject.exe "M:\T34vsTiger\TvsT_fullLOD_HARD_4GB.exe" "K:\TvTDeepseek\tree_probe\tree_stretch.dll"`.
   Tune `K` in `tree_stretch.cpp` (one `#define`) and rebuild with
   `build_stretch.bat`. Log: `K:\TvTDeepseek\tree_probe\tree_stretch.log`.
2. **C2M4 sunset** — the other 19:30 mission, same recipe family.
3. **Tree shadows on tanks** — "harvest" path scoped (`project_tvt_speedtree_
   harvest.md`), not started.
4. Older open items still valid (from prior snapshots): Pz IV G rollout across
   13 missions; Pz II / Pz III `[0]` LOD fix; 5 "stock noon" missions polish.

## Rules that bit us this session (respect them)

- `.script` = **CP1251**, byte-level edits only; verify EF BF BD count = 0
  before/after. The UTF-8 edit tool is safe ONLY on pure-ASCII files.
- **Delete `Cache\Scripts.cache`** after any script edit (cold rebuild ~2 min).
- **Backups** in `K:\TvTDeepseek\rollback\`, never inside a game folder.
- **Per-AI separation** — each AI works in its own checkout; **the user is the
  last gate** (no game-file write without their go-ahead).
- The game is **not run by this agent** — all in-game verification is the user's.
- Injection allow-list must sit **beside the DLL** (`tvt_los_allow.txt`).

## Commits this session (DeepSeek branch)

```
d85a1a7 SetTreeSize Phase 0 result - engine passes h=0
5607dbf tree LOD tuning - ModelLOD vs TreeSize, coupled size/LOD
cac8da8 SpeedTreeRT is a geometry factory - harvest plan
74a2694 trees are SpeedTreeRT (mesh+billboard), per-client procedural desync
fc92d70 tree shadows are terrain-only (engine limitation)
501e114 internal resolution - already native 1920x1080
```
