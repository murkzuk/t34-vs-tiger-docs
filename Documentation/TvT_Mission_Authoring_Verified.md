# TvT mission authoring — verified reference

Written 2026-08-18 after a full day of getting this wrong. Every claim here is
either taken from **G5's own `TvsT Editor Manual.pdf`** or verified against
shipped mission files. Where something is inferred rather than documented, it
says so.

**Read this before touching a mission.** Most of a day was spent reverse-
engineering behaviour that ten pages of the original manual simply state.

---

## The rule that would have saved the day

> **TvT missions are declarative. Routes, triggers, detection and reactions are
> properties in `Content.script`, not code in `MissionTasks.script`.**

An AI-generated Berezov mission drove everything from task-script calls
(`SetOrder_MoveToEx`, `SetEnemyReactionType`) and omitted the declarative layer
entirely. It looked plausible and never worked. Six wrong diagnoses came from
trying to fix the code instead of noticing the missing properties.

**Before diagnosing any mission, run this comparison against a shipped mission:**

```bash
for m in Campaign_1/Mission_1 Campaign_2/Mission_4 YOUR_MISSION; do
  printf "%-26s %3s objects %3s Task %3s BehRadarMask %s GroupEnemyReaction %s Path\n" "$m" \
    "$(grep -c '"GameObject"'        Missions/$m/Content.script)" \
    "$(grep -c '\["Task",'           Missions/$m/Content.script)" \
    "$(grep -c 'BehRadarMask'        Missions/$m/Content.script)" \
    "$(grep -c 'GroupEnemyReaction'  Missions/$m/Content.script)" \
    "$(grep -c '"Path"'              Missions/$m/Content.script)"
  ls Missions/$m/PositionWatchers.script >/dev/null 2>&1 || echo "    NO PositionWatchers.script"
done
```

Any zero against a shipped mission's non-zero is a missing mechanism, not a bug
to debug.

---

## 1. Unit — `Content.script`

```
[
  "PlayerTank_1",
  "GameObject",
  "CTankT34_76_42Unit",
  new Matrix( ... , X,  ... , Y,  ... , Z,  0,0,0,1 ),   // col 4 = position
  [
    ["BehRadarMask", [["ENEMY", "MainMesh"], ["FRIEND", "INVISIBLE_ON_RADAR"]]],
    ["Task", "CC1M1Tsk_USSR_TanksRadar"],
    ["Affiliation", "FRIEND"],
    ["Number", "22_13"]
  ]
]
```

- **`BehRadarMask`** — per-unit detection mask. What the unit's vision considers.
  `ViewProbabilityByMask` and `PermanentMaskChecks` operate on this; without it
  the mask terms of the vision model run on defaults. Most common shipped value
  is the one above (54 uses); `[["FRIEND","MainMesh"],["NEUTRAL","AIR"]]` (16) is
  used for AA and similar.
- **`Task`** — the unit's class in `MissionTasks.script`. If no special behaviour
  is needed use a base class: `CBaseAITankTask` (tanks), `CBaseAISAUTask` (SPGs),
  `CBaseAIBtrTask` (APCs), `CBaseAITask` (everything else).
- **`Affiliation`** — `FRIEND` / `ENEMY` / `NEUTRAL`.
- **`IsManual` / `IsPlayer`** — true only for the player's tank, one per map.
- **`HitPoints`** — affects buildings, barrels, infantry; **not** vehicles.

## 2. Group — `Content.script`

```
[
  "CC1M1Gr_PlayerTanks",
  "UnitGroup",
  "CC1M1Gr_PlayerTanks",          // control class in MissionTasks.script
  new Matrix( ... ),              // position matrix - irrelevant for a group
  [
    ["Units", ["PlayerTank_1", "PlayerTank_2"]],
    ["Path", ["NP_PP_1", "NP_PP_2", "NP_PP_3", "NP_PP_4"]],
    ["DelayedOrder", false],
    ["Formation", "Column"],
    ["FormationDistance", 17],
    ["MovingSpeed", 8.800000],
    ["FirstOrder", "Patrol"],
    ["CyclePath", false],
    ["GroupEnemyReaction", "ERT_AGGRESSIVE"]
  ]
]
```

- **`Path` + `FirstOrder`** — this is how a group receives a route. **Not**
  `SetOrder_MoveToEx` from the task script.
- **`DelayedOrder`** — the manual: *"Usually set to False."* When true the order
  is parked in `m_DelayedOrder` and only runs when something calls
  `sendEvent(0.0, "GroupName", "PopDelayedOrder", [])`. Shipped missions use true
  66:1 because they trigger from mission events. **A group with `DelayedOrder`
  true and no trigger never moves, and logs nothing.**
- **`CyclePath`** — return to the start and repeat. False means the path ends.
- **`GroupEnemyReaction`** — `ERT_AGGRESSIVE` (27 shipped uses), `ERT_PASSIVE`
  (9), `ERT_FRIGID` (1, ignores the enemy entirely).

## 3. Triggers — `PositionWatchers.script`

Every shipped mission has one. It is how groups are woken up.

