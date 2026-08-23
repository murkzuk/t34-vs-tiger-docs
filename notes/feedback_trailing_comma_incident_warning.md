# PERMANENT WARNING — the trailing-comma incident (2026-08-22)

A script edit by an AI broke the game's load. Recorded forever so no future AI repeats it.

## What happened

The user approved applying four byte-checked patch cards to the live install
(`M:\T34vsTiger`). Patch 04 (removing the ghost `"CKurtenki2Mission"` entry from
`Scripts\Menus\MissionsMenu.script`) deleted the line but **left a dangling comma** after
`"CC1M6Mission",`. The G5 parser rejects a trailing comma before the closing bracket:

```
[ScriptManager] syntax error: parse error in file: "Scripts\Menus\MissionsMenu.script", line = 32, char = 13
```

The game then refused to load (critical error at startup), and the aborted cache rebuild
left a corrupt 4-byte `Cache\Scripts.cache` that kept blocking loads even after the source
fix. The user had to ask for a full revert. Trust was damaged - correctly.

## The root causes (all real, all avoidable)

1. **Patch design flaw:** the "before/after" card removed a line but did not remove the
   comma left behind by the previous entry. Array edits must show the WHOLE changed block,
   not just the deleted line.
2. **No parse check before hand-off:** the edited file was never validated as parseable
   before the user launched the game. The project has no compiler - the closest proxy is
   scanning for structural hazards (trailing commas, unbalanced delimiters) and reading
   the changed region back.
3. **Cache blindness:** the corrupt 4-byte `Scripts.cache` (from the aborted rebuild) kept
   the game failing even after the real fix. ALWAYS delete `Cache\Scripts.cache` after any
   script edit AND after any aborted launch.

## The rules this incident made permanent

1. NEVER let a script edit touch a game file without showing the complete before/after
   block, including adjacent lines (commas, brackets).
2. After ANY edit: read the changed region back, scan for trailing commas / unbalanced
   delimiters, and confirm zero UTF-8 replacement bytes (EF BF BD).
3. The user is the last gate, always. No write to a game file without explicit go-ahead.
4. When trust is damaged, do not argue - revert, record, and let the evidence rebuild it.

See also: `project_tvt_2026-08-21_log_sweep_findings.md` (the fixes that were applied and
reverted), `K:\TvTDeepseek\patches\REDUX_2026-08-22\patch_04_MissionsMenu.md` (the corrected
card showing the full-block edit).
