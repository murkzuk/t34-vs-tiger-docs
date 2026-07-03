# Changelog — t34-vs-tiger-docs

All notable changes to this repository. The most recent entry is first.

This file is human-written, plain prose. For technical details, see [PROJECT_MAP.md](PROJECT_MAP.md) and [llms.txt](llms.txt).

---

## 2026-07-03 (Phase 2 capstone) — Full production .ms2 file parses byte-perfect end to end

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Resolved the last open discrepancy from earlier today (the `wpn_Bomb.ms2` shadow-volume block mismatch) by pulling raw x86 disassembly instead of relying on decompiler-reconstructed C, which can miscombine short-circuited expressions. Confirmed the actual machine code does three unconditional writes once the relevant flag bit is set, and confirmed via careful re-verification that the file's real count value is read correctly - the file's true end simply doesn't have room for the third write the code demands. Root cause: `MayaExp.mll` is dated June 2007, `wpn_Bomb.ms2` is dated January 2006 - a genuine historical version mismatch between an older asset and a newer build of the tool, not a parsing error. Then validated the whole approach against a full, real, shipped production asset for the first time: `ms2_parser.py` parsed `u_veh_t34_85_44.ms2` (219 nodes, 12.9MB) to the exact byte with zero leftover, using nearly every documented optional data block in real combination throughout the file. Found one more real bit not yet identified (doesn't affect byte layout). The core `.ms2` format is now considered verified against production content, not just simple test files.

### Why

Continuing to push per the user's request - this was the natural conclusion of the whole Phase 2 decompilation effort, closing the loop with the strongest possible evidence (a real, complete, shipped asset parsing perfectly).

---

## 2026-07-03 (Phase 2 final push) — All eight .ms2 optional-block bits now identified

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Closed out the flags_bitmask investigation. The five bits that didn't trace back to any of Phase 0's known mesh attributes were found instead by scanning every instruction in the whole binary for an OR against each specific bit constant - a few direct hits on the exact `flags_bitmask` struct-field pattern pinpointed the real setter function for each one immediately, no more manual call-graph tracing needed. Decompiling those functions gave real, log-message-confirmed identifications: bone/joint attachment data, skin blend weights, joint-mesh-cloning, per-joint bind-pose matrices (confirmed via a textbook identity-matrix initialization pattern), and very likely tangent-space vectors. Two bits remain confirmed-but-unnamed (real structured data, exact purpose not yet pinned down). Every one of the eight optional-block bits now has at least a confirmed real trigger condition from decompiled code.

### Why

Continuing to push per the user's request - this was the natural conclusion of the flags_bitmask work, closing out nearly the entire open question from the last update.

---

## 2026-07-03 (Phase 2 continued) — Decoded most of flags_bitmask by tracing the attribute reader

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Direct continuation of the same-day Phase 2 decompilation work. Rather than continuing to guess at the six flag-gated optional data blocks found in the `.ms2` per-node structure, traced where the exporter actually reads each Maya mesh attribute (`IsWalkMesh`, `IsCollisionMesh`, `IsHidden`, etc.) and decompiled the function that packs them into `flags_bitmask` (`FUN_1008d120` in `MayaExp.mll`). This gives a definitive, named bit-to-attribute mapping for most of the field. Critically, traced one of the mystery block-gating bits (`0x40`) to `HasShadowVolume`, and decompiling the large function that runs when it's set confirmed it's a genuine shadow-volume silhouette-edge/BSP builder - real geometry processing, not a simple flag. Also found `IsDoorObject` belongs to an entirely separate joint/hinge subsystem, not this bitmask. Five of eight block-gating bits remain unmapped - likely tied to skin/animation export rather than any of Phase 0's known mesh attributes.

### Why

Continuing to push on the remaining unidentified optional blocks per the user's request, using the same decompilation approach that already worked for the core structure.

---

