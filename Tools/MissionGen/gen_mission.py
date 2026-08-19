"""TvT mission generator.

Clones a proven, working mission and varies the parts that make it a different
battle: a new advance corridor through open ground, and the whole order of battle
transformed onto it.

Why clone rather than emit from templates: a complete mission is ~3,850 lines of
.script across 8 files, and every one of them is already known-good. The template
(BerezovKursk) uses exactly ONE identifier prefix across all 135 of its names and
defines no classes outside it - verified - so a single prefix rename makes a clone
fully unique and free of the duplicate-class launch errors that bite unzipped
mission variants.

Everything the generator relies on was proven by hand first:
  - route generation validated leg-by-leg against the engine's own 20000-step A*
    budget                                     (2026-08-18)
  - zone-bitmap orientation measured, not assumed: pixel row 0 is world y=0
                                                (2026-08-18, 606 stock navpoints)
  - rigid transform of 80 objects with orientation, auto-nudged off blocked cells
                                                (2026-08-18)
  - Editor.exe round-trips a machine-written Content.script unharmed

Usage:
    python gen_mission.py --name Kursk02 --seed 7
    python gen_mission.py --name Kursk03 --seed 12 --points 34
"""

import argparse
import heapq
import math
import os
import random
import re
import shutil
import struct
from collections import deque

GAME = r"M:\T34vsTiger"
TEMPLATE = os.path.join(GAME, "Missions", "MyMission", "BerezovKursk")
TEMPLATE_PREFIX = b"BerezovKursk"
OUT_ROOT = os.path.join(GAME, "Missions", "MyMission")
MENU = os.path.join(GAME, "Scripts", "Menus", "MissionsMenu.script")

WORLD = 9000.0
PASSABLE = 1            # ZMC_OffRoad01
ENGINE_ASTAR_BUDGET = 20000
CLEARANCE = 3           # cells of clearance a route keeps from anything blocked
EDGE_MARGIN = 60        # cells to stay clear of the map edge


# ----------------------------------------------------------------- zone maps

class ZoneMap:
    """8-bit indexed zone bitmap.

    Row order: pixel row 0 is world y=0. These files declare a POSITIVE height,
    which by the BMP spec means bottom-up - the game ignores that. Measured
    2026-08-18 across 606 hand-placed navpoints in 12 stock missions: no-flip
    puts 7.8% of them in forest and 273 on road codes; bottom-up puts 44.8% in
    forest and 70 on roads, and no-flip wins in 11 of the 12 individually.
    """

    def __init__(self, path):
        d = open(path, "rb").read()
        self.data = d
        self.off = struct.unpack_from("<I", d, 10)[0]
        w, h = struct.unpack_from("<ii", d, 18)
        self.w, self.h = w, abs(h)
        self.stride = (w + 3) // 4 * 4
        self.cell_size = WORLD / w

    def at(self, cx, cy):
        if not (0 <= cx < self.w and 0 <= cy < self.h):
            return 150
        return self.data[self.off + cy * self.stride + cx]

    def world_to_cell(self, x, y):
        return int(x / self.cell_size), int(y / self.cell_size)

    def cell_to_world(self, c):
        half = self.cell_size / 2
        return c[0] * self.cell_size + half, c[1] * self.cell_size + half


def open_region(zm):
    """Largest 4-connected region of passable cells that keeps CLEARANCE cells
    away from anything blocked, and EDGE_MARGIN cells from the map edge."""
    w, h, R = zm.w, zm.h, CLEARANCE
    clear = bytearray(w * h)
    for y in range(R, h - R):
        base = y * w
        for x in range(R, w - R):
            if zm.at(x, y) != PASSABLE:
                continue
            ok = True
            for dy in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    if zm.at(x + dx, y + dy) != PASSABLE:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                clear[base + x] = 1

    seen = bytearray(w * h)
    best = []
    for sy in range(h):
        for sx in range(w):
            i = sy * w + sx
            if not clear[i] or seen[i]:
                continue
            q = deque([(sx, sy)])
            seen[i] = 1
            cells = []
            while q:
                x, y = q.popleft()
                cells.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    j = ny * w + nx
                    if 0 <= nx < w and 0 <= ny < h and clear[j] and not seen[j]:
                        seen[j] = 1
                        q.append((nx, ny))
            if len(cells) > len(best):
                best = cells
    return set(best)


