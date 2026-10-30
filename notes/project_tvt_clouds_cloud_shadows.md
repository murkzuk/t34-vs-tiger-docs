# Clouds + cloud shadows — REDUX vs ZW

Status: PORTED to `Campaign_2\Mission_1` (2026-08-31). **Clouds VERIFIED in-game**
(user confirmed "I see the clouds"). **Cloud SHADOWS: NOT working — dormant native
feature (see below).**

## Cloud shadows — investigated, the `CloudShadow` boolean is a red herring
- User confirmed clouds render but NO shadows.
- Binary check: "CloudShadow" in the engine (Objects.dll/exe) is a **native CLASS
  name** (`?AVCCloudShadow@@`), registered as component `CID_CloudShadow` with a
  `CScriptUser<CCloudShadow>` wrapper and a `GenerateCloudShadowTexture` function.
  It sits in the internal object-type list (GridObject/SimpleObject/GroupObject/
  CloudShadow/BoundingGroup/...), NOT a boolean setting.
- So `GameSettings.script:49  final static boolean CloudShadow = true; //jm -
  Hidden WV.exe feature` is a MISUNDERSTANDING: it is a boolean named after a
  class; the engine does not read it as a settings flag. It does nothing.
- Neither REDUX nor ZW references `CCloudShadow` in any script or mission — the
  feature is dormant in BOTH builds (ZW clouds also have no shadows).
- Activating it = reverse-engineer where `CCloudShadow` is instantiated and what
  calls `GenerateCloudShadowTexture` (disassembly) — a parked-style RE task, not
  a "turn on". No script-facing method (e.g. SetCloudShadow) was found in the
  string table.
Same pattern as rain/snow: **ZW has it, REDUX never got it.**

PORTED: copied `c_cumulus1.tex` ZW→REDUX (341.5 KB) + inserted the `Cloud_Cum`
block into REDUX C2M1 `Content.script` (backup `Content.script.bak.20260831_110702`).
Cloud object placed at (4622.55, 4904.53, 1466.88) = REDUX player pos (4893.44,
4507.04) + ZW's cloud-vs-player offset (−270.89, +397.49), keeping ZW's rotation
and Boxes. IMPORTANT: REDUX and ZW C2M1 maps differ (player Y 4507 vs 8535), so
the position was translated — not copied blindly.

## What they are
1. **Clouds** — a cloud layer of cumulus sprites, placed per-mission as a
   `CCloud` GameObject (`Scripts\Common\Clouds.script`, class `CCloud extends
   CEditable, IObject`, classificator "CLOUD"). Texture `Textures/c_cumulus1.tex`
   (a 128×128 grid of 16 cumulus pages). 5 altitude bands (Height0–4) each with
   Colour/Size/Density/Material-page, plus a global SpriteSize/Density/Ambient
   and cloud-placement "Boxes".
2. **Cloud shadows** — `GameSettings.script:49`
   `final static boolean CloudShadow = true; //jm - Hidden WV.exe feature`.
   A global engine toggle (already ON in REDUX — a previous session found it).

## REDUX current state (M:\T34vsTiger)
- `Clouds.script` PRESENT (with "jeff" tweaks: DefaultSpriteSize 80, Density 1.0;
  ZW uses 50 / 0.7).
- `Textures/c_cumulus1.tex` **MISSING** ← the blocker.
- No `CCloud`/`Cloud` object in ANY REDUX mission Content.script.
- `CloudShadow = true` already set (jm). Does nothing yet — there are no clouds
  to cast shadows.
→ **REDUX renders no clouds at all.**

## ZW current state (M:\T34vsTiger_ZW2015)
- `Textures/c_cumulus1.tex` PRESENT (341 KB).
- `Clouds.script` PRESENT (SpriteSize 50, Density 0.7).
- Missions DO place cloud objects, e.g. ZW C2M1 Content.script:107:
  `["Cloud_Cum", "Cloud", "CCloud", new Matrix(...), [props...]]` with
  SpriteSize 1800, Density 0.08, 5 Height/Color/Matid/Size/Dens bands, Boxes,
  RenderClouds true, NearAtten/FarAtten.
- ZW GameSettings.script has NO CloudShadow line (REDUX's `true` is an addition).

## Port recipe (to get clouds + cloud shadows in REDUX) — NOT DONE
1. Copy `Textures\c_cumulus1.tex` ZW → REDUX (341 KB). ← the only missing asset.
2. Paste the `Cloud_Cum` GameObject block (above) into a mission's Content.script.
3. CloudShadow is already `true` in REDUX — should light up once clouds render
   (needs in-game confirmation; "Hidden WV.exe feature" implies the engine path
   is present).

## Sky texture map (2026-08-31, USER-CONFIRMED)
- **Sky_01 and Sky_02 are SUNNY days** (user confirmed). Sky_05/06/11 = overcast.
- The current `Sky_XX.tex` files were REPLACED with high-res sky PHOTOS from
  **Call to Arms** (Digitalmindsoft). The ORIGINAL TvT skies are the `.orig`
  files (e.g. `Sky_01.tex.orig`). User restored Sky_01 to original this session.
- Lesson: the material "diffuse" brightness is NOT a reliable sunny/overcast
  signal (Sky_02 = sunny but has diffuse 0.0). Trust the texture/eyeball, not
  the material table.
- NOTE: clouds were also added to C1M5 (Sky_05, overcast) by mistake — C1M5 is
  NOT a sunny day (sun elevation was used, not sky texture). To be corrected.

## Notes / caveats
- The full ZW cloud object block is captured in this session's transcript and
  readable at `ZW\Missions\Campaign_2\Mission_1\Content.script:107–151`.
- REDUX's Clouds.script "jeff" tweaks (bigger, denser default) only matter if a
  mission omits SpriteSize/Density; ZW's mission blocks set both explicitly, so
  port the block as-is.
- Same Phase 4 "turn on what's already there" family as rain/snow.
