"""Read and write TvT missions for the editor.

Everything here was established by measurement earlier in the project, and the
comments say which, because each one cost a real debugging session:

  - Content.script is CP1251. Round-tripping it through a UTF-8 assumption
    destroys every Cyrillic byte in the file, not just the edited region.
  - Line endings differ per mission - some CRLF, some LF - depending on which
    tool wrote them last. A regex anchored on a bare newline silently matches
    NOTHING on the other kind and the tool reports success having done nothing.
  - Zone bitmaps (RouterZone/TerrainZone) are stored TOP-DOWN: pixel row 0 is
    world y=0, despite a positive BMP height field which by spec means bottom-up.
  - hmap.raw is the OPPOSITE - stored FLIPPED, row 0 is world y=MAX - and the
    height factor is 0.07, not the 0.0739 an early single-sample guess produced.

Object matrices are 4x4 row-major with the position in the 4th column, and the
rotation's first COLUMN is the object's forward direction in world space.
"""

import math
import os
import re
import struct

GAME = r"M:\T34vsTiger"
MISSIONS = os.path.join(GAME, "Missions", "MyMission")
WORLD = 9000.0
HEIGHT_FACTOR = 0.07

PASSABLE = 1
FOREST = {11, 12, 13, 14, 20}
BLOCKED = {150, 101, 102}

# Rough real dimensions in metres (length, width, height) so a box reads as the
# thing it stands for. Not exact - the point is that a Tiger looks like a Tiger
# next to a rifleman, and a gun position is legible from above.
DIMS = {
    "CTankPzVIAusfEUnit":      (6.3, 3.7, 3.0),
    "CTankPzIVGUnit":          (5.9, 2.9, 2.7),
    "CTankT34_76_42Unit":      (6.1, 3.0, 2.5),
    "CTankT34_85_44Unit":      (6.1, 3.0, 2.7),
    "CSAUSU85Unit":            (8.2, 3.0, 2.5),
    "CSAUStuG40Unit":          (6.8, 2.9, 2.2),
    "CGunPak40Unit":           (6.2, 2.0, 1.3),
    "CGunZis3Unit":            (6.1, 1.6, 1.4),
    "CGunNebelUnit":           (4.0, 2.0, 1.6),
    "CBtrHanomag251AusfCUnit": (5.8, 2.1, 1.8),
    "CBtrM3A1HalftruckUnit":   (6.2, 2.2, 2.3),
    "CTruckOpelBlitzUnit":     (6.0, 2.3, 2.5),
    "CTruckZis5Unit":          (6.1, 2.2, 2.3),
    "CGermanSoldierRifleUnit": (0.6, 0.6, 1.8),
    "CSovietSoldierRifleUnit": (0.6, 0.6, 1.8),
    "CBarricadePakUnit":       (4.0, 1.0, 1.2),
    "CBarricadeFenceUnit":     (4.0, 0.4, 1.2),
    "CSandBagsUnit":           (3.0, 1.0, 1.0),
    "CDotConcreteUnit":        (4.0, 4.0, 2.0),
}
DEFAULT_DIM = (3.0, 3.0, 2.0)

OBJ_RE = re.compile(
    r'(    \[\s*\n\s*"([A-Za-z0-9_]+)",\s*\n\s*"(GameObject|UnitGroup|NavPoint|ObjectsGroup|Locator|InteriorObject)",\s*\n\s*'
    r'"([A-Za-z0-9_]*)",\s*\n\s*new Matrix\(\s*\n)'
    r'(\s*)([-\d\.]+), ([-\d\.]+), ([-\d\.]+), ([-\d\.]+),(\s*\n\s*)'
    r'([-\d\.]+), ([-\d\.]+), ([-\d\.]+), ([-\d\.]+),(\s*\n\s*)'
    r'([-\d\.]+), ([-\d\.]+), ([-\d\.]+), ([-\d\.]+)(.*?\n    \],\n)', re.S)


def read_text(path):
    """Returns (text, was_crlf). Normalised to \\n for processing."""
    raw = open(path, "rb").read()
    return raw.replace(b"\r\n", b"\n").decode("cp1251"), (b"\r\n" in raw)


def write_text(path, text, was_crlf):
    blob = text.encode("cp1251")
    open(path, "wb").write(blob.replace(b"\n", b"\r\n") if was_crlf else blob)


class ZoneMap:
    """Row 0 is world y=0 - no flip. Measured across 606 hand-placed navpoints in
    12 stock missions: no-flip puts 7.8% of them in forest, bottom-up 44.8%."""

    def __init__(self, path):
        d = open(path, "rb").read()
        self.d = d
        self.off = struct.unpack_from("<I", d, 10)[0]
        w, h = struct.unpack_from("<ii", d, 18)
        self.w, self.h = w, abs(h)
        self.stride = (w + 3) // 4 * 4
        self.cell = WORLD / w

    def at_cell(self, cx, cy):
        if not (0 <= cx < self.w and 0 <= cy < self.h):
            return 150
        return self.d[self.off + cy * self.stride + cx]

    def at(self, x, y):
        return self.at_cell(int(x / self.cell), int(y / self.cell))

    def downsample(self, step):
        """A coarse grid for the overlay - the full 1024x1024 is more than the
        browser needs to show where the going is good."""
        out = []
        for cy in range(0, self.h, step):
            row = []
            for cx in range(0, self.w, step):
                v = self.at_cell(cx, cy)
                row.append(0 if v == PASSABLE else (1 if v in FOREST else 2))
            out.append(row)
        return out


