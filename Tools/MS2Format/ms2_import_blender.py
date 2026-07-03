"""
.ms2 static-mesh importer for Blender 2.79 (GitHub issue #12, Phase 3).

Imports the static geometry (positions, normals, UVs, triangles, and
node hierarchy) from a .ms2 file into the current Blender scene. Does
NOT import skinning/bone weights, animation, or shadow-volume/physics
data - those record types aren't fully decoded yet (see
Documentation/MS2_Binary_Format_Findings_2026-07-03.md). Meshes that
use those features will still import their base geometry correctly;
they just won't be rigged or animated.

Materials/textures are not stored in .ms2 at all - they live in the
companion Models\\<name>.script file's ModelSkin class as plain text.
This importer does NOT yet parse that file (a separate, much simpler
task, since it's plain text) - imported meshes have no material
assigned.

Usage (Blender 2.79, from the Scripting tab or headless):
    import sys
    sys.path.insert(0, r"C:\path\to\Tools\MS2Format")
    import ms2_import_blender
    ms2_import_blender.import_ms2(r"C:\path\to\Models\bld_Haystack.ms2")

Or from the command line:
    blender --background --python ms2_import_blender.py -- <path-to-.ms2>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ms2_reader

import bpy
import bmesh
from mathutils import Vector


def _create_object_for_node(node, index):
    """Builds a Blender mesh object from one Ms2Node. Returns the object,
    or None for an empty/container node (created as an Empty instead)."""
    if node.is_empty or not node.positions:
        obj = bpy.data.objects.new(node.name or ("node_%d" % index), None)
        obj.empty_draw_size = 0.1
        return obj

    mesh = bpy.data.meshes.new(node.name or ("node_%d" % index))
    bm = bmesh.new()

    verts = [bm.verts.new(Vector(p)) for p in node.positions]
    bm.verts.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.new("UVMap") if node.uvs else None

    n_tris = len(node.indices) // 3
    skipped = 0
    flipped = 0
    for t in range(n_tris):
        i0, i1, i2 = node.indices[t * 3:t * 3 + 3]

        # The exported triangle winding doesn't always agree with the
        # file's own authored per-vertex normals (confirmed empirically -
        # ~7% of faces in real shipped content disagree, concentrated in
        # damage/"Crashed" variant meshes) - if left uncorrected this
        # produces dark, inside-out-looking faces from otherwise-correct
        # viewing angles. Since we have the real authored normals, use
        # them as ground truth: compute this triangle's geometric normal
        # from its vertex order, and reverse the order if it disagrees
        # with the average of the three vertices' authored normals.
        p0, p1, p2 = node.positions[i0], node.positions[i1], node.positions[i2]
        edge1 = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
        edge2 = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
        geo_normal = (edge1[1]*edge2[2]-edge1[2]*edge2[1],
                      edge1[2]*edge2[0]-edge1[0]*edge2[2],
                      edge1[0]*edge2[1]-edge1[1]*edge2[0])
        n0, n1, n2 = node.normals[i0], node.normals[i1], node.normals[i2]
        avg_normal = (n0[0]+n1[0]+n2[0], n0[1]+n1[1]+n2[1], n0[2]+n1[2]+n2[2])
        dot = geo_normal[0]*avg_normal[0] + geo_normal[1]*avg_normal[1] + geo_normal[2]*avg_normal[2]
        if dot < 0:
            i1, i2 = i2, i1
            flipped += 1

        try:
            face = bm.faces.new((verts[i0], verts[i1], verts[i2]))
        except ValueError:
            # Duplicate/degenerate face (bmesh disallows exact duplicates) -
            # skip rather than aborting the whole import.
            skipped += 1
            continue
        if uv_layer:
            for loop, vi in zip(face.loops, (i0, i1, i2)):
                if vi < len(node.uvs):
                    u, v = node.uvs[vi]
                    loop[uv_layer].uv = (u, v)

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    # Apply the file's own per-vertex normals (custom split normals),
    # rather than relying only on bmesh's recomputed face/vertex normals -
    # the .ms2 format stores real authored normals we should preserve.
    if node.normals and len(node.normals) == len(node.positions):
        mesh.use_auto_smooth = True
        try:
            mesh.normals_split_custom_set_from_vertices(
                [Vector(n) for n in node.normals])
        except Exception:
            pass  # older/newer API mismatch - not fatal, face normals still work

    if skipped or flipped:
        print("  (%s: flipped %d face(s) to match authored normals, skipped %d degenerate/duplicate)" % (
            node.name, flipped, skipped))

    obj = bpy.data.objects.new(node.name or ("node_%d" % index), mesh)
    return obj


def import_ms2(path, link_to_scene=True):
    """Imports a .ms2 file into the current Blender scene. Returns the
    list of created Blender objects, indexed the same way as the source
    node list (so obj_list[node.parent_index] gives the parent object)."""
    nodes = ms2_reader.read_ms2(path)

    scene = bpy.context.scene
    objects = []
    for i, node in enumerate(nodes):
        obj = _create_object_for_node(node, i)
        objects.append(obj)
        if link_to_scene:
            scene.objects.link(obj)

    # Wire up parenting after all objects exist, using node_id as a
    # same-file node index (confirmed against real production data -
    # see the findings doc's "node_id confirmed as parent-node index"
    # section).
    for i, node in enumerate(nodes):
        if 0 <= node.parent_index < len(objects) and node.parent_index != i:
            objects[i].parent = objects[node.parent_index]

    print("Imported %s: %d nodes (%d with geometry)" % (
        path, len(nodes), sum(1 for n in nodes if not n.is_empty and n.positions)))
    return objects


if __name__ == '__main__':
    # Support `blender --background --python ms2_import_blender.py -- <path>`
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []
    if not argv:
        print("Usage: blender --background --python ms2_import_blender.py -- <path-to-.ms2>")
    else:
        import_ms2(argv[0])
