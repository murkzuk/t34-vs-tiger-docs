"""
.ms2 static-mesh reader (GitHub issue #12, Phase 3 - importer).

This is a synced copy of Tools\\MS2Format\\ms2_reader.py, duplicated here
so the Blender add-on folder is self-contained and installable on its
own (Blender add-ons can't reliably reach outside their own folder).
Keep this in sync with the original if it changes.

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
        self.weights = []      # per-vertex (w0,w1,w2,w3)
        self.joint_idx = []    # per-vertex (j0,j1,j2,j3) node indices
        # [2026-08-26] Rest-pose transform, decoded from frame 0 of the node's
        # animation track. Without this every object imports at the origin:
        # static parts are baked in world space so a hull still looks right,
        # but anything animated (turret, gun, road wheels) is authored around
        # its own pivot and collapses into a heap.
        self.rest_pos = (0.0, 0.0, 0.0)
        self.rest_quat = (1.0, 0.0, 0.0, 0.0)   # (w, x, y, z)
        self.has_rest = False
        # [2026-08-26] Material index into the companion .script's ModelSkin
        # Materials array. Packed with the index count in one int32:
        #     (icount << 16) | material_index
        # Verified against every textured part of the King Tiger - road wheels
        # 12, track left 24, track right 25, turret 19, hull 5, kill rings 20,
        # numbers 21, flag 22, commander's uniform 0.
        self.material_index = -1
        # [2026-08-27] A node can hold SEVERAL submeshes, one per material.
        # See _read_node for the record layout. Each entry is a dict:
        #   index_start, index_count, vertex_start, vertex_count, material_index
        # Empty when the node has no geometry.
        self.submeshes = []
        self.binds = []        # (index, 4x4 matrix, vec3) per record

    def absolute_indices(self):
        """`indices` holds the RAW file values, which are relative to each
        submesh's own vertex_start. This returns them rebased into the
        node's single shared vertex array, which is what a mesh needs.

        Kept separate rather than fixed in place because ms2_writer packs
        node.indices straight back out and asserts the result is
        byte-identical to the source - rebasing in place would break
        export on every multi-submesh node.
        """
        out = list(self.indices)
        for s in self.submeshes:
            base = s["vertex_start"]
            if not base:
                continue
            end = min(s["index_start"] + s["index_count"], len(out))
            for i in range(s["index_start"], end):
                out[i] += base
        return out

    def submesh_of_triangle(self, tri):
        """Which submesh (list position) triangle `tri` belongs to, or 0."""
        first = tri * 3
        for k, s in enumerate(self.submeshes):
            if s["index_start"] <= first < s["index_start"] + s["index_count"]:
                return k
        return 0


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


_LAST_BIND = [None]   # bind block (offset, count) seen by the most recent call


def _skip_remaining_after_0x40(data, offset, vertex_count, flags_bitmask):
    """Continue past the blocks that come after 0x40 in check order
    (0x200, 0x400, 0x10000, 0x4000, 0x40000), given a starting offset.

    NOTE: this is called speculatively (twice) by _skip_optional_blocks to
    disambiguate the old/new exporter layouts, so _LAST_BIND is only
    meaningful for the branch that actually gets committed - see the
    callers, which re-run the winning branch before reading it."""
    _LAST_BIND[0] = None
    if flags_bitmask & 0x200:
        f_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + f_count * 112
    if flags_bitmask & 0x400:
        g_count = struct.unpack_from('<i', data, offset)[0]
        offset += 4 + g_count * 92
    if flags_bitmask & 0x10000:
        h_count = struct.unpack_from('<i', data, offset)[0]
        _LAST_BIND[0] = (offset + 4, h_count)
        offset += 4 + h_count * 80
    if flags_bitmask & 0x4000:
        offset += 4
    if flags_bitmask & 0x40000:
        offset += vertex_count * 12 * 2
    return offset


_LAST_SKIN = [None]


def _skip_optional_blocks(data, offset, vertex_count, flags_bitmask):
    """Skip the six flags_bitmask-gated optional blocks by their known
    exact byte sizes. Content is not read (unmapped in most cases)."""
    if flags_bitmask & 0x800:
        offset += vertex_count * 8
    if flags_bitmask & 0x10:
        _LAST_SKIN[0] = offset
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
            _skip_remaining_after_0x40_safe(data, new_style_base, vertex_count, flags_bitmask)
            return new_end
        elif old_valid and not new_valid:
            _skip_remaining_after_0x40_safe(data, base, vertex_count, flags_bitmask)
            return old_end
        elif new_valid and old_valid:
            # Both look plausible - prefer the newer layout, since it's
            # what the decompiled June 2007 exporter binary actually does.
            _skip_remaining_after_0x40_safe(data, new_style_base, vertex_count, flags_bitmask)
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

    # [2026-08-27] The 16-byte record is a SUBMESH DESCRIPTOR, four uint32:
    #
    #     (index_count << 16) | material_index,   index_start,
    #     vertex_count,                           vertex_start
    #
    # other_count is the number of submeshes, one per material used by the
    # node. Indices are stored RELATIVE TO vertex_start, so a second submesh
    # must be rebased - see Ms2Node.absolute_indices.
    #
    # The earlier note here read the record as "(packed, 0, vcount, 0)". That
    # is what it degenerates to when other_count == 1, which is 14,817 of the
    # 15,341 nodes across both builds - so single-submesh testing could never
    # have caught it. The remaining 524 nodes, in 87 of 249 models (both
    # T-34s, both Tigers, the StuG, SU-85, Panzer IV, the aircraft, bridges),
    # imported as a fan of splinters because the second submesh's triangles
    # were pointed at the first submesh's vertices.
    #
    # Verified on 518 of those 524: index_start values are contiguous from 0,
    # index counts sum to exactly icount, vertex counts to exactly vcount.
    if other_count > 0 and vcount > 0:
        subs = []
        for k in range(other_count):
            packed, istart, vcount_s, vstart = struct.unpack_from(
                '<4I', data, offset + k * 16)
            subs.append({"index_start": istart,
                         "index_count": (packed >> 16) & 0xFFFF,
                         "vertex_start": vstart,
                         "vertex_count": vcount_s,
                         "material_index": packed & 0xFFFF})
        # Only trust the descriptor when it accounts for the node exactly.
        # Two skinned nodes in the library (hum_SSTankman 'lo_Hips',
        # KingTiger 'Body_commander') carry garbage in the vertex fields;
        # falling back leaves them exactly as they imported before.
        consistent = (sum(s["index_count"] for s in subs) == icount and
                      sum(s["vertex_count"] for s in subs) == vcount and
                      all(s["vertex_start"] + s["vertex_count"] <= vcount
                          for s in subs))
        node.submeshes = subs if consistent else []
        node.material_index = subs[0]["material_index"]
    offset += other_count * 16

    node_id, flags_bitmask = struct.unpack_from('<2i', data, offset)
    node.parent_index = node_id
    offset += 8

    # [2026-08-27] Masked to 16 bits. One file in the library, ZeeWolf's
    # replacement Panzer IV (u_veh_PnzIV_G_AI_.ms2), has 0x48 sitting in the
    # top byte of this field on node 179 of 185 - d_count reads as
    # 1,207,959,794 instead of 242 and the parse dies six nodes from the end.
    # The engine loads that file perfectly well in-game, so it is not reading
    # the high half either. With the mask the file walks to exactly its own
    # length, 11,904,835 bytes, and ends on the usual HullDriver/HullGunlayer/
    # HullEngine tail. Every other file in both builds is unaffected: the top
    # 16 bits are zero in all 15,340 other nodes.
    d_count = struct.unpack_from('<i', data, offset)[0] & 0xFFFF
    offset += 4
    # [2026-08-26] THIS IS THE NODE TRANSFORM, and it used to be skipped.
    # Every node carries a fixed-length animation track: d_count positions
    # (vec3) followed by d_count rotations (quaternion, w first). 161 frames
    # in every vehicle seen so far - 161*28+4 = 4512 bytes, which is exactly
    # the 'fallback block' size earlier notes recorded without identifying.
    #
    # Frame 0 is the rest pose (measured: 199 of the King Tiger's 220 nodes
    # sit at identity rotation on frame 0, more than any other frame).
    #
    # The tracks read as you would expect of a tank: road wheels hold position
    # while their quaternion spins, Weapon_A slides 0.3 m back along its axis
    # under recoil, and Turret_A is stationary with a 0.7071 quaternion at 90
    # degrees of traverse.
    if d_count > 0:
        node.rest_pos = struct.unpack_from('<3f', data, offset)
        node.rest_quat = struct.unpack_from('<4f', data, offset + d_count * 12)
        node.has_rest = True
    offset += d_count * 12 + d_count * 16

    _LAST_SKIN[0] = None
    _LAST_BIND[0] = None
    offset = _skip_optional_blocks(data, offset, vcount, flags_bitmask)

    # [2026-08-18] The 20-byte per-vertex skin record is four float32
    # weights followed by four *byte* joint indices packed into what looks
    # like an int32 - NOT a single int32 index, as an earlier pass recorded.
    # Reading it as one int32 returns the first joint, which is correct for
    # the common single-influence case and is why the error went unnoticed.
    if _LAST_SKIN[0] is not None:
        so = _LAST_SKIN[0]
        for v in range(vcount):
            node.weights.append(struct.unpack_from('<4f', data, so + v * 20))
            node.joint_idx.append(struct.unpack_from('<4B', data, so + v * 20 + 16))
    if _LAST_BIND[0] is not None:
        bo, h = _LAST_BIND[0]
        for j in range(h):
            node.binds.append((struct.unpack_from('<i', data, bo + j * 80)[0],
                               struct.unpack_from('<16f', data, bo + j * 80 + 4),
                               struct.unpack_from('<3f', data, bo + j * 80 + 68)))

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
