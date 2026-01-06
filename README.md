🛡️ Project Redux: T-34 vs. Tiger Preservation

Welcome to the frontline. This repository is a community-driven effort to preserve, fix, and finally finish T-34 vs. Tiger. After the original developers and publishers ceased to exist, this game became "abandonware." We are here to ensure the "Cogs of War" keep turning.

Our mission is to build an open community where anyone—from veteran modders to first-time players—can contribute to making this the definitive WW2 tank simulation.
🤝 How You Can Participate

You don't need to be a coder to help! We want this project to be as open as possible.

    🕹️ Play & Report: Download the latest patch and tell us what works (and what doesn't) in the Issues Tab.

    🔧 Troubleshooting: Found a fix for a crash or a driver error? Add it to our Confirmed Fixes list to help others.

    📜 Script Tinkering: If you’ve tweaked a .script file for better physics or terrain, share your findings!.

    🎨 Texture Work: Help us update the .dds textures for vehicles and environments.

📂 Repository Roadmap

To make this "mountain" easier to climb, we are going to organise the project into key areas:

    Technical Manuals: Documentation for Maya 5.0 and the G5 Engine export pipeline.

    Mission Scripting: Detailed guides on how missions are structured.

    Legacy Assets: A collection of original and modded scripts from ZeeWolf (ZW) and Whirlwinds over Vietnam (WoV) for cross-referencing.

    Engine Fixes: Tools like the 4GB patch (LAA) and 3D driver fixes.

💡 Quick Start Troubleshooting

Game won't start? If you get an "Unable to initialize 3D driver" error on older laptops or GPUs, try deleting D3D9.dll from your game folder. See our Confirmed Fix #1 for details.
A Note on the Community

We are building this for the love of the sims. Please be patient with one another, share what you know, and let's bring this game back to life together.
# T-34 vs. Tiger - G5 Engine Export Documentation

Documentation for exporting 3D assets from Maya 5.0 to the proprietary G5 game engine.

## Overview

This repository contains comprehensive documentation for the T-34 vs. Tiger asset export pipeline. All procedures have been verified through static analysis of the original MEL source code.

## Contents

### Reference Manual
- **T34_vs_Tiger_Maya_Export_Manual(V3).md** - Complete technical reference (553 lines)
  - Complete doExportScene function signature with all 17 parameters
  - All mesh, light, physics, and shader attributes documented
  - Naming conventions and UV requirements
  - Troubleshooting guide

### Tutorials
- **T-34 vs. Tiger Creating a Destructible Prop Asset.md** - Step-by-step workflow
  - Practical use case for creating destructible props
  - Step-by-step mesh, physics, and export workflow

### Visual Guides (PDF)
- **G5_Pipeline_Mastery.pdf** - Condensed reference guide
- **T34_vs_Tiger_Asset_Pipeline_Visual_Guide.pdf** - Workflow overview
- **export manual. Tutotial 1.pdf** - Beginner's getting started guide

### Mission Scripting
- **TVT_Mission_Script_Format_Complete_Reference GOLD.md** - Mission scripting reference

## Key Technical Details

### Physics Shape Types
| Command | Shape Type |
|---------|------------|
| `createPhysicsShape(1)` | Box |
| `createPhysicsShape(2)` | Capsule |
| `createPhysicsShape(3)` | Cylinder |

### Naming Conventions
- `_1m` suffix for light map meshes
- `_col` prefix for collision geometry
- `_LOD#` suffix for level of detail meshes

### Essential Commands
```mel
addMeshProperties;           // Register mesh attributes
addLightProperties;          // Register light attributes
createPhysicsShape(1);       // Create box collider
doExportScene(...);          // Batch export function
```

## Documentation Structure

```
t34-vs-tiger-docs/
├── README.md
├── T34_vs_Tiger_Maya_Export_Manual(V3).md
├── T-34 vs. Tiger Creating a Destructible Prop Asset.md
├── TVT_Mission_Script_Format_Complete_Reference GOLD.md
├── G5_Pipeline_Mastery.pdf
├── T34_vs_Tiger_Asset_Pipeline_Visual_Guide.pdf
├── export manual. Tutotial 1.pdf
└── TVT_Mission_Script_Format_Complete_Reference GOLD.md
```

## Uploading to GitHub

To upload files to this repository:

1. Go to https://github.com/murkzuk/t34-vs-tiger-docs
2. Click "Add file" → "Upload files"
3. Drag and drop your files
4. Click "Commit changes"

## Acknowledgments

Documentation created with the assistance of multiple AI systems, analyzing MEL source code and cross-referencing visual guides to produce verified technical specifications.

## Notes

- Maya 5.0 is required for this pipeline
- The createG5Entity MEL command mentioned in some documentation was not found in the provided toolset
- Some workflow steps may require verification from project leads

## License

Documentation preserved for educational and historical purposes.
I also have included files from the ZeeWolf (zw) mod, this was a paywar mod made by the now gone ZeeWolf, his mod included, new maps, vehicles and physics. For completeness I have included the .scripts from Whirlwinds over Vietnam (WoV) because TvT is so very close to WoV, it was G5's title prior to TvT and was the main base for TvT. Unlike TvT, WoV was fully formed and released as sich, TvT was not. It was released unfininshed to save it's publisher (it did not). Both companies ceased to exist.
