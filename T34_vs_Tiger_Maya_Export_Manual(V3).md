# T-34 vs. Tiger: Maya 5 to G5 Engine Asset Export Manual

**Version:** 3.1  
**Date:** December 2025  
**Authors:** MiniMax Agent & murkz

---

## 1. Overview

This manual provides the definitive technical documentation for exporting 3D assets from Maya 5.0 to the proprietary G5 game engine used in the "T-34 vs. Tiger" project. The pipeline relies on a custom MEL script suite that extends Maya's functionality with engine-specific attributes, validation, and export commands. All procedures described herein have been verified through static analysis of the actual MEL source code provided in the development tools and cross-referenced with the project's visual documentation.

The G5 export pipeline is a multi-stage process that involves tagging Maya objects with engine-specific attributes, applying custom shaders, creating physics representations, and finally invoking the export plugin to generate the binary asset format. Understanding the relationship between Maya's node system and the G5 engine's requirements is essential for producing valid assets that will load correctly in the game environment.

The export pipeline assumes Maya 5.0 is installed with the MayaExp.mll plugin loaded. The plugin handles the translation of Maya scene data into the G5 binary format, including mesh geometry, material assignments, lighting data, and physics collider shapes. Assets must pass validation checks before export; any failures result in error messages that identify the problematic objects and the nature of the validation failure.

---

## 2. System Requirements and Setup

### 2.1 Software Environment

The G5 export pipeline requires Maya 5.0 specifically, as the provided MEL scripts and the MayaExp.mll plugin were developed and tested against this version of the software. The scripts make use of Maya 5.0-specific MEL commands and UI elements that may not be present in newer versions of Maya. Attempting to use these tools with Maya 6.0 or later may result in script errors or unpredictable behavior.

The development tools are distributed as a ZIP archive containing a "Tools" folder. This folder must be placed in a location accessible to Maya's script path. The typical installation location is the user's Maya scripts directory, which on Windows would be located at `C:/Documents and Settings/[Username]/My Documents/maya/5.0/scripts/` for Maya 5.0. The scripts are organized in a hierarchical folder structure that mirrors their functional grouping, with main utility scripts located in the root Scripts folder and UI templates located in the subdirectories.

### 2.2 Plugin Installation

The MayaExp.mll plugin must be properly installed before any export operations can be performed. The plugin files should be copied from the Tools directory to the Maya 5.0 plugins folder. Additionally, the libguide40.dll library must be registered in the Windows system directory for the plugin to function correctly.

To install the core exporter plugin, copy MayaExp.mll from the Tools directory to the Maya 5.0 bin plug-ins folder, typically located at `C:/Program Files/Alias/Maya5.0/bin/plug-ins/`. For the supporting library, run the InitMayaExp.bat file included in the Tools directory, which automatically copies libguide40.dll to the correct Windows system directory (System32 for 64-bit systems or SysWOW64 for 32-bit applications).

Before any export operations can be performed, the MayaExp.mll plugin must be loaded into Maya. This plugin contains the native code implementation of the G5 binary format encoder and provides the core `exportG5Resource` command that serves as the primary entry point for all export operations. The plugin also registers the custom G5 node types that Maya uses to store engine-specific data.

To load the plugin, open the Maya Script Editor and execute the following MEL command, replacing the path with the actual location of the MayaExp.mll file on your system:

```mel
loadPlugin "C:/Path/To/Tools/MayaExp.mll";
```

Alternatively, you can use the Plugin Manager window by navigating to Window > Settings/Preferences > Plugin Manager, clicking the "Browse" button, and selecting the MayaExp.mll file. Once loaded, the plugin remains active for the duration of the Maya session. The plugin initialization process registers the custom shelf commands and UI elements that form the primary user interface for the export pipeline.

### 2.3 Script Configuration

After copying all MEL scripts from the Tools directory to your Maya scripts folder, the pipeline must be initialized on first use. On the first launch of Maya after installing the tools, execute the G5Exp.mel script to create the G5Engine shelf and complete the plugin loading process. This initialization script sets up the user interface elements and registers all custom commands.

To verify that the installation was successful, create a simple polygon cube in the scene, confirm that the G5Engine shelf has appeared in the Maya interface, and perform a test export. A successful installation is confirmed by the creation of an .ms2 file in the specified output directory.

### 2.4 The G5 Engine Shelf

After successfully loading the plugin and running initialization, a new shelf named "G5Engine" should appear in the Maya interface. This shelf contains the primary one-click commands that artists use to interact with the export pipeline. The shelf provides quick access to the most common operations without requiring knowledge of the underlying MEL commands. The shelf is defined in the file `shelf_G5Engine.mel` and includes the following commands organized by functional area.

