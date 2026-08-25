# Disassembling the hot addresses — what the frame time actually is

2026-08-25. Follows the sampling profiler run in `M:\T34vsTiger\tvt_prof.log`.
Tooling: `pefile` + `capstone` in Python, **not** Ghidra — the DLLs carry full
MSVC RTTI, which is a faster and more precise lever for this job.

## First, a correction to the profiler's headline number

**The profiler's counters are cumulative since injection and are never reset**
(`prof.cpp` prints percentages of a running total). So the numbers quoted in
`THE_PLAN.md` — "Objects.dll 44.75%, D3D9 1.31%" — are *session averages that
include mission load*, not steady-state gameplay.

Recovering the per-window deltas from the eight cumulative reports gives the
real gameplay mix:

| module | cumulative (what we quoted) | **steady state (true)** |
|---|---|---|
| Objects.dll | 44.75% | **50–54%** |
| Engine.dll | 21.07% | 20–24% |
| ntdll.dll | 12.86% | 4–9% |
| d3dx9_30.dll | 5.72% | 5–8% |
| Service.dll | 5.29% | 5–6% |
| **D3D9.DLL (the wrapper)** | 1.31% | **0.0%** |
| J5Script.dll | 2.53% | ~2% |
| Controls.dll | 2.20% | 2–3% |
| Behavior.dll | 0.57% | ~0.5% |

The early reports were dominated by `ntdll` at 65% — that is mission *loading*
(file I/O and allocation), and it dragged every other figure down.

### Three conclusions that get stronger, not weaker

1. **The D3D9 wrapper is 0.0% of steady-state frame time.** DXVK vs dgVoodoo is
   irrelevant to framerate. That question is now closed twice over.
2. **The `.script` interpreter is not the problem.** `J5Script.dll` is ~2%.
   Script-level optimisation would be wasted effort.
3. **The AI costs nothing.** `Behavior.dll` is ~0.5% — so the LOS hook, the
   occlusion maths and the wingman work are all free. No reason to hold back on
   AI features for performance reasons.

## Engine.dll (~21%) — it is tree rendering

The hot pages cluster in one contiguous block, `+0x167000 .. +0x180000`.
Sweeping every string referenced from that block identifies it beyond doubt:

```
RenderedTrees        TreeMapSize          ShadowLOD        RootSystem
CSTDynamicVB         CSTDynamicIB         FillBillPrimitiveVertexBuffer
Unable to allocate billboard vertex buffer space for %li vertices
```

`CSTDynamicVB` / `CSTDynamicIB` are SpeedTree's dynamic vertex and index
buffers. This is the SpeedTree draw path.

Five hot pages fall inside it — `+0x17D000` (2.43%), `+0x168000` (1.22%),
`+0x16F000` (0.98%), `+0x17E000` (0.96%), `+0x179000` (0.69%) — **6.28% of
total frame time in five pages alone**, before counting everything spread more
thinly across the other ~90 KB of the block.

**This independently confirms the Phase 1 tree finding.** Pulling `ModelLOD`
back in `BaseSTTree.script` was worth 8 fps, and this is why: trees are the
single largest identifiable cost inside Engine.dll.

### The hottest single function: `Engine.dll+0x17CFD0`

2288 bytes, an SEH frame, and a 740-byte stack frame (`sub esp, 0x2E4`) — a big
routine. What it does is legible from the disassembly:

```asm
0017D00C  fld    dword ptr [esp+0x308]
0017D014  fmul   dword ptr [0x10319680]   ; f32 = 255.0     <- colour to 0..255
0017D01E  call   0x10014088

0017D02F  mov    eax, 0x78787879          ; magic-number division
0017D034  imul   ecx                      ;   2^37 / 0x78787879 = 68
0017D036  sar    edx, 5                   ; -> array of 68-byte records

0017D079  movzx  edx, byte ptr [ebx+eax+0x40]   ; byte material ID at +0x40
0017D07E  mov    ecx, dword ptr [ecx+0xc]       ; material pointer table
0017D081  mov    eax, dword ptr [ecx+edx*4]
0017D084  cmp    dword ptr [esp+0x3c], eax      ; same material as last?
0017D088  je     0x1017d26f                     ; yes -> skip the state setup
```

That is a **material-sorted batch draw loop**: walk a list of 68-byte instance
records, read a one-byte material ID from offset `+0x40`, look the material up
in a pointer table, and only do the (expensive) state setup when it differs
from the previous record. The `fmul 255.0` is a float colour being converted
for the vertex format.

It has **zero direct callers** — it is reached by virtual dispatch or a function
pointer, which is why the call-target scan alone could not find its boundaries.

## The other two hot regions in Engine.dll

| region | share | what it is |
|---|---|---|
| `+0x228F00` | ~1.12% | **UI rendering** — references `Shaders\UI.fxo` |
| `+0x031000` | ~0.67% | **D3D surface/texture format handling** — the block is surrounded by the D3DFORMAT name table (`DXT1`, `D24S8`, `A32B32G32R32F`, …) |

`Controls.dll+0x0A1000` (~0.94%) sits in input handling (`SetInputFilter`).

## Objects.dll (50–54%) — the disassembly is BLOCKED, and why

**No page-level data exists for Objects.dll in this log.** The profiler's module
table was capped at `MAX_MODULES = 128` and hit that cap exactly, so Objects.dll
fell through to the "unknown memory" path. That path resolves the *base address*
via `VirtualQuery` (which is how we know it is Objects.dll at all) but does not
bucket 4 KB pages. The `HOTTEST ADDRESSES` list therefore contains no Objects.dll
entries.

`MAX_MODULES` is now **512** and `tvt_prof.dll` was rebuilt at 13:41 — two
minutes *after* this log was written. So the fix is in place but has never run.

**Next step: one fresh profiler run.** Launcher → tick Profiler → play any
populated mission for ~2 minutes. That will produce Objects.dll page addresses,
and the RTTI map below turns them into class and method names immediately.

## The RTTI map is already built and waiting

Extracted from the shipped DLLs — MSVC RTTI survives in all of them:

| DLL | complete-object locators | vtables | **named virtual functions** | classes |
|---|---|---|---|---|
| Objects.dll | 1260 | 968 | **4778** | 300 |
| Engine.dll | 745 | 507 | 2703 | 281 |
| Controls.dll | 1176 | 883 | 4784 | 287 |

Real names, e.g. `CAnyComponentNE@g5`, `IVisible@g5`, `IPositionable@g5`,
`IVertexArray@g5`, `IMeshJoint`. So the moment we have an Objects.dll RVA we can
name the class and the vtable slot it belongs to, rather than reading raw
assembly.

Scripts live in the session scratchpad (`build.py`, `rtti.py`, `hot2.py`,
`dumpfn.py`, `region.py`, `imps.py`, `delta.py`) — cheap to rebuild, they only
read the DLLs.

## What this changes

- **Phase 1's answer is sharper, not different.** The framerate is spent on the
  game's own object and rendering code (~75%), and the wrapper is nothing.
- **Trees are confirmed as the biggest single named cost.** Already acted on.
- **Objects.dll at half the frame time is still unexplained** — and it is the
  only remaining place where a large win could hide. One profiler run away.
