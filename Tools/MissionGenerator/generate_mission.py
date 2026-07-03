#!/usr/bin/env python3
"""
Quick Mission Generator for T34 vs Tiger.

Regenerates a mission slot's Content.script from its pristine template,
adding randomized enemy units (per roster.json) and relocating the victory
NavPoint, while leaving every other file in the output folder untouched.
Two targets are available (--target quickmission|steppe):

  quickmission - Missions\\MyMission\\QuickMission\\, from the pristine
                 Missions\\MyMission\\Mission1\\ template. 9000x9000, the
                 original small map. This is the default.
  steppe       - Missions\\MyMission\\SteppeQuickMission\\, from the pristine
                 Missions\\MyMission\\SteppeTemplate\\ template. 18000x18000,
                 open/low-forest.

Choose which side you play with --faction SOVIET or --faction AXIS (or set
player_faction in roster.json) - the player's own tank and the enemy roster
both switch to match.

Usage:
    python generate_mission.py [--seed N] [--roster path\\to\\roster.json] [--faction SOVIET|AXIS] [--target quickmission|steppe]
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

ENCODING = "cp1251"

# Two mission slots this generator can target. Both were set up the same way -
# a pristine template mission copied once, class/path identifiers renamed, then
# this script regenerates only that copy's Content.script on every run, always
# starting fresh from the *pristine template's* Content.script (never the
# previous run's output). Matrix/RouterZone dimensions come from each target's
# own WorldMatricies.script, verified against the live files this session.
TARGETS = {
    "quickmission": {
        "template_dir": GAME_ROOT / "Missions" / "MyMission" / "Mission1",
        "output_dir": GAME_ROOT / "Missions" / "MyMission" / "QuickMission",
        "matrix_width": 9000.0,
        "matrix_height": 9000.0,
        "routerzone_img_width": 2048,
        "routerzone_img_height": 2048,
        "renames": {
            "Mission1Content": "QuickMissionContent",
            "Missions/MyMission/Mission1/Content.script": "Missions/MyMission/QuickMission/Content.script",
        },
        "menu_name": "Quick Mission (Generated)",
        # RouterZone_Test.bmp here was painted with a 9000x9000 MatrixWidth in
        # mind - the soft filter's color samples are at least meaningful for
        # this target, even though the mapping itself is still unproven in-game.
        "routerzone_soft_filter_supported": True,
    },
    "steppe": {
        "template_dir": GAME_ROOT / "Missions" / "MyMission" / "SteppeTemplate",
        "output_dir": GAME_ROOT / "Missions" / "MyMission" / "SteppeQuickMission",
        "matrix_width": 18000.0,
        "matrix_height": 18000.0,
        "routerzone_img_width": 2048,
        "routerzone_img_height": 2048,
        "renames": {
            "SteppeTemplateContent": "SteppeQuickMissionContent",
            "Missions/MyMission/SteppeTemplate/Content.script": "Missions/MyMission/SteppeQuickMission/Content.script",
        },
        "menu_name": "Steppe Quick Mission (Generated)",
        # RouterZone_Test.bmp was copied unmodified from Mission1/QuickMission's
        # (9000x9000) file, then reinterpreted over an 18000x18000 MatrixWidth -
        # the same real-world coordinate now samples a completely different
        # pixel/color than it would at the original scale (confirmed empirically:
        # the same anchor point maps to opposite passable-color entries depending
        # on which MatrixWidth is used for the pixel conversion). The soft filter
        # would be checking the wrong region of the bitmap for this target, so
        # it's disabled here rather than silently giving unreliable verdicts -
        # until a RouterZone bitmap painted for the 18000 scale exists.
        "routerzone_soft_filter_supported": False,
    },
}

# Set by main() from TARGETS[args.target] before anything else runs - every
# function below reads these as globals rather than taking them as parameters,
# since this is a single-run CLI script, not a library.
TEMPLATE_DIR = None
OUTPUT_DIR = None
TEMPLATE_CONTENT = None
OUTPUT_CONTENT = None
ROUTERZONE_BMP = None
MATRIX_WIDTH = None
MATRIX_HEIGHT = None
ROUTERZONE_IMG_WIDTH = None
ROUTERZONE_IMG_HEIGHT = None
RENAMES = None
ROUTERZONE_SOFT_FILTER_SUPPORTED = None


def select_target(name: str) -> None:
    """Populate the module-level path/dimension globals for the chosen target."""
    global TEMPLATE_DIR, OUTPUT_DIR, TEMPLATE_CONTENT, OUTPUT_CONTENT, ROUTERZONE_BMP
    global MATRIX_WIDTH, MATRIX_HEIGHT, ROUTERZONE_IMG_WIDTH, ROUTERZONE_IMG_HEIGHT, RENAMES
    global ROUTERZONE_SOFT_FILTER_SUPPORTED
    t = TARGETS[name]
    TEMPLATE_DIR = t["template_dir"]
    OUTPUT_DIR = t["output_dir"]
    TEMPLATE_CONTENT = TEMPLATE_DIR / "Content.script"
    OUTPUT_CONTENT = OUTPUT_DIR / "Content.script"
    ROUTERZONE_BMP = OUTPUT_DIR / "RouterZone_Test.bmp"
    MATRIX_WIDTH = t["matrix_width"]
    MATRIX_HEIGHT = t["matrix_height"]
    ROUTERZONE_IMG_WIDTH = t["routerzone_img_width"]
    ROUTERZONE_IMG_HEIGHT = t["routerzone_img_height"]
    ROUTERZONE_SOFT_FILTER_SUPPORTED = t["routerzone_soft_filter_supported"]
    RENAMES = t["renames"]

OBJECTIVE_OBJECT_ID = "end_navpoint"
PLAYER_OBJECT_ID = "MainPlayerUnit"

# The pristine template hardcodes 3 pre-existing combat units as ENEMY:
# "tiger" (CTankPzIVGUnit) and "enemy_pak40_1"/"enemy_pak40_2" (CGunPak40Unit) -
# all German/AXIS. That's correct when playing SOVIET (the template's original
# intent), but backwards when playing AXIS - a German player would still see
# these German units marked hostile. Rather than risk an untested affiliation
# flip to FRIEND, they're simply excluded from the output when their faction
# matches the chosen player_faction.
TEMPLATE_HOSTILE_UNIT_FACTIONS = {
    "tiger": "AXIS",
    "enemy_pak40_1": "AXIS",
    "enemy_pak40_2": "AXIS",
}

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
    "CSAUSU85Unit",             # Scripts\Units\SAUSU85Unit.script:536
    "CGunNebelUnit",            # Scripts\Units\GunNebelUnit.script:105
    "CGermanSoldierRifleUnit",  # Scripts\Units\GermanSoldierRifleUnit.script:103 - live in Campaign_1\Mission_1
    "CSovietSoldierRifleUnit",  # Scripts\Units\SovietSoldierRifleUnit.script:104 - live in Campaign_1\Mission_2
}
VERIFIED_TASK_CLASSES = {
    "CBaseAITask",       # live in Mission1 template (enemy_pak40_1/2); also confirmed on both
                          # infantry rifle classes (Campaign_1\Mission_1/2) and, by structural
                          # analogy (identical "extends CUnit, CPushObject" base), CGunNebelUnit -
                          # Nebelwerfer's own Task usage was not directly observed in a live mission
    "CBaseAITankTask",   # live in Mission1 template ("tiger")
    "CBaseAISAUTask",    # Scripts\Common\BaseTasks.script:3352 - confirmed live on CSAUStuG40Unit
                          # in Campaign_2\Mission_4\Content.script:260/277 (bare GameObject + Task,
                          # same pattern this generator uses) - the correct task for self-propelled
                          # guns (SAU = self-propelled artillery mount), not CBaseAITankTask
}


VALID_FACTIONS = {"SOVIET", "AXIS"}


def validate_roster_config(config, player_faction):
    """Reject roster.json (and the resolved player faction/unit) outright if
    anything names a class/task not on the hardcoded verified allowlists
    above - before any generation is attempted."""
    errors = []

    if player_faction not in VALID_FACTIONS:
        errors.append(f'player_faction "{player_faction}" must be one of {sorted(VALID_FACTIONS)}')

    player_unit_class = config.get("player_unit_class", {}).get(player_faction)
    if not player_unit_class:
        errors.append(f'No player_unit_class configured for faction "{player_faction}" in roster.json')
    elif player_unit_class not in VERIFIED_UNIT_CLASSES:
        errors.append(
            f'player_unit_class for "{player_faction}" is unverified class "{player_unit_class}" - '
            f"not in VERIFIED_UNIT_CLASSES in generate_mission.py."
        )

    for item in config.get("roster", []):
        if item.get("faction") not in VALID_FACTIONS:
            errors.append(f'roster.json entry "{item["id"]}" has missing/invalid "faction" (must be SOVIET or AXIS)')
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


def replace_entry_class(entry_text: str, new_class: str) -> str:
    """Swap only the ClassName (3rd quoted field) of an entry block, leaving
    the ObjectID, ObjectType, Matrix, and properties untouched."""
    m = HEADER_RE.match(entry_text)
    old_class = m.group(3)
    class_start = m.start(3)
    class_end = m.end(3)
    return entry_text[:class_start] + new_class + entry_text[class_end:]


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
    parser = argparse.ArgumentParser(description="Regenerate a mission slot with randomized units.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible output.")
    parser.add_argument("--roster", type=Path, default=Path(__file__).parent / "roster.json")
    parser.add_argument("--faction", choices=sorted(VALID_FACTIONS), default=None,
                         help="Play as SOVIET or AXIS. Overrides roster.json's player_faction if given.")
    parser.add_argument("--target", choices=sorted(TARGETS.keys()), default="quickmission",
                         help="Which mission slot to regenerate: 'quickmission' (small, 9000x9000, "
                              "the original) or 'steppe' (large, 18000x18000, open/low-forest).")
    args = parser.parse_args()

    select_target(args.target)

    if not TEMPLATE_CONTENT.exists():
        print(f"ERROR: template not found at {TEMPLATE_CONTENT}", file=sys.stderr)
        sys.exit(1)
    if not OUTPUT_DIR.exists():
        print(f"ERROR: output folder not found at {OUTPUT_DIR}. Run the one-time setup first.", file=sys.stderr)
        sys.exit(1)

    with open(args.roster, "r", encoding="utf-8") as f:
        config = json.load(f)

    player_faction = args.faction or config.get("player_faction", "SOVIET")

    roster_errors = validate_roster_config(config, player_faction)
    if roster_errors:
        print("roster.json FAILED validation - nothing was written. Problems found:", file=sys.stderr)
        for e in roster_errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    player_unit_class = config["player_unit_class"][player_faction]
    rng = random.Random(args.seed)

    # --- Load pristine template, always starting fresh (never the output
    #     folder's own possibly-previously-randomized Content.script) ---
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

    use_routerzone = config.get("use_routerzone_soft_filter") and ROUTERZONE_SOFT_FILTER_SUPPORTED
    if config.get("use_routerzone_soft_filter") and not ROUTERZONE_SOFT_FILTER_SUPPORTED:
        print(
            f"NOTE: RouterZone soft filter disabled for target '{args.target}' - "
            f"not verified meaningful at this target's MatrixWidth (see TARGETS in this file).",
            file=sys.stderr,
        )
    router_img = load_routerzone() if use_routerzone else None

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

    # --- Swap the player's own tank to match the chosen faction (position/
    #     properties like IsPlayer/IsManual/Affiliation/SurfaceControl untouched -
    #     only the ClassName field changes) ---
    new_player_entry = replace_entry_class(entry_by_id[PLAYER_OBJECT_ID], player_unit_class)

    updated_entries = []
    excluded_ids = []
    for entry in entries:
        oid, _, _ = parse_entry_header(entry)
        if TEMPLATE_HOSTILE_UNIT_FACTIONS.get(oid) == player_faction:
            excluded_ids.append(oid)
            continue
        if oid == OBJECTIVE_OBJECT_ID:
            updated_entries.append(new_navpoint_entry)
        elif oid == PLAYER_OBJECT_ID:
            updated_entries.append(new_player_entry)
        else:
            updated_entries.append(entry)

    # --- Generate randomized units from the roster. Only spawn entries whose
    #     faction is NOT the player's - those become the enemy. ---
    used_ids = set(entry_by_id.keys())
    roster_classes = {player_unit_class}
    roster_tasks = set()
    new_entries_text = []

    enemy_roster = [item for item in config["roster"] if item["faction"] != player_faction]
    if not enemy_roster:
        raise GeneratorError(
            f'No roster entries have a faction other than player_faction "{player_faction}" - '
            f"there would be no enemies to fight."
        )

    for item in enemy_roster:
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
                build_gameobject_entry(object_id, item["class"], x, y, z, "ENEMY", item["task"])
            )

    all_entries_text = updated_entries + new_entries_text
    new_list_body = "\n" + ",\n\n".join(all_entries_text) + "\n  "
    full_text = prefix + new_list_body + suffix

    # Apply this target's renames (self-referential class name + path strings)
    for old, new in RENAMES.items():
        full_text = full_text.replace(old, new)

    # --- Validate before writing anything. Trust classes/tasks already
    #     legitimately present in the pristine template, plus the roster.
    #     Deliberately-excluded template units (see excluded_ids above) are
    #     not expected to appear in the output. ---
    known_good_classes = template_classes | roster_classes
    known_good_tasks = template_tasks | roster_tasks
    expected_ids = used_ids - set(excluded_ids)
    errors = validate_generated_text(full_text, expected_ids, known_good_classes, known_good_tasks)
    if errors:
        print("Generation FAILED validation - nothing was written. Problems found:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # --- Guarantee every other file in the output folder is untouched ---
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
    print(f"    Playing as {player_faction} ({player_unit_class})")
    print(f"    {len(new_entries_text)} randomized enemy unit(s) added, "
          f"objective relocated to ({obj_x:.1f}, {obj_y:.1f}, {obj_z:.1f})")
    if excluded_ids:
        print(f"    Excluded {excluded_ids} (same faction as player, would have been backwards)")
    print(f"    seed={args.seed if args.seed is not None else '(none - not reproducible, pass --seed to fix)'}")
    print(f'    Load "{TARGETS[args.target]["menu_name"]}" in the Level Editor to test.')


if __name__ == "__main__":
    main()