class HeightMap:
    """Stored FLIPPED - row 0 is world y=MAX - the opposite of the zone bitmaps.
    Z = flipped_raw * 0.07, validated against 79 hand-placed stock objects
    (mean deviation +0.83 m, RMS 1.15 m)."""

    def __init__(self, path):
        raw = open(path, "rb").read()
        n = len(raw) // 2
        self.dim = int(math.isqrt(n))
        self.v = struct.unpack("<%dH" % n, raw)

    def at(self, x, y):
        gx = max(0, min(self.dim - 1, int(x / WORLD * (self.dim - 1))))
        gy = max(0, min(self.dim - 1, self.dim - 1 - int(y / WORLD * (self.dim - 1))))
        return self.v[gy * self.dim + gx] * HEIGHT_FACTOR

    def grid(self, n):
        """n x n samples of world height, row 0 = world y=0."""
        out = []
        for iy in range(n):
            y = iy * WORLD / (n - 1)
            out.append([round(self.at(ix * WORLD / (n - 1), y), 2) for ix in range(n)])
        return out


def mission_dir(name):
    return os.path.join(MISSIONS, name)


def list_missions():
    if not os.path.isdir(MISSIONS):
        return []
    out = []
    for d in sorted(os.listdir(MISSIONS)):
        if os.path.exists(os.path.join(MISSIONS, d, "Content.script")):
            out.append(d)
    return out


def _find(folder, prefix):
    for fn in os.listdir(folder):
        if fn.lower().startswith(prefix) and fn.lower().endswith(".bmp"):
            return os.path.join(folder, fn)
    return None


def load(name, grid=129, zone_step=4):
    folder = mission_dir(name)
    src, _ = read_text(os.path.join(folder, "Content.script"))

    objects = []
    for m in OBJ_RE.finditer(src):
        cls = m.group(4)
        kind = m.group(3)
        r0 = (float(m.group(6)), float(m.group(7)), float(m.group(8)))
        r1 = (float(m.group(11)), float(m.group(12)), float(m.group(13)))
        dims = DIMS.get(cls, DEFAULT_DIM)
        # forward = first COLUMN of the rotation
        objects.append({
            "name": m.group(2), "kind": kind, "cls": cls,
            "x": float(m.group(9)), "y": float(m.group(14)), "z": float(m.group(19)),
            "fx": r0[0], "fy": r1[0],
            "dims": dims,
            "props": m.group(20)[:0],     # kept out of the payload; server rewrites in place
        })

    groups = {}
    for m in re.finditer(r'"(\w+)",\s*\n\s*"UnitGroup",.*?\["Units",\s*\[(.*?)\]\]', src, re.S):
        groups[m.group(1)] = re.findall(r'"(\w+)"', m.group(2))

    paths = {}
    for m in re.finditer(r'"(\w+)",\s*\n\s*"UnitGroup",.*?\["Path",\s*\[(.*?)\]\]', src, re.S):
        paths[m.group(1)] = re.findall(r'"(\w+)"', m.group(2))

    hm = HeightMap(os.path.join(folder, "hmap.raw"))
    router = ZoneMap(_find(folder, "routerzone"))
    terrain = ZoneMap(_find(folder, "terrainzone"))

    title = ""
    ts = os.path.join(folder, "MissionTestStrings.script")
    if os.path.exists(ts):
        t, _ = read_text(ts)
        mt = re.search(r'MissionName\s*=\s*L"([^"]*)"', t)
        if mt:
            title = mt.group(1)

    return {
        "name": name, "title": title, "world": WORLD,
        "heights": hm.grid(grid), "gridN": grid,
        "router": router.downsample(zone_step),
        "terrain": terrain.downsample(zone_step),
        "zoneStep": zone_step, "zoneW": router.w // zone_step,
        "objects": objects, "groups": groups, "paths": paths,
    }


def save_positions(name, moves):
    """moves: {objectName: {x, y}} - Z is recomputed from the heightmap so a
    dragged object always sits on the ground."""
    folder = mission_dir(name)
    path = os.path.join(folder, "Content.script")
    src, crlf = read_text(path)
    hm = HeightMap(os.path.join(folder, "hmap.raw"))
    changed = [0]

    def repl(m):
        nm = m.group(2)
        if nm not in moves:
            return m.group(0)
        mv = moves[nm]
        x, y = float(mv["x"]), float(mv["y"])
        z = hm.at(x, y)
        changed[0] += 1
        f = lambda v: "%f" % v
        # The commas after X and Y are LITERAL in OBJ_RE, not captured, so they
        # have to be written back explicitly. Leaving them out produces
        # syntactically broken script that still looks plausible in a diff -
        # caught here only because the output was read back rather than trusted.
        return (m.group(1) + m.group(5)
                + ", ".join([m.group(6), m.group(7), m.group(8)]) + ", " + f(x) + "," + m.group(10)
                + ", ".join([m.group(11), m.group(12), m.group(13)]) + ", " + f(y) + "," + m.group(15)
                + ", ".join([m.group(16), m.group(17), m.group(18)]) + ", " + f(z)
                + m.group(20))

    out = OBJ_RE.sub(repl, src)
    write_text(path, out, crlf)
    return changed[0]
