# SESSION SNAPSHOT — 2026-08-24 (full handoff for Claude)

Cold-start handoff covering the whole recent arc **2026-08-21 → 08-24**.
**Supersedes `SESSION_SNAPSHOT_2026-08-23.md`** (folded in here). Everything
below names a file you can check.

## The goal (unchanged across all three sessions)

Make each mission's lighting / atmosphere / time-of-day **(A) historically
correct** and **(B) as good as the 2001 engine allows** — plus, this session,
tree rendering quality. The user is a non-coder, dyslexic; plain scannable
answers, no quizzes.

## Who / where

- **This agent (DeepSeek)** works in `K:\TvTDeepseek\t34-vs-tiger-docs`, branch
  **`deepseek/atmosphere-dawn-fog`**. All commits below live there.
- **Claude's checkout** is `C:\Users\Jeff\t34-vs-tiger-docs`, main @ `62e077f`
  (+ untracked `FINDINGS_2026-08-21_log_sweep.md`). **Not pushed — no network.**
  The branches have diverged; DeepSeek's is NOT merged to main.
- **Notes mirrored** in two places — keep both in sync:
  - `K:\TvTDeepseek\t34-vs-tiger-docs\notes\` (in-repo)
  - `K:\TvTDeepseek\notes\` (master copy)
- **Live install:** `M:\T34vsTiger` (REDUX). Reference `G:\WoV`. ZW
  `M:\T34vsTiger_ZW2015`.
- **Rollback kit:** `K:\TvTDeepseek\rollback\` (every game edit backed up,
  timestamped). Never put backups in the game folder.
- **Probes:** `K:\TvTDeepseek\fog_probe\` (D3D9 fog) and
  `K:\TvTDeepseek\tree_probe\` (SpeedTreeRT). Injector
  `K:\tvt_probe\tvt_inject.exe`.

## Handing back to DeepSeek (Claude: read this at the END of your session)

When you finish, write a dated snapshot so DeepSeek can pick up cold. The two
checkouts are **separate**, so it only works if the file lands where DeepSeek
actually looks:

- **Write `SESSION_SNAPSHOT_YYYY-MM-DD.md` into `K:\TvTDeepseek\notes\`** — the
  master copy, NOT just your `C:\Users\Jeff\...` checkout (a file only in your
  checkout is invisible to DeepSeek). Mirror it into
  `K:\TvTDeepseek\t34-vs-tiger-docs\notes\` too if you're committing.
- Use the same three heads as above: **what changed, current live state, what's
  next.** And add the two things files can't show: (1) decisions that look like
  inaction in git ("parked X", "user approved Y", "abandoned Z"), and (2) the
  one thing to do next.

If you can't write one, DeepSeek will reconstruct from `git log` + the `notes\`
folder + `K:\TvTDeepseek\rollback\` — but those two sentences are the part it
can't infer, so they're the highest-value thing to leave.

## Timeline — what happened when

### 08-21/22 — log sweep + first atmosphere win
- Swept two play-session logs; root-caused **6 issues** (recursion,
  `ActivateMove` typo, ghost menu entry, ZW gun animators, Stuka lines,
  atmosphere silencer). REDUX fixes applied then **REVERTED** after a
  trailing-comma parse error — that's now a permanent warning note
  (`feedback_trailing_comma_incident_warning.md`). Fix cards ready in
  `K:\TvTDeepseek\patches\`.
- **C2M2 dawn** applied + play-tested (commit `9cb770d`): the first proper dawn.
- Notes: `project_tvt_big_map_2d_campaign_layer.md`,
  `project_tvt_c1m2_tigers_passive_by_design.md`,
  `project_tvt_pb_campaign_reference.md`.

### 08-23 — atmosphere model + fog probe + LOD + Pz IV G
- **Learned the atmosphere system from scratch.** Key reusable knowledge:
  - **3 layers:** mission `Content.script` Atmosphere block (wins) →
    `Atmosphere.script` class fields → `BaseAtmosphere` defaults.
  - **Compass:** +X=South, −X=North, +Y=East, −Y=West, +Z=up.
    `SunDirection` = *light* direction (the sun is opposite its horizontal
    component). East dawn = light heading West (−Y).
  - **Dawn recipe (validated):** SunDirection `(0.815587, -0.551964, -0.173648)`,
    SunColor `(1.0, 0.749020, 0.294118)`, AmbientLight `(0.156863, 0.203922,
    0.243137)`, FogMode `Exp`, FogDensity `0.0013`, FogNear `10`, FogFar `450`.
  - **Fixed a 20-year-old bug:** a non-unit sun vector = real glare / white-out
    (the devs shipped wrong sun coords; the sun was invisible). Now visible.
  - **Fog correction:** in `Exp` mode the engine drives fog off `FogDensity`
    (it IGNORES `FogNear`/`FogFar`). Fog is shader-computed in compiled `.fxo`.
  - Full detail: `project_tvt_atmosphere_understanding.md`,
    `project_tvt_atmosphere_lighting_plan.md`.
- **Fog-on-objects** (tanks stay sharp in mist) root-caused as a renderer-pass
  issue → built **`fog_probe.dll`** (read-only D3D9 hook) to confirm. It proved
  **fog is skipped for ~half of unit draws** (distant-LOD `vs_1_1` shaders lack
  `FogDensity`). `vs_1_1` is a GPU shader-model split (1.1 vs 2.0), NOT an LOD
  level. → `project_tvt_fog_hook_scoping.md`, probe in `K:\TvTDeepseek\fog_probe\`.
- **LOD system mapped:** geometry is BAKED into `.ms2`; `SetLods([...])` arrays
  are DESCENDING far→near; **LOD 0 = coarsest**, so `[0]` = always-coarsest.
  **Pz II** `[0]` → `[300,100,50,5]` (applied, untested). Full tank table in
  `project_tvt_lod_distances.md`.
- **Pz IV G:** the AI unit uses a reduced 11.9 MB mesh vs the full 17.4 MB one.
  Swapping the mesh broke damage (double-render) → reverted. **Correct fix =
  swap the whole UNIT** in mission Content.script. `Panther_M1` + `C1M1`
  swapped; **13 more backed up but not swapped.** →
  `project_tvt_pz4g_full_unit_swap.md`.
- Winter/overcast rollout (3 missions) + Leningrad overcast + Zitadelle fog-test
  bed recorded (commits `9d87bc9`, `bf9d1c9`, `c5d20a6`).

### 08-24 — dawn/sunset rollout + resolution + trees
- **C1M2 dawn** applied + confirmed (commit `5b9d31c`). **C1M3 sunset** applied
  + confirmed "chef's kiss": SunDirection `(0.815587, 0.551964, -0.173648)`,
  SunColor warmed to `(1.0, 0.749020, 0.294118)`, FogMode `Exp`, FogDensity
  `0.0013`, FogNear `10`, FogFar `450`. → `project_tvt_dawn_rollout.md`.
- **Resolution:** game already renders native **1920×1080** (registry
  `HKCU\Software\G5 Software\T34`). No bump available. →
  `project_tvt_resolution_finding.md`.
- **Trees = SpeedTreeRT v1** (`SpeedTreeRT.dll` + `STTree.dll` + `.spt`).
  Terrain-only shadows; "mesh + billboard" hybrid; per-client procedural layout
  (the multiplayer desync). → `project_tvt_tree_shadow_limitation.md`,
  `project_tvt_speedtree_harvest.md`.
- **Tree LOD tuning:** settled `ModelLOD` = `[160, 280, 480, 720]` (dev
  original). `TreeSize` couples size↔LOD, so height edits were reverted.
  → `project_tvt_tree_lod_tuning.md`.
- **SetTreeSize height-only stretch:** Phase 0 proved the engine passes
  `SetTreeSize(width=TreeSize, height=0.0)`. Phase 1 `tree_stretch.dll` built
  (**not yet user-tested**). → `project_tvt_settreesize_hook_spec.md`.

## Current live game state (`M:\T34vsTiger`) — the deltas from stock

- `Missions\Campaign_2\Mission_2\Content.script` — C2M2 dawn (23rd, approved).
- `Missions\Campaign_1\Mission_2\Content.script` — C1M2 dawn (24th, approved).
- `Missions\Campaign_1\Mission_3\Content.script` — C1M3 sunset (24th, approved).
- `Scripts\Common\BaseSTTree.script` — **`ModelLOD = [160, 280, 480, 720]`**
  (the ONE tree change still live); TreeSize stock.
- Pz II `[300,100,50,5]` — applied, untested.
- Pz IV G full unit — `Panther_M1` + `C1M1` swapped.
- `Scripts\Common\EffectsBase.script` — track marks darkened; "barely changed",
  parked.
- Winter/overcast rollout — 3 missions recorded (see atmosphere plan note).

## Pending / next (in rough order)

1. **Test `tree_stretch.dll`** — `K:\tvt_probe\tvt_inject.exe
   "M:\T34vsTiger\TvsT_fullLOD_HARD_4GB.exe" "K:\TvTDeepseek\tree_probe\tree_stretch.dll"`.
   Tune `K` (`#define HEIGHT_STRETCH` in `tree_stretch.cpp`), rebuild with
   `build_stretch.bat`. Log `tree_stretch.log`.
