"""
Lay a drivable navpoint route across a generated TvT map, and rewrite the
mission's Content.script navpoint positions to match.

Two hard-won constraints drive the design:

1. TvT cannot bridge large gaps between navpoints. SetOrder_MoveToEx queues one
   MoveTo per point, each completing on "OnLeaderStopped"; if the leader cannot
   reach the next point in one hop the queue stalls silently with nothing in the
   log. Measured on Berezov: ~180-unit spacing completed 6 hops, ~900-unit
   spacing completed only 2-3. So: keep the spacing tight.

2. The route must stay on cells the ROUTER map calls drivable, which is not the
   same as cells that look like open ground. Berezov's original router map was
   60% forest under 80% grass visuals, which is why advances died on open steppe.

The route is laid greedily west to east, testing candidate headings against the
router map and refusing forest and non-passable cells.
"""

import math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tvt_terrain as T

WORLD = 9000.0            # MatrixWidth/MatrixHeight from WorldMatricies.script
STEP = 170.0              # world units between navpoints - deliberately tight


def load_router(path):
    w, h, pal, rows = T.read_bmp8(path)
    return w, h, rows


def drivable(rows, dim, x, y):
    """World coords -> router cell. Forest and non-passable both refused: forest
    is technically traversable but is exactly what stalled the original."""
    px = int(x / WORLD * dim)
    py = int(y / WORLD * dim)
    if not (0 <= px < dim and 0 <= py < dim):
        return False
    c = rows[py][px]
    return c not in T.FOREST_CODES and c != T.ZMC["NonPassable"]


def lay_route(rows, dim, start, goal, n_points):
    """A* across the router grid, then resample the path at STEP intervals.

    Greedy marching was tried first and failed: it got boxed in by a forest blob
    and wandered north-west, covering 1842 units instead of 4900. A* is what the
    engine's own router does, and it cannot be trapped by local obstacles.

    Forest is costly rather than forbidden - it is genuinely traversable, and
    refusing it outright is what left the greedy version with nowhere to go.
    """
    import heapq
    sx, sy = int(start[0]/WORLD*dim), int(start[1]/WORLD*dim)
    gx, gy = int(goal[0]/WORLD*dim),  int(goal[1]/WORLD*dim)

    def cost(px, py):
        c = rows[py][px]
        if c == T.ZMC["NonPassable"]: return None
        return 4.0 if c in T.FOREST_CODES else 1.0

    openq = [(0.0, sx, sy)]
    came, g = {}, {(sx, sy): 0.0}
    seen = set()
    while openq:
        _, x, y = heapq.heappop(openq)
        if (x, y) in seen: continue
        seen.add((x, y))
        if abs(x-gx) <= 2 and abs(y-gy) <= 2:
            gx, gy = x, y
            break
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx == dy == 0: continue
                nx, ny = x+dx, y+dy
                if not (0 <= nx < dim and 0 <= ny < dim): continue
                c = cost(nx, ny)
                if c is None: continue
                step = c * (1.414 if dx and dy else 1.0)
                ng = g[(x, y)] + step
                if ng < g.get((nx, ny), 1e18):
                    g[(nx, ny)] = ng
                    came[(nx, ny)] = (x, y)
                    h = math.hypot(nx-gx, ny-gy)
                    heapq.heappush(openq, (ng + h, nx, ny))
    if (gx, gy) not in came and (gx, gy) != (sx, sy):
        raise RuntimeError("A*: no drivable route between those points")

    cells = []
    cur = (gx, gy)
    while cur != (sx, sy):
        cells.append(cur); cur = came[cur]
    cells.append((sx, sy)); cells.reverse()

    # resample the cell path at STEP world units
    pts, acc = [start], 0.0
    px, py = start
    for (cx, cy) in cells:
        wx, wy = (cx + 0.5)/dim*WORLD, (cy + 0.5)/dim*WORLD
        d = math.hypot(wx-px, wy-py)
        acc += d
        if acc >= STEP:
            pts.append((wx, wy)); acc = 0.0
        px, py = wx, wy
    if len(pts) > n_points:
        keep = [pts[round(i*(len(pts)-1)/(n_points-1))] for i in range(n_points)]
        pts = keep
    return pts


def rewrite_navpoints(content_path, prefix, pts, z=610.0):
    """Replace the translation column of each named navpoint's matrix, in place
    and byte-safe - the file is CP1251 and must not be re-encoded."""
    raw = Path(content_path).read_bytes()
    hi_before = bytes(c for c in raw if c >= 0x80)
    changed = 0
    for i, (x, y) in enumerate(pts, 1):
        name = f"{prefix}{i:02d}".encode()
        m = re.search(rb'"' + re.escape(name) + rb'"(.{0,400}?)new Matrix\((.*?)\)',
                      raw, re.S)
        if not m:
            continue
        body = m.group(2)
        nums = re.findall(rb'-?\d+\.\d+', body)
        if len(nums) < 12:
            continue
        new_body = body
        for idx, val in ((3, x), (7, y), (11, z)):
            new_body = new_body.replace(nums[idx], b"%.6f" % val, 1)
        raw = raw[:m.start(2)] + new_body + raw[m.end(2):]
        changed += 1
    hi_after = bytes(c for c in raw if c >= 0x80)
    assert hi_before == hi_after, "CP1251 bytes changed - aborting"
    Path(content_path).write_bytes(raw)
    return changed


if __name__ == "__main__":
    mission = Path(r"M:\T34vsTiger\Missions\MyMission\BerezovKursk")
    dim, _, rows = load_router(mission / "RouterZone_Test.bmp")
    dim = 1024

    start = (568.0, 6828.0)        # Zug Falke's own start position
    pts = lay_route(rows, dim, start, (5400.0, 6500.0), n_points=34)
    print(f"laid {len(pts)} navpoints")
    print(f"  start {pts[0][0]:.0f},{pts[0][1]:.0f}   end {pts[-1][0]:.0f},{pts[-1][1]:.0f}")
    span = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
    print(f"  straight-line span {span:.0f} units, mean spacing "
          f"{sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1))/max(1,len(pts)-1):.0f}")
    bad = [i for i, (x, y) in enumerate(pts, 1) if not drivable(rows, dim, x, y)]
    print(f"  points on non-drivable ground: {bad or 'NONE'}")

    n = rewrite_navpoints(mission / "Content.script", "BerezovKurskAdvance_", pts)
    print(f"  rewrote {n} navpoint positions in Content.script")
