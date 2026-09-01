# White / washed-out sky in C1M1 — UNRESOLVED (escalated to Claude)

Status: OPEN (2026-08-31). Handed to Claude.

## The problem
C1M1 (`Campaign_1\Mission_1`) renders its sky as a "lifeless white dull colour".
It is NOT the clouds work — clouds are a separate mission object and are working.

## Ruled out (with evidence)
1. **Sky texture** — user swapped `Sky_01.tex` back and forth (original 2007 vs
   the "Call to Arms" replacement) and the white did NOT change. So it is not
   the sky texture.
2. **Fog** — user tried my suggested fix (darker blue fog + longer FogFar) and it
   stayed white. So it is not fog colour/distance either.
3. (Sanity: the atmosphere BAKE and the CLOUDS DO take effect in-game, so script
   edits are being picked up — this is not a general "edits ignored" problem.)

## Facts gathered
### Sky texture mapping (mission → sky model → texture)
Each mission's `Mission.script` calls `SetMissionSky(new #SkyObject<CSkyNNModel>())`.
Sky models live in `M:\T34vsTiger\Models\Sky_NN.script` (skin → `Textures\Sky_NN.tex`).

| Sky | Missions | Notes |
|-----|----------|-------|
| Sky_01 | C1M1, CF3, CF5, CF6, OldTest, MultiplayerTEST | user says SUNNY |
| Sky_02 | C1M2, CF1, CF4, DM5, DM6 | user says SUNNY |
| Sky_03 | C1M3, DM2 | |
| Sky_04 | C1M4 | |
| Sky_05 | C1M5, DM3 | OVERCAST |
| Sky_06 | C1M6 | OVERCAST |
| Sky_07 | C2M1, DM4 | |
| Sky_08 | C2M2 | |
| Sky_09 | C2M3 | |
| Sky_10 | C2M4, CF2 | |
| Sky_11 | C2M5 | OVERCAST |
| Sky_12 | C2M6 | |

### Sky_01 texture decode (the original, 2048×512, 24-bit, dated 08/05/2007)
- Zenith (top row): RGB (3, 94, 143) = deep blue ✓
- Average: (115, 176, 209) = sky blue ✓
- **Horizon (bottom row): (251, 253, 255) = pure WHITE** ← original fades to white
- `Sky_01.tex.coh` = "Call to Arms" replacement (8192×2048, DXT5, dated 08/04/2024,
  12.6 MB). `.coh` is the preserved high-res version; `.tex` is currently whichever
  the user restored.

### C1M1 atmosphere values (TWO places — note the SunColor alpha discrepancy)
`Content.script` "Atmosphere" property map:
- FogColor (all 4): `(0.976, 0.988, 1.0)` = near-white
- FogNear 10, FogFar 800, FogFarMax 3500, FogMode "Exp", FogDensity 0.0005
- SunDirection `(-0.0324, -0.8474, -0.5299)` → el ≈ 32°
- **SunColor `(1.0, 1.0, 1.0, 0.000000)` — ALPHA = 0** ⚠
- SunIntensity 1.0

`Atmosphere.script` class `CC1M1Atmosphere`:
- FogColor (all 4): `(0.902, 0.961, 1.0)` (slightly less white than Content)
- Same fog distances / Exp mode / el 32°
- **SunColor `(1.0, 1.0, 1.0, 1.0)` — ALPHA = 1.0** ⚠ (disagrees with Content.script)
- AmbientLight `(0.2, 0.2, 0.2, 0.1)` (alpha 0.1)

### DLL / panel log state
`atmos_wysiwyg.log` shows the panel was last driving the **Winter War overcast**
preset (grey sun 0.54/0.59/0.67, grey fog) — so if the DLL is still injected it
would GREY the scene, not WHITE it. The white is therefore probably NOT the DLL.

## Open hypotheses for Claude (in rough priority)
1. **SunColor alpha=0 in Content.script** vs alpha=1.0 in Atmosphere.script —
   which one wins? Could an alpha-0 sun colour break sky lighting (render white)?
2. **Sky dome material lighting** — `Sky_01.script` skin has ambient (1,1,1) +
   diffuse (0.80); with the atmosphere's sun+ambient on top, the sky dome may be
   over-lit to white regardless of texture.
3. **Sky mesh not loading / rendering as untextured white** — `Models/Sky.ms2`
   (does it exist? is it valid?).
4. **Texture/script cache staleness** — the game has a `Cache\Scripts.cache`;
   a stale compiled cache could ignore texture/model changes.
5. **Which atmosphere actually drives C1M1** — `Mission.script` does
   `SetMissionAtmosphere(new #Atmosphere<CC1M1Atmosphere>())` (class defaults)
   AND Content.script has an "Atmosphere" property map. Earlier finding for C2M1
   was "Content.script wins"; confirm for C1M1, especially the SunColor alpha.

