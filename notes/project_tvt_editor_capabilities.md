# T-34 vs Tiger — Level Editor capabilities (reverse-engineered from scripts)

2026-08-30. The game ships a **level editor** (`Editor.exe`) whose behaviour is
entirely **script-driven** in `M:\T34vsTiger\Scripts\Editor\`. It had no
instructions and was "flaky". This note is the missing manual, built by reading
every editor script (three parallel passes: core editing / app+menus /
specialized+atmosphere).

Headline: **the editor can edit almost everything we have been hand-editing** —
including atmosphere (time-of-day, fog, wind) — and its flakiness is mostly in
the readable scripts, not the native engine.

---

## What the editor CAN do (by area)

### 1. Mission / object editing (`MissionEditor.script`, `BaseApplication.script`, `Application.script`)
- **Place objects** from a palette (see the object list below).
- **Select** objects and joints; **move/rotate** via gizmo (**translate + rotate only — no scale gizmo**).
- **Edit commands:** align/move/lean to wall or corner, rotate, resize-to-fit-room (raycast wall/corner finding).
- **Delete, clone, rename, change-class** an object; **group/ungroup**.
- **Save a single object** to a script file (`SaveObject` → `WriteScriptFile`).
- **Save/load full game state** (`SaveState`/`LoadState`).
- **Camera view modes:** `FreeMove`, `LookDown`, `FromPlayer`; `GotoObject` flies the camera to the selected object.
- Undo/redo (see flakiness — only terrain history actually works).

### 2. Terrain editing (`TerrainEditor.script`, `TerraformModifier.script`, `ZoneEditorModifier.script`, `Terraformer.script`, `BaseWorldModifier.script`)
- **Terraform brush** — raise/lower terrain. **24 land types + 24 "water" variants** (Cliffs, Mesa, Mountain, Steep Hill, Hill, Shallow Valley, Crater, Canyon, Shallow Canyon, Valley, Steep Valley, Trench, Plateau, Plains, Quick Level, Soften, Erosion, + water versions).
- **Zone painting** — **38 zone types**: forests (Forest01–04, RoadForest), bushes (Bush01–04), shrubberies, lone tree, village plantings, grasses, off-roads, roads, "AllPassable", water (Water/ShallowWater/BeachWater), micro-textures Micro0–7.
- Brush radius +/- and speed adjust; paint while holding the select button.
- Undo/redo for terrain layers (`LayerHistory`).

### 3. Atmosphere / lighting (`Atmosphere.script` → `CMissionEditorAtmosphere extends CCommonAtmosphere`)
**This is the project's core goal, and the editor does it natively:**
- `SunDirection`, `SunColor`, `AmbientLight`, `DistanceToSun`, `HorizontPos`
- `FogNear`, `FogFar`
- **Per-direction fog colour:** `FogColorXPos` (S), `FogColorXNeg` (N), `FogColorYPos` (E), `FogColorYNeg` (W)
- `WindVector`
- `IsSunVisible`, `IsLightEnabled`, `IsShadowEnabled`

Note: our hand-edits used a single fog colour; the engine actually supports
**separate N/S/E/W fog colours**, which we may not have exploited.

### 4. Cinematics / scripted camera (`CinemaEditor.script`, `MissionEditor.script`)
- Add/delete/play/stop/pause cinematics.
- Full **keyframe editing**: `SetPos`, `Move`, `Stay`, `End`, `Lock`, `StickTo`,
  `Follow`, `Fade`, `Text`, `FOV`, `Widescreen`, `SendEvent`, `Curve`, `Options`.

### 5. Triggers / mission logic (`TriggerEditor.script`)
- Triggers = event → action rules, with conditions and spawner masks.
- **Event types:** NavigationPoint, VisualDetection, SoundDetection, VisualOrSoundDetection, ObjectStateChange, TriggerStateChange, TriggerActivation, TriggerDirect.
- **Action types:** PlayCinema, SendMessage, SetObjectState, SetObjectActive, SetTriggerActive, SetTriggerActivationsCount, SendEvent, FireEvent.
- Conditions on actions (object type/ID, state ID, compare function, compare value).

### 6. Asset viewer (`BaseAssetViewer.script`)
- Browse **Models, Objects, Effects** (Sprites/Lots partially implemented).
- Orbit/zoom/pan preview camera; orthographic camera for sprites/lots.
- Adjust point light + sun/ambient/LOD/per-channel colour; restart effects.
- Preview atmosphere + environment map.

### 7. Menu / UI editor (`MenuEditor.script`, `MenuConfig.script`)
- Edit in-game menu screens: add/delete/move/resize **15 UI control types**
  (bitmap, frame, button, text field, text edit, numeric edit, scroll bars,
  checkbox, group box, progress bar, list, combo box, etc.).

### 8. Navigation (`Navigator.script`)
- List terrain world-matrix layers; overlay a layer's texture on the terrain.
- Teleport camera to a clicked map point; show nav points / object groups / nav path.

### 9. Tools + Tests (`ToolsList.script`, `TestList.script`)
- Terrain texture tools: fill/refine/light water & terrain textures, reload patches.
- Test/QA actions: trigger Mission-1 events (patrols, air attack), damage/restore tank components (driver/gunlayer/engine/tracks/turret).

---

## What you can place (from `MenuConfig.script`)

- **Ground units:** Pak40, Zis3, Nebelwerfer, T-34-76-42, T-34-85-44, Pz.IV Ausf.G, Pz.VI Tiger, Pz.VI Tiger II, SU-85, StuG40, Opel Blitz, Zis5, Hanomag 251, M3A1 halftrack.
- **Air:** IL-2, FW-190. **Humans:** German/Soviet riflemen + tankmen.
- **Structures:** bunkers, sandbags, barricades, houses, bridges, fences, wells, haystacks, trenches.
- **Environment:** barrels, hedgehogs, antitank hedge, weapon boxes.
- **Navigation/sound objects:** nav points (sphere/box/cylinder/spawn/beacon), sound zones, terrain patches.

---

## Why it feels flaky — the concrete causes (all readable, mostly fixable)

1. **Trigger action-target selection is stubbed** — `GetActionObjectsList` returns hardcoded `["Test1","Test2"]` for PlayCinema and errors for everything else.
2. **Undo/redo is `$TMP`** — every history method only touches the FIRST registered provider (terrain `LayerHistory`), ignoring the rest.
3. **Missing/undeclared references:**
   - `SceneManager.script` has no `extends` clause and uses `EnableAssetViewer`/`m_IsObjectListValid` that are never defined in it.
   - `ZoneEditorModifier` uses `m_MissionTerrain` without assigning it (assumed inherited).
   - `BaseAssetViewer` references an undeclared `m_IsObjectListValid`.
4. **Encoding:** `BaseApplication.script` and `Terraformer.script` are **Windows-1251 (Russian)**, not UTF-8 — any tool that assumes UTF-8 fails on them.
5. **Helicopter-game leftovers:** `MissionEditor` uses `CUh1bMapView` (a helicopter map class) instead of its own `CTerrainMapView` (which exists but is commented out).
6. **Copy-paste bugs in `TestList`:** "Damage HULL_GUNLAYER/HULL_ENGINE" actually call the `Restore*` methods; `RestoreTRACK_RIGHT` uses a typo `"TrachRight"`. Also `TerraformModifier.OnTimerTick` calls `SetContinueLastOperation(GetContinueLastOperation())` — a self-reading no-op.
7. **Dead/disabled features:** no scale gizmo, second micro-texture commented out, multiplayer hardcoded, `HaxListJoints`/`CreateDefaultObjects`/`DeleteDefaultObjects`/`OnSpecialCommand` are empty stubs.
8. **Editor.log errors (separate from the scripts):** many `[Locale] There is no section [Messages]` and `Unable to find script: "Test01LandscapeLayer"` — missing locale entries and missing scripts the editor references.

---

## What this means for the project

- The atmosphere/TOD work we did by hand-editing `Content.script` is **exactly what `CMissionEditorAtmosphere` edits in the editor** — and the editor exposes **per-direction fog** we may have under-used.
- The tree/forest work (zone painting `Forest01–04`, `RoadForest`) has an editor path we did not use.
- The editor's flakiness is **mostly in readable scripts** (stubs, typos, missing references), so it is diagnosable and potentially fixable — not a sealed native black box.
- This note is the missing "instructions": what it can do, and what's broken.

## Sources
- `M:\T34vsTiger\Scripts\Editor\` — 30 script files (full inventory in the folder).
- `M:\T34vsTiger\editor.log` / `editor.log.txt` — runtime log with the flakiness errors.
- `Scripts\Editor\info.txt` — Russian note: "this directory contains the level editor scripts".
