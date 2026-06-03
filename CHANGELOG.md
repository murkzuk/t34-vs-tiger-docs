# Changelog — t34-vs-tiger-docs

All notable changes to this repository. The most recent entry is first.

This file is human-written, plain prose. For technical details, see [PROJECT_MAP.md](PROJECT_MAP.md) and [llms.txt](llms.txt).

---

## 2026-06-03 — Repo cleanup and documentation baseline

**By:** murkzuk (with Mavis / MiniMax Agent assistance)

### What changed

- **Deleted `TvT/T34vsTiger*.rar` archives** (3 files). These were full game builds, unsafe to keep in a documentation repo. Anyone with the working game build already has the files; nobody should be extracting RARs into a game install from a docs repo.
- **Removed 27 Maya export test files from the repo root** (`Sky_*.script`, `Test_House*.script`, `MyFirstModel.script`, `Landscape_test.script`, `sphere_test.script`, `test.script` and matching `.ms2` files). These were noise at the root and had no relation to the actual game. All copies had been archived in `TvT/archive/` first.
- **Moved 16 misplaced real unit files** from repo root and `TvT/archive/` to `TvT/Units/` (where the Tiger and T-34 unit scripts already lived). Units affected: FW 190, IL-2, IL-2M, Nebelwerfer, Pak 40, ZIS-3, Hanomag 251C, M3A1 Halftrack. Both `.script` and `.ms2` files moved together.
- **Removed empty `mmp7.1/` folder.** Was a chaos folder with `Scripts` (1 byte) and `temp.txt` (28 bytes). No content of value.
- **Added `PROJECT_MAP.md`** — the new top-level document explaining repo layout, who's who, what's safe to modify, and what's archival. Linked from `llms.txt`.
- **Updated `llms.txt` to v2** — new content with verification timeline, current repo state, exclusion zones (don't touch `TvTZW/`, `ZW Mission scripts/`, or `concatenate scripts/`), and the 5-tier confidence hierarchy. Dated 2026-06-03.

### Why this matters

Before this session, the repo had ~30 noise files at the root and several duplicated folders. It looked like a junk drawer to anyone landing on it for the first time. After this session:

- The root contains only folders + 2 files (`README.md`, `CHANGELOD.md`, `PROJECT_MAP.md`, `llms.txt`).
- The `TvT/Units/` folder has all the real unit scripts and their meshes.
- Future contributors and AI assistants have clear docs to read on entry.

### Contributors

- **Jeff Murkin (murkzuk)** — commits, decisions, verification
- **Mavis (MiniMax Agent)** — drafted `PROJECT_MAP.md`, `llms.txt` v2, `CHANGELOG.md`, this changelog entry. Did the file-level analysis of what was in the repo and what was safe to move/delete.

---

## Format guide for future entries

When you add a new entry, put it at the top with today's date. Use sections: **What changed**, **Why this matters**, **Contributors**. Keep prose short. Link out to docs when relevant.

The old `CHANGELOD.md` (LOD-specific) stays as a separate file. This `CHANGELOG.md` is for the project as a whole.

---

*Last updated: 2026-06-03*
