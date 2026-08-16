# t34-vs-tiger-docs — Project Map

**Date:** 2026-08-16
**Purpose:** Explain what is in this repo, who made it, and what each folder is for. This document is the **single source of truth** for new contributors and AI assistants.

> **🤖 AI ASSISTANTS — READ IN THIS ORDER:**
> 1. **`llms.txt`** (in the repo root) — the rules of the road. How to behave, what confidence tiers mean, common pitfalls.
> 2. **This file (`PROJECT_MAP.md`)** — what's actually in the repo. Folder layout, who's who, what's safe to touch, what's archival.
>
> **You need BOTH.** Skipping `llms.txt` will lead you to apply the wrong confidence tier or skip the verification step.

> **If you are an AI assistant:** Also read `llms.txt` (in the repo root) for the rules of the road — confidence tiers, verification methodology, common failure modes. This file (`PROJECT_MAP.md`) tells you *what's in the repo*; `llms.txt` tells you *how to behave in it*. You need both.

---

## What This Project Is

A 15+ year preservation effort for **T-34 vs. Tiger** (a 2001 WW2 tank simulation built on the G5/Napalm engine by G5 Software, developed by Sonar Games, published by Lighthouse Interactive). The original developers are long gone. The game is abandonware. The community consists of:

- **Jeff Murkin (murkzuk)** — Project lead, sole active maintainer. Real name "Jeff Murkin", historical aliases "Panzersim" (when he ran a team in the 2000s), "Murkz" (later), "murkzuk" (current). Author of the 2011 mission manual and the model class documentation.
- **Steve Vase (stevan / LArgetool)** — Long-term collaborator since ~2009. Author of the 2011 editor manual. Joined as LArgetool on the Panzersim team, still active on GitHub as `stevanvase0-beep`. Co-developed the multiplayer campaign and modding tools.
- **ZeeWolf (ZW)** — Late collaborator. Java coder. Created a payware single-player mod for T-34 vs. Tiger that significantly extended the engine. **ZW has since died.** His work is payware; murkzuk owns a license and has preserved the scripts for archival/educational value.

No active community. No active forum. No new releases planned. The goal is **preservation, not development.**

---

## The G5 Engine (Background)

G5 (also called "Napalm") is the proprietary 3D engine developed by G5 Software in the early 2000s. It powered:
- T-34 vs. Tiger (2001)
- American Conquest
- Cossacks
- Whirlwinds over Vietnam (WoV)

The engine uses a **Java-like scripting language** (`.script` files) for game logic. There is **no public source code** for the engine. The script files we have are decompiled/reconstructed by the community, and the engine behavior is inferred from gameplay testing and binary reverse engineering with Ghidra.

**No source code. No SDK. No active development. Pure reverse engineering.**

---

## Repo Structure — What Each Folder Is

### `TvT/` — Your (murkzuk's) work on the base game

Multiplayer campaign mission scripts, unit definitions, common systems.

| Subfolder | What it is | Author |
|---|---|---|
| `TvT/Animations/` | Animation definitions | murkzuk |
| `TvT/archive/` | Maya export experiments (Sky/Test_House/etc.) parked out of the way | murkzuk |
| `TvT/Buildings/` | Building unit definitions (`*Unit.script`) | murkzuk |
| `TvT/Common/` | Cross-cutting systems (cockpit, shadows, weapons) | murkzuk + Stevan |
| `TvT/Editor/` | Editor scripts | murkzuk |
| `TvT/Groups/` | Object group definitions | murkzuk |
| `TvT/Locale/` | Localization (`*.locale`) | murkzuk |
| `TvT/Menus/` | Menu scripts | murkzuk |
| `TvT/Missions/` | Per-mission scripts (Atmosphere, Content, Tasks) | murkzuk + Stevan |
| `TvT/Models/` | Model class definitions, mixed with a few test/scaffold files | murkzuk + Stevan |
| `TvT/Resources/` | Resource references | murkzuk |
| `TvT/Units/` | Tank/vehicle unit definitions | murkzuk + Stevan |

