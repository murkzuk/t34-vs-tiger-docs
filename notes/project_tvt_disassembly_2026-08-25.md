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

---

# UPDATE, same day — the Objects.dll run happened. It is vegetation.

The fresh run (`MAX_MODULES = 512`) worked: **164 modules known, unknown memory
down to 0.80%**, and Objects.dll now has page-level addresses. Steady state this
run: Objects.dll 48.70%, Engine.dll 21.03%, ntdll 7.96%, d3dx9 6.27%,
Service 4.76%, Controls 3.29%, J5Script 3.09%, Behavior **0.48%**.

Every hot Objects.dll page resolves through the RTTI map to a named class:

| page | share | class | what |
|---|---|---|---|
| `+0x17D000` | **9.90%** | between `CTreeKiller2` and `CSTTreesQuadTree` | forest spatial-grid query |
| `+0x0E6000` | 4.54% | `CVBWrapperTemplate<CGrassVertex,520,0>`, `CGrass` | **grass** vertex buffer fill |
| `+0x0E7000` | 2.23% | `CGrass` | **grass** |
| `+0x0EA000` | 2.12% | `CGrass` | **grass** |
| `+0x230000` | 2.01% | CRT transcendentals (`log10`,`exp2`,`atan`,`floor`) | called by the above |
| `+0x187000` | 1.66% | `CSTForest` | trees |
| `+0x186000` | 1.56% | `CSTForest` / `CTreeKiller2` | trees |
| `+0x0F1000` | 1.51% | `CGrass` / `CGridObject` | grass + spatial grid |
| `+0x19B000` | 1.47% | `CSTTreesArray` / `CTreeKiller` | trees |

Plus `Engine.dll+0x17D000` at 2.29% — the SpeedTree draw path from the first
half of this note.

### The headline

**Trees ~17% + grass ~9% = about 26% of total frame time, in the top fifteen
4 KB pages alone.** The real total across the whole vegetation code is higher —
this is only what surfaced above the reporting cut.

Vegetation is the single largest cost in this game by a wide margin. Nothing
else is close: all of the AI is 0.48%, the whole script interpreter 3.09%.

### The hottest page in the game, disassembled

`Objects.dll+0x17DD00` (736 bytes, one caller at `+0x18ACAE` inside `CSTForest`)
converts a world-space box into forest grid-cell indices:

```asm
0017DD0B  fld    dword ptr [eax]          ; x
0017DD0D  fsub   dword ptr [esp+0x18]     ; - radius
0017DD14  fdiv   dword ptr [ecx+0x43cc]   ; / cell size
0017DD22  fistp  dword ptr [esp+0x14]     ; -> int cell index
0017DD2A  test   eax, eax
0017DD32  jge    ...                      ; clamp to 0
0017DD38  mov    ecx, dword ptr [edx+0x43d0]
0017DD3E  dec    ecx
0017DD3F  cmp    eax, ecx
0017DD41  jle    ...                      ; clamp to gridDim-1
```

Four of those `fld`/`fistp` float-to-int round trips per query (min x, max x,
min y, max y). On x87 each one is a store-forward with a rounding-mode cost.
Run per query, per object, per frame — which is exactly the shape of a hot spot.

`"Cache miss"` sits one page further on at `+0x17E908`. **It is not a
performance logger — corrected after disassembling it.** The call that consumes
the string is followed by `int3`, so it never returns: it is a fatal assertion
on a lookup that is expected always to hit. There is no evidence it ever fires,
and it is not a lead. (The surrounding routine at `+0x17E8A0` is a refcounted
registry lookup returning a 36-byte record — `inc dword ptr [edx+eax*4]` then
`base + index*36`.)

## The immediately actionable part: grass has an in-game slider

`GameSettings.script:25` — `final static float GrassDetail = 1.0;` — and
`VideoOptionsMenuBase.script` wires it to an actual **Video Options slider**
(`h_grass`). So the ~9% grass cost can be tested live, with no file edit, no
cache clear, and no risk. Move the slider, watch the framerate.

`Scripts\Common\BaseGrass.script` holds the rest: `MaxVisDist = [20.0, 150.0]`
(grass draws to **150 m** at full detail), `MaxVisDistPower = 5`, and per-type
`Density` up to **2.9** for rye.