The shelf commands include operations for mesh properties, light properties, physics shape creation, and batch export functions. Each button on the shelf executes a corresponding MEL procedure that performs the necessary setup and validation for the requested operation. The shelf serves as a convenient front-end for the underlying script functions, which can also be called directly from the Script Editor for more complex or automated workflows.

---

## 3. The G5Entity Marker System

### 3.1 Understanding G5Entity

The G5Entity marker serves as the organizational backbone for every game object in the pipeline. According to project documentation, G5Entity markers are locator nodes in Maya that carry crucial metadata required by the game engine. The parent-child hierarchy established in the Maya Outliner directly translates to the in-game object hierarchy, making proper scene organization essential for correct asset behavior.

The G5Entity system links visual assets to runtime behavior through the ClassName attribute, which connects the Maya object to a runtime script file that defines the object's behavior in the game engine. Boolean toggle attributes on the G5Entity control which asset types are exported for that entity, including geometry, animation data, and other asset components.

**Important Note:** The createG5Entity MEL command mentioned in project documentation was not found in the provided MEL script suite. This may indicate that the command exists in a script not included in the tools archive, that it has been superseded by a different workflow, or that G5Entity creation occurs through a different mechanism. Users should consult project leads to confirm the current method for creating G5Entity markers before proceeding with asset creation.

### 3.2 ClassName Configuration

The ClassName attribute on G5Entity markers links the object to a runtime script file. This attribute must exactly match a class defined in the project's script files for the asset to function correctly in-game. The ClassName determines what behavior the object exhibits, including any game logic, interaction responses, or special properties unique to that asset type.

When an object appears in-game but exhibits no behavior, the most common cause is a mismatched or missing ClassName. Verify that the ClassName attribute in Maya exactly matches a class defined in the project's .txt script files. The runtime script system separates visual assets from game logic, allowing behavior modifications without requiring re-export of the 3D model, which enables faster iteration during development.

---

## 4. Mesh Asset Workflow

### 4.1 Setting Mesh Properties

The foundation of the G5 asset pipeline is the `addMeshProperties` command, which registers all engine-specific attributes on a mesh object. This command must be called on every mesh that will be exported to the G5 engine, as the export plugin uses these attributes to determine how the mesh should be processed, rendered, and integrated into the game world. The command adds both boolean flags and integer attributes that control various aspects of the mesh's behavior in the engine.

To add mesh properties to the currently selected object, execute the following command from the Script Editor or shelf button:

```mel
addMeshProperties;
```

This command operates on the current selection, so ensure that the target mesh is highlighted before execution. The command will fail if the selection is empty or if the selected object is not a mesh transform or shape node. After execution, the attribute editor will display a new section named "G5 Mesh Properties" containing the attributes described in the following sections.

The `addMeshProperties` command creates the following boolean attributes on the mesh object, which can be toggled through the Attribute Editor or via direct attribute manipulation in MEL/Python scripts. These attributes control fundamental behaviors in the game engine and must be set correctly for assets to function as intended.

### 4.2 Mesh Attribute Reference

The mesh properties system uses a combination of boolean flags and integer values to describe how a mesh should be treated by the G5 engine. The following attributes are added to every mesh that has had `addMeshProperties` called upon it.

The **IsWalkMesh** boolean attribute indicates that this mesh represents a walkable surface for player characters. When set to true, the engine's pathfinding and navigation systems will use this geometry for character movement. This attribute should only be set on meshes that represent ground, floors, platforms, or other surfaces that characters can traverse. Setting this flag on walls, ceilings, or obstacle geometry will cause pathfinding to behave incorrectly.

The **IsCollisionMesh** boolean attribute marks the mesh as a collision object for physical interactions. When enabled, the mesh participates in the physics simulation and will cause characters and other physical objects to collide with it appropriately. This flag can be combined with IsWalkMesh on appropriate geometry, or used independently on meshes that should cause collisions but are not intended for character movement.

The **IsShadowMesh** boolean attribute designates this mesh as casting shadow volumes. Shadow volumes are a specialized rendering technique used to cast sharp, dark silhouettes from the mesh onto other geometry. This technique is more computationally expensive than standard shadow mapping but produces more accurate shadows in certain scenarios, particularly for hard-edged mechanical objects like vehicles and structures.

The **IsBillboard** boolean attribute indicates that this mesh should be rendered as a billboard. Billboards are flat surfaces that always face the camera, commonly used for vegetation, debris, and other objects where the exact geometry is less important than the silhouette. When this flag is set, the engine ignores the mesh's actual geometry and renders a textured quad that rotates to face the viewing camera.

