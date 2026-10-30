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
import re
import struct

from . import ms2_reader as R
from . import ms2_layout as L


def _uv_per_vertex(mesh, fill=False):
    """ms2 uvs are per-vertex; Blender holds them per-loop. First loop wins.

    [2026-10-30] DO NOT DISCARD THE WHOLE NODE FOR ONE ORPHANED VERTEX. The importer
    creates every vertex in the file, including ones no surviving face references, so
    the per-vertex list can legitimately keep holes. The previous version made the
    caller throw the whole array away in that case, and the rebuild path then wrote
    UV (0,0) for every vertex in the node - which rendered a Tiger hull flat white
    while its turret was perfectly textured, because every triangle sampled one texel.
    Holes are now filled with a real UV taken from the same node.
    """
    layer = mesh.uv_layers.active
    if layer is None and len(mesh.uv_layers):
        layer = mesh.uv_layers[0]
    if layer is None:
        return None
    out = [None] * len(mesh.vertices)
    for i, loop in enumerate(mesh.loops):
        vi = loop.vertex_index
        if out[vi] is None:
            uv = layer.data[i].uv
            out[vi] = (uv[0], -uv[1])
    if not fill:
        return out                      # holes left in; the caller decides
    first = None
    for u in out:
        if u is not None:
            first = u
            break
    if first is None:
        return None
    return [u if u is not None else first for u in out]


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
    """Write src to dst with geometry taken from the given Blender objects.

    Per node, independently:
      counts unchanged -> PATCH the existing bytes in place, so every authored
                          normal, UV and unknown block survives exactly;
      counts changed   -> REBUILD the node from the mesh (see rebuild_node).

    Returns (patched, rebuilt, kept)."""
    original = open(src, "rb").read()
    nodes = R.read_ms2(src)
    layout = L.walk(original)
    if len(layout) != len(nodes):
        raise ValueError("layout walk found %d nodes, reader found %d"
                         % (len(layout), len(nodes)))

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

    out = bytearray(original[:8])
    patched = rebuilt = kept = 0
    for i, node_l in enumerate(layout):
        node = nodes[i]
        base = bytearray(original[node_l["start"]:node_l["end"]])
        obj = by_index.get(i)
        if obj is None or obj.type != "MESH" or node_l["vcount"] == 0:
            if node_l["vcount"]:
                kept += 1
            out += base
            continue

        mesh = obj.data
        mesh.calc_loop_triangles()
        nv, ni = len(mesh.vertices), len(mesh.loop_triangles) * 3
        spans = node_l["spans"]

        # Only a VERTEX count change needs a rebuild. An index mismatch alone means
        # Blender dropped degenerate triangles on import (Body_commander: 15 of them),
        # and the source's indices are still the right ones to keep.
        if nv != node_l["vcount"]:
            mat = node.submeshes[0]["material_index"] if node.submeshes else node.material_index
            out += rebuild_node(original, node_l, mesh, max(mat, 0), log=log)
            rebuilt += 1
            log("  %s: rebuilt %d->%d vertices, %d->%d indices"
                % (node.name, node_l["vcount"], nv, node_l["icount"], ni))
            continue

        # ---- patch path: equal length, so write straight into the node bytes
        rel = {}
        for label, (off, size) in spans.items():
            rel[label] = (off - node_l["start"], size)

        positions = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]
        for k, p in enumerate(positions):
            struct.pack_into("<3f", base, rel["positions"][0] + k * 12, *p)

        attr = mesh.attributes.get("ms2_normals") if hasattr(mesh, "attributes") else None
        if attr is not None and len(attr.data) == nv:
            for k in range(nv):
                struct.pack_into("<3f", base, rel["normals"][0] + k * 12, *attr.data[k].vector)
        elif node.normals:
            log("  %s: no usable ms2_normals, keeping the file normals" % node.name)

        uvs = _uv_per_vertex(mesh)
        if uvs is not None and not any(u is None for u in uvs):
            for k, uv in enumerate(uvs):
                struct.pack_into("<2f", base, rel["uvs"][0] + k * 8, *uv)

        moved = (len(node.positions) == nv and
                 any(abs(node.positions[k][j] - positions[k][j]) > 1e-9
                     for k in range(nv) for j in range(3)))
        if moved:
            lo, hi, c, r = _bounds(positions)
            struct.pack_into("<3f", base, rel["bbox min"][0], *lo)
            struct.pack_into("<3f", base, rel["bbox max"][0], *hi)
            struct.pack_into("<4f", base, rel["bounding sphere"][0], c[0], c[1], c[2], r)
            log("  %s: geometry moved, bbox and sphere recomputed" % node.name)
        out += base
        patched += 1

    # ---- brand-new nodes: objects carrying "ms2_new_node" = the donor/parent index
    allobjs = list(objects) if objects is not None else list(by_index.values())
    extras = [o for o in allobjs if o.get("ms2_new_node") is not None and o.type == "MESH"]
    for obj in extras:
        donor_idx = int(obj["ms2_new_node"])
        donor = layout[donor_idx]
        dnode = nodes[donor_idx]
        mat = dnode.submeshes[0]["material_index"] if dnode.submeshes else dnode.material_index
        out += rebuild_node(original, donor, obj.data, max(mat, 0), log=log,
                            name=obj.name, parent=donor_idx)
        rebuilt += 1
        log("  %s: NEW node, parent %d, %d vertices"
            % (obj.name, donor_idx, len(obj.data.vertices)))
    if extras:
        struct.pack_into("<i", out, 4, len(layout) + len(extras))

    open(dst, "wb").write(bytes(out))

    # verify before returning: the result must re-parse and walk to its own end
    # [2026-10-30] count the APPENDED nodes too. Comparing against the source count
    # alone made the new-node path raise on its own success - it wrote a correct file
    # and then refused to trust it - so adding a part could never have worked here.
    expected = len(nodes) + len(extras)
    after = R.read_ms2(dst)
    if len(after) != expected:
        raise ValueError("output parses to %d nodes, expected %d (source %d + %d new)"
                         % (len(after), expected, len(nodes), len(extras)))
    chk = L.walk(bytes(out))
    if chk[-1]["end"] != len(out):
        raise ValueError("output walks to 0x%X but is 0x%X bytes - refusing to trust it"
                         % (chk[-1]["end"], len(out)))
    log("  %d patched, %d rebuilt, %d left as they were; %d -> %d bytes"
        % (patched, rebuilt, kept, len(original), len(out)))
    return patched, rebuilt, kept

