# Atmosphere / Lighting / TOD — plan + audit (2026-08-22)

Task from the user: make each mission's lighting/atmosphere/TOD (A) historically correct
and (B) as good as the G5 engine allows. Every mission folder has `Atmosphere.script`;
the SAME params also appear in `Content.script`.

## WoV reference (G:\WoV) — the finished-engine gold standard

WoV (the completed sibling on the same engine) is the reference:
- ALL 10 WoV missions use ONE consistent daylight preset, sun vector
  `(0.172057, 0.907307, -0.383653)` with comment `// 02` — and it is a PROPER UNIT
  VECTOR (length 1.000 exactly).
- WoV writes colours as readable `/255` fractions with comments, e.g. fog
  `(124/255, 140/255, 154/255)` = clean blue-grey haze — almost exactly the
  "sky-tinted shadows (122,140,156)" value the user already found in ZW work.
- WoV's `CCommonAtmosphere` base class was carried to TvT essentially unchanged
  (only `DistanceToSun` differs: 20000 vs 5000). So the ENGINE can do it; the mess is
  in TvT's mission overrides.

## AUDIT RESULT 1 — 100% of TvT missions have non-unit sun vectors

Correct = unit length (1.000). All 34 TvT missions are BAD. Distinct broken groups:
- len 0.3427: (-0.005952, -0.155542, -0.305348)  -> C1M1, C1M4, C2M1, C2M3, C2M6, CF3,
  CF5, CF6, DM4, MultiplayerTEST