> `TvT/Campaigns/`, `TvT/Sounds/`, `TvT/Textures/` mentioned in older versions of this doc no longer exist as separate folders; their content is spread across `Missions/`, `Resources/`, and `Units/`.

⚠️ **The `TvT/Models/` folder is murkzuk's own analysis of the G5 model class structure, NOT extracted from the ZW mod.** See the verification report for details. The content diverges from the ZW concatenated archive because it's from a different source (likely direct observation of the G5 engine).

### `TvTZW/` — ZeeWolf's payware single-player mod (EMPTY PLACEHOLDER)

`TvTZW/` was intended as the home for ZW's mod scripts but never actually received them — it only ever held a `temp.md` placeholder (now parked in `_archive/`). The real ZW scripts live in **`concatenate scripts/ALL_ZW_SCRIPTS/`** (see below). Treat those the same way: ZW was a Java coder who extended the G5 engine with single-player campaign features and charged money for his mod. murkzuk owns a copy and has archived the scripts for **archival and educational value only**.

**This is not open-source. This is not murkzuk's work. This is someone else's preserved code.**

If you want to use anything from here, you need to be aware it was payware. Treat with respect.

### `ZW Mission scripts/` — ZW's mission scripts (PRESERVED, DO NOT MODIFY)

ZW's mission scripts, preserved as concatenated `ALL_*_SCRIPTS_zw.txt` files. These are duplicated inside `concatenate scripts/ZW Mission scripts/` — the two copies are kept in sync; see the note below.

### `concatenate scripts/` — Reference archives of multiple G5 games

| File | What it is |
|---|---|
| `ALL_ZW_SCRIPTS/ALL_Models_SCRIPTS_ZW.txt` | ZW mod model scripts, concatenated into one 64K-line file (UTF-16LE) |
| `ALL_ZW_SCRIPTS/...` (other files) | ZW mod's units, buildings, animations, etc., all concatenated |
| `ALL_ZW_SCRIPTS/ALL_ZW_SCRIPTS.zip` | Zipped bundle of the ZW concatenated scripts |
| `ALL_WoV_SCRIPTS/...` | Whirlwinds over Vietnam scripts, concatenated (for cross-game reference) |
| `ZW Mission scripts/` | Duplicate of the top-level `ZW Mission scripts/` folder (kept for convenience) |

These are **reference archives** — when you need to look up how a class is defined in the ZW mod or in WoV, you grep these files. They are not directly loadable by the game.

### The G5 Engine Lineage (Critical Context)

The G5 engine evolved linearly across G5 Software's games:

```
Whirlwinds over Vietnam (WoV)     [completed release]
        ↓ (engine inherited)
T-34 vs. Tiger (TvT)              [released UNFINISHED — Lighthouse Interactive (the publisher) went bankrupt]
        ↓ (engine extended)
ZeeWolf (ZW) payware SP mod       [later, by a third-party modder]
```

**T-34 vs. Tiger was released unfinished.** A lot of WoV's engine code still exists in TvT's scripts verbatim. The two games are "more or less identical" at the class-structure level. This is why:

- `TvT/Models/` class names match ZW source class names (shared engine)
- T-34 vs. Tiger texture paths differ from ZW (game-specific assets)
- Some static config lines are omitted in T-34 vs. Tiger files (optional defaults)

**When documenting T-34 vs. Tiger, you were documenting an engine that originated in WoV and was extended by ZW.** All three are branches of the same tree.

The `concatenate scripts/` archives (both WoV and ZW) are valuable for understanding this lineage.

### `Documentation/` — Reference documents (mix of murkzuk and Stevan authorship)

