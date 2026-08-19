"""Line of sight for TvT, computed the way the engine never did.

WHY THIS EXISTS
---------------
`FUN_100c9e50` in Behavior.dll is the whole of TvT's vision model: 2D distance x
angle x target state x mask, then a dice roll, with `D3DXVec2Normalize` - in two
dimensions. No ray cast, no terrain query, no foliage test. A gunner can see and
hit through a ridge or through 100 m of woodland.

This module answers "can A see B" from the mission's own static data, so the
maths can be checked and tuned BEFORE anything is hooked into a live 2001 engine.

THE MODEL - two independent effects, one march
----------------------------------------------
1. TERRAIN. The ground heightfield is exact and unambiguous. If the sight line
   passes below the ground at any point between A and B, the ridge blocks it.
   This is what gives hull-down, dead ground and reverse slopes.

2. VEGETATION. Deliberately NOT a hard ceiling. A canopy-height test alone says
   anyone standing inside a wood is blinded in every direction, which is wrong -
   you can see out of a wood along the ground, just not far. So foliage
   accumulates OPTICAL DEPTH along the path: every metre through a vegetation
   cell spends part of a budget, and sight is lost when the budget runs out.
   Standing 20 m inside a wood you see roughly 20 m. That falls out for free.

   The canopy height still matters, and it is what couples the two: a vegetation
   cell only costs anything if the sight ray is BELOW the treetops there. A
   gunner on a ridge looking down on a target beyond a wood in the valley has an
   unobstructed line over the crowns, and gets one.

WHERE THE NUMBERS COME FROM
---------------------------
Canopy heights are the game's own, not invented:

  - Every stock Terrain.script calls
        RegisterVerticalForest([ZMC_Forest01], "foreststripe.tex", [0.8], 17.0f)
    identically across all twelve campaign missions. 17 m is the engine's own
    forest wall height for Forest01, and Forest01 is the only zone that gets one.
  - The forest render layers sit at [0.0, 8.0, 11.0, 13.0, 14.0] m.
  - Everything else is the weighted mean of `TreeSize` in BaseSTTree.script over
    the species mix in that zone's template in BaseForest.script. Those mixes are
    listed against each entry below so the arithmetic can be re-checked.

The SIGHT metres are the one genuinely tuned quantity - the distance at which
that vegetation becomes opaque. They are seeded from each template's occupancy
(how much of the mix is NullTree) and are meant to be adjusted against play.

GEOMETRY CONVENTIONS - each cost a debugging session earlier in this project
---------------------------------------------------------------------------
  - hmap.raw is 2049x2049 uint16 LE stored FLIPPED: row 0 is world y=MAX.
    Z = raw * 0.07. Re-validated here against 46 hand-placed GameObjects in
    Campaign_1/Mission_2: mean -1.12 m, RMS 1.27 m. The seven other orientations
    give RMS 6.6 to 33.
  - The zone bitmaps are the OPPOSITE: row 0 is world y=0, no flip, despite a
    positive BMP height field.
  - World is 9000 x 9000 m (CWorldMatrices.MatrixWidth), so a 1024 zone cell is
    8.789 m and a 2049 height sample is 4.395 m.
"""

import math
import os
import re
import struct

WORLD = 9000.0
HEIGHT_FACTOR = 0.07

# Zone code -> (canopy height in metres, metres of sight before opaque).
#
# Height sources, per zone:
#   11 Forest01  RegisterVerticalForest(..., 17.0f) - the engine's own number.
#                Template CMiddleForest: Fir_tall_bend .20 (20 m), Fir_tall .20
#                (28), FirScotch .25 (25), FirScotchSmall .25 (20), null .10.
#                Weighted mean of the trees actually placed is 23.2 m; the
#                engine draws its wall at 17, and the engine wins.
#   12 Forest02  CLightForest: Fir_short .1 (5), Linden .2 (8), BulfordHolly .2
#                (3), Birch .2 (4), SmallBirch .2 (3), null .1 -> 4.6 m. This is
#                scrub, not woodland; a Tiger is 3.0 m tall and stands proud.
#   13 Forest03  single LiveOak, TreeSize 17.0.
#   14 Forest04  CLargeForest: Fir_tall_bend .2 (20), Fir_tall .15 (28),
#                FirScotch .15 (25), null .50 -> 23.9 m over half the cells.
#   20 RoadForest  Birch (4) + Fir_tall (28) + BulfordHolly (3), a thin line of
#                three - tall but you see between the trunks.
#   49/50/51     BulfordHollyLarge 5.0 / mixed 3.5 / BulfordHolly 3.0.
#   52 SpecialLongAloneTree  one Fir_tall (28) with three bushes.
#   60/61/62     VillagePlanting: Linden 8.0 / Linden 8.0 / AppleTree 7.5.
#
# The sight budget scales with how solid the template is. CLargeForest is half
# NullTree, so it is tall but see-through; CMiddleForest is 90% occupied.
VEGETATION = {
    # Bush01..Bush04 are NOT bushes. BaseForest.script's CellTemplates maps them
    # to the variable-density forest templates - CExtraLightForest, CLightForest,
    # CMiddleForest, CLargeForest - so they are woodland. They were missing from
    # this table at first, which silently treated real forest as open ground;
    # Campaign_1/Mission_3 has units standing in 27.
    27: ( 3.2, 220.0),
    28: ( 4.6, 160.0),
    29: (20.0,  45.0),
    30: (23.9,  90.0),
    11: (17.0,  45.0),
    12: ( 4.6, 160.0),
    13: (17.0, 120.0),
    14: (23.9,  90.0),
    20: (28.0, 200.0),
    49: ( 5.0,  70.0),
    50: ( 3.5,  90.0),
    51: ( 3.0, 100.0),
    52: (28.0, 400.0),
    60: ( 8.0, 120.0),
    61: ( 8.0, 120.0),
    62: ( 7.5, 130.0),
}

