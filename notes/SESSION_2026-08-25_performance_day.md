# 2026-08-25 — the day we stopped guessing about framerate

One session, three dead hypotheses, two null results, one real bug fixed, and
one confirmed optimisation target. **The framerate went 36-40 to 66-76** — and
the honest position is that we still do not know exactly which change did it.

## The one thing to remember

**TvT is CPU-bound with the GPU sitting idle.** Directly measured, every run:

```
inside Present()   0.1%     <- waiting for the GPU
inside Lock()      0.0%     <- waiting for a buffer
everything else   99.8%     <- ~14 ms/frame of pure CPU work
```

322,000 triangles a frame at ~68 fps is roughly 20M triangles/sec. Nothing to a
modern GPU. It is idle, waiting for one core of your CPU.

Everything else in this note follows from that.

---

## What was measured, and what it cost

Method: `drawcall_probe` (built today) plus the sampling profiler, same mission,
same spot, same facing, grass and forest sliders as the only variable.

| | frame cost | verdict |
|---|---|---|
| **A `std::map` lookup** at `+0x17DAB0`, called from `CSTForest` | **6.51%** in 128 bytes | **CONFIRMED TARGET** |
| **Grass** | **1.8 ms (12%)** | real, tunable, modest |
| Tree *rendering* | ~0 | null — 24% of draw calls, no frame time |
| Tiger shadow bug | ~0 | null — real bug, zero fps |
| GPU / fill rate | 0.1% | excluded |
| Buffer lock stalls | 0.0% | excluded |
| Draw-call submission | ~0 | excluded (removed 24%, nothing changed) |

**Roughly 12 ms/frame is still unaccounted for.** Grass is the only positive
number we have from a slider, and it is small.

### The noise floor — the most useful number of the day

Three runs, identical conditions: **66.8, 69.5, 68.4 fps** — so run-to-run
variation is **±3-4%**. Established halfway through, and it immediately settled
two arguments retroactively:

- the shadow test came back at +4.0% = **exactly noise**, not a weak effect
- the grass result at 14.2% is comfortably real

**Anything below ~4% is unmeasurable by this method.** Say so rather than
reporting it as a finding.

---

## THE TARGET — tree management runs whether or not trees are drawn

> **The finding below stands. The *function* it names does not — see the
> caller trace at the end of this note. `+0x17DD00` runs once per frame;
> the real hot code is a `std::map` lookup at `+0x17DAB0`.**

The single most valuable result. `Objects.dll +0x17D000` is the hottest page in
the game, and the forest slider does not touch it:

```
page          FOREST MAX  FOREST MIN   change   what
+0x17D000          7.54%       7.45%    -0.09   quad-tree grid query
+0x19B000          1.47%       1.38%    -0.09   CSTTreesArray / CTreeKiller
+0x186000          1.27%       1.38%    +0.11   CSTForest
```

At forest MINIMUM the draw-call probe measured **a quarter of all draw calls and
27% of buffer traffic gone** — and the tree CPU cost did not move at all.

**The slider changes what is drawn. It changes nothing about what is computed.**
Every tree goes through the quad-tree walk, the grid query and the LOD decision
every frame, and when the draw distance is short that work is thrown away.

The function itself, disassembled (`Objects.dll+0x17DD00`, 736 bytes, called
from `CSTForest+0x18ACAE`):

```asm
0017DD0B  fld    dword ptr [eax]          ; x
0017DD0D  fsub   dword ptr [esp+0x18]     ; - radius
0017DD14  fdiv   dword ptr [ecx+0x43cc]   ; / cell size
0017DD22  fistp  dword ptr [esp+0x14]     ; -> int cell index
0017DD2A  test   eax, eax                 ; clamp to 0
0017DD38  mov    ecx, dword ptr [edx+0x43d0]
0017DD3F  cmp    eax, ecx                 ; clamp to gridDim-1
```

World box to forest grid-cell range, four x87 float-to-int round trips per
query.

### Why this is worth attacking