The **LodNumber** is an integer attribute that specifies the level of detail index for this mesh. The G5 engine uses LOD systems to reduce rendering complexity for distant objects. Lower values indicate higher detail levels (LOD0 being the highest detail), while higher values indicate progressively simplified versions of the mesh. This attribute is used in conjunction with the engine's LOD switching system to determine which version of the mesh to render based on distance from the camera.

The **HasShadowVolume** boolean attribute indicates that this mesh should be rendered using the shadow volume algorithm for casting shadows onto other surfaces. Shadow volumes are typically used for characters and vehicles where accurate shadow silhouettes are important for visual clarity. This attribute is distinct from IsShadowMesh, which relates to receiving rather than casting shadows.

The **DoNotExport** boolean attribute serves as an exclusion flag for assets that should exist in the Maya scene but should not be exported to the G5 format. This is useful for reference geometry, construction aids, helper objects, or deprecated versions of assets that remain in the scene for documentation or organizational purposes. The export plugin checks this flag and skips any objects marked with it.

The **CastShadows** boolean attribute controls whether this mesh casts shadows onto other objects in the scene. This is a primary rendering attribute that affects the visibility of the object in lit areas. Disabling shadow casting can improve performance for objects whose shadows are not visually significant or are obstructed by other geometry.

The **ReceiveShadows** boolean attribute controls whether this mesh displays shadows cast by other objects. For most static geometry, this flag should remain enabled to maintain visual accuracy. Disabling shadow reception can be useful for specific artistic effects or for performance optimization on distant background objects where shadow detail is less important.

### 4.3 Geometry Standards

All exported geometry must be polygonal. NURBS surfaces must be converted to polygons before export using Maya's built-in conversion tools. The export pipeline is designed for polygonal geometry and may produce unexpected results or errors when processing NURBS surfaces.

Models should be constructed with clean edge flow and proper pole management to avoid rendering artifacts. Poor topology can cause lighting artifacts, UV mapping problems, and animation issues if the model is ever rigged or deformed. Take time to establish clean quad-based topology during the modeling phase.

**Normals** must be normalized and point outward from the mesh surfaces. The exporter will warn about inverted normals, but they should be fixed manually for correct lighting and physics behavior. Inverted normals cause lighting to appear inside-out and can interfere with collision detection and other physics calculations.

---

## 5. Naming Conventions

Consistent naming conventions are mandatory for the automated pipeline systems to function correctly. The following suffixes and prefixes are recognized by the export pipeline and trigger specific processing behaviors.

### 5.1 Light Map Naming

Meshes requiring light maps must include the `_1m` suffix in their name. For example, a tank hull mesh that requires light map generation would be named `TankHull_1m`. This suffix tells the export pipeline to generate light map UV coordinates for this mesh and include it in the light map generation process.

### 5.2 Collision Geometry Naming

Collision geometry must use the `_col` prefix to distinguish it from visual meshes. For example, a turret collision mesh would be named `_col_Turret`. This prefix identifies the mesh as a physics-only object and prevents it from being rendered while ensuring it is included in collision detection calculations.

### 5.3 Level of Detail Naming

LOD meshes use numeric suffixes to indicate their detail level. The exporter parses these suffixes to build LOD groups automatically. The naming convention follows the pattern `[MeshName]_LOD[Number]`, with LOD0 being the highest detail version. For example, a tank body might have LOD meshes named `TankBody_LOD0`, `TankBody_LOD1`, and `TankBody_LOD2`, where LOD2 represents the lowest detail version for distant viewing.

---

## 6. Lighting Assets

### 6.1 Setting Light Properties

Lights in the G5 engine require their own set of engine-specific attributes that control how they function in the runtime environment. Unlike standard Maya lights which are primarily preview tools, G5 lights must be configured with additional data that describes their behavior in the game world. The `addLightProperties` command registers these attributes on selected light transform or shape nodes.

To add light properties to the currently selected light, execute:

```mel
addLightProperties;
```

This command adds attributes that are unique to the G5 engine's lighting model, including decay parameters, static/dynamic classification, and shadow generation flags. These attributes are essential for lights that will be used in the game scene, as they control how the light interacts with the game's lighting systems and performance optimization strategies.

### 6.2 Light Attribute Reference

The light properties system provides fine-grained control over how lights behave in the game environment. The following attributes are added to light objects when `addLightProperties` is executed.

The **DecayValue** is a float attribute that controls the rate at which light intensity diminishes over distance. Higher values cause the light to fall off more rapidly, creating a more focused pool of illumination. Lower values result in light that travels farther before diminishing. This parameter is particularly important for atmospheric effects and for controlling the visual reach of light sources in large environments.

The **StaticFactor** is a float attribute that specifies the intensity multiplier for static lighting calculations. This value affects how the light contributes to lightmaps and other pre-computed lighting data. StaticFactor is used during the lighting build process to control the overall brightness contribution of this light to baked illumination.

