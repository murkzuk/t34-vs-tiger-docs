"""
T34 vs Tiger .ms2 static-mesh importer - installable Blender add-on
(GitHub issue #12, Phase 3).

Unlike the earlier `ms2_import_blender.py` script (which only ran
inside the Blender 2.79 install used to build this tool, saving a
.blend file that had to be re-opened - and silently upgraded - by
whatever newer Blender the user has), this is a real add-on: install
it once, and it runs directly inside YOUR Blender, on YOUR version,
via File > Import > TvT Model (.ms2). No .blend file round-trip, no
version-upgrade step happening invisibly in between.

Scope is unchanged from the earlier script: static geometry only
(positions, authored normals, UVs, triangles, node hierarchy). No
skinning/animation, no shadow-volume/physics data, no materials
(materials/textures aren't stored in .ms2 at all - see the companion
Models\\<name>.script file's ModelSkin class).

The Redo panel (bottom-left after importing, or F9) exposes several
options as live diagnostics, not just preferences - in particular
"Shading" lets you re-import the same file with different normal
handling to isolate exactly what's causing any visual artifact,
without needing a new file or a script re-run:
    Authored  - use the file's own per-vertex normals (matches what
                the real game engine does; the default)
    Smooth    - ignore authored normals, derive smooth shading purely
                from mesh topology (shared vertex indices)
    Flat      - no smoothing at all. If an artifact survives with Flat
                shading, it is NOT a normals/shading bug at all - it's
                real geometry (missing faces, backface-culled holes,
                overlapping duplicates), since flat shading can't
                misinterpret a normal it never uses.
"""
import re

import bpy
import bmesh
from mathutils import Vector
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from . import ms2_reader

bl_info = {
    "name": "T34 vs Tiger .ms2 Importer",
    "author": "murkzuk, with Claude Code (Anthropic) assistance",
    "version": (1, 2, 0),
    "blender": (2, 80, 0),
    "location": "File > Import > TvT Model (.ms2)",
    "description": "Imports mesh geometry and skin weights (positions/normals/UVs/triangles/hierarchy/vertex groups) from T34 vs Tiger's .ms2 model format",
    "category": "Import-Export",
}


def _tri_area(p0, p1, p2):
    """Twice-signed-area cross product magnitude / 2 - used only to find
    genuinely zero-area (degenerate) triangles: three (near-)collinear
    or repeated vertices. Never compares against authored normal data,
    so it can't produce the false positives the earlier, retracted
    "winding disagreement" heuristic did."""
    ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    bx, by, bz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return (cx * cx + cy * cy + cz * cz) ** 0.5 / 2.0


_LOD_SUFFIX_RE = re.compile(r'_LOD\d+$', re.IGNORECASE)


def _is_hidden_by_default(name):
    """Real .ms2 files use a naming convention where a base node like
    "Body" has sibling variants: "_LOD1/2/4" (lower detail levels),
    "_Crashed" (damage state), and "_CM" (collision mesh, not meant to
    be rendered). These occupy the same world-space position as the
    base node, so importing every one as visible makes intact and
    wrecked/lower-detail versions all render stacked on top of each
    other. Everything is still imported (nothing lost) - this just
    decides what's visible by default."""
    if _LOD_SUFFIX_RE.search(name):
        return True
    if 'Crashed' in name:
        return True
    if name.endswith('_CM'):
        return True
    return False


def _create_object_for_node(node, index, skip_degenerate, normal_mode):
    """Builds a Blender mesh object from one Ms2Node. Returns the
    object, or an Empty for a no-geometry node."""
    if node.is_empty or not node.positions:
        obj = bpy.data.objects.new(node.name or ("node_%d" % index), None)
        obj.empty_display_size = 0.1
        return obj

    mesh = bpy.data.meshes.new(node.name or ("node_%d" % index))
    bm = bmesh.new()

    verts = [bm.verts.new(Vector(p)) for p in node.positions]
    bm.verts.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.new("UVMap") if node.uvs else None

    n_tris = len(node.indices) // 3
    dup_skipped = 0
    degenerate = 0
    for t in range(n_tris):
        i0, i1, i2 = node.indices[t * 3:t * 3 + 3]

        if skip_degenerate:
            if i0 == i1 or i1 == i2 or i0 == i2:
                degenerate += 1
                continue
            if _tri_area(node.positions[i0], node.positions[i1], node.positions[i2]) < 1e-8:
                degenerate += 1
                continue

        try:
            face = bm.faces.new((verts[i0], verts[i1], verts[i2]))
        except ValueError:
            # Duplicate face - bmesh disallows exact duplicates. Skip
            # rather than aborting the whole import.
            dup_skipped += 1
            continue
        if uv_layer:
            for loop, vi in zip(face.loops, (i0, i1, i2)):
                if vi < len(node.uvs):
                    u, v = node.uvs[vi]
                    loop[uv_layer].uv = (u, v)

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    used_authored_normals = False
    if normal_mode == 'AUTHORED' and node.normals and len(node.normals) == len(node.positions):
        try:
            if hasattr(mesh, "use_auto_smooth"):
                mesh.use_auto_smooth = True
            mesh.normals_split_custom_set_from_vertices([Vector(n) for n in node.normals])
            used_authored_normals = True
        except Exception as e:
            print("  (%s: custom split normals unavailable on this Blender "
                  "version (%s) - falling back to smooth shading)" % (node.name, e))

    for poly in mesh.polygons:
        poly.use_smooth = (normal_mode != 'FLAT')

    if dup_skipped or degenerate:
        print("  (%s: skipped %d duplicate, %d degenerate zero-area face(s))"
              % (node.name, dup_skipped, degenerate))
    if normal_mode == 'AUTHORED' and not used_authored_normals and node.normals:
        print("  (%s: authored normals not applied - see above)" % node.name)

    obj = bpy.data.objects.new(node.name or ("node_%d" % index), mesh)
    obj["ms2_node_index"] = index
    return obj


