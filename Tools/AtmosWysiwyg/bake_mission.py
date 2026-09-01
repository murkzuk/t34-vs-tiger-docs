"""Bake the current atmosphere panel values into a mission's Content.script.

Reads atmos_state.txt (written live by atmos_server.py), converts the panel's
azimuth/elevation into the engine's sun-direction vector, and rewrites the
"Atmosphere" property map inside the mission's Content.script.

SAFE BY DEFAULT:
  - dry-run (prints what WOULD change) unless --apply is given
  - with --apply, backs up Content.script to Content.script.bak.<timestamp> first
  - refuses to write if any target key appears more than once in the file

Usage:
    python bake_mission.py "M:\\T34vsTiger\\Missions\\Campaign_2\\Mission_1"
    python bake_mission.py "M:\\T34vsTiger\\Missions\\Campaign_2\\Mission_1" --apply
"""
import argparse
import datetime
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE = os.path.join(HERE, "atmos_state.txt")

# Panel field  ->  Content.script key  (all 4 fog colors share one panel colour)
COLOR_KEYS = ["FogColorXPos", "FogColorXNeg", "FogColorYPos", "FogColorYNeg"]


def parse_state(path):
    s = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k == "version":
                continue
            s[k] = [float(x) for x in v.split(",")] if "," in v else float(v)
    return s


def azel_to_vec(az, el):
    azr, elr = math.radians(az), math.radians(el)
    return (
        math.cos(azr) * math.cos(elr),
        -math.sin(azr) * math.cos(elr),
        -math.sin(elr),
    )


def f6(x):
    return "%.6f" % x


def vec6(v):
    return "new Vector(%.6f, %.6f, %.6f)" % v


def color6(c, a=1.0):
    return "new Color(%.6f, %.6f, %.6f, %.6f)" % (c[0], c[1], c[2], a)


def build_values(state):
    az, el = state["sun_azimuth"], state["sun_elevation"]
    return {
        "SunDirection": azel_to_vec(az, el),
        "SunColor": state["sun_color"],
        "AmbientLight": state["ambient"],
        "FogNear": state["fog_near"],
        "FogFar": state["fog_far"],
        "FogDensity": state["fog_density"],
        "FogColorXPos": state["fog_color"],
        "FogColorXNeg": state["fog_color"],
        "FogColorYPos": state["fog_color"],
        "FogColorYNeg": state["fog_color"],
    }


def entry_str(key, values):
    if key == "SunDirection":
        return '["SunDirection", %s]' % vec6(values["SunDirection"])
    if key in ("SunColor", "AmbientLight", "FogColorXPos", "FogColorXNeg",
               "FogColorYPos", "FogColorYNeg"):
        return '["%s", %s]' % (key, color6(values[key]))
    return '["%s", %s]' % (key, f6(values[key]))


def find_prop_region(lines):
    """Return (open_idx, close_idx) of the Atmosphere object's property array."""
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == '"Atmosphere",':
            start = i
            break
    if start is None:
        raise SystemExit("ERROR: no 'Atmosphere' object found in Content.script")

    open_idx = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "[":
            open_idx = i
            break
    if open_idx is None:
        raise SystemExit("ERROR: no property array after Atmosphere object")

    depth = 0
    for i in range(open_idx, len(lines)):
        depth += lines[i].count("[") - lines[i].count("]")
        if depth <= 0:
            return open_idx, i
    raise SystemExit("ERROR: unbalanced brackets in Atmosphere block")


def rewrite(content, values):
    lines = content.split("\n")
    open_idx, close_idx = find_prop_region(lines)

    # Detect the property-entry indentation from an existing entry line.
    indent = "        "
    for ln in lines[open_idx + 1:close_idx]:
        m = re.match(r"^(\s*)\[", ln)
        if m:
            indent = m.group(1)
            break

    region = lines[open_idx + 1:close_idx]
    changes = []
    new_region = list(region)

    for key, val in values.items():
        # uniqueness check across the WHOLE file (these keys are atmosphere-only)
        hits = [ln for ln in lines if re.match(r"^\s*\[" + re.escape('"%s"' % key) + r"\b", ln)]
        if len(hits) > 1:
            raise SystemExit("ERROR: key %r appears %d times - refusing to write" % (key, len(hits)))

        pat = re.compile(r'^(\s*)\["%s",.*?(\],?)(\s*//.*)?$' % re.escape(key))
        replaced = False
        for idx, ln in enumerate(new_region):
            m = pat.match(ln)
            if m:
                comment = m.group(3) or ""
                new_region[idx] = indent + entry_str(key, values) + "," + comment
                changes.append((key, ln.strip(), new_region[idx].strip()))
                replaced = True
                break

        if not replaced:
            new_line = indent + entry_str(key, values) + ","
            new_region.append(new_line)
            changes.append((key, "(absent)", new_line.strip()))

    lines[open_idx + 1:close_idx] = new_region
    return "\n".join(lines), changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mission_dir")
    ap.add_argument("--state", default=DEFAULT_STATE)
    ap.add_argument("--apply", action="store_true", help="write the file (backs up first)")
    args = ap.parse_args()

    content_path = os.path.join(args.mission_dir, "Content.script")
    if not os.path.isfile(content_path):
        raise SystemExit("ERROR: no Content.script in %s" % args.mission_dir)
    if not os.path.isfile(args.state):
        raise SystemExit("ERROR: state file not found: %s" % args.state)

    state = parse_state(args.state)
    values = build_values(state)

    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content, changes = rewrite(content, values)

    print("Mission : %s" % args.mission_dir)
    print("State   : sun az=%g el=%g  sunC%s  amb%s  fog %g/%g d=%g  fogC%s" % (
        state["sun_azimuth"], state["sun_elevation"],
        tuple(state["sun_color"]), tuple(state["ambient"]),
        state["fog_near"], state["fog_far"], state["fog_density"],
        tuple(state["fog_color"])))
    print("-" * 70)
    if not changes:
        print("No changes needed (already matches).")
        return
    for key, old, new in changes:
        print("  %s:" % key)
        print("    OLD  %s" % old)
        print("    NEW  %s" % new)
    print("-" * 70)

    if not args.apply:
        print("DRY RUN - nothing written. Re-run with --apply to write.")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = content_path + ".bak." + ts
    shutil.copy2(content_path, backup)
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("APPLIED. Backup: %s" % backup)
    print("Reload the mission in-game to verify (close/reopen it fully).")


if __name__ == "__main__":
    main()
