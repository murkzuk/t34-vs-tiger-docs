Quick Mission Generator
========================

What this is
-------------
Regenerates a test mission with a randomized number of enemy tanks/AT guns
and a relocated objective, so you can play-test variety without hand-editing
mission files each time. You can play as either side, and on either of two
maps:

  - "Quick Mission (Generated)" - the original, 9000x9000, small.
  - "Steppe Quick Mission (Generated)" - a large, mostly-open 18000x18000
    map with sparse forest, built 2026-07-03 for the open-steppe mission
    concept (see the docs repo's Steppe_Map_Scoping doc for the full story).

How to use it (GUI - easiest)
-------------------------------
Double-click "Quick Mission Generator.bat" in this folder. Pick Soviet or
Axis, pick which map, optionally type/roll a seed, click "Generate Mission",
and read the result box. No command prompt needed. There's also an "Edit
Roster" button that opens roster.json directly in Notepad.

How to use it (command line)
-------------------------------
1. Open a command prompt in this folder (Tools\MissionGenerator).
2. Run:
       python generate_mission.py
   This picks a fresh random layout every time you run it, playing as
   SOVIET by default, on the small (quickmission) map by default.

   To play the large steppe map instead:
       python generate_mission.py --target steppe

   To play as the Germans instead:
       python generate_mission.py --faction AXIS
   (or set "player_faction": "AXIS" in roster.json so it's the default
   without typing the flag every time)

   To get the SAME layout again later (useful if you find a good one and
   want to replay it), add a seed number:
       python generate_mission.py --seed 42
   Same seed = same layout, every time (combine with --faction/--target as
   needed. Note: a given seed produces different layouts on each map,
   since the two targets don't consume random numbers identically - see
   "About the steppe map's RouterZone filter" below.)

3. Open the game's Level Editor, find "Quick Mission (Generated)" (or
   "Steppe Quick Mission (Generated)") in the mission list, load it, and
   play-test it (game camera mode).

4. Repeat step 2 (or click "Generate Mission" again in the GUI) whenever you
   want a new random layout. Each run completely replaces the previous one
   for that map - it does not stack on top of earlier runs, and generating
   one map never touches the other.

About the steppe map's RouterZone filter
-------------------------------------------
Unit placement optionally checks a "RouterZone" bitmap as a soft filter for
where's actually passable (an unproven, best-effort check, not authoritative
either way). The steppe map reuses the small map's same RouterZone bitmap
stretched over a much bigger area, which means the same real-world spot now
samples a different, unverified part of that bitmap - so this filter is
disabled for the steppe map until a RouterZone bitmap painted specifically
for its 18000x18000 scale exists. Units still only spawn near the same
proven-safe cluster of positions either way, so this doesn't make placement
unsafe, just means the soft filter isn't doing anything useful there yet.

Playing as AXIS uses the Tiger tank (CTankPzVIAusfEUnit), which has a few
known cosmetic-only quirks from earlier work this session (some interior
animations - gun-laying needles, commander hatch, a couple of gauges - don't
play due to a 3D model gap). Doesn't affect driving, aiming, or firing. See
roster.json's "_axis_player_note" if you'd rather switch to the Pz IV
instead.

Roster variety (as of the latest update): each side has a tank, an AT gun,
a self-propelled gun, and infantry - German Pz IV / Pak 40 / StuG 40 /
riflemen, Soviet T-34/76 / Zis-3 / SU-85 / riflemen. All grep-verified
against the actual Scripts\Units\*.script files, same as everything else
in this roster.

Changing what gets randomized
-------------------------------
Edit roster.json in this folder in any plain text editor (Notepad is fine).
Each entry has a "min" and "max" - the generator picks a random count in
that range each run. For example:

    { "id": "enemy_tank", "class": "CTankPzIVGUnit", ..., "min": 1, "max": 3 }

means 1 to 3 Pz IV tanks will spawn, chosen randomly each run.

Do NOT type in a new unit class name that isn't already in the roster -
the generator will refuse to run if it sees a class name it hasn't been
told is real and verified (see VERIFIED_UNIT_CLASSES near the top of
generate_mission.py). If you want to add a new unit type, that needs the
class name confirmed against the actual Scripts\Units\*.script files first
- ask for help with that rather than guessing, a wrong class name would
only fail when you try to load the mission in-game, which this tool can't
predict.

What it will never touch
--------------------------
Every file in this mission's folder except Content.script (Mission.script,
Atmosphere.script, Terrain.script, the terrain/texture files, etc.) is
guaranteed untouched by every run - the script checks this itself and
refuses to report success if anything else changed.

The original template mission (Missions\MyMission\Mission1\ for the small
map, Missions\MyMission\SteppeTemplate\ for the steppe map) is never touched
either - it's always the starting point for every regeneration, never
overwritten.

If something goes wrong
-------------------------
The script will print exactly what's wrong and will NOT write a broken file
- if you see "FAILED validation", nothing was changed, the previous
Content.script is still there untouched. Safe to just try again.