def import_ms2(path, hide_variants=True, skip_degenerate=True, normal_mode='AUTHORED'):
    """Imports a .ms2 file into the current Blender scene. Returns the
    list of created Blender objects, indexed the same way as the
    source node list (so obj_list[node.parent_index] gives the
    parent)."""
    nodes = ms2_reader.read_ms2(path)

    collection = bpy.context.collection
    objects = []
    hidden_count = 0
    for i, node in enumerate(nodes):
        obj = _create_object_for_node(node, i, skip_degenerate, normal_mode)
        objects.append(obj)
        collection.objects.link(obj)
        if hide_variants and _is_hidden_by_default(node.name):
            obj.hide_viewport = True
            obj.hide_render = True
            hidden_count += 1

    # Skin weights -> real Blender vertex groups, one per influencing
    # joint, named after the joint node it points at. Purely additive:
    # no vertex is moved, so this cannot change how anything looks. It
    # is what the rigging half of the pipeline needs, and it makes the
    # joint assignment directly inspectable in Blender's own UI.
    weighted = 0
    for i, node in enumerate(nodes):
        if not node.weights or not node.positions:
            continue
        obj = objects[i]
        groups = {}
        for v, (w, js) in enumerate(zip(node.weights, node.joint_idx)):
            for k in range(4):
                if w[k] <= 1e-6:
                    continue
                j = js[k]
                if not (0 <= j < len(nodes)):
                    continue
                name = nodes[j].name or ("node_%d" % j)
                g = groups.get(name)
                if g is None:
                    g = groups[name] = obj.vertex_groups.new(name=name)
                g.add([v], w[k], 'REPLACE')
        if groups:
            weighted += 1
    if weighted:
        print("  skin weights: %d objects given vertex groups" % weighted)

    # Wire up parenting after all objects exist, using node_id as a
    # same-file node index (confirmed against real production data).
    for i, node in enumerate(nodes):
        if 0 <= node.parent_index < len(objects) and node.parent_index != i:
            objects[i].parent = objects[node.parent_index]

    print("Imported %s: %d nodes (%d with geometry, %d hidden by default "
          "as LOD/Crashed/CM variants)" % (
        path, len(nodes), sum(1 for n in nodes if not n.is_empty and n.positions),
        hidden_count))
    return objects


class IMPORT_OT_tvt_ms2(Operator, ImportHelper):
    bl_idname = "import_scene.tvt_ms2"
    bl_label = "Import TvT .ms2"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".ms2"
    filter_glob: StringProperty(default="*.ms2", options={'HIDDEN'})

    hide_variants: BoolProperty(
        name="Hide LOD/Crashed/CM variants",
        description="Hide (but still import) lower-detail, damage-state, "
                    "and collision-mesh variant nodes by default, since "
                    "they occupy the same space as the base node",
        default=True,
    )
    skip_degenerate: BoolProperty(
        name="Skip zero-area triangles",
        description="Skip triangles with repeated or (near-)collinear "
                    "vertices - these render as nothing in any engine, "
                    "but can otherwise poison Blender's own topology-based "
                    "normal recomputation",
        default=True,
    )
    normal_mode: EnumProperty(
        name="Shading",
        description="How to shade the imported mesh - useful as a live "
                    "diagnostic, not just a preference",
        items=[
            ('AUTHORED', "Authored", "Use the file's own per-vertex normals "
                                      "(matches the real game engine)"),
            ('SMOOTH', "Smooth (topology)", "Ignore authored normals; derive "
                                            "smooth shading from mesh topology alone"),
            ('FLAT', "Flat", "No smoothing at all. If an artifact survives "
                              "with Flat shading, it isn't a normals bug - "
                              "it's real geometry"),
        ],
        default='AUTHORED',
    )

    def execute(self, context):
        objects = import_ms2(
            self.filepath,
            hide_variants=self.hide_variants,
            skip_degenerate=self.skip_degenerate,
            normal_mode=self.normal_mode,
        )
        self.report({'INFO'}, "Imported %d object(s) from %s" % (len(objects), self.filepath))
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_tvt_ms2.bl_idname, text="TvT Model (.ms2)")


def register():
    bpy.utils.register_class(IMPORT_OT_tvt_ms2)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(IMPORT_OT_tvt_ms2)


if __name__ == "__main__":
    register()
