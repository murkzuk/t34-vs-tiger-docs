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
materials (materials/textures aren't stored in .ms2 at all - see the
companion Models\\<name>.script file's ModelSkin class).

Per-vertex skin weights (flags_bitmask & 0x10): some nodes (confirmed:
u_veh_t34_85_44.ms2's Turret_A and 27 others in the same file) have a
per-vertex "dominant joint" index - always found rigidly weighted to
exactly one joint (never blended) - where that joint is a plain node
index into this same file's hierarchy. Cross-referencing the companion
.script file confirmed these are real animation channels (e.g.
"gun_a_recoil" -> Weapon_A, "luk_main_open" -> Luk_C/Luk_D) - moving
parts like the gun barrel (recoil) and hatches (opening), whose
vertices are baked into the SAME mesh as the fixed hull rather than
being separate nodes. Confirmed directly against the real TvT Editor
(screenshot comparison) that these vertices need a bind-pose transform
that ISN'T present anywhere in the .ms2 file or the .script file -
checked exhaustively. Without it, importing these vertices at face
value produces genuinely wrong, visibly broken geometry (a real
position defect, not a shading/normals issue). Until that transform is
found, this importer splits each such node's faces into two separate
objects: "<Name>" (vertices rigidly weighted to the node itself - safe,
correctly positioned) and "<Name>_UnresolvedSkin" (vertices weighted to
any other joint - hidden by default, parented to the main object,
nothing lost).

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
    "description": "Imports static mesh geometry (positions/normals/UVs/triangles/hierarchy) from T34 vs Tiger's .ms2 model format",
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


def _build_mesh(mesh_name, node, tri_indices, skip_degenerate, normal_mode):
    """Builds one Blender mesh from a subset of node's triangles (given
    as a list of triangle indices into node.indices)."""
    mesh = bpy.data.meshes.new(mesh_name)
    bm = bmesh.new()

    verts = [bm.verts.new(Vector(p)) for p in node.positions]
    bm.verts.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.new("UVMap") if node.uvs else None

    dup_skipped = 0
    degenerate = 0
    created = 0
    for t in tri_indices:
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
        created += 1
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
                  "version (%s) - falling back to smooth shading)" % (mesh_name, e))

    for poly in mesh.polygons:
        poly.use_smooth = (normal_mode != 'FLAT')

    if dup_skipped or degenerate:
        print("  (%s: skipped %d duplicate, %d degenerate zero-area face(s))"
              % (mesh_name, dup_skipped, degenerate))
    if normal_mode == 'AUTHORED' and not used_authored_normals and node.normals:
        print("  (%s: authored normals not applied - see above)" % mesh_name)

    return mesh, created


def _create_object_for_node(node, index, skip_degenerate, normal_mode):
    """Builds Blender object(s) from one Ms2Node. Returns a list of
    (obj, hide_by_default) tuples - normally just one entry, but a node
    with per-vertex skin weights (see module docstring) that reference
    a DIFFERENT joint than its own node index produces a second object
    "<Name>_UnresolvedSkin", hidden by default."""
    base_name = node.name or ("node_%d" % index)

    if node.is_empty or not node.positions:
        obj = bpy.data.objects.new(base_name, None)
        obj.empty_display_size = 0.1
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

    mesh, _ = _build_mesh(base_name, node, self_tris, skip_degenerate, normal_mode)
    obj = bpy.data.objects.new(base_name, mesh)
    results = [(obj, False)]

    if other_tris:
        ext_name = base_name + "_UnresolvedSkin"
        ext_mesh, ext_created = _build_mesh(ext_name, node, other_tris, skip_degenerate, normal_mode)
        if ext_created:
            ext_obj = bpy.data.objects.new(ext_name, ext_mesh)
            results.append((ext_obj, True))
        else:
            bpy.data.meshes.remove(ext_mesh)

    return results


def import_ms2(path, hide_variants=True, skip_degenerate=True, normal_mode='AUTHORED',
               hide_unresolved_skin=True):
    """Imports a .ms2 file into the current Blender scene. Returns the
    list of created Blender objects. The first len(nodes) entries are
    indexed the same way as the source node list (so
    obj_list[node.parent_index] gives the parent); any further entries
    are "_UnresolvedSkin" sub-objects, each already parented to its own
    node's main object."""
    nodes = ms2_reader.read_ms2(path)

    collection = bpy.context.collection
    primary_objects = []
    extra_objects = []
    hidden_count = 0
    unresolved_count = 0
    for i, node in enumerate(nodes):
        results = _create_object_for_node(node, i, skip_degenerate, normal_mode)
        primary_obj = results[0][0]
        primary_objects.append(primary_obj)
        collection.objects.link(primary_obj)
        if hide_variants and _is_hidden_by_default(node.name):
            primary_obj.hide_viewport = True
            primary_obj.hide_render = True
            hidden_count += 1

        for obj, hide_default in results[1:]:
            collection.objects.link(obj)
            obj.parent = primary_obj
            if hide_unresolved_skin and hide_default:
                obj.hide_viewport = True
                obj.hide_render = True
                unresolved_count += 1
            extra_objects.append(obj)

    # Wire up parenting after all objects exist, using node_id as a
    # same-file node index (confirmed against real production data).
    for i, node in enumerate(nodes):
        if 0 <= node.parent_index < len(primary_objects) and node.parent_index != i:
            primary_objects[i].parent = primary_objects[node.parent_index]

    print("Imported %s: %d nodes (%d with geometry, %d hidden by default "
          "as LOD/Crashed/CM variants, %d _UnresolvedSkin sub-object(s) "
          "hidden pending bind-transform decoding)" % (
        path, len(nodes), sum(1 for n in nodes if not n.is_empty and n.positions),
        hidden_count, unresolved_count))
    return primary_objects + extra_objects


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
    hide_unresolved_skin: BoolProperty(
        name="Hide unresolved skin-weighted parts",
        description="Some nodes (e.g. gun barrels, hatches) have vertices "
                    "rigidly weighted to a moving joint whose bind-pose "
                    "transform isn't decoded yet. Importing them at face "
                    "value produces genuinely wrong geometry (confirmed "
                    "against the real TvT Editor), so they're split into "
                    "a separate '_UnresolvedSkin' object and hidden by "
                    "default. Nothing is lost - untick to inspect them.",
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
            hide_unresolved_skin=self.hide_unresolved_skin,
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
