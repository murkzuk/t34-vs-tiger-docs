@echo off
REM Launch the SANDBOX game with the vision watcher attached.
REM
REM This build only watches. It calls TvT's real vision function, records what
REM it was asked and what it answered, and returns that answer unchanged - no
REM decision is altered. Proving the hook is stable and reading real traffic
REM comes before changing anything.
REM
REM Two safety rails, both enforced in code rather than by care:
REM   - tvt_inject.exe refuses any target outside M:\TvT_INJECT_SANDBOX
REM   - the DLL refuses to arm unless the host process is in that folder
REM
REM What to do: launch, start any mission, drive around for a minute or two
REM near enemy units, quit. Then read the log.
REM
REM Log: M:\TvT_INJECT_SANDBOX\tvt_los.log
REM   - "prologue verified" means the six bytes at Behavior.dll+0xC9E50 were
REM     exactly the mov eax,fs:[0] / push -1 the disassembly predicted. If it
REM     says mismatch instead, nothing was patched and nothing is at risk.
REM   - one sample line per 4096 calls, plus a running total every 200000.

K:\tvt_probe\tvt_inject.exe ^
  M:\TvT_INJECT_SANDBOX\TvsT_fullLOD_HARD_4GB.exe ^
  K:\tvt_los\tvt_los_hook.dll
