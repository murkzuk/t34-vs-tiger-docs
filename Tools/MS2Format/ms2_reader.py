"""
.ms2 static-mesh reader (GitHub issue #12, Phase 3 - importer).

Pure-Python, no external dependencies (works under Blender's embedded
Python as well as a normal interpreter). Reads the parts of the format
needed for a static mesh import: node hierarchy, names, and per-vertex
position/normal/UV/index data.

Deliberately does NOT attempt to read the five still-unmapped optional
data blocks (bone attachment, skin blend weights, bind-pose matrices,
and two unnamed joint/skin blocks) - see
Documentation/MS2_Binary_Format_Findings_2026-07-03.md for what's known
and not known about those. This reader skips over them by exact byte
size (which IS known) without interpreting their content, since none of
it is needed to reconstruct static geometry.

Format reference (see the findings doc for the full derivation):
    file header: int32 format_version (always 0), int32 node_count
    per node: length-prefixed name, bbox (6 floats), sphere (4 floats),
        flag/vertex_count/index_count/other_count (4 int32),
        [vertex_count position floats, x3],
        [vertex_count normal floats, x3],
        [vertex_count uv floats, x2],
        [index_count uint16 face indices],
        [other_count x 16 bytes, unidentified],
        node_id (parent index, int32), flags_bitmask (int32),
        d_count (int32) + d_count x 12 bytes + d_count x 16 bytes,
        then up to six further optional blocks gated by flags_bitmask
        bits (skipped here by their known exact sizes).
"""
import struct


class Ms2Node:
    def __init__(self):
        self.name = ""
        self.parent_index = -1
        self.bbox_min = (0.0, 0.0, 0.0)
        self.bbox_max = (0.0, 0.0, 0.0)
        self.positions = []   # list of (x,y,z)
        self.normals = []     # list of (x,y,z)
        self.uvs = []         # list of (u,v)
        self.indices = []     # flat list of vertex indices, 3 per triangle
        self.is_empty = False


def _read_cstring(data, offset):
    namelen = struct.unpack_from('<i', data, offset)[0]
    name = data[offset + 4:offset + 4 + namelen].decode('ascii', errors='replace')
    end = offset + 4 + namelen + 1
    return name, end


def _looks_like_valid_next(data, offset):
    """Heuristic used only to disambiguate the old-vs-new exporter
    behaviour for the 0x40 (shadow volume) block - see below. Checks
    whether `offset` is exactly EOF, or the start of a plausible
    length-prefixed name string."""
    if offset == len(data):
        return True
    if offset < 0 or offset + 4 > len(data):
        return False
    namelen = struct.unpack_from('<i', data, offset)[0]
    if not (0 < namelen <= 64) or offset + 4 + namelen + 1 > len(data):
        return False
    candidate = data[offset + 4:offset + 4 + namelen]
    return all(32 <= b < 127 for b in candidate) and data[offset + 4 + namelen] == 0


def _skip_remaining_after_0x40_safe(data, offset, vertex_count, flags_bitmask):
    """Like _skip_remaining_after_0x40, but treats any out-of-range read
    (from following a wrong speculative hypothesis into garbage data) as
    simply invalid rather than crashing."""
    try:
        end = _skip_remaining_after_0x40(data, offset, vertex_count, flags_bitmask)
    except struct.error:
        return None
    if end < 0 or end > len(data):
        return None
    return end


def _skip_remaining_after_0x40(data, offset, vertex_count, flags_bitmask):
    """Continue past the blocks that come after 0x40 in check order
    (0x200, 0x400, 0x10000, 0x4000, 0x40000), given a starting offset."""
    if flags_bitmask & 0x200:
        f_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + f_count * 112
    if flags_bitmask & 0x400:
        g_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + g_count * 92
    if flags_bitmask & 0x10000:
        h_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + h_count * 80
    if flags_bitmask & 0x4000:
        offset += 4
    if flags_bitmask & 0x40000:
        offset += vertex_count * 12 * 2
    return offset