def astar(cells, start, goal, limit=None):
    """8-connected A*. Returns the path, or None if `limit` steps are exceeded -
    matching how the engine gives up, so a route that passes here is one the
    engine can also solve."""
    heur = lambda c: math.hypot(c[0] - goal[0], c[1] - goal[1])
    openq = [(heur(start), 0.0, start)]
    came = {}
    best = {start: 0.0}
    steps = 0
    while openq:
        _, cost, cur = heapq.heappop(openq)
        steps += 1
        if limit and steps > limit:
            return None
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt not in cells:
                continue
            step = 1.4142 if dx and dy else 1.0
            if cost + step < best.get(nxt, 1e18):
                best[nxt] = cost + step
                came[nxt] = cur
                heapq.heappush(openq, (cost + step + heur(nxt), cost + step, nxt))
    return None


def pick_corridor(zm, cells, rng, target_len=5100.0, tolerance=0.08):
    """A corridor of roughly target_len world units that is as straight as the
    terrain allows. Straightness matters: a wandering route reads as confusion
    rather than an advance."""
    inner = [c for c in cells
             if EDGE_MARGIN <= c[0] < zm.w - EDGE_MARGIN
             and EDGE_MARGIN <= c[1] < zm.h - EDGE_MARGIN]
    if not inner:
        raise RuntimeError("no open ground away from the map edge")
    want = target_len / zm.cell_size
    best = None
    for start in rng.sample(inner, min(600, len(inner))):
        for goal in rng.sample(inner, min(40, len(inner))):
            straight = math.hypot(goal[0] - start[0], goal[1] - start[1])
            if abs(straight - want) > want * tolerance:
                continue
            path = astar(cells, start, goal)
            if not path:
                continue
            length = sum(math.hypot(path[i][0] - path[i - 1][0],
                                    path[i][1] - path[i - 1][1])
                         for i in range(1, len(path)))
            ratio = length / straight
            if best is None or ratio < best[0]:
                best = (ratio, path)
        if best and best[0] < 1.02:
            break
    if best is None:
        raise RuntimeError("no corridor of the requested length found")
    return best[1], best[0]


def resample(zm, path, count):
    """Even spacing along the path. Tight spacing is not cosmetic: the patrol
    queue only advances when the leader arrives, so a gap the leader cannot
    cross in one hop stalls the whole advance silently."""
    total = sum(math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
                for i in range(1, len(path))) * zm.cell_size
    step = total / (count - 1)
    pts = [path[0]]
    acc = 0.0
    for i in range(1, len(path)):
        acc += math.hypot(path[i][0] - path[i - 1][0],
                          path[i][1] - path[i - 1][1]) * zm.cell_size
        if acc >= step and len(pts) < count - 1:
            pts.append(path[i])
            acc = 0.0
    pts.append(path[-1])
    while len(pts) < count:
        pts.append(path[-1])
    return [zm.cell_to_world(c) for c in pts[:count]], total, step


# ----------------------------------------------------------------- heightmap

class HeightMap:
    SCALE = 621.32 / 8409.0          # from a Z the engine itself reported

    def __init__(self, path):
        raw = open(path, "rb").read()
        n = len(raw) // 2
        self.dim = int(math.isqrt(n))
        self.values = struct.unpack("<%dH" % n, raw)

    def at(self, x, y):
        gx = max(0, min(self.dim - 1, int(x / WORLD * (self.dim - 1))))
        gy = max(0, min(self.dim - 1, int(y / WORLD * (self.dim - 1))))
        return self.values[gy * self.dim + gx] * self.SCALE


# ----------------------------------------------------------------- mission text

