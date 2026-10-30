import re, io, os, glob
FIELDS = ("FireDeviation","FirePeriod","FirePeriodRandAdd","MaxSpeed","MaxPower","Mass",
          "MaxRotateSpeed","DirectionSpeedH","DirectionSpeedV","AttackDistanceMax",
          "AttackDistanceMin","MaxRadarDistance","MinRadarDistance","MaxAttackSpeed",
          "SuspensionHeight","Friction","Friction1","LockAngleVMax","LockAngleVMin")
def byclass(path):
    """field values keyed by (class, field) - the only like-for-like comparison,
    because a unit file holds separate AI and player gun classes."""
    if not os.path.exists(path): return {}
    txt = re.sub(r'//[^\n]*', '', io.open(path, encoding="latin-1").read())
    out, cur = {}, "(file)"
    for line in txt.split("\n"):
        m = re.match(r'\s*class\s+(\w+)', line)
        if m: cur = m.group(1)
        for f in FIELDS:
            d = re.search(r'\b%s\s*=\s*([-0-9][-0-9.eEf]*)\s*;' % f, line)
            if d: out[(cur, f)] = d.group(1).rstrip('f')
    return out
ORIG = r"M:\T34vsTiger - Original\Scripts\Units"
ZW   = r"M:\T34vsTiger_ZW2015\Scripts\Units"
units = sorted(os.path.basename(p) for p in glob.glob(ORIG + r"\*.script"))
rows, missing = [], []
for u in units:
    o = byclass(os.path.join(ORIG, u)); z = byclass(os.path.join(ZW, u))
    if not z: missing.append(u); continue
    for k in sorted(set(o) & set(z)):
        if o[k] != z[k]:
            try: fac = float(z[k]) / float(o[k]) if float(o[k]) else None
            except Exception: fac = None
            rows.append((u[:-7], k[0], k[1], o[k], z[k], fac))
print("=== units present in BOTH builds: %d   (only in original: %d)" % (len(units)-len(missing), len(missing)))
print("=== fields differing: %d\n" % len(rows))
print("%-22s %-38s %-18s %9s %9s %7s" % ("unit","class","field","ORIGINAL","ZW","factor"))
for u,c,f,a,b,fac in sorted(rows, key=lambda r: (-(abs((r[5] or 1)-1)), r[0])):
    fs = ("%.2fx" % fac) if fac else "  -"
    print("%-22s %-38s %-18s %9s %9s %7s" % (u[:22], c[:38], f[:18], a, b, fs))
