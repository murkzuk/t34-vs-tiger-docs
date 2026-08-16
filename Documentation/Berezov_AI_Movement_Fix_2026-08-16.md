# Berezov AI Movement Fix — 2026-08-16

How the German advance was finally made to work. The full story, in order.

## The symptom
- The 4 German groups (ZugFalke, KGKaiser, ZugLex, ZugWeidinger) moved a few dozen meters toward the first waypoint, then stopped dead.
- `editor.log` showed `AStarSteps = 20000` and `OnUnreacheable` for every order. Destinations were valid (correct `To:` grid cells after the 9000-world change), so it was not a bad waypoint problem.

## The root cause (found after a long detour)
- The game's router treats **road zone cells (ZMC_Road01, index 0) as BLOCKED**.
- `Scripts\Common\RouterMap.script` lists the passable zones: `PassableZones = [ZMC_Forest01(11), ZMC_Forest02(12), ZMC_Forest03(13), ZMC_Grass01(32), ZMC_OffRoad01(1), ZMC_OffRoad02(122), ZMC_OffRoad03(123)]`. **Index 0 (road) is not in the list, so every road cell is impassable for routing.**
- Berezov's main road runs north-south at world X ≈ 448–457 (router grid column 51) — a continuous 1–3 cell wall between the German spawn (west) and every village/objective (east).
- The units marched to the road's edge, the A* could not even start from a road cell, and every destination stayed unreachable. The units stopped at the road edge forever.
- For a long time this wall was misread as the river. It is the **road**. The terrain river (zone 217) is a separate braided network.

### Why stock missions don't have this problem
- Stock C2M5 also has 8,511 road cells in its router map — but its spawns and waypoints never force a road crossing, so nobody ever noticed roads are "blocked".
- The ZW mod's C1M1 router map contains **zero** road cells (it paints roads with other indices), so it never hit this either.
- Berezov's groups must cross the road to advance anywhere → instant total failure.

## The fix
- Repainted all road cells (index 0) in the router zone layer to **index 1 (ZMC_OffRoad01 — passable)**.
- Applied to both files:
  - Live `M:\T34vsTiger\Missions\MyMission\Berezov\RouterZone_Test.bmp` (1024×1024, 13,050 road cells)
  - Repo `TvT\Missions\MyMission\Berezov\RouterZone_Test.bmp` (2048×2048 original, 49,496 road cells)
- Deployed, cleared `M:\T34vsTiger\Cache\*.cache`, re-tested.

## Result (user's test)
- Groups now move: to the road, back, then off along the waypoint chain. **Routing works.**

## Other changes that were in play (keep, they work)
- `WorldMatricies.script`: MatrixWidth/Height 18000 → **9000** (matching all stock missions; the 18000 map was the only one in the game).
- `Mission.script`: `RouterWorkingZones = [40000, 40000, 60000, 60000]` (same as stock C2M5).
- Router map: `CC1RouterMap`, 64×64 graph, 1024×1024 zone BMP on the live install (2048×2048 in the repo — the 2048 works too; the ZW mod proves 2048 + 18000 works).

## Engine zone BMP size rule (the earlier trap, recorded so we never re-hit it)
- The engine validates the zone BMP size: file length must be exactly `fileSizeField + 2` bytes.
- 1024×1024 zone BMP = 1,049,656 bytes (field 1,049,654). 2048×2048 = 4,195,384 bytes (field 4,195,382).
- Off-by-the-palette or missing the trailing 2 bytes → "Can't load layer" → "invalid IZoneMap. RouterMap refuse working".

## What is still open (next session)
- **Water/drowning:** the user's test showed units spawn/sink in river water and die. The river zone (217) is not painted in the router layer at all, so paths can now run straight through water. Needed: move spawns (and any waypoint) out of water, and paint the river as blocked in the router layer (or rebuild the router layer to mirror the terrain layer: river blocked, roads passable, rest open).
- `hwater.raw` reads as a constant 7785 everywhere (2049×2049×2 bytes) — water level interpretation still unconfirmed.