- it is **CPU** work, and the GPU is idle waiting for it
- **no existing setting reduces it** — you cannot tune your way out
- we know **exactly which function** and what it computes
- **DLL injection into this engine already works**

### What is NOT yet known

**Why it is called so often.** That is the question that decides whether this is
fixable. Making the function faster (SSE instead of x87) wins a fraction.
Making it get *called less* — caching between frames, skipping trees that cannot
matter — is where a real win lives, and that is in the caller, not traced yet.

**Next step: trace the callers of `+0x17DD00`.** Read-only RE, no play sessions,
nothing touched in the game.

---

## Three hypotheses that died

Recorded because each was plausible, each was wrong, and the pattern matters
more than any of them.

### 1. "Grass is a fill-rate problem"

Reasoning: alpha-blended billboards, ground-level camera, huge overdraw.
Measurement: `Present` 0.1%. The GPU was never busy. **Dead.**

### 2. "AlphaBlendDistanceFactor 0.8 is widening an expensive blended band"

Proposed reverting REDUX's `//jm` 0.8 to G5's shipped 0.4. Measured: grass cost
went **up**, 9.89% -> 12.45%, and the user reported seeing tanks through the
grass. Read the engine instead of guessing:

```asm
0EE7F9  mov   dword ptr [esp+0x18], 0x3f4ccccd   ; = 0.8f, the ENGINE's default
0EE8FD  fsub  st(1)                              ; 1.0 - factor
0EE909  fdivr dword ptr [0x1039824c]             ; 1.0 / (1.0 - factor)
```

The factor is where the alpha fade **begins**. `0.8` fades over the last 20% of
draw distance; `0.4` over the last **60%** — more transparency and more blended
pixels. jm's value was right and the engine agrees with it. **Dead, backwards.**

**SAFETY: never set `AlphaBlendDistanceFactor = 1.0`** — `1/(1-1)` is a divide
by zero. `0.9` is the ceiling and is what is now in place.

### 3. "The Tiger shadow bug is worth 28 fps"

Genuinely a bug (see `project_tvt_shadow_bug_2026-08-25.md`) and genuinely
fixed. Reverted it deliberately to confirm the attribution: framerate went
**up** 4% with the bug back — noise. The tell that should have been caught
first: draw calls went **down** with the bug active, when unlimited-range
shadows had to make them go up. And C1M2 contains **two** Tigers. **Dead.**

### The method lesson

Every one of the three was plausible reasoning from real evidence. Plausible
reasoning about a 2001 engine is worth approximately nothing. **Predict the
number before the run so the hypothesis can fail, and treat anything under the
noise floor as zero.**

---

## Real things that were fixed or built

### The Tiger shadow bug — a real bug, zero framerate

`ShadowHide.script:45` sets `Cu_veh_PzVI_LATEModel::LodForShadowHide = 2.6`, but
`Models\u_veh_PzVI_LATE.script` never declared the field — the only model file
of the set that omits it. Silent "invalid LValue", so every Tiger kept
`DefaultLodForShadowHide = 9999` (never hide) and behaved unlike every other
tank. `TankPzVIAusfEUnit::getMeshObjectName()` returns the LATE model
unconditionally, so this was every Tiger in the game.

Fixed (three lines, matching `u_veh_PzVI_MAIN.script`). Error gone from the log.
**ZeeWolf's copy already had the line** — ZW was right, REDUX was the odd one.

### The bug class is closed

Static sweep of every `Class::Field = value` assignment against whether the
field is actually declared on the class or an ancestor:

```
REDUX   (2390 classes indexed):  none
ZeeWolf (4957 classes):          none
```

**Tool validated first** by feeding it the pre-fix model file — it flags exactly
the known bug, so "none" is a real negative. (v1 produced three false positives
because its declaration regex was missing `WString`; the type list now comes
from counting every declaration keyword used in the tree.)

### `drawcall_probe` — a permanent asset

