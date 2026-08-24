# SetTreeSize hook — spec (height-only tree scaling)

## Goal

Stretch specific trees (silver birch, small birch, linden) on the **height** axis
only, keeping the stock width, to fix "correct base dimensions but too short" —
without the uniform-scale "redwood" bloat we saw when raising `TreeSize`.

## Why a hook

The script exposes **one** `TreeSize` per species (`BaseSTTree.script`), and the
engine passes it to SpeedTreeRT as a **uniform** scale → the tree grows fatter as
it grows taller.

But SpeedTreeRT's real API takes width and height **separately**:

```
CSpeedTreeRT::SetTreeSize(float width, float height)
```

So we can stretch the Y axis independently by hooking that one function.

## Target

- **DLL:** `SpeedTreeRT.dll`
- **Function:** `CSpeedTreeRT::SetTreeSize(float, float)`
- **Mangled export:** `?SetTreeSize@CSpeedTreeRT@@QAEXMM@Z`
  (confirmed via `dumpbin /exports`)
- **Calling convention:** `__thiscall` — `this` in ECX, the two floats on the stack.
  A `__fastcall` shim captures `this` + args and calls the original.

## Key assumption to verify (Phase 0)

That `STTree.dll` calls `SetTreeSize(width == height == TreeSize)`. If it already
passes different w/h, the plan changes. **Verify read-only first** — extend the
existing probe to log `SetTreeSize` calls (just width + height per call), one run,
no behaviour change.

## Tree identification

Which tree is being sized? Two options:

1. **Value-based (quick PoC).** `width == height == TreeSize` identifies species:
   - Birch `4.0` → unique
   - Linden `8.0` → unique
   - SmallBirch `3.0` → **collides** with the bush (`BulfordHolly` = 3.0)
2. **Filename-based (robust).** Hook `LoadTree(char const*)` and record
   instance → `.spt` filename; look up the instance in `SetTreeSize`. This is the
   correct long-term approach and also opens the door for per-species tuning of
   every tree.

## Hook mechanism

Inline 5-byte JMP trampoline on the export — the same pattern `fog_probe` already
uses for `Direct3DCreate9`. On the hooked call:

- keep `width` = stock (correct base);
- replace `height` with `width × stretch` (or a fixed height).

## Injection timing

Determine whether `SpeedTreeRT.dll` is a **static import** (mapped during the
EXE's import resolution, so it's present before our DLL's DllMain under suspended
injection) or **runtime `LoadLibrary`** (needs the loader-notification approach
`fog_probe` uses for `d3d9.dll`). Check the import tables of `TvsT_*.exe` /
`Engine.dll` / `STTree.dll` first.

## Tunables (to dial in by eye)

| Tree | width (keep) | height (start) |
|---|---|---|
| Birch | 4.0 | ~8.0 (2×) |
| SmallBirch | 3.0 | ~6.0 |
| Linden | 8.0 | ~14–16 |

Start at 2× stock height and adjust until the silhouette reads as a real silver
birch (slender, not stubby, not redwood).

## Risks / side effects

- **LOD coupling:** `SetTreeSize` feeds SpeedTreeRT's LOD, so a taller tree pushes
  detail out (mild FPS cost) — but far less than uniform scaling since width (leaf
  volume) stays small. This may actually fix the "LOD pops at 5 m" problem as a
  side effect.
- **Collision/knockdown** uses `CTreeDescriptor`'s `TreeRadius` / `FallEnergy`
  (script side), NOT `SetTreeSize`, so a visually-taller tree may exceed its
  collision box slightly. Minor; verify a knocked-down birch still looks sane.
- **Root-system decal** (`RootSystemSize`) is separate and unaffected.

## Relationship to other notes

Same injection machinery and same DLL as `project_tvt_speedtree_harvest.md`. This
is the smallest possible first target into `SpeedTreeRT.dll` — one exported
function, one axis, immediate visible result — and it de-risks the harvest path.