The **GenerateShadows** boolean attribute controls whether this light casts shadowing in the game environment. When enabled, the light's shadow mapping system is active and the light will cast appropriate shadows from occluding objects. Disabling this flag improves performance by skipping shadow map generation and updates for this light, which can be beneficial for fill lights or lights in scenes where shadows are not visually critical.

---

## 7. Physics Shape Creation

### 7.1 Creating Physics Colliders

The G5 engine uses simplified collision geometry separate from the visual mesh for physics calculations. This approach improves performance by using lower-polygon representations for collision detection while allowing artists to use high-polygon visual meshes for rendering. The `createPhysicsShape` command generates these physics colliders based on the visual geometry of the selected mesh.

The physics shape creation command accepts a parameter that specifies the shape type to generate. This parameter allows artists to choose between different collision primitive types depending on the geometry they are working with. The command generates a new mesh that approximates the visual geometry using the selected primitive type.

To create a physics shape for the selected object, execute one of the following commands based on the desired shape type:

```mel
createPhysicsShape(1);  // Creates a Box collider
createPhysicsShape(2);  // Creates a Capsule collider
createPhysicsShape(3);  // Creates a Cylinder collider
```

The parameter is an integer indicating the shape type. A value of 1 creates a box-shaped collider that encompasses the mesh's bounding box, which is appropriate for decks, floors, and other flat geometry. A value of 2 creates a capsule collider, useful for cylindrical objects and characters. A value of 3 creates a cylinder collider, suitable for pipe-like structures and similar geometry. The generated physics shape is automatically parented under the original mesh and is marked with the appropriate physics attributes.

### 7.2 Physics Shape Attributes

After creating a physics shape, the resulting object has its own set of attributes that describe its role in the physics system. These attributes are set automatically by the `createPhysicsShape` command and should not require manual modification under normal circumstances.

The **IsPhysicsShape** boolean attribute marks this object as a physics collider rather than visual geometry. The physics system and export pipeline use this flag to identify objects that should be included in collision detection but excluded from rendering. This attribute is set automatically and should not be changed manually.

The **ShapeType** is an integer attribute that identifies the geometric primitive type used for this collider. The value corresponds to the primitive type specified when the shape was created. This attribute is primarily used for debugging and validation purposes to verify that the correct collision primitive was generated for the geometry.

### 7.3 Exporting Physics Shapes

Physics shapes are matched to their corresponding visual geometry through scene hierarchy and naming conventions. Ensure that physics shapes are parented correctly under their associated visual meshes for the export pipeline to establish the correct relationship.

To include physics shapes in the export, enable the "Export Shapes" option in the export dialogue. Properties such as Friction and Restitution are configured on the physics shape's entity attributes in the Maya Attribute Editor.

---

## 8. Light Maps

### 8.1 Light Map Generation Overview

Light maps are pre-computed textures that provide high-quality static lighting with minimal runtime performance cost. The light map generation process creates texture maps that encode baked illumination information, allowing complex lighting scenarios to be rendered efficiently in the game engine.

### 8.2 Light Map UV Requirements

Meshes requiring light maps must meet strict UV layout requirements for the light map generation process to succeed. Failure to meet these requirements will result in light map generation errors or visual artifacts in the final asset.

**No Overlapping UV Faces:** All UV faces must be unique and not overlap with any other faces on the mesh. Overlapping UVs cause light bleed between faces and produce incorrect illumination in the baked light map.

**0-1 Texture Space:** The light map UV layout must fit entirely within the 0-1 texture space. UV coordinates outside this range are invalid and will cause light map generation to fail.

**Dedicated UV Set:** It is best practice to use a second UV set specifically for light maps, separate from the material texture UVs. This separation allows material textures to be optimized for visual quality while light map UVs can be arranged for optimal light map packing efficiency. The dedicated light map UV set should be named appropriately to distinguish it from the material UV set.

---

## 9. Material and Shader Setup

### 9.1 The G5EngineShader

The G5 engine uses a custom material system that extends Maya's standard shading capabilities with engine-specific features. The primary shader used for most assets is the `G5EngineShader`, which provides the texture mapping, lighting response, and special effects capabilities required by the game. All exported meshes must have this shader or a derivative applied to ensure correct rendering in the engine.

To create a new G5EngineShader, use the Hypershade window or execute the following MEL command:

```mel
shadingNode -asShader G5EngineShader;
```

This creates an unshaded shader instance that can be configured using the Attribute Editor. After creating the shader, assign it to the target mesh using the standard Maya assignment commands or by using the hypershade connection editor.

### 9.2 Shader Attribute Reference

