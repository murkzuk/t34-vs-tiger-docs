# TvT mission editor (three.js)

`Tools/MissionEditor/` — a browser-based mission editor that reads and writes the
real files in the live install. Built 2026-08-19.

```bash
cd K:\tvt_editor
python server.py
# then open http://127.0.0.1:8765
```

---

## Why this exists

`Editor.exe` works and stays authoritative — it round-trips machine-written
`Content.script` cleanly, which was proven before any of this was built. But for
mission *creation* specifically it hides the things that actually go wrong:

- You cannot see the **router map** while placing anything, and almost every bug
  in this project came from ground that looks open and is not.
- Selection in the 3D view is right-click-and-hope, and it grabs whatever is
  nearest — with a barricade 0.8 m in front of a gun, that is rarely the gun.
- Nothing validates a route until you play it.

This editor is the *view* the Python tooling never had. The tooling already knew
how to read terrain, place objects and validate routes; it just did it blind.

## What it shows

| | |
|---|---|
| **Terrain** | `hmap.raw` as a real 3D surface, 129×129 samples, 1:1 in metres |
| **Router map** | overlay — green = forest, red = impassable, clear = drivable |
| **Terrain map** | overlay — what the player will actually see |
| **Units** | boxes at roughly true size; **grey = German, green = Soviet** |
| **Facing** | a white line out of the nose of every combat object |
| **Navpoints** | amber cones, with the advance route drawn through them |
| **Groups** | which group a selected unit belongs to |

Unit dimensions are approximate on purpose. The point is that a Tiger reads as a
Tiger beside a rifleman and a gun position is legible from above — not that the
boxes are models.

## What it does

- **Click** to select; the object list on the right cross-highlights and
  double-serves as a jump-to.
- **Shift-drag** a unit across the terrain to move it. Z is recomputed from the
  heightmap on save, so a dragged object always sits on the ground.
- **Save** writes back to `Content.script` and deletes `Scripts.cache`, so the
  next launch picks it up.
- **Validate** runs the same checks the generator does, against the engine's own
  budget:

```
unroutable legs    : A* capped at 20000 steps, the engine's actual give-up point
off the map        : silent killer - an object outside 0..9000 is invisible and useless
sharing one point  : four T-34s in one spot crashed the physics to desktop
on blocked ground  : placed where nothing can drive
worst leg          : how close the route came to the budget
```

## Coordinates — written once, deliberately

TvT is `(x, y, z)` with z up; three.js is y-up. The mapping lives in one place:

```js
const toScene = (x, y, z) => new THREE.Vector3(x - WORLD/2, z, y - WORLD/2);
```

Terrain rows and zone-map rows are both read **reversed** (`H[n-1-iy]`) so north
stays north. Getting a row order silently mirrored cost a full day earlier in this
project; it is not left to chance twice.

The file conventions the server relies on, all measured earlier:

- `Content.script` is **CP1251** — a UTF-8 round-trip destroys every Cyrillic byte
  in the file, not only near the edit.
- Line endings differ per mission. The server normalises on read and restores the
  original convention on write, because a regex anchored on a bare newline matches
  **nothing** on the other kind and the tool then reports success having done
  nothing.
- Zone bitmaps are **top-down** (row 0 = world y=0). `hmap.raw` is the
  **opposite** — flipped — with a height factor of `0.07`.

## A bug caught by verifying the artefact

The first write-back produced this:

```
0.764405, 0.644736, 0.000000, 6100.000000      <- no trailing comma
-0.644736, 0.764405, 0.000000, 6300.000000     <- no trailing comma
0.000000, 0.000000, 1.000000, 605.010000,
```

The commas after X and Y are **literal** in the object regex, not captured, so
they had to be re-emitted explicitly. The result is syntactically broken script
that still looks entirely plausible in a diff — the numbers are right and only the
punctuation is missing.

It was caught only because the file was read back after writing rather than
trusting the tool's own success message. That is the third bug in this project
found the same way, and the reason the round-trip test is part of the workflow.

## Limitations

- **Read-only for orders.** Units, waypoints and objectives are data in
  `Content.script` and are editable. Group *behaviour* lives in
  `MissionTasks.script`, which is code — a visual editor either constrains you to
  patterns it can generate, or you keep hand-writing that file. Not attempted.
- **No object creation or deletion yet** — moving and inspecting only.
- **No navpoint editing yet** — the route is drawn but not draggable.
- Positions round-trip; rotations do not (facing is shown, not edited).
- Verified against `Kursk04` (187 objects) with the browser pane not compositing,
  so the scene graph was checked programmatically via `window.__editor.stats()`
  rather than by eye. The geometry, counts and bounds are right; **nobody has
  actually looked at it yet.**
