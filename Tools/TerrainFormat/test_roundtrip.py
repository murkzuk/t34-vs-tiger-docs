"""
Validate every reader/writer by round-tripping real shipped TvT mission files.

The rule: if we cannot read a known-good file and write it back byte-identical,
we have no business generating new ones. Runs entirely offline - no game needed.
"""
import sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tvt_terrain as T

MISSIONS = Path(r"M:\T34vsTiger\Missions")
TMP = Path(r"K:\tvt_terrain\_tmp")
TMP.mkdir(exist_ok=True)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]

passed = failed = 0

def check(label, ok, detail=""):
    global passed, failed
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if ok: passed += 1
    else:  failed += 1

print("=== heightmaps (uint16 grids) ===")
for p in list(MISSIONS.rglob("hmap.raw"))[:4] + list(MISSIONS.rglob("hwater.raw"))[:2]:
    try:
        dim, vals = T.read_hmap(p)
        out = TMP / "rt.raw"
        T.write_hmap(out, dim, vals)
        check(f"{p.parent.name}/{p.name}", sha(p) == sha(out), f"{dim}x{dim}")
    except Exception as e:
        check(f"{p.parent.name}/{p.name}", False, f"ERROR {e}")

print("\n=== 8-bit indexed BMP zone maps ===")
bmps = sorted(MISSIONS.rglob("*Zone*.bmp"))[:5] + sorted(MISSIONS.rglob("micro_*.bmp"))[:2]
for p in bmps:
    try:
        w, h, pal, rows = T.read_bmp8(p)
        out = TMP / "rt.bmp"
        T.write_bmp8(out, w, h, pal, rows)
        same = sha(p) == sha(out)
        detail = f"{w}x{h}"
        if not same:
            a, b = Path(p).read_bytes(), Path(out).read_bytes()
            diff = sum(1 for x, y in zip(a, b) if x != y)
            detail += f"  size {len(a)}->{len(b)}, {diff} bytes differ"
        check(f"{p.parent.name}/{p.name}", same, detail)
    except Exception as e:
        check(f"{p.parent.name}/{p.name}", False, f"ERROR {e}")

print("\n=== DDS textures ===")
for p in sorted(MISSIONS.rglob("lnd_*.tex"))[:2] + sorted(MISSIONS.rglob("forest_*.tex"))[:2]:
    try:
        d = T.read_dds(p)
        fc = d["fourcc"] if d["fourcc"] != b"\x00\x00\x00\x00" else b"(none)"
        uncompressed = d["bpp"] == 32
        if uncompressed:
            out = TMP / "rt.tex"
            T.write_dds_a8r8g8b8(out, d["w"], d["h"], d["data"][:d["w"]*d["h"]*4])
            same = sha(p) == sha(out)
            check(f"{p.parent.name}/{p.name}", same, f"{d['w']}x{d['h']} {d['bpp']}bpp")
        else:
            check(f"{p.parent.name}/{p.name} (read-only, {fc.decode(errors='replace')})",
                  True, f"{d['w']}x{d['h']}")
    except Exception as e:
        check(f"{p.parent.name}/{p.name}", False, f"ERROR {e}")

print("\n=== resamplers (identity + known cases) ===")
src = [y * 8 + x for y in range(8) for x in range(8)]
check("nearest identity 8->8", T.resample_nearest(src, 8, 8, 8, 8) == src)
check("bilinear identity 8->8", T.resample_bilinear(src, 8, 8, 8, 8) == src)
up = T.resample_nearest(src, 8, 8, 16, 16)
check("nearest 8->16 preserves value set", set(up) == set(src))
bl = T.resample_bilinear(src, 8, 8, 16, 16)
check("bilinear 8->16 stays in range", min(bl) >= min(src) and max(bl) <= max(src))
check("bilinear 8->16 corner fidelity", bl[0] == src[0] and bl[-1] == src[-1])

print("\n=== zone palette sanity ===")
p = next(MISSIONS.rglob("TerrainZone*.bmp"))
w, h, pal, rows = T.read_bmp8(p)
used = sorted({b for r in rows for b in r})
known = set(T.ZMC.values())
unknown = [u for u in used if u not in known]
check("all palette indices used by a real map are named ZMC_ codes",
      not unknown, f"{len(used)} used" + (f", UNKNOWN {unknown}" if unknown else ""))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
