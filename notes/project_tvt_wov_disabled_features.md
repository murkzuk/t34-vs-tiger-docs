# WoV features disabled in TvT (2026-08-24)

A systematic diff of **WoV** (`G:\WoV\Scripts\`, the engine's original helicopter
game) against **TvT REDUX** (`M:\T34vsTiger\Scripts\`) to find features that are
ACTIVE in WoV but COMMENTED OUT (or emptied) in TvT. The engine is shared; TvT
inherited WoV's code and the devs switched off a whole layer of it rather than
deleting it.

## The headline

~20 distinct disabled features found. Two very different recoverability classes:

- **Plug-in** — the engine system is fully present; only the wiring call is
  commented. Uncomment + test. Likely near-free wins.
- **Re-author** — the code path exists but the *content* was stripped. Needs new
  content (voice lines, dialog scripts), not an uncomment.

## Plug-in (uncomment + test)

| Feature | Where it's off in TvT | Where it's on in WoV |
|---|---|---|
| **Troop transport (mount/dismount)** | `Units\GermanSoldierRifleUnit.script:132` `//SetupLoadTransportAnimation(...)` (also GermanTankman, Soviet* ×2) | `Units\AmericanSoldierRifleUnit.script:120` (live) |
| **Infantry fire silently** | `GermanSoldierRifleUnit.script:41` `Component BurstFireSound = null; //new #Emitter<...>()` | `AmericanSoldierRifleUnit.script:42` `new #Emitter<CM16GunFireSound>()` |
| **Vehicle track/movement sound** | `TankPzVIAusfEUnit.script:675` `//LeftTrackSound / //RightTrackSound` | `Gaz51Truck.script:80` `new #Emitter<CTruckMovementSound>()` |
| **Weapon min/max engage range** | `TankPzIVGUnit.script:36` `//final static MinDistance/MaxDistance` | `AmericanSoldierRifleUnit.script:53` (live) |
| **Static emplacement can't rotate** | `Buildings\DotConcreteUnit.script:113` `//MinRotateRadius = 0` + commented rotation block | `M29MortarPointUnit.script:89` (live) |
| **Structures take full small-arms** | `Buildings\WatchTowerUnit.script:57` `//SetDamageTypeModifier(DAMAGE_BULLET, 0)` | `WatchTowerUnit.script:55` (live) |
| **Gun recoil animation (Nebelwerfer)** | `GunNebelUnit.script:53` `//FireAnimator = new #LineAnimator<...>()` | `HowitzerUnit.script:72` (live) |
| **Gun muzzle fire + smoke (ZIS-3)** | `GunZis3Unit.script:167` `//FireEffectId / //CloudEffectId` | `HowitzerUnit.script:49` (live) |
| **End-of-mission briefing blank** | `Menus\EndMissionMenu.script:74` `//BriefingText.SetText(...)` | `EndMissionMenu.script:89` (live) |
| **"Show Cursor" key bind removed** | `Menus\ControlsSettingsMenu.script:92` `//[ "CTLCMD_SHOW_CURSOR" ... ]` | `Menus\ControlsMenu.script:87` (live) |
| **Generic bullet damage class** | `Common\Explosions.script:103` `//String DamageType = CLASSIFICATOR_DAMAGE_BULLET` | `Explosions.script:46` (live) |
| **Tactical map cursor + navpoints** | `Common\Cockpit.script:190` `//TerrainMap.SetCursorControl` | `Cockpit.script:277` (live) |
| **Interior-device damage effect leak** | `Common\IntDevices.script:95` `//DeleteEffect(m_EffectInstanceID)` | `IntDevices.script:262` (live) |

## Borderline (plug-in, but verify)

- **`CanStayAttack` AI flag** — `//final static boolean CanStayAttack = false` on
  all four TvT infantry/crew units (`GermanSoldierRifleUnit:108`, etc.).
- **Halftrack door open/close** — `BtrM3A1HalftruckUnit:446` / `BtrHanomag251
  AusfCUnit:457` door animators commented.
- **Joystick availability check** — `ControlsSettingsMenu.script:160`
  `//SetDisabled(!IsJoystickAvailable())`.
- **List-element text colours** — `MultiEndMissionMenu:164` / `MultiEscapeMenu:124`
  olive/khaki colour override commented.

## Re-author (content stripped, not just a switch)

- **Scripted mission dialogs (radio chatter).** `Common\Dialogs.script` `final
  static Array Dialogs` is emptied (one commented example line) vs WoV's ~129
  active dialog classes. **This is the "radio messages" you remembered** — the
  engine subsystem exists, but the WW2 dialog/voice content was removed.
- **Spoken-number voice table.** `Common\SoundsTable.script` `CommonSoundTable`
  is emptied (one commented example) vs WoV's full Jackson/Breadshow/Dispatcher
  number tables. Needed by the radio/messenger to voice digits.

## Not carried over (correctly — skip)

Vietnam-only content that was simply dropped, not "disabled": village scene
groups, `DesantGroup_1..8` squads, DShK-peasant emplacements, and the American
soldier class set (all deleted from TvT's `Groups\`).

## Caveats before re-enabling anything

- **Each entry must be re-verified against the current files** before editing —
  this is a snapshot from a grep sweep, not ground truth.
- "Plug-in" still assumes the **target class/effect still exists** in TvT (e.g.
  uncommenting `FireEffectId` is pointless if `GunZis3GunFireEffect` was also
  stripped). Check the named class/effect before uncommenting.
- Re-enable **one at a time**, clear `Cache\Scripts.cache`, test in-game — the
  standing rule.
- The highest signal-per-effort candidates are: **infantry gun sound** (silent
  rifles are a real bug, not a missing feature), **troop transport**, and the
  **end-mission briefing**.

## Related

- `project_tvt_atmosphere_understanding.md` — same WoV-inheritance theme (the
  richer atmosphere keys are WoV's, already present in the engine).
- The transport system itself lives in `Common\` (SetOrder_Load/Unload, loader
  joints, `IsTransport`) — fully present, just unplugged at the unit level.
