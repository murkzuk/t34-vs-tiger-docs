"""
.ms2 binary format parser, derived from decompiling MayaExp.mll's actual
writer function (GitHub issue #12, Phase 2 - ground truth via Ghidra
decompilation, not empirical guessing).

Decompiled functions (addresses in MayaExp.mll):
    0x100891f0  CExportG5ResourceCmd model-export path - writes the
                per-mesh Content.script and calls the two functions below
    0x1008e850  writes the file header, then loops over every joint/node
                calling the per-node writer below
    0x1008dde0  the actual per-node binary writer - this function is the
                source of every field/offset documented here

Per-node write order (this is the literal fwrite() call sequence from
0x1008dde0, not a memory layout - some fields are written out of their
struct-offset order):

    namelen (int32), name bytes + 1 null byte (not counted in namelen)
    bbox_min, bbox_max      (6 floats, 24 bytes)
    sphere_center, radius   (4 floats, 16 bytes)
    flag                    (int32, always 0 in every sample seen)
    vertex_count            (int32)             -- struct offset 0x38
    index_count             (int32)              -- struct offset 0x58
    other_count             (int32)              -- struct offset 0x60
    positions:  vertex_count x 3 floats
    normals:    vertex_count x 3 floats
    uvs:        vertex_count x 2 floats
    indices:    index_count x uint16
    other:      other_count x 16 bytes           -- NOT identified yet;
                always 1 record (16 bytes) in every sample with real
                geometry, 0 records for empty container nodes. This is
                the block earlier empirical (Phase 1) probing completely
                missed, and is very likely what caused the "unexplained
                leftover bytes" and "off-by-one index" mysteries in that
                earlier pass.
    node_id                 (int32)              -- struct offset 0x00.
                Defaults to a global constant (always 0 in samples) unless
                this node has an associated "parent object" set internally,
                in which case it copies a value from that parent - so this
                is plausibly a parent-node backreference, but the exact
                semantics are still not fully nailed down.
    flags_bitmask           (int32)              -- struct offset 0x08.
                Gates six further OPTIONAL blocks (see below). Always 0 in
                every sample with only base geometry (no skin/animation/
                collision data).
    d_count                 (int32)              -- struct offset 0x10.
                ALWAYS written and read (not gated by flags_bitmask). Two
                arrays follow, sized by this count:
    d_array_a:  d_count x 12 bytes                -- struct offset 0x14
    d_array_b:  d_count x 16 bytes                -- struct offset 0x18

    -- Everything from here on is OPTIONAL, gated by flags_bitmask bits.
    -- Field/bit meanings are not yet identified (no strings or other
    -- context found yet to name them) - offsets and sizes are exact
    -- (from the decompiled fwrite calls), semantics are not.

    if flags_bitmask & 0x800:  vertex_count x 8 bytes    (offset 0x48)
    if flags_bitmask & 0x10:   vertex_count x 20 bytes   (offset 0x4c)
    if flags_bitmask & 0x40:   e_count (int32, offset 0xa8),
                               e_count x 52 bytes (offset 0xac),
                               e_count*2 x 4 bytes (offset 0xb0)
    if flags_bitmask & 0x200:  f_count (int32, offset 0x1c),
                               f_count x 112 bytes (offset 0x20)
    if flags_bitmask & 0x400:  g_count (int32, offset 0x24),
                               g_count x 92 bytes (offset 0x28)
    if flags_bitmask & 0x10000: h_count (int32, offset 0x2c),
                               h_count x 80 bytes (offset 0x30)
    if flags_bitmask & 0x4000: single 4-byte value (offset 0x04)
    if flags_bitmask & 0x40000: vertex_count x 12 bytes (offset 0x50),
                               vertex_count x 12 bytes (offset 0x54)

The overall file is: int32 format_version (always 0), int32 node_count,
then node_count nodes back to back (each node is exactly the structure
above). This top-level part matches what empirical Phase 1 probing found
and is unchanged.

None of the sample files examined so far ever set flags_bitmask to
anything but 0, so the six optional blocks above are unverified against
real data - only their exact byte layout (from the decompiled fwrite
call arguments) is known, not their content or purpose.
"""
import struct
import sys


def read_cstring(data, offset):
    namelen = struct.unpack_from('<i', data, offset)[0]
    name = data[offset + 4:offset + 4 + namelen].decode('ascii', errors='replace')
    end = offset + 4 + namelen + 1  # +1 for the null terminator byte
    return name, end


def parse_node(data, offset, depth=1):
    name, off = read_cstring(data, offset)
    bbox_min = struct.unpack_from('<3f', data, off)
    bbox_max = struct.unpack_from('<3f', data, off + 12)
    sphere = struct.unpack_from('<4f', data, off + 24)
    flag, vcount, icount, other_count = struct.unpack_from('<4i', data, off + 40)
    off += 56

    indent = '  ' * depth
    is_empty = bbox_min[0] > 1e37
    print(f"{indent}{name!r}: vcount={vcount} icount={icount} "
          f"other_count={other_count} empty={is_empty}")

    if vcount > 0:
        off += vcount * 3 * 4  # positions
        off += vcount * 3 * 4  # normals
        off += vcount * 2 * 4  # uvs
    if icount > 0:
        off += icount * 2      # indices
    if other_count > 0:
        off += other_count * 16  # the previously-unidentified block

    node_id, flags_bitmask = struct.unpack_from('<2i', data, off)
    off += 8

    d_count = struct.unpack_from('<i', data, off)[0]
    off += 4
    off += d_count * 12  # d_array_a
    off += d_count * 16  # d_array_b

    print(f"{indent}  node_id={node_id} flags=0x{flags_bitmask:x} d_count={d_count} "
          f"bbox=({tuple(round(v,3) for v in bbox_min)}..{tuple(round(v,3) for v in bbox_max)})")

    if flags_bitmask != 0:
        print(f"{indent}  ** flags_bitmask is nonzero - optional blocks not yet "
              f"validated against real data, offset math below may be wrong **")

    if flags_bitmask & 0x800:
        off += vcount * 8
    if flags_bitmask & 0x10:
        off += vcount * 20
    if flags_bitmask & 0x40:
        e_count = struct.unpack_from('<i', data, off)[0]
        off += 4 + e_count * 52 + e_count * 2 * 4
    if flags_bitmask & 0x200:
        f_count = struct.unpack_from('<i', data, off)[0]
        off += 4 + f_count * 112
    if flags_bitmask & 0x400:
        g_count = struct.unpack_from('<i', data, off)[0]
        off += 4 + g_count * 92
    if flags_bitmask & 0x10000:
        h_count = struct.unpack_from('<i', data, off)[0]
        off += 4 + h_count * 80
    if flags_bitmask & 0x4000:
        off += 4
    if flags_bitmask & 0x40000:
        off += vcount * 12 * 2

    return off


def parse_file(path):
    data = open(path, 'rb').read()
    print(f"=== {path} ({len(data)} bytes) ===")
    version, node_count = struct.unpack_from('<2i', data, 0)
    print(f"format_version={version} node_count={node_count}")

    offset = 8
    for _ in range(node_count):
        offset = parse_node(data, offset)

    leftover = len(data) - offset
    print(f"parsed to offset {offset}, file size {len(data)}, leftover {leftover} bytes")
    if leftover != 0:
        print("  ** did not land exactly on EOF - something still unaccounted for **")
    print()


if __name__ == '__main__':
    for f in sys.argv[1:]:
        parse_file(f)
