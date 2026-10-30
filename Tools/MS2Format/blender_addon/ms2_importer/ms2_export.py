"""ms2_export.py - write edited geometry back into a .ms2 the engine accepts.

[2026-10-30] v1 of the export path. Vertex and index COUNTS never change, which is
what makes this tractable: positions, normals and UVs are equal-length
substitutions, so every block whose meaning is not fully mapped (shadow volumes,
bind poses, the joint table) is copied through byte-for-byte rather than rebuilt.

WHAT IS WRITTEN
    positions   from the Blender mesh, in vertex order
    normals     from the ms2_normals POINT attribute the importer stashed
    uvs         from the mesh UV layer, V negated back to the file convention
    indices     LEFT AS THE SOURCE FILE HAD THEM - topology is out of v1 scope
    bbox        recomputed from the positions (float32 x6)
    sphere      recomputed from the positions (centre xyz + radius)
    everything else   untouched

WHY THE BBOX MATTERS: it is derived data living in the node header. The old writer
only ever put geometry back unchanged, so it never had to touch it. A hull scaled 3x
with a stale bounding box may still draw in the Asset View and be culled wrongly in
a mission.

The writer refuses to produce anything it cannot stand behind: the byte length must
not change, and the result must re-parse to the same node count.
"""
import struct

from . import ms2_reader as R
from . import ms2_writer as W


def _uv_per_vertex(mesh):
    """ms2 uvs are per-vertex; Blender holds them per-loop. First loop wins."""
    layer = mesh.uv_layers.active
    if layer is None:
        return None
    out = [None] * len(mesh.vertices)
    for i, loop in enumerate(mesh.loops):
        vi = loop.vertex_index
        if out[vi] is None:
            uv = layer.data[i].uv
            out[vi] = (uv[0], -uv[1])
    return out


def _bounds(positions):
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    c = tuple((lo[i] + hi[i]) / 2.0 for i in range(3))
    r = max(((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) ** 0.5
            for p in positions)
    return lo, hi, c, r


def _find_object(by_index, node):
    obj = by_index.get(node.name)
    if obj is not None:
        return obj
    for o in by_index.values():
        if o.name == node.name:
            return o
    return None


def export_ms2(src, dst, objects=None, log=print):
    """Write src to dst with geometry replaced from the given Blender objects.
    Returns (nodes_written, nodes_skipped)."""
    original = open(src, "rb").read()
    data = bytearray(original)
    nodes = R.read_ms2(src)
    _d, _n, spans = W._spans(src)

    by_index = {}
    for obj in (objects if objects is not None else []):
        idx = obj.get("ms2_node_index")
        if idx is not None:
            by_index[int(idx)] = obj
    if not by_index:
        import bpy
        for obj in bpy.context.scene.objects:
            idx = obj.get("ms2_node_index")
            if idx is not None:
                by_index[int(idx)] = obj

    written = 0
    skipped = 0
    kept_derived = 0
    derived = []
    for s in spans:
        node = s["node"]
        vcount = s["vcount"]
        if vcount == 0:
            continue
        obj = _find_object(by_index, node)
        if obj is None or obj.type != "MESH":
            skipped += 1
            continue
        mesh = obj.data
        if len(mesh.vertices) != vcount:
            log("  %s: vertex count differs in Blender (%d vs %d); v1 cannot add or remove geometry, so this node keeps its source geometry" % (node.name, len(mesh.vertices), vcount))
            skipped += 1
            continue

        positions = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]

        attr = mesh.attributes.get("ms2_normals") if hasattr(mesh, "attributes") else None
        if attr is None:
            log("  %s: no ms2_normals attribute, keeping the normals already in the file" % node.name)
            normals = None
        else:
            normals = [tuple(attr.data[i].vector) for i in range(vcount)]

        uvs = _uv_per_vertex(mesh)
        if uvs is None or any(u is None for u in uvs):
            log("  %s: no usable UV layer, keeping the UVs already in the file" % node.name)
            uvs = None

        start = s["start"]
        buf = bytearray()
        for p in positions:
            buf += struct.pack("<3f", *p)
        if normals is not None:
            for n in normals:
                buf += struct.pack("<3f", *n)
        else:
            buf += original[start + vcount * 12:start + vcount * 24]
        if uvs is not None:
            for uv in uvs:
                buf += struct.pack("<2f", *uv)
        else:
            buf += original[start + vcount * 24:start + vcount * 32]
        if len(buf) != vcount * 32:
            raise ValueError("geometry block for %s is %d bytes, expected %d"
                             % (node.name, len(buf), vcount * 32))
        data[start:start + len(buf)] = buf

        # Derived header fields: bbox min at geo_start-56, max at -44, sphere at -32.
        #
        # [2026-10-30] RECOMPUTED ONLY WHEN THE POSITIONS ACTUALLY MOVED. Measured
        # on 4MeterBox: recomputing unconditionally produced a sphere radius one
        # ULP away from G5's own value (0x3d vs 0x37 in the low byte of the last
        # float, 0.8660254 both ways), because they and we compute the same number
        # by different arithmetic. A derived field that has not changed does not
        # need to be republished, and leaving it alone is what lets the
        # unmodified-export gate be exact rather than approximate.
        unchanged = (len(node.positions) == vcount and
                     all(abs(node.positions[i][j] - positions[i][j]) < 1e-9
                         for i in range(vcount) for j in range(3)))
        if unchanged:
            kept_derived += 1
        else:
            lo, hi, c, r = _bounds(positions)
            struct.pack_into("<3f", data, start - 56, *lo)
            struct.pack_into("<3f", data, start - 44, *hi)
            struct.pack_into("<4f", data, start - 32, c[0], c[1], c[2], r)
            derived.append((node.name, node.bbox_min, lo, node.bbox_max, hi, r))
        written += 1

    if len(data) != len(original):
        raise ValueError("refusing to write: byte length changed")
    open(dst, "wb").write(bytes(data))
    after = R.read_ms2(dst)
    if len(after) != len(nodes):
        raise ValueError("refusing: output parses to %d nodes, source had %d"
                         % (len(after), len(nodes)))
    if derived:
        log("  bbox/sphere recomputed for %d node(s), left alone for %d"
            % (len(derived), kept_derived))
        for name, lo0, lo1, hi0, hi1, r in derived[:5]:
            log("    %-20s bbox %.3f %.3f %.3f .. %.3f %.3f %.3f  ->  %.3f %.3f %.3f .. %.3f %.3f %.3f"
                % ((name,) + tuple(lo0) + tuple(hi0) + tuple(lo1) + tuple(hi1)))
    return written, skipped