2. **C2M4 sunset** — the other 19:30 mission.
3. **Tree shadows on tanks** — "harvest" path scoped, not started.
4. **Fog-on-objects hook** — actual fix (probe only diagnosed it).
5. **Pz IV G rollout** — 13 missions backed up, not swapped.
6. **Pz III** `[0]` fix; **Pz II** in-game test.
7. **5 "stock noon" missions** polish (C1M1, C1M4, C2M1, C2M3, C2M6).
8. **Re-apply the 6 log-sweep fixes** (cards ready); **track marks** stronger;
   **snow mission** (CWinterMission1).

## Where everything lives (quick map)

| What | Path |
|---|---|
| Atmosphere reference | `notes/project_tvt_atmosphere_understanding.md` |
| Lighting plan | `notes/project_tvt_atmosphere_lighting_plan.md` |
| Fog hook scoping | `notes/project_tvt_fog_hook_scoping.md` |
| LOD distances | `notes/project_tvt_lod_distances.md` |
| Pz IV G swap | `notes/project_tvt_pz4g_full_unit_swap.md` |
| Dawn rollout | `notes/project_tvt_dawn_rollout.md` |
| Tree LOD tuning | `notes/project_tvt_tree_lod_tuning.md` |
| SetTreeSize spec | `notes/project_tvt_settreesize_hook_spec.md` |
| Fog probe | `K:\TvTDeepseek\fog_probe\` |
| Tree probes | `K:\TvTDeepseek\tree_probe\` |
| Rollback | `K:\TvTDeepseek\rollback\` |
| Patch cards | `K:\TvTDeepseek\patches\` |

## Rules that never change

- `.script` = **CP1251**, byte-level edits only; verify EF BF BD count = 0
  before/after. UTF-8 edit tool is safe ONLY on pure-ASCII files.
- **Delete `Cache\Scripts.cache`** after any script edit (cold rebuild ~2 min).
- **Backups** in `K:\TvTDeepseek\rollback\`, never inside a game folder.
- **Per-AI separation** — each AI works in its own checkout; **the user is the
  last gate** (no game-file write without their go-ahead).
- The game is **not run by this agent** — all in-game verification is the user's.
- Injection allow-list sits **beside the DLL** (`tvt_los_allow.txt`).

## Recent commits (DeepSeek branch, newest first)

```
d82a8f1 session snapshot 2026-08-24 (handoff)
d85a1a7 SetTreeSize Phase 0 result - engine passes h=0
1555d38 spec SetTreeSize hook
5607dbf tree LOD tuning
cac8da8 SpeedTreeRT harvest plan
74a2694 trees are SpeedTreeRT
fc92d70 tree shadows terrain-only
501e114 resolution native
5b9d31c dawn rollout C1M2
55d5ddb Pz IV G swap + dawn research
c4b4746 retract vs_1_1 (GPU shader split)
84aedc9 LOD distances [0] bug
2bef008 fog probe result
f9796b0 fog probe v3 (loader notification)
…(earlier: fog scoping, compass, winter rollout, C2M2 dawn, log sweep)
```
