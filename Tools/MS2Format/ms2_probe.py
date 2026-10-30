"""
*** SUPERSEDED 2026-08-26 - DO NOT USE FOR ANALYSIS ***

Kept only as the record of how the .ms2 format was first worked out. Use
`blender_addon/ms2_importer/ms2_reader.py`, which parses real vehicles
correctly and decodes everything this file could not.

THIS FILE PRODUCES CONFIDENT WRONG ANSWERS. Specifically:

  * It DESYNCS at the first geometry node of any real vehicle. On the King
    Tiger it reads 11 of 220 nodes and then throws.
  * Its "other_count" is WRONG. It reports 4; the true value is 1. That
    single bad number was carried into the format notes and sent a later
    session hunting for a transform matrix in the wrong 64 bytes.

The three things it never found, all decoded 2026-08-26:

  UVs         DirectX convention - V runs 0..-1 and must be negated
  transforms  frame 0 of each node's 161-frame animation track
  materials   low 16 bits of the 16-byte "other" record

See Documentation/MS2_Node_Transforms_SOLVED.md.
"""
"""
Empirical .ms2 structure probe (GitHub issue #12, Phase 1).

Not a full parser - a research tool implementing the format understanding
documented in Documentation/MS2_Binary_Format_Findings_2026-07-03.md.
Every field interpretation here is a working hypothesis validated against
known geometry (the tutorial's own exported cube) and cross-checked with
an independent detection method (magnitude scanning), not a certainty.

Confirmed per-node layout, after the node's name + null terminator:
    bbox_min (3 floats), bbox_max (3 floats)      24 bytes
    sphere_center (3 floats), sphere_radius       16 bytes
    flag (int32)             - always 0 in samples seen so far
    vertex_count (int32)
    index_count (int32)      - number of uint16 face-index values, i.e. 3x triangle count
    other_count (int32)      - 1 when the node has geometry, 0 for an empty container node
    [only present when the file has more than one node:]
    parent_idx (int32)       - index of parent node, -1 if none
    child_count (int32)
    [if vertex_count > 0:]
        positions:  vertex_count x 3 floats
        normals:    vertex_count x 3 floats
        uvs:        vertex_count x 2 floats
        indices:    index_count x uint16
    [if vertex_count == 0:]
        unknown fallback block, size not yet determined - this tool
        locates the next node by scanning for its name string instead.
"""
import struct
import sys


def read_cstring(data, offset):
    namelen = struct.unpack_from('<i', data, offset)[0]
    name = data[offset + 4:offset + 4 + namelen].decode('ascii', errors='replace')
    end = offset + 4 + namelen + 1  # +1 for the null terminator byte
    return name, end


def find_next_name(data, start, minlen=2, maxlen=64):
    """Scan forward for the next plausible length-prefixed ASCII name,
    used to locate a following node when this one has no geometry (so
    we can't compute its size directly)."""
    n = len(data)
    i = start
    while i <= n - 8:
        namelen = struct.unpack_from('<i', data, i)[0]
        if minlen <= namelen <= maxlen and i + 4 + namelen + 1 <= n:
            candidate = data[i + 4:i + 4 + namelen]
            if all(32 <= b < 127 for b in candidate) and data[i + 4 + namelen] == 0:
                return i
        i += 1
    return None


def probe_node(data, offset, has_siblings, depth=1):
    name, after_name = read_cstring(data, offset)
    bbox_min = struct.unpack_from('<3f', data, after_name)
    bbox_max = struct.unpack_from('<3f', data, after_name + 12)
    sphere = struct.unpack_from('<4f', data, after_name + 24)
    flag, vcount, icount, other = struct.unpack_from('<4i', data, after_name + 40)

    header_end = after_name + 56
    parent_idx = child_count = None
    if has_siblings:
        parent_idx, child_count = struct.unpack_from('<2i', data, header_end)
        header_end += 8

    indent = '  ' * depth
    is_empty = bbox_min[0] > 1e37
    safe_name = name.encode('ascii', errors='replace').decode('ascii')
    print(f"{indent}{safe_name!r}: vcount={vcount} icount={icount} other={other} "
          f"empty={is_empty} parent={parent_idx} children={child_count}")

    if vcount == 0:
        next_name_at = find_next_name(data, header_end)
        if next_name_at is not None:
            print(f"{indent}  (no geometry - fallback block is "
                  f"{next_name_at - header_end} bytes, next node at {next_name_at})")
            return next_name_at
        print(f"{indent}  (no geometry, and no further node found - end of file?)")
        return None

    pos_start = header_end
    normals_start = pos_start + vcount * 3 * 4
    uv_start = normals_start + vcount * 3 * 4
    idx_start = uv_start + vcount * 2 * 4
    idx_end = idx_start + icount * 2

    print(f"{indent}  positions@{pos_start} normals@{normals_start} "
          f"uvs@{uv_start} indices@{idx_start}-{idx_end}  "
          f"(bbox {tuple(round(v, 3) for v in bbox_min)} .. "
          f"{tuple(round(v, 3) for v in bbox_max)})")

    if idx_end > len(data):
        print(f"{indent}  ** WARNING: computed end ({idx_end}) exceeds file size ({len(data)}) **")

    # sanity check: face indices should reference valid vertices
    if idx_end <= len(data):
        idxs = struct.unpack_from(f'<{icount}H', data, idx_start)
        bad = [x for x in idxs if x >= vcount]
        if bad:
            print(f"{indent}  ** WARNING: {len(bad)}/{len(idxs)} face indices "
                  f"reference out-of-range vertices (max seen {max(idxs)}, vcount={vcount}) **")

    return idx_end


def probe_file(path):
    data = open(path, 'rb').read()
    print(f"=== {path} ({len(data)} bytes) ===")
    a, b, namelen = struct.unpack_from('<iii', data, 0)
    print(f"format_version={a} node_count={b}")

    offset = 8
    has_siblings = b > 1
    for _ in range(b):
        result = probe_node(data, offset, has_siblings)
        if result is None:
            break
        offset = result
    print()


if __name__ == '__main__':
    for f in sys.argv[1:]:
        probe_file(f)