`K:\TvTDeepseek\drawcall_probe\`, source mirrored to `Tools/` in the docs repo.
Hooks D3D9 and answers "CPU or GPU?" in one run, for anything, forever. Every
vtable slot was verified against the SDK header before building — a wrong slot
crashes the game.

It killed the fill-rate hypothesis in about ninety seconds.

### The profiler's numbers were wrong, and are now right

`prof.cpp`'s counters are **cumulative since injection and never reset**, so the
headline figures included mission load. Per-window deltas give the true steady
state: **Objects.dll 50-54%, Engine.dll 20-24%, J5Script ~2%, Behavior.dll
~0.5%, D3D9 wrapper 0.0%.**

Three conclusions that got *stronger*:
- **DXVK vs dgVoodoo is irrelevant** — the wrapper is 0.0%
- **the `.script` interpreter is not a bottleneck** — 2%
- **the AI is free** — 0.5%, including the LOS hook. Never hold back an AI
  feature for performance reasons.

### The DLLs gave up their class names

RTTI survives in all of them. Extracted with `pefile` + `capstone`, not Ghidra:

| | named virtual functions | classes |
|---|---|---|
| Objects.dll | **4778** | 300 |
| Controls.dll | 4784 | 287 |
| Engine.dll | 2703 | 281 |

Any hot address now resolves to a class and vtable slot immediately. This is
what turned "Objects.dll 48%" into "`CGrass` and `CSTForest`".

Engine.dll's own hot block is **SpeedTree rendering** (`+0x167000..+0x180000`,
strings `RenderedTrees`, `CSTDynamicVB`, `FillBillPrimitiveVertexBuffer`). But
**SpeedTreeRT.dll itself is 0.04%** — the middleware is free; all the cost is
G5's own wrapper around it.

---

## Still open

- ~~Trace the callers of `Objects.dll+0x17DD00`.~~ **DONE** — it runs once per
  frame and was never the target. The real one is the `std::map` lookup at
  `+0x17DAB0`, 6.51% of the frame in 128 bytes. See the trace at the end.
- **Hook `+0x17DAB0` and count calls + distinct keys per frame.** The next
  measurement; it decides which fix is even applicable.
- **~12 ms/frame unaccounted for.** Grass is 1.8, tree management ~1.5, and the
  rest is not yet located.
- **What actually caused 36-40 -> 66-76?** Best remaining guess is that clearing
  `Cache\Scripts.cache` made earlier pending script edits live (the tree
  `ModelLOD` revert was measured at 8 fps by itself). **Not proven, and no more
  stories are being built on it.**

## Files

- `project_tvt_disassembly_2026-08-25.md` — the RTTI work, hot-page identification, the alpha-factor correction
- `project_tvt_shadow_bug_2026-08-25.md` — the shadow bug and its null result
- `K:\TvTDeepseek\drawcall_probe\` — probe, launcher, logs
- `K:\TvTDeepseek\rollback\grass_test_baseline_2026-08-25\` — every run's log, for re-diffing
- `K:\TvTDeepseek\rollback\shadowhide_2026-08-25\` — before/after of the model file

---

# THE CALLER TRACE — the hottest code in TvT is a `std::map` lookup

Done the same evening, read-only. **This corrects the target named earlier in
this note.**

## First, three more wrong claims, killed before they were made

**`+0x17DD00` is NOT the hot function.** Its single call site is linear code
with no loop — camera position and a radius in, grid-cell range out, **once per
frame**. The morning's claim that it "runs constantly" and was the optimisation
target was wrong. The error: `+0x17D000` is a 4 KB page holding **seventeen
functions**, and the page's 7.45% got attributed to the one function that
happened to have been disassembled.

**The FPU-control-word story.** `+0x17CF10` does `fnstcw`/`fldcw` rounding-mode
switching — genuinely one of the slowest idioms on modern x86, and called from
four loop sites. But those instructions sit at `0x17CF5B` and `0x17CF8C`, below
`0x17D000`, and **page `+0x17C000` never appears in the profiler log at all**.
Dead.

**The quad-tree recursion.** The caller graph showed `+0x18D0C0` calling itself.
It does not: that function ends at `0x18D128` (`ret 8`), and the call at
`0x18D15B` belongs to a *different* function starting at `0x18D130` that the
boundary detector missed. It is a `std::vector::erase` over 100-byte elements.
**Consequence: any caller trace beyond one hop is unreliable with the current
function boundaries.** Treat multi-hop chains as leads, never as fact.

## Then the measurement that settled it

Rather than guess which of seventeen functions was hot, the profiler got a
**64-byte fine histogram** over `Objects.dll +0x17C000..+0x180000` (`prof.cpp`,
`g_fine[]` — O(1) direct index per sample, no scan, so it cannot perturb what it
measures; `FINE_BASE`/`FINE_LEN` are constants, re-point and rebuild).

The result was not ambiguous:

```
FINE (64-byte buckets in Objects.dll +0x17C000..+0x180000, 367 samples)
    +0x17DAC0     6.51% of all    89.65% of range   329
    +0x17E8C0     0.28% of all     3.81% of range    14
    +0x17D580     0.08% of all     1.09% of range     4
