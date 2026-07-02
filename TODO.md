# TODO / Backlog — t34-vs-tiger-docs

Running list of things flagged during work sessions, not yet done. Newest first within each section. See `CHANGELOG.md` for what's already been done.

---

## Quick Mission Generator (`Tools\MissionGenerator\`)

- [x] Expand `roster.json` with a few more grep-verified unit types — done 2026-07-02. Added SU-85/StuG 40 (self-propelled guns, correct task is `CBaseAISAUTask` not `CBaseAITankTask` - confirmed live in Campaign_2\Mission_4) and German/Soviet riflemen (`CBaseAITask`, confirmed live in Campaign_1\Mission_1/2). Each side now has tank/AT-gun/SAU/infantry. Verified with 40-seed sweeps per faction that every class actually appears.
- [ ] Confirm the `RouterZone_Test.bmp` color-to-passability mapping in-game (currently an unproven empirical soft filter — see `Mission_File_Schema_Verified_2026-07-02.md` §2b/Unresolved).
- [ ] Unit facing/yaw randomization (v1 uses fixed identity rotation, all units face the same compass direction).
- [ ] Consider a second/bigger template mission for more spawn variety — `MyMission\Mission1`'s proven-safe zone is a small ~1300x3000 unit cluster out of the full 9000x9000 map. Real campaign missions were ruled out as templates (too trigger-coupled — see the 2026-07-02 CHANGELOG entry), so this needs either a different low-coupling mission or building a fresh dedicated template mission from scratch.

## Bigger, separate efforts (not generator-specific)

- [ ] **Tiger's own machine gun fire effect missing** (`[EffectsArray] Effect pattern not found "MachineGunMG34FireEffect"`, `Scripts\Units\TankPzVIAusfEUnit.script`) — `EffectsArray.script` only registers a generic `"MachineGunFireEffect"`, never the MG34-specific name the Tiger's script requests. Cosmetic only (damage calculation proceeds fine). Likely a genuinely new discovery from the 2026-07-02 AXIS-player feature — the Tiger was previously only ever a stationary AI enemy, so nobody had actually fired its weapon as the player before to exercise this code path.
- [ ] **Zis-3 explosion sound missing** (`[SoundsArray] Sound "GunZis3ExplosionSound" not found in sounds array`, fires when a Zis-3 gun is destroyed) — `Common\Sounds.script` registers `"Zis3GunFireSound"` but never a matching explosion sound, even though `Scripts\Units\GunZis3Unit.script:21` expects one. Pre-existing gap in the original game content (would affect any mission that destroys a Zis-3, not just the generator) — cosmetic only.
- [ ] **Tiger 3D model animation gaps** — missing gun-laying needles, commander hatch, and a few gauges, from the `Cu_veh_PzVI_MAINModel` → `Cu_veh_PzVI_LATEModel` swap (part of earlier "improved LODs" work). Needs actual Maya work, not scripting — `Documentation/T34_vs_Tiger_Maya_Export_Manual(V3).md` and the newer `export manual. Tutorial 1 2024 revision b.pdf` (not yet added to this repo) are the relevant references.
- [ ] **Proper AI Task classes for Campaign_2\Mission_5's 3 groups** (`CC2M5GroupSU85`, `CC2M5GroupStug_40`, `CC2M5GroupRusSoldiers`) — currently bare `extends CBaseUnitGroup {}` stubs (fixed a "doesn't load at all" bug, but they lack the scripted combat behavior real groups like `CC1M3RussianPanzerGroup1Task` have. See `Mission_File_Schema_Verified_2026-07-02.md` §2c.
- [ ] **AutoCommander false→float bug** (`Common\BaseTankAutoThingUI.script` area, fires 3x every mission start) — root cause likely compiled `Controls.dll`/`UI.dll`, not `.script` text. Ruled out every script-side theory this session (including one tested-and-reverted placeholder fix). Would need actual DLL disassembly to go further — bigger, riskier undertaking than anything done so far.
- [ ] `Missions\MISSIONS\CF*/DM*` and `MyMission`/`MyMPMission` are now tracked in this repo, but nobody's done a fresh error-log sweep on them yet the way the campaign missions got this session.

## Documentation gaps (schema doc's own "Open Questions" section)

- [ ] `IsMissionFullCompleted()` vs `IsMissionCompleted()` — when is the "full" variant actually used?
- [ ] The 5th `m_MissionObjectives` tuple element (`RedTeamObj`/`BlueTeamObj` counting) — looks multiplayer-specific, needs an MP mission example to confirm.
- [ ] `SOID_MissionController`'s full event/method surface — only `"StartRetreat"`/`"CompleteMissionStatus"` traced so far.