COMPASS = [(22.5, "eastward"), (67.5, "north-eastward"), (112.5, "northward"),
           (157.5, "north-westward"), (202.5, "westward"), (247.5, "south-westward"),
           (292.5, "southward"), (337.5, "south-eastward"), (360.1, "eastward")]


def bearing_name(a, b):
    """Compass word for the advance. +X is east, +Y is north."""
    deg = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360.0
    for limit, word in COMPASS:
        if deg < limit:
            return word
    return "eastward"


def retitle(dest, name, route, title=None):
    """Give the clone its own name and a briefing that matches the battle it
    actually generated. Without this every clone inherits the template's name and
    shows up in the menu as a duplicate - and its briefing points the player the
    wrong way, since the corridor direction is different every time."""
    path = os.path.join(dest, "MissionTestStrings.script")
    b = open(path, "rb").read()
    heading = bearing_name(route[0], route[-1])
    distance = sum(math.hypot(route[i][0] - route[i - 1][0],
                              route[i][1] - route[i - 1][1])
                   for i in range(1, len(route)))
    shown = title or ("Kursk Steppe - %s advance (%s)" % (heading, name))

    def put(field, value):
        nonlocal b
        pat = re.compile((r'(final static WString %s\s*=\s*L")[^"]*(")' % field).encode())
        if pat.search(b):
            b = pat.sub(lambda m: m.group(1) + value.encode("cp1251") + m.group(2), b, count=1)

    put("MissionName", shown)
    put("BriefingText",
        "Your Tiger spearheads the attack across the Kursk steppe, with the Panzer IVs "
        "of Zug Falke alongside and KG Kaiser following behind. The axis of advance runs "
        "%s for some %d metres. Smash the anti-tank positions and armour barring the "
        "route, then press on. Move quickly - the assault depends on breaking through "
        "before the Russian can reinforce." % (heading, int(distance)))
    put("ObjectivesText",
        "Advance %s along the approach route and destroy the Soviet defence." % heading)
    put("Objective01", "Advance %s along the approach route" % heading)
    open(path, "wb").write(b)
    return shown


# ----------------------------------------------------------------- generation

MATRIX_RE = re.compile(
    rb'("([A-Za-z0-9_]+)",\s*\n\s*"(GameObject|UnitGroup|NavPoint)",\s*\n\s*'
    rb'"[A-Za-z0-9_]+",\s*\n\s*new Matrix\(\s*\n)'
    rb'(\s*)([-\d\.]+, [-\d\.]+, [-\d\.]+, )([-\d\.]+)(,\s*\n\s*)'
    rb'([-\d\.]+, [-\d\.]+, [-\d\.]+, )([-\d\.]+)(,\s*\n\s*)'
    rb'([-\d\.]+, [-\d\.]+, [-\d\.]+, )([-\d\.]+)')


