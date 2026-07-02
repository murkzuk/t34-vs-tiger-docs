#!/usr/bin/env python3
"""
Quick Mission Generator for T34 vs Tiger (QuickMission slot).

Regenerates Missions\\MyMission\\QuickMission\\Content.script from the
pristine Missions\\MyMission\\Mission1\\Content.script template, adding
randomized enemy units (per roster.json) and relocating the victory
NavPoint, while leaving every other file in QuickMission\\ untouched.

Usage:
    python generate_mission.py [--seed N] [--roster path\\to\\roster.json]
"""

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

# ---------------------------------------------------------------------------
# Fixed paths and constants (verified this session against the real files)
# ---------------------------------------------------------------------------

GAME_ROOT = Path(__file__).resolve().parent.parent.parent  # Tools\MissionGenerator\..\.. = game root
TEMPLATE_DIR = GAME_ROOT / "Missions" / "MyMission" / "Mission1"
OUTPUT_DIR = GAME_ROOT / "Missions" / "MyMission" / "QuickMission"
TEMPLATE_CONTENT = TEMPLATE_DIR / "Content.script"
OUTPUT_CONTENT = OUTPUT_DIR / "Content.script"
ROUTERZONE_BMP = OUTPUT_DIR / "RouterZone_Test.bmp"

ENCODING = "cp1251"

# From WorldMatricies.script (verified against QuickMission\WorldMatricies.script
# this session - MatrixWidth/Height and the RouterZoneLayer's ImageWidth/Height).
MATRIX_WIDTH = 9000.0
MATRIX_HEIGHT = 9000.0
ROUTERZONE_IMG_WIDTH = 2048
ROUTERZONE_IMG_HEIGHT = 2048

# Renames applied when deriving QuickMission's Content.script from Mission1's
# pristine template - must match the one-time setup renames exactly.
RENAMES = {
    "Mission1Content": "QuickMissionContent",
    "Missions/MyMission/Mission1/Content.script": "Missions/MyMission/QuickMission/Content.script",
}

OBJECTIVE_OBJECT_ID = "end_navpoint"
PLAYER_OBJECT_ID = "MainPlayerUnit"

# Object types that represent real placeable positions - excludes the
# pseudo-objects "Atmosphere"/"Terrain" which sit at the coordinate origin
# and are not meaningful anchor points.
ANCHOR_OBJECT_TYPES = {"GameObject", "InteriorObject", "NavPoint", "Locator"}

# Hardcoded allowlist, independent of roster.json's own contents. Every one
# of these was individually grep-confirmed against Scripts\Units\*.script
# (or is already live in the pristine template) this session - see the plan
# and Mission_File_Schema_Verified_2026-07-02.md. roster.json is user-editable
# and MUST NOT be trusted to self-certify its own class/task names - a typo'd
# or invented class name here would only fail at game-launch time, which this
# tool cannot detect, so it is rejected before generation even starts instead.
VERIFIED_UNIT_CLASSES = {
    "CTankPzIVGUnit",       # Scripts\Units\TankPzIVGUnit.script - live in Mission1 template ("tiger")
    "CGunPak40Unit",        # Scripts\Units\GunPak40Unit.script:282 - live in Mission1 template
    "CTankT34_76_42Unit",   # Scripts\Units\T34_76_42.script:879
    "CTankT34_85_44Unit",   # Scripts\Units\T34_85_44.script - live as MainPlayerUnit's class
    "CSAUStuG40Unit",       # Scripts\Units\SAUSTUG40Unit.script:547 - live in Campaign_2\Mission_5
    "CTankPzVIAusfEUnit",   # Scripts\Units\TankPzVIAusfEUnit.script:1227 (the actual Tiger tank)
    "CGunZis3Unit",         # Scripts\Units\GunZis3Unit.script:286
}
VERIFIED_TASK_CLASSES = {
    "CBaseAITask",       # live in Mission1 template (enemy_pak40_1/2)
    "CBaseAITankTask",   # live in Mission1 template ("tiger")
}


def validate_roster_config(config):
    """Reject roster.json outright if it names any class/task not on the
    hardcoded verified allowlist above - before any generation is attempted."""
    errors = []
    for item in config.get("roster", []):
        if item["class"] not in VERIFIED_UNIT_CLASSES:
            errors.append(
                f'roster.json entry "{item["id"]}" uses unverified class "{item["class"]}" - '
                f"not in VERIFIED_UNIT_CLASSES in generate_mission.py. Grep-confirm it against "
                f"Scripts\\Units\\*.script and add it to that set before using it."
            )
        if item["task"] not in VERIFIED_TASK_CLASSES:
            errors.append(
                f'roster.json entry "{item["id"]}" uses unverified task "{item["task"]}" - '
                f"not in VERIFIED_TASK_CLASSES in generate_mission.py."
            )
    return errors