## Files involved
- `M:\T34vsTiger\Missions\Campaign_1\Mission_1\Mission.script` (sky = Sky01, line 97)
- `...\Atmosphere.script` (CC1M1Atmosphere)
- `...\Content.script` (Atmosphere property map + our Cloud_Cum block, backup
  `Content.script.bak.20260831_142933`)
- `M:\T34vsTiger\Models\Sky_01.script` (skin/material)
- `M:\T34vsTiger\Textures\Sky_01.tex` + `Sky_01.tex.coh`
- `M:\T34vsTiger\Textures\c_cumulus1.tex` (ported from ZW — clouds work)

## Cloud rollout status (unrelated but adjacent)
- Clouds (CCloud) ported to REDUX: C2M1 ✓, C1M5 (rolled back — overcast), C1M1 ✓.
- Cloud SHADOWS: dormant native feature (see `project_tvt_clouds_cloud_shadows.md`).

---

# SOLVED 2026-09-01 - the sky texture FAILS TO LOAD

## The cause

`execution.log` says it outright:

    Unable to load texture Textures/Sky_01.tex

The dome renders untextured, which is white. That single line explains every
symptom at once: swapping the texture changed nothing (both candidates were
oversized), the fog tests changed nothing, and the material change changed nothing.

**Nobody read the game's own log for this bug.** It had been sitting there.

## Why it fails: dimensions, not format

REDUX has four 2024 sky replacements at **8192x2048**. The engine will not load
them. Format is NOT the issue - the working Sky_02 is also DXT5.

| sky | dimensions | date | missions |
|---|---|---|---|
| Sky_01 | 8192x2048 | 2024-04 | C1M1, CF3, CF5, CF6, MP test, OldTest |
| Sky_04 | 8192x2048 | 2024-10 | C1M4 |
| Sky_07 | 8192x2048 | 2024-10 | C2M1, DM4 |
| Sky_08 | 8192x2048 | 2024-10 | C2M2 |

Every other sky is 2048x512 and loads. **ZW is unaffected** - all its skies are
2048x512, which is why the bug never appeared there.

## The fix

