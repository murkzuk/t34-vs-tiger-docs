# T-34 vs. Tiger: Creating a Destructible Prop Asset

This guide provides a complete workflow for creating a new destructible prop asset using the T-34 vs. Tiger Maya to G5 export pipeline. The guide follows the manual structure while providing a practical, step-by-step tutorial for this specific asset type.

---

## 1. Asset Planning

Before opening Maya, you should understand what destruction system your prop will use and how it fits into the game. Destructible props typically fall into two categories: pre-fractured destruction where the object starts broken into pieces, and procedural destruction where the object fractures at runtime. For most game props, pre-fractured destruction is the standard approach because it gives artists full control over how the object breaks and performs better at runtime.

For this guide, we will create a wooden crate that breaks into several pieces when destroyed. The prop will have three states: intact (the main mesh), destroyed debris (multiple fractured pieces), and a destruction threshold that determines when the debris appears. Each state requires proper naming conventions and attribute configuration for the G5 engine to recognize and process them correctly.

The naming convention for destructible props should follow the patterns established in the manual. The main intact mesh uses the base name, debris pieces use a numbered suffix convention, and all collision geometry uses the _col prefix. For a wooden crate, the mesh hierarchy might look like this: Crate as the parent transform, Crate_Intact as the visible intact mesh, Crate_Debris_01 through Crate_Debris_04 as the broken pieces, and _col_Crate as the collision representation for the intact state.

---

## 2. Scene Setup and G5Entity Creation

Open Maya 5.0 and ensure the G5Engine shelf is visible. If the shelf is not present, run the G5Exp.mel script from your scripts folder to initialize the pipeline. The G5Entity marker serves as the organizational backbone for every game object, so creating this first establishes the proper relationship between your Maya scene and the game engine.

Create a new scene and save it to your project directory. The recommended directory structure follows the pattern established in the manual, with separate folders for source files, exported models, and reference textures. Your working directory should contain the Maya scene file (.mb), all source textures, and any reference geometry you might need.

Create a transform node to serve as the root of your prop. This node will become the G5Entity marker for your asset. The G5Entity marker stores metadata that the game engine uses to understand how to handle the asset, including which script class controls its behavior and what export options apply to its components. Name this node according to your project's naming convention, for example, Prop_Crate_Wood_01.

**Note:** The createG5Entity MEL command mentioned in project documentation was not found in the provided toolset. If you have access to this script, use it to create the G5Entity marker. Otherwise, create a transform node and configure the ClassName attribute manually after the mesh is complete. The manual documents this system in Section 3.

---

## 3. Creating the Intact Mesh

Create the intact mesh for your prop using standard polygon modeling techniques. The manual specifies in Section 4.3 that all exported geometry must be polygonal, so ensure you convert any NURBS surfaces before export. Model your wooden crate with clean edge flow and proper pole management to avoid rendering artifacts when the game engine processes it.

The crate should be modeled at its final intended size. The manual notes in Section 4.2 that scale conversion issues often only appear at runtime, so work at final game scale from the beginning. Create the geometry with six faces for a basic crate, or add additional detail like bracing boards if your design calls for more complexity.

Once the geometry is complete, apply the G5EngineShader. Section 6.1 of the manual covers shader creation and assignment. Create a new G5EngineShader using the Hypershade or by executing:

```mel
shadingNode -asShader G5EngineShader;
```

Assign the shader to your crate mesh and configure the texture attributes. The BaseTexture attribute specifies the primary diffuse map, while attributes like DiffuseColor allow you to tint the surface without modifying the texture itself. For a wooden crate, you might set up a wood grain diffuse map, a normal map for board texture, and optionally a micro texture for fine surface detail.

Section 6.2 through 6.8 of the manual documents all available shader attributes. For a simple destructible prop, the essential attributes are BaseTexture, normalCamera (for normal mapping), and UseSpecularShading (typically disabled for wood). Additional attributes like AmbientColor, HeightMapTexture, and LightMapTexture can be configured based on your specific material requirements.

---

## 4. Setting Mesh Properties

With your intact mesh selected, execute the addMeshProperties command documented in Section 4.1 of the manual:

```mel
addMeshProperties;
```

This command registers all engine-specific attributes on the mesh object. After execution, the Attribute Editor displays a "G5 Mesh Properties" section with the attributes described in Section 4.2. Configure these attributes according to your prop's intended use.

For a destructible wooden crate that can be shot and walked around, set IsCollisionMesh to true so that characters and objects collide with it properly. Set IsShadowMesh to true if you want the crate to cast shadow volumes, though this may not be necessary for smaller props. Set DoNotExport to false (the default) so the mesh is included in the export.

