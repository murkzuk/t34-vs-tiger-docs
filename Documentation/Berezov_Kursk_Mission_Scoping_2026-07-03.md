# "Operation Citadel: Berezov" — Panzer Elite Mission Recreation Scoping (2026-07-03)

Scoping pass for recreating one of the user's favorite Panzer Elite (Wings Simulations) missions inside TvT. This document is the full picture gathered today, meant to pick up work later without re-deriving any of it. Source material: `Berezov.zip` (user-provided, on Desktop), containing `Berezov-ger.scn`, `Berezov-us.SCN`, `Berezov.bmp`, and English/German briefing text files for both sides.

## What the mission actually is

"Operation Citadel: Berezov" — a dual-perspective mission set on the historically real first day of the Battle of Kursk (5 July 1943, 08:20 start, 2-hour duration, 31°C, light clouds). German side spearheads a breakthrough with the player's own platoon (`Zug Falke`) leading, `KG Kaiser` (panzers + grenadiers) following behind, punching through three villages in sequence along one road — **Berezov → Gremuchi → Gonki** — against a Soviet defense-in-depth. The Soviet side (not being built yet, see "Build order" below) plays the mirror: hold the line, and specifically flank rather than trade shots at range — their own briefing says "close in... attack them from behind," a real, deliberate asymmetry given the German side's gun-range advantage.

## File format — confirmed plain text, no reverse-engineering needed

`.scn` files are **plain text** (99.95%+ printable ASCII, confirmed by direct byte inspection), using a `[Chunk:TypeName(N)] ... key:value ... [ChunkEnd]` structure. Fully human-readable with the `Read`/`Grep` tools directly — no binary parsing required, unlike TvT's own `.ms2` format. Chunk types found in `Berezov-ger.scn` (131KB): `Globalsettings`, `Node(0-412)` (map reference points), `Area(N)` (named zones, e.g. `BEREZOV`/`GREMUCHI`/`GONKI`/`Rakovo`/`Visloe`, each linked to 2 boundary `Node`s), `PathNode(0-333)` + `Path(0-27)` (AI movement routes), `PreDefPos(0-7)` (predefined positions, likely tied to the named briefing markers), `ArtAirStrikes` (artillery/air support config), `CombatGroup(N)` + nested `Unit(N)` (the order of battle — 64 individual units across ~19 named platoons/groups), `CombatScript(N)` + `ScriptRow(N)` (the event/trigger system), `BehaviourSetNew(N)` (AI engagement-range profiles: `_Ignore all`, `_Low/Medium/Long Range Fight`), `UserDefGroup(N)`.