## 2026-07-03 (Phase 2) — Ground truth for the .ms2 format via real decompilation

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Moved from empirical byte-probing to actual decompilation of `MayaExp.mll`, per the user's direction. Ghidra was already installed on the machine but had no working JDK (only JREs) - downloaded the official portable Eclipse Temurin JDK 21 (zip, no installer) and pointed Ghidra's config at it, now saved permanently at `M:\TvT 2024 working folder\jdk-21-portable` for future sessions. Traced the real code path from plugin registration through to the `exportG5Resource` command's actual implementation. Confirmed the model-export function writes the `Models\*.script` boilerplate directly (matching this project's own earlier `.script` housekeeping-file audits exactly) before calling the real `.ms2` binary writer, which was fully decompiled. This confirmed every Phase 1 empirical finding was correct as far as it went, and revealed several real fields Phase 1's byte-probing had completely missed - most importantly a `node_id` field, confirmed via a real 219-node vehicle file to be the parent node's index in the file (explaining what Phase 1 had misidentified, in the wrong byte position, as "parent_idx"), and a `flags_bitmask` gating six optional data blocks that real shipped assets always use but no test/tutorial file ever triggers. Built `Tools\MS2Format\ms2_parser.py` implementing the ground-truth structure - 4 of 9 test files parse to an exact, zero-leftover byte match.

### Why

User's direction: move to real decompilation as the logical next step once empirical byte-probing alone started hitting diminishing returns on the multi-node hierarchy puzzle.

---

## 2026-07-03 (latest of all, corrected) — Real breakthrough: found the actual vertex/index count fields

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Direct continuation of the same-day Phase 1 work below. Caught and corrected a real mistake in that earlier pass: 16 bytes that were reported as "always-zero padding" were actually being misread - printing them as `round(float_value, 6)` made tiny denormalized floats (the bit pattern for int32 `24` reinterpreted as float32 is `3.36e-44`) display as `0.0`, hiding real data. Re-reading the same bytes as int32 revealed the actual `vertex_count` and `index_count` fields - confirmed exact against the known cube (24 vertices, 36 indices) and cross-validated against an independent magnitude-based estimate for `Sky.ms2`'s `SkyDome` (395 vertices both ways). Verified the complete per-vertex geometry layout end to end on 7 diverse sample files, all producing physically sensible bounding boxes for their actual shapes. Built `Tools\MS2Format\ms2_probe.py`, a real (if still limited) parser implementing this. Found two new, still-open problems while stress-testing further: a 3-node file breaks the `parent_idx`/`child_count` pattern that held for the 2-node case, and some files have large unexplained trailing data that doesn't scale simply with vertex count.

### Why

Continuing Phase 1 of the issue #12 effort at the user's request - a genuine correction of an earlier mistake, caught by cross-checking int32 vs float32 interpretations rather than trusting a rounded display value.

---

## 2026-07-03 (latest of all) — Phase 1: first real decoded structure in the .ms2 binary format

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Direct follow-up to the Phase 0 scoping/documentation pass on issue #12. Started empirical byte-level probing of real `.ms2` files, beginning with the smallest samples - `Landscape_test.ms2` (124 bytes) and `MyFirstModel.ms2` (1695 bytes, which is literally the exact cube exported in the tutorial's own screenshots, giving a known-geometry test case). Confirmed a universal file header across all 62 sample files (version constant, a node count that scales cleanly with model complexity, a length-prefixed object name). Then, cross-checking every numeric guess against the known cube's actual dimensions rather than eyeballing hex, fully decoded and closed-loop verified the entire per-vertex geometry block for a simple mesh: bounding box, bounding sphere (radius matched to 7 significant figures), 24 vertex positions, 24 normals (all exact axis-aligned unit vectors), 24 UV coordinates, and 36 uint16 triangle indices (exactly matching a cube's 12 triangles, every index valid). Also found that `u_veh_t34_76_41.ms2` (the already-known orphaned cut-content T-34/76 variant) has a structurally anomalous root node compared to its finished siblings - independent confirmation, from pure binary analysis, of something only previously suspected from a separate script-level audit. Clarified that materials/textures aren't stored in `.ms2` at all - they live in the already-fully-understood companion `.script` files. Findings written up in a new `Documentation/MS2_Binary_Format_Findings_2026-07-03.md`, linked from the Phase 0 manual.

### Why

User asked to proceed with Phase 1 of the previously-scoped plan for issue #12 - real progress toward the eventual goal of Blender import/export support.

---

