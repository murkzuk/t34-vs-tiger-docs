"""Rebuild the missing mipmap chain on a DXT1 .tex.

THE BUG. ZeeWolf's mega-terrain material lists sixteen micro textures - eight
"Close" and eight "Near" (a distant tier stock TvT does not have). Fifteen of
them carry a full mipmap chain. lnd_micro16.tex, which is index 7 = FOREST in
the Near tier, has NONE:

    lnd_micro09..15   256x256 DXT1, 6 mips, 43680 bytes of payload
    lnd_micro16       256x256 DXT1, 0 mips, 32768 bytes of payload

A texture with no mipmaps is sampled at one texel per screen pixel no matter
how far away it is. Viewed nearly head-on that is merely sharp; viewed at a
GRAZING angle, where one screen pixel covers dozens of texels, it aliases into
bright blown-out patches. Which is exactly the reported symptom: distant
terrain perfect from the F6 external camera (looking down at the ground, low
minification) and large white pockets from the commander's low unbuttoned view
(looking along it). Pockets, because index 7 is forest ground - it appears
where the forest is, not everywhere.

THE FIX. Generate levels 1..5 and splice them on. The base level is copied
BYTE FOR BYTE from the original, so the texture you actually see up close is
untouched and no re-compression artefact is introduced where it would show.
Only the distant levels are new, and those are the ones that do not currently
exist at all.

The header is taken wholesale from a sibling (same dimensions, same format,
same mip count), which is safer than hand-editing flag bits.

Validation is built in: the output must be byte-for-byte the same LENGTH as its
siblings, 43808. If the arithmetic is wrong that check fails loudly.
"""
import io
import os
import struct
import sys

TEX = r"M:\T34vsTiger_ZW2015\Textures"


def decode_dxt1(data, w, h):
    """DXT1 -> list of (r,g,b) rows. Alpha is ignored; these are ground tiles."""
    px = [[(0, 0, 0)] * w for _ in range(h)]
    o = 0
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            c0, c1, bits = struct.unpack_from("<HHI", data, o)
            o += 8
            cols = []
            for c in (c0, c1):
                r = (c >> 11) & 0x1F
                g = (c >> 5) & 0x3F
                b = c & 0x1F
                cols.append((r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2))
            if c0 > c1:
                cols.append(tuple((2 * cols[0][i] + cols[1][i]) // 3 for i in range(3)))
                cols.append(tuple((cols[0][i] + 2 * cols[1][i]) // 3 for i in range(3)))
            else:
                cols.append(tuple((cols[0][i] + cols[1][i]) // 2 for i in range(3)))
                cols.append((0, 0, 0))
            for j in range(4):
                for i in range(4):
                    x, y = bx + i, by + j
                    if x < w and y < h:
                        px[y][x] = cols[(bits >> (2 * (4 * j + i))) & 3]
    return px


def halve(px):
    """Box filter. The right choice for a mip chain: cheap, and it averages
    rather than picking, which is what stops distant ground shimmering."""
    h, w = len(px), len(px[0])
    nh, nw = max(1, h // 2), max(1, w // 2)
    out = [[(0, 0, 0)] * nw for _ in range(nh)]
    for y in range(nh):
        for x in range(nw):
            a = px[2 * y][2 * x]
            b = px[2 * y][min(2 * x + 1, w - 1)]
            c = px[min(2 * y + 1, h - 1)][2 * x]
            d = px[min(2 * y + 1, h - 1)][min(2 * x + 1, w - 1)]
            out[y][x] = tuple((a[i] + b[i] + c[i] + d[i]) // 4 for i in range(3))
    return out


def _565(c):
    return ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)


def encode_dxt1(px):
    """Endpoints from the block's luminance extremes, then nearest of the four
    palette entries. Not a rate-distortion optimiser - but these are mip levels
    of a ground tile that currently do not exist, so anything correct is an
    improvement on nothing."""
    h, w = len(px), len(px[0])
    out = bytearray()
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            block = []
            for j in range(4):
                for i in range(4):
                    block.append(px[min(by + j, h - 1)][min(bx + i, w - 1)])
            lum = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in block]
            lo = block[lum.index(min(lum))]
            hi = block[lum.index(max(lum))]
            c0, c1 = _565(hi), _565(lo)
            if c0 == c1:                    # flat block: keep 4-colour mode
                if c1 == 0:
                    c0 = 1
                else:
                    c1 = c0 - 1
            if c0 < c1:
                c0, c1 = c1, c0
            pal = []
            for c in (c0, c1):
                r = (c >> 11) & 0x1F
                g = (c >> 5) & 0x3F
                b = c & 0x1F
                pal.append((r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2))
            pal.append(tuple((2 * pal[0][i] + pal[1][i]) // 3 for i in range(3)))
            pal.append(tuple((pal[0][i] + 2 * pal[1][i]) // 3 for i in range(3)))
            bits = 0
            for n, c in enumerate(block):
                best, bd = 0, None
                for k, p in enumerate(pal):
                    d = sum((c[i] - p[i]) ** 2 for i in range(3))
                    if bd is None or d < bd:
                        bd, best = d, k
                bits |= best << (2 * n)
            out += struct.pack("<HHI", c0, c1, bits)
    return bytes(out)


def fix(target, sibling, levels=6):
    tp = os.path.join(TEX, target)
    sp = os.path.join(TEX, sibling)
    tgt = io.open(tp, "rb").read()
    sib = io.open(sp, "rb").read()

    hdr = sib[:128]                      # same size/format/mip count - trust it
    h, w = struct.unpack_from("<II", tgt, 12)
    base = tgt[128:128 + (w * h // 2)]
    print("%s: %dx%d, base payload %d bytes" % (target, w, h, len(base)))

    px = decode_dxt1(base, w, h)
    chain = bytearray(base)              # level 0 kept byte for byte
    for lvl in range(1, levels):
        px = halve(px)
        enc = encode_dxt1(px)
        chain += enc
        print("   level %d: %dx%d -> %d bytes" % (lvl, len(px[0]), len(px), len(enc)))

    out = hdr + bytes(chain)
    if len(out) != len(sib):
        raise SystemExit("SIZE MISMATCH: built %d, siblings are %d"
                         % (len(out), len(sib)))
    print("   total %d bytes - matches %s exactly" % (len(out), sibling))

    bak = tp + ".bak_nomips"
    if not os.path.exists(bak):
        io.open(bak, "wb").write(tgt)
        print("   original backed up to", os.path.basename(bak))
    io.open(tp, "wb").write(out)
    print("   written")


if __name__ == "__main__":
    fix(sys.argv[1] if len(sys.argv) > 1 else "lnd_micro16.tex",
        sys.argv[2] if len(sys.argv) > 2 else "lnd_micro15.tex")