# Eye and target heights above the object's own origin, in metres. Sighting is
# done from the gunner's optic; the thing being looked for is the hull, because
# a turret roof showing over a crest is not a target you can hit.
EYE = {
    "CTankPzVIAusfEUnit":      2.30,
    "CTankPzVIAusfE_LateUnit": 2.30,
    "CTankPzIVGUnit":          2.10,
    "CTankT34_76_42Unit":      1.95,
    "CTankT34_85_44Unit":      2.15,
    "CSAUSU85Unit":            1.90,
    "CSAUStuG40Unit":          1.75,
    "CGunPak40Unit":           1.10,
    "CGunZis3Unit":            1.10,
    "CBtrHanomag251AusfCUnit": 1.70,
    "CBtrM3A1HalftruckUnit":   1.90,
}
EYE_DEFAULT = 1.70
HULL = {
    "CGunPak40Unit":           0.80,
    "CGunZis3Unit":            0.80,
    "CGermanSoldierRifleUnit": 0.90,
    "CSovietSoldierRifleUnit": 0.90,
}
HULL_DEFAULT = 1.30

CLEAR, BLOCKED_TERRAIN, BLOCKED_FOLIAGE = "clear", "terrain", "foliage"


class Terrain:
    """The static half of a mission: ground height and vegetation cover.

    Both grids are loaded once and never change during a mission, which is the
    whole reason this can be cheap enough to run inside a per-frame AI call.
    """

    def __init__(self, folder):
        self.folder = folder
        self._load_height(_find(folder, "hmap.raw"))
        self._load_zones(_find_bmp(folder, "terrainzone"))

    def _load_height(self, path):
        raw = open(path, "rb").read()
        n = len(raw) // 2
        self.hdim = int(math.isqrt(n))
        self.h = struct.unpack("<%dH" % n, raw)
        self.hcell = WORLD / (self.hdim - 1)

    def _load_zones(self, path):
        d = open(path, "rb").read()
        self.zoff = struct.unpack_from("<I", d, 10)[0]
        w, h = struct.unpack_from("<ii", d, 18)
        self.zw, self.zh = w, abs(h)
        self.zstride = (w + 3) // 4 * 4
        self.z = d
        self.zcell = WORLD / w

    def ground(self, x, y):
        """Bilinear, because a march that samples nearest-neighbour on a 4.4 m
        grid produces staircase ridges that block sight lines that are actually
        open. The interpolation costs three multiplies and removes the artefact."""
        fx = x / self.hcell
        fy = (WORLD - y) / self.hcell           # flipped: row 0 is world y=MAX
        ix, iy = int(fx), int(fy)
        if ix < 0: ix = 0
        if iy < 0: iy = 0
        if ix > self.hdim - 2: ix = self.hdim - 2
        if iy > self.hdim - 2: iy = self.hdim - 2
        tx, ty = fx - ix, fy - iy
        d, v = self.hdim, self.h
        a = v[iy * d + ix]
        b = v[iy * d + ix + 1]
        c = v[(iy + 1) * d + ix]
        e = v[(iy + 1) * d + ix + 1]
        top = a + (b - a) * tx
        bot = c + (e - c) * tx
        return (top + (bot - top) * ty) * HEIGHT_FACTOR

    def zone(self, cx, cy):
        if not (0 <= cx < self.zw and 0 <= cy < self.zh):
            return 0
        return self.z[self.zoff + cy * self.zstride + cx]

    def zone_at(self, x, y):
        return self.zone(int(x / self.zcell), int(y / self.zcell))


