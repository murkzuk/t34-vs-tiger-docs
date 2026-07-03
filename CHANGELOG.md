# Changelog — t34-vs-tiger-docs

All notable changes to this repository. The most recent entry is first.

This file is human-written, plain prose. For technical details, see [PROJECT_MAP.md](PROJECT_MAP.md) and [llms.txt](llms.txt).

---

## 2026-07-03 — Issue tracker audit, fix German distance-callout voice lines

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Audited all 12 open GitHub issues against the current live game state. Four turned out to already be fixed (the "Distance" sound-id bug, the Cockpit.script "Invalid this reference" spam, the PzVI_E gun-load sound naming mismatch) and one had a stale "Confirmed Fix" label never closed. GitHub issue #11 diagnosed a narrower bug than what was actually there: it flagged the German 100m distance callout playing the 200m wav file, but checking `Resources/` showed neither `g_100.wav` nor `g_200.wav` exist at all - every one of the 16 entries in `Dialogs.script`'s German distance table pointed at a nonexistent filename format. The real files are `GDistance100.wav` through `GDistance1600.wav`, original G5 2008 assets. Fixed all 16 entries, not just the one pair the issue caught.

### Why

Direct follow-up to setting up branch protection and reviewing the issue tracker's overall health.

---

## 2026-07-02 (final) — Steppe mission scoping pass

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Pure investigation/scoping, nothing built. User proposed a large open-steppe mission to sidestep the unfixable tree-LOS AI gap. Investigated the separate ZW mod install's 4 "Kursk" custom missions (36000x36000m and 18000x18000m, vs REDUX's typical 9000x9000) and found the technique behind them: stretch REDUX's own standard-resolution terrain images (2049 heightmap etc.) over a much bigger `MatrixWidth`/`MatrixHeight`, confirmed directly from commented-out code in ZW's `WorldMatricies.script` files. No new terrain content or ZW assets needed - REDUX's own `Mission1` already uses the same standard resolution. Also confirmed tree density is controlled by `TerrainZone` bitmap painting via `RegisterForestRegion`, not individually placed objects. Checked REDUX's roster against the real Kursk order of battle (T-34/85 and SU-85 are anachronistic for July 1943) and sampled every REDUX mission's heightmap for flatness (`Campaign_2\Mission_6` is the flattest). Full write-up in `Documentation/Steppe_Map_Scoping_2026-07-02.md`, cross-linked from `TODO.md`.

### Why

Direct follow-up to the user's mission-creation question, explicitly asked to be scoped before any building starts.

---

## 2026-07-02 (very latest) — Remove MG catch-all mask tier, stop MGs engaging tanks

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

The two hit-triggered bugs below were confirmed fixed (both gone from the log), but FPS was still poor and the user spotted the actual cause from gameplay: MGs were now firing at tanks, wasting ammo and CPU on rounds that can't hurt armor. Traced to the catch-all `[[],[]]` tier added in the earlier MG mask fix - fine for a pillbox with no other weapon, but pointless and costly for a tank that already has a main gun for armor. Removed the catch-all tier from all 10 mask blocks across the same 6 unit files, keeping the HUMAN/VEHICLE/BTR tiers intact. Not yet re-tested.

### Why

Direct user observation during FPS re-testing - MGs shooting at tanks rather than the soft targets the fix was meant to enable.

---

## 2026-07-02 (newest) — Fix two hit-triggered bugs exposed by the MG mask fix

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Testing the MG mask fix below showed a real FPS dip. Log check found no errors from the mask fix itself, but two unrelated pre-existing bugs firing much more often now that MG fire actually lands on tanks: `MissionTasks.script` (Campaign 2 Mission 5) called a nonexistent function `ActivateGroupRadar` on every hit-received event (151 failed calls this session) - fixed as a typo for `ActivateRadar`, which the same file already calls correctly elsewhere, in all 3 spots. `PlayerUnit.script:1519` divided by zero whenever an already-destroyed component took another hit (138+ times this session) - added a zero-guard; the computed value turned out to be dead, write-only state anyway. Neither bug was caused by the mask fix - it just made both fire far more often by making MGs actually hit things.

