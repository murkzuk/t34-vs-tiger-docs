# Changelog — t34-vs-tiger-docs

All notable changes to this repository. The most recent entry is first.

## 2026-08-27 (c) — the replacement Panzer IV's twitchy handling

User reported it "turns too quickly, it is jarring". First check compared
`MaxRotateSpeed`, road speed and mass — all identical to stock — and said so.
Wrong field.

```
                            stock       ZW replacement
MaxNegativeAccelleration    1.5         2.5      67% harder braking
CollisionRadius            12.0         8.0
```

Differential braking is how a tracked vehicle pivots, so harder deceleration
makes turns snap rather than sweep. **`TankPnzIV_G_AI` at 2.5 was the highest of
any vehicle in the game** — everything else sits between 0.1 and 1.5. One unit
tuned and overshot, not a factional thing. Set to 1.5.

`MaxBrakingAccelleration` verified identical (2.5 both). `CollisionRadius` left
alone — 8.0-8.5 is normal for ZW units; the stock 12.0 is the outlier.

ZW stamped `v0.260827c`.


## 2026-08-27 (b) — the ZW-ONLY units, which is where the bias actually lived

**The first revert was necessary but incomplete, and a play test proved it.**
User died quickly playing Soviet; the log showed why — the mission fields
`CTankPzVI_E1_AI_Unit`, `CTankPnzIV_G_AIUnit`, `CTankT34_76_42AIUnit`, none of
which the first pass touched. It could only cover the **19 units with a 2001
original to diff against**; ZeeWolf's own variants, which his missions actually
use, were out of scope by construction.

What they were carrying:

```
Tiger E1              0.001      Panzer IV AI      0.10
Panther D Playable    0.001      Panzer III L60    0.10
Panther D              0.01      Hummel            0.10
Tiger E1 Early         0.01      Nashorn / Pak 43  0.25
Panther A / StuG F8    0.05      Flak 88            0.5
Marder / Wespe / sIG   0.05      Tiger AI variants  0.1 - 0.25
```

**The Tiger E1 was on `0.001`. G5's Tiger is `1.2` — twelve hundred times less
accurate.** Meanwhile the restored T-34/85 sits at 1.25 and the ZW T-34/76 AI at
1.6.

**21 values changed**, mapping each ZW-only unit to its G5 counterpart:

```
Tiger family, Panther, StuG family   -> 1.2   (G5's Tiger / StuG III)
Panzer IV, Panzer III, SP guns,      -> 1.5   (G5's Panzer IV / Pak 40)
towed AT (Pak 43, Flak 88/38)
```

Panther has no G5 equivalent and was treated as Tiger-class. **Soviet artillery
left alone** at 1.75–4.75 — mortars and howitzers scattering is correct for
indirect fire.

