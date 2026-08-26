# The LOS hook and performance — read before touching `hook.cpp`

**2026-08-26: this hook was costing 55% of the framerate.** It is fixed, but the
mistake is easy to repeat, so the rules are here rather than only in the commit
history.

```
BEFORE   LOS on   51 fps      LOS off  115 fps      ~10.9 ms/frame
AFTER    LOS on  120 fps                            free
```

## `readable()` is a syscall. Treat it as one.

```c
static bool readable(const void *p, size_t n)
{
  MEMORY_BASIC_INFORMATION mbi;
  if (!VirtualQuery(p, &mbi, sizeof(mbi))) return false;   // <-- NtQueryVirtualMemory
  ...
}
```

`VirtualQuery` is a kernel transition. **Never call it per element in a loop.**
Validate the whole span once and index inside it.

Two places got this wrong:

| where | cost |
|---|---|
| `find_endpoints()` | up to `128 + 128*128` = **16,512 syscalls per vision check**, to validate a window **520 bytes** wide |
| `CrewHook()` sweep | **256 syscalls per crew tick, ungated** — `g_crew_calls` hit 125,185 in one session |

## `g_diag_sweep` — the gate for reverse-engineering scaffolding

Default **`false`. Never ship it `true`.** It controls three things that exist
only to *discover* struct layout, not to run the feature:

- the `CrewHook` field sweep (which offset moves when the gunner slews)
- the periodic `[CTRL]`/`[CREW]` dumps (which flag gates the crew update)
- the periodic `[CMDR]` dump

Those dumps were **3,788 of 5,252 log lines** in one ZeeWolf session, and
`llog()` calls `fflush()` on every line — a `WriteFile` syscall each, on the
game thread. Gating them took ZW's log from 5,252 lines / 613 KB to 732 / 66 KB.

One-time (first-tick) dumps are deliberately kept, so a startup record survives.

## The rule this cost a day to learn

**Instrumentation added during reverse engineering must be gated before it
ships. A discovery sweep is not a feature.** Both storms above were debug code
that outlived the question it was written to answer, and nobody switched it off.

**And: when two runs differ, diff the CONFIGURATIONS before profiling either
one** — which hooks, which wrapper, which overlay. An injected DLL is the
largest variable in the room. On 2026-08-26 the decisive evidence (a fast run
had no LOS log) was in hand at 11:40 and read backwards, as "so LOS wasn't the
difference". Its absence *was* the difference; the rest of the day went into
renderers and syscall attribution downstream of that.

See `Documentation/TvT_Performance.md` for the full write-up.
