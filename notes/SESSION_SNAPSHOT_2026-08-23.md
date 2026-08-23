# SESSION SNAPSHOT — 2026-08-23

One-page "where we are" for a cold start. Written end-of-session; will go stale as work
continues — update it, don't trust it blindly.

## The session in one paragraph

Two play-session logs were swept and 6 issues root-caused (recursion, `ActivateMove`
typo, ghost menu entry, ZW gun animators, Stuka lines, atmosphere silencer). The REDUX
fixes were applied then REVERTED (a trailing-comma parse error spooked it — now a
permanent warning note). Then the atmosphere/lighting system was learned from scratch
using C2M2 as the test bed: fixed a 20-year-old non-unit-sun glare bug (sun now visible
for the first time), built a proper dawn + early-morning mist, and mapped the whole
lighting stack. All of it is committed to a git branch for review.

## Live game state (M:\T34vsTiger)

**Applied + tested + user-approved:**
- `Missions\Campaign_2\Mission_2\Content.script` — dawn recipe + mist (orange sun, cool
  shade, muted anti-sun, `FogFar 450`, grey-blue fog).
- `Scripts\Common\EffectsBase.script` — ground track marks darkened `(0.25,0.21,0.21)`;
  user said "barely changed" — parked, revisit later.

**NOT applied (parked / reverted):**
- The 6 log-sweep REDUX fixes (recursion guard, `ActivateMove` ×2, menu entry) — cards
  ready, reverted pending user go-ahead.
- ZW fixes (FH18 `TurnSpeedAnim`, Stuka `ForEachUnitTask`, `SetIsCameraAdjustEnabled`
  stub) — separate build, not started.

## The atmosphere model (the key knowledge)

- **3-layer model:** Content.script block (data, wins) → Atmosphere.script class fields
  (fallback) → BaseAtmosphere defaults.
- **Dawn recipe:** warm sun + warm fog + **cool ambient** + **muted anti-sun**.
- **`FogFar` drives terrain haze** (proven); `FogDensity` does nothing (Exp broken).
- **Non-unit sun = real glare/invisible-sun bug** (not cosmetic).
- **Fog-on-objects** (tanks stay sharp in mist) = renderer-pass issue → likely a D3D9 hook.
- Full details: `project_tvt_atmosphere_understanding.md`.

## The branch

`deepseek/atmosphere-dawn-fog` — 4 commits, in `K:\TvTDeepseek\t34-vs-tiger-docs`.
Contains the game edits, findings, notes, and fix cards. Review with
`git diff main...deepseek/atmosphere-dawn-fog`. Not pushed (no network in sandbox).

## What's next (in order)

1. **Snow mission** (`CWinterMission1`, ZW install) = next atmosphere test — winter
   overcast recipe (cold light, flat contrast, white ground).
2. **Fog-on-objects hook** — make tanks sit *in* the mist (the big realism win).
3. **Track marks** — stronger darkening (current change too subtle).
4. **Re-apply the 6 log-sweep fixes** — one at a time, when the user is ready.
5. **Patton's Best campaign** — PARKED; see `project_tvt_pb_campaign_reference.md`.

## Where everything lives

| What | Path |
|---|---|
| Atmosphere reference | `K:\TvTDeepseek\notes\project_tvt_atmosphere_understanding.md` |
| Atmosphere trail | `K:\TvTDeepseek\notes\project_tvt_atmosphere_lighting_plan.md` |
| PB/campaign reference | `K:\TvTDeepseek\notes\project_tvt_pb_campaign_reference.md` |
| Tigers finding | `K:\TvTDeepseek\notes\project_tvt_c1m2_tigers_passive_by_design.md` |
| Trailing-comma warning | `K:\TvTDeepseek\notes\feedback_trailing_comma_incident_warning.md` |
| Repo (branch) | `K:\TvTDeepseek\t34-vs-tiger-docs` |
| Rollback backups | `K:\TvTDeepseek\rollback\` |
| Patch cards | `K:\TvTDeepseek\patches\REDUX_2026-08-22\` |
| Claude's memory | `.claude\projects\M--T34vsTiger---REDUX0-001-Scripts\memory\` |

## Rules that never change

- `.script` files are **CP1251** — never UTF-8 round-trip; edit byte-level; check for
  `\xef\xbf\xbd` before/after.
- **Delete `Cache\Scripts.cache`** after any script edit.
- **Never place files inside a game folder** (TvT reads every file regardless of
  extension; zip a backup if it must live there).
- Backups live in the rollback kit, **outside** game folders.
- One change at a time; the **user is the last gate** — no write without go-ahead.
- Live install: `M:\T34vsTiger`. ZW: `M:\T34vsTiger_ZW2015`. WoV reference: `G:\WoV`.
- The user is a non-coder, dyslexic — plain words, scannable, no quizzes.
