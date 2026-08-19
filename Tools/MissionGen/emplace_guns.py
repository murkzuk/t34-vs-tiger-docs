"""Turn bare anti-tank guns into proper gun positions.

An AI-authored mission tends to drop a gun on the map and stop there. A real
Pakfront position has a crew serving the gun, something to shoot from behind, and
the vehicle that towed it into place. TvT ships all three and its own missions use
them - this just applies the same convention.

Modelled on Campaign_1/Mission_1, where every gun looks like:

    LeftAntiTank_1            CGunPak40Unit
      _8                      CBarricadePakUnit          0.8m
      LeftAntiTank_1_Gunner_1 CGermanSoldierRifleUnit    2.5m   ["Guncrew", true]
      LeftAntiTank_1_Gunner_2 CGermanSoldierRifleUnit    2.4m   ["Guncrew", true]
      _91                     CBarricadeFenceUnit        8.4m

`["Guncrew", true]` is the property that ties a soldier to the gun - without it a
rifleman standing next to a Pak is just a rifleman standing next to a Pak.

Everything placed here gets `["SurfaceControl", "PutonGround"]` (or the Upright /
LandingJoints variants), which the engine uses 946 times across the stock missions
to snap an object down onto the terrain. Stock gives CBarricadePakUnit "None" and
relies on an exact authored Z; ours are placed programmatically from a heightmap
whose sampling was measurably wrong, so letting the engine do it is both correct
and robust. The user spotted this: "there is a put on ground option in the editor".

Usage:
    python emplace_guns.py --mission BerezovKursk
    python emplace_guns.py --mission Kursk03 --no-trucks
"""

import argparse
import math
import os
import re
import struct

GAME = r"M:\T34vsTiger"
MISSIONS = os.path.join(GAME, "Missions", "MyMission")
WORLD = 9000.0

# gun class -> (soldier class, prime mover class)
NATION = {
    "CGunZis3Unit":  ("CSovietSoldierRifleUnit", "CTruckZis5Unit"),
    "CGunPak40Unit": ("CGermanSoldierRifleUnit", "CTruckOpelBlitzUnit"),
}

BARRICADE = "CBarricadePakUnit"
SANDBAGS = "CSandBagsUnit"

# how far from the gun each piece sits, along the gun's own facing
BARRICADE_FWD = 0.8
SANDBAG_FWD = 2.2
SANDBAG_SIDE = 2.6
CREW_BACK = 2.5
CREW_SIDE = 1.3
TRUCK_BACK = 26.0
TRUCK_SIDE = 4.0

OBJ_RE = re.compile(
    r'\[\s*\n\s*"([A-Za-z0-9_]+)",\s*\n\s*"GameObject",\s*\n\s*"([A-Za-z0-9_]+)",\s*\n'
    r'\s*new Matrix\(\s*\n'
    r'\s*([-\d\.]+), ([-\d\.]+), ([-\d\.]+), ([-\d\.]+),\s*\n'
    r'\s*([-\d\.]+), ([-\d\.]+), ([-\d\.]+), ([-\d\.]+),\s*\n'
    r'\s*([-\d\.]+), ([-\d\.]+), ([-\d\.]+), ([-\d\.]+),.*?\n\s*\),\s*\n'
    r'\s*\[(.*?)\n      \]\s*\n    \],', re.S)


class Router:
    def __init__(self, path):
        d = open(path, "rb").read()
        self.d = d
        self.off = struct.unpack_from("<I", d, 10)[0]
        w, h = struct.unpack_from("<ii", d, 18)
        self.w, self.h = w, abs(h)
        self.stride = (w + 3) // 4 * 4
        self.cs = WORLD / w

    def passable(self, x, y):
        cx, cy = int(x / self.cs), int(y / self.cs)
        if not (0 <= cx < self.w and 0 <= cy < self.h):
            return False
        return self.d[self.off + cy * self.stride + cx] == 1


def facing_rotation(fx, fy):
    """Rotation whose local +X points along (fx, fy), Z still up.

    Columns of the rotation are the local axes in world space, so col0 = (fx,fy,0),
    col2 = (0,0,1), col1 = col2 x col0 = (-fy,fx,0). Verified against the stock
    Campaign_1/Mission_1 guns, whose matrices satisfy exactly this relation.
    """
    n = math.hypot(fx, fy) or 1.0
    fx, fy = fx / n, fy / n
    return ((fx, -fy, 0.0),
            (fy,  fx, 0.0),
            (0.0, 0.0, 1.0))


