# Changelog — t34-vs-tiger-docs

All notable changes to this repository. The most recent entry is first.

This file is human-written, plain prose. For technical details, see [PROJECT_MAP.md](PROJECT_MAP.md) and [llms.txt](llms.txt).

---

## 2026-07-02 — execution.log error-hunt session (Claude Code)

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Worked through `execution.log` warnings/errors iteratively: apply a fix, clear `Cache\Scripts.cache`, relaunch, check the new log, repeat. Confirmed fixed (verified via log re-check after each change):

- **`Scripts\Common\CockpitControls.script`** — the `TrackLeft`/`TrackRight`/`HullEngine` rows in both `CCommonStatusScreen.Devices` (Soviet) and `CTigerCommonStatusScreen.Devices` (Tiger) were missing the `0` int placeholder before `new Color(...)`, shifting every value after it one slot left. Was producing `Can not assign value (Color(...)) to typed variable (int)` / `[N] entry is invalid` spam on every cockpit load.
- **`Missions\Campaign_1\Mission_4\MissionTasks.script`** and **`Mission_5\MissionTasks.script`** — 7 task classes declared `extends CC1M3, ...` where `CC1M3` doesn't exist; should be `CC1M3Broken`, a generic AI "broken path" pathing helper defined once in `Mission_3\MissionTasks.script`. Fixed all 7. This was the source of `[ScriptHost] class CC1M3 was not found`, which is unrelated to the actual `CC1M3Mission` campaign class (that one is fine, lives in `Missions\Campaign_1\Mission_3\Mission.script`).
- **`Scripts\Units\BtrM3A1HalftruckUnit.script`** and **`BtrHanomag251AusfCUnit.script`** — both halftracks' driving-wheel roll animation (`LineSpeedAnim`) was disabled via `= "";//"wheels_left";`-style comments, leaving an empty string. Restored on both sides, both vehicles. Wheels should now visibly roll while driving, not just steer.
- **`Scripts\Common\LensFlare.script`** — added `SunAlpha` to the shared base `CLensFlare` class. It had only ever been patched into `Missions\Campaign_1\Mission_3\C1M3LensFlare.script` (a `//jm` fix), so every other mission's lens flare (6 other `CxxxLensFlare.script` files) still hit `Variable SunAlpha not found in script`.
- **`Missions\Campaign_2\Mission_4\Atmosphere.script`**, **`Missions\MISSIONS\CF2Mission\Atmosphere.script`**, **`Missions\MISSIONS\DM2Mission\Atmosphere.script`** — `SunDirection = new Vector(0.99, -0.08, -0.35)` wasn't unit length; engine was silently renormalizing it every load and logging `[Atmosphere] Incorrect sun direction`. Replaced with the exact engine-computed value (`0.933706, -0.075451, -0.35`), taken directly from the log's own correction message — same lighting, no more warning.
- **`Scripts\Units\SAUSU85Unit.script`** — `CloudEffectId = "HeavyGunWoMuzzleCloudEffect"` was a typo (extra "Wo"); the real registered effect is `"HeavyGunMuzzleCloudEffect"` (confirmed working on `GunPak40Unit.script` and `SAUSTUG40Unit.script`). SU-85 was firing its main gun with no muzzle smoke.
- **`Missions\Campaign_2\Mission_5\MissionTasks.script`** — added `CC2M5GroupSU85`, `CC2M5GroupStug_40`, and `CC2M5GroupRusSoldiers` group classes. None existed anywhere despite `Content.script` referencing them by name; the engine logged `[UnitGroup] script host "..." was not created` for all three and the member units loaded standalone with no group AI. Confirmed via log: post-fix, these groups now issue real orders (`SetFormation`, `Maneuver destination`, units taking fire and dying), where before they likely just sat inert. Added as minimal `extends CBaseUnitGroup {}` stubs, matching the same pattern already used by `CC2M5Group1T_IV`/`CC2M5Group2T_IV` in the same mission — they don't have a full custom AI Task class the way `Mission_3`'s scripted groups do, so their combat behavior may be more basic than originally intended. Writing proper Task classes for these three is separate follow-up work, not a bug fix.

### Investigated, deliberately left alone