## 2026-07-03 (yet later) — Scope GitHub issue #12 (Maya exporter / .ms2 format), correct existing Maya export manual

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User's goal for issue #12 is bigger than the issue's own title suggests: understanding the `.ms2` format well enough to eventually build a Blender import/export pipeline - a real community deliverable. First corrected the issue's own premise: `MayaExp.mll` is a standard Windows PE32 DLL, not a proprietary encoding needing "unpacking" (the CGNS_MLL link in the issue is an unrelated aerospace/CFD standard, a coincidental acronym match). Then did "Phase 0" of a proposed multi-phase plan: re-verified the repo's existing `Documentation/T34_vs_Tiger_Maya_Export_Manual(V3).md` line-by-line against the actual `Tools\Scripts\*.mel` source, since it claimed to be fully verified but wasn't - found and corrected 4 fabricated mesh attributes, 11 missing real ones, a wrong collision-naming convention, and an entirely fabricated "G5Entity" section, while adding 3 previously-undocumented systems (character head swap, portal/occlusion culling, a schema-migration utility) and flagging a real unreconciled discrepancy (`exportG5Resource` called with two different argument counts from two different scripts). Also found and added a newer 2024-revision tutorial (from the user's own external TvT manuals archive) revealing a D3DX9_28.dll dependency not previously documented anywhere in this repo. The manual is now v4.0. The actual `.ms2` binary format itself remains completely unstarted - this pass only nailed down the Maya-side authoring metadata, which is a necessary but not sufficient step toward a real importer/exporter.

### Why

User wants a properly scoped foundation before committing to the real reverse-engineering work, and specifically flagged Blender import/export as valuable to the wider community - worth getting the groundwork right rather than rushing in.

---

## 2026-07-03 (even later) — Fix missing/broken intersection entries (GitHub issue #8)

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Same pattern as issue #4: the model-header half of this issue was already resolved (every real gameplay model already declares both `UseBoxForIsection`/`UseShapesAsWalkedMesh`). The real gaps were in `Common\Intersections.script`'s per-model override list. Added a missing entry for `Cfence_PoleModel` (its fence siblings both had entries, this one had none). Found and fixed a genuine typo, not an engine limitation: two tanks (`Cu_veh_PzIVGModel`, `Cu_veh_t34_76_42Model`) had their `UseBoxForIsection` line commented out with a note claiming it "creates error in execution log" - the actual line read `= fasle;`, a misspelling of `false` that's an invalid identifier, which is almost certainly what actually threw the compile error. Confirmed `fasle` appears nowhere else in the codebase. Uncommented and corrected both to match every other tank's existing pattern. Left two genuinely ambiguous cases alone rather than guess (the cockpit-interior `_Inside` submeshes, and an odd static-vs-moving mismatch between tankman and soldier-rifle human models) - flagged in TODO.md for anyone who wants to test them properly in-game.

### Why

User asked to scope then fix the confident parts of issue #8, continuing today's run through the open issue backlog.

---

## 2026-07-03 (later still) — Resolve duplicate T-34/85 model files (GitHub issue #7)

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Issue #7 flagged two T-34/85 model file sets in `Models\` (2006 and 2007) and asked which to remove, expecting in-game testing to decide. Turned out code evidence alone was conclusive: the 2007 set (`u_veh_t34_85_44.ms2`/`.script`) is the live model, wired directly into the real playable/AI unit and the only one with cockpit-camera/hatch joints for the driver's interior view. The 2006 `_2` set shares nearly the same textures/skin but has no cockpit joints at all - an old pre-cockpit-support export left behind, not a distinct tank variant (unlike `TankPzVI_LATE`/`T34_76_41`, which have real unused stats worth finishing). It was never wired to any Unit class, never placed in a mission, and only touched 8 generic per-model housekeeping scripts (shadow/instance/intersection config) - those 10 leftover lines were removed. The two orphaned model files were moved to `Models\_Removed\` on the live install rather than deleted outright (an auto-mode safety check declined a same-turn deletion of files identified by investigation rather than named explicitly by the user, so relocation was used instead - fully reversible either way).

### Why

User asked to scope and then fix issue #7 after a run of smaller wins this session.

---

## 2026-07-03 (later) — Fix Nebelwerfer shadow-LOD copy-paste typo

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

While looking into GitHub issue #4 (shadow settings missing from model headers), found that issue is largely already resolved - every real gameplay model has all 7 shadow-related header fields; only skyboxes and dev/test scaffolding lack them, which is correct (they don't cast shadows). But `Common\ShadowHide.script`'s `InitializeShadowsHide()` had a real copy-paste typo: the Nebelwerfer's line set `LodForShadowChange` (already correctly set to 2.5 elsewhere, in `ShadowsChange.script`) a second time, instead of `LodForShadowHide` as intended - meaning the Nebelwerfer's actual `LodForShadowHide` was silently falling back to `CBaseModel::DefaultLodForShadowHide` (9999.0f, i.e. never hide/reduce the shadow at distance), unlike its Pak 40/Zis-3 static-gun siblings which correctly drop to a cheaper shadow at LOD 2.5. Fixed the field name to match its siblings.