The CastShadows and ReceiveShadows attributes control shadow behavior. For most props, leave both enabled for proper lighting integration. The IsWalkMesh attribute should typically be false for a crate, as characters should walk around it rather than across it. Only enable IsWalkMesh if your crate is meant to serve as a walkable surface like a platform.

The HasShadowVolume attribute enables shadow volume casting, which is a specialized technique for sharp silhouettes. For a wooden crate in a typical game scene, standard shadow mapping is usually sufficient. Only enable this if your art direction specifically requires shadow volume effects.

---

## 5. Creating Destruction Geometry

Destructible props require separate mesh geometry for their destroyed state. Create the fractured pieces that will appear when the crate is destroyed. These pieces should approximate the volume of the original crate while showing visible breaks and separation. The debris pieces should be parented under the same root transform as the intact mesh.

Name your debris pieces using a consistent suffix convention. Section 5.3 of the manual documents the physics shape creation workflow, but debris geometry uses standard mesh objects rather than physics shapes. For our crate, debris pieces might be named Crate_Debris_01, Crate_Debris_02, and so on. This naming convention helps the export pipeline identify and process the components correctly.

Each debris piece needs its own shader assignment. Create a new G5EngineShader or duplicate the intact crate shader for the debris. The debris pieces might use a fresher or more detailed texture since players will see them close-up when destroyed. Configure the shader attributes for each debris piece using the same process documented in Section 6.

Apply addMeshProperties to each debris piece:

```mel
select -r Crate_Debris_01 Crate_Debris_02 Crate_Debris_03 Crate_Debris_04;
addMeshProperties;
```

Set DoNotExport to false for all debris pieces so they are included in the export. These pieces will be stored in the .ms2 file and activated by the destruction script when the prop is destroyed in-game.

---

## 6. Creating Physics Collision Geometry

Section 7 of the manual documents the physics shape creation workflow. For a destructible prop, you typically need two collision representations: one for the intact state and potentially different shapes for the debris pieces. The physics shapes define how the object interacts with the physics simulation.

Select the intact crate mesh and create a box-shaped collider:

```mel
createPhysicsShape(1);
```

The parameter values documented in the manual are: 1 for Box, 2 for Capsule, 3 for Cylinder. The box shape works well for crates and other rectangular objects. The createPhysicsShape command creates a new node and sets the IsPhysicsShape and ShapeType attributes automatically.

The physics shape is created as a separate node parented under the original mesh. Section 7.2 documents that the ShapeType attribute corresponds to the primitive type used. The physics shape is not rendered in-game but is used for collision detection calculations.

Name the physics shape using the _col prefix as documented in Section 5.2 of the manual. For our crate, the collision mesh should be named _col_Crate. This naming convention tells the export pipeline that this mesh is collision geometry rather than visual geometry.

For debris physics, you have two options. You can create simplified colliders for each debris piece using createPhysicsShape, or you can disable collision on debris entirely if the pieces will fall through the world or disappear shortly after destruction. The appropriate choice depends on how your destruction system handles physics for broken pieces.

---

## 7. Light Map Configuration

If your prop requires light maps, Section 8 of the manual documents the requirements and Section 5.1 documents the _1m naming convention. Meshes requiring light maps must include the _1m suffix in their name. Rename your meshes accordingly if light maps are needed.

The light map UV requirements are critical for successful light map generation. Section 8.2 of the manual specifies that all UV faces must be unique and not overlap, the layout must fit within 0-1 texture space, and a dedicated UV set should be used for light maps separate from material textures.

For the wooden crate, create a second UV set specifically for light maps. This keeps your material UV layout optimized for texture appearance while allowing a separate layout optimized for light map packing. Use Maya's UV layout tools to arrange the faces within the 0-1 space with appropriate texel density for the expected light map resolution.

Name the UV set appropriately using Maya's UV set editor. The manual does not specify a required naming convention for UV sets, but using a descriptive name like "LightMapUVs" helps identify the purpose of each set.

---

## 8. Level of Detail Setup

Section 5.3 of the manual documents the _LOD# naming convention for level of detail meshes. If your prop benefits from LOD switching at distance, create simplified versions of the crate geometry and name them with the LOD suffix convention.

For a simple wooden crate, LOD may not be necessary as the geometry is already low-poly. For more complex props, create reduced-polygon versions at one or two lower detail levels. The LOD0 mesh is the highest detail, LOD1 is simplified, and LOD2 is the lowest detail version.

The naming convention follows the pattern [MeshName]_LOD[Number]. For our crate, if we created LOD versions, they would be named Crate_Intact_LOD0 (or just Crate_Intact without suffix for the highest detail), Crate_Intact_LOD1, and Crate_Intact_LOD2.