An existing PE mission-analysis toolkit already exists at `L:\2025\PE\PE Mission Reader CMD\` (built earlier by the user with prior AI assistance) — focused on the binary `.dat` terrain/object format, not needed here since `.scn` turned out to be plain text.

## Mission-goal system — directly comparable to TvT's own

`Globalsettings` has explicit, semicolon-delimited goal definitions:
```
MissionGoal0:Take GONKI;primary;Clear;90;area;GONKI;;
MissionGoal1:Destroy Soviet HQ;primary;Destroy;100;cg;Soviet HQ;;
MissionGoal2:Destroy Plt.Samsonov;secondary;Destroy;100;cg;Plt.Samsonov;;
MissionGoal3:Take BEREZOV;Secondary;Clear;90;area;BEREZOV;;
MissionGoal4:GONKI;bonus;Arrive;40;cg;Zug Falke;area;GONKI
```
Format: `Name;PrimaryOrSecondaryOrBonus;Verb;Threshold;TargetKind;TargetName;AreaKind;AreaName`. This maps cleanly onto TvT's own primary/secondary/bonus `m_MissionObjectives` tuple system — no new mission-goal mechanism needed on the TvT side.

## Trigger/event system — same shape as work already done this session

`CombatScript` chunks fire on `Always` (unconditional) or `CG State` events (a named combat group arrives at a named area, is "under attack," or is "destroyed"), each driving a chain of `ScriptRow` actions (`move` to a road/area, `Wait` a timer, `American`/artillery call, trigger a numbered briefing message). Example: a `CombatScript` on `KG Kaiser` triggers a `move` `ScriptRow` toward `BEREZOV` that also sends message #2 ("KG Kaiser is moving out towards Berezov now.") — directly matching the numbered `[Messages]` list in the briefing `.txt` files. This is functionally the same pattern already used this session for the steppe mission's Soviet group AI (state-triggered task classes reacting to combat/arrival events) — PE just expresses it as a data table instead of script code. No new TvT capability needed, just the same kind of per-group Task-class scripting already proven.

## Roster — real discrepancy found and resolved

**Important**: the bundled `Berezov-ger.scn`'s actual unit data uses **Panzer III/IV** for the German side (`Zug Falke` = 5× `Pz4H2`, `KG Kaiser` = mixed `Pz3M`/`Pz3L`/`Pz3J`), **not** the "14 Tigers... 8th Kp./SS Pz Rgt. 2" described in the bundled English briefing text. Soviet side: T-34/76 (`T3476-0/1/2`, several 3-4-unit platoons: `Plt.Samsonov`, `Plt.Kutuzov`, `Plt.Popov`, `Plt.Oleshev`), KV-1 heavies (`KV176-0`, `Plt.Voronov` — 3 units, despite the briefing describing this position as a "T-34 concentration"), SU-152 heavy assault guns (`Plt.Stepichev`, `Plt.Kotin`), 76mm AT guns + crews (`Plt.Berzina`, `Plt.Rhyzov`), `Soviet HQ` (SU-76M + truck + infantry, the primary-objective "destroy HQ" target), plus recon/light units (`Plt.Zhilin`: armored car + 2× T-70). This is likely an earlier/base-game roster revision; the Tiger-equipped version the user actually played is a variant not included in this particular file.

**Decided (user confirmed from memory of actual play)**: build the **Tiger version** — `Zug Falke` = **1× Tiger (player) + 4× Panzer IV (AI wingmen)**, `KG Kaiser` stays Panzer III × 4 (AI support column) exactly as authored. This is how the user actually played it ("just me... the rest of the zug had 4's") — PE lets a player freely pick their own personal vehicle within a platoon (constrained by period-correctness/supply in PE's career mode), independent of the squad's default equipment; that meta vehicle-choice/supply system itself is explicitly **out of scope** — a separate, much bigger feature TvT doesn't have and isn't being built here. For this mission, the Tiger-for-`Zug Falke`-only substitution is simply a fixed roster choice, no new engine capability required (TvT already supports mixed-vehicle-type platoons with one player slot).

No direct TvT equivalents exist for KV-1, SU-152, or Panzer III — the Soviet-side build (see below) will need stand-ins or an adapted roster when it's tackled.

## Scale — comfortably within TvT's proven budget

64 individual units across ~19 combat groups (platoon-sized, 2-5 units each), well within the unit-count budget already proven this session for TvT missions (`Campaign_2\Mission_5` runs 60fps with a comparable count).

## Terrain — real distances extracted, SteppeTemplate confirmed as the build target

**Decided**: reuse `Missions\MyMission\SteppeTemplate\` (already built and tested this session — 18000×18000 world units, sparse forest, 125fps) rather than build new terrain from scratch. Confirmed TvT's world units and PE's map units are both meters-scale (PE's `Berezov.bmp` is exactly 1/5th of `ScenarioWidth`/`ScenarioHeight` — 5920÷1184 = 4920÷984 = 5.0 precisely, confirming consistent real map units), so the real village-to-village distances can be used directly with no scaling or distortion needed.

**Extracted real distances** (from each `Area`'s two boundary `Node` positions, midpoint-to-midpoint):
- Rakovo → Berezov: ~945 units
- Berezov → Gremuchi: ~1,346 units
- Gremuchi → Gonki: ~1,983 units
- Total Berezov-to-Gonki advance corridor: ~3,310 units

A ~4.2km (Rakovo-to-Gonki) corridor fits comfortably inside `SteppeTemplate`'s 18km×18km space, using well under a quarter of its width.

**Still open / not yet done**:
- The road isn't straight — the briefing map shows it jogging at each village. Needs tracing from the map image and either finding/extending `SteppeTemplate`'s existing road or adding one.
- `SteppeTemplate` currently has zero buildings — the three village clusters are real new authoring work (though existing TvT missions with village prop clusters can be used as a pattern reference, not built from nothing).
- Anchor point/orientation for placing the whole corridor within `SteppeTemplate`'s existing safe zone/passability data not yet chosen.

## Full order-of-battle position extraction — DONE 2026-07-03

Extracted all 19 combat groups / 64 units with exact positions, saved to `Documentation/Berezov_OOB_positions_2026-07-03.json` (group + per-unit `PositionX`/`PositionY`, distance and compass bearing from the Berezov anchor). German groups: `Zug Falke` (player Tiger + 4 AI, dist 1725/bearing 252° from Berezov), `HQ` (Pak crew + halftrack, 1641/251°), `KG Kaiser` (4 tanks, 1725/250°, now Panzer IV per the roster decision above), `Zug Lex` (2 halftracks, 1791/252°), `Zug Weidinger` (infantry + halftrack, 1309/255°) — all clustered west of Berezov, consistent with staging just behind the front line before the push.

Soviet groups span a genuine defense-in-depth, not a flat line — real tactical variety worth preserving in the build:
- Close-in, right on top of Berezov: `Plt.Voronov` (3× KV-1, dist 399/bearing 83°), `Plt.Rhyzov` (AT guns + infantry, 181/286°), `Plt.Zhadov` (AT gun + infantry, 93/189°), `Plt.Zhilin` (armored car + 2 recon tanks, 601/290°).
- Mid-depth, around/behind Gremuchi: `Plt.Samsonov` (4× T-34/76, 1137/92°), `Plt.Sytnik` (5× T-34/76, 1150/64°), `Plt.Kotin` (SU-152 + infantry, 1336/89°).
- Deep reserve, toward/behind Gonki: `Plt.Kutuzov` (4× T-34/76, 2128/79°), `Plt.Stepichev` (SU-152 + infantry, 2295/95°), `Plt.Berzina` (AT gun + SU-152, 2597/95°), `Soviet HQ` (SU-76M + truck + infantry, 3281/98°, the primary "destroy HQ" objective), `Plt.Markov` (AT gun, 3257/97°), `Plt.Oleshev` (4× T-34/76, farthest at 4036/91°, near/past Gonki).
- **Genuine flanking ambush, confirmed real (not a data glitch — checked every individual unit position)**: `Plt.Popov` (4× T-34/76, 2225 units out but at bearing 12° — almost due north of Berezov, off the main east-west corridor entirely) sits far off the line as a flank threat, exactly matching the briefing's own warning about "any tanks attempting an attack from this direction."

## Build order — DECIDED 2026-07-03

1. **Build now**: German attack side only — player as Tiger, `Zug Falke` (4× Panzer IV AI wingmen), `KG Kaiser` (Panzer IV × 4 AI support column — changed from Panzer III, which doesn't exist in TvT at all, confirmed via `ls` on both `Models\` and `Scripts\Units\`) — pushing Berezov → Gremuchi → Gonki against the Soviet defense-in-depth (Soviet roster/positions as authored, pending stand-ins for KV-1/SU-152/etc.).
2. **After testing**: the Soviet defense side, reusing the same underlying battle setup (per the user's own observation, PE's AI is genuinely bilateral — both sides fight for real regardless of which is player-controlled, which is already how TvT's own AI works, not a new feature to build).

## Next mechanical step (not started)

Extract the complete position/unit dataset (all ~64 units across all combat groups) relative to the village anchor points, so the full authored tactical layout (AT gun positions, ambush platoons, reserve lines) is in hand before touching `SteppeTemplate` itself.
