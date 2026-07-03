# T-34 vs. Tiger: Maya 5 to G5 Engine Asset Export Manual

**Version:** 4.0
**Date:** 2026-07-03
**Authors:** murkz, with Claude Code (Anthropic) assistance (prior drafts by MiniMax Agent)

---

## 1. Overview

This manual documents the G5 Maya export pipeline (`MayaExp.mll` + the `Tools\Scripts\*.mel` suite) and the `.ms2` binary asset format it produces, as groundwork for GitHub issue #12 ("G5 Maya Exporter — how to unpack Mayaexp.mll"), whose real goal is enabling a Blender import/export pipeline for the community.

**Every attribute, command signature, and naming convention in this version was re-verified by directly reading the actual `.mel` files in `Tools\Scripts\` on 2026-07-03** (not inferred, not carried over from a prior draft without checking). Where the previous version (3.1) contained claims that turned out not to match the real source, those are corrected here and noted in the changelog. Anything below still marked `[UNVERIFIED]` or `[INFERRED]` genuinely could not be confirmed from the files available and should not be trusted at face value.

### 1.1 Correcting a premise from the original GitHub issue

`MayaExp.mll` is **not** a proprietary encoded container needing to be "unpacked." Its file header is a completely standard Windows PE32 DLL (`MZ` signature; confirmed via `file`: "PE32 executable for MS Windows 4.00 (DLL), Intel i386, 4 sections"). Maya simply uses `.mll` as the file extension for its native plugin DLLs — this is normal, documented Maya SDK behavior, not something specific to G5. The CGNS_MLL standard the issue links to is an unrelated aerospace/CFD (computational fluid dynamics) file format that happens to share the "MLL" acronym by coincidence — it does not apply here. The correct tooling for this job is a standard native-code decompiler (e.g. Ghidra, free), not a special unpacker.

One genuine build clue: a companion `libguide40.dll` ships alongside the plugin and must be copied to `%SYSTEMROOT%` (per `InitMayaExp.bat`) — this is Intel's OpenMP runtime library, indicating the plugin was built with an Intel C++ compiler. A 2024-revision tutorial (found in the user's own TvT manuals archive, not previously in this repo) also notes a hard dependency on `D3DX9_28.DLL` (DirectX 9.0c runtime) for the plugin to load at all — meaning the plugin likely calls D3DX utility functions internally, a useful clue for anyone decompiling it.

---

## 2. System Requirements and Setup

### 2.1 Software Environment

The pipeline requires Maya 5.0 specifically — the MEL scripts and `MayaExp.mll` were built and tested against it. Newer Maya versions may not run these scripts correctly without adaptation.

### 2.2 Plugin Installation

1. Copy `MayaExp.mll` (in `Tools\`) to the Maya 5.0 plug-ins folder, e.g. `C:\Program Files\AliasWavefront\Maya5.0\bin\plug-ins`.
2. Ensure `D3DX9_28.DLL` (part of the DirectX 9.0c runtime) is present on the system — confirmed by the 2024-revision tutorial to be critical for the plugin to load, even if other DLLs are already present in Maya's `bin` folder.
3. Run `InitMayaExp.bat` (or manually copy `libguide40.dll` to `%SYSTEMROOT%`).
4. Copy the contents of `Tools\Scripts\` to your Maya scripts path (the 2024 tutorial says "copy the contents of the tools folder from the TvT CD to `mydocuments\maya`").
5. Load the plugin via Window > Settings/Preferences > Plug-in Manager (or `loadPlugin` in the Script Editor).

**Outstanding question, not resolved by this pass**: no `G5Exp.mel` or shelf-initialization script was found anywhere in `Tools\Scripts\`. `shelf_G5Engine.mel` (below) defines the shelf button layout as a MEL proc, but nothing in the available files calls it automatically — how the shelf actually gets created on a fresh Maya install is unconfirmed.

---

## 3. The "ClassName" / Script Class Name field — corrected

**The previous version of this manual described a "G5Entity marker system"** — locator nodes with a `ClassName` attribute, created via a `createG5Entity` command, forming a scene-hierarchy-driven behavior-linking system. **After re-reading every `.mel` file in `Tools\Scripts\`, no such command, node type, or attribute exists anywhere in the available source.** This appears to have been an inference (possibly extrapolated from the "Script Class Name" text field seen in the export options dialogue, below) presented with more confidence than the evidence supported.

What is actually confirmed: `exportG5Resource` (see Section 9) takes a single `$ClassName` / `$ScriptClassName` string parameter **per export operation**, entered once in a text field in the export dialogue (`MS2ExportPlugin.mel`'s `ms2ScriptClassName` field, labelled "Script Class Name"). This is a whole-scene/whole-export setting passed straight to the native export command, not a per-object Maya attribute set on individual nodes. There is no evidence of a hierarchical per-object "entity" marker system in this codebase's MEL layer. If such a thing exists, it would have to live inside the compiled `.mll` itself with no MEL-side exposure — genuinely possible, but unconfirmed and not something to design a Blender importer around without further evidence.

---

## 4. Mesh Asset Workflow

### 4.1 Setting Mesh Properties

`addMeshProperties` (in `addMeshProperties.mel`) is the command that registers every engine-specific attribute on a selected mesh/joint/transform node. Run it on the current selection:

```mel
addMeshProperties;
```

It only adds an attribute if the node doesn't already have it (checks via `attributeExists` first), and applies the full attribute set only to `transform`-type nodes that aren't joints; joints only get `DoNotExport`.

### 4.2 Mesh Attribute Reference — corrected against source

The following is the **complete, verbatim list** from `addMeshProperties.mel` — nothing added, nothing omitted:

| Attribute | Type | Default | Notes |
|---|---|---|---|
| `DoNotExport` | bool | false | Also added to joints, not just transforms |
| `IsWalkMesh` | bool | false | Walkable/navigable surface |
| `IsRouterMesh` | bool | false | Likely feeds the same "RouterZone" passability concept already used elsewhere in the shipped game's terrain system (`RouterZone_Test.bmp`) — unconfirmed link, but the naming strongly suggests it |
| `IsCollisionMesh` | bool | false | Physics collision |
| `IsBoneNode` | bool | false | |
| `IsHidden` | bool | false | |
| `IsNear` | bool | false | |
| `LodNumber` | long | 0 (range 0-4) | LOD index; see Section 5 for the real naming convention that drives this |
| `DoNotGenerateShadows` | bool | false | Renamed from an older `IsNonLightingObject` attribute — see `ConvertProp.mel` migration note below |
| `IsNotReciveLighting` | bool | false | Verbatim spelling from source (typo preserved: "Recive" not "Receive") |
| `IsDoorObject` | bool | false | |
| `HasShadowVolume` | bool | **true** | Note the default is true, unlike most other flags |
| `TransparentShadows` | bool | **true** | |
| `IsSelfLOD` | bool | false | |
| `DoNotCastShadow` | bool | false | |
| `DoNotUseInIsection` | bool | false | Verbatim spelling ("Isection" not "Intersection") — matches the live game's own `UseBoxForIsection` field naming convention found in `Common\Intersections.script` |
| `IsNearGeometry` | bool | false | |
| `OnlyCastShadow` | bool | false | |

**Removed from this manual** (present in v3.1, not found anywhere in the actual source): `IsShadowMesh`, `IsBillboard`, `CastShadows`, `ReceiveShadows`. These may have been a reasonable-sounding inference but do not exist in `addMeshProperties.mel` or anywhere else in `Tools\Scripts\`.

**A real schema-evolution clue**: `ConvertProp.mel` is a one-time migration utility that renames an old `IsNonLightingObject` attribute to `DoNotGenerateShadows` on every node in the scene, and copies its value into a *new* `IsNotReciveLighting` attribute. This confirms the schema changed over time — what's now two separate flags (shadow-casting vs. light-receiving) used to be one combined attribute.

### 4.3 Geometry Standards

`triangulate.mel` confirms the export pipeline expects triangulated geometry — it runs Maya's `polyCleanupArgList` (with a fairly aggressive cleanup argument set) followed by `polyTriangulate` before export. This is a real, confirmed pre-export step, not a guess: **the `.ms2` format almost certainly only stores triangles, never arbitrary n-gons or quads.**

---

## 5. Naming Conventions — corrected against source

**The previous version claimed `_1m` for lightmapped meshes, `_col` prefix for collision, and `_LOD[N]` with `LOD0` as highest detail.** Only one of those three is directly evidenced by the source, and even that one is different in detail than claimed.

The real evidence is `LOD_CM_SCRIPT.mel`, in full:

```mel
select -r "*_LOD1"; addMeshProperties; setAttr "*_LOD1.LodNumber" 1;
select -r "*_LOD2"; addMeshProperties; setAttr "*_LOD2.LodNumber" 2;
select -r "*_LOD3"; addMeshProperties; setAttr "*_LOD3.LodNumber" 3;
select -r "*_LOD4"; addMeshProperties; setAttr "*_LOD4.LodNumber" 4;
select -r "*_CM";   addMeshProperties; setAttr "*_CM.IsCollisionMesh" 1;
```

Confirmed naming convention:
- **`_LOD1` through `_LOD4`** suffixes, mapping directly to `LodNumber` 1-4. There is no confirmed `_LOD0` — the highest-detail mesh may simply be the unsuffixed base name (unconfirmed, but consistent with this evidence: `LodNumber`'s own declared range in `addMeshProperties.mel` is 0-4, and 0 is never assigned by this script, implying 0 is the implicit/default "unsuffixed" case).
- **`_CM`** suffix (not `_col` prefix) for collision geometry, setting `IsCollisionMesh = 1`.

**`_1m` for lightmap-requiring meshes is not evidenced anywhere in the available source** — `LightMapsWnd.mel`'s lightmap baking tool takes a folder + numeric parameters (texture size, texels/meter, etc., see Section 8) but nothing there references a naming suffix at all. Treat `_1m` as unconfirmed until real evidence turns up.

---

## 6. Lighting Assets

### 6.1 Setting Light Properties

`addLightProperties` (in `addLightProperties.mel`) registers attributes on selected `transform`-type nodes:

| Attribute | Type | Range/Default |
|---|---|---|
| `DecayValue` | double | 0.0-10.0, default 1.0 |
| `StaticFactor` | double | 0.0-1.0, default 0.0 |
| `GenerateShadows` | bool | default false |
| `IsMask` | bool | default false |

**`IsMask` was missing from the previous version of this manual** — added here, confirmed present in source.

---

## 7. Physics Shape Creation

`createPhysicsShape.mel`'s `createPhysicsShape(int $shapeId)` creates a new Maya node via `createNode BoxShape` (1), `CapsuleShape` (2), or `CylinderShape` (3), then adds two hidden attributes to its transform: `IsPhysicsShape` (bool, true) and `ShapeType` (long, matching the shape ID). This part of the previous manual was accurate and is unchanged here.

---

## 8. Light Maps

`LightMapsWnd.mel` provides a UI wrapper around a native `generateLightMaps(...)` command (and `getMapsFolder`, another native command not defined anywhere in the MEL layer — implemented in the compiled plugin). Confirmed real parameters, all with UI defaults:

| Parameter | Default |
|---|---|
| Maps folder | (via `getMapsFolder`) |
| Texture size | 512 |
| Texels per meter (density) | 20.0 |
| Scale intensity coefficient | 1.0 |
| Refraction coefficient | 100.0 |
| Use smooth shadows | on |
| Smooth coefficient | 0.8 |
| Random samples | 64 |
| Light distance (m) | 10.0 |
| Point light radius (cm) | 2.0 |
| Ambient color | (0,0,0) |
| Intensity curve scale C | 1.2 |
| Intensity curve scale L | 1.0 |

The previous manual's UV-layout requirements section (no overlapping UVs, 0-1 texture space, dedicated UV set) is generic, reasonable Maya lightmap-baking practice but **is not directly confirmed by anything in `LightMapsWnd.mel`** — flagged here as `[INFERRED]`, not verified.

---

## 9. The Export Commands

### 9.1 `exportG5Resource` — two different call shapes found, not yet reconciled

This is a native command (implemented inside the compiled `MayaExp.mll`, not defined in any `.mel` file) invoked from two different scripts with **different argument counts**:

**From `MS2ExportPlugin.mel`'s `TransferModelExportData` (12 arguments):**
```mel
exportG5Resource(
    "Model",              // $Command: "Model" or "Animation"
    $ScriptClassName,
    $ExportModel,
    $ExportSkin,
    $ExportAnimation,
    $ExportLights,
    $ExportPortals,
    $ExportBehaviorInfo,
    $RegionsByJoints,
    $CellSize,
    $ExportShapes,
    $ExportTangentSpace
  );
