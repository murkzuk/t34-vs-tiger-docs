# REDUX fixes — ready to apply (Tuesday)

Made 2026-08-22. Checked byte-for-byte against the real game files on `M:\T34vsTiger`.
**APPLIED to the live install on 2026-08-22** (byte-safe, rollback kit verified, cache
cleared). In-game test pending — do NOT re-apply; verify by grepping the files first.

## What each change does (plain words)

1. **patch_01** — stops a German infantry group spinning in a loop forever (the big one,
   the 6,451 "stack overflow" lines). Fix lives in the shared `UnitGroup.script`, so it
   protects every mission, not just one.
2. **patch_02** — two small fixes in Mission 2: a misspelled command for the BTR half-tracks,
   and a "only do this once" guard for the same infantry group (belt-and-braces).
3. **patch_03** — the same misspelled command in another mission (Campaign 2, Mission 3).
4. **patch_04** — removes a ghost menu entry ("Kurtenki 2") that never had a real mission,
   which was making the menu log errors.

## The rules that matter (they are the whole trick)

- `.script` files are old-style Windows text (CP1251). **Never** open/save them in a modern
  editor — that destroys hidden letters. Apply changes with byte-safe tools only.
- After any change, **delete `M:\T34vsTiger\Cache\Scripts.cache`** or the change won't show
  in-game ("the edit did nothing" is this, 9 times out of 10).
- **Backups live OUTSIDE the game folders only** — the pristine copies are already in the
  rollback kit at `K:\TvTDeepseek\rollback\REDUX_2026-08-22\`. **Never leave any extra file
  inside a game folder**: TvT reads every file regardless of extension, so a stray
  `.bak`/`.md` copy = "Duplicate Class" errors. If a backup must sit inside a game folder,
  zip it first — that is the only way to hide it from the game.
- Test by launching `TvsT_fullLOD_HARD_4GB.exe` (not the plain exe), then read
  `M:\T34vsTiger\execution.log`.

## What testing looks like (for whoever tests)

- Mission 2: play until the German infantry patrol reaches the end of its road — that was
  where the loop started. The log should show **no** "Possible stack overflow" lines.
- Campaign 2 Mission 3: just loads and plays normally.
- Mission menu: 6 Soviet missions listed, **no** `CKurtenki2` errors in the log.

Worst case for any change: does nothing visible, or a mission acts odd. Both are easy to
undo (restore the `.bak`). This is the safe order: **patch_01 on its own first** (it is the
only one that touches shared code), then 02 + 03 + 04 together.
