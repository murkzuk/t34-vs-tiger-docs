# Tree height-only scaling (GetGeometry Y-scale) — PLAN (REDUX first)

Status: **PARKED 2026-08-29 — blocked, revisit later.** Supersedes the parked
SetTreeSize approach (`project_tvt_settreesize_hook_spec.md` has the Phase 0/1
results). The reverse-engineering is COMPLETE and recorded below; the blocker is
an unexplained runtime failure (see "Step 3 result").

## Why parked (read this first on revisit)

The whole SGeometry layout is mapped (branches `+0x90`, count `+0x84`, Z=up;
fronds `+0x60`; leaf cards; billboard). A scaler was built and its hook's
calling convention was verified byte-for-byte correct (`ret 0x14`, args on the
stack). **Yet ANY hook on `CSpeedTreeRT::GetGeometry` — even a bare
call-original-and-return passthrough (`tree_minhook.dll`) — makes trees cull/pop
in and out by camera angle** (confirmed by a control test: stock launch is fine).
Hot-path overhead was ruled out (O(1) hash changed nothing). The mechanism is
NOT yet understood; see "Step 3 result". Do not ship `tree_yscale.dll` /
`tree_yprobe.dll` / `tree_minhook.dll` — they are diagnostic only.

## Goal

Stretch **Birch** (CBirch `TreeSize 4.0`, CSmallBirch `3.0`) and **Linden** on the
**height (Y) axis only** — keep stock width — to fix "correct width but too short",
with **no "redwood" uniform bloat**. **REDUX first**, then ZW.

## Why SetTreeSize is dead

`STTree.dll` calls `SetTreeSize(width=TreeSize, height=0)`; SpeedTreeRT scales
proportionally only, so any height override fattens the whole tree (Phase 1 proved
it). The engine pulls triangles through ONE seam — `CSpeedTreeRT::GetGeometry` —
so that's the hook point.

## Plan

1. **Reverse-engineer `SGeometry`** — disassemble
   `?GetGeometry@CSpeedTreeRT@@QAEXAAUSGeometry@1@KFFF@Z` (prologue `55 8B EC 6A FF`)
   in `SpeedTreeRT.dll` to find the vertex-position array offset + stride inside the
   `SGeometry` struct.
2. **Build `tree_yscale.dll`** — hook `GetGeometry` (loader-notification, same as
   `tree_size_probe`), identify `Birch.spt` / `Linden.spt` by filename, and scale
   each vertex's Y around the tree base by factor **K** for those species only.
3. **Pick K** — A/B test K = 1.5 then 2.0 by eye (birch/linden are currently too
   short; target a natural height, not redwoods).
4. **Test REDUX** — birch/linden taller, width unchanged; check for LOD pop at range
   (geometry-Y doesn't feed `SetTreeSize`'s LOD box), collision/knockdown
   (`TreeRadius`/`FallEnergy` unchanged), and root decal.
5. **Then ZW** — same DLL; first confirm ZW's Birch/Linden `TreeSize` values and
   whether ZW has the same "too short" symptom.

## Step 1 result (2026-08-29) — SGeometry layout mapped

Disassembled `GetGeometry` (RVA `0x1DAD0`, prologue `55 8B EC 6A FF` as expected)
with capstone. It dispatches on a flag bitmask in arg2 (`bl`) to fillers:

| flag bit | filler RVA | fills |
|---|---|---|
| 0 | `0x1CC70` | leaf cards — `SGeometry+0x10` count(word), `0x14/0x18/0x1c/0x20/0x24` pointers |
| 1 | `0x1CF90` | fronds — `0x4c` count, `0x50–0x70` array pointers, `0x3c/0x40` |
| 2 | `0x1AD30` | **branches** — fills `SIndexedTri` at `SGeometry+0x78` |
| 3 | `0x1AFB0`/`0x1BD50` | whole-tree billboard — `0xfc–0x11c` |

**Branch mesh (`SIndexedTri` at `SGeometry+0x78`), from filler `0x12d40`:**