- len 0.2259: (-0.051952, -0.155542, -0.155348) -> all MyMission/* (Berezov, Kursk02-04,
  Mission1, QuickMission, Steppe*, SteppeTemplate) + OldTestMis
- len 1.0531: (0.99, -0.08, -0.35)               -> C1M3, C2M4, CF2, DM2
- len 1.2456: (-0.99, 0.67, -0.35)               -> CF1, CF4, DM5, DM6
- len 0.3855: (-0.105195, -0.105554, -0.355535)  -> C1M5, C1M6, C2M5, DM3
- len 1.1981: (-0.69, 0.87, -0.45)               -> C1M2 (unique)
- len 0.4181: (0.32, -0.18, -0.2)                -> C2M2 (unique, "// Lowered sun angle")

The CHANGELOG claims "non-unit sun-direction bug fixed in 10 more mission files" — the
audit shows the campaign + MyMission files still carry it. Fix = normalise each vector to
unit length (direction preserved), WoV's `(0.172, 0.907, -0.384)` as the daytime baseline.

## AUDIT RESULT 2 — Content.script has a SECOND atmosphere block, out of sync

C1M2 `Content.script` L22-45 has an `"Atmosphere"` object with EMPTY type fields
(`""`, `""`) and a DIFFERENT param set that disagrees with `Atmosphere.script`:
- Content.script: `FogFar = 3.0`, `FogDensity = 0.003`, `AntiSunAngle = 10.0`
- Atmosphere.script: `FogFar = 500.0`, no FogDensity, no AntiSunAngle
This is the documented "Content.script Atmosphere type mismatch" (7/12 missions). Two
sources of truth that don't agree = the game's lighting is partly whatever wins. Must be
reconciled before any aesthetic tuning.

## PLAN

### Phase 1 — structural fixes (foundation)
1a. Reconcile Content.script Atmosphere block vs Atmosphere.script (fix empty type
fields; make values agree).
1b. Normalise every sun vector to unit length.
1c. Decide FogMode vs FogNear/Far vs FogDensity semantics (Exp uses density; most
missions declare FogFar/FogFarMax and no FogDensity).
1d. Learn what IsIllumination / IsSunVisible actually toggle (night support?).
Deliverable: per-mission current-vs-intended table + backup zips. Read-only first.

### Phase 2 — historical correctness (A)
Research each battle's real date/time/weather -> map to dials:
TOD -> SunDirection+SunColor+AmbientLight+FogColor; season -> sun height+hue;
weather -> FogFar/FogFarMax (visibility) + FogColor* + WindVector + ShadowColor.
Deliverable: target-atmosphere spec table for approval before edits.

### Phase 3 — engine realism (B)
- Learn how numbers reach the screen (small RE/experiment pass).
- Fix fog-not-applied-to-objects (OPEN; likely a hook, like LOS work).
- Sky/horizon tuning (AntiSunColor, HorizontPos, EnableHorizontAdjustment).
- Shadows per weather (ShadowColor = the proven lever; ShadowFar, TerrainShadowPower,
  TreeLightKoef).
- Test under BOTH DXVK (play) and dgVoodoo (editor).

### Phase 4 — rollout (trust rules)
One mission, one param-group, one play-test. Before/after screenshots (SH_*.bmp).
Backups in rollback kit (zip), cache cleared, user as last gate. CHANGELOG + VersionID
per change. Tune ONE reference mission, then copy the recipe.

HEADLINE: WoV gives the correct math + finished palette; the audit shows TvT is 100%
broken on sun vectors and has a dual-source Content/Atmosphere mismatch. Phase 1 is the
safe foundation; Phase 2 is research + a lookup table; Phase 3's fog-on-objects is the one
hard job (likely a hook).

## Backup
Rollback zip: K:\TvTDeepseek\rollback\atmosphere_2026-08-22.zip (all Atmosphere.script +
Content.script, structure-preserved). Created before any edit.

## PILOT RESULT + DISCOVERY (2026-08-23)

Applied the one-line sun-normalisation pilot to C2M2 Content.script
(SunDirection 0.99,-0.67,-0.4 -> 0.775787,-0.525028,-0.35, the engine's own suggested
unit vector). Backup verified byte-identical before edit; U+FFFD=0 after; cache cleared.

RESULT (user-verified in-game):
1. Worked - mission loads clean.
2. 'Incorrect sun direction' warning is gone (0 in execution.log).
3. INADVERTENTLY FIXED A SUN GLARE BUG - user: "the sun must have been too close to us".
4. "I actually see the sun! That is a first."

DISCOVERY (CORRECTS THE CHANGELOG): the non-unit sun vector is NOT purely cosmetic. The
CHANGELOG (2026-07-03) claimed "normalized to length 1, so lighting is unchanged" - that
is WRONG. The engine places the sun at SunDirection * DistanceToSun; a non-unit vector
(length ~1.26) put the sun ~26% off and broke the lens-flare/blindness so it rendered as
glare instead of a visible sun disc. Writing the unit vector resolved the sun into a
proper visible disc.

IMPLICATION: this one-line fix is a VISIBLE improvement in every mission (all 34 carry a
non-unit sun), not cosmetic cleanup. Priority raised. Each mission's correct value comes
straight from the engine's own log warning ("make to ...").

FOLLOW-UPS: roll the same fix across the other 33 missions (carded, one-at-a-time or
sweep, at the user's pace); investigate DistanceToSun (TvT 2000 vs WoV 20000) as the next
"sun realism" lever.
## C2M2 = atmosphere test bed (decided 2026-08-23)

Decision: use C2M2 (Campaign 2 Mission 2) as the SINGLE test bed for all further
atmosphere/lighting improvements, rather than sweeping the other missions. Rationale:
- It is already the "experiment" mission - hand-tuned comments in Atmosphere.script:
  "// Lowered sun angle for early dawn", "// Reduced from 5000 for realistic dawn
  visibility" - but those edits went into Atmosphere.script, which the engine IGNORES
  (runtime reads Content.script; proven by the sun warning coming from Content.script).
- Single-mission tuning = Phase 4's "tune ONE reference mission to perfection, then copy
  the recipe".
- The user play-tests each change in C2M2; when it is perfect, copy the whole tuned
  parameter set to the other missions.

NEXT (in order):
1. Nail "which file is authoritative at runtime" on C2M2 (SunDirection already proven =
   Content.script; confirm fog/colours too; determine whether Atmosphere.script is dead).
2. Make C2M2 actually LOOK like early dawn (its stated intent) - proper dawn sun
   direction + dawn colours, all in Content.script.
3. Then DistanceToSun (TvT 2000 vs WoV 20000), fog-on-objects, shadows - further realism
   tests, one at a time, each play-tested.
## Dawn tint fix (2026-08-23): warm highlights + COOL shade

After the dawn port, the user reported: lighting looks great, but track marks, dust and
exhaust smoke went "off white". Cause: the dawn recipe set AmbientLight (the SHADE fill)
to warm brown (0.180, 0.161, 0.140). Neutral-white effects that sit in shade (dust, smoke,
track marks - not directly sun-lit) picked up the warm tint.

PRINCIPLE (records for future TOD work): real dawn = WARM highlights + COOL shade. The
warm half is SunColor (orange sun) + warm fog; the cool half is AmbientLight (blue-grey
shade). Setting BOTH warm washes out neutral-white effects. Keep AmbientLight cool
(original 0.156863, 0.203922, 0.243137 = blue-grey) and only warm SunColor/Fog.

FIX APPLIED: AmbientLight reverted to cool (0.156863, 0.203922, 0.243137) in C2M2
Content.script. Result: white dust/smoke/track marks restored; dawn contrast (warm sun vs
cool shade) actually improved. This is now the canonical dawn recipe for C2M2.

DISCOVERY (engine): the sun warning showed a FIXED "make to" value (0.775787, -0.525028,
-0.35) regardless of input - the engine has a fixed expected sun elevation (~20.5 deg),
not just "unit length". Changing sun ELEVATION via SunDirection alone still warns; the
warning is cosmetic if the game renders correctly (which it does). Source of the fixed
value not found in scripts/binary - likely derived at runtime (anti-sun angles or native).
## AntiSunAngle / AntiSunHorAngle - understood (2026-08-23)

The ANTI-SUN is a SECOND directional fill light (sky bounce from the anti-solar point).
Direction set by TWO ANGLES, not a vector:
- AntiSunAngle = elevation (Base default 30.0)
- AntiSunHorAngle = azimuth/horizontal (Base default 0.0)
Passed to native SetAntiSunDirectionAngle / SetAntiSunDirectionHorAngle
(BaseAtmosphere.script L144-145). Exact angular convention (0 = which compass, sign,
elevation-from-horizon vs zenith) is NATIVE - unknown without in-game test or binary RE.
The anti-sun also has colour (AntiSunColor), intensity (AntiSunIntensity), specular
(AntiSunSpecularIntensity) - a full secondary light. It is the sky fill that tints
shaded/neutral surfaces (second "off white" suspect after AmbientLight).

Values: most missions Angle=10/HorAngle=105; C1M3=180/180; C1M5/C1M6/C2M5/DM3=30/105;
MyMission/* omit HorAngle (default 0); WoV omits BOTH (default 30/0 - finished game never
overrode anti-sun direction).

THREE-LAYER ATMOSPHERE MODEL (key structural finding, corrects earlier "Atmosphere.script
is dead" claim):
1. Content.script "Atmosphere" block = DATA override (wins for keys it lists).
2. Atmosphere.script class fields (CC2M2Atmosphere > CCommonAtmosphere > CBaseAtmosphere)
   = fallback for keys NOT in Content.script.
3. BaseAtmosphere defaults = fallback for keys in neither.
So Atmosphere.script is PARTIALLY live: the dawn designer's SunSpecularIntensity(0.8),
AntiSunSpecularIntensity(0.0), TerrainShadowPower(4.0), DistanceToSun(2000),
WindVector(0,1.5,0), IsSunVisible, IsLightEnabled DID apply (keys not in Content.script);
their SunDirection/SunColor/Ambient/FogColor/intensity edits did NOT (keys in
Content.script). BaseAtmosphere.GetDefaultProperties() (33 keys) is the definitive
atmosphere schema.
## WIN CONFIRMED (2026-08-23): track marks 100% correct

User-verified in-game: the AmbientLight revert (cool shade 0.156863, 0.203922, 0.243137)
fixed the off-white track marks 100%. Warm highlights + cool shade principle holds.
(Pending: dust/exhaust smoke still to be checked - AntiSunColor is the standby next lever
if they are still slightly tinted.)
## C2M2 DAWN REFERENCE RECIPE (locked 2026-08-23, user-confirmed better than stock)

Final Content.script "Atmosphere" block values (MD5 CB552EA905EE61CB7D4D9273CDD68F22):
  AmbientLight  (0.156863, 0.203922, 0.243137)   <- COOL shade (the "off white" fix)
  SunColor      (1.000000, 0.749020, 0.294118)   <- orange dawn
  SunIntensity  0.350000
  SunDirection  (0.815587, -0.551964, -0.173648) <- low ~10deg, unit length
  ShadowColor / StencilShadowColor (0.345098, 0.419608, 0.466667)  <- warm
  ShadowFar     1050.0
  FogFar        1500.0 ; FogFarMax 3000.0 ; FogMode "Exp" ; FogDensity 0.0013
  FogColor (warm dawn): XPos(0.968627,0.898039,0.749020) XNeg(0.623529,0.698039,0.654902)
                        YPos(0.584314,0.615686,0.666667) YNeg(0.556863,0.678431,0.709804)
  AntiSunEnabled true ; AntiSunColor (0.498039,0.521569,0.607843) ; AntiSunIntensity 0.25
  AntiSunAngle 10.0 ; AntiSunHorAngle 105.0
  TreeLightKoef 0.6 ; TreeShadowLodDistance 35.0 ; SunShines 0.1
  EnableHorizontAdjustment true ; FogNear 1.0

PRINCIPLE (the whole recipe in one line): warm sun + warm fog + COOL ambient. Copy this
block to give another mission the same dawn. Standby lever if dust/smoke ever tint:
AntiSunColor back to original (0.584314, 0.584314, 0.784314).
## AntiSunColor experiment + conclusion (2026-08-23)

A/B test result: track marks (and dust/smoke) are tinted by BOTH AmbientLight AND
AntiSunColor.
- bright BLUE AntiSunColor (0.584, 0.584, 0.784, stock) -> off-white track marks
- MUTED AntiSunColor (0.498, 0.522, 0.608, dawn designer's value) -> clean white marks

CORRECTED PRINCIPLE for dawn: cool shade comes from a COOL AMBIENTLIGHT, NOT a bright
blue anti-sun. The anti-sun must stay MUTED/DIM (it over-lights neutral-white effects
when bright). So: warm sun + warm fog + cool ambient + DIM anti-sun.

FIX: reverted AntiSunColor to muted (0.498039, 0.521569, 0.607843) - restores clean white
track marks. The dawn designer's muted anti-sun was correct all along; the "cool shade"
half lives in AmbientLight only.

LEVER MAP (now fully understood for neutral-effect tint):
- AmbientLight -> flat shade tint (cool = clean white effects)
- AntiSunColor -> sky-fill tint (keep MUTED, not bright blue, or effects go off-white)
- AntiSunIntensity -> fill strength (dim for dawn is fine)
## TERMINOLOGY CORRECTION (2026-08-23) - track marks are DARK, not white

Correction from the user: track marks should be DARK EARTH, not white. The bug was them
turning WASHED-OUT WHITISH. "100% correct" = dark again (not white). So the lever map's
goal is: keep track marks DARK / not washed-out. Dust and exhaust smoke ARE meant to be
whitish-grey (they are white by nature); track marks are NOT. The fix (cool AmbientLight +
muted AntiSunColor) keeps track marks dark and dust/smoke neutral - which is what the
user confirmed as correct.
## FOG-ON-OBJECTS investigation (2026-08-23)

Findings:
- Fog is PER-SHADER, baked into compiled .fxo files as FogFar/FogDensity params.
- ALL visible-geometry shaders HAVE fog: terrain (ChunkedTerrainMesh/Grass/ForestStripe),
  SceneMesh_* (static objects), SkinMesh1/4_* (skinned UNITS = tanks), PlanarShadow*
  (blob shadows). Only ShadowMesh_ST / SkinShadowMesh_ST (stencil volumes) lack it - they
  do not need it.
- So tanks CAN fog; the shader supports it. The engine just is not feeding fog to units
  at draw time (or Exp fog is broken - the 4x FogDensity test changed nothing at all).

TWO leading theories:
1. Fog uniforms set for the terrain pass but not the object/unit pass.
2. FogMode "Exp" silently broken/falls back - fog values not reaching shaders.

FIX PATH: renderer-level, not a script value. Likely a D3D9-level hook (like the LOS
hook but on d3d9.dll) to inspect the fog render state per draw call (terrain vs tank),
then force it for units.

KEY OBSERVATION to split the theories (user to check in-game): do distant BUILDINGS haze
or stay sharp like tanks? buildings-sharp = fog broken for all objects (renderer-wide);
buildings-haze-tanks-dont = unit-specific (skinned mesh pass).
## TRACK-MARK BRIGHTNESS - lever map + change (2026-08-23)

Track marks are particle effects; brightness is script-controlled via SetBaseColor
(RGB = darkness, alpha = opacity). GLOBAL, not per-mission (lives in Scripts\Common):
- GROUND marks: EffectsBase.script:587  CGroundUnitTraceEffect  SetBaseColor(0.33,0.28,0.28,0.35)
- FOREST marks: Effects.script:1531     CForestUnitTraceEffect  SetBaseColor(0.40,0.38,0.27,1.0)
- ROAD marks:   Effects.script:1483     CRoadUnitTraceEffect    SetBaseColor(0.52,0.48,0.35,rand)
- FOREST DUST:  Effects.script:1505     CForestUnitDustTraceEffect SetBaseColor(0.48,0.45,0.35,0.3)

Indirect dial: atmosphere lighting (warm ambient + bright anti-sun over-lights these
particles - the earlier "off white" issue). Now fixed (cool ambient + muted anti-sun).

CHANGE APPLIED 2026-08-23: ground track marks darkened - SetBaseColor
(0.33,0.28,0.28,0.35) -> (0.25,0.21,0.21,0.35). Backup:
K:\TvTDeepseek\rollback\EffectsBase.script.bak_2026-08-23. (Forest/road not changed yet.)

NOTE: user reports no distant houses in C2M2 within first 10 min - the fog observation
test (buildings haze or not) needs a different mission/session.
## Track marks - "barely changed" (PARKED 2026-08-23)

User verdict: the ground track-mark darkening (0.33,0.28,0.28 -> 0.25,0.21,0.21) barely
changed the look. PARKED for now (moving to fog/mist). Future options when revisited:
go darker still (e.g. ~0.18,0.15,0.15), lower the alpha 0.35, or check whether the
particle is being lit (m_LightingParticle) which overrides SetBaseColor. Backup exists:
K:\TvTDeepseek\rollback\EffectsBase.script.bak_2026-08-23.
## ATMOSPHERE UNDERSTANDING - CONSOLIDATED (2026-08-23, READ THIS FIRST)

SOLID (tested, working):
- 3-layer model: Content.script "Atmosphere" block (data, wins) > Atmosphere.script class
  fields (fallback) > BaseAtmosphere defaults (~33 params, BaseAtmosphere.GetDefaultProperties).
- SUN: SunDirection read from Content.script. Engine normalizes + warns "make to X"
  (cosmetic; X fixed ~20.5deg, source unknown/native). NON-UNIT sun = REAL visual bug
  (sun glare + invisible sun disc), NOT cosmetic - user-verified. Unit-length fixes it.
- LIGHTING: warm highlights (SunColor + warm fog) + cool shade (AmbientLight) + MUTED
  anti-sun (bright blue anti-sun over-lights neutral-white effects). AmbientLight AND
  AntiSunColor BOTH tint track marks/dust/smoke.
- FOG: FogFar drives the terrain haze (PROVEN by mist experiment). FogDensity 4x did
  nothing (Exp likely broken/not wired). Fog baked into ALL visible-geometry .fxo shaders
  (terrain, SceneMesh static, SkinMesh units, planar shadows). FogFar 450 + grey-blue
  colours = natural dawn mist (user-approved "more natural").
- TRACK MARKS: SetBaseColor in EffectsBase.script:587 (ground) etc; GLOBAL not per-mission.
- WoV (G:\WoV) = finished-engine reference: unit sun vector (0.172,0.907,-0.384), clean
  /255 colours, consistent one-preset daylight.

OPEN (known unknowns):
1. AntiSunAngle/AntiSunHorAngle exact convention (elevation/azimuth, 0=direction) - native.
2. The engine's fixed "make-to" sun-elevation source - native.
3. Fog-on-objects (tanks stay sharp in mist) - renderer-pass, likely a D3D9 hook.
4. FogMode "Exp" vs "Linear" - is Exp actually implemented?
5. Night / IsIllumination / IsSunVisible - never tested.