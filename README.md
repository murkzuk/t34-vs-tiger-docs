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
