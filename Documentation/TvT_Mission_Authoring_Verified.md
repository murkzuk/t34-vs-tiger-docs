# TvT mission authoring — verified reference

Written 2026-08-18 after a full day of getting this wrong, and revised the
same day after two of its own claims turned out to be wrong. Every claim here is
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

```
[
  "RetreatPath_1",
  "NavPoint",
  "CZAxisCylNavPoint",
  new Matrix( ... , X, ... , Y, ... , Z, 0,0,0,1 ),
  [
    ["PositionType", "Ground"],   <- snaps to terrain. Empty string means it does not.
    ["Range", 10.000000]          <- arrival radius
  ]
]
```

**Correction, 2026-08-18.** An earlier version of this document claimed a navpoint
without `["Range", ...]` can never be arrived at, and traced a causal chain through
`UnitGroup.script` to prove it. **That claim was false.** The navpoints in question
already carried `["Range", 10.000000]` at the *end* of their property list; the
"fix" added a second, duplicate `Range` near the top and was mistaken for the cause
of an improvement. Verified against `Content.script.bak_regress`, the backup taken
before that edit.

The same edit also changed `["PositionType", ""]` to `["PositionType", "Ground"]`.
That is the more plausible cause of any real change - an unsnapped navpoint sits at
its authored Z while the ground is elsewhere - but it has **not** been isolated, and
is recorded here as an untested hypothesis, not a finding.

The lesson is the one that keeps repeating in this project: **two changes went in
together and the improvement was attributed to the wrong one.** Change one thing.

### What actually stops a route

The real blocker, measured: **the destination must be routable, not merely passable
at the endpoint.** The engine paths leg by leg and gives up after 20000 A* steps:

```
[Router] Warning! Path Generated in more than 20000 iterations:
[Router]  - To:   [-1, -1]
[CBaseAITask::OnUnreacheable] Unit ... can not move to Vector(689.9, 6947.8, 621.3)
```

Sampling the zone map *at each navpoint* is not enough - every navpoint on the failed
route sat on a passable cell. What mattered was the ground **between** them. The
acceptance test that works:

> Run A* on the router bitmap between every consecutive pair of navpoints, capped at
> **20000 steps**, the engine's own budget. Every leg must solve.

On the failed Berezov route the first leg exceeded the budget and returned nothing.
On a route generated by A* through the largest connected open region, the worst leg
cost **75 steps** - and all four German groups then advanced in lockstep with zero
`OnUnreacheable` in the log.

- Create in the Editor: `View > Special objects > Nav Points`, then
  `Create Object() > Special Objects > Navigation Points > Z Axis Cylinder`.
- **Keep spacing tight - roughly 150-180 world units.**
- Generate routes *from* the router bitmap rather than drawing them and checking
  afterwards. A path A* found is a path the engine can also find.

### Caution: zone-bitmap row order is not settled

`RouterZone_*.bmp` and `TerrainZone_*.bmp` are 8-bit indexed BMPs with a positive
height field, which by the BMP spec means bottom-up rows. Reading them bottom-up
produced a route with zero routing failures, which is strong evidence it is right.
But reading stock `Campaign_1/Mission_3` bottom-up puts none of its 55 navpoints on
road codes, while top-down puts 30 of them on roads - which is what hand-authored
routes should look like.

**These two results disagree and the question is open.** Do not trust a zone-map
sample as ground truth on its own; confirm against the engine's routing behaviour or
the Editor's Navigator overlay.

## 4b. Group orders go inert - three engine-script bugs

All three were found on Berezov by instrumenting `Scripts\Common\UnitGroup.script`
and reading the log. All three are in G5's own code, not in mission content, so they
affect **every** mission - stock campaigns included.

### The shape of the failure

`ContinueOrder()` logs `[ALARM] No orders in group <name> task script` when it finds
`m_CurrentOrder.m_Order == ""` and `PopOrder()` has nothing to restore. A group in
that state never recovers: it repeats the alarm for the rest of the mission and never
moves again. Berezov produced 114 of these before the fixes, then 143 from a
different set of groups afterwards.

### 1. `OnOrderFulfilled()` destroys an order it cannot restore

