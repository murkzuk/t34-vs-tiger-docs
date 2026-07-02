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
- **Turret-needle animations** (`gun_c_leftup/leftdn/rightup/rightdn`), **commander hatch** (`luk_main_commander`), and **body-recoil animations** — all `MainPlayerUnit`-only (i.e. Tiger-only), likely from `TankPzVIAusfEUnit.script:1311`'s exterior mesh swap from `Cu_veh_PzVI_MAINModel` to `Cu_veh_PzVI_LATEModel` (see the commented-out old `SetupMesh` call at line 1320) losing some bone/channel connections in the interior extension model. Needs 3D tool work, not scripting — left untouched. (The large batch of `Cockpit.script` "Invalid this reference" errors seen alongside these was *not* actually related to this model swap — see later in this same session's entry below for the real cause and fix.)
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

## 2026-07-02 (continued) — Mission 5 AI, hit effects, ballistics, and the real Cockpit.script fix

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

- **Campaign_2\Mission_5's three unit groups got real AI, not just the empty stubs from earlier in this session.** `CC2M5GroupSU85` and `CC2M5GroupStug_40` were sitting completely inert — this file's own pattern shows unit AI behavior starts inactive until a group explicitly turns it on, and neither stub ever did. Added `Init()` to both, activating behavior/radar/aggressive posture (they're static defensive/ambush positions, so no movement orders needed). Also found `CC2M5GroupStug_40`'s two units had no `Task` property in `Content.script` at all — added `CBaseAISAUTask`. `CC2M5GroupRusSoldiers` had a fully-built, unused 6-point NavPoint advance path sitting in `Content.script` since the mission was made, never referenced anywhere — added a `StartFirstAdvance`/`EndFirstAdvance_Attack` pair mirroring the mission's own existing group idiom and wired it into `StartCombat()`. Confirmed via log: SU-85s now fire and get destroyed in sequence, StuGs maneuver and attempt to aim, all 9 Soviet riflemen issue move orders.
- **The metal-hit splash/smoke effect (massive flames, then cubes instead of smoke on track/armor hits) — root cause found and fixed.** `Scripts\Common\EffectsMetal.script`'s hit-splash and hit-smoke classes had been hand-edited a while back chasing spall-effect realism, with every duration/size/count/brightness parameter multiplied 2-5x (old values were still sitting in `// Was X` comments). The smoke effect's particle-count loops fed their own loop counter into the texture-frame index; pushing the count past the texture's actual 16 frames made the engine's missing-material fallback render as solid cubes. Reverted every parameter to its original value.
- **Added a real spall/fragment debris effect, done properly this time.** Built `CCalibre7576_85_88BulletMetalHitDebrisEffect`, modeled on the game's own existing wood-splinter debris pattern (gravity + tumbling rotation), using `MetalDebrisEffectSkin` — an asset the original devs registered but never wired to anything. The loop bound reads the texture's real frame count at runtime instead of a hardcoded number, so this specific class of bug can't recur here. Wired into both the full-caliber and subcaliber (AP round) hit chains — subcaliber previously had no fragment effect at all, despite AP-round spall being the classic real-world case. First tuning pass wasn't visible enough at combat range; bumped particle size/speed/spread/count for a properly visible burst.
- **Every tank machine gun now has its own period-accurate bullet velocity**, instead of one generic 650 m/s shared by every tank regardless of nationality. Added named constants to `Piercing.script` following the file's own established `real_velocity * 0.8` convention (confirmed against the Tiger's own 88mm gun, which already uses this exact pattern): German MG34 (Tiger, Pz IV, Hanomag) at 755 m/s real / 604 in-game, Soviet DT-29 (T-34/76, T-34/85) at 840 m/s real / 672 in-game. The only existing precedent for this pattern in the whole codebase was the M3 halftrack's own machine gun — extended it to the other 5 vehicles' 10 weapon classes (coax + hull/turret gun each).
- **`Cockpit.script` "Invalid this reference" spam — actually root-caused this time**, not left alone like the earlier entry above says. Turns out unrelated to the Tiger's model swap. Real cause: this file has an established `if (!m_CockpitExists) return;` guard (used in 16 other places) specifically to stop cockpit UI methods running on units that never went through real player cockpit setup — i.e. AI-driven tanks, which share this class but never get one built. `SetPlayerSit()` and three `PlayerUnit.script` event handlers (`ChangeCommanderState`, `ShakeTank`, `ReturnToBinocular` — all things that legitimately fire for AI tanks too, like getting shaken by a nearby hit) were missing that guard. Added it, matching the file's own existing idiom. Confirmed via log: thousands of occurrences down to zero.

### Incidental: more pre-existing CP1251 corruption found and fixed

Several more instances of Cyrillic-comment corruption predating this session turned up while editing `EffectsArray.script`, the five tank/halftrack unit scripts touched for the MG velocity work, and `PlayerUnit.script` — all comment-only, zero gameplay impact, all repaired via byte-level Python writes sourced from this repo's own `TvT\` mirror. One of these (`PlayerUnit.script`) was actually caused *by* an edit in this session, not just discovered — a reminder that checking a file is clean before editing it doesn't guarantee it's still clean after, since every save re-serializes the whole file. Worth a post-edit check every time, not just a pre-edit one.

### Why this matters

The Mission_5 group fix and the metal-hit effect fix are both real, previously-invisible gameplay bugs (AI units doing nothing, a broken visual effect masquerading as intentional design). The Cockpit.script fix closes out something flagged as "can't confirm, needs 3D tool work" in the earlier entry above — turned out to be a pure script bug with an existing, established fix pattern already used elsewhere in the same file, once actually chased down instead of assumed to be model-related.

### Contributors

- **Jeff Murkin (murkzuk)** — ran the game after each fix, cleared cache, pasted `execution.log` back for the next round, gave direct feedback on what was and wasn't visually working (the debris effect, MG feel, cockpit view-switching).
- **Claude Code (Anthropic)** — traced root causes rather than symptom-patching where possible (Cockpit.script, metal-hit effect), was explicit about remaining uncertainty rather than guessing, fixed CP1251 corruption encountered along the way.

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
