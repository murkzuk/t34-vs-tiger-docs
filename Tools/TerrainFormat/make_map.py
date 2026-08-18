"""
Generate a complete, self-consistent TvT mission terrain set from real SRTM
elevation.

Why this exists: SteppeTemplate - and therefore Berezov, and everything else
built on it - has its RouterZone and TerrainZone effectively inverted. Its
visuals are 80% grass while its router map says 60% dense forest, so AI advances
die on open ground with nothing logged. Working shipped missions are the other
way round (Campaign_2/Mission_4: 64% forested terrain, 93% open router map).

The rule this generator enforces by construction:

    TerrainZone  = what you SEE      (vegetation, ground cover)
    RouterZone   = where you can DRIVE (passability)

They are related but not the same, and the router map must never be a copy of
the vegetation map.

Elevation source: AWS elevation-tiles-prod "terrarium" tiles, the same data the
ww2-tank-battle-terrain-generator uses. Decoding is
    height_m = (R * 256 + G + B / 256) - 32768
"""

import math, struct, urllib.request, zlib, io, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tvt_terrain as T

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


# ------------------------------------------------------------------ tiles

def deg2tile(lat, lon, z):
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y


def _png_gray_rgb(data):
    """Minimal PNG reader for the 8-bit RGB terrarium tiles (no PIL dependency)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    w = h = None
    idat = b""
    pos = 8
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitd, colt = struct.unpack(">IIBB", chunk[:10])
            assert bitd == 8 and colt == 2, f"unexpected PNG format {bitd}/{colt}"
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3
    out = bytearray(w * h * 3)
    prev = bytearray(stride)
    p = 0
    for row in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if f == 1:
            for i in range(3, stride): line[i] = (line[i] + line[i - 3]) & 255
        elif f == 2:
            for i in range(stride): line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - 3] if i >= 3 else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - 3] if i >= 3 else 0
                c = prev[i - 3] if i >= 3 else 0
                b = prev[i]
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[row * stride:(row + 1) * stride] = line
        prev = line
    return w, h, out


def fetch_heights(lat, lon, span_m, zoom=14):
    """Return (dim, [metres]) covering a square span_m centred on lat/lon.

    Zoom matters: at zoom 12 one source pixel covers ~24 m, which is 5.5 output
    samples on a 2049-grid over 9 km - that terraces the ground visibly. Zoom 14
    is ~6 m per source pixel (1.4 samples), and the mosaic is then sampled
    BILINEARLY rather than nearest-neighbour, which removes the stepping.
    """
    dlat = span_m / 111320.0
    dlon = span_m / (111320.0 * math.cos(math.radians(lat)))
    n, s_, w_, e_ = lat + dlat/2, lat - dlat/2, lon - dlon/2, lon + dlon/2
    x0, y0 = deg2tile(s_, w_, zoom)
    x1, y1 = deg2tile(n, e_, zoom)
    tx0, tx1 = int(math.floor(min(x0, x1))), int(math.floor(max(x0, x1)))
    ty0, ty1 = int(math.floor(min(y0, y1))), int(math.floor(max(y0, y1)))

    nx, ny = tx1 - tx0 + 1, ty1 - ty0 + 1
    print(f"  fetching {nx*ny} tiles at zoom {zoom} ...")
    TS = 256
    mosaic = [0.0] * (nx*TS * ny*TS)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            url = TILE_URL.format(z=zoom, x=tx, y=ty)
            tw, th, px = _png_gray_rgb(urllib.request.urlopen(url, timeout=30).read())
            ox, oy = (tx - tx0)*TS, (ty - ty0)*TS
            for j in range(th):
                row = (oy + j) * (nx*TS) + ox
                for i in range(tw):
                    o = (j*tw + i)*3
                    mosaic[row + i] = (px[o]*256 + px[o+1] + px[o+2]/256.0) - 32768.0

    MW, MH = nx*TS, ny*TS
    def bilinear(fx, fy):
        fx = min(max(fx, 0), MW - 1.001); fy = min(max(fy, 0), MH - 1.001)
        ix, iy = int(fx), int(fy)
        tx_, ty_ = fx - ix, fy - iy
        a = mosaic[iy*MW + ix];       b = mosaic[iy*MW + ix + 1]
        c = mosaic[(iy+1)*MW + ix];   d = mosaic[(iy+1)*MW + ix + 1]
        return (a*(1-tx_) + b*tx_)*(1-ty_) + (c*(1-tx_) + d*tx_)*ty_

    dim = T.HMAP_DIM
    out = [0.0] * (dim*dim)
    for j in range(dim):
        fy = (y0 + (y1 - y0) * (j/(dim-1)) - ty0) * TS
        base = j*dim
        for i in range(dim):
            fx = (x0 + (x1 - x0) * (i/(dim-1)) - tx0) * TS
            out[base + i] = bilinear(fx, fy)
    return dim, out


# ------------------------------------------------------------------ writers

def write_terrain_set(outdir, heights_m, dim, span_m,
                      forest_frac=0.18, water_level=None, seed=1943,
                      RAW_PER_METRE=18.0):
    """
    Write hmap.raw plus the zone maps, keeping router and terrain distinct:

      TerrainZone (what you see) - grass everywhere, forest in the chosen patches
      RouterZone  (where you drive) - open by default; forest only where the
                  terrain actually has forest, non-passable only for water and
                  genuinely steep slopes.
    """
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    import random
    rng = random.Random(seed)

    # Robust range, not min/max. A single corrupt sample (one cell in 4.2M was
    # decoding to -1665 m) otherwise consumes the whole output band and squashes
    # the real terrain into a sliver - which reads in game as both wrong relief
    # and visible terracing.
    srt = sorted(heights_m)
    lo = srt[int(len(srt) * 0.001)]
    hi = srt[int(len(srt) * 0.999)]
    raw_lo, raw_hi = srt[0], srt[-1]
    if raw_lo < lo - 5 or raw_hi > hi + 5:
        print(f"  outliers rejected: raw {raw_lo:.0f}..{raw_hi:.0f} m -> "
              f"using {lo:.0f}..{hi:.0f} m")
    heights_m = [min(hi, max(lo, h)) for h in heights_m]
    print(f"  elevation {lo:.0f}..{hi:.0f} m  (relief {hi-lo:.0f} m)")

    # TvT stores heights as uint16, but NOT over the full range. Every shipped
    # map sits in a narrow band - Campaign_2/Mission_4 is 7672..10920 and the
    # original Berezov 7642..10918, i.e. base ~7650 with ~3280 of relief. The
    # engine applies FloatValueFactor (0.07*257) on top, so writing 0..65535
    # produces mountains kilometres high. Map real metres into the shipped band
    # instead, which keeps vehicle physics and camera behaviour comparable to
    # hand-built missions.
    # Do NOT normalise real relief to fill the shipped band. Shipped maps use
    # ~3250 raw of relief because their designers wanted dramatic ground; the
    # Kursk steppe is genuinely gentle (75 m over 9 km, under 1% grade).
    # Stretching 75 m to fill 3250 raw turns rolling hills into ridges.
    # Use a FIXED metres-per-raw-unit scale so gentle ground reads as gentle.
    RAW_BASE = 7650
    hm = [RAW_BASE + int(round((h - lo) * RAW_PER_METRE)) for h in heights_m]
    print(f"  vertical scale {RAW_PER_METRE} raw/m -> "
          f"{(hi-lo)*RAW_PER_METRE:.0f} raw of relief "
          f"({(hi-lo)*RAW_PER_METRE/3250*100:.0f}% of a shipped map's)")
    T.write_hmap(outdir / "hmap.raw", dim, hm)
    T.write_hmap(outdir / "hwater.raw", dim, [0] * (dim * dim))
    print(f"  hmap.raw   {dim}x{dim}")

    # slope, computed on the height grid, drives both forest placement and
    # non-passable marking
    zd = T.ZONE_DIM
    def h_at(px, py):
        return hm[min(dim - 1, py * dim // zd) * dim + min(dim - 1, px * dim // zd)]
    slope = [0] * (zd * zd)
    for y in range(zd):
        for x in range(zd):
            c = h_at(x, y)
            dx = abs(h_at(min(zd - 1, x + 1), y) - c)
            dy = abs(h_at(x, min(zd - 1, y + 1)) - c)
            slope[y * zd + x] = max(dx, dy)
    smax = max(slope) or 1
    steep = sorted(slope)[int(len(slope) * 0.985)]     # top 1.5% counts as steep

    # coherent forest blobs rather than noise
    forest = bytearray(zd * zd)
    n_blobs = int(forest_frac * 340)
    for _ in range(n_blobs):
        cx, cy = rng.randrange(zd), rng.randrange(zd)
        r = rng.randint(14, 46)
        for y in range(max(0, cy - r), min(zd, cy + r)):
            for x in range(max(0, cx - r), min(zd, cx + r)):
                d = math.hypot(x - cx, y - cy)
                if d < r * (0.72 + 0.28 * rng.random()):
                    forest[y * zd + x] = 1

    pal = _steppe_palette()
    terr = bytearray(zd * zd)
    rout = bytearray(zd * zd)
    Z = T.ZMC
    for i in range(zd * zd):
        wooded = forest[i]
        st = slope[i]
        # --- what you see ---
        terr[i] = Z["Forest01"] if wooded else Z["Grass01"]
        # --- where you can drive ---
        if st >= steep:
            rout[i] = Z["NonPassable"]
        elif wooded:
            rout[i] = Z["Forest01"]
        else:
            rout[i] = Z["OffRoad01"]

    T.write_bmp8(outdir / "TerrainZone_Test.bmp", zd, zd, pal, _rows(terr, zd))
    T.write_bmp8(outdir / "RouterZone_Test.bmp", zd, zd, pal, _rows(rout, zd))
    T.write_bmp8(outdir / "micro_Test.bmp", zd, zd, pal, _rows(terr, zd))

    fpix = bytearray()
    for i in range(zd * zd):
        v = 255 if forest[i] else 0
        fpix += bytes((v, v, v, 255))
    T.write_dds_a8r8g8b8(outdir / "forest_Test.tex", zd, zd, fpix)
    lnd = bytearray()
    for i in range(256 * 256):
        lnd += bytes((90, 120, 70, 255))
    T.write_dds_a8r8g8b8(outdir / "lnd_Test.tex", 256, 256, lnd)

    fr_t = sum(1 for b in terr if b in T.FOREST_CODES) * 100.0 / (zd * zd)
    fr_r = sum(1 for b in rout if b in T.FOREST_CODES) * 100.0 / (zd * zd)
    np_r = sum(1 for b in rout if b == Z["NonPassable"]) * 100.0 / (zd * zd)
    print(f"  TerrainZone forest {fr_t:5.2f}%")
    print(f"  RouterZone  forest {fr_r:5.2f}%   non-passable {np_r:4.2f}%")
    print(f"  -> router is {100-fr_r-np_r:.1f}% drivable "
          f"(Campaign_2/Mission_4, which works, is ~93%)")


def _rows(buf, dim):
    return [bytearray(buf[y * dim:(y + 1) * dim]) for y in range(dim)]


def _steppe_palette():
    """256-entry BGRA palette using the real ZMC colours where they are known."""
    pal = [(0, 0, 0, 0)] * 256
    known = {
        0: (255, 0, 255), 1: (255, 229, 0), 11: (46, 0, 114), 12: (97, 0, 114),
        13: (0, 0, 119), 32: (128, 255, 26), 33: (39, 118, 0), 34: (144, 112, 0),
        35: (0, 112, 95), 101: (0, 0, 153), 102: (0, 0, 204), 103: (0, 0, 255),
        122: (255, 204, 0), 150: (0, 0, 0), 217: (253, 224, 0),
    }
    for idx, (r, g, b) in known.items():
        pal[idx] = (b, g, r, 0)
    return pal


if __name__ == "__main__":
    # Placeholder centre - southern face of the Kursk salient. CONFIRM before use.
    LAT, LON, SPAN = 50.86, 36.10, 9000
    out = Path(r"K:\tvt_terrain\out\Berezov")
    print(f"generating {SPAN}m map centred on {LAT}, {LON}")
    dim, h = fetch_heights(LAT, LON, SPAN)
    write_terrain_set(out, h, dim, SPAN)
    print(f"\nwritten to {out}")