```

**One bucket holds 89.65% of the region.** And `+0x17C000` is confirmed cold,
exactly as predicted.

## The function

`Objects.dll+0x17DAB0`, **128 bytes, 6.51% of total frame time** — about 87% of
the whole hot page. It is a red-black-tree descent, textbook MSVC
`std::map::lower_bound`:

```asm
0017DAB1  mov  ecx, dword ptr [ecx]      ; this->_Myhead
0017DAB3  mov  eax, dword ptr [ecx+4]    ; root
0017DAC2  mov  esi, dword ptr [edi]      ; the key
0017DAC4  cmp  dword ptr [eax+0x10], esi ; compare node key      <-- LOOP TOP
0017DAC7  jl   0x17dad0
0017DAC9  mov  edx, eax                  ; remember candidate
0017DACB  mov  eax, dword ptr [eax+8]    ; descend LEFT
0017DACE  jmp  0x17dad3
0017DAD0  mov  eax, dword ptr [eax+0xc]  ; descend RIGHT
0017DAD3  test eax, eax
0017DAD5  jne  0x17dac4                  ; while node != nil
```

Node layout: children at `+8`/`+0xC`, integer key at `+0x10`. The hot 64-byte
bucket `+0x17DAC0` covers exactly the descent loop.

**Eight instructions, and the most expensive code in the game** — not because
the instructions are slow, but because every node hop is a pointer chase into
unpredictable memory. It is a cache-miss machine.

### The six call sites

```
+0x17DEDB  in +0x17DD00   (the once-per-frame grid query)
+0x17E320  in +0x17E100
+0x17E8BA  in +0x17E8A0   <- the "Cache miss" function
+0x17E8D3  in +0x17E8A0   <- same, twice
+0x1869B1  in +0x186950   <- CSTForest block
+0x18770B  in +0x1876B0   <- CSTForest block
```

**The `"Cache miss"` string finally makes sense.** Two call sites are inside the
function whose failure path prints it — **that map IS the cache**. The assert
never fires because lookups succeed; they are simply expensive. An earlier
section of this note dismissed that string as a dead lead. It was pointing at
the right subsystem the whole time, just not for the stated reason.

The two `CSTForest` call sites are why the tree pages stay hot with the forest
slider at minimum: **the lookups happen per tree regardless of what is drawn.**

## Why this is better news than geometry

The morning's assumption was that the cost was arithmetic — float conversions,
grid maths. That is hard to improve. **A data-structure lookup is a different
class of problem** with well-understood fixes: memoise a repeated key, replace
the tree with a flat array if the keys are dense, or hoist the lookup out of the
per-tree loop.

## NEXT — and it is a measurement, not a theory

**Hook `+0x17DAB0`, count calls per frame, record the keys.** That answers with
no interpretation:

- how many lookups per frame
- how many **distinct** keys — a handful means an array replaces the tree
- whether the same key repeats — if so, one cached result kills most of the cost

Same read-only hook pattern already proven twice. One play session.

**Do not skip to patching.** Six theories died today; the count of distinct keys
decides which fix is even applicable, and it is cheap to measure.