- **4 WIP cockpit gauges** (`tacho`/`speed`/`oil_pressure`/`water_temperature`) in `TankPzVIAusfEUnit.script` — these are murkzuk's own `//jm`-tagged additions; the Tiger's current 3D model doesn't have those animation channels yet. Commented out (same pattern already used for `OilTemperatureAnimator`) so the log stays clean until the model has them. Needs 3D modeling work, not scripting.
- **Turret-needle animations** (`gun_c_leftup/leftdn/rightup/rightdn`), **commander hatch** (`luk_main_commander`), **body-recoil animations**, and a large batch of `[ScriptManager] Cockpit.script ... Invalid this reference` errors during cockpit view-switching — all `MainPlayerUnit`-only (i.e. Tiger-only) and all likely the same root cause: `TankPzVIAusfEUnit.script:1311` swapped the Tiger's exterior mesh from `Cu_veh_PzVI_MAINModel` to `Cu_veh_PzVI_LATEModel` (see the commented-out old `SetupMesh` call at line 1320), presumably as part of earlier LOD-improvement work, and the interior extension model (`Cu_veh_PzVI_MAIN_InsideModel`) appears to have lost some bone/channel connections in that swap. Not confirmed with certainty for the `Cockpit.script` "Invalid this reference" errors specifically (couldn't fully trace the runtime call chain from static reading alone), but consistent with everything else found. Needs 3D tool work, not scripting — left untouched to avoid guessing at cockpit-switching logic shared by every tank in the game.
- **`Common\Armour.script` — `[UnitDamageHandler2] Incorrect data value of substance damage modifier: 0.2, 0.15, 0.5`.** All 28 unique armor-point entries in the table use the identical third value (`0.5`), with zero exceptions. This is a deliberate, uniform, original G5 constant, not a typo — left untouched rather than guess at undocumented engine validation ranges and risk changing damage balance for every vehicle.
- **`[Router] Could not create script host "CBaseLightNavalBehavior"/"CBaseHeavyNavalBehavior"/"CBaseHoverBehavior"`** — confirmed dead code carried over from the studio's earlier title, *Whirlwind over Vietnam* (a helicopter/naval combat sim on the same G5 engine). Not applicable to a tank sim; left alone.
- **`[MenuGroup] Object with identifier "EscTimer" not found`** — fires exactly once, right at shutdown, after `CEscapeMenu` has already cleanly registered/unregistered it itself. Reads as the engine's generic menu-cleanup sweep hitting something already torn down; harmless.
- **`Common\BaseTankAutoThingUI.script` false→float type error near AutoCommander init** (`Can not assign value (false) to typed variable (float)` / `[1] entry is invalid`, fires 3x every mission start) — tested the theory that empty `AutoGunnerMessages`/`AutoCommanderMessages` arrays were the cause by filling them with placeholder entries; **no change in the log**, so that theory is ruled out. Checked the compiled DLLs directly (`UI.dll` contains the `"%s[%d] entry is invalid"` format string tied to `CCommonStatusScreen`/`CCockpitControl`) but couldn't find a remaining script-side candidate after exhausting `CockpitControls.script`, `BaseTankAutoThingUI.script`, `CockpitSkin.script`, `AutoShooter.script`, `AutoCommander.script`, and `TankPzVIAusfEUnit.script`. Best guess: this one lives in compiled `Controls.dll`/`UI.dll`, not editable `.script` text. Left alone.

### Why this matters

Several of these were pure log noise (SunAlpha, sun-direction), but at least two were real gameplay bugs hiding behind log spam: the SU-85's missing muzzle smoke, and — more significantly — three entire unit groups in Campaign 2 Mission 5 (SU-85s, StuGs, Soviet infantry) that were failing to load as groups at all, meaning they likely weren't receiving coordinated AI orders during that mission. Also confirmed (again) that `Scripts\` is not self-contained — `Missions\`, `Resources\`, and `Locale\` all hold content that a Scripts-only search will miss; see `PROJECT_MAP.md`/`llms.txt` if that's not already called out there.

### Contributors

- **Jeff Murkin (murkzuk)** — ran the game after each fix, cleared cache, pasted `execution.log` back for the next round, made all judgment calls on what to leave alone.
- **Claude Code (Anthropic)** — traced each log line to its source file, applied fixes, verified via log diffs before/after, ruled out failed theories rather than leaving them unstated.

---

## 2026-06-03 — Repo cleanup and documentation baseline

**By:** murkzuk (with Mavis / MiniMax Agent assistance)

### What changed

- **Deleted `TvT/T34vsTiger*.rar` archives** (3 files). These were full game builds, unsafe to keep in a documentation repo. Anyone with the working game build already has the files; nobody should be extracting RARs into a game install from a docs repo.
- **Removed 27 Maya export test files from the repo root** (`Sky_*.script`, `Test_House*.script`, `MyFirstModel.script`, `Landscape_test.script`, `sphere_test.script`, `test.script` and matching `.ms2` files). These were noise at the root and had no relation to the actual game. All copies had been archived in `TvT/archive/` first.
- **Moved 16 misplaced real unit files** from repo root and `TvT/archive/` to `TvT/Units/` (where the Tiger and T-34 unit scripts already lived). Units affected: FW 190, IL-2, IL-2M, Nebelwerfer, Pak 40, ZIS-3, Hanomag 251C, M3A1 Halftrack. Both `.script` and `.ms2` files moved together.
- **Removed empty `mmp7.1/` folder.** Was a chaos folder with `Scripts` (1 byte) and `temp.txt` (28 bytes). No content of value.
- **Added `PROJECT_MAP.md`** — the new top-level document explaining repo layout, who's who, what's safe to modify, and what's archival. Linked from `llms.txt`.
- **Updated `llms.txt` to v2** — new content with verification timeline, current repo state, exclusion zones (don't touch `TvTZW/`, `ZW Mission scripts/`, or `concatenate scripts/`), and the 5-tier confidence hierarchy. Dated 2026-06-03.

### Why this matters

Before this session, the repo had ~30 noise files at the root and several duplicated folders. It looked like a junk drawer to anyone landing on it for the first time. After this session:

- The root contains only folders + 2 files (`README.md`, `CHANGELOD.md`, `PROJECT_MAP.md`, `llms.txt`).
- The `TvT/Units/` folder has all the real unit scripts and their meshes.
- Future contributors and AI assistants have clear docs to read on entry.

### Contributors

- **Jeff Murkin (murkzuk)** — commits, decisions, verification
- **Mavis (MiniMax Agent)** — drafted `PROJECT_MAP.md`, `llms.txt` v2, `CHANGELOG.md`, this changelog entry. Did the file-level analysis of what was in the repo and what was safe to move/delete.

---

## Format guide for future entries

When you add a new entry, put it at the top with today's date. Use sections: **What changed**, **Why this matters**, **Contributors**. Keep prose short. Link out to docs when relevant.

The old `CHANGELOD.md` (LOD-specific) stays as a separate file. This `CHANGELOG.md` is for the project as a whole.

---

*Last updated: 2026-06-03*
