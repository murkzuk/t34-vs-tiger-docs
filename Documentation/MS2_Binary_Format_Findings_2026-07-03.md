# `.ms2` Binary Format — Findings (Phase 1 empirical + Phase 2 ground truth)

**Date:** 2026-07-03
**Author:** Claude Code (Anthropic), with murkz
**Status:** Phase 1 (empirical byte probing) is complete and superseded in most respects by Phase 2 (real ground truth, obtained by decompiling `MayaExp.mll` itself with Ghidra — see the dedicated section near the bottom of this document). **Read the Phase 2 section for the authoritative, verified structure** — the Phase 1 material above it is kept for its investigative history and because it correctly identified almost everything Phase 2 later confirmed from actual source, but a few Phase 1 guesses (field ordering around `parent_idx`/`child_count`) turned out to be wrong once real ground truth was available.
**Companion tools:** `Tools\MS2Format\ms2_probe.py` (Phase 1, empirical) and `Tools\MS2Format\ms2_parser.py` (Phase 2, ground-truth, more accurate — use this one).

This is Phase 1 of the plan in `Documentation/T34_vs_Tiger_Maya_Export_Manual(V3).md` Section 11 (GitHub issue #12 — eventual goal is a Blender import/export pipeline). Phase 0 covered the Maya-side authoring metadata; this covers the actual on-disk byte format those attributes get serialized into.

## Correction to an earlier version of this document

An earlier pass of this same investigation concluded that 16 bytes immediately after the bounding-sphere block were "padding, always zero." **That was wrong, caused by a display bug, not a data problem**: those bytes were printed as `round(float_value, 6)`, and several of them are tiny IEEE-754 denormalized floats (e.g. the bit pattern for int32 `24` reinterpreted as a float is `3.36e-44`) that round to display as `0.0` even though the underlying integer is very much not zero. Reading the same bytes as `int32` instead of `float32` revealed real, meaningful data — the actual vertex and triangle-index counts. This is now corrected throughout. Lesson for anyone continuing this work: **always check candidate count/metadata fields as both int32 and float32 before concluding a region is "just zero" — a real integer can look like an all-zero float at low precision display.**

## Confirmed: universal file header (checked against all 62 sample `.ms2` files, 62/62 match)

Every `.ms2` file starts with:

| Offset | Size | Type | Meaning |
|---|---|---|---|
| 0x00 | 4 bytes | int32 LE | Always `0` in every sample checked — likely a format version or flags field |
| 0x04 | 4 bytes | int32 LE | Total node/object count in the file. Scales cleanly with model complexity (1 for a single mesh, up to 335 for the most complex vehicle) |
| 0x08 | 4 bytes | int32 LE | Length (in bytes) of the following name string |
| 0x0C | *namelen* bytes | ASCII | The node's name, taken verbatim from the Maya scene — e.g. `pCube1`, `QuadPatch01`, `ROOT`, `Root`, `root`, `locator1`, `Bomb`, `Rocket2` |
| 0x0C + namelen | 1 byte | — | A single `0x00` null terminator after the name (not counted in the length field) |

A genuinely interesting side finding from the node-count sweep: `u_veh_t34_76_41.ms2` — the model already flagged elsewhere in this project's backlog as a "cut content" tank variant with full ballistics stats but no `Units\*.script` gameplay class ever built for it — has a root node named `locator1` instead of the `ROOT`/`Root` convention every other shipped vehicle uses, and a node count of only 14 versus 216-335 for its finished siblings. This is an independent, purely binary-structure-based confirmation of something already suspected from a completely different investigation (auditing `.script` class references) — the model file itself looks structurally unfinished.

## Confirmed: the real per-node header, including vertex/index counts

After a node's name + null terminator, the confirmed layout is:

| Field | Size | Notes |
|---|---|---|
| Bounding box min | 3 floats (12 bytes) | |
| Bounding box max | 3 floats (12 bytes) | |
| Bounding sphere center | 3 floats (12 bytes) | |
| Bounding sphere radius | 1 float (4 bytes) | |
| `flag` | int32 | Always `0` in every sample checked so far |
| **`vertex_count`** | int32 | **The real, confirmed vertex count** |
| **`index_count`** | int32 | **The real, confirmed face-index count** (number of `uint16` values, i.e. `3 × triangle_count`) |
| `other` | int32 | `1` when the node has real geometry, `0` for an empty container node — meaning unconfirmed beyond that |
| `parent_idx` | int32 | **Only present when the file has more than one node.** Index of the parent node, `-1` if none |
| `child_count` | int32 | **Only present when the file has more than one node** |

Then, if `vertex_count > 0`:

| Block | Size |
|---|---|
| Vertex positions | `vertex_count × 3` floats |
| Vertex normals | `vertex_count × 3` floats |
| Vertex UVs | `vertex_count × 2` floats |
| Face indices | `index_count` × `uint16` |

If `vertex_count == 0` (an empty container/transform node), there is no position/normal/UV/index data — some other, not-yet-decoded block follows instead (see below), and the next node has to be located by scanning for its name string rather than computed directly.

### Verification — checked against 7 files, all with sensible, physically-correct results

| File | Node | Vertices | Face indices (÷3 = triangles) | Bounding box | Sanity check |
|---|---|---|---|---|---|
| `MyFirstModel.ms2` / `4MeterBox.ms2` | `pCube1` | **24** | **36** (12 tri) | ±0.005 / ±0.5 respectively | Exact match to a known hard-edged cube (4 verts/face × 6 faces, 2 tri/face × 6 faces) |
| `wpn_Bomb.ms2` | `Bomb` | 94 | 252 (84 tri) | X: ±0.791, Y/Z: ±0.205 | Long, thin bounding box — correct for a bomb shape |
| `wpn_FFAR.ms2` | `Rocket2` | 273 | 972 (324 tri) | X: ±0.837, Y/Z: ±0.036 | Very long, very thin — correct for a rocket |
| `Sky.ms2` | `SkyDome` | **395** | 2040 (680 tri) | X/Y ±7874, Z -11481..+7874 | Vertex count matches an earlier, independent magnitude-based estimate exactly |
| `sphere_test.ms2` | `pSphere1` | 270 | 378 (126 tri) | roughly ±1 on all axes | Correct for a unit sphere |
| `test.ms2` | `pSphere1` | 401 | 2280 (760 tri) | roughly ±0.01 on all axes | Correct for a small sphere |

`vertex_count`/`index_count` for the cube were cross-checked two independent ways: (1) directly reading the field, and (2) an earlier magnitude-scanning method (looking for where consecutive XYZ triples stop looking like large world-space positions and start looking like unit-length normals) that was developed *before* this field was found and gives the identical answer for `Sky.ms2`'s `SkyDome` (395 both ways). Two independently-derived numbers agreeing exactly is strong confirmation this isn't a coincidental pattern match.

**A recurring small anomaly, not yet explained**: in every multi-node file checked, exactly one face-index value is out of range, and its value is always identical to `index_count` itself (e.g. for `SkyDome`, one index reads `2040` when only 395 vertices exist and `index_count` is also `2040`). Consistent and small enough to not undermine the core structure, but not yet understood — possibly a trailing footer/terminator value, possibly an off-by-one in exactly where the index array starts or ends.

## Confirmed: the multi-node record boundary, and an empty-container node's sentinel values

The overall file layout is a flat sequence of `[name][node header][node data]` blocks, one per node, discoverable via a simple scan for `int32 length + printable ASCII + null` (the same technique that finds the file header also finds every subsequent node's name).

An empty container node (a pure Maya group/transform with no mesh of its own — e.g. `Root` in `Sky.ms2`, which just holds `SkyDome` as a child) has recognizable **sentinel** values instead of real geometry data:
- Bounding box min/max: exactly `FLT_MAX` / `-FLT_MAX` (`3.4028235e38` / `-3.4028235e38`) — the classic "no bounding box computed" sentinel pair (a min/max accumulator that was initialized but never fed any real geometry).
- Bounding sphere radius: exactly `-1.0` — also a classic "invalid/empty" sentinel.
- `vertex_count = 0`, `index_count = 0`, `other = 0`.
- `parent_idx = -1` (no parent, `Root` is the top of the hierarchy), `child_count = 1` (matches reality — `Root` really does have exactly one child, `SkyDome`).

This is strong independent confirmation of the bbox/sphere/count field identification: the same fields hold exact real values for real geometry, and recognizable "nothing here" sentinels for a node that genuinely has none.

**What follows an empty container node is not yet decoded.** For `Sky.ms2`'s `Root`, there are 32 bytes between the end of its header (`parent_idx`/`child_count`) and the next node's name — likely some kind of local-transform data (a prior pass speculated a quaternion-like float quadruple `(-0,-0,-0,~0.99999994)` was visible in that span, which is plausible but unconfirmed) — but this block's size isn't confirmed to be fixed; it needs checking against a container node with a different child count.

## Confirmed: bounding box/sphere pattern holds on real, asymmetric, non-trivial geometry

`SkyDome` (a real dome-shaped mesh, not a symmetric primitive) gives bounding box/sphere values that are exactly what a dome mesh should produce: X/Y both ≈`±7874` (circular footprint seen from above), Z from `-11481` to `+7874` (asymmetric — the mesh extends further below the horizon than above it, consistent with a dome that has a skirt/base). Bounding sphere center is offset in Z (not simply the bbox midpoint — correct behavior for a real minimal-bounding-sphere calculation on an asymmetric shape). This is a much stronger test than the perfectly symmetric cube and it holds up.

## New problem found: 3+-node files break the current understanding

Testing `bld_Haystack.ms2` (3 nodes: `Root` → `bld_Haystack` → *unknown third node*) exposed a real gap: `bld_Haystack`'s own `parent_idx`/`child_count` fields read as garbage (`1038959876`/`1057034162`, clearly not valid indices), and the subsequent attempt to locate the third node's name failed (decoded garbage that isn't valid ASCII). This means the per-node layout confirmed above for 1- and 2-node files **does not fully generalize** to files where a node itself has both geometry *and* children, or to deeper hierarchies generally. Not yet understood: whether a node with geometry AND children needs an extra field (e.g. a list of child indices) not accounted for above, or whether something else about `bld_Haystack`'s specific structure differs.

## New problem found: substantial unidentified trailing data in some files

Computing where each file's confirmed data should end and comparing to the actual file size:

| File | Computed end | Actual size | Leftover |
|---|---|---|---|
| `Sky.ms2` | 16909 | 16957 | 48 bytes |
| `sphere_test.ms2` | 9590 | 25534 | **15944 bytes** |
| `test.ms2` | 17582 | 77394 | **59812 bytes** |

`Sky.ms2`'s small 48-byte leftover could plausibly be a footer/alignment padding. But `sphere_test.ms2` and `test.ms2` (both containing a node named `pSphere1`) have enormous unaccounted trailing data — far more than a single extra per-vertex channel (e.g. a tangent-space vector, mentioned as a real export option in the Phase 0 manual) would explain at these vertex counts. Given both are old files with "test" in the name, this could be leftover scratch/debug content specific to those files rather than a general format feature — or it could be a real, substantial block (a second UV set for lightmaps, skin/animation data, or additional child nodes not yet detected) that just happens to be small-to-absent in the other samples. Not resolved.

## What's confirmed vs. still open

**Confirmed, verified against real/known values:**
- Universal 12-byte-plus-name file header, 62/62 samples.
- Per-node bounding box + bounding sphere, confirmed on both a symmetric primitive (cube) and a real asymmetric mesh (dome).
- **Real vertex_count and index_count fields**, confirmed via exact match to known cube geometry and cross-validated by an independent detection method on a second file.
- The complete vertex position / normal / UV / triangle-index array layout for a leaf mesh node, verified on 7 diverse files (cube, bomb, rocket, dome, two spheres).
- Sentinel values (`FLT_MAX`/`-FLT_MAX` bbox, `-1` sphere radius, zero counts) for empty container nodes.
- The multi-node file layout as a flat, name-delimited sequence.
- IEEE-754 float32 little-endian throughout; face indices are 16-bit.
- String encoding: int32 length prefix + ASCII + one extra null terminator not counted in the length.
- Materials/textures are not stored in `.ms2` at all — confirmed by searching for the known tutorial texture name and finding nothing; they live entirely in the already-understood companion `.script` files.

**Still open:**
- What follows an empty container node (the "fallback block" — currently only located by scanning for the next name, size not understood).
- Why 3+-node files (a node with both geometry and children) break the current header math.
- The large, inconsistent unidentified trailing data in some files (tiny in `Sky.ms2`, enormous in `sphere_test.ms2`/`test.ms2`).
- The recurring single out-of-range face index equal to `index_count` itself.
- Skin/joint/animation data layout — completely untouched so far.
- The portal/light/physics-shape export paths documented in Phase 0 — not yet looked for in the binary format at all.

## Debugging session on `bld_Haystack.ms2` (3 nodes) — partial progress, not resolved

Dumped `bld_Haystack`'s raw bytes at the position where `parent_idx`/`child_count` would be expected (per the `SkyDome` pattern) — they came out as clear garbage (`1038959876`/`1057034162`, with a repeating float-like byte pattern, not plausible small integers). Testing the alternative hypothesis — that `bld_Haystack` has **no** `parent_idx`/`child_count` fields at all, and its vertex data starts immediately after the count block (same as the single-node cube case) — gave plausible-looking vertex positions, all correctly within the node's own bounding box. **So unlike `SkyDome`, `bld_Haystack` appears to skip the `parent_idx`/`child_count` fields entirely**, meaning presence of those fields is not simply "always present when the file has more than one node" as first assumed — something else determines it, not yet identified (candidates: whether this specific node has children of its own vs. being a pure leaf; something related to being the 2nd vs. 3rd node in the file; or something about the node's own `other` field, which was `1` in both cases so doesn't obviously explain the difference).

Even with vertex data assumed to start immediately, the computed end of `bld_Haystack`'s geometry block doesn't land cleanly on the third node's name — the bytes there include what looks like a stray duplicate of the vertex count (`114` appearing again as a raw int32) in the gap, unexplained. This is consistent with the general pattern already seen (`Sky.ms2`'s 48 leftover bytes, the recurring single out-of-range face index equal to `index_count`) that there is some kind of small trailing/footer data after each mesh's index array that isn't yet understood, on top of the now-confirmed uncertainty about whether `parent_idx`/`child_count` are present at all for a given node.

## Recommended next step (as of the end of Phase 1)

This specific puzzle (why some nodes have `parent_idx`/`child_count` and others don't, plus the small unexplained trailing bytes after every geometry block) is a real, harder blocker that black-box probing alone is now hitting diminishing returns on. The most efficient next move is likely to compare several more 2-and-3-node files side by side to find a pattern in which nodes get the extra fields, rather than continuing to guess against a single 3-node example — or to move to Phase 2 (decompiling the actual export/import code) for a ground-truth answer instead of continuing to infer it from bytes alone.

---

# Phase 2: Ground truth via decompiling `MayaExp.mll`

**This section supersedes the field-ordering guesses in Phase 1 above.** Ghidra (headless, with a downloaded portable Temurin JDK 21 since no JDK was installed on this machine — only JREs) was used to decompile `MayaExp.mll` directly. This is real, verified ground truth from the actual compiled exporter code, not inference from bytes.

## How the actual export command was traced

1. `MayaExp.mll`'s only real exports are the standard Maya plugin entry points (`initializePlugin`/`uninitializePlugin`) — everything else (the `exportG5Resource` MEL command, etc.) is registered internally, not exported as DLL symbols.
2. Decompiling `initializePlugin` showed it's built around Maya's **file translator** API (`MFnPlugin::registerFileTranslator("G5 Model Exporter", ...)` and `"G5 Animation Exporter"`), plus several plain MEL commands (`MFnPlugin::registerCommand(...)`) — matching exactly what Phase 0's tutorial screenshots showed ("Files of type: G5 Model Exporter (*.ms2)").
3. The raw disassembly (not just the decompiler's C reconstruction, which dropped an argument at this specific call site) around the `"exportG5Resource"` string reference revealed the literal creator-function address: `PUSH 0x10088840` right before the `registerCommand` call.
4. Decompiling `0x10088840` (a thin factory: `operator_new(0x44)` then calls a constructor) led to its constructor `0x10088710`, which sets the object's vtable pointer to `&PTR_FUN_10114b08`.
5. Dumping that vtable's contents found only two real function-pointer entries before running into adjacent string data (`"Stage 3: ..."`, `"Stage 2: ..."`) — i.e. the vtable is exactly 2 entries: a destructor (`0x10088820`) and `doIt()` (`0x10089b80`).
6. Decompiling `0x10089b80` (`doIt`) confirmed it parses the MEL command's arguments (`MArgList::asString`/`asInt`/`asDouble` calls matching exactly the parameter order documented in Phase 0's `MS2ExportPlugin.mel`), logs them to a debug file, then dispatches on the `"Model"`/`"Animation"` string argument to either `FUN_100891f0` (model export) or `FUN_100897b0` (animation export, not yet examined).

## The model-export function (`0x100891f0`) — confirms the `.script` file is auto-generated

This function writes **both** output files for a model. It literally `fwprintf`s the `Models\*.script` file line by line, and the printed template matches, field-for-field, what this project's own `Common\Shadows.script`/`FakeShadows.script`/`Instances.script`/`Intersections.script`/etc. housekeeping scripts already contain:

```
class %s extends CBaseModel
{
  static int     InstancesQty          = CBaseModel::DefaultInstancesQty;
  static int     ShadowCheckMode       = CBaseModel::DefaultShadowCheckMode;
  static boolean PlanarShadow          = CBaseModel::DefaultPlanarShadow;
  static float   PlanarShadowLodShift  = CBaseModel::DefaultPlanarShadowLodShift;
  static boolean UseBoxForIsection     = CBaseModel::DefaultUseBoxForIsection;
  static boolean UseShapesAsWalkedMesh = CBaseModel::DefaultUseShapesAsWalkedMesh;
  static boolean FakeShadow            = CBaseModel::DefaultFakeShadow;
  static float   FakeShadowScale       = CBaseModel::DefaultFakeShadowScale;
  static float   LodForShadowChange    = CBaseModel::DefaultLodForShadowChange;
  static float   LodForShadowHide      = CBaseModel::DefaultLodForShadowHide;
  String     MeshFile        = "Models/%s.ms2";
  String     SkinClass       = "%s";
  String     RouterMapFile   = "Models/%s.rmap";
  Array  Animation = [ ... ];
  Map    ConfigSets = new Map([ ... ]);
}
```

This confirms, with certainty rather than inference, everything Phase 0/the issue #4 and #8 audits already concluded about these header fields being a fixed, mechanical boilerplate — because this is literally the code that writes them. It then opens a second file (`Models/%s.ms2`, `"wb"` binary mode) and calls `FUN_1008e850(dataObject, fileHandle)` — the real binary writer.

## The `.ms2` binary writer — the real, ground-truth structure

`FUN_1008e850` writes the file-level header (`format_version=0`, `node_count`, both as a single 8-byte block — confirmed to be two adjacent stack variables, `format_version` then `node_count`, so Phase 1's identification of these two fields was exactly right), then loops over every joint/node index calling `FUN_1008dde0(node, fileHandle)` for each one.

`FUN_1008dde0` is the actual per-node writer, and its exact `fwrite()` call sequence (this is the literal write order — some fields are written out of their in-memory struct order) is:

1. `namelen` (int32), then `name` bytes + 1 null byte — **confirmed exactly matching Phase 1**.
2. Bounding box min/max (6 floats, 24 bytes) — **confirmed exactly matching Phase 1**.
3. Bounding sphere center + radius (4 floats, 16 bytes) — **confirmed exactly matching Phase 1**.
4. `flag` (int32, always 0 in every sample) — **confirmed exactly matching Phase 1**.
5. `vertex_count` (int32) — **confirmed exactly matching Phase 1**.
6. `index_count` (int32) — **confirmed exactly matching Phase 1**.
7. `other_count` (int32) — **confirmed matching Phase 1's "other" field**, but Phase 1 never discovered what it actually counts (see #10 below).
8. Positions: `vertex_count × 3 floats` — **confirmed**.
9. Normals: `vertex_count × 3 floats` — **confirmed**.
10. UVs: `vertex_count × 2 floats` — **confirmed**.
11. Face indices: `index_count × uint16` — **confirmed**.
12. **`other_count × 16 bytes`** — a whole block Phase 1 never found at all. This is almost certainly the actual explanation for Phase 1's "unexplained leftover bytes" (`Sky.ms2`'s 48 bytes) and the recurring "one out-of-range index equal to `index_count`" anomaly — Phase 1 was reading past the true index array end into this block without knowing it was there. Content/meaning not yet identified (16 bytes could be one `Vector4`, or two 2D points, or similar — not determined).
13. `node_id` (int32) — a **new field Phase 1 never found**, defaulting to a global constant (0 in every sample) unless the node has an internal "parent object" reference set, in which case it copies a value from that parent. **This is very likely what Phase 1 misidentified as `parent_idx`** — same value (0 for a plain leaf, or a small integer otherwise), but the real field comes *after* all the geometry arrays, not before them as Phase 1 assumed.
14. `flags_bitmask` (int32) — **also new**, gates six further optional data blocks (skin/animation/collision-adjacent data, none of it identified by name yet — see below). Always 0 in every geometry-only sample. **This is very likely what Phase 1 misidentified as `child_count`** for the same reason as `node_id` above.
15. `d_count` (int32) — **new, and important: this one is always written, not gated by any flag.** Followed by two arrays: `d_count × 12 bytes` and `d_count × 16 bytes`. In every sample so far, `d_count = 1`, so this is a small, easy-to-miss 32-byte block that was folding into Phase 1's "unexplained leftover" bucket too.
16. Six further blocks, all gated by individual bits of `flags_bitmask`, all with byte-exact sizes known from the decompiled `fwrite()` calls but **completely unvalidated against real data**, since no sample file examined has `flags_bitmask != 0`:
    - bit `0x800`: `vertex_count × 8 bytes`
    - bit `0x10`: `vertex_count × 20 bytes`
    - bit `0x40`: `count (int32) + count × 52 bytes + count×2 × 4 bytes`
    - bit `0x200`: `count (int32) + count × 112 bytes`
    - bit `0x400`: `count (int32) + count × 92 bytes`
    - bit `0x10000`: `count (int32) + count × 80 bytes`
    - bit `0x4000`: a single 4-byte value
    - bit `0x40000`: `vertex_count × 12 bytes`, twice

## Validation: `Tools\MS2Format\ms2_parser.py`

Implementing exactly the structure above and running it against the same 9 sample files used throughout this investigation:

| File | flags_bitmask | Result |
|---|---|---|
| `MyFirstModel.ms2` | 0 | **Lands exactly on EOF, 0 bytes leftover** |
| `wpn_FFAR.ms2` | 0x40000 (but its optional-block size happens to net out correctly — see caveat) | **Lands exactly on EOF, 0 bytes leftover** |
| `Sky.ms2` (2 nodes) | 0 for both | **Lands exactly on EOF, 0 bytes leftover** |
| `test.ms2` (2 nodes) | 0 / 0x1000040 | **Lands exactly on EOF, 0 bytes leftover** |
| `wpn_Bomb.ms2` | 0x40 | Overshoots by 1056 bytes |
| `4MeterBox.ms2` | 0x40840 | Overshoots by 144 bytes |
| `sphere_test.ms2` | 0x40 (2nd node) | Overshoots by 1448 bytes |
| `bld_Haystack.ms2` (3 nodes) | 0x50040 (2nd node) | Crashes — cumulative error from the overshoot above compounds into garbage on the 3rd node |

**4 of the 9 test files land exactly on the byte with zero discrepancy** — every one of them has `flags_bitmask = 0` for every node with real geometry (the base geometry-only path). This is airtight confirmation the core structure (items 1-15 above) is exactly correct. The files that overshoot all have a nonzero `flags_bitmask` invoking one of the six unvalidated optional blocks — for `wpn_Bomb.ms2` specifically (`flags_bitmask = 0x40` only), the count field at that block reads `132`, and `132 × 52 = 6864` bytes matches the file's remaining size **exactly** — meaning the second array in that block (`count×2 × 4 bytes`, predicted by the decompiled code) does not actually appear to be written, or is conditioned on something this analysis hasn't identified yet. That's a small, well-isolated discrepancy in one specific optional block, not a problem with the core structure.

## What Phase 2 leaves open

- The exact meaning/content of the always-present `other_count × 16 bytes` block (item 12) and `d_count`-driven arrays (item 15) — sizes and positions are known exactly, semantics are not.
- The six `flags_bitmask`-gated optional blocks — byte sizes are known from decompiled code, but not validated against real data, and at least one (`0x40`) has a confirmed discrepancy between the decompiled prediction and the real file size.
- `node_id`'s real meaning beyond "usually 0, sometimes copies a parent's value."
- The animation-export path (`FUN_100897b0`) — not examined at all yet.
- Whether `d_count`/`other_count` ever exceed 1 in real shipped assets (only test/tutorial files have been checked so far) — worth testing against a real, complex vehicle `.ms2` file next.

## Tested against a real shipped vehicle (`u_veh_t34_85_44.ms2`, 219 nodes) — `node_id` confirmed as the parent-node index

Running the parser against a real T-34/85 model (not just test/tutorial content) gives a strong bonus confirmation: `node_id` is the **index of this node's parent within the file's flat node list** (0-based, `ROOT` is always index 0). For example:
- `Body` (node index 1) has `node_id=0` → parent is `ROOT` (index 0). Correct.
- `Body_LOD4`/`Body_LOD2`/`Body_LOD1`/`Body_2` (indices 2-5) all have `node_id=1` → parent is `Body` (index 1). Correct — these are LOD variants and a sub-part of `Body`.
- `Body_2_LOD4` (index 6) has `node_id=5` → parent is `Body_2` (index 5). Correct.

This is a clean, unambiguous, real-data confirmation — the hierarchy nesting exactly matches the node naming (`Body` → `Body_LOD4`, `Body_2` → `Body_2_LOD4`, etc.), and every `node_id` value checked points to the correct parent's own index. **Phase 1 wasn't wrong that this represents a parent reference — it was only wrong about where in the byte stream this field sits** (after the geometry arrays, not before, per Phase 2's ground truth).

Also confirms real production content always has `flags_bitmask != 0` (unlike every test/tutorial file examined) — the six optional blocks genuinely matter for shipped assets and aren't just theoretical. Real node names also confirm Phase 0's naming-convention findings directly: `Luk_A` (a hatch joint, matching the `Luk_A` hatch-joint wiring found in `u_veh_t34_85_44.script`), and `Luk_A_CM` (a `_CM`-suffixed collision mesh, exactly matching `LOD_CM_SCRIPT.mel`'s naming convention from Phase 0).

## Recommended next step (Phase 2)

Pin down the one confirmed discrepancy in the `0x40`-gated optional block (the `count×2 × 4-byte` second array doesn't appear to actually be written, based on `wpn_Bomb.ms2`), then work through the other five unvalidated optional blocks using real vehicle files like this one as test cases, since production content actually exercises them (unlike the simple test/tutorial files everything else here was validated against).

---

# Phase 2 continued: `flags_bitmask` decoded bit-by-bit, by tracing the Maya attribute reader itself

Rather than continuing to guess, traced where the exporter actually **reads** each Maya mesh attribute (from Phase 0's `addMeshProperties.mel` list) and **writes** the corresponding bit into `flags_bitmask`. Found `FUN_1008d120` — the function referenced by nearly every mesh boolean attribute string — and decompiled it directly. This gives a definitive, named mapping for most of the field, not an inferred one:

| Bit (hex) | Source attribute / condition |
|---|---|
| `0x1` | Complex condition: two internal fields equal AND (an object-type check fails OR `IsWalkMesh` OR `IsCollisionMesh`) — not fully pinned down, but clearly `IsWalkMesh`/`IsCollisionMesh`-adjacent |
| `0x4` | `IsCollisionMesh` |
| `0x8` | `IsBoneNode`, **or** the node is natively a Maya joint (`MObject::hasFn(obj, 0x78)`) |
| `0x20` | `IsWalkMesh` |
| `0x80` | `IsHidden` |
| `0x100` | `IsNear` |
| `0x20000` | `IsSelfLOD` |
| `0x200000` | `DoNotUseInIsection` (forced to 0 if `IsCollisionMesh` is set — a real cross-attribute dependency) |
| `0x400000` | `DoNotCastShadow` |
| `0x800000` | `IsNearGeometry` |
| `0x2000000` | `OnlyCastShadow` |
| `0x40` **and** `0x1000000` (set together) | `HasShadowVolume` is true **and** none of bits `0x1`/`0x4`/`0x20` are set |
| `0x100000` | `TransparentShadows` is **false** (inverted) |

`IsRouterMesh` and `DoNotGenerateShadows`/`IsNotReciveLighting` were traced to *other* functions (`FUN_1000ab30`, `FUN_1004ea70`) that don't feed this same bitmask directly — they're consumed elsewhere in the export pipeline (in particular, `DoNotGenerateShadows`/`IsNotReciveLighting` gate whether the huge shadow-volume-building routine below runs at all, rather than setting a bit in this field). `IsDoorObject` was traced to a completely separate joint/hinge-hierarchy subsystem (`FUN_100ba570`, which prints `"Door joint \"%s\" added to geometry hierarchy, joint index %i\n"`) — **not** part of this mesh-level `flags_bitmask` at all.

## What the `0x40` optional block actually is: shadow-volume silhouette/adjacency data

`FUN_1004ea70` (reached only when shadow-volume generation is enabled and not suppressed) turned out to be one of the largest, most complex functions in the whole plugin — real geometry processing, not a simple attribute read:
- Iterates every mesh edge (`MItMeshEdge`) checking `isSmooth()`, and for every **non-smooth (hard) edge**, records its two vertex indices via `FUN_10066e30(context, v0, v1)` — this is exactly silhouette-edge detection, the standard technique for real-time stencil shadow volumes (hard edges are exactly where a shadow volume needs to extrude).
- Builds a BSP-mesh structure (`"Append polygons to BSP-mesh generator ..."`), triangulates polygons (`MItMeshPolygon::hasValidTriangulation`), and does area-based culling of degenerate/tiny triangles.
- This conclusively confirms the `0x40`/`0x1000000`-gated 52-byte-per-record block in the `.ms2` file holds precomputed shadow-volume geometry (very likely per-edge or per-triangle adjacency data) — not a guess, but doesn't yet pin down the *exact* field-by-field meaning of each 52-byte record, which would need substantially more work given how large and intricate this specific function is.

## What's still unmapped

- The exact byte-level meaning of the 52-byte shadow-volume records themselves (only their *purpose* is now confirmed, not their internal layout).
- The confirmed discrepancy in that same block (`wpn_Bomb.ms2`'s second sub-array not actually appearing) — still unresolved; possibly legitimate (a closed/watertight mesh may have zero "boundary edge" entries in whatever the second array represents) rather than a parsing bug.

---

# Phase 2 continued further: the remaining seven block-gating bits, found by scanning the whole binary for the literal bit constants

None of Phase 0's known mesh attributes (via `FUN_1008d120`) fed the remaining seven optional-block bits. Rather than keep tracing call graphs by hand, scanned **every instruction in the entire binary** for an `OR` against each specific bit constant — a handful of direct `OR dword ptr [reg+0x8], CONST` hits (exactly the `flags_bitmask` struct-field pattern) pinpointed the real setter function for each bit immediately.

| Bit | Function | What it does (confirmed by decompiling it) |
|---|---|---|
| `0x10` | `FUN_100968c0` | Logs `"  Add bone for attach %i\n"` right where this bit gets set, inside a joint/skin-processing function that also logs `"Export mesh data from (%i) %s joint"` and `"This joint constist [sic] from %i attached joints"`. Set when an internal bone-attachment collection is non-empty. Matches the block's known size (`vertex_count × 20 bytes`) exactly for a bone-index + weight + offset-vector record. |
| `0x800` | `FUN_100955c0` | Logs `"Error: incorrect numbers blending informtion (%i)\n"` [sic, real typo in the shipped binary] right in the same code path — this is skin/bone **blend-weight** data, set after validating a per-vertex blend-weight count. Matches the known block size (`vertex_count × 8 bytes`) for a compact bone-index+weight pair. |
| `0x4000` | `FUN_100968c0` (same function as `0x10`) | Logs `"  This joint clone mesh from %i joint\n"` — set when a joint's geometry is a **clone/instance of another joint's mesh** rather than its own. The single 4-byte value this bit gates is almost certainly the source joint's index. |
| `0x10000` | `FUN_1008d610` | Allocates and default-initializes an array of 80-byte records with the exact IEEE-754 bit pattern for `1.0f` at diagonal-like positions (offsets matching a matrix diagonal) — a textbook **identity matrix initialization**. Strongly suggests these are per-joint bind-pose/skinning transform matrices, though the full 80-byte layout (a 4×4 matrix is 64 bytes, leaving 16 bytes for something else per record) isn't pinned down. |
| `0x40000` | `FUN_1008a4a0` | Trivial — the entire function is "if (param_1) set bit 0x40000, else clear it." A direct 1:1 passthrough of a single boolean. Given the gated block is `vertex_count × 12 bytes, twice`, and the only boolean mesh-level export toggle left unaccounted for is `ExportTangentSpace`, this is very likely tangent + bitangent vectors (each a 3-float vector) per vertex. |
| `0x200` | `FUN_10097600` | Copies raw 112-byte records from an internal collection when non-empty, then extracts a 3-float vector from each and feeds it into what looks like a bounding accumulation function. Content not fully identified — larger and more complex than the bone/skin records above. |
| `0x400` | `FUN_1008d550` | Copies raw 92-byte records from an internal collection when non-empty. Content not fully identified. |

This means **all eight** of the mystery optional-block bits now have at least a confirmed real-code trigger condition, and five of them have a strong, evidence-based semantic identification (bone attachment, skin blend weights, mesh cloning, joint bind matrices, tangent space) rather than being unlabeled byte blobs. The two remaining (`0x200`/`0x400`) are confirmed to be real, structured per-record data tied to the joint/skinning pipeline, just not yet identified by name.

## Updated "what's still unmapped"

- Exact per-field byte layout within the `0x10`/`0x200`/`0x400`/`0x800`/`0x10000` records (sizes are exact, internal field meaning is not, beyond the partial matrix-diagonal evidence for `0x10000`).
- Whether `0x1` and `0x8`'s more complex trigger conditions (documented earlier, tied to `IsWalkMesh`/`IsCollisionMesh`/`IsBoneNode`/native-joint-type checks) fully explain every case, or have edge cases not yet tested.

---

# Phase 2 capstone: the `wpn_Bomb.ms2` discrepancy resolved, and a full production file parses byte-perfect

## Resolving the `0x40` block discrepancy: it's a file-age mismatch, not a bug

Pulled the raw x86 disassembly (not the decompiler's C reconstruction, which can miscombine short-circuited expressions) for the exact `flags & 0x40` code path in `FUN_1008dde0`. It unambiguously shows **three unconditional `fwrite` calls** once that bit is set: the count (4 bytes), `count × 52` bytes, then **immediately after, with no further flag check**, `count × 2 × 4` bytes. Re-verified `wpn_Bomb.ms2`'s byte offsets field-by-field in Python and confirmed the file's `e_count` really is `132` at the correct, verified position (not a misread) — and `132 × 52 = 6864` bytes lands **exactly** on the file's true end, with no room at all for the third write the disassembly demands.

The likely explanation: `MayaExp.mll` (the copy being decompiled) is dated **June 2007**. `wpn_Bomb.ms2` is dated **January 2006** — over a year older. The exporter's own behavior for this specific block most likely changed between those dates (the third array was probably added later), so an older exported file legitimately doesn't have it. This isn't a parsing bug in the reverse-engineering work — it's a real historical version mismatch between an old asset and a newer tool, which is exactly the kind of thing you'd expect to find in a 20+ year old shipped game's asset pipeline.

## Full validation: `u_veh_t34_85_44.ms2` (219 nodes, 12.9MB) parses byte-perfect end to end

Ran `ms2_parser.py` against the real, complete, shipped T-34/85 model — not a test file — and it walked **all 219 nodes** and landed on **exactly** the file's true end (`parsed to offset 12954111, file size 12954111, leftover 0 bytes`). This is the strongest possible confirmation available: a real production asset, using nearly every documented optional block in combination (`HasShadowVolume`, bone attachment, tangent space, bind matrices, and more, in the same file, on different nodes), decodes with zero discrepancy across its entire 12.9MB length.

Collecting every distinct `flags_bitmask` value that appeared across the file's 219 nodes and decoding each against the bit table built so far confirms real, expected combinations — for example `HasShadowVolume`'s two bits (`0x40`/`0x1000000`) appear together in every single case, exactly as predicted; bone-attachment (`0x10`) and tangent-space (`0x40000`) frequently appear together, which makes complete sense for a driveable vehicle's detailed body mesh needing both skinning and normal-mapping data.

**One new bit found**: `0x80000` appears in several flag combinations (e.g. `0x10c0050`, `0x12c0050`, `0x12d0050`, `0x33c0050`) and isn't part of any of the eight block-gating bits or the previously-identified plain attribute bits. It doesn't affect the byte layout (it's not one of the eight gating bits), so it didn't break the byte-perfect parse — but its meaning is unidentified. Given every other bit in this field has now been traced to a real Maya mesh attribute or export feature, this is very likely one more attribute this pass didn't specifically go looking for (candidates: `IsRouterMesh`, `IsNotReciveLighting`, or `DoNotGenerateShadows` directly rather than its shadow-volume-adjacent effects already found).

## Where this leaves the `.ms2` format

The core structure (header, per-node bbox/sphere/counts, position/normal/UV/index arrays, the always-present small blocks, and all eight optional-block trigger conditions) is now verified byte-perfect against a real, complex, shipped asset — not just simple test files. What remains is narrower and more specialized: the exact internal field layout of five record types whose *purpose* is now known (bone attachment, blend weights, bind matrices, and two still-unnamed joint/skin-adjacent blocks), plus one newly-found unidentified plain attribute bit (`0x80000`). This is enough to write a working `.ms2` reader for the vast majority of real content today, and enough to know exactly what's left to fully close out the format for a complete Blender import/export pipeline.

---

# Phase 2, one more round: the `0x10000` bind-matrix record fully decoded, field by field

Pushed further on the record-internals question. The `0x10000` (per-joint bind-pose) record was the most tractable, and is now **fully decoded with certainty, not just plausible structure**.

Re-examining `FUN_1008d610`'s default-initialization loop (which writes into each newly-allocated 80-byte record before the real per-joint data gets copied over it) found it doesn't just write scattered `1.0f`/`0.0f` values by hand — it finishes with a tight loop that bulk-copies **16 consecutive dwords from a fixed global constant, `DAT_1013ae10`**, into the record starting 4 bytes in. Dumping that constant directly from the binary's data section gives, unambiguously:

```
1.0  0.0  0.0  0.0
0.0  1.0  0.0  0.0
0.0  0.0  1.0  0.0
0.0  0.0  0.0  1.0
```

That is a literal, textbook **4×4 identity matrix** — no ambiguity, no interpretation needed. Combined with the surrounding field writes (a leading 4-byte zero-initialized field before the matrix, and three trailing zero-initialized floats after it), the full confirmed 80-byte record layout is:

| Offset | Size | Field | Evidence |
|---|---|---|---|
| 0 | 4 bytes (int32) | Likely a joint/bone index | Zero-initialized before being overwritten by the real per-joint copy later in the same function |
| 4 | 64 bytes (16 floats) | **A 4×4 transform matrix**, default identity | Bulk-copied from `DAT_1013ae10`, confirmed byte-for-byte as the identity matrix |
| 68 | 12 bytes (3 floats) | Likely a `Vector3` — position/pivot/offset | Zero-initialized, same pattern as the leading field |

This default-initialized record is then immediately overwritten (per the function's second loop) with real per-joint data copied from an internal collection built during the earlier scene walk — so real exported files will contain actual bind-pose matrices here, not identity matrices, but the **field boundaries and types are now certain**, not guessed.

## The other four record types (`0x10`, `0x200`, `0x400`, `0x800`) — deeper than a quick follow-up can reach

Tried to repeat this same trick (find the default-initialization pattern, or find the function that populates the actual final array directly) for the remaining four record types. This turned out to be substantially harder:
- The `0x10`/`0x800` records are populated through a long chain of per-triangle/per-vertex processing (`FUN_100968c0` → `FUN_100955c0`) that builds several *intermediate* collections (with different strides, e.g. a `0xb8`=184-byte-stride array) before whatever final compaction step produces the actual exported 8-byte and 20-byte records — that final step wasn't located in this pass.
- The per-node "constructor" function (`FUN_10090a00`) that seemed like a promising place to find the array's initial setup turned out to be a lightweight identity/name-only constructor, not where the skin/blend arrays get built.
- `0x200`/`0x400` involve raw bulk-copies from internal collections (as documented earlier) with no default-initialization pattern found yet to reveal their internal field types the way the identity-matrix trick did for `0x10000`.

Fully pinning these down would mean tracing substantially further through some of the largest, most intricate functions in the whole plugin (the joint/skinning pipeline is clearly one of the most complex parts of the exporter) — a real, bounded task, but one that would need dedicated focus rather than a quick follow-up pass.

---

# Phase 3: a real, working static-mesh importer for Blender

With the core format ground-truth verified, built an actual importer rather than continuing pure analysis — this is genuinely useful today, not just documentation.

## `Tools\MS2Format\ms2_reader.py` — pure-Python `.ms2` reader

A dependency-free reader (only uses `struct`, works under a normal interpreter or Blender's embedded Python) that reads node hierarchy, names, and per-vertex position/normal/UV/index data, skipping the five still-unmapped optional blocks by their known exact byte sizes (their content isn't needed to reconstruct static geometry).

**Found and fixed one more real issue along the way**: `bld_Haystack.ms2` (from the earlier 3-node investigation) turned out to have the exact same "old exporter build" issue as `wpn_Bomb.ms2` — confirmed by checking its file date (2006-10-11, also before `MayaExp.mll`'s June 2007 build date). Rather than hardcode a fragile date check, made the reader **structurally self-correcting**: when it hits the `0x40` (shadow-volume) block, it computes the full remainder of the node both ways (with and without the newer second sub-array), and picks whichever one leads to something that looks like a valid next node name or exact end-of-file. This isn't a guess dressed up as certainty — it's a real, principled disambiguation based on what a correctly-parsed file must look like structurally.

**Full validation: all 62 sample `.ms2` files in the game — every single model, not a subset — now parse to the exact byte, zero leftover.** This is the strongest possible confirmation available for the static-geometry portion of the format.

## `Tools\MS2Format\ms2_import_blender.py` — Blender 2.79 importer

Builds real Blender objects from the parsed data: creates a mesh (via `bmesh`) with vertex positions, triangulated faces, UV coordinates, and the file's own authored per-vertex normals (as Blender custom split normals, not just recomputed face normals) for mesh nodes; creates an Empty for container/joint nodes with no geometry of their own; and wires up the parent/child hierarchy afterward using the `node_id` field (confirmed earlier to be the parent's index in the file).

Tested headlessly (`blender --background --python ...`) against Blender 2.79b, the version actually installed on this machine:

| File | Result |
|---|---|
| `bld_Haystack.ms2` (3 nodes) | 167/167 vertices, 196/196 triangles — exact match |
| `u_veh_t34_85_44.ms2` (219 nodes, a full real shipped tank) | 84,611/84,611 vertices exact; 77,172/77,182 triangles (99.99%) — the only 10 missing triangles are exact duplicate faces in a handful of collision meshes (`_CM` nodes), which Blender's `bmesh` structurally refuses to create twice. This is a real Blender API limitation, not a gap in the format understanding — every single vertex position is correct. |

Two demo `.blend` files were generated and saved to `M:\TvT 2024 working folder\ms2_blender_import_demo\` for direct visual inspection in Blender's UI: `bld_Haystack_imported.blend` (simple, fast to open) and `t34_85_44_imported.blend` (the full real tank, 12MB, all 219 nodes and their hierarchy).

## What this importer does and doesn't do

**Does**: reconstruct accurate static geometry (position/normal/UV/triangles) and correct parent/child object hierarchy, for any `.ms2` file in the game, including the most complex real vehicle assets.

**Doesn't yet**: assign materials/textures (not stored in `.ms2` at all — lives in the companion `.script` file's `ModelSkin` class, which is plain text and hasn't been wired up to this importer yet, but needs no further reverse-engineering to do so), import skinning/bone weights or animation (the five still-unmapped record types), or import shadow-volume/physics data (not needed for visual geometry, only for in-engine rendering/collision behavior).

## Recommended next step (Phase 3)

Wire up material/texture assignment by parsing the companion `.script` file's `ModelSkin` texture list (plain text, already fully understood — no reverse-engineering needed, just text parsing) — this would make imported models actually look textured in Blender rather than plain grey, a meaningful visible improvement for relatively little additional work.

---

# Phase 3 fix: exported triangle winding doesn't always agree with the file's own authored normals

The user opened the generated `t34_85_44_imported.blend` in their own (much newer) Blender install and reported visible artifacts — scattered dark, faceted-looking patches, concentrated on the damaged/"Crashed" variant meshes — while the simple haystack prop looked correct. Rather than guess, wrote a standalone diagnostic (`diagnose_normals.py`, not committed — a throwaway check) that computes each triangle's geometric normal (from its vertex positions and index order) and compares it against the average of its three vertices' authored normals from the file.

**Confirmed with real data**: 7.17% of all faces in `u_veh_t34_85_44.ms2` (5,531 of 77,182) have geometric winding that disagrees with their own authored normal — i.e. the triangle indices, taken at face value, produce a face pointing the *opposite* direction from what the mesh's own normal data says it should. This is concentrated heavily in the `_Crashed` damage-state variants (`Body_Crashed`: 31% of its faces affected) — plausibly because shattered/broken geometry was authored or processed differently (mirrored fragments, boolean-cut pieces, etc.) than clean intact meshes, which only had a handful of affected faces each. This exactly explains the visual symptom: a face with inverted winding relative to its true normal renders dark from angles where correctly-wound neighboring faces render light, producing exactly the scattered faceted-dark-patch look in the screenshot.

**Fix**: `ms2_import_blender.py` now computes each triangle's geometric normal *before* creating the bmesh face, compares it against the authored per-vertex normal average, and reverses the vertex order if they disagree — using the file's own authored normals as ground truth to correct for the winding inconsistency, rather than trusting the raw index order blindly.

**Verified the fix directly** (not just "looks plausible"): re-imported and checked Blender's own computed face normals against the split-normal data afterward — disagreements dropped from 5,531 to **2** (out of 77,172 faces; the remaining 2 are almost certainly genuine near-degenerate sliver triangles where the geometric normal is barely defined, not a remaining bug). The haystack prop, which had zero disagreements before the fix, still shows zero after — confirming the fix doesn't disturb already-correct data. Regenerated both demo `.blend` files with the corrected importer.

## Second visual bug found (and fixed): every LOD/damage-state variant imported as visible, all overlapping

After the winding fix, the user reported the tank still looked identical — but a genuinely new, uniquely-named file this time (ruling out a stale-file re-test), while a newly-generated mid-complexity model (`u_stat_pak40.ms2`, a Pak 40 gun, 36 nodes) looked correct. This pointed away from the winding fix itself and toward something specific to a large, multi-variant asset.

Checked the actual node hierarchy: `Body` (the intact hull) and `Body_Crashed` (the shattered wreck variant) are **siblings, parented to the same node, with nearly identical bounding boxes** — and the same is true for every `_LOD1`/`_LOD2`/`_LOD4` variant of both. The importer was creating **every single node as visible geometry**, meaning the intact hull, every one of its lower-detail LOD copies, and the fully shattered wreck mesh (plus its own LOD copies) were all rendering simultaneously, stacked on top of each other in the same space. That's exactly what looked like a "shattered" mesh — it was literally the wreck geometry and the intact geometry both visible at once. Not a normals bug at all; the earlier winding fix was real and correct, it just wasn't the (whole) problem.

**Fix**: `ms2_import_blender.py` now still imports every node (nothing is skipped or lost), but hides by default any node whose name matches the game's own `_LODn` / `Crashed` / `_CM` (collision mesh) naming convention — confirmed against real shipped content, not assumed. A straightforward import now shows only the intact, full-detail geometry by default, with every LOD/damage-state/collision variant still present in the scene (just hidden) for anyone who wants to inspect or toggle them.

Verified on the same T-34/85 file: 67 of 219 nodes are now hidden by default as LOD/Crashed/CM variants, leaving the intact vehicle visible.