def _skip_optional_blocks(data, offset, vertex_count, flags_bitmask):
    """Skip the six flags_bitmask-gated optional blocks by their known
    exact byte sizes. Content is not read (unmapped in most cases)."""
    if flags_bitmask & 0x800:
        offset += vertex_count * 8
    if flags_bitmask & 0x10:
        offset += vertex_count * 20
    if flags_bitmask & 0x40:
        # Two exporter behaviours confirmed to exist for this block: files
        # older than MayaExp.mll's own June 2007 build date only write the
        # count + count*52-byte array; newer files also write a further
        # count*2 x 4-byte array. A file's true "version" isn't a property
        # we can read directly, so disambiguate structurally: compute the
        # full remainder of this node BOTH ways (continuing through any
        # later optional blocks in each case) and pick whichever ends at
        # something that looks like a valid next node name, or exact EOF.
        e_count = struct.unpack_from('<i', data, offset)[0]
        base = offset + 4 + e_count * 52
        new_style_base = base + e_count * 2 * 4

        old_end = _skip_remaining_after_0x40_safe(data, base, vertex_count, flags_bitmask)
        new_end = _skip_remaining_after_0x40_safe(data, new_style_base, vertex_count, flags_bitmask)

        old_valid = old_end is not None and _looks_like_valid_next(data, old_end)
        new_valid = new_end is not None and _looks_like_valid_next(data, new_end)
        if new_valid and not old_valid:
            return new_end
        elif old_valid and not new_valid:
            return old_end
        elif new_valid and old_valid:
            # Both look plausible - prefer the newer layout, since it's
            # what the decompiled June 2007 exporter binary actually does.
            return new_end
        else:
            # Neither validates - fall back to the newer layout as the
            # best-documented behaviour; a downstream parse error will at
            # least surface clearly rather than silently picking wrong.
            return new_end if new_end is not None else new_style_base
    if flags_bitmask & 0x200:
        f_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + f_count * 112
    if flags_bitmask & 0x400:
        g_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + g_count * 92
    if flags_bitmask & 0x10000:
        h_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + h_count * 80
    if flags_bitmask & 0x4000:
        offset += 4
    if flags_bitmask & 0x40000:
        offset += vertex_count * 12 * 2
    return offset


def _read_node(data, offset):
    node = Ms2Node()
    node.name, offset = _read_cstring(data, offset)

    node.bbox_min = struct.unpack_from('<3f', data, offset)
    node.bbox_max = struct.unpack_from('<3f', data, offset + 12)
    sphere = struct.unpack_from('<4f', data, offset + 24)
    flag, vcount, icount, other_count = struct.unpack_from('<4i', data, offset + 40)
    offset += 56

    node.is_empty = node.bbox_min[0] > 1e37

    if vcount > 0:
        pos_floats = struct.unpack_from('<%df' % (vcount * 3), data, offset)
        node.positions = [pos_floats[i:i + 3] for i in range(0, len(pos_floats), 3)]
        offset += vcount * 3 * 4

        norm_floats = struct.unpack_from('<%df' % (vcount * 3), data, offset)
        node.normals = [norm_floats[i:i + 3] for i in range(0, len(norm_floats), 3)]
        offset += vcount * 3 * 4

        uv_floats = struct.unpack_from('<%df' % (vcount * 2), data, offset)
        node.uvs = [uv_floats[i:i + 2] for i in range(0, len(uv_floats), 2)]
        offset += vcount * 2 * 4

    if icount > 0:
        node.indices = list(struct.unpack_from('<%dH' % icount, data, offset))
        offset += icount * 2

    offset += other_count * 16

    node_id, flags_bitmask = struct.unpack_from('<2i', data, offset)
    node.parent_index = node_id
    offset += 8

    d_count = struct.unpack_from('<i', data, offset)[0]
    offset += 4
    offset += d_count * 12 + d_count * 16

    offset = _skip_optional_blocks(data, offset, vcount, flags_bitmask)

    return node, offset


def read_ms2(path):
    """Returns a list of Ms2Node, in file order (index 0 is always the
    root). node.parent_index is the index of the parent within this
    same list, or -1 for the root."""
    with open(path, 'rb') as f:
        data = f.read()

    version, node_count = struct.unpack_from('<2i', data, 0)
    if version != 0:
        raise ValueError("Unexpected format_version %d (expected 0) - "
                          "this file may use a variant of the format "
                          "not covered by this reader" % version)

    nodes = []
    offset = 8
    for _ in range(node_count):
        node, offset = _read_node(data, offset)
        nodes.append(node)

    return nodes


if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        nodes = read_ms2(path)
        print("%s: %d nodes" % (path, len(nodes)))
        for i, n in enumerate(nodes):
            kind = "empty" if n.is_empty else ("%d verts, %d tris" % (
                len(n.positions), len(n.indices) // 3))
            print("  [%d] %r parent=%d (%s)" % (i, n.name, n.parent_index, kind))