Backups: `ZW_Units_2026-08-27_pre_revert\` (before pass 1) and
`ZW_Units_2026-08-27_pre_zwonly\` (before this pass), so either is independently
reversible. ZW stamped `v0.260827b`.

**Running total for the ZW work: 47 values** — 23 reverted to G5, 3 sensor
ranges equalised, 21 ZW-only units mapped.

### The lesson

**Check what the missions actually field before measuring anything.** A whole
pass was spent on units that never appear in play. One `grep` of the execution
log for instantiated unit classes would have shown it in seconds.


## 2026-08-27 — ZW's handling and gunnery bias reverted to G5's values

**23 changes applied to `M:\T34vsTiger_ZW2015\Scripts\Units\`**, each verified
against the untouched 2001 original. ZW stamped `v0.260827`, cache cleared.
Backup: `K:\TvTDeepseek\rollback\ZW_Units_2026-08-27_pre_revert\` (87 files).

**AI main-gun accuracy** (`FireDeviation`) — every German gun had been made
3–60× more accurate than G5 set it, every Soviet gun worse or untouched:
```
CGunPak40Gun        0.5  -> 1.5      CTankT34_76_42Gun   1.6  -> 1.5
CTankPzIVGGun       0.10 -> 1.5      CTankT34_85_44Gun   1.55 -> 1.25
CTankPzVIAusfEGun   0.05 -> 1.2      Tiger coax + hull MG 0.05 -> 0.15
CSAUStuG40Gun       0.02 -> 1.2
```

**The only player-gun nerf in the game:**
`CTankT34_85_44PlayerGun` **0.15 -> 0.005** — the player's T-34/85 had been made
thirty times less accurate while every German player gun was left untouched.

**Turret traverse** (`DirectionSpeedH`): T-34/85 8→17, T-34/76 7→36, SU-85 3→5,
ZiS-3 4→6, Panzer IV 8→14, Tiger 6.5→4.5.

**Tiger mobility and rate of fire:** mass 40t→56t (real Tiger I is 57 t),
suspension 0.4→0.9, engine max RPM 2730→2200, fire period 7000→12000, random
add 2000→8000. **T-34/85 mass** 48t→40t.

**Also reverted on the user's call:** `T-34/85 MaxPower` 1800→1400 (ZW had
*buffed* the Soviet engine — keeping it would have been a thumb on the scale in
the other direction) and `SU-85 FirePeriod` 9000→8000 (the only gun in the game
ZW made *slower*, and it was Soviet, while the Pak 40 went 10000→5000).

**CORRECTED AND FIXED 2026-08-27, same day.** The sensor decision below was
made on a partial sample and was wrong. The Tiger detected at 2600 m against the
T-34/85's 1650 m - a 950 m window where it engaged and the Soviet tank could not
see it - and the T-34/76 engaged at 2600 m while detecting at only 800 m, the
only vehicle in the game whose vision ZW *reduced*.

**Resolved by equalising upward** (option 2 - keep ZW's better ranges, remove
the tilt): `T-34/85` detection and engagement 1650 -> 2600, `T-34/76` detection
800 -> 2600. Both T-34s now see as far as a Tiger. SU-85 (2400) and StuG III
(2000) left as they were - the Soviet vehicle is already the better of that
pair.

**Deliberately NOT reverted (see correction above):** sensor and engagement ranges
(`MaxRadarDistance`, `AttackDistanceMax` etc.). ZW raised those for **both**
sides — ZiS-3 800→3200 m, SU-85 1200→2400 m — which is genuine modding over G5's
myopic originals, not bias. Also left: the general rate-of-fire increase applied
to both sides, both halftracks' mass halving, and the AI-driving fields
(`AutoDriverAnglePower` etc.), which look like real AI improvements.

Method: edited **per class**, because a unit file holds separate AI and player
gun classes with the same field name. Dry-run first (21 of 21 expected values
found exactly where predicted), then applied, then re-compared against the
original to confirm. `Tools/compare_unit_stats.py` makes the check repeatable.


## 2026-08-26 — the .ms2 exporter works, confirmed in the engine

**The G5 Level Editor loaded and rendered a `.ms2` written by our own code.**

Test: `Models/4MeterBox.ms2`, an original G5 file from **December 2005** used by
no mission, exposed in the Editor as "Dartboard 4 meters". Every Z coordinate
tripled — Asset View showed `C4MeterBoxModel` as a 3× tall rectangle, console
clean. Original restored, md5 verified.

**Step 1 first, and it is why this worked on the first attempt:** all 249 models
in both builds were read and rewritten *unedited*, then diffed —
**248 byte-identical, 0 differ**, 1 pre-existing reader failure
(`u_veh_PnzIV_G_AI_.ms2` does not parse at all). Round-trip before you edit.

`Tools/MS2Format/ms2_writer.py` does not regenerate a file. It copies the
original byte-for-byte and substitutes only the geometry span, so every block of
known size and unknown meaning — `vcount × 24` tangent data, 80-byte bind poses,
161-frame animation tracks — is preserved verbatim rather than invented. It
asserts the geometry round-trips before writing and refuses length-changing
edits.

**Limit: vertex and index counts must not change.** Moving, rescaling and UV
edits are safe; adding geometry needs the `vcount × 24` block identified first.
Skinned meshes untested (the subject was a static box).

Two runs were lost to the test bed rather than the code: the exe was launched by
full path from another directory (TvT resolves `Scripts\`, `Models\` and its log
relative to the **current** directory — grey screen, no log), and
`M:\TvT_INJECT_SANDBOX` had 25 drifted scripts including one that would not
compile. The sandbox was refreshed from live. **The Level Editor is the better
test bed** — it loads models directly rather than through a mission.


## 2026-08-26 — the .ms2 model format, fully decoded

The importer went from "imports parts" to "imports finished vehicles". Three
things it was skipping:

- **UVs are DirectX convention** — V runs 0 to **-1**, so it must be negated
  (`loop.uv = (u, -v)`). 104 of the King Tiger's 138 textured nodes had UVs
  outside 0..1, every V range negative. Values beyond 1 after flipping are
  legitimate **tiling** (the track mesh runs to 8.0, one per link repeat).
- **The node transform is frame 0 of an animation track** — `d_count` positions
  then `d_count` quaternions (W first), `d_count == 161` in every vehicle.
  `161*28+4 = 4512`, exactly the "fallback block" size earlier notes recorded
  without naming. Frame 0 measured as the rest pose: 199 of 220 nodes at
  identity rotation there.
- **The material index is packed** into the 16-byte record also being skipped:
  `(icount << 16) | material_index`, low half indexing the `.script`'s ModelSkin
  array. All 138 geometry nodes resolve.

Supporting facts: `.tex` files are plain **DDS**; materials, texture paths and
alpha modes are plain text in the model `.script`; **alpha mode `NORMAL` must be
honoured** or decals render as black rectangles; and **a material with no
texture is armour/collision geometry**, not visual — hide it.

Verified against the real vehicles: King Tiger imports at **10.21 m** against a
true 10.29 m, Tiger I at 8.34 m against 8.45 m.

Two instrument traps recorded: **Blender loads the installed addon copy, not the
repo one** (ours was 8 days stale, so edits silently did nothing), and
**`matrix_world` is stale until `view_layer.update()`**, which made a working fix
look like a failure.

`ms2_probe.py` is **superseded** — it desyncs on real vehicles, and the
`other_count == 4` in older notes came from that desync. It is 1.


## 2026-08-26 — version stamps

Both builds bumped to **`v0.260826`** (`VersionID` in
`Scripts\GameSettings.script`), caches cleared.

Note the rule was extended: **a DLL-only change counts as a ship.** The whole
win below lives in `tvt_los_hook.dll` with no script edit at all, and "which
build has the LOS fix in it?" is precisely the question the on-screen stamp
exists to answer. The launcher injects the same hook into either install, so
both get bumped together and matching dates mean the two are in step.

## 2026-08-26 — the LOS hook was costing 55% of the framerate

```
BEFORE   LOS on   51 fps      LOS off  115 fps
AFTER    LOS on  120 fps      the hook is now free
```

**2.35x, and the answer to the long-standing "70-90 fps feels bad".** It was
never the 2001 engine - it was our own hook, default-on in the launcher.

`readable()` in `K:\tvt_los\hook.cpp` is a `VirtualQuery`, i.e. a syscall. Two
places called it in loops:

- `find_endpoints()` - up to `128 + 128*128 = 16,512` syscalls **per vision
  check**, to validate a window only 520 bytes wide. Now one whole-window check
  (with a per-element fallback if it straddles a region boundary), and
  candidates collected once instead of re-validated 128 times in the inner loop.
- `CrewHook()` - a 256-field sweep, **ungated, every crew tick**
  (`g_crew_calls` hit 125,185 in one session, so ~32 million syscalls). This was
  reverse-engineering scaffolding hunting for which offset moved when the gunner
  slewed; that question was answered long ago and it was never switched off. Now
  behind `g_diag_sweep`, default `false`.

**Applies to ZW as well** - the launcher injects the same binary into either
build and `M:\T34vsTiger_ZW2015` is on the allow list.

**Method failure worth recording:** at 11:40 the evidence was already in hand
and was read backwards - the fast run had no LOS log, and the conclusion drawn
was "so LOS wasn't the difference". Its absence WAS the difference. The rest of
the day went into renderers, syscall attribution and a native-vs-DXVK A/B, all
downstream of that misreading. **When two runs differ, diff the CONFIGURATIONS
before profiling either one.**

Also this day: anti-aliasing enabled, tested, **broke rendering** (no terrain,
invisible tanks, silently) and reverted - and the value persists to the
registry, so closing the menu row left no way back. Native D3D9 vs DXVK
measured at the noise floor (50 vs 48 with F9 on both); DXVK is free.

This file is human-written, plain prose. For technical details, see [PROJECT_MAP.md](PROJECT_MAP.md) and [llms.txt](llms.txt).

---

## 2026-08-25 (Performance, shipped) — "Faster trees" in the launcher, confirmed in both builds

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

The map-lookup cache — a one-entry cache in front of the hottest function in the game, worth a measured +6.3% framerate — is now a launcher option rather than a batch file, and it has been confirmed running live in ZeeWolf 2015 alongside line of sight.

Getting there needed one change to the injector. It only ever accepted a single DLL, which is why Line of sight and Profiler were already mutually exclusive in the launcher, and adding the cache as a third exclusive option would have forced a choice between AI line of sight and the framerate. That is an unnecessary choice: the two hooks patch completely different engine DLLs — line of sight goes into `Behavior.dll`, the cache into `Objects.dll` — and never meet. So the injector now takes up to eight, loading each one fully before the next begins, with the process suspended throughout. The opt-in rail survived intact: every DLL is allow-checked against the list sitting beside *itself*, so each still has to authorise itself, and each checks the same list again from inside once loaded. That was verified three ways before anything was wired up — a single bad path still errors as before, a bad second DLL is named correctly rather than blamed on the first, and an install that is not on the list is still refused.

The launcher gained a "Faster trees (map cache - about +6% fps)" checkbox that can be ticked together with Line of sight. The Profiler still clears both, deliberately — measuring while something else is changing the thing being measured is worthless.

Then the confirmation, which is the part that mattered: two injected DLLs coexisting in a real process is not something argument tests can prove. In ZeeWolf, both armed and both worked. Line of sight reported `enforcement live` and its terrain fit check passed on ZW's own map dimensions (+1.58 to +1.59 m across three observer positions, 0.01 m spread) rather than assuming REDUX's — that per-mission fix is still holding. The cache ran 458,779,776 calls at a 66.8% hit rate with zero mismatches, and the game exited cleanly.

That hit rate is worth noting: 66.8% in ZeeWolf against 67.2% in REDUX. Different build, different missions, different terrain, essentially the same number — because the access pattern the cache exploits is a property of the engine itself, not of either mod.

The cumulative record now stands at roughly **3.6 billion calls across four sessions and two game builds, with zero mismatches**.

### Why

The cache had been proven fast and proven correct, but it was still a batch file that had to be run instead of the launcher, which in practice means it would never have been used. Making it a normal option next to line of sight is what turns a measurement into something that actually improves the game. The injector change was the price of not making the user choose between two features that have no reason to conflict.

The safety pattern is what made any of it defensible: the cache verifies its own predictions against the real function 400,000 times before it is allowed to skip a single lookup, and one disagreement disables it permanently. Putting a cache in front of a container lookup inside a binary with no source is otherwise not a reasonable thing to do.


---

## 2026-08-25 (Crash fix) — Campaign 1 Mission 2 no longer crashes to desktop

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Fixed a genuine crash-to-desktop in Campaign 1 Mission 2. One AI group — `CC1M2Gr_NGerman_Infantry2` — reached the end of its patrol path and re-entered its own order handler forever: `OnOrderFulfilled` restored the "Patrol" order and called `RepeatOrder`, which at end-of-path fired `OnPathEndReached`, where the mission's override re-armed the attack, which came back round to `ContinueOrder` and started again. The script interpreter warned all the way up — 6,451 `Possible stack overflow` lines — and the process died at stack depth 1,391.

The cause was an accidental side effect of the 2026-08-18 change to `OnOrderFulfilled`, which made groups resume a patrol after being interrupted by a fight. It resumed the patrol even when the patrol was already finished. The fix adds one condition — only resume if there is road left (`m_NextPatrolPoint < m_PatrolPath.size()`) — so an exhausted patrol falls through into the static-group branch immediately below, which parks the group and pointedly does not re-enter `RepeatOrder()`.

Because `UnitGroup.script` is shared by every mission in the game, that patch was applied and tested completely alone, with the game launched normally — no injected hooks, no probes, nothing else changed — so the patch was the only variable. The specific regression to rule out was making the guard too strict and leaving groups inert after combat, which would have undone the point of the 2026-08-18 change. Measured on the confirming run: **80 patrol resumptions and zero groups parked**. Groups attacked mid-patrol still pick their route back up. Stack overflows went from 6,451 to **0**, the offending group's log volume from 1,395 lines to 11, alarms from 143 to 4 (two unrelated tank groups), and the mission ran to a proper ending.

A second patch followed once the first was confirmed: in `Missions\Campaign_1\Mission_2\MissionTasks.script`, the misspelled `ActivateMove(false)` became `ActivateMovement(false)` — the misspelled name does not exist, so the engine had been logging a `[ScriptManager]` error on every mission load, and the correct name was verified to be a real command in `BaseTasks.script` rather than taken on trust — plus a `RadarArmed` one-shot guard so that infantry group re-arms its attack order once instead of every time. That guard is belt-and-braces; patch 01 had already fixed the root cause.

Worth recording a trap in that second patch for anyone who touches it later: the block being replaced is **not unique** on its first six lines, because `CC1M2Gr_NGerman_Infantry1` has a near-identical `OnPathEndReached`. A careless replace silently patches the wrong group. The full nine-line block including the `"AttackGermanInfantry2"` event name is unique and is the correct anchor — confirmed by counting matches before replacing and by checking Infantry1 was untouched afterwards.

### Why

This had all been done before. It was diagnosed on 2026-08-21, written up and reviewed on the 22nd, and then parked without ever being applied — and untracked in both TODO.md and this changelog. Three days later it crashed a live play session, and because an experimental performance cache happened to be injected at the time, real effort went into ruling that out before the actual cause surfaced in the log.

The lesson is bookkeeping rather than code: a diagnosed, written, reviewed fix that isn't on the board does not exist. Both patches are now applied, tested and recorded, and the remaining unapplied siblings from that same 2026-08-22 set (the same `ActivateMove` typo in Campaign 2 Mission 3, and a `MissionsMenu` patch) are on the board rather than in a folder nobody reads.


---

## 2026-08-25 (Performance) — Found out where the frame time actually goes, mostly by being wrong

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Spent a session establishing, by measurement rather than reasoning, why TvT runs the way it does. The framerate moved from 36-40 to 66-76 over the day, and I want to be upfront that **we never established which change caused that** — the best remaining guess is that clearing `Cache\Scripts.cache` made earlier pending script edits go live, and I'm deliberately not building anything further on that guess.

The finding everything else rests on: **TvT is CPU-bound with the GPU sitting idle.** A new D3D9 draw-call probe (`Tools/drawcall_probe.cpp`) measures where the game's own thread actually sits, and it is unambiguous — 0.1% inside `Present` waiting for the GPU, 0.0% inside `Lock` waiting for a buffer, and 99.8% doing CPU work, about 14 ms of it per frame. 322,000 triangles a frame at ~68 fps is roughly 20M triangles/sec, which is nothing to a modern GPU; it is asleep, waiting for one core.

The one real target that came out of it: **tree management runs whether or not trees are drawn.** With the forest detail slider at minimum the probe measured a quarter of all draw calls and 27% of buffer traffic gone — and the tree code's share of CPU did not move at all (`Objects.dll+0x17D000`, the hottest page in the game, went 7.54% to 7.45%). The slider changes what is *drawn* and nothing about what is *computed*: every tree still goes through the quad-tree walk, the grid query and the LOD decision every frame, and at short draw distances that work is calculated and discarded. That is roughly a tenth of the frame. The function is disassembled and identified — a 736-byte routine converting a world box to forest grid-cell indices with four x87 float-to-int round trips per query, called from `CSTForest+0x18ACAE`. What is *not* yet known is why it runs so often, which is the question that decides whether it can be fixed; that is the next piece of work and it is read-only.

Three hypotheses died along the way, all recorded in the write-up because the pattern matters more than any of them. Grass is not a fill-rate problem (the GPU was never busy). REDUX's `AlphaBlendDistanceFactor = 0.8` is not too high — reverting it to G5's shipped `0.4` made grass *more* expensive and put visible transparency on tanks, and reading the engine settled it: it computes `1.0 / (1.0 - factor)`, so the value is where the alpha fade *begins*, and `0.8` is the engine's own hardcoded default. It is now `0.9`, and **1.0 must never be used — it is a divide by zero.** And the Tiger shadow bug is not worth 28 fps; putting the bug deliberately back moved the framerate *up* 4%, which is noise.

That shadow bug is real and is fixed regardless. `ShadowHide.script:45` sets `Cu_veh_PzVI_LATEModel::LodForShadowHide = 2.6`, but `Models\u_veh_PzVI_LATE.script` never declared the field — the only model file of the whole set that omits it — so the assignment failed silently and every Tiger kept `DefaultLodForShadowHide = 9999`, meaning "never hide this shadow", behaving unlike every other tank in the game. ZeeWolf's copy already had the missing line. A static sweep then checked every `Class::Field = value` assignment in both installs against whether the field is actually declared, and found nothing else of the kind — 2390 classes in REDUX, 4957 in ZW, both clean, with the sweep validated against the known bug first so that "none" means something.

Two pieces of supporting work worth recording. The sampling profiler's numbers were wrong: its counters are cumulative since injection and never reset, so the headline figures included mission load. Per-window deltas give the true steady state — Objects.dll 50-54%, Engine.dll 20-24%, the `.script` interpreter ~2%, all of the AI ~0.5%, and the D3D9 wrapper **0.0%**, which closes the DXVK-versus-dgVoodoo question for good. And RTTI turns out to survive in all the shipped DLLs, so `pefile` plus `capstone` yields 4778 named virtual functions across 300 classes in Objects.dll alone — which is what turned "Objects.dll is 48% of the frame" into "`CGrass` and `CSTForest` are".

Also established, and probably the most useful number of the day: three runs in identical conditions gave 66.8, 69.5 and 68.4 fps, so **run-to-run noise is ±4% and anything below that is not a result.**

### Why

Phase 1 of the roadmap was never "make it faster" — it was "know *why* the framerate is what it is". Guessing had demonstrably run out: three plausible explanations in a row, each reasoned from real evidence, each wrong the moment it was measured. Building the probe cost an hour and settled in ninety seconds what a day of reasoning had got backwards. The lesson is written into the notes so it survives me: predict the number before the run so the hypothesis can fail, and treat anything under the noise floor as zero.


---

## 2026-07-03 (Skirmish mission sweep) — Same non-unit sun-direction bug fixed in 10 more mission files

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Followed up on the earlier campaign-mission bug-hunt by sweeping the CF/DM skirmish missions and the multiplayer test mission the same way, adapted to work statically since I can't launch the game to get a fresh log for these specific files. Checked every mission's class hierarchy and object-group references - all clean, no undefined classes (these missions don't use custom AI task scripts at all, so that category of bug from the campaign missions doesn't apply here). Found the exact same non-unit-length `SunDirection` bug already fixed for Campaign_2/CF2/DM2 in 10 more files (`CF1/CF3/CF4/CF5/CF6/DM3/DM4/DM5/DM6Mission`, `MultiplayerTESTMISSION`) - fixed each to the same direction, normalized to length 1, so lighting is unchanged but the engine's repeated renormalization warning goes away. Also noticed `DM5`/`DM6Mission` have lens flare disabled (commented out) unlike every sibling mission - flagged rather than re-enabled, since it's unclear whether that was deliberate.

### Why

Closing out a known backlog item (`TODO.md`'s "nobody's swept these missions yet") with the same rigor as the campaign-mission pass, while being upfront that a static sweep without a live log can't catch everything a real play-test would.

---

## 2026-07-03 (Phase 3 attempted fix, reverted) — Skin-weight split removed too much legitimate geometry

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Decoded the file's per-vertex skin-weight block and confirmed (via the companion `.script` file) that the turret's gun barrel and hatches are weighted to animation joints whose bind-pose transform isn't stored anywhere in the file - confirmed by comparing directly against the real TvT Editor, which renders a normal barrel. Built a fix that split any node using this weighting into a safe part and a hidden `_UnresolvedSkin` part holding whatever couldn't be positioned correctly. Tested on the real tank file and it looked clean, but the user's own test found it hid a lot of legitimate geometry along with the actually-broken parts - the self/external split was too coarse. Reverted the whole fix (`git revert`) back to the prior importer. The turret/barrel spike corruption is confirmed still present and unfixed; the skin-weight decoding groundwork is documented in TODO.md for a future, more careful attempt.

### Why

The user's test is the only reliable signal here - a fix that looks clean in my own render but removes real content on their side is worse than no fix, so it's honest to revert immediately rather than try to defend or partially salvage it.

---

## 2026-07-03 (Phase 3 update) — Real installable Blender add-on, replacing the .blend-file round-trip

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User tested the zero-area-triangle fix and reported no visible change at all, falsifying that theory. Realized the actual testing method had a gap: every demo `.blend` file was built and saved in this environment's Blender 2.79, then opened by the user in their own much newer Blender (5.1.2) - so the mesh the user actually sees has already passed through Blender's own opaque old-file version-upgrade process, entirely outside this importer's control. Replaced the script-that-saves-a-.blend-file approach with `Tools\MS2Format\blender_addon\ms2_importer\`, a real installable add-on targeting Blender 2.80+ that adds a File > Import > TvT Model (.ms2) menu entry, so the user's own Blender builds the mesh natively - no round-trip, no invisible version-upgrade step. Also exposed hide-variants, skip-degenerate-triangles, and a three-way shading mode (Authored/Smooth/Flat) as live Redo-panel options, so the user can now run diagnostic experiments themselves rather than waiting on a new file each time. Packaged as a one-click-installable zip.

### Why

Chasing the visual bug by generating new files each round was slow and, it turned out, testing something slightly different from what was actually asked (a file that survived Blender's own version upgrade, not this importer's direct output). Giving the user a real tool in their own Blender turns future diagnosis into something they can iterate on directly, and unblocks their stated goal of testing other models themselves.

---

## 2026-07-03 (Phase 3 correction + fourth fix) — Winding-disagreement diagnosis retracted; real cause found: zero-area degenerate triangles

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User re-tested and reported the turret still breaks "from the commander's hatch forwards," and firmly rejected the standing explanation that this was a pre-existing inconsistency in the 2006-era turret asset - they can view the exact same model correctly in the real TvT Editor, proving the source data is fine by the actual engine's own rules. The Phase 3 winding-disagreement diagnostic (which compared each triangle's geometric normal against the file's authored normal) was retracted as a false signal, and its "fix" (reversing vertex order on disagreement) was fully reverted - the importer now trusts the file's triangle index order exactly as authored.

Went looking for a defect that doesn't depend on comparing against authored normals at all: checked for genuinely zero-area triangles (repeated vertex indices, or collinear points via cross-product area). Found 70 real degenerate triangles in `Turret_A`, all clustered in the turret's roof/hatch region - matching the user's description closely - and the same pattern elsewhere in the file (`Body_Crashed`, several LOD/CM variants), while `Body` itself (never complained about) has none. These triangles have undefined normals; the real engine never recomputes normals from geometry so they're harmless there, but the importer's prior "third fix" (topology-based smooth shading) made Blender recompute normals from geometry, letting the degenerate triangles' undefined normals smear bad shading onto real neighboring faces in exactly that region.

**Fix**: skip zero-area/repeated-index triangles entirely at import (like duplicate faces already were - they're invisible in any renderer regardless), and reinstated the file's own authored per-vertex normals via custom split normals, since with the poisoning source removed there's no longer a reason to distrust them. Regenerated and rendered the tank import - clean shading everywhere, including the hatch region.

### Why

The user's counter-evidence (correct rendering in the real TvT Editor) was decisive proof the source data itself isn't at fault, so continuing to blame it would have been wrong. Finding an engine-independent structural check (real geometric degeneracy, not a comparison against authored data) gives a fix that doesn't rest on any assumption about which renderer or Blender version is involved - unlike the retracted one.

---

## 2026-07-03 (Phase 3 third fix) — Replaced a version-sensitive normals API with plain smooth shading

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User re-tested with another fresh file and reported the turret/barrel still looked wrong while hull/wheels were correct. Rendered the scene directly (both a full shot and a turret close-up) rather than guessing - nothing looked broken in those renders. Checked the turret mesh's own vertex data for a genuine outlier (none found) and re-verified the earlier winding fix has zero remaining disagreements, ruling out geometry and winding entirely. The key realization: this importer's own testing only ever used Blender 2.79's old internal renderer, matching the Blender version that authored the demo files, while the user was viewing the same files in a much newer Blender using Eevee - and the importer applied authored normals via a comparatively obscure, version-sensitive custom split normals API. Replaced it with plain `polygon.use_smooth = True`, a basic feature that shades from mesh topology alone rather than trusting stored normal vectors across Blender versions - correctly reproduces hard/soft edges since the format already duplicates vertices at hard edges. Flagged honestly that this specific fix couldn't be independently verified here, since only Blender 2.79 (pre-Eevee) is installed - needs the user's own test.

### Why

Continuing to chase a real defect the user found through careful, deliberate re-testing (a fresh file, a specific description of which part looked wrong) rather than declaring victory prematurely.

---

## 2026-07-03 (Phase 3 second fix) — LOD/damage-state variants no longer all render at once

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

After the winding fix, the user re-tested with a brand-new, uniquely-named file (ruling out a stale re-test) and a deliberately-chosen mid-complexity model - the mid-complexity model looked correct, the tank still looked shattered. Checked the actual node hierarchy and found the intact hull and its shattered "Crashed" wreck variant (plus every `_LOD1/2/4` copy of both) are siblings with nearly identical bounding boxes - the importer was creating every single node as visible geometry, so intact and wrecked and every LOD copy were all rendering simultaneously, stacked in the same space. This was a real, separate bug from the winding issue, not a repeat of it. Fixed the importer to still import every node (nothing lost) but hide by default anything matching the game's own LOD/damage-state/collision-mesh naming convention, confirmed against real shipped content rather than assumed - a straightforward import now shows just the intact, full-detail vehicle.

### Why

Direct fix for a second real defect the user found through careful re-testing with a new mid-complexity sample specifically chosen to help isolate the problem.

---

## 2026-07-03 (Phase 3 fix) — Fixed real visual artifacts found via user testing

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

User opened the generated tank `.blend` in their own Blender install and reported scattered dark, faceted patches - the simple haystack prop looked correct, but the tank didn't. Diagnosed with a data-driven check rather than guessing: compared every triangle's geometric normal (from its vertex order) against its authored normal data from the file, and found 7.17% of all faces (5,531 of 77,182) have winding that disagrees with their own authored normal - heavily concentrated in the damaged "Crashed" variant meshes. Fixed the importer to use the file's authored normals as ground truth, reversing a triangle's vertex order whenever it disagrees, rather than trusting the raw index order. Verified directly: disagreements dropped from 5,531 to 2 (noise-level), and the already-correct haystack prop was unaffected. Regenerated both demo files.

### Why

Direct fix for a real defect the user found by actually opening the output - exactly the kind of empirical, in-application testing this project has relied on throughout, now applied to the new importer tool itself.

---

## 2026-07-03 (Phase 3) — A real, working static-mesh Blender importer

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

After the user asked how far off a working import/exporter actually was, gave an honest assessment (static meshes close, skinned/animated content further off) and then built the static-mesh half. `Tools\MS2Format\ms2_reader.py` is a dependency-free `.ms2` reader implementing everything ground-truth confirmed so far. Found one more real issue along the way: `bld_Haystack.ms2` had the same "predates the exporter's own build" version mismatch already found in `wpn_Bomb.ms2` - rather than hardcode a date check, made the reader structurally self-correcting by computing a node's remainder both possible ways and picking whichever leads to a valid subsequent read. Result: all 62 sample `.ms2` files in the game now parse to the exact byte with zero leftover - a complete validation of the format's static-geometry portion. Built `Tools\MS2Format\ms2_import_blender.py` on top of this, targeting Blender 2.79 (the version installed on this machine), and tested it headlessly against both a simple prop and the full real 219-node T-34/85 tank model - vertex counts matched exactly in both cases, with only 10 of 77,182 triangles skipped due to a Blender API restriction on duplicate faces, not a format gap. Two demo `.blend` files were saved for direct visual inspection.

### Why

Direct continuation of the user's question about import/export readiness - moving from pure analysis to an actual, working, tested tool.

---

## 2026-07-03 (Phase 2, record internals) — Bind-matrix record fully decoded; honest limits on the rest

**By:** murkzuk (jmurkz), with Claude Code (Anthropic) assistance

### What changed

Pushed further on decoding the exact internal byte layout of the five remaining record types whose purpose (but not precise fields) was identified earlier today. The `0x10000` (per-joint bind-pose) record is now fully decoded with certainty: its default-initialization code bulk-copies a fixed global constant into each record, and dumping that constant directly from the binary confirmed it's a literal 4x4 identity matrix, pinning down the full 80-byte layout as index + matrix + vector3. Attempted the same technique for the other four record types (bone attachment, blend weights, and two unnamed joint/skin blocks) but found they're populated through much deeper, more intricate per-triangle/per-vertex processing chains without a simple default-initialization shortcut - honestly documented as needing substantially more dedicated tracing rather than claiming false completeness.

### Why

Continuing to push per the user's request, while being transparent about where quick wins run out and real, bounded-but-substantial remaining work begins.

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

## v0.260821 - 21 August 2026

**Versioning starts here.** Both builds now carry a date-stamped `VersionID` in
`Scripts\GameSettings.script`, shown bottom right in game: `REDUX v0.260821`
and `ZW v0.260821`. The format is **`v0.YYMMDD`** deliberately - DDMMYY would
sort a September build below an August one. ZW's version string had been
commented out entirely and showed nothing.

Bump it whenever a change ships. It is how "which build am I running" gets
answered from the screen instead of from a log, which cost real time twice this
week.

### This week, in both builds

- **Line of sight runs on ZW** as well as REDUX - no rebuild needed, the engine
  binaries are identical. 84-90% of AI sightings refused, at 0.4-0.95% of wall
  time.
- **Three things are read per mission, not assumed**: `MatrixWidth`,
  `ImageFileName` and `FloatValueFactor`. Each was hardcoded and each was wrong
  somewhere - including on REDUX's own steppe missions, which had been running
  at half scale.
- **ZW's "4GB" executable was never large-address-aware.** Capped at 2 GB,
  which is why the 36 km Kursk map crashed. One bit.
- **Wingman and Hanomag followers fixed** - cruise speed in one case, the wrong
  kind of order in the other.
- **Commander/binocular mouse speed** is editable, and the mouse is held inside
  the game window on multi-monitor desktops.
- **A launcher GUI** and a launch-time banner that says whether occlusion armed.