def los(t, ax, ay, az, bx, by, bz, step=None, detail=False):
    """Can an observer at (ax,ay,az) see a point at (bx,by,bz)?

    Returns (visible, reason, distance_at_which_it_was_lost).

    The march is uniform-step rather than a true DDA. A DDA visits every cell
    boundary exactly once and is the right answer for a shipping implementation;
    a fixed step is easier to reason about while the model is still being
    argued over, and at 4 m over a 1 km line that is 250 samples - fast enough
    that this prototype is not the bottleneck. Swap it when the model settles.
    """
    dx, dy = bx - ax, by - ay
    flat = math.hypot(dx, dy)
    if flat < 1.0:
        return True, CLEAR, 0.0
    if step is None:
        step = t.zcell * 0.5                     # two samples per zone cell
    n = int(flat / step)
    if n < 2:
        return True, CLEAR, 0.0

    inv = 1.0 / flat
    ux, uy = dx * inv, dy * inv
    dz = bz - az
    budget = 1.0                                 # fraction of sight remaining
    trace = [] if detail else None

    for i in range(1, n):
        d = i * step
        x = ax + ux * d
        y = ay + uy * d
        rz = az + dz * (d * inv)
        g = t.ground(x, y)

        if rz < g:
            if detail:
                trace.append((round(d, 1), round(rz, 1), round(g, 1), "GROUND"))
            return False, BLOCKED_TERRAIN, d

        veg = VEGETATION.get(t.zone_at(x, y))
        if veg is not None:
            canopy_h, sight = veg
            if rz < g + canopy_h:
                budget -= step / sight
                if detail:
                    trace.append((round(d, 1), round(rz, 1),
                                  round(g + canopy_h, 1), "%.2f" % budget))
                if budget <= 0.0:
                    return False, BLOCKED_FOLIAGE, d

    if detail:
        los.last_trace = trace
    return True, CLEAR, flat


# --------------------------------------------------------------------------
# Reading a mission's objects. Content.script is CP1251 and its line endings
# vary per mission depending on which tool wrote it last, so both are
# normalised on the way in. Nothing here writes back.
# --------------------------------------------------------------------------

OBJ_RE = re.compile(
    r'\[\s*\n\s*"([A-Za-z0-9_]+)",\s*\n\s*"(GameObject)",\s*\n\s*'
    r'"([A-Za-z0-9_]*)",\s*\n\s*new Matrix\(\s*\n'
    r'\s*([-\d.]+), ([-\d.]+), [-\d.]+, ([-\d.]+),\s*\n'
    r'\s*([-\d.]+), ([-\d.]+), [-\d.]+, ([-\d.]+),\s*\n'
    r'\s*[-\d.]+, [-\d.]+, [-\d.]+, ([-\d.]+),')

AFFIL_RE = re.compile(r'\["Affiliation",\s*"(\w+)"\]')


class Unit:
    def __init__(self, name, cls, x, y, z, fx, fy, side):
        self.name, self.cls = name, cls
        self.x, self.y, self.z = x, y, z
        self.fx, self.fy = fx, fy
        self.side = side

    def eye(self, t):
        """Measured from the heightfield, not from the authored Z.

        Those two disagree by up to 0.9 m in Campaign_1/Mission_2 - the mission
        was hand-placed and the terrain has been resampled since. Mixing them
        makes a sight line start below its own ground and self-occlude in the
        first few metres, which reads as a terrain block and is not one. The
        march is against the heightfield, so the endpoints must be too."""
        return t.ground(self.x, self.y) + EYE.get(self.cls, EYE_DEFAULT)

    def hull(self, t):
        return t.ground(self.x, self.y) + HULL.get(self.cls, HULL_DEFAULT)

    def __repr__(self):
        return "%s(%s,%s)" % (self.name, self.cls, self.side)


def read_units(folder):
    """Affiliation is a property of the object's own property block, which
    follows the matrix. Take the first one after each match, which is that
    object's - the regex stops at the matrix so the block has to be scanned
    forward from there."""
    raw = open(os.path.join(folder, "Content.script"), "rb").read()
    s = raw.replace(b"\r\n", b"\n").decode("cp1251")
    out = []
    for m in OBJ_RE.finditer(s):
        name, _, cls, r00, r01, x, r10, r11, y, z = m.groups()
        tail = s[m.end():m.end() + 600]
        a = AFFIL_RE.search(tail)
        side = a.group(1) if a else "?"
        out.append(Unit(name, cls, float(x), float(y), float(z),
                        float(r00), float(r10), side))
    return out


def _find(folder, name):
    for fn in os.listdir(folder):
        if fn.lower() == name:
            return os.path.join(folder, fn)
    raise IOError("%s not found in %s" % (name, folder))


