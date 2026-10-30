# T-34 vs Tiger — Level Editor deep dive (Editor.exe + native classes + hook story)

2026-08-30. Complements `project_tvt_editor_capabilities.md` (the script layer).
This note covers the BINARY, the NATIVE classes the editor scripts call, the DLL
dependency graph, and whether/how we can inject and hook the editor.

## 1. What Editor.exe is (binary facts, measured)

| | Editor.exe | TvsT.exe (game) |
|---|---|---|
| timestamp | 2009-01-21 | 2008-08-01 |
| image size | 0x262000 (~2.4 MB) | 0x4B000 (~300 KB) |
| subsystem | GUI (2) | GUI (2) |
| imports | WINMM, d3dx9_30, COMCTL32, **gdiplus (59)**, KERNEL32, USER32, GDI32, comdlg32, ADVAPI32, ole32, OLEAUT32 | WINMM, KERNEL32, USER32, GDI32, ole32, OLEAUT32, **MSVCI70/MSVCR70 (old CRT)** |
| exports | none | none |

- Editor.exe is a **later, bigger build with a GDI+ / common-controls GUI front
  end** (gdiplus.dll + comctl32.dll = rich 2D dialogs/toolbars/tree views).
- **Neither exe statically links the engine** — both load it at runtime.
- Editor.exe strings reference the **same engine DLLs**: `Objects.dll`,
  `Engine.dll`, `J5Script.dll`, `STTree.dll`, `Service.dll`, `Controls.dll`,
  `Behavior.dll`.
- Resource string: `<description>G5 Software Level Editor</description>`.
- It reads/writes the **same mission files we hand-edit**:
  `Content.script`, `Atmosphere.script`, `Mission.script`, `MissionStrings.script`,
  `Terrain.script`, `WorldMatricies.script` (per `Missions/MyMission/%s/`).

**Conclusion: Editor.exe = the game engine + a GDI+ GUI shell + the editor
scripts + the editor's native classes. Same engine, same DLLs, same files.**

## 2. Architecture — three layers

1. **GUI shell** — `Editor.exe` (GDI+, common controls). Flaky, undocumented.
2. **Script layer** — `Scripts\Editor\` (30 files, documented in
   `project_tvt_editor_capabilities.md`). Thin orchestration only.
3. **Native classes** — in `Objects.dll` / `Engine.dll`. The real work.

The editor scripts are thin wrappers: `MissionEditor.script` line 61 does
`Component Editor = new #MissionEditor();` and delegates to it. The actual
editing (terraform math, zone painting, object ops) is native.

## 3. Native classes the editor instantiates (`new #X`)

- **Engine core:** `#GameController`, `#InputController`, `#Timer`,
  `#FileDataStorage`, `#TextControl`, `#InputThroughputControl`,
  `#MissionController`, `#EffectsArray`, `#MaterialManager`.
- **Editor-specific natives:** `#MissionEditor`, `#TerrainZoneEditor`,
  `#Terraformer<TerraformerOptions>`, `#MatrixLayerHistory`,
  `#GizmoCursorTranslate` / `#GizmoCursorRotate`, `#GeometryCursor`,
  `#RadarObject`, `#TerrainMap<CUh1bMapView>`.
- **Rendering/objects:** `#Camera`, `#ManualCameraControl`/`2`,
  `#AnimatedObject`, `#SpriteObject`, `#Locator`, `#LightEmitter`,
  `#EnvironmentMap`, `#Atmosphere`, `#SpriteViewManager`, `#GameObject<T>`.
- **UI:** `#MenuGroup`, `#BitmapButton`, `#SliderCursorControl`, `#CursorControl`,
  `#MenuEditor<T>`.

These names are present in `Objects.dll` / `Engine.dll` (RTTI), so the native
editor classes live in the same DLLs we already hook for the game.

## 4. Can we hook it? — YES, and here is why

**Can:** Editor.exe loads the same engine DLLs; the native classes are in
`Objects.dll`/`Engine.dll`; the injector's allow-list already covers
`M:\T34vsTiger`. The proven infrastructure (tvt_inject.exe suspended launch +
`LdrRegisterDllNotification` + 5-byte JMP trampolines) works on Editor.exe
exactly as on the game.

**Why (in value order):**

1. **The editor's real work is native and opaque.** The scripts don't say *what*
   `#Terraformer::TransformTerrain` or `#TerrainZoneEditor` actually do — hooking
   them reveals the behaviour.
2. **Drive it headlessly.** Inject a DLL that loads a mission, sets atmosphere,
   paints terrain, and saves — programmatically, no flaky GUI. This is the
   user's "run it headless" idea made concrete.
3. **Instrumentation.** Hook + log to see exactly what the editor does on click
   (debug the flakiness; trace the save path).
4. **Fix native bugs.** Patch the native editor functions.
5. **Confirm the save format.** The editor writes `Content.script` etc. — hooking
   the serializer would pin the exact format.

## 5. IMPORTANT — a headless path already exists (no hooking needed)

`K:\TvTDeepseek\t34-vs-tiger-docs\Tools\MissionEditor\`:

- `mission_io.py` — reads/writes TvT missions headlessly. Handles `Content.script`
  (CP1251, CRLF/LF aware), zone bitmaps (top-down), `hmap.raw` (flipped, height
  factor 0.07), object matrices (4x4 row-major, position in 4th column). Ships
  real tank/vehicle dimensions.
- `server.py` — a local web server (`http://127.0.0.1:8765`) that serves a
  web-based mission editor and writes straight back to `Content.script`.

**The round-trip was already proven:** a machine-written `Content.script` opened
in Editor.exe, hand-edited, saved, and came back clean with CP1251 intact.

**Scope gap:** this Python tool covers OBJECT positions + terrain height (hmap) +
zone bitmaps. It does **not** cover atmosphere/TOD/fog (that's still
Editor.exe's `CMissionEditorAtmosphere` or our hand-editing of the Atmosphere
block — which we already know how to write).

## 6. The strategic picture (updated)

- Object placement → already headless (Python tool).
- Terrain height + zones → already headless (hmap.raw + bitmaps in the Python tool).
- **Atmosphere/TOD/fog → the gap.** We hand-edit it today; Editor.exe edits it
  visually; neither is scripted/headless. This is the highest-value thing to
  add — either extend `mission_io.py` to write the Atmosphere block, or hook
  `CMissionEditorAtmosphere`.
- Cinematics / triggers → Editor.exe only (native `#MissionEditor` keyframe
  system); hooking is the way to understand these if we ever want them headless.

**Recommended next move:** extend `mission_io.py` (or a sibling) to read/write
the Atmosphere block of `Content.script` — we already know its format from the
hand-edits — giving us headless, scriptable time-of-day/weather/fog without
touching Editor.exe or hooking anything. Hooking the native `#Terraformer` /
`#TerrainZoneEditor` remains available if we want the exact native behaviour.