### Why

Small, low-risk fix spotted while triaging issue #4 - a genuine inconsistency worth closing out on its own even though the broader issue turned out to already be substantially addressed.

---

## 2026-07-03 (final, corrected) — Fix "MissionName not found" briefing-menu crash

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

The previous entry below ("Dynamic scout-report briefing text") shipped a version of `MissionTestStrings.script` that wrote the computed scout-report text as literal `WString` values directly into each target's Strings class every run. That loaded fine in the Level Editor, but the real in-game briefing menu (`StartMissionMenu.script`) failed with `"Static variable MissionName not found in class CSteppeQuickMissionMission_Strings"`, cascading into a `SetText` failure - and this persisted even after a fully clean Editor/cache restart, which ruled out the initial stale-cache hypothesis and pointed at a real bug. Root cause, confirmed via cross-codebase evidence rather than guesswork: `getStaticClassMember()`'s reflection does not reliably find literal `WString` static fields, even though literal plain `String` fields work fine via the exact same mechanism (proven precedent in `Common\PassangerAnimator.script`). Every real, active `WString` field in every mission's Strings class in the entire codebase uses `getLocalized(...)` - there is no working precedent anywhere for a literal `WString`.

Fix: `MissionTestStrings.script` is a static file again (not regenerated per run), using `getLocalized(LOCALE_SECTION, "Field")` against two new dedicated sections in `Locale\eng.locale` (`[QuickMissionGenerated]`, `[SteppeMissionGenerated]`) - never the shared `[MissionTest]` section `Mission1` itself depends on. `generate_mission.py` now rewrites only that one dedicated section each run and separately verifies every other section of the shared locale file stays byte-identical. Verified with a 40-combination sweep (2 targets x 2 factions x 10 seeds): single-section replacement (no duplication) on repeated runs, `[MissionTest]` untouched, 0 CP1251 corruption.

### Why

Direct fix for a real bug the user caught by testing in-game, not just in the Editor - a good reminder that Editor play-test success doesn't fully prove the real menu flow works.

---

