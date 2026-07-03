# `.ms2` Binary Format — Empirical Findings (Phase 1)

**Date:** 2026-07-03
**Author:** Claude Code (Anthropic), with murkz
**Status:** Early empirical probing. Everything below is derived from directly reading bytes out of real `.ms2` files and checking the numbers against known geometry — not guessed, not inferred from the Maya-side tooling docs. Confidence level is noted per finding.

This is Phase 1 of the plan in `Documentation/T34_vs_Tiger_Maya_Export_Manual(V3).md` Section 11 (GitHub issue #12 — eventual goal is a Blender import/export pipeline). Phase 0 covered the Maya-side authoring metadata; this covers the actual on-disk byte format those attributes get serialized into.

## Method

Started with the two smallest/simplest real `.ms2` files in `Models\`:
- `Landscape_test.ms2` (124 bytes) — a tiny test file, root object named `QuadPatch01`.
- `MyFirstModel.ms2` (1695 bytes) — **the exact cube from the export tutorial's own screenshots** (Section 1 of the Phase 0 manual). We know in advance this is a single default Maya polygon cube, exported with the `bld_Haystack` texture, no animation, no skin, no lights, no portals — about as close to a known-plaintext test case as this kind of format probing ever gets.

All numeric interpretations below were checked with Python's `struct` module, not eyeballed hex.

## Confirmed: universal file header (checked against all 62 sample `.ms2` files, 62/62 match)

Every `.ms2` file starts with:

| Offset | Size | Type | Meaning |
|---|---|---|---|
| 0x00 | 4 bytes | int32 LE | Always `0` in every sample checked — likely a format version or flags field |
| 0x04 | 4 bytes | int32 LE | Scales strongly with model complexity — see table below. Almost certainly a total node/object count for the file |
| 0x08 | 4 bytes | int32 LE | Length (in bytes) of the following name string |
| 0x0C | *namelen* bytes | ASCII | The root object's name, taken verbatim from the Maya scene — e.g. `pCube1`, `QuadPatch01`, `ROOT`, `Root`, `root`, `locator1`, `Bomb`, `Rocket2` |
| 0x0C + namelen | 1 byte | — | A single `0x00` null terminator after the name (not counted in the length field) |

**Evidence for the "node count" field**: checked across all 62 files —

| File | Root name | Node count field | Notes |
|---|---|---|---|
| `MyFirstModel.ms2` / `4MeterBox.ms2` | `pCube1` | 1 | Single default cube |
| `wpn_Bomb.ms2` | `Bomb` | 1 | Single mesh |
| `wpn_FFAR.ms2` | `Rocket2` | 1 | Single mesh |
| `Landscape_test.ms2` | `QuadPatch01` | 1 | Single quad |
| `Sky.ms2` / `sphere_test.ms2` / `test.ms2` | `Root`/`root` | 2 | Small test scenes |
| `bld_Haystack.ms2` | `Root` | 3 | Simple prop |
| `bld_ReloadUSSR.ms2` | `ROOT` | 4 | |
| `u_veh_t34_76_41.ms2` | **`locator1`** (not `ROOT`!) | **14** | See note below — this is the orphaned/cut-content T-34/76 variant |
| `u_veh_t34_76_42.ms2` (the shipped, playable-adjacent sibling) | `ROOT` | 216 | |
| `bld_USRHouseWood.ms2` | `Root` | 320 | Most complex static building |
| `u_veh_PzVI_LATE.ms2` | `ROOT` | 335 | Most complex file overall |

A genuinely interesting side finding: `u_veh_t34_76_41.ms2` — the model already flagged elsewhere in this project's backlog as a "cut content" tank variant with full ballistics stats but no `Units\*.script` gameplay class ever built for it — has a root node named `locator1` instead of the `ROOT`/`Root` convention every other shipped vehicle uses, and a node count of only 14 versus 216-335 for its finished siblings. This is an independent, purely binary-structure-based confirmation of something already suspected from a completely different investigation (auditing `.script` class references) — the model file itself looks structurally unfinished, not just missing its gameplay wrapper.

## Confirmed: bounding volume data immediately follows the name (high confidence — exact numeric match to known geometry)

Using `MyFirstModel.ms2` (the known tutorial cube), the 40 floats immediately after the name+null terminator (starting at file offset 19):

| Floats | Values | Interpretation |
|---|---|---|
| 0-2 | (-0.005, -0.005, -0.005) | Bounding box **min** corner |
| 3-5 | (0.005, 0.005, 0.005) | Bounding box **max** corner |
| 6-8 | (-0.0, -0.0, -0.0) | Bounding sphere **center** (at origin — correct, the cube is centered) |
| 9 | 0.008660... | Bounding sphere **radius** |

The radius value is not a coincidence: for a cube with half-extent 0.005, the circumscribed sphere radius is `0.005 × √3 = 0.0086602540...` — an exact match to 7 significant figures. This confirms floats 0-9 are a bounding box + bounding sphere pair, not a guess.

Floats 10-13 are all zero in this sample (likely a pivot/local-origin field, untested since this cube has no offset pivot — needs a second sample with a non-origin pivot to confirm).

Floats 14 onward are combinations of exactly `±0.005` in various sign patterns — consistent with vertex position data for a cube whose corners are all at `(±0.005, ±0.005, ±0.005)`. A hard-edged cube typically needs 24 vertices (4 per face × 6 faces, since each face needs its own normal/UV even at shared corners) rather than 8 — the data seen so far (26 of an expected ~72 floats for 24 vertices × 3 components) is consistent with this but not yet fully walked to a confirmed vertex count or the start of face/index data.

## Confirmed: the full per-mesh geometry block, closed-loop verified end to end

Continuing the walk through `MyFirstModel.ms2` (1695 bytes total) after the bounding volume block, byte-exact:

| Byte range | Size | Contents | Verification |
|---|---|---|---|
| 19-42 | 24 bytes (6 floats) | Bounding box min + max | Exact match: ±0.005 on all 3 axes |
| 43-58 | 16 bytes (4 floats) | Bounding sphere center + radius | Exact match: center (0,0,0), radius `0.005×√3` to 7 sig figs |
| 59-74 | 16 bytes (4 floats) | Unknown — all-zero in this sample | Likely a pivot/local-origin field; untested against an off-origin object |
| 75-362 | 288 bytes (72 floats) | **24 vertex positions** (x,y,z each) | Every value is exactly `±0.005` — matches a hard-edged cube's 24 corner instances (4 per face × 6 faces, since each face needs its own normal) |
| 363-650 | 288 bytes (72 floats) | **24 vertex normals** (x,y,z each) | Every value is exactly `0.0`, `1.0`, or `-1.0` — the 6 axis-aligned cube face normals, repeated 4× each |
| 651-842 | 192 bytes (48 floats) | **24 vertex UV coordinates** (u,v each) | Small integer/half-integer values consistent with Maya's default "cross layout" auto-UV for a new polyCube |
| 843-914 | 72 bytes (36 × uint16) | **Face/triangle indices** | All 36 values fall in range 0-22 (valid indices into the 24 vertices); 36 indices = exactly 12 triangles — matches a cube's 6 quad faces × 2 triangles each **exactly** |
| 915-1694 | 780 bytes | Unidentified | Not text (searched for the known `bld_Haystack`/`.tga` texture name from the tutorial — not found anywhere in the file). Not a clean multiple of 24 (rules out a simple second per-vertex channel at the same vertex count). Left for a future pass. |

This means the entire vertex/normal/UV/index pipeline for a simple static mesh is now understood well enough to write a working decoder, and by symmetry, a large fraction of what a Blender exporter's write path would need to produce.

**A clarifying architectural finding**: the texture/material reference is **not** embedded in the `.ms2` file at all — confirmed by searching the whole file for the known texture name (`bld_Haystack`, referenced in the export tutorial) and finding nothing. This matches what's already independently known from this project's `.script` reverse-engineering: every `Models\*.script` file (e.g. `u_veh_t34_85_44.script`) has its own plain-text `ModelSkin` class listing texture paths per submesh. The `.ms2` file is very likely pure geometry; material/texture binding happens entirely in the companion hand-written `.script` file, which is already fully human-readable and doesn't need any reverse-engineering at all.

## What's confirmed vs. still open

**Confirmed (verified against known values, not just plausible-looking):**
- Universal 12-byte-plus-name header, present in 100% of samples.
- Field semantics: version/flag constant, node count, name length + name.
- Bounding box + bounding sphere block immediately follows the name.
- The complete vertex position / normal / UV / triangle-index block for a simple single-node mesh, closed-loop verified against a cube's known geometry (24 vertices, 12 triangles).
- IEEE-754 float32, little-endian, throughout; face indices are 16-bit.
- String encoding: int32 length prefix + ASCII bytes + one extra null terminator not counted in the length.
- Materials/textures are not stored in `.ms2` at all — they live in the already-understood companion `.script` files.

**Still completely open:**
- The unidentified 780 trailing bytes in this sample file (roughly half the file's total size).
- The per-node repeated record structure for files with `node count > 1` (everything above only covers the single node in a `node count = 1` file — need to check whether/how this block repeats for multi-node files).
- Skin/joint/animation data layout.
- The portal/light/physics-shape export paths documented in Phase 0.
- The unknown 4-float block at bytes 59-74 (pivot? local transform origin? needs a non-origin sample).

## Recommended next step

Examine a small multi-node file (`Sky.ms2`, node count = 2, only 16957 bytes) to find where one node's data ends and the next begins — this is the natural next question, since every real asset in the game (buildings, vehicles) has many nodes, and nothing about the multi-node record boundary is understood yet.