def _find_bmp(folder, prefix):
    for fn in sorted(os.listdir(folder)):
        if fn.lower().startswith(prefix) and fn.lower().endswith(".bmp"):
            return os.path.join(folder, fn)
    raise IOError("no %s*.bmp in %s" % (prefix, folder))


# --------------------------------------------------------------------------

FIGHTERS = ("Tank", "SAU", "Gun", "Btr")


def survey(folder, ranges=(500.0, 1000.0, 1500.0)):
    """Every hostile pair in a mission, scored two ways: what the shipped engine
    believes (distance only) against what the terrain actually permits.

    The gap between those two columns is the size of the flaw, in the game's own
    missions, measured rather than asserted."""
    t = Terrain(folder)
    units = [u for u in read_units(folder)
             if any(k in u.cls for k in FIGHTERS) and u.side in ("FRIEND", "ENEMY")]
    friends = [u for u in units if u.side == "FRIEND"]
    enemies = [u for u in units if u.side == "ENEMY"]

    print("%s" % os.path.basename(folder))
    print("  %d fighting units: %d FRIEND, %d ENEMY"
          % (len(units), len(friends), len(enemies)))

    for R in ranges:
        pairs = seen = terr = foli = 0
        for a in friends:
            for b in enemies:
                d = math.hypot(b.x - a.x, b.y - a.y)
                if d > R:
                    continue
                pairs += 1
                ok, why, _ = los(t, a.x, a.y, a.eye(t), b.x, b.y, b.hull(t))
                if ok:
                    seen += 1
                elif why == BLOCKED_TERRAIN:
                    terr += 1
                else:
                    foli += 1
        if not pairs:
            print("  within %5.0f m: no hostile pairs" % R)
            continue
        print("  within %5.0f m: %4d pairs, engine sees all of them; "
              "real LOS sees %d (%.0f%%)  -  %d blocked by ground, %d by trees"
              % (R, pairs, seen, 100.0 * seen / pairs, terr, foli))
    return t, units


def profile(folder, ax, ay, bx, by, eye=2.2, hull=1.3, n=24):
    """Print the ground and sight-ray heights between two points.

    The single most useful thing when a verdict looks wrong: it shows whether a
    block came from a real crest or from an artefact, and no amount of reasoning
    substitutes for looking at the profile."""
    t = Terrain(folder)
    az = t.ground(ax, ay) + eye
    bz = t.ground(bx, by) + hull
    d = math.hypot(bx - ax, by - ay)
    print("%.0f,%.0f -> %.0f,%.0f   %.0f m   eye %.1f  hull %.1f"
          % (ax, ay, bx, by, d, az, bz))
    for i in range(n + 1):
        f = i / float(n)
        x, y = ax + (bx - ax) * f, ay + (by - ay) * f
        g = t.ground(x, y)
        rz = az + (bz - az) * f
        z = t.zone_at(x, y)
        veg = VEGETATION.get(z)
        mark = "GROUND" if rz < g else ("trees " if veg and rz < g + veg[0] else "      ")
        print("  %6.0f m  ground %7.1f  ray %7.1f  %s  zone %3d" % (f * d, g, rz, mark, z))
    print("  verdict:", los(t, ax, ay, az, bx, by, bz))


def map_survey(folder, ranges=(200, 400, 800, 1500), samples=4000, seed=7):
    """Sight lines between random points, which is the honest picture of a map.

    The unit survey only covers where the mission author happened to put people;
    this covers the ground they will actually fight over once they move."""
    import random
    t = Terrain(folder)
    rng = random.Random(seed)
    print("%s - random sight lines" % os.path.basename(folder))
    for R in ranges:
        c = {CLEAR: 0, BLOCKED_TERRAIN: 0, BLOCKED_FOLIAGE: 0}
        for _ in range(samples):
            x, y = rng.uniform(400, WORLD - 400), rng.uniform(400, WORLD - 400)
            th = rng.uniform(0, math.tau)
            bx, by = x + math.cos(th) * R, y + math.sin(th) * R
            if not (0 < bx < WORLD and 0 < by < WORLD):
                continue
            ok, why, _ = los(t, x, y, t.ground(x, y) + 2.2,
                             bx, by, t.ground(bx, by) + 1.3)
            c[why] += 1
        n = sum(c.values()) or 1
        print("  %5d m   clear %5.1f%%   ground %5.1f%%   trees %5.1f%%"
              % (R, 100.0 * c[CLEAR] / n, 100.0 * c[BLOCKED_TERRAIN] / n,
                 100.0 * c[BLOCKED_FOLIAGE] / n))


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args and args[0] == "map":
        map_survey(args[1])
    elif args and args[0] == "profile":
        profile(args[1], *[float(v) for v in args[2:6]])
    elif args:
        survey(args[0])
    else:
        survey(r"M:\T34vsTiger\Missions\Campaign_1\Mission_2")