Restored the four `.tex.orig` files (2006-2007 originals, 2048x512) over the
oversized ones. The 2024 hi-res versions are preserved in
`K:\TvTDeepseekollback\skies_2024_hires\` - they could be downscaled to
2048x512 later to keep the better artwork at a size the engine accepts.

## Two corrections to my own reasoning

1. **The `diffuse 0.8017` theory was WRONG.** I argued Sky_01's non-zero diffuse
   over-lit the dome to white. The cache proved the change went live and the sky
   stayed white. **Reverted** to 0.801660 so this run tests one variable only.

2. **The "C1M4 control" was never verified.** I treated C1M4 as a working control
   because the user had not complained about it - and built the whole diffuse
   argument on that. C1M4 uses Sky_04, which is also oversized, so it is affected
   too. An absence of complaint is not a measurement.

## Lesson

For any in-game visual bug, read `execution.log` BEFORE forming a hypothesis. The
answer was one grep away and I went three hypotheses deep without looking.

## My diffuse test was CONFOUNDED - the two variables were never separated

The texture fix was real (`Unable to load texture Textures/Sky_01.tex` is gone
from execution.log) but the sky stayed white. Tracing the chain properly:

    Mission.script:97  SetMissionSky(new #SkyObject<CSky01Model>())
      -> CSky01Model    MeshFile Models/Sky.ms2, SkinClass CSky01ModelSkin
      -> CSky01ModelSkin  material "0" -> Textures/Sky_01.tex

Everything in that chain checks out: `Sky.ms2` holds one node (`SkyDome`) and
carries no material-id strings, so it uses index 0, which the skin defines. There
is no Sky object in `Content.script` at all. `[MaterialManager] Material "19" not
found` sits between LensFlare and EffectsArray in the log - it is the effects
chain, NOT the sky. Red herring.

**The mistake:** I tested `diffuse = 0` while the texture was STILL FAILING TO
LOAD. An untextured dome is white whatever the diffuse is, so that test could
never have shown anything. I then fixed the texture and reverted the diffuse in
the same step. Two variables, never separated, and I called the theory dead on
the strength of an invalid test.

Diffing Sky_01 against the known-good stock Sky_02, diffuse is now the ONLY
difference:

| | Sky_01 (white) | Sky_02 (works) |
|---|---|---|
| ambient | 1,1,1 | 1,1,1 |
| **diffuse** | **0.8017** | **0.0** |
| all other fields | identical | identical |

A sky dome is meant to be unlit: ambient (1,1,1) already shows the texture at full
brightness, and diffuse adds sunlight on top - with SunIntensity 1.0 and SunColor
(1,1,1) that clips to white. Nine of twelve skies use 0.0; the exceptions are
Sky_01, Sky_07 (C2M1, DM4) and Sky_12 (C2M6).

Now set to 0.0 **with a loadable texture in place** - the first valid test of it.

### On the SunColor alpha hypothesis
`Variable SunAlpha not found in script` is the engine asking for a script variable
called `SunAlpha` that exists nowhere in `Scripts/` or the mission. That the engine
wants a SEPARATE `SunAlpha` argues that `SunColor`'s own alpha channel is not the
sun's alpha - which makes the alpha-0 theory less likely, though not disproven.
It stays as the next candidate if diffuse does not settle it.

## Diffuse DISPROVEN by ZW; fog is the live candidate

Diffed the whole sky chain against ZW, which runs the same engine and has a
working sky:

    REDUX:   String RouterMapFile = "Models/Sky.rmap";
    ZW:    //String RouterMapFile = "Models/Sky.rmap";
    REDUX:  diffuse 0.000000   (my change)
    ZW:     diffuse 0.801660   <- and ZW's sky WORKS

`Sky.ms2` is byte-identical between the builds (md5 8d53a17d).

**Both of my theories are dead:**
- **diffuse** - ZW renders correctly at 0.801660, the very value I called the bug.
  Reverted to stock.
- **the missing .rmap** - `Sky.rmap` is missing in BOTH builds, and so is nearly
  every other `.rmap` (only `u_veh_KingTiger.rmap` exists). The working Sky_02 has
  an active RouterMapFile line pointing at the same missing file. Not fatal.

### What fits every observation instead: fog

`fogfix` is active - `fogfix.log` was written at 07:31, the same session as the
07:25 `execution.log`, and it reports **848 fog-on restores, 377 shaders tracked**.
Its entire job is forcing fog back on for geometry the engine had disabled it for.
The sky dome is the most distant geometry there is.

And C1M1 has the whitest fog of any mission:

| mission | FogColor | FogFar |
|---|---|---|
| **C1M1** | **0.976, 0.988, 1.000 - near pure white** | 800 |
| C1M3 | 0.651, 0.761, 1.000 | 450 |
| C1M5 | 0.627 grey | 500 |
| C2M2 | 0.720, 0.750, 0.800 | 450 |
| ZW C1M1 | 0.918, 0.906, 0.859 (warm) | - |

This explains everything the other theories could not: the white is perfectly
uniform with no gradient (fog colour is uniform), near terrain is correctly lit,
distant hills are visibly hazed in the screenshot, texture swaps changed nothing
(fog paints over the result), and the bug appeared right after fogfix shipped on
2026-08-28.

**Test in place:** diffuse restored to stock 0.801660 so fog is the ONLY variable,
and C1M1's four FogColor entries set to an unmistakable blue
`(0.450, 0.620, 0.850)`. Backup:
`K:\TvTDeepseekollback\C1M1_Content.script.bak.*`

- Sky turns BLUE -> confirmed, and the fix is simply a sky-appropriate fog colour
  (fog colour is *meant* to match the sky).
- Sky stays WHITE -> fog is ruled out properly for the first time, and the next
  step is a D3D9 capture of the sky-dome draw itself rather than another theory.

# CONFIRMED AND FIXED 2026-09-01 - the FOG COLOUR paints the sky

User-verified: setting C1M1's FogColor to blue turned the sky blue, **with the
clouds and the gradient visible**. The sky texture was rendering the whole time.

## The mechanism

`fogfix` forces fog back on for geometry the engine had disabled it for (its own
log: **848 fog-on restores, 377 shaders tracked**). The sky dome is the most
distant geometry in the scene, so it takes the fog colour. C1M1's fog was
`0.976, 0.988, 1.000` - near pure white. White fog, white sky.

**Fog colour now effectively controls sky appearance.** That is not a bug in
fogfix - fog colour is *meant* to match the sky - but it means any mission whose
fog colour was left near-white now renders a white sky.

## Why every earlier theory failed

The texture, the material, the mesh, the `.rmap` and the sun alpha were all fine.
Nothing in the sky chain was broken:

- The oversized-texture bug WAS real and IS fixed (`Unable to load texture
  Textures/Sky_01.tex` is gone) - but it was a second, independent bug.
- `diffuse 0.801660` is disproven by ZW, which uses that exact value and renders
  correctly. Reverted to stock.
- `Sky.rmap` is missing in both builds, and in nearly every model script - the
  working Sky_02 points at the same missing file.
- `Material "19" not found` belongs to the effects chain, not the sky.

## Rolled out

Missions carrying the identical stock near-white fog, all now
`(0.450, 0.620, 0.850)`:

| mission | sun elevation | note |
|---|---|---|
| C1M1 | 32 deg | user-verified blue |
| C1M4 | 32 deg | atmosphere byte-identical to C1M1 |
| C2M3 | 25 deg | one entry was hand-edited to a 3-component form |
| C2M6 | 45 deg | |

**C1M2 left alone** - its fog is warm near-white (0.953, 0.953, 0.871, luminance
0.947) on a dawn mission, which is plausibly intentional haze. Flag for the user
rather than change.

Backups: `K:\TvTDeepseekollback\*_Content.script.bak.20260901_0747*`

**Note:** `Campaign_2/Mission_3/Content.script` is **pure LF**, not CRLF (verified
against the backup: 0 CRLF, 6065 LF, before and after). Line endings are per-file
in this project - always check before editing.