Note two REDUX changes already in that file, both marked `//jm`, and both of
which *increase* grass cost:

```
float   AlphaBlendDistanceFactor = 0.8;  //jm 0.4
boolean RenderOverShadow         = true; //jm false
```

`RenderOverShadow = true` means grass is drawn over shadowed ground as well —
extra fill. Worth knowing before tuning anything else.

## Bug found in the same log — `Cu_veh_PzVI_LATEModel`

`execution.log`: `"Scripts\Common\ShadowHide.script", 45(7): invalid LValue in
assignment`.

`ShadowHide.script:45` assigns `Cu_veh_PzVI_LATEModel::LodForShadowHide = 2.6`,
but **`Models\u_veh_PzVI_LATE.script` never declares that field** — it is the
only model file of the whole set that omits it. Every other one has it at the
same place, right after `LodForShadowChange`.

Effect: the late-model Tiger never gets its shadow-hide LOD, so its shadow
behaves differently from every other tank. One missing line, cosmetic, real.
NOT yet applied — awaiting the user's go-ahead.

---

# CORRECTION — the grass fill-rate hypothesis was WRONG

I proposed that `AlphaBlendDistanceFactor = 0.8` (a REDUX `//jm` change from
G5's shipped `0.4`) was widening an expensive alpha-blended band, and that
reverting it to `0.4` would buy back framerate. **Tested, and it is wrong in
both directions.**

Measured steady-state (per-window deltas, full grass both runs):

| | grass pages | verdict |
|---|---|---|
| `0.8` / `RenderOverShadow true` (jm) | **9.89%** | better |
| `0.4` / `RenderOverShadow false` (G5) | **12.45%** | worse |

The user also reported the visual symptom independently: *"i can see the tank
through the grass"*.

## What the value actually does — read from the engine, not guessed

`Objects.dll+0x0EE7D0`, the property registration for `CGrass`:

```asm
0EE7F9  mov   dword ptr [esp+0x18], 0x3f4ccccd   ; = 0.8f  <- ENGINE's own default
0EE8F3  fld   dword ptr [0x1039824c]             ; 1.0
0EE8FD  fsub  st(1)                              ; 1.0 - factor
0EE909  fdivr dword ptr [0x1039824c]             ; 1.0 / (1.0 - factor)
```

The engine stores **`1.0 / (1.0 - AlphaBlendDistanceFactor)`**. So the factor is
where the alpha fade-out *begins*, as a fraction of max view distance:

- `0.8` -> grass fades over the last **20%** of the draw distance
- `0.4` -> grass fades over the last **60%** — far more semi-transparent grass,
  which is both uglier (you see tanks through it) and *more* blended pixels

And the engine's hardcoded default is `0.8`, not the `0.4` in G5's own script.
**jm's change was right, and for exactly the reason the symptom showed.**

### SAFETY: never set `AlphaBlendDistanceFactor = 1.0`

`1.0 / (1.0 - 1.0)` is a division by zero. `0.9` is the practical ceiling (fade
over the last 10%). Reverted to `0.8`.

## Where the grass trade-off actually stands

| state | fps | grass CPU |
|---|---|---|
| grass slider off | **70-90** | absent |
| grass max, jm settings | 36-40 | 9.89% |
| grass max, G5 settings | (not measured) | 12.45% |

The doubling from turning grass off is real but the CPU share was only ~10% —
so most of that win is **GPU fill rate, which the sampling profiler cannot
see**. Corroborating evidence: the main thread never exceeds ~58% busy in any
run, so the game is not CPU-bound; it is waiting on the GPU.

**There is no free win here.** It is a straight quantity-vs-framerate trade.

### What is left to try, cheapest first

1. **Slider at the middle rather than max or off.** `MaxVisDist = [20.0, 150.0]`
   is a min/max pair the slider interpolates, so mid-slider is roughly 85 m of
   grass. Free, no file edit, and almost certainly the best value-for-effort.
2. Lower the `150.0` upper bound directly — distant grass at a grazing angle is
   the worst overdraw and the least visible benefit.
3. `Density` on the two expensive types (rye 2.9, high grass 2.5).

### Method note for next time

Two values were changed in one edit, so the 9.89% -> 12.45% result cannot be
attributed between them. Change one thing per measurement.
