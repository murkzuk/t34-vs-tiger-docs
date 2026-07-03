# `.ms2` Binary Format — Empirical Findings (Phase 1)

**Date:** 2026-07-03
**Author:** Claude Code (Anthropic), with murkz
**Status:** Active empirical probing, real breakthrough this pass. Everything below is derived from directly reading bytes out of real `.ms2` files and checking the numbers against known geometry — not guessed. A significant correction was made partway through this document's own history (see "Correction" note below) — read that before trusting any offset math from an earlier draft.
**Companion tool:** `Tools\MS2Format\ms2_probe.py` — a research script implementing everything confirmed below.

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

## Recommended next step

This specific puzzle (why some nodes have `parent_idx`/`child_count` and others don't, plus the small unexplained trailing bytes after every geometry block) is a real, harder blocker that black-box probing alone is now hitting diminishing returns on. The most efficient next move is likely to compare several more 2-and-3-node files side by side to find a pattern in which nodes get the extra fields, rather than continuing to guess against a single 3-node example — or to move to Phase 2 (decompiling the actual export/import code) for a ground-truth answer instead of continuing to infer it from bytes alone.