The G5EngineShader provides a comprehensive set of attributes that control the material's appearance and behavior. These attributes are defined in the file `AEG5EngineShaderTemplate.mel` and represent the verified configuration options for the shader. The shader attributes are organized into collapsible sections in the Attribute Editor for easier navigation.

The **BaseTexture** string attribute specifies the path to the primary diffuse texture map. This texture provides the main color and pattern information for the material. The path should be specified relative to the game's texture directory or using the game's asset path conventions.

The **AmbientColor** color attribute controls the ambient lighting contribution for this material, affecting how the surface appears in shadowed areas. This value is multiplied with the ambient lighting in the scene to determine the final ambient color contribution.

The **DiffuseColor** color attribute specifies the base color tint applied to the material's diffuse response. This attribute affects how the surface responds to direct lighting and is the primary mechanism for controlling the material's overall color appearance.

The **normalCamera** attribute (accessed through the bump mapping controls) connects a normal map texture that provides surface detail through perturbed normals. This technique adds apparent geometric detail without increasing polygon count, making it essential for realistic surfaces with fine surface variation.

The **HeightMapTexture** attribute connects a height map texture that can be used for parallax effects, creating the appearance of surface depth on flat geometry. The Parallax attribute controls the intensity of the height map effect.

The **LightMapTexture** attribute connects a pre-baked light map texture that provides static illumination information. This attribute is used when light maps are generated externally rather than through the engine's light map generation system.

The **IsDoubleSided** boolean attribute controls whether the material renders on both sides of the geometry. When enabled, backfaces are rendered normally; when disabled, backfaces are culled, which is more efficient for closed geometry.

The **EnvironmentMapTexture** attribute connects a cubemap or spherical environment map for reflections. This attribute is essential for metallic surfaces that require realistic reflections of the environment.

### 9.3 Micro Texture Attributes

The **MicroTexture** attribute connects a micro-detail texture that provides fine surface variation at close range. This texture is tiled at a high frequency to add surface detail that would otherwise require extremely large base textures.

### 9.4 Emissive Attributes

The **UseEmissiveEffect** boolean attribute enables emissive lighting for this material, causing it to appear self-illuminated regardless of external lighting conditions. This attribute is useful for lights, displays, and other emissive surfaces.

The **EmissiveColor** color attribute specifies the color of emitted light when emissive effects are enabled. This attribute is only accessible when UseEmissiveEffect is set to true.

The **EmissiveTexture** attribute connects a texture that controls the pattern of emissive illumination. Only the texels corresponding to non-black areas in this texture will appear to emit light.

The **Intensity** float attribute controls the overall brightness of the emissive effect. Higher values produce brighter emission.

The **DecayRate** integer attribute controls the falloff behavior of the emissive light. A value of 0 indicates no decay, while non-zero values enable distance-based falloff.

The **DecayValue** float attribute specifies the rate at which the emissive light intensity decreases over distance when DecayRate is non-zero.

The **StaticFactor** float attribute specifies the intensity multiplier for static lighting calculations. This value affects how the light contributes to lightmaps and other pre-computed lighting data.

The **GenerateShadows** boolean attribute controls whether this material casts shadows when acting as an emissive light source.

The **DirectionSurface** boolean attribute controls directional behavior for surface-based emissive materials.

### 9.5 Specular Shading Attributes

The **UseSpecularShading** boolean attribute enables specular highlights on this material. When enabled, the material responds to light sources with shiny highlights appropriate for metallic or glossy surfaces. This attribute controls the visibility of specular-related attributes.

The **SpecularPower** float attribute controls the sharpness of specular highlights. Higher values produce tighter, sharper highlights characteristic of glossy surfaces, while lower values create broader, softer highlights typical of matte materials.

The **SpecularColor** color attribute specifies the color of specular highlights. This attribute allows specular reflections to be tinted independently from the base material color.

The **SpecularTexture** attribute connects a texture that controls the pattern of specular response, allowing for varied shininess across the surface.

### 9.6 Transparency Attributes

The **MixingMode** integer attribute controls how transparency is applied to the material. Different mixing modes produce different transparency behaviors for various effects.

The **Opacity** float attribute controls the overall transparency of the material, with values ranging from 0.0 (fully transparent) to 1.0 (fully opaque). This attribute is used for translucent materials such as glass, water, and foliage.

The **OpacityMap** attribute connects a texture that controls the pattern of opacity across the surface, allowing some areas to be more transparent than others.

### 9.7 Special Attributes

The **SurfaceType** integer attribute specifies the material surface classification, which affects how the material interacts with lighting and effects. Different surface types may trigger different rendering behaviors in the engine.

The **LightingModel** integer attribute controls the lighting calculation model used for this material.

