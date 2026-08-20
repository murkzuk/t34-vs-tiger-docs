# ZW mission inventory

Measured 2026-08-20 by reading each mission's own `WorldMatricies.script` and
its `TerrainZone*.bmp`. Nothing here is copied from a readme.

**The headline: ZW's missions are not one size.** Anything that assumes a
9000 m world — as the line-of-sight tooling did until this was measured — is
silently wrong on most of them.

| mission | world (m) | heightfield | zone map | painted vegetation |
|---|---|---|---|---|
| CustomMissions/KurskMission | **36000** | **4097²** | 2048² | 35.9% |
| CustomMissions/KurskMission2 | 36000 | 2049² | 2048² | 35.9% |
| CustomMissions/KurskMission3 | 36000 | 2049² | 2048² | 35.9% |
| CustomMissions/CLeningrad43_M1 | 20002 | 2049² | 2048² | 43.9% |
| Campaign_1/Mission_1 | 18000 | 2049² | 2048² | 73.6% |
| Campaign_2/Mission_1 | 18000 | 2049² | 2048² | 74.4% |
| Campaign_2/Mission_2 | 18000 | 2049² | 2048² | 74.4% |
| Campaign_2/Mission_3 | 18000 | 2049² | 2048² | 74.4% |
| Campaign_2/Mission_4 | 18000 | 2049² | 2048² | 76.4% |
| Campaign_2/Mission_6 | 18000 | 2049² | 2048² | 73.6% |
| CustomMissions/CWinterMission1 | 18000 | 2049² | 2048² | 49.9% |
| CustomMissions/CWinterMission2 | 18000 | 2049² | 2048² | 49.7% |
| CustomMissions/KurskMission4 | 18000 | 2049² | 1024² | 25.0% |
| MyMission/TargetPractice | 18000 | 2049² | 2048² | 74.4% |
| CustomMissions/Panther_M1..M3 | 12000 | 2049² | 1024² | 37.9% |
| Campaign_1/Mission_2 | 9000 | 2049² | 1024² | 69.1% |
| Campaign_1/Mission_3 | 9000 | 2049² | 1024² | 60.3% |
| Campaign_1/Mission_4 | 9000 | 2049² | 1024² | 70.4% |
| Campaign_1/Mission_5 | 9000 | 2049² | 1024² | 66.4% |
| Campaign_1/Mission_6 | 9000 | 2049² | 1024² | 65.1% |
| Campaign_2/Mission_5 | 9000 | 2049² | 1024² | 57.8% |
| Campaign_2/Mission_7 | 9000 | 2049² | 1024² | 64.0% |
| CustomMissions/CWinterMission3 | 9000 | 2049² | 1024² | 71.4% |
| MISSIONS/CF1..CF6Mission | 9000 | 2049² | 1024² | 58–70% |
| MISSIONS/TESTMISSION, OldTestMis, MultiplayerTEST | 9000 | 2049² | 1024² | 21–60% |
| MyMission/Mission1, murkz2 | 9000 | 2049² | 1024² | 60.4% |
| MISSIONS/DM2..DM6Mission | — | — | **none** | deathmatch, no `TerrainZone*.bmp` |

## Things worth knowing before touching any of them

**The heightfield resolution is not constant per metre.** Almost every mission
is 2049² regardless of world size, so a 9 km map samples ground every 4.4 m and
an 18 km map every 8.8 m. `KurskMission` is the exception at 4097², which is a
larger terrain than TvT itself ever ships — and 32 MB of it, which matters in a
32-bit process.

**The file is not always `hmap.raw`.** ZW's missions name theirs `hmap1.raw`
and similar, and declare the real path in `WorldMatricies.script` as
`ImageFileName`, relative to the game root. Any tool that globs for `hmap.raw`
will skip the entire `CustomMissions` set.

**Zone maps are 1024² or 2048².** Combined with the world size that gives cell
sizes from 8.8 m to 17.6 m. Derive it, never assume it.

**Painted vegetation is not tree density.** The campaign missions are painted
60–76% vegetation, far more than the Kursk maps at 25–36%, yet the Kursk maps
are the ones that plant trees sparsely. The percentage in this table says how
much of the map is *marked* forest, not how thickly it is planted — see
[Line_Of_Sight.md](Line_Of_Sight.md), where that distinction turned out to
matter a great deal.

**The DM missions have no zone bitmap at all.** Any terrain-aware tooling must
handle that rather than failing.

## How to regenerate this table

```python
import canopy_los as c, collections, os, glob
for wm in glob.glob(r'M:\T34vsTiger_ZW2015\Missions\*\*\WorldMatricies.script'):
    d = os.path.dirname(wm)
    t = c.Terrain(d)          # reads MatrixWidth and ImageFileName itself
    h = collections.Counter()
    for y in range(0, t.zh, 8):
        for x in range(0, t.zw, 8):
            h[t.z[t.zoff + y*t.zstride + x]] += 1
    tot = sum(h.values())
    veg = sum(n for cd, n in h.items() if cd in c.VEGETATION)
    print(d, t.world, t.hdim, t.zw, '%.1f%%' % (100.0 * veg / tot))
```

`canopy_los.py` is in [`../../Tools/LineOfSight/`](../../Tools/LineOfSight).