### Why

Direct follow-up to a user-reported FPS regression after testing the coax/hull MG fix in-game.

---

## 2026-07-02 (latest) — Coax/hull MG target mask fix

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User reported the Tiger's hull MG never seems to get used by the AI. Investigation found it wasn't Tiger-specific - every tank and halftrack in the game (Tiger, both T-34s, Pz IV, both halftracks) has its coax and hull machine guns masked to only ever engage `HUMAN`-classified targets (`GunSpecificFireMask = [["HUMAN"],[]]`), with no `VEHICLE` tier and no catch-all fallback. Compared against the pillbox/bunker MGs, which correctly implement a tiered mask (`HUMAN` → `VEHICLE` → `BTR` → catch-all) - confirmed this is a real omission on the vehicle MGs, not intentional. Added the same three missing tiers to all 6 affected unit files, preserving each file's existing HUMAN-tier settings exactly. Not yet play-tested.

Repaired the usual recurring CP1251 corruption across 4 of the 6 files, byte-spliced from the docs mirror each time as before.

### Why

Direct user report from gameplay observation, following up on the AI target-prioritization fix below.

---

## 2026-07-02 (even later) — AI target prioritization fix

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User reported AI units shoot at whatever's on radar instead of the closest/most dangerous threat, including engaging unarmed trucks over real threats. Scoped first: found `Common\BaseTasks.script` had 5 near-duplicate code paths (covering guns/infantry, wingman aircraft, SPGs, tanks, halftracks) that all took the engine's raw `GetTargetedEnemy()` radar callback and locked onto it with no distance or threat comparison at all. Added one shared `SelectAttackTarget()` method to the common AI task base class that enumerates all currently radar-visible enemies, filters to armed units only (checking `m_WeaponNames` — empty for trucks, since they never register weapons), and picks the nearest, with a 15% hysteresis margin to avoid target-flicker. All 5 call sites now route through it. Left the group-level "first spotter picks for the whole squad" behavior (`UnitGroup.script`) untouched — separate mechanism, not what was reported. Not yet play-tested.

Also hit and repaired the usual recurring CP1251 corruption in `BaseTasks.script` (pre-existing Cyrillic comments elsewhere in the file, re-corrupted by each edit — same pattern as prior sessions, restored via byte-level splice from the docs mirror each time).

### Why

Direct user report from actual gameplay ("ai do not prioritise target either, they shot at any target and ignore the closest threats"), with an explicit follow-up requirement that "nearest" must also mean "armed" — a truck sitting closer than a tank shouldn't win target selection.

---

