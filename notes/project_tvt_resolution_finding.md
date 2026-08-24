# Internal resolution finding (2026-08-24)

## Bottom line

- The game renders at the monitor's **native 1920×1080**, NOT 1024×768.
- There is **no resolution left to raise** — both monitors are 1080p and the game
  is already at that ceiling.

## Evidence (live registry read)

Key `HKEY_CURRENT_USER\Software\G5 Software\T34`:

```
ScreenWidth   = 1920
ScreenHeight  = 1080
RefreshRate   = 180
WindowMode    = 0      (fullscreen)
ColorDepth    = 32
VideoDevice   = 0
```

## Where the resolution actually lives

- The in-game **Video Options → Resolution** menu (`VideoOptionsMenuBase.script`)
  is a real dropdown built from `GameSettings.GetVideoModesList()`, with a
  fullscreen/windowed toggle. `ApplySettings()` calls
  `GameSettings.SetVideoMode(device, mode, windowMode)`.
- The chosen mode is saved to the **registry** (key above), not to any script.
- `WindowWidth = 1024` / `WindowHeight = 768` in `GameSettings.script` are
  **first-run default fallbacks only** — the engine uses them until the user picks
  a mode, then the registry value wins. They are not the live resolution.

## Why it still looks soft (not the resolution)

1. **2001-era source art.** Tank/terrain textures and models shipped low-res.
   Nothing to raise here.
2. **HUD / cockpit is 1024×768 art stretched to 1080p.**
   - `CockpitSkin.script`: for any width > 1024 it sets `CurrentMode = 1280` but
     still loads `Materials_1024_768`.
   - `Materials_1280_960` exists in the script but is **commented out**.
   - The 1280×960 `.tex` files were **never shipped** (searched `Resources\` —
     none exist). Uncommenting would reference missing files and break the cockpit.

## Actionable takeaways

- **Resolution is a dead end.** The real visual gains are atmosphere / lighting /
  fog / LOD — already in progress.
- **ReShade self-fight:** `tvt.ini` runs FXAA alongside SMAA + LumaSharpen + CAS.
  FXAA softens while the others sharpen. One-checkbox in-game test: turn **FXAA
  off** and let SMAA + CAS do the work, for crisper tank/terrain edges.

## Editing rules (reminder)

- `.script` = CP1251; byte-level edits only; verify EF BF BD count stays 0.
- Delete `Cache\Scripts.cache` after any script edit (cold rebuild ~2 min).
- Backups stay in `K:\TvTDeepseek\rollback\`, never inside the game folders.
