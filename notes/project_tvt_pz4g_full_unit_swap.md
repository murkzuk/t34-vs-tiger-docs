# Pz IV G "shocking LODs" — full-unit swap (2026-08-23)

## The bug

AI Pz IV Gs in ZW missions looked "shocking" (low-poly) because they spawn the
**reduced** AI unit `CTankPnzIV_G_AIUnit` → `u_veh_PnzIV_G_AI.ms2` (**11.9 MB**),
not the full `u_veh_PzIVG.ms2` (**17.4 MB**).

## The fix (user's idea — correct)

Point missions at the **full** unit `CTankPzIVGUnit` instead. It is a **complete AI
unit**, not a player stub:

- `SetupBehavior(new #VehicleBehavior<CTankPzIVGBehavior>())` ✓
- `AITankVehicle<CTankPz4GManualControl>` ✓
- `SetupWeapon(...)` MG + main gun ✓
- damage code → `Turret_A_Crashed` — matches the full mesh's joints ✓ (so **no
  double-render**, unlike swapping the mesh inside the AI unit)

Bonus: `CTankPnzIV_G_AIUnit` has a copy-paste bug (its MG damage reads
`TankPzVIAusfEMachineGunDamage` = the TIGER's, instead of `TankPzIVAusfGMachineGunDamage`);
the full unit is correct.

## Rollout state — PARTIAL (tooling blocked the batch)

Replace `CTankPnzIV_G_AIUnit` → `CTankPzIVGUnit` in `Content.script`:

| Mission | Status |
|---|---|
| CustomMissions\Panther_M1 | ✅ swapped, user-verified "much better" |
| Campaign_1\Mission_1 | ✅ swapped |
| Campaign_1 M2–M6 | ⏳ backed up, NOT swapped |
| Campaign_2 M2, M3, M5, M6, M7 | ⏳ backed up, NOT swapped |
| CustomMissions\KurskMission2/3/4 | ⏳ backed up, NOT swapped |

All files backed up to `K:\TvTDeepseek\rollback\` (stamp 20260823-163737 + single
C1M1/Panther_M1 backups). Nothing is broken — the unswapped missions just still use
the (working, lower-poly) reduced unit.

### Tooling blocker (for next session)

Batched pwsh writes to `M:\` (escalated `danger-full-access`) fail with
`Error: spawn EPERM`. Single-file escalated writes work; non-escalated loops work.
So the remaining swaps must be done **one file per pwsh command** (single-file
pattern works), or via the `edit` tool after a prior `read` (the `Content.script`
files are pure ASCII, so the UTF-8 edit tool is safe for them).

## Winter

Winter missions (`CWinterMission1/2/3`) use `CTankPnzIV_G_AI_WUnit` — there is **no
full winter model** (winter is only a skin on the reduced mesh), so winter stays as-is.

## Dawn rollout research (Phase 2) — started, not applied

The 12 campaign missions' briefings (`Resources\Mission*.rsr`) **state the kick-off
time + weather**. Most missions already match (dawn 07:00, sunset 19:30, overcast).
Open items:
- **C1M2 has `FogFar = 3.0` in Content.script** (near-zero visibility — bug; its
  Atmosphere.script says 500).
- 5 "stock noon" missions (C1M1, C1M4, C2M1, C2M3, C2M6) could be refined.
- C1M3 is on `Exp2` + `FogFar 1500` (odd for a sunset) — review.
