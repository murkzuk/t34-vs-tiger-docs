"""Hostile-pair visibility per mission, to separate a code regression from a
map that is simply severe.

A run showing 94% of sightings denied means nothing on its own: the question is
whether the same model gives sensible answers on maps of different character.
If open maps stay open and only the hilly one closes down, the model is
reading terrain rather than imposing a range cap.
"""
import collections
import math
import os
import sys

import canopy_los as L

BASE = r"M:\TvT_INJECT_SANDBOX\Missions"
MAPS = [
    ("Campaign_2/Mission_3", "hilly, just played"),
    ("Campaign_2/Mission_5", "played earlier"),
    ("MyMission/BerezovKursk", "your steppe"),
    ("Campaign_1/Mission_2", "stock woodland"),
]

print("%-24s %-20s %6s %7s %7s %7s %8s %6s" %
      ("mission", "", "pairs", "half+", "ground", "trees", "relief", "mean"))
for rel, note in MAPS:
    folder = os.path.join(BASE, *rel.split("/"))
    if not os.path.isdir(folder):
        continue
    t = L.Terrain(folder)
    units = [u for u in L.read_units(folder)
             if any(k in u.cls for k in L.FIGHTERS) and u.side in ("FRIEND", "ENEMY")]
    friends = [u for u in units if u.side == "FRIEND"]
    enemies = [u for u in units if u.side == "ENEMY"]
    c = collections.Counter()
    for a in friends:
        for b in enemies:
            if math.hypot(b.x - a.x, b.y - a.y) > 1500:
                continue
            f, why, _ = L.los(t, a.x, a.y, a.eye(t), b.x, b.y, b.hull(t))
            c[L.CLEAR if f >= L.VISIBLE else why] += 1
            c["_sum"] += f
    # Relief over a coarse grid, as a one-number summary of how broken the
    # ground is - the thing that should explain the difference.
    hs = [t.ground(x * 300.0, y * 300.0) for x in range(1, 30) for y in range(1, 30)]
    n = sum(c.values()) or 1
    n = c["clear"] + c["terrain"] + c["foliage"] or 1
    print("%-24s %-20s %6d %7d %7d %7d %7.0f m %6.2f" %
          (rel, note, n, c["clear"], c["terrain"], c["foliage"], max(hs) - min(hs), c["_sum"] / n))
