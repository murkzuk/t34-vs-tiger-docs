"""Local server + slider panel for the live atmosphere editor.

Serves an HTML panel of sliders; on every change the page POSTs the values here,
and this server writes them to atmos_state.txt (a simple key=value file with a
version counter). The injected atmos_wysiwyg.dll polls that file ~10x/sec and
applies any change to the live game/editor atmosphere.

Run:
    python atmos_server.py            # http://127.0.0.1:8766
Then inject atmos_wysiwyg.dll into the editor (play_atmos_editor.bat) and open
the panel in a browser.
"""
import datetime
import json
import os
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bake_mission  # noqa: E402  (shared bake logic)

STATE = os.path.join(HERE, "atmos_state.txt")
PANEL = os.path.join(HERE, "atmos_panel.html")
MISSIONS_ROOT = r"M:\T34vsTiger\Missions"

DEFAULTS = {
    "sun_azimuth": 64.0,
    "sun_elevation": 25.0,
    "sun_color": [1.0, 0.75, 0.45],
    "ambient": [0.25, 0.25, 0.30],
    "fog_near": 10.0,
    "fog_far": 800.0,
    "fog_density": 0.001,
    "fog_color": [0.7, 0.7, 0.7],
}

_lock = threading.Lock()
_version = [0]
_state = dict(DEFAULTS)


def write_state():
    with _lock:
        lines = ["version=%d" % _version[0]]
        lines.append("sun_azimuth=%.4f" % _state["sun_azimuth"])
        lines.append("sun_elevation=%.4f" % _state["sun_elevation"])
        lines.append("sun_color=%.4f,%.4f,%.4f" % tuple(_state["sun_color"]))
        lines.append("ambient=%.4f,%.4f,%.4f" % tuple(_state["ambient"]))
        lines.append("fog_near=%.4f" % _state["fog_near"])
        lines.append("fog_far=%.4f" % _state["fog_far"])
        lines.append("fog_density=%.6f" % _state["fog_density"])
        lines.append("fog_color=%.4f,%.4f,%.4f" % tuple(_state["fog_color"]))
        tmp = STATE + ".tmp"
        with open(tmp, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, STATE)


def list_missions():
    out = []
    if not os.path.isdir(MISSIONS_ROOT):
        return out
    for dirpath, _dirnames, filenames in os.walk(MISSIONS_ROOT):
        if "Content.script" in filenames:
            out.append({"name": os.path.relpath(dirpath, MISSIONS_ROOT),
                        "path": dirpath})
    out.sort(key=lambda m: m["name"])
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/missions":
            return self._send(200, json.dumps(list_missions()))
        if self.path == "/state":
            with _lock:
                payload = dict(_state)
                payload["version"] = _version[0]
            return self._send(200, json.dumps(payload))
        # serve the panel page
        try:
            with open(PANEL, "rb") as f:
                return self._send(200, f.read(), "text/html")
        except OSError:
            return self._send(404, "panel not found")

    def do_POST(self):
        if self.path == "/save_mission":
            return self.do_save_mission()
        if self.path != "/state":
            return self._send(404, "not found")
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n))
        except Exception:
            return self._send(400, "bad json")
        with _lock:
            for k in DEFAULTS:
                if k in data:
                    _state[k] = data[k]
            _version[0] += 1
        write_state()
        return self._send(200, json.dumps({"ok": True, "version": _version[0]}))

    def do_save_mission(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n))
        except Exception:
            return self._send(400, json.dumps({"ok": False, "error": "bad json"}))

        mission = data.get("mission")
        state = data.get("state")
        if not state:
            with _lock:
                state = dict(_state)
        if not mission:
            return self._send(400, json.dumps({"ok": False, "error": "no mission"}))

        # Local tool, but never write outside the missions tree.
        root = os.path.abspath(MISSIONS_ROOT).lower()
        if not os.path.abspath(mission).lower().startswith(root):
            return self._send(400, json.dumps({"ok": False, "error": "mission outside missions root"}))

        content_path = os.path.join(mission, "Content.script")
        if not os.path.isfile(content_path):
            return self._send(400, json.dumps({"ok": False, "error": "no Content.script"}))

        try:
            values = bake_mission.build_values(state)
            with open(content_path, "r", encoding="utf-8") as f:
                content = f.read()
            new_content, changes = bake_mission.rewrite(content, values)
            if not changes:
                return self._send(200, json.dumps({"ok": True, "changed": 0, "backup": None}))
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = content_path + ".bak." + ts
            shutil.copy2(content_path, backup)
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return self._send(200, json.dumps({"ok": True, "changed": len(changes), "backup": backup}))
        except SystemExit as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    write_state()
    port = 8766
    print("atmos panel: http://127.0.0.1:%d" % port)
    print("state file:  %s" % STATE)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