Apply addMeshProperties to each LOD mesh and set the LodNumber attribute appropriately. The manual documents that the LodNumber attribute specifies the level of detail index, with lower values indicating higher detail. Each LOD mesh should have its LodNumber set to match its position in the LOD chain.

---

## 9. ClassName and Behavior Configuration

The ClassName attribute on the G5Entity marker links your Maya object to a runtime script file that defines the object's behavior in the game engine. Section 3.2 of the manual documents this relationship. The ClassName must exactly match a class defined in the project's .txt script files.

For a destructible prop, your script class defines how the destruction system works. The script controls the destruction threshold, which determines how much damage the prop can take before breaking. It also controls which debris pieces appear when destroyed and any sound effects or particle effects associated with destruction.

Your project should have existing script templates for destructible props. Consult your project's script directory to find the appropriate base class for your prop. The script might be named something like "CDestructibleProp" or similar, depending on your project's naming conventions.

Set the ClassName attribute on your G5Entity marker to match the appropriate script class. If the export succeeds but the prop exhibits no behavior in-game, the manual's troubleshooting section (Section 12.4) notes that this typically indicates a mismatched or missing ClassName.

---

## 10. Export Configuration

With all mesh and attribute setup complete, you're ready to configure and execute the export. Section 10 of the manual documents the export commands in detail. For a complete prop export with all components, you can use the doExportScene function with appropriate parameters.

The manual provides the complete function signature in Section 10.2. For a prop export with physics shapes, the relevant parameters are ExportModel set to 1, ExportLights set to 1 if the prop has lights, ExportShapes set to 1 to include collision geometry, and ExportTangentSpace set to 1 if using normal mapping.

Alternatively, you can use the export dialogue interface documented in Section 10.3. Open the dialogue from the G5Engine shelf, enter your ClassName, and enable the appropriate checkboxes for your export options. The dialogue provides a visual interface for configuring the same parameters that doExportScene accepts programmatically.

Before executing the export, perform the validation checks documented in Section 11.2 of the manual. Verify that addMeshProperties has been called on all meshes, that each mesh has a valid G5EngineShader assigned, that physics shapes are properly parented, and that naming conventions are consistent throughout the scene.

---

## 11. Export Execution

Execute the export using your preferred method. For programmatic export, you would call doExportScene with your specific parameters:

```mel
doExportScene(
    "C:/Path/To/Output/Directory/",      // Output directory
    "C:/Path/To/Source/Scene/Crate.mb",  // Scene file
    "Model",                              // Command type: "Model" or "Animation"
    "CPropCrate",                         // Class name
    1,  // ExportModel - export visual mesh
    0,  // ExportAnimation - no animation data
    1,  // UseAnimationsByJoint - use joint-based animation (irrelevant without animation)
    1,  // ExportLights - export light objects
    0,  // ExportPortals - no portals on props
    0,  // ExportBehaviorInfo - no behavior data
    0,  // RegionsByJoints - no regions (irrelevant without behavior)
    0,  // CellSize - cell size for regions (irrelevant)
    1,  // ExportShapes - export physics collision shapes
    0,  // LifeHeadExportEnabled - no life head
    "", "", ""  // Life head parameters (empty)
);
```

Alternatively, use the graphical export dialogue for interactive export. The manual documents this interface in Section 10.3. Configure the options as shown above and click the Export Process button to generate the .ms2 file.

After export, verify that the .ms2 file was created in the output directory. Section 11.3 of the manual recommends immediate in-engine testing to verify correct behavior. Load the asset in the game editor or test level and verify that the prop appears correctly, that collision works as expected, and that any destruction triggers function properly.

---

## 12. Quick Reference Checklist

This checklist summarizes the steps for creating a destructible prop asset:

Create the G5Entity root transform and configure the ClassName attribute to match your destruction script. Create the intact mesh geometry using polygons and apply a G5EngineShader with appropriate textures. Execute addMeshProperties on the intact mesh and configure collision and shadow attributes. Create debris geometry for the destroyed state, parent it under the root, and apply shaders. Execute addMeshProperties on all debris pieces. Create physics shapes using createPhysicsShape(1) for box colliders and name them with the _col prefix. Configure light map UVs if light maps are required, using a dedicated UV set with non-overlapping faces in 0-1 space. Create LOD meshes if needed, following the _LOD# naming convention and setting LodNumber attributes. Validate the scene and execute the export using the dialogue or doExportScene function. Test the exported asset in the game engine to verify correct behavior.

---

This guide complements the reference manual by providing a practical workflow for a specific asset type. The manual provides comprehensive technical specifications, while this guide shows how to apply those specifications to create a production-quality destructible prop.