def read_route(src):
    """The advance navpoints, whatever the mission's prefix."""
    pts = {}
    pat = re.compile(r'"(\w*Advance_(\d\d))",\s*\n\s*"NavPoint",\s*\n\s*'
                     r'"[A-Za-z0-9_]+",\s*\n\s*new Matrix\(([^)]*)\)')
    for m in pat.finditer(src):
        n = [float(v) for v in re.findall(r'-?\d+\.?\d*', m.group(3))]
        pts[int(m.group(2))] = (n[3], n[7])
    return [pts[k] for k in sorted(pts)]


def matrix_block(rot, x, y, z):
    (a, b, c), (d, e, f), (g, h, i) = rot
    return ("      new Matrix(\n"
            "          %f, %f, %f, %f,\n"
            "          %f, %f, %f, %f,\n"
            "          %f, %f, %f, %f,\n"
            "          0.000000, 0.000000, 0.000000, 1.000000\n"
            "        ),\n" % (a, b, c, x, d, e, f, y, g, h, i, z))


def make_object(name, cls, rot, x, y, z, props):
    body = ",\n".join("        " + p for p in props)
    return ('    [\n      "%s",\n      "GameObject",\n      "%s",\n%s      [\n%s\n      ]\n    ],\n'
            % (name, cls, matrix_block(rot, x, y, z), body))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mission", required=True)
    ap.add_argument("--crew", type=int, default=2, help="gunners per gun")
    ap.add_argument("--no-trucks", action="store_true",
                    help="skip the prime movers")
    ap.add_argument("--keep-facing", action="store_true",
                    help="leave gun rotations alone (default: turn them to face the advance)")
    ap.add_argument("--no-cover", action="store_true",
                    help="skip barricades and sandbags")
    args = ap.parse_args()

    folder = os.path.join(MISSIONS, args.mission)
    content = os.path.join(folder, "Content.script")
    if not os.path.exists(content):
        ap.error("no such mission: %s" % folder)

    router = None
    for fn in os.listdir(folder):
        if fn.lower().startswith("routerzone") and fn.lower().endswith(".bmp"):
            router = Router(os.path.join(folder, fn))
            break

    raw = open(content, "rb").read()
    src = raw.decode("cp1251")

    guns, existing = [], set()
    for m in OBJ_RE.finditer(src):
        name, cls = m.group(1), m.group(2)
        existing.add(name)
        if cls in NATION:
            rot = ((float(m.group(3)), float(m.group(4)), float(m.group(5))),
                   (float(m.group(7)), float(m.group(8)), float(m.group(9))),
                   (float(m.group(11)), float(m.group(12)), float(m.group(13))))
            aff = re.search(r'\["Affiliation",\s*"(\w+)"\]', m.group(15))
            guns.append({"name": name, "cls": cls, "rot": rot,
                         "x": float(m.group(6)), "y": float(m.group(10)),
                         "z": float(m.group(14)),
                         "aff": aff.group(1) if aff else "ENEMY",
                         "props": m.group(15)})

    if not guns:
        print("no anti-tank guns found in %s" % args.mission)
        return 0

    print("%s: %d guns" % (args.mission, len(guns)))
    additions = []
    counts = {"crew": 0, "barricade": 0, "sandbag": 0, "truck": 0, "skipped": 0}

    route = read_route(src)
    refaced = 0

    for g in guns:
        soldier, truck = NATION[g["cls"]]
        # local +X in world space is the first COLUMN of the rotation
        fx, fy = g["rot"][0][0], g["rot"][1][0]
        n = math.hypot(fx, fy) or 1.0
        fx, fy = fx / n, fy / n

        # A defending gun must face the threat. Measured on Berezov: not one of
        # its seven guns faced the advance - two pointed 150 degrees away - because
        # the original placement was arbitrary and the mission was later rotated
        # bodily onto a new corridor, which destroyed whatever intent there was.
        # Everything below is placed relative to this facing, so it has to be right
        # before the crew and cover go down.
        if route and not args.keep_facing:
            gx, gy = g["x"], g["y"]
            tx, ty = min(route, key=lambda p: math.hypot(p[0] - gx, p[1] - gy))
            dx, dy = tx - gx, ty - gy
            if math.hypot(dx, dy) > 1.0:
                off = math.degrees(math.acos(max(-1.0, min(1.0,
                      (fx * dx + fy * dy) / math.hypot(dx, dy)))))
                if off > 15.0:
                    g["rot"] = facing_rotation(dx, dy)
                    d = math.hypot(dx, dy)
                    fx, fy = dx / d, dy / d
                    g["refaced"] = off
                    refaced += 1
        lx, ly = -fy, fx                      # left of the gun

        # already emplaced? don't double up
        if g["name"] + "_Gunner_1" in existing:
            counts["skipped"] += 1
            continue

        for k in range(args.crew):
            side = (k - (args.crew - 1) / 2.0) * CREW_SIDE
            x = g["x"] - fx * CREW_BACK + lx * side
            y = g["y"] - fy * CREW_BACK + ly * side
            additions.append(make_object(
                "%s_Gunner_%d" % (g["name"], k + 1), soldier, g["rot"], x, y, g["z"],
                ['["Affiliation", "%s"]' % g["aff"],
                 '["Guncrew", true]',
                 '["SurfaceControl", "PutonGroundUpright"]',
                 '["Task", "CBaseAITask"]']))
            counts["crew"] += 1

        if not args.no_cover:
            additions.append(make_object(
                "%s_Cover" % g["name"], BARRICADE, g["rot"],
                g["x"] + fx * BARRICADE_FWD, g["y"] + fy * BARRICADE_FWD, g["z"],
                ['["HitPoints", -1.000000]',
                 '["SurfaceControl", "PutonGround"]',
                 '["Affiliation", "NEUTRAL"]',
                 '["Route", []]',
                 '["ShadowPlaneOffset", 0.050000]',
                 '["FakeShadowOffset", 0.090000]']))
            counts["barricade"] += 1
            for s, side in (("L", SANDBAG_SIDE), ("R", -SANDBAG_SIDE)):
                additions.append(make_object(
                    "%s_Sand%s" % (g["name"], s), SANDBAGS, g["rot"],
                    g["x"] + fx * SANDBAG_FWD + lx * side,
                    g["y"] + fy * SANDBAG_FWD + ly * side, g["z"],
                    ['["HitPoints", -1.000000]',
                     '["SurfaceControl", "PutonGround"]',
                     '["Affiliation", "NEUTRAL"]',
                     '["Route", []]']))
                counts["sandbag"] += 1

        if not args.no_trucks:
            tx = g["x"] - fx * TRUCK_BACK + lx * TRUCK_SIDE
            ty = g["y"] - fy * TRUCK_BACK + ly * TRUCK_SIDE
            if router and not router.passable(tx, ty):
                # a lorry cannot have driven somewhere a lorry cannot drive
                tx = g["x"] - fx * TRUCK_BACK
                ty = g["y"] - fy * TRUCK_BACK
            if not router or router.passable(tx, ty):
                additions.append(make_object(
                    "%s_Tractor" % g["name"], truck, g["rot"], tx, ty, g["z"],
                    ['["Affiliation", "%s"]' % g["aff"],
                     '["SurfaceControl", "PutonGroundLandingJoints"]',
                     '["Task", "CBaseAITask"]']))
                counts["truck"] += 1

    if not additions:
        print("  nothing to do - already emplaced")
        return 0

    # Write the corrected facings back into the guns' own matrices. Position
    # (the 4th column) is preserved exactly - only the rotation changes.
    out = src
    for g in guns:
        if "refaced" not in g:
            continue
        pat = re.compile(
            r'("%s",\s*\n\s*"GameObject",\s*\n\s*"%s",\s*\n\s*new Matrix\(\s*\n)'
            r'\s*[-\d\.]+, [-\d\.]+, [-\d\.]+, ([-\d\.]+),\s*\n'
            r'\s*[-\d\.]+, [-\d\.]+, [-\d\.]+, ([-\d\.]+),\s*\n'
            r'\s*[-\d\.]+, [-\d\.]+, [-\d\.]+, ([-\d\.]+),'
            % (re.escape(g["name"]), re.escape(g["cls"])))
        r0, r1, r2 = g["rot"]

        def rep(m, r0=r0, r1=r1, r2=r2):
            return (m.group(1)
                    + "          %f, %f, %f, %s,\n" % (r0[0], r0[1], r0[2], m.group(2))
                    + "          %f, %f, %f, %s,\n" % (r1[0], r1[1], r1[2], m.group(3))
                    + "          %f, %f, %f, %s," % (r2[0], r2[1], r2[2], m.group(4)))

        out, n = pat.subn(rep, out, count=1)
        if not n:
            print("  WARNING: could not rewrite the matrix for %s" % g["name"])

    marker = out.rindex("\n    ],") + len("\n    ],\n")
    out = out[:marker] + "".join(additions) + out[marker:]
    open(content, "wb").write(out.encode("cp1251"))

    if refaced:
        print("  re-faced    %d guns onto the advance" % refaced)
    print("  crew        %d" % counts["crew"])
    print("  barricades  %d" % counts["barricade"])
    print("  sandbags    %d" % counts["sandbag"])
    print("  prime movers %d" % counts["truck"])
    if counts["skipped"]:
        print("  skipped     %d (already had crew)" % counts["skipped"])

    cache = os.path.join(GAME, "Cache", "Scripts.cache")
    if os.path.exists(cache):
        os.remove(cache)
        print("  cleared Scripts.cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
