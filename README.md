# TvTPP — the T-34 vs Tiger Preservation Project

> **TvTPP** (T-34 vs Tiger Preservation Project) is the umbrella name for this
> work: the REDUX build, the tooling, the reverse-engineered format
> documentation, and the effort to finish what others could not.

This repository is a community-driven effort to preserve, fix, and finally finish T-34 vs. Tiger. After the original developers and publishers ceased to exist, this game became "abandonware." We are here to ensure the "Cogs of War" keep turning.

Our mission is to build an open community where anyone — from veteran modders to first-time players — can contribute to making this the definitive WW2 tank simulation.

## 🤝 How You Can Participate

You don't need to be a coder to help! We want this project to be as open as possible.

- 🕹️ **Play & Report**: Download the latest patch and tell us what works (and what doesn't) via the [Issues tab](../../issues).
- 🔧 **Troubleshooting**: Found a fix for a crash or a driver error? Add it to `CHANGELOG.md` so others can find it.
- 📜 **Script Tinkering**: If you've tweaked a `.script` file for better physics or terrain, share your findings!
- 🎨 **Texture Work**: Help us update the textures for vehicles and environments.

## 🔒 A Note on Contributing (please read before pushing)

As of 2026-07-02, `main` is protected. Direct pushes to `main` will be rejected — this isn't personal, it's a safety net for everyone's work (including yours!). Here's the workflow now:

1. Create a new branch for your change (e.g. `git checkout -b fix/some-bug`).
2. Push your branch and open a Pull Request.
3. It'll get reviewed and merged into `main` once it's good to go.

This exists because a previous contribution accidentally deleted a working function during an unrelated cleanup, and it went straight into `main` unnoticed since there was no review step at the time. A branch + PR review would have caught it immediately. Nothing to do with any one person — just closing a gap that bit us once already.

## 📂 Repository Roadmap

To make this "mountain" easier to climb, we have organized the project into key areas:

- **[Technical Manuals](./Documentation):** Engine specifications, mission-scripting reference, and project analysis. See below for the highlights.
- **[Development Tools](./Tools):** Scripts, Maya export manuals, and utilities created for TvT by G5 (the original developers).
- **[Blender add-on: open the game's models](./Tools/MS2Format):** install [`ms2_importer.zip`](./Tools/MS2Format/blender_addon/ms2_importer.zip) and get **File → Import → TvT Model (.ms2)** — whole vehicles, assembled and textured, in one step. Writing models back out works too. [Install instructions and format notes](./Tools/MS2Format/README.md).
- **[Executables](./Executables):** The 4GB LAA patch and essential engine fixes.
- **[Patches](./Patches):** Ready-to-apply hotfix packages — grab the latest one if you just want fixes without touching the source. See [`RELEASING.md`](./RELEASING.md) for how to publish a new one.
- **[Mission Templates](./Templates):** Standardized headers to prevent "Duplicate Class" errors.
- **[Stable Build (Pre001)](./Fixed%20Pre001):** The first verified "fixed" pre-0.001 build, included in the patch.
- **[Consolidated Scripts](./concatenate%20scripts):** Mission scripts processed through `cat` for easy debugging.
- **[Original Logic](./TvT):** The base stock scripts for T-34 vs. Tiger — this is the mirror kept in sync with the live REDUX game install.
- **[ZeeWolf Legacy](./concatenate%20scripts/ALL_ZW_SCRIPTS):** Preservation of ZeeWolf (ZW) mod scripts and logic — see the note below on what this is.
- **[ZW Missions](./ZW%20Mission%20scripts):** Specific mission scripts from the ZeeWolf collection.
- **[Archive](./TvT/archive):** Maya export experiments parked out of the way (not part of any working build).
- **`TODO.md`**: Running backlog of known issues, half-finished content, and investigation notes.
- **`CHANGELOG.md`**: Full history of fixes and changes, newest first — this is the "Confirmed Fixes" list.

### Technical Manual Highlights

The most-used documents in [`Documentation/`](./Documentation):

- **`T34_vs_Tiger_Maya_Export_Manual(V3).md`** — the complete Maya 5.0 → G5 engine asset export reference (mesh/light/physics/shader attributes, naming conventions, the full `doExportScene` signature).
- **`T-34 vs. Tiger Creating a Destructible Prop Asset.md`** — a step-by-step tutorial building on the manual above.
- **`TVT_Mission_Script_Format_Complete_Reference GOLD.md`** — mission scripting reference.
- **`Mission_File_Schema_Verified_2026-07-02.md`** — verified mission file syntax, written while building the Quick Mission Generator tool.
- **`ZeeWolf Mod REDUX Technical Fix Documentation.md`** — notes on fixes originally found via the ZeeWolf mod.

This list grows regularly — check the folder itself for anything newer than what's listed here.

### A Note on the ZeeWolf (ZW) Mod and Whirlwind over Vietnam (WoV)

This repository also preserves scripts from the ZeeWolf (ZW) mod, a paid mod for TvT made by a modder who has since disappeared without sharing his source — only the compiled game files survive, which is what's preserved here. Separately, this repo includes scripts from *Whirlwind over Vietnam* (WoV), G5's earlier title and the engine base TvT was built from. Unlike TvT, WoV was fully finished and released; TvT was pushed out unfinished in an attempt to save its publisher (it didn't work). Both companies no longer exist. These are kept here for the same preservation reasons as everything else in this repo.

## 💡 Quick Start Troubleshooting

**Game won't start?** If you get an "Unable to initialize 3D driver" error on older laptops or GPUs, try deleting `D3D9.dll` from your game folder.

**Loads to the menu but crashes when starting a mission on Windows 11?** Grab `msvcp71.dll` and `msvcr71.dll` from another old game install (or elsewhere) and copy them into the main game folder alongside the existing files. Confirmed working on a fresh Windows 11 install (thanks Glyn).

See `CHANGELOG.md` for these and other confirmed fixes.

## Uploading Files to This Repository

If you're not comfortable with git/branches yet, you can still contribute docs or notes directly through GitHub's web UI:

1. Go to https://github.com/murkzuk/t34-vs-tiger-docs
2. Click "Add file" → "Upload files"
3. Drag and drop your files
4. Click "Commit changes"

Note this still goes through the branch protection above — GitHub will prompt you to create a new branch and open a Pull Request rather than committing straight to `main`.

## Acknowledgments

Documentation and fixes in this repository have been developed with the assistance of multiple AI systems, cross-referencing source code, MEL scripts, and visual guides to produce verified technical specifications.

## Notes

- Maya 5.0 is required for the asset-export pipeline documented in `Documentation/`.
- The `createG5Entity` MEL command mentioned in some documentation was not found in the available toolset.
- Some workflow steps may still need verification from project leads.

## License

Documentation and preserved scripts in this repository are shared for educational and historical preservation purposes.

## A Note on the Community

We are building this for the love of the sims. Please be patient with one another, share what you know, and let's bring this game back to life together.
