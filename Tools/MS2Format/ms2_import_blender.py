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

Every node in the file is imported (nothing is skipped), but nodes
matching the game's own "_LODn" / "_Crashed" / "_CM" naming convention
are hidden by default, since they occupy the same world-space position
as their base node and would otherwise all render simultaneously
stacked on top of each other - see _is_hidden_by_default() below.

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
    degenerate = 0
    tri_verts = []  # (i0, i1, i2) for each face actually created, in order
    for t in range(n_tris):
        i0, i1, i2 = node.indices[t * 3:t * 3 + 3]

        # NOTE: an earlier version of this importer "corrected" triangle
        # winding whenever it disagreed with the file's own authored
        # per-vertex normals (computed via cross product vs the file's
        # normal data). That was WRONG - confirmed directly by the user,
        # who can view these exact assets correctly in the real TvT
        # Editor with no issue, proving the raw source data already
        # renders correctly in the actual target engine. The "disagreement"
        # this importer was detecting is not a real defect in the source
        # data; trust the file's index order exactly as authored instead.

        # A genuinely zero-area triangle (collinear/repeated vertices) has
        # no well-defined normal. It renders as nothing in any engine, but
        # if left in, Blender's own topology-based normal/shading
        # recomputation can pick up its undefined normal and smear
        # incorrect shading onto the real triangles sharing its vertices -
        # found via a direct check of Turret_A's raw geometry: 70 such
        # triangles, all clustered in the same upper/roof region the user
        # reported as visibly broken ("commander's hatch forwards").
        # Skipping them here is a one-way filter on genuine geometric
        # degeneracy, not a guess about authored intent.
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
        tri_verts.append((i0, i1, i2))
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
    # recomputation. This was tried before and briefly reverted to plain
    # smooth shading on a hypothesis that the custom-normals API itself
    # was version-sensitive across Blender releases - but with the
    # degenerate triangles above now filtered out (they were the only
    # concrete mechanism found for topology-based normals to actually
    # break), reapplying the authored normals is strictly more faithful
    # to the source data than any Blender-side recomputation, and is what
    # the real TvT engine itself does (it never derives normals from
    # geometry either).
    if node.normals and len(node.normals) == len(node.positions):
        mesh.use_auto_smooth = True
        mesh.normals_split_custom_set_from_vertices(
            [Vector(n) for n in node.normals])
    else:
        for poly in mesh.polygons:
            poly.use_smooth = True

    if skipped or degenerate:
        print("  (%s: skipped %d duplicate, %d degenerate zero-area face(s))"
              % (node.name, skipped, degenerate))

    obj = bpy.data.objects.new(node.name or ("node_%d" % index), mesh)
    return obj


def import_ms2(path, link_to_scene=True):
    """Imports a .ms2 file into the current Blender scene. Returns the
    list of created Blender objects, indexed the same way as the source
    node list (so obj_list[node.parent_index] gives the parent object)."""
    nodes = ms2_reader.read_ms2(path)

    scene = bpy.context.scene
    objects = []
    hidden_count = 0
    for i, node in enumerate(nodes):
        obj = _create_object_for_node(node, i)
        objects.append(obj)
        if link_to_scene:
            scene.objects.link(obj)
        if _is_hidden_by_default(node.name):
            obj.hide = True
            obj.hide_render = True
            hidden_count += 1

    # Wire up parenting after all objects exist, using node_id as a
    # same-file node index (confirmed against real production data -
    # see the findings doc's "node_id confirmed as parent-node index"
    # section).
    for i, node in enumerate(nodes):
        if 0 <= node.parent_index < len(objects) and node.parent_index != i:
            objects[i].parent = objects[node.parent_index]

    print("Imported %s: %d nodes (%d with geometry, %d hidden by default "
          "as LOD/Crashed/CM variants)" % (
        path, len(nodes), sum(1 for n in nodes if not n.is_empty and n.positions),
        hidden_count))
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
