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

### Zone-bitmap row order: SETTLED — row 0 is world y=0, no flip

`RouterZone_*.bmp` and `TerrainZone_*.bmp` declare a **positive** height in the
BMP header, which by the format spec means bottom-up rows. **The game does not
read them that way.** It treats pixel row 0 as world y=0.

Settled 2026-08-18 by testing **all eight** possible orientations (four rotations,
each with and without an axis swap) against **606 navpoints that G5 placed by hand
across 12 stock missions**. Hand-authored routes sit on roads and open ground, not
inside trees, so forest hit-rate discriminates cleanly:

| orientation | on road codes | in forest |
|---|---|---|
| **row 0 = world y=0 (no flip)** | **273** | **7.8%** |
| bottom-up (the BMP spec reading) | 70 | 44.8% |
| mirror-X+Y | 66 | 55.5% |
| the other five | ≤56 | 60–75% |

Not a close call, and it holds per-mission: no-flip wins in **11 of 12**, often
overwhelmingly (`Campaign_1/Mission_4` 1.5% vs 73.9%, `Campaign_1/Mission_2` 0% vs
69.7%). The road count is the corroborating half — 273 navpoints on road codes
versus 70. Hand-drawn routes follow roads, and only one reading shows that.

**Why the wrong reading survived a whole afternoon:** a route generated on the
vertically mirrored map ran in-game with *zero* routing failures. That looked like
confirmation and was luck — 86.7% of that map is passable, so a corridor picked to
avoid forest in a mirrored map lands in genuinely open ground most of the time.
Checked afterwards against the correct orientation, 32 of its 34 navpoints were
still fine and only two needed moving. **A successful run is weak evidence for a
model when most random choices also succeed.**

The user spotted it first, from the Editor: a waypoint that the mirrored map called
grass had visible trees on it.

`K:\tvt_terrain\tvt_terrain.py` `read_bmp8`/`write_bmp8` were both flipping rows;
fixed 2026-08-18. Note the writer still emits a positive height, because every
shipped TvT zone BMP does — the originals are top-down data behind a bottom-up
header, and matching them exactly is safer than being spec-correct.

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

### `[PATROL]` - the permanent progress line

`ContinueOrder()` carries one deliberate, permanent log line at the patrol
increment:

```
[PATROL] <GroupID> reached point 7 of 34
```

`m_CurrentOrder.m_NextPatrolPoint++` is the **only** place the patrol index moves,
so this single line is the entire progress signal for any mission. It is not gated
by `StatusDebug`, because without it progress has to be inferred from proxies - and
inferring it from the wrong proxy has already produced one confidently wrong "zero
advances" reading of a log where the advance was in fact running.

To count progress per group:

```bash
grep -a '\[PATROL\]' execution.log | awk '{print $2, $6}'   | awk '{if($2+0>m[$1])m[$1]=$2+0} END{for(g in m) printf "%-16s %d
", g, m[g]}'
```

### Instrumenting something else yourself

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

`Scripts\Menus\MissionsMenu.script` holds the mission lists;
`Scripts\Menus\MissionsControls.script` holds the menu's layout.

### The three limits, and how each was removed (2026-08-18)

Stock TvT could list **7 missions per side** and no more. Three separate things
caused that, and all three are fixed in REDUX.

**1. Campaign progress gates the list.** `UpdateMissionList()` builds
`min(GetUserValue("USSRCampaign"/"GerCampaign"), array.size())` rows. Appending a
mission to `USSR_Missions` / `Germany_Missions` therefore leaves it **invisible**
until the player has unlocked that many campaign missions. Correct for a campaign,
wrong for anything standalone.

*Fix:* two new arrays, `USSR_ExtraMissions` and `Germany_ExtraMissions`, listed in
full after the campaign rows and never gated. Put standalone and generated
missions there. Campaign progression is untouched.

**2. The Load handler indexes the campaign array by row position.**

```c
final int iMission = GetObject("MissionList").GetCurrentItem();
CStartMissionMenu::MissionClassName = Germany_Missions[iMission];   // stock
```