def _mesh_arrays(mesh):
    """positions, normals, uvs and triangle indices, per vertex.

    [2026-10-30] NORMALS COME FROM THE AUTHORED ATTRIBUTE WHERE IT STILL APPLIES.
    A rebuilt node keeps its old vertices in their original order, so the ms2_normals
    attribute the importer stashed is still valid for indices below the old count -
    only the vertices the edit added have no authored normal. Using Blender normals
    for everything replaced 26,958 of 59,112 authored normal components on one Tiger
    hull, i.e. it silently re-shaded the whole tank to add a pyramid.
    """
    mesh.calc_loop_triangles()
    positions = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]
    normals = [(v.normal.x, v.normal.y, v.normal.z) for v in mesh.vertices]
    attr = mesh.attributes.get("ms2_normals") if hasattr(mesh, "attributes") else None
    if attr is not None:
        kept = 0
        for i in range(min(len(attr.data), len(normals))):
            n = attr.data[i].vector
            if abs(n[0]) + abs(n[1]) + abs(n[2]) > 1e-6:
                normals[i] = (n[0], n[1], n[2])
                kept += 1
        if kept:
            print("  %s: kept %d authored normals, %d vertices computed"
                  % (mesh.name, kept, len(normals) - kept))
    uvs = _uv_per_vertex(mesh, fill=True)
    if uvs is None:
        uvs = [(0.0, 0.0)] * len(mesh.vertices)
    idx = []
    for tri in mesh.loop_triangles:
        idx.extend(tri.vertices)
    return positions, normals, uvs, idx


def _unit(a):
    m = (a[0] ** 2 + a[1] ** 2 + a[2] ** 2) ** 0.5
    if m < 1e-12:
        return (1.0, 0.0, 0.0)
    return (a[0] / m, a[1] / m, a[2] / m)


def tangent_basis(positions, uvs, idx, normals):
    """dP/du then dP/dv per vertex, orthonormalised against the normal - what the
    0x40000 block turned out to hold. See
    notes/project_tvt_ms2_0x40000_is_tangent_space.md."""
    n = len(positions)
    tan = [[0.0, 0.0, 0.0] for _ in range(n)]
    bit = [[0.0, 0.0, 0.0] for _ in range(n)]
    for t in range(0, len(idx) - 2, 3):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        if max(i0, i1, i2) >= n:
            continue
        p0, p1, p2 = positions[i0], positions[i1], positions[i2]
        e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        d1 = (uvs[i1][0] - uvs[i0][0], uvs[i1][1] - uvs[i0][1])
        d2 = (uvs[i2][0] - uvs[i0][0], uvs[i2][1] - uvs[i0][1])
        det = d1[0] * d2[1] - d2[0] * d1[1]
        if abs(det) < 1e-12:
            continue
        r = 1.0 / det
        T = ((e1[0] * d2[1] - e2[0] * d1[1]) * r, (e1[1] * d2[1] - e2[1] * d1[1]) * r,
             (e1[2] * d2[1] - e2[2] * d1[1]) * r)
        B = ((e2[0] * d1[0] - e1[0] * d2[0]) * r, (e2[1] * d1[0] - e1[1] * d2[0]) * r,
             (e2[2] * d1[0] - e1[2] * d2[0]) * r)
        for v in (i0, i1, i2):
            for k in range(3):
                tan[v][k] += T[k]
                bit[v][k] += B[k]
    out = []
    for i in range(n):
        nn = _unit(normals[i])
        t = _unit(tan[i])
        d = t[0] * nn[0] + t[1] * nn[1] + t[2] * nn[2]
        out.append(_unit((t[0] - nn[0] * d, t[1] - nn[1] * d, t[2] - nn[2] * d)))
    for i in range(n):
        nn = _unit(normals[i])
        b = _unit(bit[i])
        d = b[0] * nn[0] + b[1] * nn[1] + b[2] * nn[2]
        out.append(_unit((b[0] - nn[0] * d, b[1] - nn[1] * d, b[2] - nn[2] * d)))
    return out


