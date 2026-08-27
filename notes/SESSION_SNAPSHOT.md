# START HERE — snapshot 2026-08-27, end of day

Written for whoever picks this up next (DeepSeek or a fresh Claude session).
The user is out of plan until Tuesday 2026-09-01. **Everything below is committed
and pushed**; docs repo `8e6de62`, memory repo `dee0ed7`, both clean.

---

## THE HEADLINE: a Tiger II is in the game, and the Axis AI can finally fight

Both are new today and both are **live in `M:\T34vsTiger` (REDUX)**. The Tiger II
is in ZW too. Versions bumped: `REDUX v0.260827b`, `ZW v0.260827d`.

---

## GAME FILES CHANGED TODAY — read before editing anything

Backups for ALL of it: `K:\TvTDeepseek\rollback\kingtiger_2026-08-27\`

| file | build | what |
|---|---|---|
| `Scripts/Units/TankPzVI_KingTigerIIUnit.script` | both | **NEW** — the Tiger II, 74 KB, generated from G5's Tiger |
| `Scripts/Common/Piercing.script` | both | Tiger II ballistics, real KwK 43 falloff |
| `Scripts/Common/Armour.script` | REDUX | Tiger II armour (ZW already had it) |
| `Scripts/Common/HitPoints.script` | both | Tiger II hit points |
| `Scripts/Common/Bullets.script` | both | registrations; ZW also had 5 AI-written STUB classes REMOVED |
| `Scripts/Common/Explosions.script` | both | registrations; ZW had 14 stub/duplicate classes REMOVED |
| `Scripts/Common/UnitGroup.script` | both | **the Axis AI fix — one line, shared by 36 missions** |
| `Scripts/Common/AutoCommander.script` | both | target priority rows; REDUX also anti-thrash values |
| `Scripts/Common/PlayerUnit.script` | both | Tiger II target identification |
| `Scripts/Common/Mission.script` | REDUX | Tiger II in the German roster |
| `Scripts/Editor/MenuConfig.script` | both | Tiger II placeable in the editor |
| `Models/u_veh_KingTiger.*` + 23 textures | REDUX | **copied in** (25 MB); ZW already had them |
| `Models/u_veh_KingTiger.ms2` | both | gun elevation track corrected (binary edit) |
| `Missions/MyMission/BerezovKursk/*` | REDUX | Tiger II placed; Axis attack orders |

**Both `Cache\Scripts.cache` are deleted** — they rebuild on next launch.

---

## PROVEN vs NOT PROVEN

**Proven in game, from `execution.log`:**
- Tiger II loads, joins its platoon, is attacked by Soviets
- German attacks went **0 → 20** after the `UnitGroup.script` fix
- The general fix does the work: 39 single-target acquisitions vs 13 from the
  BerezovKursk hand-listed workaround

**NOT proven — do these first:**
1. **The anti-thrash change has never been run.** `LastTargetDangerAdd` 50 → 150
   and `RadarUpdateTime` 1.0 → 2.0 in REDUX's `AutoCommander.script`. Cheap to
   check: count target switches per unit in the log; it was 13 for one platoon.
2. **`UnitGroup.script` is shared by 36 missions.** Only BerezovKursk has been
   run. Watch the next few logs for anything odd elsewhere.
3. **The BerezovKursk hand-listed 37 Soviet targets can now come out** — the
   general fix carries it, and removing it lets the Kampfgruppe fight *while*
   advancing instead of `SetOrder_Attack` cancelling the patrol.

---

## OPEN, IN PRIORITY ORDER

1. **Friendly fire, 3 incidents, all in the German HQ group.** `HQ_1_Tractor`
   has no `BehRadarMask` so it is visible to its own side — **42 of 102 units in
   that mission lack the property**. Does NOT explain `ZugWeidinger_1`, which
   has it and was shot anyway. Mission-data pass.
2. **`GunFlak88` is classified `["GER","GROUND"]` with no type classificator** —
   the deadliest AT gun in the game is invisible to target priority. One word.
3. **There is no threat model.** `PreferedTargets` weights by type and distance
   only; a T-34 and a StuG weigh the same. Needs the binary acquisition hook —
   see `notes/project_tvt_acquisition_parked.md`.
4. **Tiger II leftovers**: Winter variant undefined; playable version needs
   `Cu_veh_PzVI_KingTigerII_PlayableModel`; `Textures/Pk_CAP.tex` referenced and
   absent in both builds.

---

## THE .MS2 TOOL — two real fixes today, both published

- **Submesh descriptor decoded.** Indices are relative to each submesh's
  `vertex_start`. Missing it shredded the upper hull of **87 of 249 models**.
- **Character rigs were importing collapsed flat** (33 mm head-to-foot). Fixed
  per-subtree under `l_Hips`. Also fixes crew figures inside tanks.
- Add-on zip rebuilt; user's Blender 5.2 copy verified current, pycache cleared.

**Open**: the `vertex_count * 24` block (flag `0x40000`) is **49% of every model
file** and still unidentified. **Tested and RULED OUT today: it is not tangent +
binormal** (mean |dot| 0.51 against computed values — random). Until it is
understood, the exporter cannot ADD geometry, only reshape what exists with
vertex/index counts unchanged. That is what blocks importing a new vehicle.

The zeroing experiment (zero the block, see if the Editor still draws it) is
still the right next test. **The sandbox Editor does not work** — it dies before
writing an `editor.log`, and there is no evidence it has ever run there. That
needs sorting first, or the test needs doing another way.

---

## TRAPS THAT COST TIME TODAY

- **Check line endings PER FILE, not per project.** `PositionWatchers.script` is
  pure LF; `MissionTasks.script` is MIXED (42 CRLF, 412 LF). `grep -c $'\r'` is
  NOT a reliable CRLF test here — it reported zero on a 100% CRLF file. Count
  `b'\r\n'` in Python.
- **There are two Berezov missions.** The game loads `BerezovKursk`. An edit went
  into `Berezov` and did nothing. Check which mission the log actually names.
- **A test that cannot distinguish the hypotheses is not a verification.** The
  "vehicle transforms verified" claim covered position and scale only; a bounding
  box cannot detect a rotation-handedness error on a near-symmetric tank.
- **Arming a group is not ordering it to fire.** `ActivateFire` +
  `ERT_AGGRESSIVE` logs "engaging" and produces zero attacks.