`GetCurrentItem()` returns a **row index**. Any row not sourced from that array
reads off the end. This is the one that bites silently — it surfaces as a mission
failing to load or the wrong mission loading, which looks like a mission-authoring
fault rather than a menu one.

*Fix:* `UpdateMissionList()` records `ListedCampaignCount`, and the handler splits
on it:

```c
if (iMission >= ListedCampaignCount)
  ... = Germany_ExtraMissions[iMission - ListedCampaignCount];
else
  ... = Germany_Missions[iMission];
```

**3. The list box was only tall enough for ~7 rows, with no scrollbar.**
`MissionList` was `height 0.2070` against a `25.0/768.0` element height. The space
below it was dead all the way to the Back/Load buttons at `y 0.9128`.

*Fix:* box extended to `height 0.4607` (**14 rows**), background to `0.4824`, and a
real scrollbar added for anything beyond that.

### Adding a scrollbar to a TvT list — the recipe

The engine already supports this; TvT's own `ControlsSettings` and `Escape` menus
use it, and WoV's campaign list (same engine) is built identically. Three pieces:

1. A `CUIVerticalScrollBar` control beside the list, using the existing
   `VScrollerUp` / `VScrollerDown` / `VScrollerScroller` materials.
2. `list.SetSlaveScroller(GetObject("<BarName>"));` — **this is the piece that is
   usually missing.** `MissionList` already called `SetListScrollStep` and still
   did not scroll, because nothing was bound to drive it.
3. Handlers for `<BarName>_Arrow1` / `_Arrow2` calling `ScrollUp()` / `ScrollDown()`.

Bind the slave scroller **after** populating the list — `ClearWithUnregister()`
rebuilds it every time `UpdateMissionList` runs, and TvT's own `ControlsSettings`
menu also binds after populating.

Match the scroll step to the element height. `MissionList` shipped with
`SetListScrollStep(32.7 / 768.0)` against `25.0/768.0` rows, which does not
correspond to a row and matters once a scrollbar is attached.

### Verified

`CBerezovKurskMission` was moved out of `Germany_Missions` into
`Germany_ExtraMissions`, so the new path is exercised on every launch rather than
lying dormant. Confirmed in play: the row lists, loads (125 objects, 2.55s), and
`execution.log` shows **zero** `[ScriptManager]` errors with
`Script Class CMissionsMenu 1` registering normally.

Missions under `Missions\MyMission\` are absent from these arrays by default and
are therefore Editor-only until added.

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

## 10. Unit placement — the matrix, and which way is forward

Added 2026-08-26 while making a second Tiger spawn beside the player in C2M1.

A unit's `new Matrix(...)` in `Content.script` is four rows of four. **The
translation is the fourth column, not the fourth row:**

```
new Matrix(
    xvec.x, xvec.y, xvec.z, origin.x,
    yvec.x, yvec.y, yvec.z, origin.y,
    zvec.x, zvec.y, zvec.z, origin.z,
    0.0,    0.0,    0.0,    1.0
  ),
```

**`xvec` — the first row — is the FORWARD axis.** This is not a guess:
`Scripts\Common\FreePlayerCamera.script` places the chase camera behind the
player with

```c
Vector DirectionX   = new Vector(_Target.xvec[0], _Target.xvec[1], 0.0);
DirectionX.Normalize();
Vector CameraOrigin = _Target.origin + DirectionX * -20.0;
```

A camera at `xvec * -20` is 20 m *behind*, so `+xvec` is where the tank is
looking. `zvec` is near `(0,0,1)` in every shipped unit, i.e. Z is up.

### Placing one unit relative to another

To put a unit N metres directly behind another, copy the leader's three basis
rows verbatim (so it faces the same way) and offset the origin along the
normalised ground-plane forward:

```python
m   = math.hypot(xvec[0], xvec[1])          # ignore the tiny z tilt
fwd = (xvec[0]/m, xvec[1]/m)
pos = (origin[0] - fwd[0]*N, origin[1] - fwd[1]*N, origin[2])
```

**Add `["SurfaceControl", "PutonGround"]`** rather than trusting the copied Z.
The terrain under the new spot is not the terrain under the old one, and the
heightfield row order is not what you would guess (see the placement note in the
project map).

---

## 11. Making a unit follow the player

### Use `Formation`, and put it on the TASK

Groups have a `Formation` **property** (`"Independent"`, plus a
`FormationDistance`) which arranges units *within* the group. That is not the
same thing and will not make a unit follow the player.

The follow order lives on the task, from `CBaseAITask`:

```c
Formation(_LeaderID, _Displacement, _DistanceOptimum, _DistanceMax,
          _CruiserSpeed, _OvertakeSpeed, _NotifyOnReached, _Oriented)
