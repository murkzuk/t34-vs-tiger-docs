"""
TvT terrain format reader/writer.

Formats confirmed by byte-exact arithmetic against real mission folders:

  hmap.raw / hwater.raw   2049 x 2049 uint16 little-endian, no header
                          (2049^2 * 2 = 8,396,802 bytes exactly)
  RouterZone_*.bmp        2048 x 2048 8-bit indexed BMP (2048^2 + 1080)
  TerrainZone_*.bmp       1024 x 1024 8-bit indexed BMP (1024^2 + 1080)
  micro_*.bmp             1024 x 1024 8-bit indexed BMP
  lnd_*.tex               DDS, 256x256 A8R8G8B8 (128-byte header + data)
  forest_*.tex            DDS, 1024x1024 A8R8G8B8

Palette indices in the zone BMPs are the ZMC_* constants from
Scripts\\Common\\BaseZone.script - the engine reads them through a script-side
ColorTable and logs "Unknown color %0X in cell (%i,%i,%i)" for anything it does
not recognise, which makes the masks self-validating in-game.

Design rule: every writer here is validated by round-tripping a real shipped
mission file and comparing bytes. A writer that cannot reproduce a known-good
file is not trusted to generate a new one.
"""

import struct
from pathlib import Path

# ---------------------------------------------------------------- constants

HMAP_DIM = 2049          # heightmap is (2^n)+1 - vertex grid, not cell grid
ROUTER_DIM = 2048
ZONE_DIM = 1024

# ZMC_* zone codes, from Scripts\Common\BaseZone.script
ZMC = {
    "Road01": 0,          "OffRoad01": 1,
    "Forest01": 11,       "Forest02": 12,   "Forest03": 13,   "Forest04": 14,
    "PowerLine02": 19,    "RoadForest": 20, "Pole01": 20,     "Pole02": 18,
    "PowerLine01": 17,
    "Bush01": 27,         "Bush02": 28,     "Bush03": 29,     "Bush04": 30,
    "Grass01": 32,        "Grass02": 33,    "Grass03": 34,    "Grass04": 35,
    "Road01Add": 39,
    "ShrubberyLarge": 49, "ShrubberyRegular": 50,
    "ShrubberyCasual": 51, "SpecialLongAloneTree": 52,
    "VillagePlanting01": 60, "VillagePlanting02": 61, "VillagePlanting03": 62,
    "Water01": 101,       "ShallowWater01": 102, "BeachWater01": 103,
    "RoadObject": 110,    "AllPassable": 111,
    "OffRoad02": 122,     "OffRoad03": 123,
    "NonPassable": 150,
    "OffRoad04": 217,
}
FOREST_CODES = {ZMC["Forest01"], ZMC["Forest02"], ZMC["Forest03"],
                ZMC["Forest04"], ZMC["RoadForest"]}


# ---------------------------------------------------------------- heightmap

def read_hmap(path):
    """Return (dim, list-of-uint16). Validates the size is exactly dim^2*2."""
    data = Path(path).read_bytes()
    n = len(data) // 2
    dim = int(round(n ** 0.5))
    if dim * dim * 2 != len(data):
        raise ValueError(f"{path}: {len(data)} bytes is not a square uint16 grid")
    return dim, list(struct.unpack("<%dH" % n, data))


def write_hmap(path, dim, values):
    if len(values) != dim * dim:
        raise ValueError(f"expected {dim*dim} values, got {len(values)}")
    Path(path).write_bytes(struct.pack("<%dH" % len(values), *values))


# ---------------------------------------------------------- 8-bit indexed BMP

def read_bmp8(path):
    """Return (width, height, palette[256] as RGBA tuples, rows top-to-bottom)."""
    d = Path(path).read_bytes()
    if d[:2] != b"BM":
        raise ValueError(f"{path}: not a BMP")
    pix_off = struct.unpack_from("<I", d, 10)[0]
    hdr = struct.unpack_from("<I", d, 14)[0]
    w, h = struct.unpack_from("<ii", d, 18)
    bpp = struct.unpack_from("<H", d, 28)[0]
    if bpp != 8:
        raise ValueError(f"{path}: {bpp}bpp, expected 8")
    bottom_up = h > 0
    h = abs(h)
    pal_off = 14 + hdr
    palette = [tuple(d[pal_off + i * 4: pal_off + i * 4 + 4]) for i in range(256)]
    stride = (w + 3) // 4 * 4
    rows = []
    for y in range(h):
        src = h - 1 - y if bottom_up else y
        start = pix_off + src * stride
        rows.append(bytearray(d[start:start + w]))
    return w, h, palette, rows


