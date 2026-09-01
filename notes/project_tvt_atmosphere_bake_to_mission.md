# Bake atmosphere preset → mission (Save to mission)

Status: BUILT + VERIFIED in-game (2026-08-30). User confirmed the bake works.

## What it does
Takes the panel's CURRENT slider values (sun, sun colour, ambient, fog) and
writes them permanently into a mission's file, so the look sticks without the
live panel. The full loop is now proven: tune live → bake → reload → it sticks.

## Key finding — which file is authoritative
A mission stores its atmosphere in TWO places:
1. `Missions\<...>\Content.script` — an "Atmosphere" entry in
   `m_MissionObjectList`, whose property map holds the real values. **This is
   what the game reads.** (Header says "DO NOT EDIT" — that's the editor's
   auto-generated file, but hand-editing it IS what the previous tuning session
   did, and it took effect.)
2. `Missions\<...>\Atmosphere.script` — a per-mission class
   (`CC2M1Atmosphere extends CCommonAtmosphere`) with the same values as member
   defaults. `Mission.script` does `SetMissionAtmosphere(new #Atmosphere<CC2M1Atmosphere>())`.
   This file can be STALE (its AmbientLight in C2M1 is 0.250 vs Content.script's
   0.300) — evidence that Content.script's property map is applied on top / wins.

→ Bake writes **Content.script** only. `Atmosphere.script` is left alone (it is
the editor's template; syncing it is a possible later refinement, not required).

## Why the editor's "Save Mission" doesn't capture panel changes
The panel drives the native CAtmosphere directly (via the injected DLL) — it
bypasses the script layer entirely. The editor saves ITS OWN script-level
atmosphere state, which the panel never touched. So "change in panel → save in
editor" = no persistence. Confirmed by the user's test. The fix: the panel writes
the mission file itself.

## Files (all in `Tools\AtmosWysiwyg\`)
- `bake_mission.py` — the bake engine (NEW). Dry-run by default; `--apply` backs
  up `Content.script` to `.bak.<timestamp>` first. Locates the Atmosphere
  property array, replaces/inserts 10 keys, refuses on ambiguity.
- `atmos_server.py` — added `GET /missions` (lists missions under
  `M:\T34vsTiger\Missions`) and `POST /save_mission` (backup + write, guarded to
  the missions tree).
- `atmos_panel.html` — added a "Save to mission" section: mission dropdown +
  button + status line.

## Sun vector conversion (re-confirmed)
`x = cos(az)·cos(el)`, `y = −sin(az)·cos(el)`, `z = −sin(el)`.
Verified against C2M1's existing vector (−0.027, −0.707, −0.707) = az≈92°, el=45°.

## Fields baked (panel → Content.script key)
SunDirection (Vector), SunColor (Color), AmbientLight (Color), FogNear, FogFar,
FogDensity, FogColorXPos/XNeg/YPos/YNeg (all 4 = panel's single fog colour).
NOT touched: FogMode, FogFarMax, ShadowColor, StencilShadowColor, AntiSun*,
SunIntensity, tree settings — the bake is additive-over-these, replace-the-rest.

## Verified
- C2M1 baked with Bagration Dawn; user loaded it in-game and confirmed the look.
- Backup: `Missions\Campaign_2\Mission_1\Content.script.bak.20260830_153958`.
- Sandbox HTTP test: `/save_mission` returns ok/changed=10, writes correctly,
  creates backup; `/missions` returns 34 missions; out-of-tree path → 400.

## To use (after this session)
Restart the panel server (the running one predates these changes), then:
1. Pick a preset (or drag sliders) in the panel.
2. Pick the mission in the "Save to mission" dropdown.
3. Click "Save to mission" — it backs up + writes + shows the backup name.
4. Reload the mission in-game (fresh) to see it.