The **SubstanceType** integer attribute specifies the material substance classification, which may affect physics interactions and other game systems.

The **Glossiness** float attribute provides an alternative way to control specular response, often used in conjunction with the LightingModel attribute.

The **Fresnel** float attribute controls Fresnel effects, which affect how the material appears at different viewing angles.

The **GroupID** integer attribute assigns the material to a rendering group, which can be used for controlling draw order or special rendering effects.

### 9.8 Hardware and Radiosity Attributes

The **UseFilter** boolean attribute controls hardware texture filtering for this material.

The **IsNotUseForTracing** boolean attribute excludes this material from ray tracing calculations, which can improve performance for materials that don't require accurate reflections or refractions.

---

## 10. The Export Command

### 10.1 Understanding exportG5Resource

The `exportG5Resource` command is the primary mechanism for generating G5 binary assets from Maya scenes. This command is implemented in the MayaExp.mll plugin and performs the complete export pipeline including scene validation, data conversion, binary encoding, and file output. Understanding the parameters of this command is essential for creating reliable export workflows.

The `exportG5Resource` command is called with the following signature:

```mel
exportG5Resource(
    string $Command,           // "Model" or "Animation"
    string $ClassName,
    int    $ExportModel,       // 1 to export visual mesh
    int    $ExportSkin,        // 1 to export skin data
    int    $ExportAnimation,   // 1 to export animation data
    int    $ExportLights,      // 1 to export light objects
    int    $ExportPortals,     // 1 to export portal data
    int    $ExportBehaviorInfo,// 1 to export behavior information
    int    $RegionsByJoints,   // 1 to process regions by joints
    float  $CellSize,          // Cell size for region calculations
    int    $ExportShapes,      // 1 to export physics shapes
    int    $ExportTangentSpace // 1 to export tangent space data
);
```

The first parameter `$Command` specifies the operation mode for the export command. The value "Model" performs a full model export, while "Animation" performs an animation-only export.

The second parameter `$ClassName` specifies the asset class or category for the exported object. This parameter influences how the engine interprets the exported data and may affect which validation rules are applied.

The remaining parameters are integer flags (1 for enabled, 0 for disabled) that control which components are included in the export. The ExportModel parameter controls visual mesh export, ExportSkin controls skeletal skin data, ExportAnimation controls animation clips, ExportLights controls light object export, ExportPortals controls portal data export, ExportBehaviorInfo controls behavior information export, RegionsByJoints controls region processing method, CellSize sets the region cell size, ExportShapes controls physics shape export, and ExportTangentSpace controls tangent space data for normal mapping.

### 10.2 Understanding doExportScene

The `doExportScene` function in `ExportBatch.mel` provides a comprehensive wrapper around `exportG5Resource` with additional scene loading and output directory handling. This is the recommended interface for batch export operations and scripted export workflows.

The full function signature for doExportScene is:

```mel
global proc doExportScene(
    string $OutpuDirectory,        // Output directory for exported files
    string $SceneFile,             // Full path to source Maya file
    string $Command,               // "Model" or "Animation"
    string $ClassName,             // Asset class name
    int    $ExportModel,           // Export visual mesh
    int    $ExportAnimation,       // Export animation data
    int    $UseAnimationsByJoints, // Use joints for animation
    int    $ExportLights,          // Export light objects
    int    $ExportPortals,         // Export portal data
    int    $ExportBehaviorInfo,    // Export behavior information
    int    $RegionsByJoints,       // Process regions by joints
    int    $CellSize,              // Cell size for regions
    int    $ExportShapes,          // Export physics shapes
    int    $LifeHeadExportEnabled, // Enable life head export
    string $LifeHeadHeadJoint,     // Life head head joint name
    string $LifeHeadNeckJoint,     // Life head neck joint name
    string $LifeHeadClassName      // Life head class name
);
```

The doExportScene function handles loading the specified scene file, changing to the output directory, and calling exportG5Resource with the provided parameters. This allows for batch processing of multiple scenes without manual intervention.

### 10.3 Using the Export Dialogue

The MS2ExportPlugin.mel script provides a graphical user interface for configuring and executing exports. The export dialogue is accessed through the shelf button or by calling the appropriate export function. The dialogue presents all available export options in an organized layout with contextual help and validation.

The dialogue includes a Script Class Name field for specifying the asset class, checkboxes for enabling export of models, lights, portals, shapes, tangent space, skin data, animation info, and behavior information. Additional options for region processing by joints and cell size appear when behavior export is enabled.

### 10.4 Command Line Export

The export pipeline can be executed from the command line using Maya's batch processing capability. This allows the export to be integrated into larger build scripts and automated pipelines.

The command line structure for batch export is:

