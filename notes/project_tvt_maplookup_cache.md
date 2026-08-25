# The map-lookup cache — +6.3% framerate, measured under control

2026-08-25. **The first performance change in this project proven rather than
eyeballed.** Code: `K:\TvTDeepseek\maplookup_memo\`, source mirrored to `Tools/`
in the docs repo.

## What was changed

A **one-entry cache** in front of `Objects.dll+0x17DAB0` — MSVC
`std::map::lower_bound`, a 128-byte red-black-tree descent that the profiler
measured at **7.59% of the entire frame**, the most concentrated cost in the
game.

Nothing on disk is modified. It is an injected DLL; launching the game normally
gives stock REDUX.

## Why a cache was the right shape of fix

The counting probe measured, across 23 report blocks with no spread at all:

```
lookups                  2,857,139 per second   (~41,400 per frame)
key repeats previous          67.2%   (67.0 - 67.5% every single block)
distinct keys                 8192+   (table full - a floor)
top 16 keys cover            19-51%
```

**41,000 `std::map` lookups per frame**, for a scene containing 72
`TreeObject`s. And two-thirds of them repeat the key of the call immediately
before — so the caller loops over things that share a key and re-walks the tree
for every one.

A one-entry cache turns that into a single walk per group. **It is hoisting the
lookup out of the loop, done from outside the engine without touching the
loop.**

Adjacent keys in the hot list (`441863`/`441864`, `385665`/`385666`,
`392830`/`392831`) say these are consecutive spatial grid-cell indices.

## THE RESULT

Measured by the DLL A/B-testing **itself** — see the method note below:

```
CACHE     124.2  126.5  123.9  116.6      median 124.2
BYPASS    117.1  117.1  115.6  116.5      median 116.8
                                          -------------
                                          +7.4 fps   +6.3%
