# TvT's AI vision model, decoded

*2026-08-19. Derived from the disassembly of `Behavior.dll` (SHA-identical in
the live install and the sandbox), not from any documentation. Every address
here is an RVA against the DLL's preferred base `0x10000000`; the DLL relocates
by ~237 MB at runtime, so resolve at runtime and never hardcode.*

## The whole of it

`FUN_100c9e50` — `Behavior.dll + 0xC9E50`, 752 bytes — is TvT's entire vision
model. Not part of it. All of it.

```
visibility  = 1.0                                   // or [this+0x110] if the target changed
visibility *= stateTable[target->GetState()]        // [this+0x114][i]
visibility *= angleCurve(dot(dirToTarget, forward)) // piecewise curve at this+0xEC
visibility *= rangeCurve(distance)                  // piecewise curve at this+0xF8
if (visibility <= 0) return false

for each 0x1c-byte modifier in [this+0x104 .. this+0x108):
    if (predicate holds) visibility *= modifier.factor   // float at modifier+0x18
    if (visibility <= 0) return false

cache[key] = visibility                             // via FUN_100c9c60
if (visibility >= 1.0) return true

p = 1 - pow(1 - visibility, dt)
return rand() / 32767.0 < p
```

**There is no ray cast, no terrain sample and no foliage test anywhere in it.**
The direction work is done with a two-component vector product — the Z axis
never enters the calculation. A gunner sees, and shoots, through a ridge.

## Signature

`__thiscall`, `ret 0x1c`, so seven stack arguments:

| where | what it is | how that is known |
|---|---|---|
| `ECX` | the vision component (`this`) | `mov esi, ecx` at `+0x19` |
| arg1 | `float dt` | `fld [esp+0x5c]` then fed to `pow` |
| arg2 | target holder | `mov ecx,[edx]`, then a vtable slot-0 call with `EDX = 0x1024970c` — an interface cast by id |
| arg3 | cache key | passed to `FUN_100c9c60`, the per-key store |
| arg4 | modifier context | consumed inside the mask loop |
| arg5 | `float[2]` target position | reads `[eax]` and `[eax+4]` only |
| arg6 | `Matrix*` observer transform | reads `[eax]` and `[eax+0x10]` — column 0 of rows 0 and 1, i.e. the forward direction |
| arg7 | `float` distance | pushed straight into the range curve |

Note what arg5 and arg6 are **not** asked for: no Z from either. The observer's
height sits at `arg6[11]` and is never read.

## The early-out at `this+0x1A`

The first thing the function does:

```asm
100C9E6B  mov  al, byte ptr [esi + 0x1a]
100C9E6E  test al, al
100C9E70  jne  0x100c9e86        ; non-zero -> do the real work
100C9E72  mov  al, 1             ; zero     -> "visible", unconditionally
```

A single byte switches the whole check off. Zero means *everything is visible*.
This is the field the earlier probe work was circling as `SpecVisibilityCheck`
(the `LEA ECX,[EDI+0x8e8]` block at `10033ca7`).

## Helper functions, identified

| address | what it is | evidence |
|---|---|---|
| `0x1018BC30` | `rand()` | textbook MSVC LCG: `*0x343FD + 0x269EC3`, then `& 0x7FFF` |
| `0x1018D0A0` | `pow()` | SSE/x87 control-word preamble, two doubles in |
| `0x10042CB0` | piecewise-linear curve evaluator | walks 12-byte entries, compares against `[edx]`, returns `[edx+4]` |
| `0x1003DE80` | 2-component vector product | loads `[ecx]`,`[ecx+4]`,`[edx]`,`[edx+4]` and multiplies |

Constants: `0x102464EC` = `0.0`, `0x10246968` = `1.0`, `0x10246260` = `32767.0`.

## Why this is good news

The detection roll is a proper per-tick exponential — `1 - (1 - v)^dt` — which
is a sound piece of engineering. The model is not crude. It is *incomplete*:
every factor that should reduce visibility is present except the one that
depends on the world's shape.

And the shape of the gap tells you exactly where the fix goes. The engine
already walks a list of modifiers, each of which may multiply visibility by a
factor and bail out at zero. **Occlusion is one more modifier that returns
zero.** It does not need a new subsystem or a fight with the architecture — it
needs a multiplier the designers never wrote.

## The watcher

`K:\tvt_los\hook.cpp` → `tvt_los_hook.dll`, launched by `K:\tvt_los\watch.bat`
through the existing `tvt_inject.exe`.

It calls the original and returns its answer **unchanged**. It only records what
was asked and what came back. Reading real traffic and proving the hook is
stable comes before altering a decision — wiring new per-frame work into a 2001
engine's AI can wreck framerate or destabilise behaviour, and neither is proven.

Implementation notes worth keeping:

- The first instruction is `mov eax, fs:[0]` — six bytes, one instruction, no
  relocation. So a 5-byte `JMP` plus one `NOP` splits nothing, and the
  trampoline needs no length disassembler: copy those six bytes, jump back to
  `target+6`.
- `__fastcall` with a dummy second parameter is bit-for-bit `__thiscall`: arg1
  in `ECX`, arg2 in `EDX`, the rest pushed, callee cleans `0x1c`. Both the hook
  and the trampoline are therefore ordinary C functions, with no hand-written
  assembly anywhere.
- The prologue is verified against the six expected bytes before anything is
  patched. A mismatch aborts without touching the function.
- The trampoline pointer is published *before* the jump goes in. This function
  is called every tick for every observer against every candidate, so a thread
  can be inside the hook the instant the first byte changes.
- Sandbox only, enforced twice: the injector refuses any target outside
  `M:\TvT_INJECT_SANDBOX`, and the DLL refuses to arm unless its host process
  is in that folder.