- `+0x1c` = word (vertex/index count)
- `+0x20` = index array pointer
- **`+0x24` = vertex coordinate array (float xyz, stride 12 bytes)** ← the Y-scale target
- `+0x28` = word (branch count)
- `+0x2c` = branch record pointer

The vertex read (`0x12E2F`): `coord = [SIndexedTri+0x24]; x=coord[i*3], y=coord[i*3+1], z=coord[i*3+2]` (stride 12).

**Open (for step 2):** the filler does `1.0 - x` (mirror on first coord = handedness),
so confirm which axis is "up" (Y or Z) in tree space — pin by testing scale-Y vs
scale-Z on a birch. Frond (`0x50–0x70`) and leaf-card arrays are there too for a
complete stretch, but branches are the main structure.

Tooling added: `K:\TvTDeepseek\tree_probe\disasm_geometry*.py` (capstone dumps).

## Step 1b result (2026-08-29, same session — CORRECTION to Step 1)

Deeper disasm of `0x1AD30` (GetGeometry bit2 dispatch) + `0x12d40` (the branch
filler) **corrects the Step 1 field attribution**:

- The filler's `this` is `[CSpeedTreeRT + 8]` — the tree's **internal geometry
  object**, NOT the `SIndexedTri` at `SGeometry+0x78`. So `+0x1c/+0x20/+0x24/
  +0x28/+0x2c` above are fields of that **internal** object, and `+0x24` is the
  RAW `.spt` input coords (read-only, consumed inside `GetGeometry`).
- The engine-visible output is a **0x3c-byte `SIndexedTri` copied INLINE at
  `SGeometry+0x78`** — the filler ends with `rep movsd` (15 dwords = 0x3c bytes)
  from a cached **per-branch record** (`[geom_obj+0x2c] + branch_index*0x44`) into
  `SGeometry+0x78`. That record is what the engine draws.
- The transform (raw coords → cross-expanded output at `[geom_obj+0x10]`) is
  **cached per branch** via a dirty flag (`[branch_record+0x3c]`). Therefore
  scaling the raw `+0x24` coords **after** `GetGeometry` returns does nothing —
  the transform already ran and won't re-run.
- **Up axis settled:** the transform is a 2×2 matrix on the first TWO coords
  (X, Y) using a per-vertex 2-component direction `(A0,A1)` at `[geom_obj+0x20]`;
  the third coord (Z) passes through as height. `1.0 - x` mirrors X (horizontal
  symmetry). So **Z = up**, X/Y = horizontal pair. (Plan title says "Y-scale" —
  that's the stale name; the axis is Z.)

**Next:** find the real vertex-array pointer field inside the 0x3c `SIndexedTri`
(`SGeometry+0x78..+0xb4`). Built `tree_yprobe.dll` (read-only) to dump that
struct + candidate pointers on the first Birch/Linden `GetGeometry` call. After
one REDUX run, the log pins the exact pointer offset and the scaler targets it.

## Step 1c result (2026-08-29 — full SGeometry mapped from tree_yprobe log)

`tree_yprobe.dll` dumped a live REDUX Linden (`flags=7` = leaf+frond+branch).
Verified the hook's compiled code is clean (`ret 0x14`, args on the stack, no
stack imbalance). Full `SGeometry` decode:

- **Branches** (`SIndexedTri` inline at `SGeometry+0x78`, 0x3c bytes):
  `+0x0c` = WORD vertex count (42), `+0x18` = **vertex POSITIONS pointer** →
  `SGeometry+0x90` (float xyz, stride 12). Z = height (branch Z −0.97..9.05).
  `+0x1c/+0x20` ≈ texcoords, `+0x28/+0x2c/+0x30` ≈ normals/tangents/binormals.
- **Fronds**: positions pointer at `SGeometry+0x60` (Z 1.4..6.6 — the canopy
  skeleton), normals at `+0x54/0x58/0x5c`, texcoords at `+0x64`.
