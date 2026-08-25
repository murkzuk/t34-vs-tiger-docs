# START HERE — snapshot, end of 2026-08-25

Replaces the 2026-08-23 snapshot. Read this first.

## NEXT SESSION, IN THIS ORDER — agreed with the user

### 1. The ZW sweep

ZeeWolf 2015 got almost none of 2026-08-25's attention, and the one thing that
*was* checked (`LodForShadowHide`) turned out to be already correct there, while
the grass alpha turned out to be **wrong** there. So neither "ZW is fine" nor
"ZW needs the same fixes" is safe to assume — it has to be checked item by item.

Compare ZW against every fix REDUX has had, and report which apply:

- `AlphaBlendDistanceFactor` — **known already: see item 2**
- the `ActivateMove` / `ActivateMovement` typo (REDUX had it in C1M2 and still
  has it in C2M3 line 932)
- the `UnitGroup.script` patrol-recursion guard (patch 01) — does ZW's
  `OnOrderFulfilled` have the same 2026-08-18-style change, and therefore the
  same crash?
- the sun-vector normalisation / glare bug
- the undeclared-static-assignment class (**already swept clean in ZW**, 4957
  classes, none — no need to repeat)
- tree `ModelLOD`, `ShadowFar`, `FogDensity` values

Method that works: byte-compare the two trees file by file and eyeball the
diffs, rather than grepping for one thing at a time.

### 2. The grass alpha fix for ZW

ZW has **two** grass zone maps and only the winter one was ever fixed:

```
ZW  CBaseGrassC1        (summer)  line 281:  0.4            <- UNFIXED
ZW  CBaseWinterGrassC1  (winter)  line 529:  0.8  //jm 0.4  <- already raised
REDUX (single class)              line 276:  0.9
```

Summer is most of ZW's missions, and `0.4` fades grass over the last **60%** of
draw distance — the see-through-tanks effect, plus more blended pixels. The
engine's own hardcoded default is `0.8`, so G5's `0.4` was arguably always
wrong.

- **Summer `0.4` -> `0.9`** — the real fix. User agreed.
- **Winter `0.8` -> `0.9`** — consistency only, marginal, user's call.
- **`1.0` is forbidden**: the engine computes `1.0 / (1.0 - factor)`.

Byte-level edit (CP1251), backup outside the game folder, clear
`M:\T34vsTiger_ZW2015\Cache\Scripts.cache`.

### 3. Phase 2 proper

`THE_PLAN.md` says Phase 2, 4 of 7. The unowned item worth taking:
**the five "stock noon" missions** — pick a time of day per mission and apply
the recipe that already exists. Largest remaining visible-quality gap, and
pleasant work after a day of profiling.

Also open in Phase 2: fog reaching distant objects (DeepSeek's), and tree height
without the redwood effect (unowned).

---

## WHERE THINGS STAND

**Framerate: 36-40 -> 66-76**, and the reason is known rather than guessed.
The one thing that made the difference has **not** been identified — best
remaining guess is a stale `Cache\Scripts.cache` releasing earlier edits. No
further theories are being built on it.

### Shipped today

- **C1M2 crash-to-desktop FIXED.** Patrol recursion; 6,451 stack overflows -> 0.
  Both parked patches applied and confirmed by a full mission played to an end.
- **Map-lookup cache, +6.3%**, launcher option "Faster trees", confirmed in both
  builds alongside line of sight. ~3.6 billion calls, 4 sessions, 0 mismatches.
- **Injector now takes up to 8 DLLs** so LOS and the cache run together.
- Tiger shadow-hide bug fixed (worth zero fps, still a real bug), and that whole
  bug class swept clean in both builds.

### Facts not to relearn

- **TvT is CPU-bound with the GPU idle** — `Present` 0.1%. Never treat TvT
  framerate as a GPU problem.
- **Noise floor is ±4%.** Anything smaller is not a result.
- **DXVK vs dgVoodoo is irrelevant** (wrapper 0.0%); the `.script` interpreter
  is ~2%; **all the AI is ~0.5%**, so never hold back an AI feature for
  performance.
- **`AlphaBlendDistanceFactor` is where the alpha fade BEGINS**; engine computes
  `1/(1-x)`; its own default is 0.8; **never 1.0**.
- A 4 KB profiler page holds ~17 functions — **never attribute a page to a
  function** without the 64-byte fine histogram (`prof.cpp`, `FINE_BASE`).

### Method lessons that cost real time today

- **Predict the number before the run**, so a hypothesis can fail. Six died on
  2026-08-25; two were killed by the user's own observation, not by analysis.
- **A parked fix that is not on the board does not exist.** The C1M2 crash was
  diagnosed on the 21st, written on the 22nd, and crashed a live session on the
  25th because it was tracked nowhere.
- **When something experimental is attached and the game crashes, read
  `execution.log` first.** It named the cause immediately; real effort went into
  suspecting the injected cache instead.

### Tooling built today (all in the docs repo `Tools/`)

`drawcall_probe` (CPU or GPU, one run) · `prof.cpp` with a 64-byte fine
histogram and a full-module concentration curve · RTTI maps for all three DLLs
(4778 named vfuncs in Objects.dll) · the self-A/B pattern for any future
performance claim.

### Open, not started

- Multi-entry cache (4-8 entries vs the current 1) — Phase 1 overflow, park it
  unless Phase 2 stalls
- `ActivateMove` typo in C2M3 line 932; `patch_04_MissionsMenu.md` unreviewed
- ~12 ms/frame of the CPU frame still unlocated
- Fog rollout to C1M3/C2M2/C2M4 — DeepSeek's, still `FogDensity 0.0013`
