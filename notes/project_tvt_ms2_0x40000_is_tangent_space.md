# The 0x40000 block is the tangent-space basis - the "unknown" that blocked new geometry

2026-10-30. Found in the isolated `K:\TvTDeepseek\ms2_tool\` workspace. This retires a
statement that has been load-bearing since August: that `vcount*24` (flag `0x40000`) is
unidentified, and that until it is understood the writer cannot add geometry.

**It is `vcount` tangents followed by `vcount` bitangents**, 12 bytes each, sequential and
not interleaved. Every vector is exactly unit length (min = max = 1.0000 over 1222 vectors on
one node), each is orthogonal to the authored normal, and each is orthogonal to its partner
(|cos| = 0.000 in 611 of 611).

## How it was found

1. Printed as six float32 lanes (`ms2_tool/ms2_block.py`), every 24-byte record had **two**
   halves that were both unit length, 100.0% of records. Two unit vectors per vertex is a
   frame, not noise.
2. The two candidate layouts were separated (`ms2_block_fit.py`):
   interleaved `v[2i]` vs `v[2i+1]` gives mean |cos| 0.816 - nonsense; **sequential**
   `v[i]` vs `v[vcount+i]` gives |cos| 0.000 for all 611, and both halves also 0.000 against
   the normal.
3. Compared against a frame derived from the mesh itself - dP/du and dP/dv per triangle from
   positions and UVs, accumulated per vertex and orthonormalised against the authored normal
   (`ms2_tangent_test.py`, `ms2_tangent_pop.py`):

        model                 comparable verts   dP/du vs 1st half    dP/dv vs 2nd half
        u_veh_KingTiger.ms2          72,150     0.9959 (92.4% >0.999)  0.8589 (57.1%)
        u_veh_t34_76_41.ms2          12,520     0.9992 (97.9%)         0.9847 (83.5%)
        bld_BridgeWood.ms2            5,027     0.9947 (92.8%)         0.9757 (83.3%)
        4MeterBox.ms2                    24     1.0000 (100%)          1.0000 (100%)

   Cross-check, dP/du against the *second* half: 0.019 mean, 0.000 median.

## The retraction that matters

"Tested and ruled out as tangent + binormal (mean |dot| 0.51 against computed values)" was
**a pairing error, not a result**. It compared the two halves of a 24-byte record, which are
tangent and bitangent of two *different* vertices when the arrays are sequential. That is the
same shape of mistake as the submesh `vertex_start` rebase the same week: a decode validated
on the common case, then trusted everywhere.

## What it changes

* **Adding geometry is no longer blocked by this.** The block is derivable from positions + UVs
  + normal, so a writer can generate it for vertices that did not exist before.
* The engine stores **dP/dv**, not `cross(N, T)`, in the second half - handedness travels in
  the data rather than being reconstructed from a sign.
* Because it is derivable, the "49% of every model file" framing can be dropped: it is 24 bytes
  of 68 bytes per vertex of vertex data (positions 12, normals 12, UVs 8, tangent frame 24,
  before indices), not an unexplained mass.

## Still open

1. Where the derived bitangent disagrees - King Tiger 57% vs 83-84% on the other models. That
   model also carries 5,801 UV-degenerate triangles, so quantify before regenerating.
2. Regeneration is close, not bit-exact (frames agree to |cos| > 0.999). Anything round-tripping
   must still preserve the block where geometry is not being changed.
3. Which UV set fed the tangents: `Turret_A_CM` has 317 of 321 UV-degenerate triangles yet a
   complete valid tangent set, so on those meshes the tangents came from a UV set that is not
   the one stored at `+uvs`. Candidate: the `0x800` block (`vcount*8`, a second float2 per
   vertex) - untested, and absent on the King Tiger.

Tooling and full write-up: `K:\TvTDeepseek\ms2_tool\README.md` (`ms2_block.py`,
`ms2_block_fit.py`, `ms2_tangent_test.py`, `ms2_tangent_pop.py`).