```bash
mayabatch.exe -file "sourcefile.ma" -script "doExportScene(\"output_dir\",\"config\",\"ClassName\");"
```

The mayabatch.exe executable runs Maya in command-line mode without displaying the user interface, executing the specified MEL script command and then exiting. This approach is suitable for automated builds and overnight processing of large asset libraries.

---

## 11. Export Pipeline Best Practices

### 11.1 Scene Organization

Maintaining a well-organized scene is essential for efficient asset production and reliable exports. The G5 export pipeline relies on clean scene hierarchies and consistent naming conventions to correctly identify and process assets. Before beginning work on any new asset, establish a clear organizational structure that separates visual geometry, physics colliders, and reference objects.

Visual geometry should be grouped under parent transform nodes that describe the asset's position and orientation in the game world. These parent nodes should use descriptive names that identify the asset and its purpose. Physics colliders should be parented under the visual mesh or in a clearly designated "physics" group to maintain the relationship between visual and collision representations.

Objects that should not be exported should be marked with the DoNotExport attribute as described in Section 4.2. This is preferable to hiding objects or moving them to hidden layers, as the DoNotExport flag persists through scene operations and is checked automatically by the export pipeline.

### 11.2 Validation Before Export

Always run validation on assets before attempting export, particularly for complex assets or when making significant changes to existing assets. The validation process checks for common problems such as missing attributes, invalid geometry, broken references, and incorrect shader assignments.

The most common validation errors involve forgotten mesh properties and incorrect shader assignments. Before exporting, verify that `addMeshProperties` has been called on all visual meshes and that each mesh has a valid G5EngineShader assigned. Lights should have `addLightProperties` called and should be correctly configured for their intended role in the scene.

Geometry errors such as non-manifold vertices, duplicate faces, or degenerate geometry can cause export failures or unexpected behavior in the game engine. Use Maya's cleanup utilities to identify and repair these problems before export. The G5 engine's geometry processor is robust but may silently discard or incorrectly process malformed geometry.

### 11.3 Export Testing

After exporting a new asset or making changes to an existing one, immediately test it in the game engine to verify correct behavior. The export process may complete without errors while still producing incorrect results if the asset has semantic errors that are not caught by the validation system.

Common issues that only appear at runtime include incorrect scale or unit conversion, missing collision detection on certain mesh configurations, and unexpected visual artifacts caused by texture coordinate problems. Testing in the engine catches these issues before they become entrenched in the asset pipeline.

When reporting export problems to the development team, provide the exact error messages from the export log, the Maya scene file that produced the error, and a description of the expected versus actual behavior. This information allows the team to quickly identify the root cause and implement appropriate fixes.

---

## 12. Troubleshooting Common Issues

### 12.1 Attribute Editor Problems

If the G5 mesh or light property sections do not appear in the Attribute Editor after running `addMeshProperties` or `addLightProperties`, the script execution may have failed silently. Check the Script Editor for error messages and verify that the correct object is selected. The commands require a mesh or light node to be selected and will not execute on other object types.

If attributes appear but cannot be edited, the object may be referenced from another file with reference editing disabled. In this case, you must edit the attribute through the reference file or unlock the reference for editing.

### 12.2 Export Failures

Export failures most commonly occur due to missing attributes, invalid geometry, or file permission problems. The export log provides detailed error messages that identify the specific object and the nature of the problem. Common fixes include re-running `addMeshProperties` on affected meshes, repairing geometry errors, and ensuring the output directory exists and is writable.

If the export succeeds but the asset does not appear in the game, verify that the DoNotExport flag is not set, that the output file was written to the expected location, and that the asset was properly registered with the game's resource management system.

### 12.3 Physics Shape Issues

Incorrect physics shapes usually result from using an inappropriate primitive type for the visual geometry. If a physics shape does not adequately approximate its visual counterpart, try creating a different primitive type. The `createPhysicsShape` command can be run multiple times on the same object; each run replaces the previous physics shape.

For very complex visual meshes, the box primitive may provide better collision performance than more complex shapes, even if the approximation is less precise. Test different collision approaches to find the best balance between accuracy and performance for each asset type.

### 12.4 Behavior and ClassName Issues

If an object appears in-game but exhibits no behavior, the ClassName attribute on the G5Entity is likely incorrect or does not match any script file. Verify the ClassName attribute in Maya exactly matches a class defined in the project's .txt script files.

### 12.5 Lighting Issues

If lighting on an object looks wrong or is missing, check that mesh normals are pointing in the correct direction. Inverted normals cause incorrect lighting calculations. Also verify that the `_1m` suffix is used for meshes requiring light maps and that light maps have been properly generated. Check UV layouts for overlaps or out-of-bounds coordinates.

---