## 2026-07-02 (later still) — Full whole-repo diff against the live game

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Follow-up to the Vase audit below — this time compared *every* text/script file in the `TvT\` mirror against the live game, not just the ones his commits touched (601 files checked).

- **573 matched exactly.** Good baseline health for the mirror.
- **21 differences were pure line-ending or whitespace noise** (CRLF vs LF, one missing trailing newline, one missing space in a `.rsr` file) — synced for consistency, no real content changed.
- **4 had genuine content differences**, and all four went the same direction as the Vase audit — the live game had moved ahead and the mirror hadn't caught up: `Common\Instances.script` (a much more complete instance-count table for the full current roster), `Common\Mission.script` (see below), `Units\SAUSU85Unit.script` (3 cockpit UI-parm lines deliberately commented out across all its ammo types — reads as an intentional in-progress fix, not an accident), and `Models\bld_Barricade_Pak.script` (the same header/shadow-alignment cleanup pattern as Vase's Feb batch, just never synced back).
- **Interesting side-find**: `Common\Mission.script` references three unit classes by name — `CTankT34_76_41Unit`, `CTankT34_85_44_2Unit`, `CTankPzVI_LATEUnit` — and has real initialization code touching `CPiercing::TankPzVI_LATE...` constants, even though none of those three `Units\*.script` files actually exist. Combined with the fact that their 3D model files already exist and work (from Vase's earlier Model pass), this makes the "LATE Tiger" and the two second T-34 variants the most complete of the cut-content roster found earlier today — model done, some integration done, just missing the actual unit class.
- **Cleanup**: removed 7 stray duplicate Model-type scripts that had ended up sitting in `TvT\Units\` (should only hold gameplay unit scripts — correct copies already lived in `TvT\Models\`), plus one empty leftover `zztest.txt`.

### Why this matters

Confirms the pattern from the Vase audit generalizes: the mirror's staleness is overwhelmingly "live game moved on, git didn't get told," not "git has unapplied fixes." Only one real exception to that found across both passes (the Cockpit.script Distance-wav fix). Also turned up a genuinely actionable lead for anyone wanting to add real new content: the LATE Tiger variant is closer to done than it looked.

### Contributors

- **Jeff Murkin (murkzuk)** — asked for the follow-up pass after the Vase-specific audit.
- **Claude Code (Anthropic)** — built the full-repo comparison, verified each real difference's direction and cause before syncing, distinguished genuine content changes from line-ending noise.

---

## 2026-07-02 (later) — Audited Stevan Vase's git history, fixed a real regression, re-synced the mirror

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Went through all 30 of stevanvase0-beep's commits from Jan-Mar 2026 one by one, diffing every file he touched against the current live game to see what actually made it in versus what's still sitting unapplied.

- **His Feb 3-4 Model/LOD/shadow completeness pass (49 files) is good, already-integrated work.** Confirmed byte-for-byte match with the live game.
- **His Jan 8-9 mission-lighting sweep across ~14 Campaign_1/Campaign_2 missions has been superseded** by the user's own later hand-tuning (values tagged `//jm`) done directly on the live install — nothing to apply, but it meant the docs-repo mirror for those files was stale.
- **Found and fixed a real regression**: his Jan 13 "structure alignment" pass on `TankPzVIAusfEUnit.script` accidentally deleted `void AddWingman(Component unit) { }` — a stub that exists purely to stop `Common\BaseTasks.script`'s wingman-task code from throwing a "function not found" error on the player's tank. Restored it, and added the same stub to `T34_85_44.script` and `T34_76_42.script` too, since neither of them had ever had it despite being equally exposed to the same call path (Pz IV was left alone — it's AI-only, never player-controlled, so it can never be the target of that call). Hasn't caused a visible problem in any log yet since the wingman feature itself is dormant, but it's a real latent bug, not a hypothetical one.
- **Applied his Jan 24 Cockpit.script fix** that had never made it to the live game — an empty `["Distance", ""]` sound file mapping (both Soviet and German sound tables) was commented out, matching what looked like an attempt to stop a "can't load" error.
- **Re-synced 27 stale files** in the `TvT\` mirror (7 shadow scripts, ~14 mission files, plus the 3 tank scripts and Cockpit.script touched above) from the live game.

### Why this matters

This wasn't just a courtesy check — it turned up a genuine bug (the missing wingman stub) that's been live since January and would have surfaced eventually. It also confirmed the bulk of Vase's work is solid and already paying off (the shadow/LOD pass), while making clear the docs-repo mirror had drifted out of sync with the live game in both directions - some contributions never got applied, some live-game improvements never got synced back.

### Contributors

- **stevanvase0-beep (Stevan Vase)** — original author of the Model/LOD/shadow work, the mission-lighting pass, and the Cockpit.script Distance-wav fix, and the unintentional source of the AddWingman regression.
- **Jeff Murkin (murkzuk)** — flagged that Vase's contributions had never been reviewed, made the call to fix and sync.
- **Claude Code (Anthropic)** — audited every commit, diffed against the live game, traced the AddWingman call chain to confirm it was a real (if dormant) risk before fixing it.

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