_LOD_SUFFIX = re.compile(r"_LOD(\d+)$")


def lod_level(name):
    """The LOD level encoded by a node name, 0 for everything that is not an LOD.

    [2026-10-30] THE FIRST OF THE FOUR INT32s AFTER THE BOUNDING SPHERE IS THE LOD
    LEVEL, NOT A FLAG. Measured across G5's and ZeeWolf's whole libraries: on the
    file whose ladder the editor's LOD slider demonstrably switches, every LOD node
    carries field == its _LOD<n> suffix (_LOD0 -> 0), and 96% of all other nodes
    carry 0. Writing 0 for an added LOD declares it as level 0 - the base level -
    so the engine sees one level and never selects it. That is exactly why four
    appended hull LODs did nothing in the Asset View while G5's stock Tiger
    coarsened under the same slider.
    """
    m = _LOD_SUFFIX.search(name or "")
    return int(m.group(1)) if m else 0


def rebuild_node(data, node, mesh, material_index, log=print, name=None, parent=None):
    """Node bytes for a rebuilt node.

    `node` is the DONOR: the source node whose track and non-count-sized blocks are
    copied. With name/parent given, the same builder emits a BRAND NEW node instead -
    which is what an added LOD is. Everything count-sized (positions, normals, uvs,
    indices, bbox, sphere, 0x40000 tangents) is generated; everything else is copied.
    """
    flags = node["flags"]
    if flags & 0x10:
        raise ValueError("node is skinned (0x10): its weights scale with the vertex "
                         "count and cannot be regenerated here")
    positions, normals, uvs, idx = _mesh_arrays(mesh)
    vc, ic = len(positions), len(idx)
    if vc > 0xFFFF:
        raise ValueError("vertex count %d exceeds what uint16 indices address" % vc)
    new_flags = flags & ~0x800
    out = bytearray()
    if name is None:
        o, size = node["spans"]["name"]
        out += data[o:o + size]
    else:
        raw = name.encode("ascii", "replace")[:63]
        out += struct.pack("<i", len(raw)) + raw + b"\x00"
    lo, hi, c, r = _bounds(positions)
    out += struct.pack("<3f", *lo) + struct.pack("<3f", *hi)
    out += struct.pack("<4f", c[0], c[1], c[2], r)
    if name is None:
        co, _cs = node["spans"]["counts"]
        level = struct.unpack_from("<i", data, co)[0]      # keep the donor's own
    else:
        level = lod_level(name)                            # added node: read the name
    out += struct.pack("<4i", level, vc, ic, 1)
    for p in positions:
        out += struct.pack("<3f", *p)
    for n in normals:
        out += struct.pack("<3f", *n)
    for uv in uvs:
        out += struct.pack("<2f", *uv)
    for i in idx:
        out += struct.pack("<H", i)
    out += struct.pack("<4I", (((ic & 0xFFFF) << 16) | (material_index & 0xFFFF)), 0, vc, 0)
    out += struct.pack("<2i", node["parent"] if parent is None else parent, new_flags)
    o, size = node["spans"]["d_count"]
    out += data[o:o + size]
    if "anim track" in node["spans"]:
        o, size = node["spans"]["anim track"]
        if name is None:
            out += data[o:o + size]
        else:
            # [2026-10-30] A NEW node is parented to the donor PART, which already carries
            # the part's own transform - so copying the donor's track applies that offset
            # TWICE and the level floats away from the thing it belongs to. G5's own LOD
            # children all carry an identity track (frame0 pos 0,0,0 quat 1,0,0,0) while
            # their bases carry real offsets: Body -0.456, TrackLeft +1.500, Turret_A -0.035.
            # Written blank here, keeping the frame COUNT so anchors stay in step.
            frames = size // 28
            out += b"\x00" * (frames * 12)
            out += struct.pack("<4f", 1.0, 0.0, 0.0, 0.0) * frames
    for label, bit in (("opt 0x40", 0x40), ("opt 0x200", 0x200), ("opt 0x400", 0x400),
                       ("opt 0x10000", 0x10000), ("opt 0x4000", 0x4000)):
        if new_flags & bit and label in node["spans"]:
            o, size = node["spans"][label]
            out += data[o:o + size]
    if new_flags & 0x40000:
        for t in tangent_basis(positions, uvs, idx, normals):
            out += struct.pack("<3f", *t)
    return bytes(out)