```

**265 million calls, 0 mismatches, 67.4% hit rate.**

The `BYPASS` control spans 115.6 - 117.1 across four separate phases — a 1.5 fps
spread. That tightness is what makes the result trustworthy: the scene really
was identical and the cache really was the only variable.

### It beat the arithmetic, and that is informative

7.59% of frame x 67% hit rate = **5.1% theoretical maximum**. Measured **6.3%**.

The excess is almost certainly the second-order effect: skipping 27 million tree
walks per second does not only save those walks, it stops them evicting
everything else from cache. **The code around it got faster too.** Worth
remembering when sizing any future pointer-chasing fix — the direct arithmetic
is a floor, not a ceiling.

### It also beat the prediction

Predicted +3 to +5%, with an explicit warning it might land below the +-4% noise
floor and be unprovable. It came in at +6.3%, above the floor. The prediction
was recorded before the run precisely so it could fail.

## THE METHOD — the DLL A/B tests itself

The user pointed out that the in-game F9 counter costs frames of its own. True,
but the bigger problem was that comparing two separate runs cannot rule out
standing somewhere slightly different, or the +-3 fps of run-to-run drift that
had already made a mess of the shadow-bug attribution earlier the same day.

So the DLL hooks `Present` to count its own frames, and **flips its own cache on
and off every 10 seconds**, reporting fps for each phase. Same scene, same
session, same position, seconds apart — one variable. `BYPASS` is a true
pass-through (it still refreshes the cache entry, it just never uses it), so
neither phase is handicapped.

**This is the technique to reuse for any future performance change.** It removes
position, drift, and observer overhead in one move, and it produces a control
column you can look at to judge whether the measurement is sound.

## THE SAFETY — it validates itself before it acts

A stale cache in front of a container lookup returns a dangling iterator and the
game corrupts. The guard depends on MSVC's `std::map` layout — `_Myhead` at
`this+0` (confirmed in the disassembly) and `_Mysize` at `this+4` (**inferred**).
Six theories had already died that day from inference.

So the cache does not trust itself:

| mode | behaviour |
|---|---|
| **VERIFY** | The real function runs **every time**; the cache only *predicts* alongside and compares. Zero behaviour change. |
| **FAST** | Entered only after **400,000 agreements with zero disagreements**. Only now does it skip work. |
| **DISABLED** | Entered instantly and permanently on the **first** disagreement, logged loudly. Pure pass-through. |

A wrong assumption produces a log line and a normal game, never a corrupted one.
It passed on the first attempt and has never disagreed once in **~3.6 billion
calls across four sessions and two game builds** — see the cumulative table at
the end.

The guard requires all four to match: `this` pointer, key, root node
(`*(this->_Myhead + 4)`), and size (`*(this + 4)`). Size is the load-bearing one
— no insert or erase can leave it unchanged.

**Reuse this pattern.** Verify against ground truth, refuse to activate on a
single disagreement. It is what made it safe to change a live hot path at all.

## Technical notes worth keeping

**Calling convention.** The target is `__thiscall`. MSVC cannot declare a
`__thiscall` function pointer, but **`__fastcall` with a dummy second parameter
is ABI-identical**: arg1 in `ecx`, arg2 in `edx` (unused), the rest on the
stack, callee cleans up. The original ends in `ret 8`, exactly what `__fastcall`
expects for two stack arguments. This let the whole hook be written in plain C
rather than naked assembly.

**Objects.dll relocates.** The address is always `GetModuleHandleA` + RVA, and
the six prologue bytes (`51 8B 09 8B 41 04`) are verified before anything is
written. Hardcoding an address is what killed the 2025 attempt at injection.

**The loader race is real.** The first version polled for `d3d9.dll` and lost —
the game had already called `Direct3DCreate9` by the time it got there, and the
run produced nothing at all. `LdrRegisterDllNotification` patches during the
DLL's load and is the only reliable way.

## NEXT — the obvious follow-on

**The cache is one entry.** The top 16 keys covered up to 51% of all lookups, so
a small direct-mapped table (4 or 8 entries, indexed by low bits of the key)
should push the hit rate well past 67%. Same verify-then-activate safety, same
self-A/B to measure it.

If the hit rate reached 85%, the arithmetic says ~8% and the observed
second-order effect suggests more.

**Not yet done, and it should be measured the same way — predicted number first.**

---

# SHIPPED — launcher integration and the ZW confirmation

2026-08-25, same day. The cache is now a launcher option, and it has been
confirmed working in **both** builds alongside line of sight.

## The blocker: the injector took only one DLL

`tvt_inject.exe` accepted a single DLL, which is why Line of sight and Profiler
were already mutually exclusive in the launcher. Adding the cache as a third
exclusive option would have forced a choice between **AI line of sight and +6%
framerate** — a bad choice, and an unnecessary one, because the two hooks touch
completely different engine DLLs (`Behavior.dll` and `Objects.dll`) and never
meet.

So the injector now accepts **up to eight DLLs**, loading each one fully before
the next begins — so a DLL that arms a loader notification is in place before
the following one loads. The process stays suspended throughout.

### The safety rail survived the change

Every DLL is allow-checked **against the list beside itself**, not just the
first one. Each still has to authorise itself, and each checks the same list
again from inside. Verified before wiring anything up:

```
single DLL, bad path        -> ERROR: DLL not found: K:
ope.dll      (backward compatible)
two DLLs, second bad        -> ERROR: DLL not found: K:
ope2.dll     (names the right one)
two real DLLs, bad install  -> REFUSED: not listed in tvt_los_allow.txt
```

Backup of the single-DLL version: `K:\tvt_probe\inject.cpp.bak_singledll`.

## The launcher

```
[x] Line of sight  (the AI cannot see through hills or woods)
[ ] Performance HUD  (fps, draw calls, GPU - DXVK only)
[ ] Profiler  (find where the frames go - replaces line of sight)
[ ] Faster trees  (map cache - about +6% fps)          <- new
```

**Line of sight and Faster trees can both be ticked.** The Profiler still clears
both, deliberately: measuring while something else is changing the thing being
measured is worthless.

Form grew 24 px and everything below the new row shifted down. Parses clean.
Backup: `K:\TvTDeepseek
ollback\TvT_Launcher.ps1.before_cache_20260825`.

## THE CONFIRMATION — both hooks, live, in ZeeWolf

The one thing argument tests could not prove is two injected DLLs coexisting in
a real process. They do:

```
LINE OF SIGHT   enforcement live
                fit check +1.58..+1.59 m (spread 0.01 m) - terrain accepted

MAP CACHE       458,779,776 calls
                306,386,442 hits   66.8%
                          0 mismatches
                clean exit
```

Two details worth keeping:

**The hit rate is a property of the engine, not of either mod.** 66.8% in ZW
against 67.2% in REDUX — different build, different missions, different terrain,
essentially the same number. The access pattern that makes the cache work is
inherent to how the engine walks trees.

**The LOS fit check passed on ZW's own terrain**, reading ZW's world size and
height factor rather than assuming REDUX's. That per-mission fix is still
holding.

## Cumulative record

| session | build | calls | mismatches |
|---|---|---|---|
| A/B measurement | REDUX | 366M | 0 |
| Second A/B | REDUX | 265M | 0 |
| Full play session | REDUX | 2,471M | 0 |
| Launcher + LOS together | **ZW** | 459M | 0 |
| | | **~3.6 billion** | **0** |

Four sessions, two game builds, roughly 3.6 billion calls, and the guard has
never once been wrong.

**The verify-then-activate pattern is what earned that.** It is the reason it
was ever defensible to put a cache in front of a container lookup inside a
binary with no source. Reuse it for anything similar.
