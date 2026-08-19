"""Local server for the TvT mission editor.

Serves the editor page and exposes the real mission files as JSON. Writes go
straight back to Content.script in the live install, so the result stays
interoperable with the real Editor rather than replacing it - the round-trip was
proven earlier: a machine-written Content.script opened in Editor.exe, was edited
by hand, saved, and came back clean with its CP1251 encoding intact.

    python server.py            # http://127.0.0.1:8765
    python server.py --port N
"""

import argparse
import json
import math
import os
import posixpath
import re
import struct
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

import mission_io as M

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ENGINE_ASTAR_BUDGET = 20000


def astar(zm, start, goal, limit=ENGINE_ASTAR_BUDGET):
    """The engine gives up after 20000 steps and logs
    `[Router] Path Generated in more than 20000 iterations` followed by
    `OnUnreacheable`. Matching that budget means a route the editor calls good is
    one the engine can also solve - the check whose absence cost an afternoon."""
    import heapq
    if zm.at_cell(*start) != M.PASSABLE or zm.at_cell(*goal) != M.PASSABLE:
        return None, 0
    h = lambda c: math.hypot(c[0] - goal[0], c[1] - goal[1])
    openq = [(h(start), 0.0, start)]
    best = {start: 0.0}
    steps = 0
    while openq:
        _, cost, cur = heapq.heappop(openq)
        steps += 1
        if steps > limit:
            return None, steps
        if cur == goal:
            return steps, steps
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            n = (cur[0] + dx, cur[1] + dy)
            if zm.at_cell(*n) != M.PASSABLE:
                continue
            c = cost + (1.4142 if dx and dy else 1.0)
            if c < best.get(n, 1e18):
                best[n] = c
                heapq.heappush(openq, (c + h(n), c, n))
    return None, steps


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC, **kw)

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            print("  %s" % (fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/missions":
            return self._json({"missions": M.list_missions()})
        m = re.match(r"^/api/mission/([A-Za-z0-9_]+)$", path)
        if m:
            try:
                return self._json(M.load(m.group(1)))
            except Exception as e:
                return self._json({"error": "%s: %s" % (type(e).__name__, e)}, 500)
        return super().do_GET()

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            return self._json({"error": "bad JSON: %s" % e}, 400)

        m = re.match(r"^/api/mission/([A-Za-z0-9_]+)/save$", self.path)
        if m:
            try:
                n = M.save_positions(m.group(1), payload.get("moves", {}))
                cache = os.path.join(M.GAME, "Cache", "Scripts.cache")
                if os.path.exists(cache):
                    os.remove(cache)
                return self._json({"saved": n, "cacheCleared": True})
            except Exception as e:
                return self._json({"error": "%s: %s" % (type(e).__name__, e)}, 500)

        m = re.match(r"^/api/mission/([A-Za-z0-9_]+)/validate$", self.path)
        if m:
            try:
                return self._json(self._validate(m.group(1), payload))
            except Exception as e:
                return self._json({"error": "%s: %s" % (type(e).__name__, e)}, 500)

        return self._json({"error": "unknown endpoint"}, 404)

    def _validate(self, name, payload):
        """Route legs against the engine's own budget, plus the three silent
        killers found this session: objects off the map, objects sharing one
        point (four T-34s in a single spot crashed the physics), and objects on
        ground nothing can drive to."""
        folder = M.mission_dir(name)
        zm = M.ZoneMap(M._find(folder, "routerzone"))
        pts = payload.get("route", [])
        objs = payload.get("objects", [])

        legs, worst = [], 0
        for i in range(1, len(pts)):
            a = (int(pts[i - 1]["x"] / zm.cell), int(pts[i - 1]["y"] / zm.cell))
            b = (int(pts[i]["x"] / zm.cell), int(pts[i]["y"] / zm.cell))
            ok, steps = astar(zm, a, b)
            worst = max(worst, steps)
            if not ok:
                legs.append(i)

        off_map, stacked, blocked = [], [], []
        seen = {}
        for o in objs:
            x, y = o["x"], o["y"]
            if not (0 <= x <= M.WORLD and 0 <= y <= M.WORLD):
                off_map.append(o["name"])
                continue
            key = (round(x, 1), round(y, 1))
            if key in seen:
                stacked.append("%s/%s" % (seen[key], o["name"]))
            else:
                seen[key] = o["name"]
            if o.get("kind") == "GameObject" and zm.at(x, y) != M.PASSABLE:
                blocked.append(o["name"])

        return {"unroutableLegs": legs, "worstLeg": worst,
                "budget": ENGINE_ASTAR_BUDGET, "offMap": off_map,
                "stacked": stacked, "onBlocked": blocked}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("TvT mission editor on http://127.0.0.1:%d" % args.port)
    print("  missions: %s" % ", ".join(M.list_missions()))
    srv.serve_forever()


if __name__ == "__main__":
    main()
