"""Can this gun defeat that target at this range?

The AI's answer today is a range cap: CAutoShooter.RadarMaxDistance = 3000,
CAutoCommander = 1500. A number with no relationship to what the gun can
actually do to what it is pointed at.

TvT already holds everything needed to answer it properly:

  Common\\Piercing.script   penetration vs range, per ammo type, per gun
  Common\\Armour.script     armour thickness per facet, per vehicle

Piercing stores penetration as a NORMALISED curve times a power:

    ...CalibrePenetrationPower      = 98.0 / 100.0
    ...CalibrePenetrationByDistance = [[100, 98/98, 2000, 63/98],
                                       [[500, 91/98], [1000, 82/98], [1500, 72/98]]]

which is 98 mm at 100 m falling to 63 mm at 2000 m. Armour is
[thickness_mm, something, 0.5] per facet. So the comparison is direct.

This reads both files and prints the honest answer, which is what the AI
should be asking instead of "is it within 3000 m".
"""
import io
import re
import sys

SCRIPTS = r"M:\T34vsTiger\Scripts\Common"


def read(name):
    return io.open("%s\\%s" % (SCRIPTS, name), "rb").read().decode("cp1251", "replace")


def guns():
    """Penetration curves: {gun: {ammo: [(range_m, mm), ...]}}"""
    s = read("Piercing.script")
    power = dict(re.findall(r"(\w+?)PenetrationPower\s*=\s*([\d.]+)\s*/\s*[\d.]+", s))
    out = {}
    for key, body in re.findall(r"(\w+?)PenetrationByDistance\s*=\s*(\[.*?\]\];)", s):
        if key not in power:
            continue
        mm = float(power[key])
        pts = [(float(d), float(a) / float(b) * mm)
               for d, a, b in re.findall(r"([\d.]+)\s*,\s*([\d.]+)\s*/\s*([\d.]+)", body)]
        out[key] = sorted(set(pts))
    return out


def armour():
    """{vehicle: {facet: mm}}"""
    s = read("Armour.script")
    out = {}
    for veh, facet, mm in re.findall(
            r"(\w+?)UnitArmour(\w+?)\s*=\s*\[\s*([\d.]+)", s):
        out.setdefault(veh, {})[facet] = float(mm)
    return out


def pen_at(curve, rng):
    """Linear interpolation between the tabulated points."""
    if rng <= curve[0][0]:
        return curve[0][1]
    if rng >= curve[-1][0]:
        return curve[-1][1]
    for (d0, p0), (d1, p1) in zip(curve, curve[1:]):
        if d0 <= rng <= d1:
            return p0 + (p1 - p0) * (rng - d0) / (d1 - d0)
    return curve[-1][1]


def table(gun_key, target, facets, ranges=(100, 500, 800, 1000, 1500, 2000)):
    G, A = guns(), armour()
    curve = G.get(gun_key)
    arm = A.get(target)
    if not curve or not arm:
        print("missing data:", gun_key, target)
        return
    print("\n%s  vs  %s" % (gun_key, target))
    print("  %-16s %s" % ("facet (mm)", "".join("%8d m" % r for r in ranges)))
    for f in facets:
        if f not in arm:
            continue
        row = ""
        for r in ranges:
            p = pen_at(curve, r)
            row += "%9s" % ("%+.0f" % (p - arm[f]))
        print("  %-16s %s" % ("%s %.0f" % (f, arm[f]), row))
    print("  (mm of penetration MINUS armour: positive kills, negative bounces)")


if __name__ == "__main__":
    G = guns()
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for k in sorted(G):
            print("  %-52s %s" % (k, " ".join("%.0f@%.0f" % (p, d) for d, p in G[k])))
        sys.exit()
    FACETS = ["TurretFWD", "HullFWD", "HullRIGHT", "TurretREAR"]
    table("TankPzVIAusfECalibre", "TankT34_85_44", FACETS)
    table("TankT34_85_44Calibre", "TankPzVIAusfE", FACETS)
    table("TankPzIVAusfGCalibre", "TankPzVIAusfE", FACETS)