## 2026-07-03 (final) — Dynamic scout-report briefing text for the Quick Mission Generator

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Both generated mission slots showed generic, disconnected placeholder briefing text ("Destroy the ZIS-3 battery" regardless of whether that unit was even in the roster) pulled from a shared locale section - and it was actively misleading, since the real win condition is just reaching the marked NavPoint. `generate_mission.py` now computes a real scout report from the actual randomized layout (enemy composition, distance, compass bearing from the player's spawn) and writes it as literal text directly into each target's own `MissionTestStrings.script`, bypassing the shared locale file so `Mission1`'s own tutorial text is never touched. Confirmed literal `WString` assignment is valid syntax first (proven elsewhere in the codebase) before relying on it. `MissionTestStrings.script` became a second legitimate per-run output file, so the "nothing else changes" safety check was updated accordingly. Fixed a grammar bug caught during testing ("infantrys"). Verified with a 40-combination sweep.

### Why

User's idea, inspired by Whirlwind over Vietnam's text/radio mission briefings - wanted to add context to the Quick Mission Generator's output rather than leave it blank/generic.

---

## 2026-07-03 (latest) — Reposition steppe map spawn away from immediate detection

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

With the floating-object bug fixed, the player spawn worked but got spotted the instant they appeared - the inherited `Mission1` enemy cluster (Tiger + 2 Pak 40s) sat only 1300-1500m away with no forest left to screen it, unlike the original wooded map which silently protected this same layout. Per the user's suggestion, moved the spawn to 2000m from the enemy cluster along the same approach axis, and rotated it to face back toward the cluster. Confirmed the engine's rotation-matrix convention empirically (from the existing obstacle objects' clean 2D rotations) before trusting it for the new orientation. The new spawn's height needed a linear fit calibrated from the other 26 objects' known-good heights, since this is a genuinely new location rather than a rescaled existing one - flagged clearly as an estimate, not a guaranteed exact match like the earlier floating-gun fix.

### Why

Direct follow-up to the user getting spotted immediately on spawn and suggesting the fix themselves.

---

## 2026-07-03 (later still) — Fix floating-object bug on the steppe map (root cause of the RouterZone issue too)

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User spotted a Pak 40 gun floating in mid-air testing `SteppeQuickMission` in the Editor. Root cause: every object's position was copied verbatim from `Mission1`, but stretching `MatrixWidth` to 18000 changes which heightmap pixel a given X/Y coordinate samples - so authored Z values no longer matched the real terrain height there. Confirmed empirically (311 raw elevation units off). Fixed by scaling every object's X/Y (not Z) in `SteppeTemplate\Content.script` by 2.0, the same stretch factor - verified this puts every object back on its originally-authored heightmap pixel. This turned out to be the same root cause behind the earlier RouterZone soft-filter issue, so that filter was re-enabled for the steppe target now that the actual problem is fixed rather than worked around. Re-ran the full 20-combination target/faction/seed sweep - all pass.

### Why

Direct follow-up to the user spotting the floating gun while testing in the Level Editor.

---

## 2026-07-03 (later) — Steppe map confirmed working, generator extended to target it

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

`SteppeTemplate` loaded successfully in the Level Editor after the earlier BMP byte-size fix - terrain and sparse forest look right, 125fps. Built `SteppeQuickMission` (same setup pattern as `QuickMission`/`Mission1`) and extended `generate_mission.py` with a `--target quickmission|steppe` option, `quickmission` staying the default so nothing about the existing tool changed for existing use. `gui.py` got a matching map-choice control. While testing, found the same seed produced different unit counts on the two targets - traced to the RouterZone bitmap being reused unmodified at a different MatrixWidth, so the same coordinate samples a different pixel/passability verdict on each target, desyncing the RNG stream. Fixed by disabling that (already-unproven) soft filter specifically for the steppe target rather than leaving it silently inconsistent. Verified both targets across a 20-combination seed/faction sweep.

### Why

Direct continuation of the steppe mission work, extending the existing Quick Mission Generator tool to the new map per the user's decision to reuse it rather than hand-script a new battle.

---

## 2026-07-03 — Fix SteppeTemplate Editor crash (BMP byte-size mismatch)

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

First Editor test of `SteppeTemplate` crashed at ~20% load. `editor.log` pointed at `TerrainZone_Test.bmp` failing a strict file-size check, which cascaded into "Can't find layer with id TerrainZone" and the crash. Root cause: the earlier forest-thinning pass re-saved the bitmap through PIL, which writes a slightly different BMP structure than the original file (2 bytes shorter - Mission1's original has 2 trailing null bytes PIL doesn't reproduce). Fixed by redoing the thinning directly on the raw file bytes - read the original, modify only the pixel-data byte range in place, keep everything else byte-for-byte identical. Result matches the original's exact 1049656-byte size. Also fixed a harmless, pre-existing naming mismatch (inherited from Mission1 itself) between the mission-strings class name and what the menu script actually looks up.

### Why

Direct follow-up to the user testing the newly-built SteppeTemplate mission in the Level Editor and hitting a crash.

---

## 2026-07-03 — First steppe mission template built

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Built `Missions\MyMission\SteppeTemplate\`, the first concrete step on the large open-steppe mission concept. Rejected `Campaign_2\Mission_6` as the terrain source after actually rendering its heightmap (a statistically-flat candidate identified in scoping) - it showed no real terrain features at all even after heavy smoothing, unlike `Mission1`'s terrain which clearly shows a real river valley and hills under the same rendering. Used `Mission1`'s own terrain instead, unmodified, relying on the confirmed stretch technique (same height values mapped over a bigger `MatrixWidth`) to flatten the effective slope for free - proved this with an actual elevation cross-section plot rather than just asserting it. Forest density needed a real fix though: `Mission1`'s zone bitmap was 55.7% forest-coded, and stretching doesn't reduce that percentage, so thinned it via 32-pixel block-clustered random removal down to 8.84%. Registered the new template in `MenuConfig.script` at 18000x18000 (a deliberately moderate first step, not the full 36000 ZW used). Not yet opened in the Level Editor to confirm it works.

### Why

Direct follow-up to the steppe mission scoping pass, per the user's decision to reuse the Quick Mission Generator's approach with a second, bigger template.

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
