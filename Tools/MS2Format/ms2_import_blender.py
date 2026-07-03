"""
.ms2 static-mesh importer for Blender 2.79 (GitHub issue #12, Phase 3).

Imports the static geometry (positions, normals, UVs, triangles, and
node hierarchy) from a .ms2 file into the current Blender scene. Does
NOT apply skin animation - see "Per-vertex skin weights" below for what
that means for nodes that have them.

Materials/textures are not stored in .ms2 at all - they live in the
companion Models\\<name>.script file's ModelSkin class as plain text.
This importer does NOT yet parse that file (a separate, much simpler
task, since it's plain text) - imported meshes have no material
assigned.

Every node in the file is imported (nothing is skipped), but nodes
matching the game's own "_LODn" / "_Crashed" / "_CM" naming convention
are hidden by default, since they occupy the same world-space position
as their base node and would otherwise all render simultaneously
stacked on top of each other - see _is_hidden_by_default() below.

Per-vertex skin weights (flags_bitmask & 0x10): some nodes (confirmed:
u_veh_t34_85_44.ms2's Turret_A) have a per-vertex "dominant joint" index
- always found rigidly weighted to exactly one joint (never blended) -
where that joint is a plain node index into this same file's hierarchy.
Cross-referencing the companion .script file confirmed these joints are
real animation channels (e.g. "gun_a_recoil" -> Weapon_A, "luk_main_open"
-> Luk_C/Luk_D) - moving parts like the gun barrel (recoil) and hatches
(opening), whose vertices are baked into the SAME mesh as the fixed hull
rather than being separate nodes. Confirmed directly against the real
TvT Editor (screenshot comparison) that these vertices need a bind-pose
transform applied that ISN'T present anywhere in the .ms2 file or the
.script file - checked exhaustively (bbox/sphere fields, every optional
block gated by the joint node's own flags). Without that transform,
importing these vertices at face value produces genuinely wrong,
visibly broken geometry (confirmed via direct render comparison against
the real editor - not a normals/shading issue, an actual position
defect). Until that transform is found, this importer splits each such
node's faces into two separate objects: "<Name>" (vertices rigidly
weighted to the node itself - safe, correctly positioned) and
"<Name>_UnresolvedSkin" (vertices weighted to any other joint - hidden
by default, parented to the main object, nothing lost, clearly labeled
as needing more reverse-engineering rather than silently showing broken
geometry).

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
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ms2_reader

import bpy
import bmesh
from mathutils import Vector


def _tri_area(p0, p1, p2):
    """Twice-signed-area cross product magnitude / 2 - used only to find
    genuinely zero-area (degenerate) triangles. This is NOT the same
    check as the retracted "winding disagreement" heuristic: it never
    compares against the file's authored normals, so it can't produce
    the same false positives - a triangle is only flagged here if its
    three vertices are (near-)collinear, which is a real defect no
    matter which engine renders it."""
    ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    bx, by, bz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return (cx * cx + cy * cy + cz * cz) ** 0.5 / 2.0


_LOD_SUFFIX_RE = re.compile(r'_LOD\d+$', re.IGNORECASE)


def _is_hidden_by_default(name):
    """Real .ms2 files use a naming convention (confirmed against shipped
    content, e.g. u_veh_t34_85_44.ms2) where a base node like "Body" has
    sibling variants: "_LOD1/2/4" (lower detail levels), "_Crashed"
    (damage state), and "_CM" (collision mesh, not meant to be rendered).
    These siblings all occupy the same world-space position as the base
    node, so importing every one of them as visible geometry makes the
    intact and wrecked/lower-detail versions all render simultaneously,
    stacked on top of each other - this is what produced the "shattered"
    look reported when first testing this importer, not a normals bug.
    Everything is still imported (nothing is skipped or lost) - this
    just decides what's visible by default so a straightforward import
    looks like the intact, full-detail vehicle."""
    if _LOD_SUFFIX_RE.search(name):
        return True
    if 'Crashed' in name:
        return True
    if name.endswith('_CM'):
        return True
    return False


def _build_mesh(mesh_name, node, tri_indices):
    """Builds one Blender mesh from a subset of node's triangles (given
    as a list of triangle indices into node.indices). Returns (mesh,
    faces_created)."""
    mesh = bpy.data.meshes.new(mesh_name)
    bm = bmesh.new()

    verts = [bm.verts.new(Vector(p)) for p in node.positions]
    bm.verts.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.new("UVMap") if node.uvs else None

    skipped = 0
    degenerate = 0
    created = 0
    for t in tri_indices:
        i0, i1, i2 = node.indices[t * 3:t * 3 + 3]

        # NOTE: an earlier version of this importer "corrected" triangle
        # winding whenever it disagreed with the file's own authored
        # per-vertex normals. That was WRONG - confirmed directly by the
        # user, who can view these exact assets correctly in the real
        # TvT Editor with no issue, proving the raw source data already
        # renders correctly in the actual target engine. Trust the
        # file's index order exactly as authored instead.

        # A genuinely zero-area triangle (collinear/repeated vertices) has
        # no well-defined normal, and can poison Blender's own topology-
        # based normal/shading recomputation for real neighboring
        # triangles - found via a direct check of Turret_A's raw
        # geometry (70 such triangles). Skipping them is a one-way filter
        # on genuine geometric degeneracy, not a guess about intent.
        if i0 == i1 or i1 == i2 or i0 == i2:
            degenerate += 1
            continue
        if _tri_area(node.positions[i0], node.positions[i1], node.positions[i2]) < 1e-8:
            degenerate += 1
            continue

        try:
            face = bm.faces.new((verts[i0], verts[i1], verts[i2]))
        except ValueError:
            # Duplicate face (bmesh disallows exact duplicates) - skip
            # rather than aborting the whole import.
            skipped += 1
            continue
        created += 1
        if uv_layer:
            for loop, vi in zip(face.loops, (i0, i1, i2)):
                if vi < len(node.uvs):
                    u, v = node.uvs[vi]
                    loop[uv_layer].uv = (u, v)

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    # Reapply the file's own authored per-vertex normals as Blender custom
    # split normals, rather than trusting Blender's own geometry-based
    # recomputation - strictly more faithful to the source data, and
    # matches what the real TvT engine itself does (it never derives
    # normals from geometry either). See the findings doc for why the
    # earlier "version-sensitive API" hypothesis for this was dropped
    # once the real cause (degenerate triangles above) was found.
    if node.normals and len(node.normals) == len(node.positions):
        mesh.use_auto_smooth = True
        mesh.normals_split_custom_set_from_vertices(
            [Vector(n) for n in node.normals])
    else:
        for poly in mesh.polygons:
            poly.use_smooth = True

    if skipped or degenerate:
        print("  (%s: skipped %d duplicate, %d degenerate zero-area face(s))"
              % (mesh_name, skipped, degenerate))

    return mesh, created


def _create_object_for_node(node, index):
    """Builds Blender object(s) from one Ms2Node. Returns a list of
    (obj, hide_by_default) tuples - normally just one entry, but a node
    with per-vertex skin weights (flags_bitmask & 0x10, see module
    docstring) that reference a DIFFERENT joint than its own node index
    produces a second object holding just that geometry, named
    "<Name>_UnresolvedSkin" and hidden by default."""
    base_name = node.name or ("node_%d" % index)

    if node.is_empty or not node.positions:
        obj = bpy.data.objects.new(base_name, None)
        obj.empty_draw_size = 0.1
        return [(obj, False)]

    n_tris = len(node.indices) // 3

    if node.vertex_joint:
        self_tris = []
        other_tris = []
        for t in range(n_tris):
            i0, i1, i2 = node.indices[t * 3:t * 3 + 3]
            if (node.vertex_joint[i0] == index and node.vertex_joint[i1] == index
                    and node.vertex_joint[i2] == index):
                self_tris.append(t)
            else:
                other_tris.append(t)
    else:
        self_tris = list(range(n_tris))
        other_tris = []

    mesh, _ = _build_mesh(base_name, node, self_tris)
    obj = bpy.data.objects.new(base_name, mesh)
    results = [(obj, False)]

    if other_tris:
        ext_name = base_name + "_UnresolvedSkin"
        ext_mesh, ext_created = _build_mesh(ext_name, node, other_tris)
        if ext_created:
            ext_obj = bpy.data.objects.new(ext_name, ext_mesh)
            results.append((ext_obj, True))
        else:
            bpy.data.meshes.remove(ext_mesh)

    return results


def import_ms2(path, link_to_scene=True):
    """Imports a .ms2 file into the current Blender scene. Returns the
    list of created Blender objects. The first len(nodes) entries are
    indexed the same way as the source node list (so
    obj_list[node.parent_index] gives the parent object); any further
    entries are "_UnresolvedSkin" sub-objects, each already parented to
    its own node's main object."""
    nodes = ms2_reader.read_ms2(path)

    scene = bpy.context.scene
    primary_objects = []
    extra_objects = []
    hidden_count = 0
    unresolved_count = 0
    for i, node in enumerate(nodes):
        results = _create_object_for_node(node, i)
        primary_obj = results[0][0]
        primary_objects.append(primary_obj)
        if link_to_scene:
            scene.objects.link(primary_obj)
        if _is_hidden_by_default(node.name):
            primary_obj.hide = True
            primary_obj.hide_render = True
            hidden_count += 1

        for obj, hide_default in results[1:]:
            if link_to_scene:
                scene.objects.link(obj)
            obj.parent = primary_obj
            if hide_default:
                obj.hide = True
                obj.hide_render = True
                unresolved_count += 1
            extra_objects.append(obj)

    # Wire up parenting after all objects exist, using node_id as a
    # same-file node index (confirmed against real production data -
    # see the findings doc's "node_id confirmed as parent-node index"
    # section).
    for i, node in enumerate(nodes):
        if 0 <= node.parent_index < len(primary_objects) and node.parent_index != i:
            primary_objects[i].parent = primary_objects[node.parent_index]

    print("Imported %s: %d nodes (%d with geometry, %d hidden by default "
          "as LOD/Crashed/CM variants, %d _UnresolvedSkin sub-object(s) "
          "hidden pending bind-transform decoding)" % (
        path, len(nodes), sum(1 for n in nodes if not n.is_empty and n.positions),
        hidden_count, unresolved_count))
    return primary_objects + extra_objects


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
