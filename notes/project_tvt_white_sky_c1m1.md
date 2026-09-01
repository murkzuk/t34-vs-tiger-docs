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
