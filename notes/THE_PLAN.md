# The plan — five phases, in order

**Why this exists:** the board has 115 items. That is a list, not a plan, and a
list gives no sense of direction. This is the ladder: what we are doing, in what
order, and how you know a rung is finished.

**Read this first each session.** One phase at a time. Work that belongs to a
later phase gets written down, not started.

Last updated 2026-08-25.

---

## PHASE 1 — Make it RUN right   ✅ COMPLETE 2026-08-29
###### the fog rollout landed 2026-08-29 (DeepSeek): FogDensity 0.0013 -> 0.002
###### on C1M3/C2M2/C2M4, in Content.script. Phase 1 has no open items.

Nothing else is worth doing if the game stutters. And you cannot judge whether a
visual change is good while the framerate is fighting you.

| | status |
|---|---|
| Tree draw distance measured and tuned | **done** — worth 8 fps |
| Shadow distance measured and tuned | **done** — worth 2 fps |
| Fog distance measured and balanced against engagement range | **done** — C1M2 |
| Roll the fog value out to the other dawn/sunset missions | **DONE 2026-08-29 (DeepSeek)** — 0.0013 -> 0.002 on C1M3 / C2M2 / C2M4, in `Content.script`; validated 2026-09-01 |
| REDUX gunsight cost — does it share ZW's? | **closed 2026-08-27, MEASURED** — gunsight 107 fps vs 83 external, *29% faster*, on DOUBLE ZW's `FogFarMax`. Predicted a 3-5x drop; wrong. Nothing changed. The ZW finding does not generalise |
| **Sampling profiler — find the rest of the drop** | **DONE 2026-08-25** — it is `Objects.dll` at 50-54%, not the wrapper (disassembled) |

**ANSWERED — final, 2026-08-25.** Measured, not reasoned. **TvT is CPU-bound
with the GPU idle**: 0.1% inside `Present`, 0.0% inside `Lock`, 99.8% CPU, about
14 ms/frame. 322k triangles/frame is nothing to a modern GPU — it is asleep,
waiting for one core.

Steady-state split (per-window deltas; the raw counters are cumulative):
Objects.dll 50-54%, Engine.dll 20-24%, J5Script ~2%, Behavior.dll ~0.5%,
**D3D9 wrapper 0.0%**.

What each thing actually costs: **grass 1.8 ms (12%)**; **tree *rendering* ~0**
(forest slider at minimum removes 24% of draw calls and changes frame time by
nothing); **Tiger shadow bug ~0** (confirmed by reverting it). **Noise floor is
±4%** — three identical runs gave 66.8 / 69.5 / 68.4 fps.

**The one confirmed target: tree *management* runs whether or not trees are
drawn.** `Objects.dll+0x17D000` is the hottest page in the game and the forest
slider does not touch it (7.54% -> 7.45%). ~10% of the frame is spent deciding
things that are then discarded. Disassembled and identified; the open question
is why it is called so often. **That is Phase 1 overflow, not a Phase 2 item —
it gets picked up when it is picked up, and it is read-only work.**

Framerate went **36-40 -> 66-76** over the session. Which change did that is
**not established**, and no further theories are being built on it.

Write-up: `SESSION_2026-08-25_performance_day.md`.

**PHASE 1 OVERFLOW — done anyway, 2026-08-25.** Having found *why*, the single
hottest function got fixed too: a one-entry cache in front of
`Objects.dll+0x17DAB0` (`std::map::lower_bound`, 41,000 calls/frame), worth a
measured **+6.3%** under controlled self-A/B. Shipped as a launcher option
alongside line of sight, confirmed in both builds, **~3.6 billion calls across
4 sessions with 0 mismatches**. See `project_tvt_maplookup_cache.md`.

**Done when:** you know *why* the framerate is what it is, and it is steady at a
number you are happy with. Not "faster" — *known*.

**The honest state:** 36-40 -> 66-76, and we now know the *shape* of the
problem even though not every millisecond is accounted for. Roughly 12 ms of
the frame is still unlocated. That is fine: the phase asked *why*, not *fix*.

---

## PHASE 2 — Make it LOOK right ◀ WE ARE HERE

The 2001 art is what it is. Everything else — light, time of day, weather,
distance haze — is ours to set, and it is where the biggest visual gain is.

| | status |
|---|---|
| Understand the atmosphere system | **done** — 3-layer model, compass, sun vectors |
| Fix the 20-year sun-vector glare bug | **done** |
| Dawn / sunset on the missions that call for it | **done** — C1M2, C1M3, C2M2, C2M4 |
| Winter overcast rollout | **done** — 4 ZW missions |
| The 5 "stock noon" missions | open |
| Fog reaching distant objects (the `vs_1_1` shader question) | open — DeepSeek |
| Tree height without the redwood effect | open, unowned |

**Done when:** every mission has a time of day that matches its briefing, and
nothing looks obviously wrong at distance.

---

## PHASE 3 — Make the AI FIGHT right

The half that changes how the game plays rather than how it looks.

| | status |
|---|---|
| AI line of sight — terrain and foliage | **done, shipped both builds** |
| The player's gunner keeps a target honestly (retention) | **done** |
| The player's gunner *acquires* honestly | **parked** — 4 dead ends documented |
| Penetration instead of an arbitrary range cap | open — the design is written |
| Buildings block line of sight | open |
| Wingman and follower behaviour | **done** — cruise speed, spacing, order type |

**Done when:** a tank crew sees what it should see, shoots at what it can
actually kill, and its friends behave like a platoon.

---

## PHASE 4 — Turn on what is already there

About twenty features are present in the engine and commented out — troop
transport, track sounds, gun recoil, muzzle flash, the end-mission briefing, the
whole radio-chatter subsystem. Nearly free wins, but each needs verifying: one
"bug" in that list was already disproven.

| | status |
|---|---|
| Systematic WoV-vs-TvT diff | **done** — ~20 features found |
| Triage each one (verify the mechanism before uncommenting) | open |
| Troop transport — the highest-value one | open |
| Radio chatter — subsystem present, content stripped (re-author) | open |

**Done when:** the switched-off features are triaged, and the ones that work are
on.

---

## PHASE 5 — The decision

**Patton's Best.** One tank, day after day, damage and crew carrying forward,
Germans getting nastier as you get better.

This is deliberately NOT phase 1-4 work. It is the thing you decide about **once
those are done** — and the decision is a real fork: yes it is worth months, or
no, TvT is now the game you wanted and that is enough.

**Done when:** you have decided, either way.

**Groundwork already in hand** (whether or not it happens): the mission
generator, the injected hook as a state bridge, shared terrain proven, death
with attribution, and every dawn/sunset mission that already knows what time it
is.

---

## The rule that makes this work

**Finish a phase before starting the next.** Ideas from later phases get written
down — that is what the board and the notes are for — but not started. The point
of a ladder is that you can see which rung you are on.

The one exception: if something in a later phase is **blocking** the current
phase, it gets promoted and this file says why.

## How to see progress

Phase 1: **COMPLETE, 5 of 5**. Phase 2: 4 of 7. Phase 3: 4 of 6. Phase 4: 1 of 4.

That is the number to watch — not the 115.