```c
class ClosingProof extends CPositionWatcher, CBaseUtilities
{
  final static String Positionable  = "WatcherPoint";     // a named object
  final static Array  ControlPoints = ["MainPlayerUnit"]; // who is watched
  final static Array  RegionDefs    = [600.0];            // radius, world units

  void PointRegionChanged(Component _PositionWatcher, int _Point, int _RegionMask)
  {
    sendEvent(0.0, "CC2M4Gr_AvantGuard76", "StartAttack", []);
    GetMission().ShutdownWatcher(_PositionWatcher);
  }
  void PointRelativeSpeedChanged(Component _w, int _p, float _s) { }
}
```

It must be **registered in `Mission.script`** — the file is not auto-loaded:

```c
Component ClosingProof;                              // member
...
ClosingProof = new ClosingProof();                   // in the constructor
ClosingProof.Initialize(this, "ClosingProof");
```

And the group needs a matching handler:

```c
void StartAttack()
{
  ActivateRadar(true);
  ActivateFire(true);
  SetFormation("CFrontFormation", 50.0, true, true);
  SetEnemyReactionType(ERT_AGGRESSIVE);
  SetOrder_Attack(m_Targets, ERT_AGGRESSIVE);
}
```

## 4. Navpoints

- Create in the Editor: `View > Special objects > Nav Points`, then
  `Create Object() > Special Objects > Navigation Points > Z Axis Cylinder`.
- **Keep spacing tight — roughly 170-180 world units.** Measured: a 34-point
  route at ~180 spacing completed 6 hops; the same route resampled to 8 points at
  ~900 spacing completed only 2-3. The queue advances on `OnLeaderStopped`, so a
  gap the leader cannot cross in one hop stalls the advance **silently**.
- Routes must stay on ground the **router** map calls passable, which is not the
  same as ground that looks open.

## 5. Mission directory (from the manual)

| file | purpose |
|---|---|
| `atmosphere.script` | lighting, fog |
| `content.script` | objects, groups, navpoints — saved by Editor File>Save Level |
| `hmap.raw` | landscape heights |
| `hwater.raw` | water level |
| `mission.script` | main mission file, control scripts, watcher registration |
| `missiontasks.script` | unit/group control classes |
| `routerzone.bmp` | **map of landscape passability** |
| `terrainzone.bmp` | **map of vegetation, roads, surface** |
| `micro.bmp` | microtexture tile placement |
| `positionwatchers.script` | position triggers |
| `worldmatricies.script` | landscape classes, `MatrixWidth/Height`, texture refs |
| `terrain.script` | landscape parameters, forest settings |
| `lnd.tex` | low-res landscape texture |
| `forest.tex` | distant-forest texture — **identical in every mission**, copy it |

**`routerzone` and `terrainzone` are different maps and must not mirror each
other.** Verified: Campaign_2/Mission_4 is 64% forest in `terrainzone` but 93%
open in `routerzone`. `SteppeTemplate` (and Berezov, built on it) has this
inverted — 80% grass visually, 60% forest in the router map — so AI advances die
on ground that looks completely open. Zone indices are fixed numeric codes
(`ZMC_*` in `Scripts\Common\BaseZone.script`); match by index, never by colour.

## 6. Strings — do not use `Locale\eng.locale`

`getLocalized("SectionName", "Key")` reads **`Resources\*.rsr`**, not
`Locale\eng.locale`. Sections added to `eng.locale` produce
`[Locale] There is no section [X]` even though they are visibly in the file.

For a mission without an `.rsr`, use literal strings:

```c
class CMyMission_Strings extends CCommonStrings
{
  final static WString MissionName = L"Operation Citadel: Berezov";
}
```

The menu reads the name via
`getStaticClassMember(<MissionClass> + "_Strings", "MissionName")`.

## 7. Menu registration

`Scripts\Menus\MissionsMenu.script` holds `USSR_Missions` and
`Germany_Missions`. The list renders
`min(GetUserValue("GerCampaign"), array size)` entries, so **appending past the
campaign's mission count makes an entry invisible**. Missions under
`Missions\MyMission\` are absent from these arrays and therefore Editor-only.

## 8. The Editor cannot test AI

`Editor.exe` loads and renders a mission but **never runs the behaviour
classes** — `Radar`, `Task` and `UnitGroup` appear zero times in `editor.log`
against 79 `Router` entries in a real game run. Any AI change must be tested in
the game. Use the Editor's Navigator panel to *view* `routerzonemap`,
`terrainzone` and `microtextures` overlaid on the landscape.

## 9. Cache

`Cache\Scripts.cache` must be deleted for any `.script` edit to take effect.
It cannot be deleted while the game is running. A cold rebuild recompiles ~513
scripts and takes a couple of minutes.

---

## Method notes

- **Read the manual first.** `D:\T34vstiger 2023\TvT manuals\TvsT Editor Manual.pdf`
  is an original G5 document, not AI-generated, and corrected four independent
  wrong conclusions in twenty minutes.
- **Absence of errors is not evidence of success.** `#VehicleBehavior3` was
  accepted by the script compiler with no warning and silently produced a plain
  `CVehicleBehavior` — proven by a live memory census showing zero v3 instances.
  Verify by measurement, not by a clean log.
- **A log line is not a proxy until you know what emits it.** `Maneuver
  destination` was read as "unit is moving"; it is actually combat evasion, fired
  when a unit is shot at.
- **Distinguish shipped-content bugs from missing triggers.** A group logging
  `[ALARM] No orders in group` may simply be waiting for a `PositionWatcher`
  event that the player has not triggered yet.
