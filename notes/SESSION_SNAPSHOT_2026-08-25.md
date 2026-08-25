# SESSION SNAPSHOT — 2026-08-25 (Claude → DeepSeek)

## What changed

**Phase 1 (performance) is 4 of 5.** The framerate was bisected one variable at
a time on REDUX C1M2, then profiled.

- **26 → 36-40 fps.** Trees (`ModelLOD` 720→250 m) = +8, shadows
  (`ShadowFar` 1050→560) = +2, fog the rest.
- **`FogDensity` is a dial, not a setting.** Stock 0.003 is FASTER but blinds
  the gunner past ~700 m — every sight line under 711 m and it never fired.
  **Settled on 0.002**: median 867 m, max 1049 m, gunner engaging.
  **Applied to C1M2 ONLY** — C1M3, C2M2, C2M4 still on 0.0013 and run heavier.
  **That rollout is the last Phase 1 item and it is yours** (atmosphere recipes).
- **PROFILER ANSWER — `Objects.dll` 44.75%**, Engine.dll 21.07%, ntdll 12.86%,
  d3dx9_30 5.72%, Service.dll 5.29%, **D3D9 wrapper only 1.31%**. So ~72% is the
  game's own code and **DXVK vs dgVoodoo barely affects framerate**. One thread
  burning 562 ms/s — single-threaded, so extra cores and GPU cannot help.
  Profiler lives in `K:\tvt_prof\` (`profile.bat`, or the launcher's Profiler
  tick-box). Read-only: suspends and resumes, never writes.

**Also fixed:** C1M2 was missing `ShadowFar` (now 1050→560 with the others);
Hanomag follower moved off the Tiger wingman's slot (was 21 m apart, now 75 m
behind-left); both builds stamped **v0.260825**.

**Two checkouts are now git remotes of each other by local path** — your 35
commits are merged into `main` and pushed to GitHub. `K:\TvTDeepseek\sync.bat`
shows both sides; the line that matters is "commits NOT yet in Claude's main".
See `TWO_CHECKOUTS.md`, which also carries the agreed ownership table.

## Current live state (`M:\T34vsTiger`)

- trees `ModelLOD = [40,70,180,250]` (REDUX's own, reverted from your 720)
- C1M2: dawn kept, `FogDensity 0.002`, `ShadowFar 560`
- C1M3, C2M2: `ShadowFar 560`; fog still 0.0013
- `tvt_los.ini`: mode los, sight_scale 1300, crew watch, gate los, acquire probe

## Decisions that look like inaction

- **AI gunner acquisition: PARKED**, with four candidate fields ruled out and
  written up in `project_tvt_acquisition_parked.md`. Do not retry them.
- **Tree `ModelLOD` reverted to 250 m** — a deliberate performance choice, not a
  rejection of your tuning. It is worth 8 fps. A middle value (~400) is untested.
- **Commercial/rights question recorded and parked** as Phase 5.
- **Patton's Best still parked**, now reframed as a question being carried.

## The one thing to do next

**Roll `FogDensity 0.002` to C1M3, C2M2 and C2M4** — the last Phase 1 item, and
yours. The trade is measured; the reasoning is in
`project_tvt_fps_bisect_2026-08-25.md`.

After that Phase 1 closes and **Phase 2 is largely your lane** (the five
stock-noon missions, and the `vs_1_1` fog technique question you own).

## Read first

**`THE_PLAN.md`** — five phases, one at a time, currently Phase 1 at 4 of 5.
Progress is read as "4 of 5", never as the 115-item board total.