def clone(name):
    dest = os.path.join(OUT_ROOT, name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(TEMPLATE, dest,
                    ignore=shutil.ignore_patterns("*.bak*", "__pycache__"))
    prefix = name.encode("ascii")
    renamed = 0
    for fn in os.listdir(dest):
        if not fn.endswith(".script"):
            continue
        p = os.path.join(dest, fn)
        b = open(p, "rb").read()
        if TEMPLATE_PREFIX in b:
            renamed += b.count(TEMPLATE_PREFIX)
            open(p, "wb").write(b.replace(TEMPLATE_PREFIX, prefix))
    return dest, renamed


def nudge(zm, x, y):
    cx, cy = zm.world_to_cell(x, y)
    if zm.at(cx, cy) == PASSABLE:
        return (x, y), 0.0
    for r in range(1, 60):
        best = None
        for dx in range(-r, r + 1):
            for dy in ((-r, r) if abs(dx) < r else range(-r, r + 1)):
                if zm.at(cx + dx, cy + dy) == PASSABLE:
                    p = zm.cell_to_world((cx + dx, cy + dy))
                    dist = math.hypot(p[0] - x, p[1] - y)
                    if best is None or dist < best[1]:
                        best = (p, dist)
        if best:
            return best
    return (x, y), -1.0


def retarget(dest, name, route, zm, hm):
    """Point the navpoints at the new corridor and carry the whole order of
    battle across with a rigid transform, so formations and defensive depth
    survive intact."""
    path = os.path.join(dest, "Content.script")
    src = open(path, "rb").read()

    nav_re = re.compile((name + r"Advance_(\d\d)").encode("ascii"))
    old = {}
    for m in MATRIX_RE.finditer(src):
        nm = m.group(2)
        a = nav_re.fullmatch(nm)
        if a:
            old[int(a.group(1))] = (float(m.group(6)), float(m.group(9)))
    if not old:
        raise RuntimeError("no advance navpoints found in the clone")

    first, last = min(old), max(old)
    oa, ob = old[first], old[last]
    na, nb = route[0], route[-1]
    ov = (ob[0] - oa[0], ob[1] - oa[1])
    nv = (nb[0] - na[0], nb[1] - na[1])
    scale = math.hypot(*nv) / math.hypot(*ov)
    theta = math.atan2(nv[1], nv[0]) - math.atan2(ov[1], ov[0])
    ct, st = math.cos(theta), math.sin(theta)

    def xform(x, y):
        dx, dy = (x - oa[0]) * scale, (y - oa[1]) * scale
        return na[0] + dx * ct - dy * st, na[1] + dx * st + dy * ct

    stats = {"nav": 0, "obj": 0, "nudged": 0, "stuck": 0}

    def replace(m):
        nm, kind = m.group(2), m.group(3)
        ox, oy = float(m.group(6)), float(m.group(9))
        a = nav_re.fullmatch(nm)
        if a:
            i = int(a.group(1)) - 1
            nx, ny = route[i] if i < len(route) else route[-1]
            stats["nav"] += 1
        else:
            nx, ny = xform(ox, oy)
            if kind == b"GameObject":
                (nx, ny), dist = nudge(zm, nx, ny)
                if dist > 0:
                    stats["nudged"] += 1
                elif dist < 0:
                    stats["stuck"] += 1
            stats["obj"] += 1
        nz = hm.at(nx, ny)
        r1 = [float(v) for v in m.group(5).decode().rstrip(", ").split(", ")]
        r2 = [float(v) for v in m.group(8).decode().rstrip(", ").split(", ")]
        n1 = [ct * r1[k] - st * r2[k] for k in range(3)]
        n2 = [st * r1[k] + ct * r2[k] for k in range(3)]
        fmt = lambda v: b"%f" % v
        return (m.group(1) + m.group(4)
                + b", ".join(fmt(v) for v in n1) + b", " + fmt(nx) + m.group(7)
                + b", ".join(fmt(v) for v in n2) + b", " + fmt(ny) + m.group(10)
                + m.group(11) + fmt(nz))

    open(path, "wb").write(MATRIX_RE.sub(replace, src))
    return stats


def validate(dest, name, zm):
    src = open(os.path.join(dest, "Content.script"), "rb").read()
    nav_re = re.compile((name + r"Advance_(\d\d)").encode("ascii"))
    pts, objs = {}, []
    for m in MATRIX_RE.finditer(src):
        x, y = float(m.group(6)), float(m.group(9))
        a = nav_re.fullmatch(m.group(2))
        if a:
            pts[int(a.group(1))] = (x, y)
        elif m.group(3) == b"GameObject":
            objs.append((m.group(2).decode(), x, y))

    cells = {(x, y) for y in range(zm.h) for x in range(zm.w)
             if zm.at(x, y) == PASSABLE}
    order = sorted(pts)
    bad_pts = [i for i in order if zm.at(*zm.world_to_cell(*pts[i])) != PASSABLE]
    bad_objs = [n for n, x, y in objs if zm.at(*zm.world_to_cell(x, y)) != PASSABLE]

    worst, unroutable = 0, []
    for i in range(1, len(order)):
        a = zm.world_to_cell(*pts[order[i - 1]])
        b = zm.world_to_cell(*pts[order[i]])
        steps = astar(cells, a, b, limit=ENGINE_ASTAR_BUDGET)
        if steps is None:
            unroutable.append((order[i - 1], order[i]))
        else:
            worst = max(worst, len(steps))
    return {"navpoints": len(order), "bad_navpoints": bad_pts,
            "objects": len(objs), "bad_objects": bad_objs,
            "unroutable": unroutable, "worst_leg": worst}


def register(name, side="Germany"):
    """Add the mission to the always-listed extra array. NOT the campaign array -
    that one is gated by GetUserValue("<X>Campaign"), so an entry appended there
    stays invisible until the player has unlocked that many campaign missions."""
    b = open(MENU, "rb").read()
    cls = ('"C%sMission"' % name).encode("ascii")
    if cls in b:
        return False
    marker = ("final static Array %s_ExtraMissions = [" % side).encode("ascii")
    i = b.index(marker) + len(marker)
    sep = b"\r\n" if b"\r\n" in b else b"\n"
    existing = b[i:b.index(b"];", i)].strip()
    # The comma goes AFTER the new entry, not before it: inserting straight after
    # the "[" means anything already there follows us.
    entry = sep + b"                " + cls + (b"," if existing else b"")
    open(MENU, "wb").write(b[:i] + entry + b[i:])
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True,
                    help="mission name, used as the folder AND the unique class prefix")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--points", type=int, default=34,
                    help="navpoints on the advance (the template defines 34)")
    ap.add_argument("--length", type=float, default=5100.0,
                    help="advance length in world units")
    ap.add_argument("--side", default="Germany", choices=["Germany", "USSR"])
    ap.add_argument("--title", default=None,
                    help="menu name; defaults to one describing the generated advance")
    ap.add_argument("--no-register", action="store_true")
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", args.name):
        ap.error("name must be alphanumeric and start with a letter - it becomes "
                 "a script class prefix")

    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    rng = random.Random(seed)
    print("generating %r  (seed %d)" % (args.name, seed))

    dest, renamed = clone(args.name)
    print("  cloned template, renamed %d identifiers" % renamed)

    zm = ZoneMap(os.path.join(dest, "RouterZone_Test.bmp"))
    hm = HeightMap(os.path.join(dest, "hmap.raw"))
    cells = open_region(zm)
    print("  open region: %d cells (%.1f%% of map)"
          % (len(cells), 100.0 * len(cells) / (zm.w * zm.h)))

    path, ratio = pick_corridor(zm, cells, rng, target_len=args.length)
    route, total, step = resample(zm, path, args.points)
    print("  corridor: %.0f units, straightness %.4f, %d navpoints ~%.0f apart"
          % (total, ratio, len(route), step))

    shown = retitle(dest, args.name, route, args.title)
    print("  titled %r" % shown)

    stats = retarget(dest, args.name, route, zm, hm)
    print("  placed %d navpoints, %d objects (%d nudged, %d unplaceable)"
          % (stats["nav"], stats["obj"], stats["nudged"], stats["stuck"]))

    v = validate(dest, args.name, zm)
    print("  VALIDATION")
    print("    navpoints on passable ground : %d/%d"
          % (v["navpoints"] - len(v["bad_navpoints"]), v["navpoints"]))
    print("    objects on passable ground   : %d/%d"
          % (v["objects"] - len(v["bad_objects"]), v["objects"]))
    print("    unroutable legs              : %d" % len(v["unroutable"]))
    print("    worst leg                    : %d A* steps (engine budget %d)"
          % (v["worst_leg"], ENGINE_ASTAR_BUDGET))

    ok = not v["bad_navpoints"] and not v["unroutable"] and not v["bad_objects"]
    if not args.no_register:
        if register(args.name, args.side):
            print("  registered in %s_ExtraMissions" % args.side)
        else:
            print("  already registered")

    cache = os.path.join(GAME, "Cache", "Scripts.cache")
    if os.path.exists(cache):
        os.remove(cache)
        print("  cleared Scripts.cache")

    print("  -> %s" % dest)
    print("  %s" % ("OK" if ok else "PROBLEMS FOUND - see validation above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
