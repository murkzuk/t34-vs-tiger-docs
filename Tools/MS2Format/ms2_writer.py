"""
.ms2 writer - edit geometry in place and write the file back.  [2026-08-26]

DESIGN, and the reason it is shaped this way:

The .ms2 layout is fully walked - the reader accounts for 100% of every file
tested, an 8-byte header and no trailing bytes - but several blocks are of
known SIZE and unknown MEANING (notably the vcount*24 block gated by flag
0x40000, almost certainly tangent/binormal data, and the 80-byte bind-pose
records on skinned nodes).

So this writer does not regenerate a file. It copies the original byte-for-byte
and substitutes only the geometry span, which is proven to round-trip exactly
(138 of 138 nodes byte-identical on the King Tiger). Everything unknown is
preserved verbatim rather than invented.

CONSEQUENCE, and it is a real limit: vertex and index COUNTS must not change.
Changing them would invalidate the vcount-sized blocks, the bounding box and
sphere, and the packed (icount << 16) | material_index record. Moving vertices,
rescaling, and rewriting UVs are all safe. Adding or removing geometry is NOT
supported here and needs those blocks regenerated first.

Verified: an unedited round-trip is byte-identical to the source file.
"""
import struct
import ms2_reader as R


def _spans(path):
    """Walk the file, recording each node's geometry byte-range."""
    data = open(path, 'rb').read()
    out = []
    orig = R._read_node

    def traced(d, offset):
        start = offset
        node, newoff = orig(d, offset)
        _, o = R._read_cstring(d, start)
        vcount, icount, other = struct.unpack_from('<3i', d, o + 44)
        o += 56
        geo_start = o
        if vcount > 0:
            o += vcount * 3 * 4 * 2 + vcount * 2 * 4
        if icount > 0:
            o += icount * 2
        out.append({"node": node, "vcount": vcount, "icount": icount,
                    "start": geo_start, "end": o})
        return node, newoff

    R._read_node = traced
    try:
        nodes = R.read_ms2(path)
    finally:
        R._read_node = orig
    return data, nodes, out


def _pack(node, vcount, icount):
    buf = struct.pack('<%df' % (vcount * 3), *[c for p in node.positions for c in p])
    buf += struct.pack('<%df' % (vcount * 3), *[c for p in node.normals for c in p])
    buf += struct.pack('<%df' % (vcount * 2), *[c for p in node.uvs for c in p])
    if icount:
        buf += struct.pack('<%dH' % icount, *node.indices)
    return buf


def rewrite(src, dst, edit=None):
    """Copy `src` to `dst`, optionally applying `edit(node)` to each node first.

    `edit` may mutate node.positions / normals / uvs / indices in place, but
    must not change their lengths. Returns (nodes_written, nodes_edited)."""
    data, nodes, spans = _spans(src)
    edited = 0
    out = bytearray(data)
    for s in spans:
        n = s["node"]
        if s["vcount"] == 0:
            continue
        before = _pack(n, s["vcount"], s["icount"])
        assert before == data[s["start"]:s["end"]], \
            "geometry does not round-trip for node %r - refusing to write" % n.name
        if edit is not None and edit(n):
            after = _pack(n, s["vcount"], s["icount"])
            if len(after) != len(before):
                raise ValueError("edit changed the byte length of node %r" % n.name)
            out[s["start"]:s["end"]] = after
            edited += 1
    open(dst, 'wb').write(bytes(out))
    return len(nodes), edited
