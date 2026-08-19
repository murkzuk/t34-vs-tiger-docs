"""Score the engine's own vision answers against real line of sight.

Reads tvt_los.log - what the shipped engine was asked and what it answered,
captured live - and runs the same pairs through canopy_los. The interesting
column is the one where the engine said SEEN and the ground says otherwise:
that is the flaw, in the game's own missions, at positions the game itself
chose, rather than at random points.

Only that direction counts. Real LOS may force a "no"; it must never turn a
"no" into a "yes", because the engine's "no" is usually just the detection dice
failing on that tick and says nothing about geometry.

WHERE THE OBJECT ORIGIN SITS - settled here, and it matters
-----------------------------------------------------------
The Z the engine reports for a unit is NOT its ground contact. Measured across
Campaign_1/Mission_2, height of origin above the sampled heightfield:

    CSovietSoldierRifleUnit  +0.85 m   (17 units, spread 0.01 m)
    CGermanSoldierRifleUnit  +0.86 m   ( 8 units, spread 0.06 m)
    CTankT34_76_42Unit       +1.46 m   ( 3 units, spread 0.05 m)
    CTankPzVIAusfEUnit       +1.72 m   ( 2 units, spread 0.00 m)

The offset scales with the model's height - roughly half of it - so it is an
origin convention (origins sit near mid-model), NOT a bias in the heightfield.
A sampling error would shift every class by the same amount.

Which also means the heightfield is very accurate indeed: seventeen soldiers
agreeing to within 1 cm is a stronger check on it than any of the authored-Z
comparisons done earlier.

So both endpoints are taken as absolute heights above the sampled ground, and
the engine's Z is ignored - adding an eye height to a Z that is already
mid-model would put the gunner's eye a metre and a half too high and make
everything look more visible than it is.
"""

import math
import re
import sys

import canopy_los as L

LINE = re.compile(
    r"\[\s*(\d+)\] obs \(\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\) "
    r"fwd \(\s*([-\d.]+),\s*([-\d.]+)\)\s+tgt \(\s*([-\d.]+),\s*([-\d.]+)\)"
    r"\s+dist\s+([-\d.]+)\s+dt ([\d.]+)\s+-> (\S+)")

HULL = 1.3          # centre of a tank hull, the thing being looked for


def identify(units, x, y, tol=3.0):
    """Match a logged position back to a unit in Content.script, so the right
    optic height is used rather than a blanket default. Units that have driven
    off their start position simply will not match, and fall back."""
    for u in units:
        if abs(u.x - x) < tol and abs(u.y - y) < tol:
            return u
    return None


def main(logpath, mission):
    t = L.Terrain(mission)
    units = L.read_units(mission)
    rows = []
    for line in open(logpath, encoding="utf-8", errors="replace"):
        m = LINE.match(line.strip())
        if m:
            rows.append(m.groups())
    if not rows:
        print("no sample lines in", logpath)
        return

    print("%d sampled calls from %s" % (len(rows), logpath))

    # Cross-check the heightfield against live engine positions, per class.
    by_cls = {}
    for _, ox, oy, oz, _, _, _, _, _, _, _ in rows:
        ox, oy, oz = float(ox), float(oy), float(oz)
        u = identify(units, ox, oy)
        cls = u.cls if u else "(moved)"
        by_cls.setdefault(cls, []).append(oz - t.ground(ox, oy))
    print("\norigin height above sampled ground, from live positions:")
    for cls, v in sorted(by_cls.items(), key=lambda kv: -len(kv[1])):
        print("  %-28s %3d calls  %+.2f m  (spread %.2f)"
              % (cls, len(v), sum(v) / len(v), max(v) - min(v)))

    agree_yes = flip = dice = both_no = 0
    flips = []
    for n, ox, oy, oz, fx, fy, tx, ty, dist, dt, ans in rows:
        ox, oy = float(ox), float(oy)
        tx, ty = float(tx), float(ty)
        seen = (ans == "SEEN")

        u = identify(units, ox, oy)
        eye = L.EYE.get(u.cls, L.EYE_DEFAULT) if u else L.EYE_DEFAULT
        ok, why, at = L.los(t, ox, oy, t.ground(ox, oy) + eye,
                            tx, ty, t.ground(tx, ty) + HULL)

        if seen and ok:
            agree_yes += 1
        elif seen and not ok:
            flip += 1
            flips.append((n, float(dist), why, at))
        elif ok:
            dice += 1
        else:
            both_no += 1

    print()
    print("  engine SEEN, ground agrees          %4d" % agree_yes)
    print("  engine SEEN, ground says BLOCKED    %4d   <- the flaw" % flip)
    print("  engine missed, ground was clear     %4d   (detection dice, not geometry)"
          % dice)
    print("  engine missed, ground blocked too   %4d" % both_no)
    if agree_yes + flip:
        print("\n  %.0f%% of the engine's positive sightings are through solid "
              "ground or woodland." % (100.0 * flip / (agree_yes + flip)))

    if flips:
        print("\n  blocked sightings, by cause:")
        for n, dist, why, at in flips[:30]:
            print("    call %-6s %6.0f m   lost to %-8s at %5.0f m"
                  % (n, dist, why, at))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1
         else r"M:\TvT_INJECT_SANDBOX\tvt_los.log",
         sys.argv[2] if len(sys.argv) > 2
         else r"M:\T34vsTiger\Missions\Campaign_1\Mission_2")
