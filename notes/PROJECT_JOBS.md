# TVTPP — Full jobs list (all work, all owners)

Compiled 2026-08-29 from THE_PLAN.md, TODO.md, and this week's notes. Sorted by the
5-phase plan. **[ ]** = open, **[x]** = done.

---

## PHASE 2 — Make it LOOK right (current phase)

- [x] ==Understand the atmosphere system (3-layer, compass, sun vectors)==
- [x] ==Fix the 20-year sun-vector glare bug==
- [x] ==Dawn/sunset rollout — C1M2, C1M3, C2M2, C2M4==
- [x] ==Winter overcast rollout — 4 ZW missions==
- [x] ==Fog reaching distant objects (fogfix) — DeepSeek, both builds==
- [x] ==Stock-noon mission: C2M1 ZW (golden dawn + briefing + v0.260828b)==
- [x] ==Stock-noon mission: C1M1 ZW (06:15 clear morning)==
- [x] ==Stock-noon missions: **C1M4** (10:00 morning), **C2M3** (sunset), **C2M6** (dawn breakout) — all done 2026-08-29==
- [ ] Tree height without the "redwood" effect — **parked 2026-08-29**. SGeometry fully mapped (branch verts `SGeometry+0x90`, count `+0x84`, Z=up; fronds `+0x60`). Blocker: ANY hook on `GetGeometry` — even a bare passthrough — makes trees cull/pop by camera angle; cause unknown. See `project_tvt_tree_height_getgeometry_plan.md` Step 3 for the unresolved candidates.
- [ ] **Dust see-through wheat** — diagnosed; fix = sort the transparent pass (Claude)
- [ ] **Distant trees transparent to tanks** — same family as dust (Claude)
- [ ] **Terrain LOD — distant tanks float above ground, worse in REDUX** — plan recorded
- [ ] **Camera port REDUX→ZW** — FOV 90°, momentum 0.01, shake off, calm commander mouse. Started, rolled back to isolate the tree issue; re-apply (ZFar change was NOT the tree cause)

## ==PHASE 1 — Make it RUN right (answered 2026-08-25)==

- [x] ==Tree draw distance measured + tuned (8 fps)==
- [x] ==Shadow distance measured + tuned (2 fps)==
- [x] ==Fog distance measured + balanced (C1M2)==
- [x] ==Sampling profiler — it's Objects.dll at 50-54%, CPU-bound, GPU idle==
- [x] ==Map-lookup cache (Objects.dll hot function) — +6.3%, both builds==
- [x] ==Fog rollout to remaining dawn/sunset missions (C1M3 / C2M2 / C2M4 FogDensity==)

## PHASE 3 — Make the AI FIGHT right

- [x] AI line of sight — terrain and foliage (shipped both builds)
- [x] Player gunner target retention (honest)
- [x] Wingman/follower behaviour (cruise speed, spacing, order)
- [ ] Player gunner *acquisition* — parked, 4 dead ends documented
- [ ] Penetration instead of arbitrary range cap — design written, not built
- [ ] Buildings block line of sight
- [ ] `CAutoCommanderComponent` acquisition / best home
- [ ] Replace `RadarMaxDistance` with "can I get through?"
- [ ] Tune sight-through distances against play
- [ ] Cache and stagger ray-tests (per-observer, not per-frame)
- [ ] **LOS hook "Behavior.dll never loaded"** — 60s window; fix = loader notification (Claude)

## PHASE 4 — Turn on what is already there

- [x] Systematic WoV-vs-TvT diff — ~20 commented-out features found
- [ ] Triage each one (verify mechanism before uncommenting)
- [ ] Troop transport (highest-value one)
- [ ] Radio chatter — subsystem present, content stripped (re-author)
- [ ] Muzzle flash / gun recoil / end-mission briefing / track sounds (from the ~20)

## PHASE 5 — The decision (Patton's Best)

- [ ] Decide whether to build it — one tank, persistent damage/crew, escalating AI
- Groundwork already in hand: mission generator, hook state bridge, shared terrain, death attribution

---

## Claude's open backlog (TODO.md, not phase-owned yet)

- [ ] One-map dynamic campaign (theatre layer / Falcon-4 bubble) — build two missions on shared terrain first
- [ ] Operation Citadel: Berezov recreation (Panzer Elite) — positions extracted, triggers + objectives + facing not done
- [ ] Steppe template / bigger quick-mission template (built, not fully used)
- [ ] Control settings not saving (GitHub issue #3)
- [ ] Compass / heading indicator (parked, reverted)
- [ ] Gun emplacement geometry (waiting on hand-placed reference)
- [x] ==**Shadow visible through terrain ridges** — unsolved, 3 attempts reverted==
- [ ] T-34/76 (`CTankT34_76_42Unit`) make playable
- [ ] `TankPzVI_LATE` second Tiger variant (stats in Piercing.script, no unit)
- [ ] Tiger II cut-content roster / King Tiger ghosts (King Tiger itself now done + posted)
- [ ] Machine-gun penetration modeling (abandoned experiment)
- [ ] Tiger 3D animation gaps (Maya work, not scripting)
- [ ] AutoCommander false→float bug (likely compiled DLL, needs disassembly)
- [ ] Documentation gaps (schema open questions: IsMissionFullCompleted, 5th tuple element, SOID_MissionController surface)

## Friendly-fire / classification (from prior snapshot, still open unless Claude closed them)

- [ ] Friendly-fire: 42/102 units lack `BehRadarMask`
- [ ] `GunFlak88` classification
- [ ] Threat model (binary acquisition hook)

## Content / units

- [ ] **Pz IV G rollout** — 13 missions backed up, not swapped
- [ ] **Pz III `[0]` LOD fix**
- [ ] (King Tiger unit class — done, posted 2026-08-28)

---

## Done this week (2026-08-24 → 08-29) — for the record

- Fog on distant tanks (fogfix) — both builds, launcher toggle
- C2M1 ZW golden dawn + historical briefing dateline + version bump
- C1M1 ZW 06:15 clear-morning historical TOD
- King Tiger finished + posted to the ZW thread (forum) — with Claude + DeepSeek credited
- Dust bug diagnosed (D3D9 probe: wheat writes depth, dust doesn't; render-order fix handed to Claude)
- LOS hook timeout diagnosed (60s Behavior.dll window; handed to Claude)
- Terrain LOD floating-tanks issue identified + plan recorded
- Discord log entries: fog, shadows, Kurtenki dawn

## Rule

One phase at a time (THE_PLAN.md). Progress number to watch: **Phase 1: 4/5 · Phase 2: ~9/16 · Phase 3: 3/9 · Phase 4: 1/~8 · Phase 5: undecided.**