- **Leaf cards**: `+0x10` = count(8)/flag, pointers `+0x18` (corners), `+0x1c`
  (normal 0,0,−1), `+0x20/0x24` (tangents) — card-local, needs separate handling.
- **Billboard**: `+0xfc..+0x11c` (LOD far card).

## Step 2 result (2026-08-29) — first scaler build + the hot-path hypothesis

Built `tree_yscale.dll` (K=1.5) scaling branch Z at `SGeometry+0x90`. **Every
build caused trees to pop in/out by camera angle** — a user control test (stock
launch) confirmed it was the DLL. First hypothesis was hot-path overhead (an
O(512) filename-map scan every frame per visible tree). Rebuilt with targets in
an O(1) open-addressing hash set (recorded at `LoadTree`, `hash_contains` in the
hook, no map scan / strstr / logging in the hot path; each buffer scaled once).
**The O(1) fix changed nothing** — the overhead hypothesis is WRONG.

## Step 3 result (2026-08-29) — the blocker: ANY GetGeometry hook breaks trees

Bisected with `tree_minhook.dll` = hook `GetGeometry` and do NOTHING but call the
original (`g_orig(self, geom, flags, f1, f2, f3)`) — no `LoadTree` hook, no hash,
no scale, no hot-path logging. **Trees still pop in/out.** So the 5-byte JMP
trampoline on `GetGeometry` itself is the problem, and the reason is NOT yet
understood:

- Prologue `55 8B EC 6A FF` verified before patching; export RVA `0x1DAD0`.
- Disassembled the real export: it ends `ret 0x14` (and a second `ret 0x14` path);
  the hook's compiled code also ends `ret 0x14`, args read from the correct stack
  slots, `this` in ECX — byte-for-byte correct calling convention.
- SEH/EBP chain and stack balance traced and shown correct.
- The same trampoline pattern works on `LoadTree`/`SetTreeSize` (Phase 0/1) with
  trees rendering fine; it is `GetGeometry` specifically that breaks.
- `flags=7` (leaf+frond+branch) in the live call; f1/f2/f3 arrive as NaN from the
  engine (passed through unchanged).

**Unresolved candidates for revisit:** (1) `GetGeometry` is called far more often
than estimated (per-LOD/per-branch), so even the trampoline's ~20 cycles tips the
game's frame budget and its dynamic LOD culls trees — test by counting call rate;
(2) patching happens while a render thread is mid-call (timing race on
VirtualProtect) — test by patching from the loader notification before any tree
renders vs. deferring; (3) the engine reads the export bytes / checksums the
function; (4) the extra call/ret layer disturbs a render-thread stack assumption.
None confirmed.

## Risks (from the spec note)

- LOD box is driven by `SetTreeSize`, not the geometry → a taller tree may pop when
  the LOD switches. Verify and note if acceptable.
- Knockdown/collision uses script-side `TreeRadius`/`FallEnergy` → a visually-taller
  tree slightly exceeds its collision box. Minor.
- Root-system decal (`RootSystemSize`) is separate and unaffected.

## Tooling (all in `K:\TvTDeepseek\tree_probe\`, none are ship-ready)

- `tree_size_probe.{cpp,dll}` — Phase 0 logger (keep).
- `tree_stretch.{cpp,dll}` — Phase 1 SetTreeSize override (superseded, do not ship).
- `tree_yprobe.{cpp,dll}` + `run_yprobe.bat` — read-only GetGeometry dump (worked;
  produced the full SGeometry map). Diagnostic only.
- `tree_yscale.{cpp,dll}` + `run_yscale.bat` — the height scaler (K=1.5, O(1) hot
  path). Builds and hooks correctly but inherits the Step-3 blocker. Do not ship.
- `tree_minhook.{cpp,dll}` + `run_minhook.bat` — bare GetGeometry passthrough;
  proves the blocker is the GetGeometry patch itself. Diagnostic only.
- `build*.bat`, `disasm_geometry*.py` — build + capstone reverse-engineering aids.
- No game files were modified by any of this — every DLL is runtime-injected and
  vanishes when the game closes.
