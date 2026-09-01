# Where this stands — 2026-09-01

A stopping point, written so none of it has to be carried in anyone's head.
Everything below is committed and pushed.

---

## Done and verified — safe to forget about

| | |
|---|---|
| **White sky in C1M1** | **SOLVED, user-confirmed.** The mission's `FogColor` paints the sky. Fixed. |
| Sky textures failing to load | Four 8192×2048 replacements the engine cannot load, restored to originals |
| DeepSeek's 25 commits | Merged and pushed — they had sat unpushed for four days |
| AtmosWysiwyg + 9 project notes | Recovered into the repo; they existed nowhere else |
| Map-lookup multi-entry cache | Measured, **no benefit**, closed. Do not build it |

### The white-sky cause, in one line
`fogfix` forces fog back on for distant geometry. The sky dome is the most distant
thing in the scene, so **the sky takes the fog colour**. C1M1's fog was
`0.976, 0.988, 1.000` — near white. White fog, white sky.

Rolled out to the missions carrying that identical stock fog: **C1M1, C1M4, C2M3,
C2M6** → `(0.450, 0.620, 0.850)`. Backups in
`K:\TvTDeepseek\rollback\*_Content.script.bak.20260901_*`.

**Left deliberately alone:** C1M2's fog is warm near-white on a dawn mission
(`0.953, 0.953, 0.871`) — plausibly intentional haze. Your call, not mine.

---

## The dust bug — open, and honestly stuck

**Symptom:** dust makes the wheat see-through. Ground truth you established: stop
the tank → no dust → artefact gone. So the dust is the cause.

### Ruled out WITH EVIDENCE — do not re-try these

| theory | how it died |
|---|---|
| Render-state leak from dust into wheat | Wheat state is **byte-identical** before and after the dust, across all 8 capture windows |
| Draw ordering / "sort the transparent pass" | Dust and wheat **already interleave**. Sorting cannot fix a draw that ignores depth |
| `ZENABLE` forced on | 481 toggles, 33,622 draws forced, **no visual change whatsoever** |
| `ZWRITE=0` forced (dustfix, 08-28) | 31,649 forces, no change — ZWRITE was *already* 0 |
| Additive dust blend | Dust got lighter, hole unchanged. Reverted |
| Hooking `DrawPrimitiveUP` | Dust goes through `DrawIndexedPrimitive`. Red herring |

### What is actually known
- Wheat draws as **single billboards, 2 primitives each**, `WZAT`, blend 5,6,
  `ALPHAREF=0` — so it writes depth while alpha-blended, over nearly its whole quad.
- Peak wheat is only **18 draws per frame**; 87% of frames draw some.
- Gameplay averages ~100 draws/frame (peak 328). Menu averages ~6 but **spikes
  over 30**, which is why probe gates must use ~100, not 30.
- Some effect draws run `ZENABLE=0` — depth testing off entirely — interleaved
  between wheat billboards. Forcing that off changed nothing, so it is a fact
  about the frame, not the cause.

### The one step not yet taken
`dustbisect` — skip one draw class at a time and see what disappears. It finds the
culprit by elimination instead of by theorising. **Built, keys corrected, never got
a clean run.** If anyone picks this up, that is the next move, not a new theory.

---

## Tools, and what state each is in

| tool | state |
|---|---|
| `Tools/DustOrder` (`dust_order`) | **Works.** Trigger capture, frame numbers, rolling windows |
| `K:\TvTDeepseek\dustzfix` | Works; the fix it applies **does nothing**. Keep as a null result |
| `K:\TvTDeepseek\dustbisect` | Built, keys fixed, **untested in a real mission** |
| `Tools/AtmosWysiwyg` | Live sun/fog panel + bake-to-mission. Built and verified |

### Gotchas that cost real runs — worth reading before touching any of this
- **F11 is `CTLCMD_SELF_DESTRUCTION`** (`DefaultControls.script:72`). F9 is the fps
  display. The game binds **F1–F6 and F11**. Free: **F7, F8, F10, F12**.
  *Check `DefaultControls.script` before binding any hotkey.*
- **Read `execution.log` before forming a hypothesis.** The white-sky answer sat in
  it the whole time while three theories were built without looking.
- Probe log paths must be **per-PID**. A fixed path let a throwaway test overwrite
  a real 175 KB gameplay capture.
- **Check the DLL is newer than the .cpp** before launching. One run was wasted on
  a build that was 20 seconds stale.
- A retry loop without `Sleep` produced a **328 MB log** and captured nothing.
- Never learn draw classes during the menu — gate on ~100 draws/frame.

---

## Other open items (unchanged, not touched today)

- Distant trees transparent to tanks — same family as the dust
- Terrain LOD — distant tanks float above ground
- LOS hook "Behavior.dll never loaded" — fix is known
  (`LdrRegisterDllNotification`, already proven in these probes), not yet applied
- Tree height — **parked and blocked**: any `GetGeometry` hook, even a bare
  passthrough, makes trees cull by camera angle
- The four hi-res 2024 sky textures could be **downscaled to 2048×512** to get the
  better artwork back at a size the engine accepts —
  `K:\TvTDeepseek\rollback\skies_2024_hires\`

---

## Honest summary of 2026-09-01

The white sky was a real, weeks-old bug and it is genuinely fixed and confirmed.

The dust work went badly, and mostly not because the bug is hard: four runs were
lost to defects in **my** tooling — the log flood, overwriting the capture, the
probe learning in the menu twice, and binding MARK to the self-destruct key. The
bug itself remains unsolved, with three theories properly killed and one untried
instrument sitting ready.

Nothing here is time-sensitive. It will all still be true whenever anyone comes
back to it.
