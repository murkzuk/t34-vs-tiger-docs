# Line of sight on ZW

*2026-08-20. The AI line-of-sight hook runs on ZW. Nothing was rebuilt for it —
ZW's `Behavior.dll`, `Engine.dll` and `UI.dll` are SHA-256 identical to
REDUX's, so both hooks land on the same addresses.*

## Running it

Desktop shortcut **ZeeWolf 2015 (line of sight)**, or:

```
K:\tvt_los\play_zw.bat
```

- ZW must be listed in `K:\tvt_los\tvt_los_allow.txt` (it is).
- Settings: `M:\T34vsTiger_ZW2015\tvt_los.ini` — **its own file**, separate
  from REDUX's, because the two need different calibration.
- Log: `M:\T34vsTiger_ZW2015\tvt_los.log`.
- Nothing on disk is modified; launching ZW normally gives a stock ZW.

## What had to change before it worked

**The world size could not be assumed.** The tooling hardcoded 9000 m. ZW's
missions run 9000 to 36000 — see [Mission_Inventory.md](Mission_Inventory.md).
Now read per mission from `MatrixWidth`.

**Nor could the terrain filename.** ZW names its heightfields `hmap1.raw` and
declares the path in `WorldMatricies.script`. The mission scan now recognises a
mission by having a `WorldMatricies.script` at all.

**The heightfield is mapped, not read.** On the 36 km map it is 32 MB, and
asking a 32-bit process for that as one contiguous heap block while it builds a
forest is antisocial. It is a read-only file mapping now.

**The fit check rejected a correct terrain.** It required every observer's
height offset under 3.0 m — the band REDUX's models occupy. ZW measured
+3.30..+3.31 m and the check threw the terrain away, dropping to watch mode for
a whole session. It now judges by **agreement** (a 0.01 m spread across three
separated tanks cannot happen on the wrong map) plus a wide sanity range. A
genuinely wrong terrain misses by tens of metres.

## The calibration: ZW's forests are 13x thinner

This is the ZW-specific fact worth keeping.

| map | forest area | trees planted | density |
|---|---|---|---|
| REDUX Berezov | 9.4 km² | 40,473 | **4,310 /km²** — one per 232 m² |
| ZW KurskMission | 463.7 km² | 155,375 | **335 /km²** — one per 2,985 m² |

One tree every 55 metres. That is scattered parkland, and you can see across it
— but 29.4% of that map is painted zone 11, which the model calls dense conifer
and treats as opaque at 12 m. Every kilometre-range sight line clipped a few
hundred metres of "forest" and was refused absolutely: **368 of 368 gate checks
refused**, and the player's gunner would not engage a Pak at 1600 m.

**`sight_scale = 1300`** in ZW's ini — the measured 13x, not a guess. The
tooling's ceiling was 500 and had to be raised to 5000 to allow it.

Tree counts come free from `execution.log`:

```
[STForest] 155375 trees generated
```

**Known limitation:** `sight_scale` is per *install*, but planting density is
per *mission*. 1300 was measured on `KurskMission`. The campaign missions are
painted 60–76% vegetation against Kursk's 36%, so they may well need a
different figure. Reading the `STForest` count and the painted area per mission
and calibrating automatically is the obvious fix and is not built.

## Canopy depth: grazing the treetops is not ploughing through them

Found from a play report — two tanks on opposite slopes, trees in the valley
below, plainly visible to each other, and the model refused the line.

The profile of that exact line showed the ray running at **390.0 m** while the
treetops reached **393.1 m**. It clipped the top **three metres of a
seventeen-metre canopy**, and the old test charged it as though it were down
among the trunks.

Attenuation now scales with how far below the canopy top the ray actually is —
0 at the crowns, full at ground level. That is also the right shape physically:
the top of a tree is a few thin branches, the mass is lower down.

Effect on the refused line, at increasing `sight_scale`:

| sight_scale | visibility | |
|---|---|---|
| 100 | 0.042 | blocked |
| 500 | 0.531 | visible |
| 1300 | 0.784 | visible |

REDUX was re-checked afterwards and still blocks 63 / 81 / 89% at 400 / 800 /
1200 m, with terrain doing most of the work and foliage the rest — which is the
right balance and the band that was play-tested.

## What it achieves on ZW

From a full session on the 36 km map:

```
490,000 calls, 486,474 seen, 442,579 denied by LOS      91% refused
march: 486,474 lines, 8 us each, 3.95 s = 0.37% of wall time
```

**467 vision calls a second** — fifteen times REDUX's rate, because ZW's
battles are far larger — and the whole thing costs under four seconds in
seventeen minutes. The line-of-sight work is not a framerate cost on ZW. See
[Rendering_And_Framerate.md](Rendering_And_Framerate.md) for what is.