```

A working column follower, from `C2M1MPUTigerTask`:

```c
void Init()
{
  CBaseAITankTask::Init();
  ActivateBehavior(true);
  ActivateMovement(true);                    // NOT false - see below
  sendEvent(3.0, getIdentificator(user), "KeepStation", []);
}

event void KeepStation()
{
  Component mission = GetMission();
  Vector XYRank = new Vector(0.0, -40.0, 0.0);   // (0,-40) = dead astern, 40 m
  Formation(mission.GetMainPlayerObjectID(), XYRank, 40.0f, 80.0f,
            0.15f * GetMaxSpeed(), GetMaxSpeed(), false, false);
  sendEvent(8.0, getIdentificator(user), "KeepStation", []);
}
```

**Three things that are not obvious and each cost a session somewhere:**

1. **`Formation` is continuous; `SetOrder_MoveTo` is not.** Re-issuing a MoveTo
   in a loop can only ever produce drive-arrive-stop-wait, which the player sees
   as lurching. It is not a navigation problem and not a physics cost — it is
   the wrong *kind* of order. `Formation` has its own cruise and overtake
   speeds and the engine holds the slot itself.
2. **Cruise speed must be set explicitly and LOW.** Passed as `0`, the wrapper
   defaults it to two thirds of max speed — far faster than a tank actually
   crawls, so the follower surges and brakes. `0.15 * GetMaxSpeed()` works.
3. **Never issue `Follow` and `Formation` together.** Two orders arrive per tick
   and fight; if their distances disagree the unit micro-stutters in place.

**Displacement convention, empirically:** `(0, -40)` is dead astern at 40 m and
`(-45, -60)` is behind and out to one flank at ~75 m. Note the shipped
`CWingmanTask` constants are Whirlwind-over-Vietnam leftovers — 200 m spacing
with `z = 30`, which is *altitude* — so do not copy them as an example. ZW's
`BaseTasks.script` has retuned values; REDUX's has not.

### A real bug to route around

`BaseTasks.script`'s six-argument `SetOrder_Formation` overload (~line 1320)
passes `_Displacement`, `_DistanceOptimum` and `_DistanceMax` — which are the
parameter names of a *different* function. Its own parameters are called
`_FormationVector`, `_PosDistanceOptimum`, `_PosDistanceMax`. Call the
eight-argument `Formation()` wrapper instead, which routes to the seven-argument
overload and is sound.

---

## 12. Scripted escorts are on rails — find every override first

A shipped unit that "just sits there" is usually not broken; it is being told to
sit there by several places at once. C2M1's second Tiger had **five**, and any
follow order would have been overwritten within seconds by four of them:

| where | what it did |
|---|---|
| its task's `Init()` | `ActivateMovement(false)` — movement off outright |
| `Content.script` group | `["FirstOrder", "Patrol"]` + `["DelayedOrder", true]` + a `["Path", ...]` |
| `StartMPU` event | `PopDelayedOrder()` released that patrol at mission start |
| `CheckDistance` event | a **don't-overtake-the-player gate** issuing its own 4-navpoint route |
| `StartPhase1` / `2Act` / `3Act` | three more `SetOrder_Move` calls |

**Before changing a unit's behaviour, grep its ID across every file in the
mission folder.** In C2M1 the Tiger also appeared in `Mission.script`'s
`GermanKillList`, in a `sendEvent` for a bombing manoeuvre, in two
`OnUnitExplosion` handlers, and in `PositionWatchers.script`'s `ControlPoints` —
none of which should be disturbed while changing how it moves.

### Do not strip `FirstOrder` to stop a patrol

Tempting, and it risks the "no orders in group" alarm that produced the C1M2
recursion crash (see the `UnitGroup.script` bugs in section 4b). **Leave the
declarative properties alone and stop the order being *popped* instead** —
comment out the `PopDelayedOrder()` call. The group keeps a valid order
definition it simply never uses.

Likewise, when removing a scripted move from a combat phase, keep the
`ActivateRadar` / `ActivateFire` / `SetEnemyReactionType` calls around it. Those
are what make the unit fight; only the movement order needs to go.

---

## 13. Atmosphere — which layer wins, and the 10-degree ceiling

### `Content.script` overrides `Atmosphere.script`

A mission's `Atmosphere.script` sets fields like `SunDirection`; its
`Content.script` may then override the same fields inside an `"Atmosphere"`
object. **`Content.script` is what the engine uses.** They are frequently out of
sync in shipped missions — C1M4 has opposite signs on the sun's X component
between the two files, and has since 2001.

**Measure the `Content.script` value.** Reading `Atmosphere.script` alone
produced a confident, wrong conclusion that a whole fix had never been applied.

### The sun is only visible below ~10 degrees elevation

`Scripts\Common\CockpitControls.script`:

```c
CommanderCameraLink.SetMaxVertAngle(Math_PI*(10.0f/180.0f));
CommanderCameraLink.SetMinVertAngle(- Math_PI*(7.0f/180.0f));
```

The player cannot look higher than **10 degrees**. Unit declarations agree
(`MaxVertAngle = 0.17` rad = 9.7 degrees). So:

- a sun above ~10 degrees elevation **cannot be seen at all** — it is a light
  source, not an object
- what the player *does* see is **shadow length and the angle light strikes
  hulls**, which respond at any elevation
- the sun disc itself only enters view at dawn or dusk

G5 shipped every campaign mission with the sun at 63-67 degrees. Normalising
those vectors made no visible difference precisely because the sun was, and
remained, out of view — a null result that is fully explained rather than
mysterious.

### `SunDirection` length is position, not brightness

The sun billboard is placed along `SunDirection * DistanceToSun` (2000 in every
shipped mission). A vector of length 0.34 therefore puts the sun at ~680 m
instead of 2000 m — close enough to sit inside fog or below the skyline.
Brightness is a separate `SunIntensity` field. **Normalising a sun vector moves
the sun; it does not make it brighter.**

Elevation from a direction vector is `asin(-z / |v|)`; the compass bearing is
`atan2(y, x)`. To change the time of day without swinging the light round to a
different side of the map, preserve the bearing and change only the elevation.
---

## 14. Shadows — three systems, and they must agree

Added 2026-08-26 after a user complaint ("tank shadows are so dark they crush
all detail") turned into four rounds of pulling the wrong lever. **Read this
before touching shadow darkness.** The model matters more than any value.

### There are three separate shadow systems, plus one thing that is not a shadow

| | setting | what it draws |
|---|---|---|
| 1. Stencil shadow | `StencilShadowColor` | **vehicles** — the real cast shadow |
| 2. Projected shadow | `ShadowColor` | terrain and buildings |
| 3. Fake shadow | `FakeShadow` / `FakeShadowScale` | a cheap dark blob under a vehicle, enabled per model in `Scripts\Common\FakeShadows.script` |

`ShadowFar`, `LodForShadowChange`, `LodForShadowHide` and `ShadowDetail` control
**distance and level of detail**, not darkness.

**`AmbientLight` is not a shadow setting at all.** It is the fill light — how
bright a surface is when the sun is not hitting it. Two different mechanisms
produce what a player calls "shadow":

```
surface FACING AWAY from the sun     -> AmbientLight only
surface facing the sun but BLOCKED   -> sun x ShadowColor / StencilShadowColor
```

This is why raising `StencilShadowColor` fixed hull detail and did **nothing**
for the tank commander: he was not in a cast shadow, he was simply facing away
from the sun.

### What can cast onto what — `StencilShadowSettings`

Only objects listed in `Scripts\Common\Settings.script` (~L64) cast a stencil
shadow, and **stencil is the only shadow that can fall onto another object**:

```
StencilShadowSettings = [
    [ [], [CLASSIFICATOR_SHADOW] ],
    [ [], ["INVENTORY_ITEM"]  ],
    ...
];
```

That is tanks, guns, buildings. **Trees are not in it**, and cannot be added
usefully — see below.

### Why a tank parked under a tree stays fully lit

Trees are classified as terrain (`CLASSIFICATOR_TERRAINFOREST`) and their
shadows are drawn by a **separate vegetation pass that only touches the
terrain**, gated by `TreeShadowLodDistance` (default 500) and `TreeLightKoef` in
`BaseAtmosphere.script`.

So a tree shadow is terrain-only *by design*. It has no path onto a dynamic
mesh. This is an engine limitation, not a settings mistake, and **it is not
script-fixable** — the pass lives in the compiled renderer.

Worth knowing before anyone spends a day trying to make woods provide visual
cover: they never will, however the shadow colours are set. (The AI *does* see
through foliage correctly — that is the separate line-of-sight work.)

### The trees are SpeedTreeRT v1

`SpeedTreeRT.dll` + `STTree.dll` in the game root, `Models\Trees\*.spt` as
procedural definitions (6-15 KB each - the geometry is generated at runtime, not
baked). Textures split into `*Bark.tex` (3D trunk/branch geometry),
`*Frond/Leaves/Needles*.tex` (billboard foliage) and `*_Billboard.tex` (the
full-tree impostor at distance).

So a tree is **both** mesh and billboard. There is real geometry to cast from —
but SpeedTreeRT renders its own projected ground shadow, separate from the
engine's stencil pass, which is the whole reason tree shadows never reach tanks.

**Procedural generation also means per-client tree layout.** In multiplayer each
client generated its own tree positions, so one player drove through gaps
another player's client had filled with trunks. The layout was never
synchronised.

### RULE: `ShadowColor` and `StencilShadowColor` must match within a mission

They are the same physical shadow drawn by two different renderers. If they
differ, a tank and the ground beside it cast visibly different shadows.

**The evidence for the rule is in the shipped missions.** The two anyone
actually finished have them identical:

```
C1M2   ShadowColor (0.404, 0.494, 0.545)   Stencil (0.404, 0.494, 0.545)   matched
C2M2   ShadowColor (0.345, 0.420, 0.467)   Stencil (0.345, 0.420, 0.467)   matched
```

State of the campaign as of 2026-08-26:

```
1M1  (0.325 grey)          stencil MISSING -> falls back to 0.3
1M3  (0.200, 0.200, 0.250) (0.500, 0.500, 0.500)   MISMATCHED by 0.30
1M4  (0.325 grey)          stencil MISSING
1M5  (0.847) (0.875)       close - overcast, correctly near-white
1M6  (0.847) (0.875)       close
2M1  (0.560, 0.580, 0.630) matched   <- fixed 2026-08-26
2M5  (0.847) (0.875)       close
2M3  2M4  2M6              stencil MISSING
```

**Six of twelve missions never set `StencilShadowColor` at all**, so their
vehicle shadows fall back to `BaseAtmosphere.script`'s default of
`(0.3, 0.3, 0.3)` — the darkest value anywhere in the game, and dead neutral
grey. Nobody chose that; it is what you get when nobody sets it.

### Choosing a value

- **Tint it blue.** What actually fills a real shadow is skylight. Neutral grey
  reads as dead. The finished missions do this: C1M2 `(0.404, 0.494, 0.545)`.
- **Overcast wants a high value.** C1M5 / C1M6 / C2M5 use `0.875` — on an
  overcast day shadows are barely darker than lit ground. Whoever set those
  understood the setting, and they are the proof it does what we think.
- **Sunny wants roughly 0.45-0.60.** `0.30` crushes; the user judged `0.45`
  "better, details becoming visible" and settled around `0.56`.

### Watch the ambient/sun ratio too

`AmbientLight` luminance against `SunIntensity` decides how harsh a mission is:

```
C2M1   ambient 0.120   SunIntensity 1.000   8.3:1   <- harshest in the game
C1M2 / C1M3 / C2M2 / C2M4   ambient 0.201   0.35-1.2   the tuned value
C2M3   ambient 0.092   SunIntensity 0.600
```

C2M1 paired the **lowest ambient with the highest sun** — two independent
defaults meeting badly. Raised to `0.210` on 2026-08-26 to match the tuned
missions.

### FakeShadow — and a bug worth knowing about

`FakeShadows.script` enables a cheap shadow blob per model class. **No Tiger
gets one.** The file sets `Cu_veh_PzVI_MAINModel::FakeShadow = true`, but
`TankPzVIAusfEUnit::getMeshObjectName()` returns `Cu_veh_PzVI_LATEModel`
unconditionally — `LATE` appears zero times in that file.

Same shape as the `LodForShadowHide` bug: G5 wired the MAIN model, switched the
units to LATE, and never updated the shadow config. **This class of bug does not
show up in a log** — it is a perfectly valid assignment to a class nothing
instantiates, so nothing errors. The only way to find it is to cross-check
configured model classes against the ones units actually ask for.

### Could a modern shadow technique be hooked in? — assessed 2026-08-26

Prompted by a Gemini conversation the user shared. Its structural model of the
engine was **independently correct** and matched everything above, derived
without knowledge of this document — two shadow pipelines, `StencilShadowSettings`
as the gate, `TreeShadowLodDistance` capping the tree pass, foliage physically
unable to shade a vehicle, and the `vs_1_1` / `vs_2_0` material split. It missed
only the third system, the per-model fake-shadow blob.

**Its load-bearing performance claim is wrong, and this is the part worth
remembering.**

> *"If shadows cause a CPU/GPU dip, the culprit is almost exclusively dynamic
> vehicle/building stencil volumes"* — and therefore emptying
> `StencilShadowSettings` *"immediately claws back CPU frame time"*.

**Measured, and it does not.** No shadow class appears anywhere in either
build's profiler hot pages:

```
REDUX   CGrass, CSTForest, CTreeKiller, CGridObject, a std::map lookup
ZW      CAbstractObject, CAbstractJoint, CCylinderShape / CDynamicIntersector
```

`ShadowFar` tuning was worth about 2 fps. **Emptying `StencilShadowSettings`
would delete every vehicle shadow in the game and buy close to nothing.** It is
a reasonable inference from how the engine is built; it simply is not what the
frame is spent on. See `TvT_Performance.md`.

#### The idea that IS worth something

**Screen-space directional shadows** — raymarch the depth buffer toward the sun
vector, so any pixel whose ray crosses tree-canopy depth gets shaded. Because
trees and tanks both write depth, **this would let foliage shade a tank**, which
the engine fundamentally cannot otherwise do. That is a real visual capability,
not a performance play.

Its honest limit: screen-space only knows what is on screen. Park under a tall
tree and look down and the canopy leaves the frame, so the shadow fades.

#### Feasibility, grounded in what already exists here

The genuinely hard part of a DIY implementation is reading a D3D9 depth buffer
from a pixel shader — D3D9 was never designed for it, and it needs vendor FourCC
formats (`INTZ` on NVIDIA, `DF24` on AMD), interception of
`CreateDepthStencilSurface`, clear-call tracking and MSAA resolution.

**That is already solved in this install.** `ReShade32.dll` is loaded, the
shader folder is present, `ReShade.ini` is live, and the user has confirmed
depth capture works. Reimplementing it inside our own DLL means rewriting
thousands of lines to reach a capability that is already running.

**The sensible split, if this is ever pursued:** ReShade does depth extraction;
our injected DLL supplies the sun vector and camera matrices. We already hook
`SetVertexShaderConstantF` in the fog probe, so feeding a shader is proven
machinery. A full internal Cascaded Shadow Map means rendering the scene a
second time from the sun's viewpoint — double the draw calls on the single core
that is already the bottleneck, which is the wrong trade for this engine.

**NOT STARTED. Recorded so the "killing stencils is free performance" idea does
not resurface as a new thought in six months.**

### Before blaming the lighting, check the texture

The commander stayed dark through every lighting change. He was never a lighting
problem:

```
hum_German_Tankman.tex    22% average luminance   <- the commander
u_veh_PzVI_MAIN1.tex      62%                      hull
u_veh_PzVI_MAIN2.tex      53%                      turret
```

German panzer crews wore black and G5 painted him accordingly — average texel
`RGB(60, 56, 44)`. Light is *multiplied* by texture, so at 22% base even
doubling the ambient barely moves him, while the same lift visibly improves a
62% hull.

**Measure the texture before reaching for a lighting lever.** Average DXT1
luminance is cheap to compute from the block endpoint colours and settles the
question in seconds.
---

## 15. Skinned meshes (crew figures) — an open bug and a hard limit

Added 2026-08-26. **The bug below is NOT solved.** Recorded so the next attempt
does not repeat seven dead ends.

### THE OPEN BUG: tank commanders render as black silhouettes

Every German tank commander renders as a near-black silhouette while the hull he
is standing in is correctly lit, in bright sunlight.

**Ruled out, each by test rather than reasoning:**

| candidate | how it was eliminated |
|---|---|
| the texture | `hum_German_Tankman.tex` is a normal-toned face on a **field-grey** uniform. Looked at directly. |
| material colours | material 6 is **byte-identical** between the LATE and MAIN models, and its ambient `(0,0,0)` matches the hull's - every material on the tank has ambient 0 |
| the mesh | switching `getMeshObjectName()` to `Cu_veh_PzVI_MAINModel` - a different `.ms2` entirely - left him just as dark |
| scene `AmbientLight` | raised 75% (lum 0.120 -> 0.210). Slight improvement, nowhere near enough |
| `StencilShadowColor` | raised twice, 0.3 -> 0.45 -> 0.56. Fixed **hull** detail, did nothing for him |
| the `FakeShadowComm` config set | renamed to `set1` to match MAIN. No change. |
| lightmaps | the Tiger uses no light textures at all |

**What that leaves:** something in the skinned-mesh render path. Crew figures are
bone-animated (`l_Spine`, `l_Shoulder_Left`, `Body3`, `Head`, `LHand1-3`) and go
through `SkinMesh1`/`SkinMesh4` shaders, not the `SceneMesh` ones the hull uses.

**The next step is an observation, not another hypothesis:** do *other* crew
figures render dark - infantry, Soviet tankmen, the hull driver? All dark means
an engine-wide skinned-mesh lighting problem, which is a D3D9 shader-path
investigation on the scale of the fog work. Only the Tiger commander means the
model, and something specific was missed.

### A MEASURING TRAP that wasted four rounds

The texture was first "measured" by averaging DXT1 block endpoint colours across
the whole file, giving 22% luminance against the hull's 62%, and that was
reported as the cause. **It was meaningless.** Most of a character sheet is dark
background around the UV islands; the average described empty space, not the
face. The user opened the texture and saw immediately that it was fine.

**Sample the region you care about, or just look at the image.** A whole-file
average of a character texture tells you nothing.

### THE HARD LIMIT: skinned meshes are missing 64 shader variants

Counted in `Shaders\`:

```
SceneMesh (rigid)     150 variants   has both *N and *L
SkinMesh1             86 variants    *N only
SkinMesh4             86 variants    *N only

missing from both skinned sets: 64, and they differ in exactly one
character - position 4 is L instead of N (positions 1-3 spread evenly)
```

So whatever feature position 4 `L` selects — `LightMap.fxo` exists alongside, so
lightmapping is the obvious candidate — **skinned meshes have no shader for it
and cannot use it.** Rigid geometry can; anything bone-animated cannot.

Not the cause of the commander bug (the Tiger uses no light textures), but a
real and permanent capability gap worth knowing before designing anything that
expects crew figures to light like vehicles.

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

### Added 2026-08-26

**Count braces excluding comments.** A naive `{` versus `}` count raised a false
alarm on `MissionTasks.script` — the file has commented-out code blocks, so the
raw counts are unbalanced in the *original* too. Strip `/* */`, `//` and string
literals before counting, or compare against the untouched backup rather than
against zero.

**Print the whole report block, never a tail of it.** A `tail -30` silently cut
the top four entries off a profiler listing and made a correct tool look broken.

**Check the before and after are the same mission.** A framerate comparison
showed +24% and was worthless — the baseline was C1M2 and the new run was C1M1.
The tell was in the data: draw calls and triangles both went *up* after a change
that could only reduce them.

---