```

**From `ExportBatch.mel`'s `doExportScene` (15 arguments passed through to `exportG5Resource` itself — the wrapper function declares 17 parameters total, but 2 of them, `$OutpuDirectory`/`$SceneFile`, are consumed locally for `chdir`/scene loading and never forwarded):**
```mel
exportG5Resource(
    $Command,
    $ClassName,
    $ExportModel,
    $ExportAnimation,
    $UseAnimationsByJoints,
    $ExportLights,
    $ExportPortals,
    $ExportBehaviorInfo,
    $RegionsByJoints,
    $CellSize,
    $ExportShapes,
    $LifeHeadExportEnabled,
    $LifeHeadHeadJoint,
    $LifeHeadNeckJoint,
    $LifeHeadClassName
  );
```

Note the differences: the batch version drops `$ExportSkin` and `$ExportTangentSpace` entirely, and adds `$UseAnimationsByJoints` plus three `LifeHead*` parameters (a character head-swap system — see `addHeadProperties.mel`, Section 10). **This is either (a) a MEL command that accepts variable argument counts (common for `MPxCommand`-based Maya plugin commands), or (b) `ExportBatch.mel` is a stale/adapted script — it hardcodes paths like `d:/Projects/Metro2/...` and `d:/Projects/Metro-2/...`, suggesting it may have been reused from a different G5 Software project and not perfectly kept in sync with the T34vsTiger-specific build of the plugin.** Whoever eventually decompiles `MayaExp.mll` should treat this as an open question to resolve empirically (check the plugin's actual `MPxCommand::doIt` argument parsing), not assume either call site is fully authoritative on its own.

### 9.2 The export options dialogue

`MS2ExportPlugin.mel`'s `CreateMs2ExportOptionsWnd` builds the "Model Export Options" window: a "Script Class Name" text field, then checkboxes for Export Model/Lights/Portals/Shapes/Tangent Space, a collapsible "Animation options" section (Export Skin Data, Export Animation Info), and a collapsible "Behavior options" section (Export Behavior Info, "Treat regions by joints", Cell Size slider 0.0-10.0). A separate `CreateAnimExportOptionsWnd` provides an animation-only export path.

### 9.3 Character head system (new in this version — not in v3.1 at all)

`addHeadProperties.mel` adds a modular head/face system, apparently for swappable character heads: `HeadModel` (string), `HeadMuscules` (string, typo for "Muscles" preserved from source), `HeadLinkJointName` (string, default `"HeadLink"`), `NeckLinkJointName` (string, default `"NeckLink"`). It calls a native `getHeadModels` command (not defined in MEL) to enumerate available head models for a dropdown. This connects directly to the `LifeHead*` parameters seen in `ExportBatch.mel`'s extended `exportG5Resource` call (Section 9.1) — evidently a shared, cross-project character system, though nothing in this codebase's own shipped human units (`hum_GermanSoldierRifle`, `hum_SovietTankman`, etc.) has been checked yet for whether this system is actually used here or is dead-in-this-project tooling inherited from elsewhere.

### 9.4 Portal system (new in this version — not in v3.1 at all)

`createPortal.mel`'s `createPortal` command adds `IsClosed` (bool), `IsPortal` (bool, default true), and `ReverseNormal` (bool) to selected geometry, sets `doubleSided` off, and automatically creates a mirrored instance of the geometry with `ReverseNormal = 1` — both the original and the instance get added to a `"Portals"` display layer (auto-created if missing). This is a visibility/occlusion-culling portal system (standard in engines of this era), exported via the `ExportPortals` flag seen in the `exportG5Resource` signatures above.

### 9.5 Command line export

`ExportBatch.bat` confirms the real invocation: `maya -batch -script ExportBatch.mel -log "d:/batch.log"` — not `mayabatch.exe` as the previous version stated (that binary may exist in some Maya versions, but it's not what this codebase's own batch file actually uses).

---

## 10. Material and Shader Setup

This section of the previous manual (v3.1) was checked line-by-line against `AEG5EngineShaderTemplate.mel` and found to be accurate — reproduced here with only minor trims, no corrections needed.

### 10.1 The G5EngineShader

Create via Hypershade or `shadingNode -asShader G5EngineShader`. Confirmed real attributes, organized into the same collapsible sections the shader's own Attribute Editor template uses:

**Common Material Attributes**: `BaseTexture`, `AmbientColor`, `DiffuseColor`, bump mapping (`normalCamera`), `HeightMapTexture` + `Parallax`, `LightMapTexture`, `IsDoubleSided`, `EnvironmentMapTexture`.

**Micro Texture Attributes**: `MicroTexture`.

**Emissive Attributes**: `UseEmissiveEffect`, `EmissiveColor`, `EmissiveTexture`; nested "Emissive Light Attributes": `Intensity`, `DecayRate`, `DecayValue`, `StaticFactor`, `GenerateShadows`, `DirectionSurface`.

**Specular Shading**: `UseSpecularShading`, `SpecularPower`, `SpecularColor`, `SpecularTexture`.

**Transparency Attributes**: `MixingMode`, `Opacity`, `OpacityMap`.

**Special Attributes**: `SurfaceType`, `LightingModel`, `SubstanceType`, `Glossiness`, `Fresnel`, `GroupID`.

**Hardware Attributes**: `UseFilter`. **Radiosity Attributes**: `IsNotUseForTracing`.

Note: `AEshaderSurfaceTypeControl` shows `SurfaceType == 3` is a special case that enables `Intensity`/`DecayRate`/`DecayValue`/`StaticFactor`/`GenerateShadows`/`DirectionSurface` — i.e. some `SurfaceType` value makes the shader itself behave as a light source. The specific numeric meaning of `SurfaceType`'s values (beyond "3 = light-emitting") is not documented anywhere found so far.

---

## 11. Path to a Blender Importer/Exporter — recommended next phases

This manual (Phase 0 of the issue #12 effort) captures everything the plaintext MEL/tutorial sources reveal for free, with zero binary reverse-engineering. It does **not** yet reveal the actual `.ms2` byte-level format — that's the real remaining work. Recommended phases from here:

1. **Phase 1 — empirical byte-level probing**: pick a few of the simplest `.ms2` files already in `Models\` (e.g. a static prop) and look for recognizable structural patterns (magic numbers, size-prefixed chunks, plausible vertex-position float ranges), cross-checked against the known attribute schema above. Similar in spirit to the BMP-format lessons learned elsewhere in this project's terrain work.
2. **Phase 2 — decompilation**: use Ghidra (or similar) on `MayaExp.mll`'s `exportG5Resource` implementation, and/or on whichever compiled engine DLL (`Engine.dll`/`Objects.dll`/`Behavior.dll`) actually *reads* `.ms2` at runtime — not yet identified; a string search for literal `.ms2`/`MS2` text turned up nothing in any of those three, so the runtime loader's filenames are likely built via string concatenation from the `.script` files' own `MeshFile` paths rather than hardcoded.
3. **Phase 3 — implementation**: a Python `.ms2` reader first (validates understanding, useful standalone before any Blender integration), then a writer, tested by round-tripping through the actual Level Editor.

This is realistically a multi-week-plus undertaking, not a single session's work — track it as its own project.

---

## Appendix A: Change Log

**Version 4.0 (2026-07-03)**
Full re-verification against the actual `.mel` source files, prompted by scoping GitHub issue #12. Found and corrected real errors in v3.1: removed four fabricated mesh attributes (`IsShadowMesh`, `IsBillboard`, `CastShadows`, `ReceiveShadows`) not present anywhere in `addMeshProperties.mel`; added eleven real attributes that were missing (`IsRouterMesh`, `IsBoneNode`, `IsHidden`, `IsNear`, `IsDoorObject`, `TransparentShadows`, `IsSelfLOD`, `DoNotCastShadow`, `DoNotUseInIsection`, `IsNearGeometry`, `OnlyCastShadow`); added missing light attribute `IsMask`; corrected the collision-mesh naming convention from a claimed `_col` prefix to the source-evidenced `_CM` suffix, and corrected `_LOD0`-based LOD numbering to the evidenced `_LOD1`-`_LOD4`; flagged the `_1m` lightmap-naming claim as unverified (no evidence found); replaced the "G5Entity marker system" section (not found anywhere in source) with a corrected description of `ClassName` as a single per-export text field, not a per-object attribute; added three previously-undocumented systems found in this pass (character head system via `addHeadProperties.mel`, portal system via `createPortal.mel`, and the `ConvertProp.mel` schema-migration utility); documented that `exportG5Resource` is called with two different, unreconciled argument counts from two different scripts; added the D3DX9_28.dll dependency finding from a 2024-revision tutorial not previously in this repo; corrected the premise that `.mll` needs "unpacking" (it's a standard PE32 DLL); added a phased recommendation for the actual `.ms2` binary format reverse-engineering work still needed.

**Version 3.1 (December 2025)**
Comprehensive update based on cross-referencing with the Visual Guide (v2.2) and additional MEL source code analysis. Added complete doExportScene function signature with all 17 parameters. Corrected createPhysicsShape parameter values (Box=1, Capsule=2, Cylinder=3). Added comprehensive shader attribute documentation with all attributes from AEG5EngineShaderTemplate.mel. Added G5Entity marker documentation (with caveat about missing createG5Entity command) — **this section was removed in v4.0 after further verification found no supporting evidence at all.** Added naming conventions section documenting _1m, _col, and _LOD# standards — **the _col and _LOD0 claims were corrected in v4.0.** Added light map UV requirements. Documented portal export option which is supported in the pipeline. Added initialization documentation (G5Exp.mel). Added command line export documentation.

**Version 3.0 (December 2025)**
Complete revision based on static analysis of MEL source code. All procedural content verified against actual script implementations. Removed all speculative content and replaced with documented facts from `ExportBatch.mel`, `addMeshProperties.mel`, `addLightProperties.mel`, `createPhysicsShape.mel`, and `AEG5EngineShaderTemplate.mel`. Added comprehensive attribute reference tables with verified attribute names and types.

**Version 2.2 (Earlier)**
Removed portal documentation based on user feedback that portals belong to level meshes rather than individual assets. Marked all remaining speculative content with [INFERRED] tags for user reference.

**Version 2.1 (Earlier)**
Fixed Chinese character encoding error. Added [INFERRED] markers to sections containing uncertain information. Removed documented portal workflow from tank model section.

**Version 2.0 (Earlier)**
Initial version with speculative content based on analysis of provided tools structure without access to MEL source code.

---

## Appendix B: Outstanding Questions

1. **`exportG5Resource`'s true native signature** — two different call shapes exist (12-arg vs. 15-arg forwarded), not reconciled. Needs either decompilation of the plugin or empirical testing of both call shapes against the actual T34vsTiger build.
2. **Which compiled engine DLL reads `.ms2` at runtime** — not identified; no literal `.ms2`/`MS2` string found in `Engine.dll`, `Objects.dll`, or `Behavior.dll` via a direct binary string search.
3. **Whether the character head/LifeHead system is used by this project at all**, or is dead tooling inherited from another G5 project (the hardcoded `Metro2`/`Metro-2` paths in `ExportBatch.mel` suggest cross-project tool reuse).
4. **The real `.ms2` byte-level format itself** — this manual only documents the Maya-side authoring/export metadata schema, not the binary format those attributes get serialized into. That's the actual prerequisite for a Blender importer/exporter and remains completely unstarted.
5. **`SurfaceType`'s numeric value mapping** — confirmed that value `3` makes a shader behave as a light source; other values' meanings are unconfirmed.
6. **How the G5Engine Maya shelf actually gets created on a fresh install** — `shelf_G5Engine.mel` defines it, but no initialization script that calls it was found.
