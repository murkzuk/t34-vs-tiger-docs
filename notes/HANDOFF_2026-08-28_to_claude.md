# Handoff to Claude — DeepSeek session 2026-08-28

DeepSeek can't push (sandbox has no network), so this is yours to pull + push and
to keep an eye on. Everything below is already committed locally and backed up.

## 1. Git — please pull + push

- Checkout: `K:\TvTDeepseek\t34-vs-tiger-docs` (your remote is wired as `claude`).
- Branch: `deepseek/atmosphere-dawn-fog` (clean working tree, last commit `458c47e`).
- This session's commits are the top ~15 (notes, Discord log, forum post). Pull the
  branch into your `main` and push to GitHub when convenient.

## 2. Game files changed (M:\ — NOT in git; documented in the notes)

These are live in the installs and backed up in `K:\TvTDeepseek\rollback\`:

- **C2M1 ZW** — golden dawn (sun 10° ENE) applied to `Content.script` +
  `Atmosphere.script`; briefing dateline added to `MissionC2M1.rsr` (UTF-16LE).
- **C1M1 ZW** — 06:15 clear summer morning (sun 11° ENE) applied to `Content.script`
  + `Atmosphere.script`.
- **Version:** ZW → `v0.260828b`, REDUX → `v0.260828a`.
- `EffectsSkin.script` — dust "NORMAL→ADDITIVE" was tried and **reverted** (net zero).

## 3. Open handoffs — your territory

1. **Dust see-through wheat** — `project_tvt_dust_see_through.md`. Diagnosed via a
   D3D9 probe (wheat writes depth while alpha-blended; dust doesn't). Fix = sort the
   transparent pass back-to-front. Probe artifacts: `K:\TvTDeepseek\dustfix\`.
2. **LOS hook "Behavior.dll never loaded"** — `project_tvt_los_hook_behavior_dll_timeout.md`.
   60-second window at process start, but Behavior.dll loads at mission start. Fix =
   `LdrRegisterDllNotification` (or drop the 60s cap).

## 4. Note for REDUX

REDUX C2M1 is a **different mission** from ZW C2M1 — "Securing Kurtenki REDUX by
Murkz" (July 1943, a rough mission the user wants **left alone**). Do NOT mirror the
ZW 1944 dawn onto it.

## 5. Launcher

`K:\tvt_los\TvT_Launcher.ps1` gained a "Dust fix" toggle. It and "Fog on distant
tanks" are **mutually exclusive** because both patch `Direct3DCreate9`. If both are
ever wanted at once, merge them into one DLL. Backup:
`K:\TvTDeepseek\rollback\TvT_Launcher_2026-08-28_pre_dusttoggle.ps1`.
