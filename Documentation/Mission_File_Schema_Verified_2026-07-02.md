# T34 vs Tiger — Mission File Schema (Verified)

**Status:** Draft for review. Every pattern below is quoted or paraphrased from an actual file in the game install, with a file:line reference, verified by direct inspection during the 2026-07-02 Claude Code session (see `CHANGELOG.md` for that session's fix list). Nothing here is inferred from training-data knowledge of unrelated engines.

**Relationship to `TVT_Mission_Script_Format_Complete_Reference GOLD.md`:** That document is the larger, older reference and its unit/group/navpoint patterns and MOTID_*/MOSID_* constants were spot-checked against this session's findings and confirmed accurate. This document exists because GOLD explicitly flags the trigger/`PositionWatchers.script` system as "(Further analysis needed)" (GOLD line 1008) — that gap is filled here, plus the victory-condition mechanism, which GOLD doesn't trace end-to-end. Read GOLD first for broader context; treat this as a supplement, not a replacement.

**Worked examples used throughout:** `Missions\Campaign_1\Mission_3\` (the most heavily-scripted single mission in the game — full campaign objective chain, duck-blind ambush trigger, retreat trigger, speed-matching AI) and `Missions\Campaign_2\Mission_5\` (where I added 3 missing unit-group classes this session — a good "before" reference for what happens when a group has no Task). Also `Missions\MyMission\Mission1\` for the simplest possible victory-condition pattern.

---

## 1. File Structure

Each mission is a folder under `Missions\<CampaignFolder>\<MissionFolder>\`. Not every file is present in every mission — `Mission_3` has all of them; simpler missions omit what they don't need.

| File | Role | Verified in |
|---|---|---|
| `Mission.script` | The mission's main class (`extends CSPMission`). Constructor wires up terrain/atmosphere/sky, declares `m_MissionObjectives`, and hosts the event handlers that drive objective completion and mission end (`OnObjectEnterNavPoint`, `StartMission`, etc.). | `Campaign_1\Mission_3\Mission.script:10` (`class CC1M3Mission extends CSPMission`) |
| `Content.script` | The mission's object placement table — every unit, unit group, and navpoint in the level, as one big array of array-entries. See §2. | `Campaign_1\Mission_3\Content.script:16` (`class CC1M3Content`) |
| `MissionTasks.script` | AI behavior classes for unit groups (`extends CBaseUnitGroup`) and their order-queue tasks (`extends CBaseAITankTask` etc.), plus any mission-wide utility mixins. | `Campaign_1\Mission_3\MissionTasks.script:344` (`CC1M3RussianPanzerGroup1Task extends CC1M3Broken, CC1M3OnUnreacheableUnitProcessingTask`) |
| `PositionWatchers.script` | Proximity/distance-based triggers. See §3. | `Campaign_1\Mission_3\PositionWatchers.script` (whole file) |
| `Mission<Cx>M<x>Strings.script` (e.g. `MissionC1M3Strings.script`) | A `extends CCommonStrings` class whose fields are all `getLocalized("SectionName", "Key")` calls — the mission's briefing/objective text pulled from the locale system. See §4. | `Campaign_1\Mission_3\MissionC1M3Strings.script:12` (`class CC1M3Mission_Strings extends CCommonStrings`) |
| `Atmosphere.script` | Lighting/sky config (`SunDirection`, `AmbientLight`, etc.) — see the 2026-07-02 CHANGELOG entry for the `SunDirection` unit-vector bug found in several of these. | `Campaign_2\Mission_4\Atmosphere.script` |
| `Terrain.script` | Terrain/heightmap wiring. Pairs with the `hmap.raw`/`hwater.raw`/`*.tex`/`*.bmp` binary assets in the same folder. | — |
| `WorldMatricies.script` | World-space transform layer registration (terrain/router/microtexture layer names) — referenced by `SetMissionWorldMatrices()` in `Mission.script`. | `Missions\MyMission\Mission1\Mission.script:67` |
| `C<x>M<x>LensFlare.script` (optional) | A mission-specific `extends CLensFlare` subclass overriding sun-flare visuals. Only present when a mission wants non-default flare behavior — see the `SunAlpha` base-class fix in `Common\LensFlare.script` from the 2026-07-02 session, which was previously only patched into this one file for Mission_3. | `Campaign_1\Mission_3\C1M3LensFlare.script:10` (`class CC1M3LensFlare extends CLensFlare`) |
| `vssver.scc` | Leftover Visual SourceSafe metadata from G5's original toolchain. Not read by the game; safe to ignore. | — |

**Naming convention:** the mission's class-name prefix (`CC1M3`, `CC2M5`, `CF2`, `DM2`, `CMission1`, etc.) is used consistently as a namespace prefix across every class and object ID inside that mission's files — group names, task names, navpoint names, string-section names. This convention is exactly what broke in the CC1M3 typo bug: `Missions\Campaign_1\Mission_4\MissionTasks.script` and `Mission_5\MissionTasks.script` had 7 classes declared `extends CC1M3, ...` where the real shared helper is `CC1M3Broken` (defined once in `Mission_3\MissionTasks.script:56`) — a dropped suffix, not a different naming scheme.

---

## 2. Unit Placement Syntax (`Content.script`)

The whole file is one big `Array` (assigned to a field like `m_ObjectList` inside a class named `C<x><x>Content`), where every element is itself an array with this shape:

```
[
  "<ObjectID>",       // unique string ID for this object within the mission
  "<ObjectType>",     // one of: "GameObject", "UnitGroup", "NavPoint", "Atmosphere", ...
  "<ClassName>",      // the script class to instantiate
  new Matrix( ... ),  // 4x4 world-space transform (rotation + position)
  [ ...properties... ] // array of ["PropertyName", value] pairs, type-specific
]
```

### 2a. A single unit (`"GameObject"`)

```
[
  "CC2M5GroupStug_40_1",
  "GameObject",
  "CSAUStuG40Unit",
  new Matrix(
      0.065048, -0.997375, 0.031823, 4871.114746,
      0.997880, 0.065081, 0.000007, 3272.299072,
      -0.002078, 0.031755, 0.999493, 578.507996,
      0.000000, 0.000000, 0.000000, 1.000000
    ),
  [
    ["Affiliation", "FRIEND"],
    ["Number", "r221"]
  ]
]
```
Verified: `Campaign_2\Mission_5\Content.script:602-616`. `<ClassName>` here (`CSAUStuG40Unit`) is a real unit class from `Scripts\Units\SAUSTUG40Unit.script` — the same class file I fixed the muzzle-effect typo in this session (`CloudEffectId`, `Scripts\Units\SAUSU85Unit.script:105`, for the sibling SU-85 unit).

### 2b. A unit group, with an AI task (`"UnitGroup"`)

```
[
  "CC1M3RussianPanzer_Group1",
  "UnitGroup",
  "CC1M3RussianPanzer_Group1",
  new Matrix( ... ),
  [
    ["Units", ["CC1M3RussianPanzer_Group1_1", "CC1M3RussianPanzer_Group1_2"]],
    ["Task", "CC1M3RussianPanzerGroup1Task"]
  ]
]
```
The `<ClassName>` for a `UnitGroup` entry is conventionally identical to the `<ObjectID>` — the engine expects a script class of exactly that name (`extends CBaseUnitGroup`) to exist. `"Units"` lists the member unit IDs (which must also appear as separate `"GameObject"` entries elsewhere in the same file). `"Task"` names an AI task class (`extends CBaseAITankTask` or similar, defined in `MissionTasks.script`) that governs the group's combat behavior — attack patterns, retreat conditions, targeting priority.

### 2c. A unit group **without** a task

```
[
  "CC2M5GroupStug_40",
  "UnitGroup",
  "CC2M5GroupStug_40",
  new Matrix( ... ),
  [
    ["Units", ["CC2M5GroupStug_40_1", "CC2M5GroupStug_40_2"]]
  ]
]
```
Verified: `Campaign_2\Mission_5\Content.script:587-600`. No `"Task"` entry. **This is the pattern that was broken this session** — `Content.script` referenced `CC2M5GroupSU85`, `CC2M5GroupStug_40`, and `CC2M5GroupRusSoldiers` by name, but no matching `class CC2M5GroupSU85 extends CBaseUnitGroup { }` etc. existed anywhere in `MissionTasks.script`, so the engine logged `[UnitGroup] script host "..." was not created` and the member units loaded as standalone, un-coordinated objects. Fixed by adding minimal stub classes (`Missions\Campaign_2\Mission_5\MissionTasks.script`, appended at end of file) — matching the pre-existing pattern of `CC2M5Group1T_IV`/`CC2M5Group2T_IV` in the same file, which are also bare `extends CBaseUnitGroup { }` with no custom Task. **A group without a Task class still loads and can receive generic move/attack orders (confirmed via `execution.log`: `SetFormation`, `Maneuver destination`, and units taking damage after the fix), but it won't have mission-specific combat logic (retreat thresholds, target priority, etc.) the way a group with a real Task class does.**

### 2d. A NavPoint

```
[
  "NP_PlayerTanks_PP_1",
  "NavPoint",
  "CZAxisCylNavPoint",
  new Matrix( ... ),
  [
    ["Range", 3.000000]
  ]
]
```
`"Range"` is the trigger radius in meters. NavPoints are read by `OnObjectEnterNavPoint`/`OnObjectLeaveNavPoint` in `Mission.script` (see §3b) and by `PositionWatcher` classes (see §3a), which reference them by `<ObjectID>` string.

---

## 3. Trigger Types

There are three distinct trigger mechanisms in this engine, used for different purposes. GOLD doc marks this area "(Further analysis needed)" — the following is traced end-to-end from `PositionWatchers.script` and `Mission.script` source.

### 3a. Position Watchers — continuous proximity/distance monitoring

A class in `PositionWatchers.script` extends `CPositionWatcher, CBaseUtilities`. It's registered from `Mission.script`'s constructor or an event handler like:
```
GetMission().CC1M3PosWatchDB_RusPz_Gr1 = new CC1M3PosWatchDB_RusPz_Gr1();
GetMission().CC1M3PosWatchDB_RusPz_Gr1.Initialize(GetMission(), "CC1M3PosWatchDB_RusPz_Gr1");
```
(Verified: `Campaign_1\Mission_3\MissionTasks.script:1220-1221`.)

The watcher class declares:
- `final static String Positionable` — the object being watched *from* (usually a NavPoint or a unit).
- `final static Array ControlPoints` — the list of object IDs being watched *for distance to* `Positionable`.
- `Initialize()` — calls `CPositionWatcher::Initialize()`, fetches the objects by ID via `GetMission().GetObject(...)`, and sets the polling interval with `SetUpdatePeriod(ms)`.
- `Update(Component _Watcher)` — called every `UpdatePeriod` ms. Reads `_Watcher.GetPointInfo(index)` per control point (returns an `Array` with `INDEX_Distance`, `INDEX_Speed`, `INDEX_RegionMask`) and calls `PointRegionChanged(...)`.
- `PointRegionChanged(...)` — where the actual trigger logic lives: distance comparisons, `sendEvent(...)` calls, `ChangeMoveSpeed(...)`, `SetEnemyReactionType(...)`, `GetMission().ShutdownWatcher(...)`.

Four distinct uses of this pattern exist in `Mission_3` alone (`PositionWatchers.script`), each a different trigger *purpose*:
1. **Speed-matching AI** (`CC1M3PlayerUnit_RussianPanzer_Group1/2`, lines 13-224) — continuously adjusts a friendly group's movement speed based on distance to the player, so they arrive together. Not a one-shot trigger; runs every 3 seconds for the whole mission.
2. **Ambush activation** (`CC1M3PosWatchDB_RusPz_Gr1/2`, lines 229-357) — one-shot: when a unit gets within 400m, calls `GetMission().ActivateDuckBlind()`, sets a flag, and shuts down both watchers (`ShutdownWatcher`) so it only fires once.
3. **Enemy-reaction escalation** (`CC1M3DistanceForAttack`, lines 362-444) — two-tier distance trigger: at 200m, stops all other position watchers (`ShutdownWatchers("God")`) and sets a group speed; at 70m, sets `ERT_DEFENSIVE` reaction type and shuts itself down.
4. **Retreat trigger** (`CC1M3PW_DistanceForBTRRetreat`, lines 449-475) — simplest form: no `Update()` override at all (uses the base class's default per-tick check against `RegionDefs`), and `PointRegionChanged` just fires `sendEvent(0.0, SOID_MissionController, "StartRetreat", ["Vysochany"])`.

### 3b. NavPoint enter/leave — discrete zone crossing

`Mission.script` (or `CBaseUtilities`-derived classes) implements:
```
void OnObjectEnterNavPoint(String _NavPointID, String _ObjectID)
{
  if (_NavPointID == "NavPoint_RussianGroup1_DuckBlind")
  {
    if (_ObjectID == "MainPlayerUnit")
    {
      SetObjectiveStatus(1, MOSID_Completed);
      ...
    }
  }
}
```
Verified: `Campaign_1\Mission_3\Mission.script:303-319`. This fires once per (navpoint, object) pair, when that object's collision volume enters the NavPoint's `"Range"` radius (§2d). `OnObjectLeaveNavPoint` is the exit-side counterpart. This is the mechanism behind both objective completion (§4) and the simplest victory-condition pattern (§5).

### 3c. Scheduled / chained events (`sendEvent`)

Not a "trigger" in the zone-based sense, but the connective tissue between all the above: `sendEvent(<delaySeconds>, <targetID>, "<EventName>", [<args>])` queues a named event to fire on a target object after a delay (0.0 = next tick). Used to chain trigger consequences — e.g. `CC1M3PW_DistanceForBTRRetreat`'s `PointRegionChanged` doesn't retreat units directly; it sends a `"StartRetreat"` event to `SOID_MissionController`, which is presumably handled elsewhere (in `MissionTasks.script` or the base mission controller) to actually issue the retreat orders.

---

## 4. Objective Definitions

Declared in `Mission.script` as a field on the mission class:

```
static Array m_MissionObjectives = [
  [MOTID_Primary,   CC1M3Mission_Strings::Objective01, MOSID_InProgress, true],
  [MOTID_Secondary, CC1M3Mission_Strings::Objective02, MOSID_InProgress, true],
  [MOTID_Primary,   CC1M3Mission_Strings::Objective03, MOSID_InProgress, false]
];
```
Verified: `Campaign_1\Mission_3\Mission.script:21-23`. Each entry is a 4-tuple: `[Type, StringRef, InitialStatus, InitiallyVisible]`.

- **Type** — `MOTID_Primary` or `MOTID_Secondary` (constants defined in `Common\Mission.script`, base class `CMission`). **Only `MOTID_Primary` objectives gate mission completion** — see §5.
- **StringRef** — a reference to a field on the mission's `Cx<x>Mission_Strings` class (§1), which itself is `getLocalized("MissionC1M3", "Objective01")` — the actual display text comes from the locale system (`Locale\eng.locale` / `eng.tsv`), keyed by mission-name section.
- **InitialStatus** — one of `MOSID_InProgress` (0), `MOSID_Completed` (1), `MOSID_Failed` (2), `MOSID_FullCompleted` (3). Defined `Common\Mission.script:64-67`.
- **InitiallyVisible** — boolean; objective #3 above starts hidden (`false`) and gets revealed mid-mission via `SetObjectiveVisible(2, true)` once objective #1 completes (`Campaign_1\Mission_3\Mission.script:297`) — a common pattern for objectives that only make sense to show after an earlier stage.

**Objectives are addressed by array index, not by name**, in every call site: `SetObjectiveStatus(0, MOSID_Completed)`, `SetObjectiveVisible(2, true)`, etc. — the index is positional within `m_MissionObjectives`. This is fragile if the array order ever changes without updating call sites, though I found no instance of that bug in this session.

**The `MissionTest` locale-orphan case** (from the 2026-07-02 session) is the degenerate version of this pattern: `Missions\MyMission\Mission1\MissionTestStrings.script` declares a `CMission1_Strings` class with `Objective02`/`Objective03` fields pointing at `getLocalized("MissionTest", ...)`, but `Missions\MyMission\Mission1\Mission.script`'s own `m_MissionObjectives` array is empty (`Array m_MissionObjectives = [ ];`) — the strings class exists but the mission never actually wires it into an objectives array. Confirms `MyMission\Mission1` is unfinished prototype content, not a live objective chain.

---

## 5. Victory Conditions

Two patterns exist, depending on mission complexity. Both bottom out in the same base-class method (`Common\Mission.script`, class `CMission`).

### 5a. Simple / direct (`MyMission\Mission1`)

```
void OnObjectEnterNavPoint(String _NavPointID, String _ObjectID)
{
  if (_ObjectID == "MainPlayerUnit")
  {
    sendEvent(1.0, getIdentificator(this), "CloseMission", [MOSID_Completed]);
  }
}
```
Verified: `Missions\MyMission\Mission1\Mission.script:106-112`. No objective-tracking at all — reaching a single NavPoint directly schedules `CloseMission(MOSID_Completed)` one second later. Appropriate for a minimal test mission; not how any real campaign mission in this game is built.

### 5b. Objective-driven (every real campaign mission, e.g. `Mission_3`)

No mission script calls `CloseMission` directly. Instead:

1. Mission logic calls `SetObjectiveStatus(index, MOSID_Completed)` (or the `_Objective`-based event handlers `CompleteObjective`/`FailObjective`, `Common\Mission.script:930-946`) whenever a gameplay condition is met — a kill-count reaching zero, a NavPoint trigger, a PositionWatcher condition, etc.
2. `SetObjectiveStatus` (`Common\Mission.script:964-1006`) updates `m_MissionObjectives[_Objective][2]`, then checks `IsMissionCompleted()`.
3. `IsMissionCompleted()` (`Common\Mission.script:1057-1063`) returns `true` **only when every objective with `MOTID_Primary` has status `MOSID_Completed`** — secondary objectives are informational and never block completion.
4. If completed (and the mission hasn't already failed — `m_MissionFailed`), it schedules `sendEvent(m_CompleteDelay, SOID_MissionController, "CompleteMissionStatus", [MOSID_Completed])` (`Common\Mission.script:1003`), which eventually reaches `CloseMission(MOSID_Completed)` (`Common\Mission.script:1125-1174`) — locks input, sets `CEndMissionMenu::MissionStatus`, shows the end-mission screen.

**Failure** works the same way via `MOSID_Failed` and the `m_MissionFailed` flag (`Common\Mission.script:1097,1129` — once set, further `MOSID_Completed` calls are ignored, so a failed mission can't be accidentally "won" by a late-arriving completion event).

**Practical implication for building new missions:** don't call `CloseMission` directly unless you're deliberately writing a minimal test mission. For anything meant to feel like a real campaign mission, define `m_MissionObjectives` with real `MOTID_Primary` entries and drive them to `MOSID_Completed` via gameplay triggers (§3) — the base class handles ending the mission automatically once they're all done.

---

## 6. Open Questions / Not Yet Verified

- `IsMissionFullCompleted()` (`Common\Mission.script:1043-1053`) exists alongside `IsMissionCompleted()` and checks *all* objectives regardless of type, using `MOSID_FullCompleted` — I did not find a call site that distinguishes when this variant is used vs. the primary-only check. Worth investigating before relying on it.
- The `RedTeamObj`/`BlueTeamObj` counting logic at `Common\Mission.script:1028-1036` (keyed by `m_MissionObjectives[i][4]`, a 5th tuple element not seen in any single-player example above) looks multiplayer-specific — none of the single-player missions examined this session use a 5-element objective tuple. Needs a multiplayer mission example to confirm.
- `SOID_MissionController` (used as a `sendEvent` target throughout) — its full method surface wasn't mapped this session; only `"StartRetreat"`/`"CompleteMissionStatus"` were traced.