**This callback is fired by the engine itself.** There is no script-side caller to
guard - which is why grepping `Scripts\` and `Missions\` for it finds almost nothing
and sends you to the wrong place. A day was lost guarding the wrong function.
Original code:

```c
void OnOrderFulfilled ()
{
  m_CurrentOrder.m_Order = "";
  RepeatOrder();
}
```

Measured sequence on a patrolling group:

```
Group ZugFalke: pushing order Patrol; stack size = 1
[FULFILLED] ZugFalke order='Attack' stack=1     <- fine, pops Patrol back
Group ZugFalke: popping order Patrol; stack size = 0
RepeatOrder() : Patrol order to point Advance_01
[FULFILLED] ZugFalke order='Patrol' stack=0     <- fatal
[ALARM] No orders in group ZugFalke             <- x114
```

Fix: if nothing is stacked but the group still holds a patrol path, resume the patrol
rather than destroying it. `SetOrder_Attack` edits `m_CurrentOrder` in place and never
touches `m_PatrolPath` or `m_NextPatrolPoint`, so both are still intact at that moment.

### 2. The same callback strands *static* groups

Groups with no `Path` - dug-in AT guns, defensive platoons - have nothing to fall back
on. `RepeatOrder()` forwards to `ContinueOrder()` (see the `// default forwarding`
comment at the end of `RepeatOrder`), which alarms on every callback.

Fix: hold position, and **do not** call `RepeatOrder()` - there is nothing to repeat.
The group still re-engages later, because `OnEnemyTargeted` issues a fresh attack from
an empty order.

### 3. The order stack leaks

`CBaseAITankTask::OnNoEnemy` in `Common\BaseTasks.script` calls:

```c
m_Group.SetOrder_Attack([], ERT_AGGRESSIVE);
```

An attack order with an **empty target list**, and a hardcoded `ERT_AGGRESSIVE` that
walks straight past the group's own `GroupEnemyReaction`. Every time any unit loses a
target, `SetOrder_Attack` pushes another copy of the current order. Measured stack
depth on one platoon climbing `2,3,4,5,6,7,8,9` - none of it ever popped.

Fix: do not push when the order being issued is the one already running.

```c
if (m_CurrentOrder.m_Order != "" && m_CurrentOrder.m_Order != "Maneuver"
    && m_CurrentOrder.m_Order != "Attack")
  PushOrder();
```

### Telling them apart in a log

| symptom | cause |
|---|---|
| `[ALARM]` on a group that has a `Path` | bug 1 |
| `[ALARM]` on a group with no `Path` | bug 2 |
| `stack=` climbing across `[FULFILLED]` lines | bug 3 |
| `[ALARM]` on a group still waiting for a `PositionWatcher` | not a bug - no trigger yet |

Backups of the unmodified engine file sit beside it as `UnitGroup.script.bak_*`.

### Instrumenting this yourself

The three log points that made all of it visible, all in `UnitGroup.script`:

- `[FULFILLED]` at the top of `OnOrderFulfilled()` - print the order name **and**
  `m_OrderStack.size()`. The stack depth is what separates the three bugs.
- `[ADVANCE]` immediately after `m_CurrentOrder.m_NextPatrolPoint++` in
  `ContinueOrder()`. That statement is the only place the patrol index moves.
- `[IDX]` in `RepeatOrder()`'s Patrol branch.

`StatusDebug` on the group class turns on G5's own push/pop tracing, which is what
finally showed the order being pushed and then destroyed one line apart.

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

## 8. The Editor and AI

**Corrected 2026-08-18.** An earlier version of this document said the Editor never
runs behaviour classes. It does run unit groups: a Berezov session in `Editor.exe`
produced 20 `[ADVANCE]` and 20 `[STOPPED]` lines and drove four groups six navpoints
along their path, with zero routing failures.

The original observation — zero `Radar`/`Task`/`UnitGroup` entries in `editor.log` —
came from a mission whose groups were all waiting on `DelayedOrder` triggers, so
there was nothing running to observe. That was read as "the Editor cannot run AI"
when it only showed "these particular groups had no orders yet".

Groups with `DelayedOrder false` and a `Path` **do** advance in the Editor, which
makes it a fast loop for testing routes — no campaign menu, no mission start. Weapons,
damage, scoring and player-triggered watchers still need the game.

Use the Editor's Navigator panel to *view* `routerzonemap`, `terrainzone` and
`microtextures` overlaid on the landscape.

## 9. Cache

`Cache\Scripts.cache` must be deleted for any `.script` edit to take effect.
It cannot be deleted while the game is running. A cold rebuild recompiles ~513
scripts and takes a couple of minutes.

---

## Method notes

- **Compare against a stock mission before anything else.** "How does a stock
  mission do it?" found the missing `Range` property in twenty minutes after
  hours of failed script reading. Two files side by side beats any amount of
  reasoning about the engine.
- **Instrument the exact line you care about.** `[IDX]` was placed in
  `RepeatOrder` while the increment it was meant to observe lives in
  `ContinueOrder` - so it logged zeros in healthy stock content too and proved
  nothing. Put the log statement on the statement in question.
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