| File | Author | Date | What it is |
|---|---|---|---|
| `T34 vs Tiger.pdf` | **Steve Vase** | Dec 2011 | Editor manual. Original Panzersim/Murkz work, updated by LArgetool (Stevan). |
| `t34vstiger new mission manual.pdf` | **Jeff Murkin** (you) | Feb 2011 | How to create a custom mission. Originally by Ivan Spogreev (Head of Sonar Games, the developer), updated by you. |
| `T34vsTiger Human Unit Soldier Model Hierarchy.docx` + `.pdf` | Stevan | Feb 2026 | Model hierarchy documentation |
| `G5_Pipeline_Mastery.pdf` | ? | ? | Ghidra-derived content about the G5 pipeline |
| `T-34 vs. Tiger Creating a Destructible Prop Asset.md` | ? | ? | Modding guide |
| `T-34 vs. Tiger Preservation.md` | ? | ? | Project background |
| `T34_vs_Tiger_Maya_Export_Manual(V3).md` | ? | ? | Maya export pipeline |
| `TVT_Mission_Script_Format_Complete_Reference GOLD.md` | ? | ? | Script format reference |
| `ZeeWolf Mod REDUX Technical Fix Documentation.md` | ? | ? | ZW mod technical reference |
| `enabled Large Address Aware (LAA) for the game executable.txt` | murkzuk | ? | 4GB memory patch notes [MURKZ-VERIFIED] |
| `Messages.rsr_File_Format_Documentation.md` | ? | ? | RSR file format reverse-engineered docs |
| `Mission_File_Schema_Verified_2026-07-02.md` | murkzuk | Jul 2026 | Verified mission file syntax (built while writing the Quick Mission Generator) |
| `MS2_Binary_Format_Findings_2026-07-03.md` | murkzuk | Jul 2026 | `.ms2` binary format reverse-engineering findings (Phases 0-3) |
| `Complete Project Analysis - Final of all 12 campaign missions.md` | ? | ? | Mission analysis |
| `Berezov_Kursk_Mission_Scoping_2026-07-03.md` + `.json` | murkzuk | Jul 2026 | Berezov (Kursk) mission recreation scoping + order-of-battle data |
| `Steppe_Map_Scoping_2026-07-02.md` | murkzuk | Jul 2026 | Steppe map analysis for template/anchor-point work |
| `MyFolderList.txt` | ? | ? | Folder listing (probably auto-generated) |

### `Executables/` — Patched game executables

| File | What it is |
|---|---|
| `TvsT_fullLOD_HARD_4GB.zip` | The 4GB LAA-patched executable with full LOD settings [MURKZ-VERIFIED] |

### `Fixed Pre001/` — murkzuk's fixes from before Stevan's involvement

Pre-existing fixes for unit scripts and effects. **Do not modify without testing.**

### `Tools/`, `Templates/` — Modding tools and template files

Template scripts for creating new missions, units, etc.

### Root files

The repo root now holds only meta files (`.gitignore`, `README.md`, `CHANGELOG.md`, `TODO.md`, `PROJECT_MAP.md`, `llms.txt`) plus an `_archive/` folder for repo-level junk.

The Maya export experiments (`Sky_*.script`, `Test_House*.script`, `MyFirstModel.script`, `sphere_test.script`, etc. and their `.ms2` meshes) used to sit at the root but have been moved to `TvT/archive/` (with their own `README.md`). They are **not** part of any working build.

| File | What it is | Verdict |
|---|---|---|
| `README.md` | Top-level readme | Keep |
| `CHANGELOG.md` | Full fix history, newest first | Keep |
| `TODO.md` | Running backlog | Keep |
| `PROJECT_MAP.md` | This file | Keep |
| `llms.txt` | AI assistant guide | Keep |
| `_archive/` | Non-destructive parking for stray placeholder files | Keep |

---

## Confidence Tiers (How to Read This Repo)