class GeneratorError(Exception):
    """Raised for any condition that should stop generation before writing anything."""


# ---------------------------------------------------------------------------
# CP1251-safe file I/O (see Tools\MissionGenerator - never use a text editor
# or a bare-UTF8 tool on these files, per this project's CP1251 lesson).
# ---------------------------------------------------------------------------

def read_text(path: Path) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode(ENCODING)


def write_text_verified(path: Path, text: str) -> None:
    """Write text as CP1251 bytes, then read it back and compare byte-for-byte -
    catches any character that can't survive a CP1251 round trip before it
    can silently corrupt the file."""
    encoded = text.encode(ENCODING)
    with open(path, "wb") as f:
        f.write(encoded)
    with open(path, "rb") as f:
        check = f.read()
    if check != encoded:
        raise GeneratorError(
            f"CP1251 round-trip check failed writing {path} - refusing to trust the output."
        )


def hash_file(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Parsing the template Content.script
# ---------------------------------------------------------------------------

def find_matching_bracket(text: str, open_index: int) -> int:
    """Given the index of an opening '[' character, return the index of its
    matching ']' by depth-tracking, skipping over bracket-like characters
    that appear inside string literals."""
    depth = 0
    in_string = False
    i = open_index
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            if ch == '"' and text[i - 1] != "\\":
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise GeneratorError("Unbalanced brackets while parsing template Content.script")


def split_top_level_entries(list_body: str):
    """Split the inside of m_MissionObjectList = [ ... ] into its top-level
    entry strings (each one a whole '[ ... ]' block), preserving exact text."""
    entries = []
    i = 0
    n = len(list_body)
    while i < n:
        if list_body[i] == "[":
            end = find_matching_bracket(list_body, i)
            entries.append(list_body[i:end + 1])
            i = end + 1
        else:
            i += 1
    return entries


HEADER_RE = re.compile(r'\s*\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"')


def parse_entry_header(entry_text: str):
    """Extract (ObjectID, ObjectType, ClassName) - the first 3 quoted values
    of an entry block."""
    m = HEADER_RE.match(entry_text)
    if not m:
        raise GeneratorError(f"Could not parse entry header from: {entry_text[:80]!r}")
    return m.group(1), m.group(2), m.group(3)


MATRIX_RE = re.compile(
    r"new Matrix\(\s*"
    r"([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*"
    r"([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*"
    r"([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*"
    r"([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\s*\)",
    re.DOTALL,
)


def parse_matrix_translation(entry_text: str):
    m = MATRIX_RE.search(entry_text)
    if not m:
        raise GeneratorError(f"Could not find/parse Matrix in entry: {entry_text[:80]!r}")
    values = [float(v) for v in m.groups()]
    x, y, z = values[3], values[7], values[11]
    return x, y, z


def build_identity_matrix_text(x: float, y: float, z: float) -> str:
    return (
        "new Matrix(\n"
        f"          1.000000, 0.000000, 0.000000, {x:.6f},\n"
        f"          0.000000, 1.000000, 0.000000, {y:.6f},\n"
        f"          0.000000, 0.000000, 1.000000, {z:.6f},\n"
        "          0.000000, 0.000000, 0.000000, 1.000000\n"
        "        )"
    )


# ---------------------------------------------------------------------------
# RouterZone bitmap soft filter (empirical, not proven in-game - see plan)
# ---------------------------------------------------------------------------

def load_routerzone():
    if not HAVE_PIL:
        print("NOTE: Pillow not installed - RouterZone soft filter disabled.", file=sys.stderr)
        return None
    if not ROUTERZONE_BMP.exists():
        print(f"NOTE: {ROUTERZONE_BMP} not found - RouterZone soft filter disabled.", file=sys.stderr)
        return None
    return Image.open(ROUTERZONE_BMP).convert("RGB")


def world_to_pixel(x: float, y: float):
    px = int((x / MATRIX_WIDTH) * ROUTERZONE_IMG_WIDTH)
    py = int((y / MATRIX_HEIGHT) * ROUTERZONE_IMG_HEIGHT)
    px = max(0, min(ROUTERZONE_IMG_WIDTH - 1, px))
    py = max(0, min(ROUTERZONE_IMG_HEIGHT - 1, py))
    return px, py


def is_passable(img, x: float, y: float, passable_colors) -> bool:
    if img is None:
        return True  # filter disabled entirely -> treat everything as passable
    px, py = world_to_pixel(x, y)
    pixel = img.getpixel((px, py))
    return tuple(pixel) in {tuple(c) for c in passable_colors}


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

def pick_position(rng, anchors, jitter_radius, router_img, config, distance_constraint=None):
    """distance_constraint, if given, is (from_x, from_y, min_distance)."""
    for _ in range(config["max_placement_attempts"]):
        ax, ay, az = rng.choice(anchors)
        x = ax + rng.uniform(-jitter_radius, jitter_radius)
        y = ay + rng.uniform(-jitter_radius, jitter_radius)
        z = az
        if distance_constraint is not None:
            fx, fy, min_dist = distance_constraint
            if ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 < min_dist:
                continue
        if config.get("use_routerzone_soft_filter") and router_img is not None:
            if not is_passable(router_img, x, y, config["routerzone_passable_colors"]):
                continue
        return x, y, z
    # Every attempt failed a constraint - fall back to an anchor point exactly,
    # which is guaranteed valid since the template itself places something there.
    ax, ay, az = rng.choice(anchors)
    return ax, ay, az


def build_gameobject_entry(object_id, class_name, x, y, z, affiliation, task):
    matrix_text = build_identity_matrix_text(x, y, z)
    return (
        "    [\n"
        f'      "{object_id}",\n'
        '      "GameObject",\n'
        f'      "{class_name}",\n'
        f"      {matrix_text},\n"
        "      [\n"
        f'        ["Affiliation", "{affiliation}"],\n'
        f'        ["Task", "{task}"]\n'
        "      ]\n"
        "    ]"
    )


# ---------------------------------------------------------------------------
# Validation - static checks only, no game launch required
# ---------------------------------------------------------------------------

def validate_generated_text(full_text: str, expected_ids: set, known_good_classes: set, known_good_tasks: set):
    errors = []

    for open_ch, close_ch in [("{", "}"), ("[", "]"), ("(", ")")]:
        if full_text.count(open_ch) != full_text.count(close_ch):
            errors.append(
                f"Bracket mismatch for '{open_ch}{close_ch}': "
                f"{full_text.count(open_ch)} vs {full_text.count(close_ch)}"
            )

    ids_found = re.findall(
        r'^\s*\[\s*\n\s*"([^"]+)",\s*\n\s*"(?:GameObject|InteriorObject|NavPoint|Locator|)"',
        full_text, re.MULTILINE,
    )
    seen = set()
    for oid in ids_found:
        if oid in seen:
            errors.append(f"Duplicate ObjectID: {oid}")
        seen.add(oid)
    missing = expected_ids - seen
    if missing:
        errors.append(f"Expected ObjectIDs missing from output: {sorted(missing)}")

    for m in MATRIX_RE.finditer(full_text):
        if len(m.groups()) != 16:
            errors.append("A Matrix(...) call does not have exactly 16 numeric values")
        for g in m.groups():
            try:
                float(g)
            except ValueError:
                errors.append(f"A Matrix(...) value is not a valid float: {g!r}")

    classes_used = set(re.findall(r'"(C[A-Za-z0-9_]+Unit)"', full_text))
    unknown_classes = classes_used - known_good_classes
    if unknown_classes:
        errors.append(f"Unexpected/unverified unit class name(s) in output: {sorted(unknown_classes)}")

    tasks_used = set(re.findall(r'\["Task",\s*"([^"]+)"\]', full_text))
    unknown_tasks = tasks_used - known_good_tasks
    if unknown_tasks:
        errors.append(f"Unexpected/unverified task class name(s) in output: {sorted(unknown_tasks)}")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Regenerate the QuickMission slot with randomized units.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible output.")
    parser.add_argument("--roster", type=Path, default=Path(__file__).parent / "roster.json")
    args = parser.parse_args()

    if not TEMPLATE_CONTENT.exists():
        print(f"ERROR: template not found at {TEMPLATE_CONTENT}", file=sys.stderr)
        sys.exit(1)
    if not OUTPUT_DIR.exists():
        print(f"ERROR: QuickMission folder not found at {OUTPUT_DIR}. Run the one-time setup first.", file=sys.stderr)
        sys.exit(1)

    with open(args.roster, "r", encoding="utf-8") as f:
        config = json.load(f)

    roster_errors = validate_roster_config(config)
    if roster_errors:
        print("roster.json FAILED validation - nothing was written. Problems found:", file=sys.stderr)
        for e in roster_errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)

    # --- Load pristine template, always starting fresh (never QuickMission's
    #     own possibly-previously-randomized Content.script) ---
    template_text = read_text(TEMPLATE_CONTENT)

    list_marker = "m_MissionObjectList   = ["
    if list_marker not in template_text:
        raise GeneratorError(f"Could not find {list_marker!r} in template - has the template file changed?")
    list_start = template_text.index(list_marker) + len(list_marker) - 1  # index of the '['
    list_end = find_matching_bracket(template_text, list_start)
    prefix = template_text[:list_start + 1]
    list_body = template_text[list_start + 1:list_end]
    suffix = template_text[list_end:]

    entries = split_top_level_entries(list_body)

    anchors = []
    entry_by_id = {}
    template_classes = set()
    template_tasks = set()
    for entry in entries:
        oid, otype, cls = parse_entry_header(entry)
        entry_by_id[oid] = entry
        if cls:
            template_classes.add(cls)
        for task_match in re.findall(r'\["Task",\s*"([^"]+)"\]', entry):
            template_tasks.add(task_match)
        if otype in ANCHOR_OBJECT_TYPES:
            anchors.append(parse_matrix_translation(entry))

    if not anchors:
        raise GeneratorError("No anchor positions found in template - cannot place units safely.")
    if PLAYER_OBJECT_ID not in entry_by_id:
        raise GeneratorError(f"Template is missing expected object '{PLAYER_OBJECT_ID}'")
    if OBJECTIVE_OBJECT_ID not in entry_by_id:
        raise GeneratorError(f"Template is missing expected object '{OBJECTIVE_OBJECT_ID}'")

    player_x, player_y, player_z = parse_matrix_translation(entry_by_id[PLAYER_OBJECT_ID])

    router_img = load_routerzone() if config.get("use_routerzone_soft_filter") else None

    # --- Relocate the objective NavPoint (ID/Range/ClassName untouched, only
    #     its Matrix moves - see schema doc section 3 for why this is safe) ---
    obj_x, obj_y, obj_z = pick_position(
        rng, anchors, config["jitter_radius"], router_img, config,
        distance_constraint=(player_x, player_y, config["objective_min_distance_from_player"]),
    )
    old_navpoint_entry = entry_by_id[OBJECTIVE_OBJECT_ID]
    old_matrix_text = MATRIX_RE.search(old_navpoint_entry).group(0)
    new_matrix_text = build_identity_matrix_text(obj_x, obj_y, obj_z)
    new_navpoint_entry = old_navpoint_entry.replace(old_matrix_text, new_matrix_text)

    updated_entries = []
    for entry in entries:
        oid, _, _ = parse_entry_header(entry)
        updated_entries.append(new_navpoint_entry if oid == OBJECTIVE_OBJECT_ID else entry)

    # --- Generate randomized units from the roster ---
    used_ids = set(entry_by_id.keys())
    roster_classes = set()
    roster_tasks = set()
    new_entries_text = []

    for item in config["roster"]:
        roster_classes.add(item["class"])
        roster_tasks.add(item["task"])
        count = rng.randint(item["min"], item["max"])
        for i in range(count):
            n = i + 1
            object_id = f'{item["id"]}_{n}'
            while object_id in used_ids:
                n += 1
                object_id = f'{item["id"]}_{n}'
            used_ids.add(object_id)

            x, y, z = pick_position(rng, anchors, config["jitter_radius"], router_img, config)
            new_entries_text.append(
                build_gameobject_entry(object_id, item["class"], x, y, z, item["affiliation"], item["task"])
            )

    all_entries_text = updated_entries + new_entries_text
    new_list_body = "\n" + ",\n\n".join(all_entries_text) + "\n  "
    full_text = prefix + new_list_body + suffix

    # Apply the QuickMission renames (self-referential class name + path strings)
    for old, new in RENAMES.items():
        full_text = full_text.replace(old, new)

    # --- Validate before writing anything. Trust classes/tasks already
    #     legitimately present in the pristine template, plus the roster. ---
    known_good_classes = template_classes | roster_classes
    known_good_tasks = template_tasks | roster_tasks
    errors = validate_generated_text(full_text, used_ids, known_good_classes, known_good_tasks)
    if errors:
        print("Generation FAILED validation - nothing was written. Problems found:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # --- Guarantee every other file in QuickMission is untouched ---
    other_files = [p for p in OUTPUT_DIR.iterdir() if p.is_file() and p.name != "Content.script"]
    hashes_before = {p: hash_file(p) for p in other_files}

    write_text_verified(OUTPUT_CONTENT, full_text)

    hashes_after = {p: hash_file(p) for p in other_files}
    changed = [p for p in other_files if hashes_before[p] != hashes_after[p]]
    if changed:
        # Should be structurally impossible since this script never opens
        # these files, but check anyway per the plan's safety requirements.
        print("WARNING: files outside Content.script changed unexpectedly:", file=sys.stderr)
        for p in changed:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: wrote {OUTPUT_CONTENT}")
    print(f"    {len(new_entries_text)} randomized unit(s) added, "
          f"objective relocated to ({obj_x:.1f}, {obj_y:.1f}, {obj_z:.1f})")
    print(f"    seed={args.seed if args.seed is not None else '(none - not reproducible, pass --seed to fix)'}")
    print('    Load "Quick Mission (Generated)" in the Level Editor to test.')


if __name__ == "__main__":
    main()