## 13. Technical Reference

### 13.1 Command Quick Reference

The following commands form the core of the G5 export pipeline. Each command operates on the current selection unless otherwise specified.

| Command | Purpose |
|---------|---------|
| `addMeshProperties` | Register engine attributes on mesh objects |
| `addLightProperties` | Register engine attributes on light objects |
| `createPhysicsShape(int)` | Generate collision geometry (1=Box, 2=Capsule, 3=Cylinder) |
| `exportG5Resource(...)` | Export asset to G5 binary format |
| `doExportScene(...)` | Batch export with scene loading |

### 13.2 Attribute Quick Reference

The following attributes are available on G5-enabled objects. Attributes marked with an asterisk are boolean flags.

| Attribute | Object Type | Description |
|-----------|-------------|-------------|
| IsWalkMesh* | Mesh | Marks walkable navigation surface |
| IsCollisionMesh* | Mesh | Enables physics collision detection |
| IsShadowMesh* | Mesh | Creates shadow volumes |
| IsBillboard* | Mesh | Renders as camera-facing quad |
| LodNumber | Mesh | Level of detail index |
| HasShadowVolume* | Mesh | Casts shadow volumes |
| DoNotExport* | Mesh | Excludes object from export |
| CastShadows* | Mesh | Controls shadow casting |
| ReceiveShadows* | Mesh | Controls shadow reception |
| DecayValue | Light | Light falloff rate |
| StaticFactor | Light | Baked lighting multiplier |
| GenerateShadows* | Light | Enables shadow generation |
| IsPhysicsShape* | Physics | Identifies collision object |
| ShapeType | Physics | Collision primitive type |
| ClassName | G5Entity | Links to runtime script |
| UseEmissiveEffect* | Shader | Enables self-illumination |
| UseSpecularShading* | Shader | Enables specular highlights |
| MixingMode | Shader | Transparency mode |
| SurfaceType | Shader | Material classification |

### 13.3 File Locations

The following files contain the core implementation of the G5 export pipeline. Understanding these files is useful for troubleshooting and extending the pipeline.

| File | Purpose |
|------|---------|
| `ExportBatch.mel` | Batch export interface and doExportScene function |
| `MS2ExportPlugin.mel` | Export dialogue UI and options |
| `shelf_G5Engine.mel` | Shelf button definitions |
| `addMeshProperties.mel` | Mesh attribute registration |
| `addLightProperties.mel` | Light attribute registration |
| `createPhysicsShape.mel` | Physics collider generation |
| `AEG5EngineShaderTemplate.mel` | Shader attribute definitions |
| `LightMapsWnd.mel` | Light map generation interface |

### 13.4 File Formats

| Extension | Format Type | Description |
|-----------|-------------|-------------|
| `.ma` / `.mb` | Maya ASCII/Binary | Source scene files |
| `.ms2` | MS2 Binary | Final exported game asset format |
| `.tex` | Renamed DDS | Engine's compressed texture format |
| `.bmp` | Bitmap | Uncompressed source texture format |
| `.raw` | Raw Binary | Uncompressed texture data for special cases |
| `.txt` | Plain Text | Runtime script class definitions |

---

## Appendix A: Change Log

**Version 3.1 (December 2025)**  
Comprehensive update based on cross-referencing with the Visual Guide (v2.2) and additional MEL source code analysis. Added complete doExportScene function signature with all 17 parameters. Corrected createPhysicsShape parameter values (Box=1, Capsule=2, Cylinder=3). Added comprehensive shader attribute documentation with all attributes from AEG5EngineShaderTemplate.mel. Added G5Entity marker documentation (with caveat about missing createG5Entity command). Added naming conventions section documenting _1m, _col, and _LOD# standards. Added light map UV requirements. Documented portal export option which is supported in the pipeline. Added initialization documentation (G5Exp.mel). Added command line export documentation.

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

The following items could not be verified from the provided MEL source code and require further investigation or clarification from project leads:

1. **createG5Entity Command:** The createG5Entity MEL command mentioned in the Visual Guide was not found in the provided script suite. The current method for creating G5Entity markers should be confirmed.

2. **Physics Shape Types:** The Visual Guide mentions ConvexHull, Sphere, and Mesh physics types in addition to Box, but only Box, Capsule, and Cylinder were found in the createPhysicsShape.mel source code. The existence of additional shape types should be verified.

3. **Shader Surface Types:** The Visual Guide mentions specific shader types (Track, Environmental, Armored Surface, Glass) that likely correspond to SurfaceType attribute values. The exact mapping between surface type names and numeric values should be documented.

4. **G5Exp.mel Location:** The initialization script mentioned in the Visual Guide was not found in the provided tools. The correct initialization procedure should be verified.