| Tier | Meaning | Examples in this repo |
|---|---|---|
| `[MURKZ-VERIFIED]` | Tested personally by Jeff, works in-game | LAA patch, LOD fixes |
| `[COMMUNITY-CONFIRMED]` | Multiple users reported working | (none currently tagged) |
| `[GHIDRA-DERIVED]` | From binary reverse engineering | Most documentation PDFs |
| `[LEGACY/HISTORICAL]` | From old forums or modder knowledge | 2011 manuals, ZW mod techniques |
| `[UNTESTED-AI-GENERATED]` | AI output never tested | Stevan's recent in-game script modifications |
| `[ARCHIVAL]` | Preserved from external sources, not for direct use | `TvTZW/`, `ZW Mission scripts/`, `concatenate scripts/` |

---

## What NOT To Do

❌ **Do not modify anything in `concatenate scripts/ALL_ZW_SCRIPTS/` or `ZW Mission scripts/`** — that's ZW's payware work, preserved for archival value.

❌ **Do not assume anything in `TvT/Models/` matches the ZW mod** — they're different sources, both valuable, neither is a copy of the other.

❌ **Do not delete files just because the commit message is unhelpful** — git history shows the date and author; use that to decide.

---

## What To Do With Each File Type

| File type | Action |
|---|---|
| `.script` in `TvT/` (Units, Common, Missions) | Test in-game before modifying. AI-tweaked files exist. |
| `.script` in `TvT/Models/` | Treat as murkzuk's analysis, not as game-loadable code |
| `.script` in `TvTZW/` or `ZW Mission scripts/` | Do not modify. Archival. |
| `.script` in `concatenate scripts/` | Reference only. Do not extract into game. |
| `.pdf` or `.docx` in `Documentation/` | Read, but be aware some are 14 years old |
| `.zip` archives (in `Patches/`, `Executables/`, `concatenate scripts/`) | Do not extract into game. Keep as backups. |
| `.ms2` files | Binary mesh data. Reference only. |
| `.exe` patches in `Executables/` | Use the LAA-patched version. [MURKZ-VERIFIED] |

---

## Historical Timeline (Best Reconstruction)

| Year | Event |
|---|---|
| ~2000-2001 | G5 Software releases WoV (Whirlwinds over Vietnam) — completed |
| 2001 | T-34 vs. Tiger developed by G5 Software / Sonar Games (Ivan Spogreev is the lead developer), published by **Lighthouse Interactive**. Released UNFINISHED — Lighthouse went bankrupt mid-release. |
| ~2003-2009 | Panzersim team is active. Murkz (Jeff), LArgetool (Steve), others. Forums on panzersim.forumotion.com. |
| 2009 | First version of the editor manual (joint Panzersim + Murkz work). |
| Feb 2011 | Jeff writes the mission manual (originally based on Ivan's tutorial). |
| Dec 2011 | Steve updates the editor manual. |
| ~2012-2020 | Team disperses. Some die (ZW). Jeff keeps the work alive solo. |
| Dec 2025 | Jeff (murkzuk) returns to the GitHub repo. AI-assisted work begins. |
| Jan 2026 | Stevan (Steve) joins the repo. AI-assisted script changes start. |
| Feb 2026 | murkzuk creates `TvT/Models/` with 75 model class documentation files. |
| Mar 2026 | Stevan makes last commits. Both go quiet. |
| Jun 2026 | You (Jeff) come back. Trying to make sense of it all. |
| Jul 2026 | Major work sprint: issue-tracker audit, Stevan contribution audit, MG/fire-mask and AI fixes, `.ms2` binary format reverse-engineering (Ghidra), Blender importer add-on, Quick Mission Generator. |
| Aug 2026 | Repo tidy-up: non-destructive `.gitignore`, stray files parked in `_archive/`, docs brought in sync with the tree. |

---

## Branches

- **`main`** — The single source of truth. All recent work lands here via PR (see `README.md`).
- *(No other branches currently exist. An older `backup-main-snapshot` branch was referenced in earlier versions of this doc but has since been removed — git history on `main` is the record of everything that happened.)*

---

*This document is a living record. Update it as you learn more about the repo.*
