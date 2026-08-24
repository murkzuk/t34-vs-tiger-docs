# SetTreeSize hook — spec + Phase 0 result (height-only tree scaling)

## Goal

Stretch specific trees (silver birch, small birch, linden) on the **height** axis
only, keeping the stock width, to fix "correct base dimensions but too short" —
without the uniform-scale "redwood" bloat we saw when raising `TreeSize`.

## Why a hook

The script exposes **one** `TreeSize` per species (`BaseSTTree.script`), and the
engine passes it to SpeedTreeRT as **width only** (`height = 0`), so the tree's
height comes from the `.spt`'s own proportions → raising `TreeSize` grows the
tree fatter *and* taller together (the "redwood").

SpeedTreeRT's real API takes width and height **separately**:

```
CSpeedTreeRT::SetTreeSize(float width, float height)
```

So we can stretch the Y axis independently by hooking that one function.

## Target

- **DLL:** `SpeedTreeRT.dll`
- **Function:** `CSpeedTreeRT::SetTreeSize(float, float)`
- **Mangled export:** `?SetTreeSize@CSpeedTreeRT@@QAEXMM@Z` (confirmed via `dumpbin /exports`)
- **Calling convention:** `__thiscall` — `this` in ECX, the two floats on the stack.
  A `__fastcall` shim captures `this` + args and calls the original.
- **Prologue:** both `SetTreeSize` and `LoadTree` open with `55 8B EC 6A FF`
  (push ebp; mov ebp,esp; push -1) — disassembled from the shipped DLL. A clean
  5-byte whole-instruction boundary, so a 5-byte JMP trampoline is safe.

## Phase 0 result (confirmed 2026-08-24, read-only probe)

`STTree.dll` calls **`SetTreeSize(width = TreeSize, height = 0.0)`** — every
call, every species. Not a uniform `w==h` pass; `0.0` is the engine's "don't set
height" signal (height comes from the `.spt`).

```
LoadTree this=… file=Models/Trees/Birch.spt
SetTreeSize this=… w=4.000 h=0.000 Models/Trees/Birch.spt
```

So the fix is trivial: **when `h == 0`, replace it with `width × K`**. Width stays
untouched → correct base, taller only.

## Tree identification (resolved)

The `LoadTree` → instance map worked perfectly (every `SetTreeSize` call logged
its `.spt`). The log also showed **several classes share one `.spt`**, so width
is the real species discriminator:

| `.spt` | widths → class |
|---|---|
| Birch.spt | 4.0 = CBirch, 3.0 = CSmallBirch |
| FirScotch.spt | 25.0 = CFirScotch, 20.0 = CFirScotchSmall |
| BulfordHolly.spt | 3.0 = bush, 5.0 = large bush |
| AppleTree.spt | 7.5 = CAppleTree, 6.2 = CSmallAppleTree |

Phase 1 identifies by **filename** (`Birch.spt` / `Linden.spt`) and treats both
birch widths as the same species.

## Hook mechanism (Phase 1)

Inline 5-byte JMP trampoline on the export (same pattern as `fog_probe`). On the
hooked call:

- if `height == 0` **and** the tree is a target (`Birch.spt` / `Linden.spt`),
  replace `height` with `width × K`;
- otherwise pass through unchanged.

## Injection timing (resolved)

`SpeedTreeRT.dll` is **runtime-loaded**: the EXE / Engine.dll / Objects.dll do
not import it; `STTree.dll` (itself runtime-`LoadLibrary`'d) statically imports
it (`dumpbin /imports` verified). The loader-notification approach (`fog_probe`'s)
works — Phase 0 patched on load, confirmed live.

## Tunables (dial in by eye)

`K` is the one knob (a `#define` in `tree_stretch.cpp`). Start at `2.0`
(height = 2× width) and adjust until the silhouette reads as a real silver birch
(slender, not stubby, not redwood).

| Tree | width (unchanged) | height = width × K at K=2 |
|---|---|---|
| Birch | 4.0 | 8.0 |
| SmallBirch | 3.0 | 6.0 |
| Linden | 8.0 | 16.0 |

## Risks / side effects

- **LOD coupling:** `SetTreeSize` feeds SpeedTreeRT's LOD, so a taller tree pushes
  detail out (mild FPS cost) — but far less than uniform scaling since width stays
  small. May fix the "LOD pops at 5 m" problem as a side effect.
- **Collision/knockdown** uses `CTreeDescriptor`'s `TreeRadius` / `FallEnergy`
  (script side), NOT `SetTreeSize`, so a visually-taller tree may exceed its
  collision box slightly. Minor; verify a knocked-down birch still looks sane.
- **Root-system decal** (`RootSystemSize`) is separate and unaffected.

## Tooling

- Phase 0 (logger): `K:\TvTDeepseek\tree_probe\tree_size_probe.{cpp,dll}`
- Phase 1 (stretch): `K:\TvTDeepseek\tree_probe\tree_stretch.{cpp,dll}`
- Allow-list: `K:\TvTDeepseek\tree_probe\tvt_los_allow.txt` (beside the DLL —
  the injector requires it)

## Relationship to other notes

Same injection machinery and same DLL as `project_tvt_speedtree_harvest.md`. This
is the smallest possible first target into `SpeedTreeRT.dll` — one exported
function, one axis, immediate visible result — and it de-risks the harvest path.
