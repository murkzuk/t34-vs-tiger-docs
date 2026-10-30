# LOD distances & the `[0]` always-coarsest bug (2026-08-23)

> **SUPERSEDED IN PART — 2026-10-30.** The "LOD 0 = COARSEST" claim below is backwards; see the
> correction at the foot of this file. The distance tables and the script inventory are still good.


## How LOD works in G5

- LOD geometry (the actual reduced meshes) is **BAKED into each `.ms2` model** — you
  cannot add/improve LOD levels by script.
- LOD switch distances ARE script-controlled: `SetLods([...])` or
  `SetupMesh(model, [distances])` on the mesh component.
- Array semantics: **DESCENDING, far → near**. `[400, 270, 170, 50, 5]` =
  coarsest beyond 400 m … finest within 5 m.
- **LOD 0 = COARSEST.** So `[0]` (single element) = "LOD 0 always" = the tank
  renders at its lowest-detail mesh at every distance. This is the "rubbish" look.

## Full ZW tank LOD table (`Scripts\Units\*.script`)

| Tank | LOD |
|---|---|
| Pz II (SdKfz121) | `[0]` |
| Pz III L60 / 75 L24 | `[0]` |
| Pz IV G (AI summer) | `[360, 180, 120, 80]` |
| Pz IV G (AI winter) | was `[0,200,380,420,580]` (broken ascending) |
| Tiger E1 / Early (playable) | `[0]` |
| Tiger Ausf E (AI) | `[400, 270, 170, 50, 5]` |
| Tiger PzVI AI / AINR | `[300, 170, 50, 5]` |
| Tiger E1 / Mid (AI) | `[0, 80, 60, 40, 30]` |
| Panther A / D | `[0]` |
| StuG 40 | `[400, 270, 50, 5]` |
| StuG 75L24 / F8, SturmHaubitze, sIG-33B | `[0]` |
| Wespe / Marder II / Hummel / Nashorn | `[0]` |
| T-34 (76 & 85) | `[300, 100, 50, 5]` |
| T-34 ChTz / HardEdge / Turret41C | `[0]` |
| KV-1s / KV-1 Zis5 / KV-85 | `[0]` |
| SU-85 | `[400, 270, 50, 5]` |
| SU-122 | `[0]` |
| SU-152 | `[0, 640, 320, 160, 80]` |

## Changes made (all backed up in `K:\TvTDeepseek\rollback\`)

- **Pz II**, 3 variants (`Tank_PNZ_II.script` L679/1071/1462): `[0]` →
  `[300, 100, 50, 5]`. UNTESTED in-game (couldn't find a Pz II in a mission).
- **Pz IV G winter** (`TankPnzIV_G_AI.script` L1250): `[0,200,380,420,580]` →
  `[360, 180, 120, 80]` (the ascending array was genuinely broken — "coarsest
  beyond 0 m" = always coarsest).

## Pz IV G "shocking" look — root cause & the failed swap

- The AI Pz IV G uses a **reduced** mesh: `u_veh_PnzIV_G_AI.ms2` = **11.9 MB**,
  vs the full `u_veh_PzIVG.ms2` = **17.4 MB**. It is lower-poly BY DESIGN (cheap
  AI tanks so many can be fielded).
- The full mesh has a **different joint layout** (turret = `Turret_A` /
  `Turret_A_Crashed` vs the AI mesh's `Commander` / `Commander_crashed`).
- Swapping the AI unit onto the full mesh fixed the look but produced a
  **double-render** (normal + crashed/destroyed both visible), because the AI
  unit's damage system / ConfigSets are written for the AI mesh's joints.
- **Reverted.** Options going forward:
  1. Accept the reduced AI mesh (working as designed).
  2. Push the AI mesh's LOD distances out (cheap, partial — mesh stays low-poly).
  3. Port the full mesh AND re-point the damage/joint code (complex, correct).

## Next

- Test the Pz II `[300, 100, 50, 5]` in-game.
- Pz III is `[0]` too — next candidate for the same one-line fix
  (`TankPzIII_L60Unit.script`, `TankPz_III_75L24Unit.script`).
- Playable-only tanks (`[0]`) are fine to leave — always near the camera.

## Editing rules (reminder)

- `.script` = CP1251; byte-level edits only; verify EF BF BD count stays 0.
- Delete `Cache\Scripts.cache` after any script edit (cold rebuild ~2 min).
- Backups stay in `K:\TvTDeepseek\rollback\`, never inside the game folders.
## CORRECTION 2026-10-30 — the level numbering here is backwards

Everything above about *distances* stands. The line "**LOD 0 = COARSEST**" does not.

Measured from the bytes: each node header carries a **LOD level** field (the first of the four
int32s after the bounding sphere, long mislabelled "flag"). Across G5's 66 models and ZW's 184,
that field equals the node's `_LOD<n>` name suffix on 95.1% of the 3,708 LOD nodes, and
`u_veh_PzVI_LATE.ms2` — the file whose ladder the editor's LOD slider demonstrably switches —
matches on every single node. The base mesh is level 0 and the added levels get **higher** numbers
as they get coarser:

```
Body            3965 verts  = level 0 (the base mesh, no suffix)
Body_LOD1       2026        = level 1
Body_LOD2       1335        = level 2
Body_LOD3        586        = level 3
Body_LOD4        266        = level 4  <- coarsest
```

`Camera.LockLOD()` in the asset viewer agrees: it takes a normalised 0..1 position where 0 is the
finest mesh (see `project_tvt_editor_lod_slider.md`). So **level 0 is the finest, not the
coarsest**, and the sentence "`[0]` (single element) = 'LOD 0 always' = the tank renders at its
lowest-detail mesh at every distance" cannot be right as written.

What is still unverified is how a `SetLods([...])` array maps a distance to a *level*. The
one-element case `SetLods([0])` may well clamp to the coarsest, which would produce the observed
"rubbish" look — but it is not because level 0 is coarse. **Do not cite this note's
"LOD 0 = COARSEST" line; it is superseded.**

Consequence for the changes recorded above: the Pz II (`[0]` -> `[300,100,50,5]`) and Pz IV G
winter (`[0,200,380,420,580]` -> `[360,180,120,80]`) edits were made on the strength of the
backwards claim. The Pz IV G one is defensible either way, since an ascending array is wrong under
any reading. Both remain **untested in-game**, exactly as recorded.