def write_bmp8(path, w, h, palette, rows):
    """Write bottom-up 8-bit indexed BMP with a 40-byte BITMAPINFOHEADER."""
    stride = (w + 3) // 4 * 4
    pad = stride - w
    pix_off = 14 + 40 + 256 * 4
    size = pix_off + stride * h
    out = bytearray()
    out += b"BM" + struct.pack("<IHHI", size, 0, 0, pix_off)
    out += struct.pack("<IiiHHIIiiII", 40, w, h, 1, 8, 0, stride * h, 0, 0, 256, 0)
    for c in palette:
        out += bytes(c)
    for y in range(h - 1, -1, -1):          # bottom-up
        out += bytes(rows[y]) + b"\x00" * pad
    # Every shipped TvT zone BMP carries two zero bytes past the declared file
    # size. Surplus by the spec, but universal in the originals - match the
    # convention rather than gamble on whether the loader depends on it.
    out += b"\x00\x00"
    Path(path).write_bytes(bytes(out))


# ----------------------------------------------------------------- DDS (.tex)

def read_dds(path):
    d = Path(path).read_bytes()
    if d[:4] != b"DDS ":
        raise ValueError(f"{path}: not a DDS")
    h, w = struct.unpack_from("<ii", d, 12)
    fourcc = d[84:88]
    bpp = struct.unpack_from("<I", d, 88)[0]
    return {"w": w, "h": h, "fourcc": fourcc, "bpp": bpp,
            "header": d[:128], "data": d[128:]}


def write_dds_a8r8g8b8(path, w, h, pixels_bgra):
    """Uncompressed 32-bit DDS, matching how lnd_*.tex / forest_*.tex are stored."""
    if len(pixels_bgra) != w * h * 4:
        raise ValueError("pixel buffer size mismatch")
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<I", hdr, 4, 124)
    struct.pack_into("<I", hdr, 8, 0x1007)          # CAPS|HEIGHT|WIDTH|PITCH
    struct.pack_into("<i", hdr, 12, h)
    struct.pack_into("<i", hdr, 16, w)
    struct.pack_into("<I", hdr, 20, 0)              # pitch: shipped .tex files store 0
    struct.pack_into("<I", hdr, 76, 32)             # pixelformat size
    struct.pack_into("<I", hdr, 80, 0x41)           # RGB | ALPHAPIXELS
    struct.pack_into("<I", hdr, 88, 32)             # bit count
    struct.pack_into("<I", hdr, 92, 0x00FF0000)     # R
    struct.pack_into("<I", hdr, 96, 0x0000FF00)     # G
    struct.pack_into("<I", hdr, 100, 0x000000FF)    # B
    struct.pack_into("<I", hdr, 104, 0xFF000000)    # A
    struct.pack_into("<I", hdr, 108, 0x1002)        # caps: TEXTURE
    Path(path).write_bytes(bytes(hdr) + bytes(pixels_bgra))


# ------------------------------------------------------------------ resample

def resample_nearest(src, sw, sh, dw, dh):
    """Nearest-neighbour. Used for zone masks, where interpolation would invent
    palette indices that do not exist in the ColorTable."""
    out = [0] * (dw * dh)
    for y in range(dh):
        sy = min(sh - 1, y * sh // dh)
        row = sy * sw
        orow = y * dw
        for x in range(dw):
            out[orow + x] = src[row + min(sw - 1, x * sw // dw)]
    return out


def resample_bilinear(src, sw, sh, dw, dh):
    """Bilinear. Used for heights, where smoothness matters and any value is legal."""
    out = [0] * (dw * dh)
    xr = (sw - 1) / max(1, dw - 1)
    yr = (sh - 1) / max(1, dh - 1)
    for y in range(dh):
        fy = y * yr
        y0 = int(fy); y1 = min(sh - 1, y0 + 1); ty = fy - y0
        for x in range(dw):
            fx = x * xr
            x0 = int(fx); x1 = min(sw - 1, x0 + 1); tx = fx - x0
            a = src[y0 * sw + x0]; b = src[y0 * sw + x1]
            c = src[y1 * sw + x0]; d = src[y1 * sw + x1]
            top = a + (b - a) * tx
            bot = c + (d - c) * tx
            out[y * dw + x] = int(round(top + (bot - top) * ty))
    return out
