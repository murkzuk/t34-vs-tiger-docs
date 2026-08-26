// tvt_prof - a sampling profiler for T-34 vs Tiger.
//
// THE QUESTION IT EXISTS TO ANSWER
//
// Reverting every change made this week took REDUX from 26 fps to 36-40, but a
// framerate of 72 had been measured earlier. So roughly half the loss predates
// anything we touched, and bisecting has run out of things to bisect. Guessing
// which subsystem is slow has already cost several sessions.
//
// This does not guess. It interrupts the game a few hundred times a second,
// records where each thread actually IS, and turns five years of "why is it
// slow" into a ranked list of modules and addresses.
//
// HOW IT WORKS
//
//   1. Cache a module table (base, size, name) OUTSIDE any suspend.
//   2. Every tick: for each thread except our own, SuspendThread ->
//      GetThreadContext -> ResumeThread, and keep the instruction pointer.
//   3. Resolve that pointer against the CACHED table - no API calls while a
//      thread is suspended.
//   4. Aggregate into per-module counts and 4 KB address buckets.
//   5. Dump a ranked report to prof.log every REPORT_SECS.
//
// WHY THE CACHE MATTERS (the deadlock this avoids)
//
// Calling GetModuleFileName or anything else that takes the loader lock while
// a thread is suspended is a classic self-deadlock: if the suspended thread
// held that lock, we wait for it forever and the game hangs. So resolution
// happens only against a snapshot taken while everything was running.
//
// Read-only. It suspends and resumes; it never writes to the game's memory.
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdarg.h>

// 200 Hz is plenty. Suspend/resume is not free, and a profiler that changes
// the thing it measures is worse than no profiler - at 1000 Hz the sampling
// itself would show up in the numbers.
static const int   SAMPLE_HZ    = 200;
static const int   REPORT_SECS  = 20;
static const int   MAX_MODULES  = 512;   // 128 was hit exactly - the table was full, which is why Objects.dll looked like unknown memory
static const int   MAX_BUCKETS  = 4096;   // 4 KB address buckets
static const DWORD MODULE_REFRESH_MS = 5000;

struct Mod { DWORD base, size; char name[64]; };
static Mod   g_mods[MAX_MODULES];
static int   g_nmods;
static CRITICAL_SECTION g_lock;

// Per-thread CPU accounting.
//
// The first version sampled EVERY thread and reported 94% in ntdll - which is
// just "most threads are asleep". A game process keeps a dozen threads parked
// in a wait; they dominate the sample count while doing no work at all.
//
// So: measure CPU time per thread, and only sample the ones actually BURNING
// it. That is what "where do the frames go" means.
struct Thr { DWORD id; __int64 last_cpu, delta; bool hot; };
static Thr   g_thr[64];
static int   g_nthr;
static __int64 g_thr_samples[64];

static __int64 cpu_of(HANDLE h)
{
  FILETIME c, e, k, u;
  if (!GetThreadTimes(h, &c, &e, &k, &u)) return 0;
  __int64 kk = ((__int64)k.dwHighDateTime << 32) | k.dwLowDateTime;
  __int64 uu = ((__int64)u.dwHighDateTime << 32) | u.dwLowDateTime;
  return kk + uu;                       // 100 ns units
}

struct Bucket { int mod; DWORD rva; __int64 hits; };
static Bucket g_buckets[MAX_BUCKETS];
static int    g_nbuckets;
static __int64 g_mod_hits[MAX_MODULES];
static __int64 g_total, g_unknown;

// Unknown-region accounting. Half the samples landed outside every loaded
// module, which is the largest single bucket in the report - so the next
// question is simply WHAT that memory is. VirtualQuery answers it: MEM_IMAGE
// means a module the snapshot missed, MEM_PRIVATE with execute permission
// means generated code (a JIT, or a shader compiler emitting stubs).
struct Region { DWORD base, size; DWORD type, prot; __int64 hits; };
static Region g_regions[64];
static int g_nregions;

static void record_unknown(DWORD eip)
{
  MEMORY_BASIC_INFORMATION mbi;
  if (!VirtualQuery((void *)eip, &mbi, sizeof(mbi))) return;
  DWORD base = (DWORD)mbi.AllocationBase;
  for (int i = 0; i < g_nregions; i++)
    if (g_regions[i].base == base) { g_regions[i].hits++; return; }
  if (g_nregions < 64) {
    g_regions[g_nregions].base = base;
    g_regions[g_nregions].size = (DWORD)mbi.RegionSize;
    g_regions[g_nregions].type = mbi.Type;
    g_regions[g_nregions].prot = mbi.Protect;
    g_regions[g_nregions].hits = 1;
    g_nregions++;
  }
}

static const char *type_name(DWORD t)
{
  if (t == MEM_IMAGE)   return "IMAGE (a module we missed)";
  if (t == MEM_MAPPED)  return "MAPPED (file/section)";
  if (t == MEM_PRIVATE) return "PRIVATE (generated code)";
  return "?";
}

static char g_log[MAX_PATH], g_root[MAX_PATH];

static void plog(const char *fmt, ...)
{
  char line[1024];
  va_list ap; va_start(ap, fmt);
  _vsnprintf(line, sizeof(line) - 2, fmt, ap);
  va_end(ap);
  strcat(line, "\n");
  FILE *f = fopen(g_log, "a");
  if (f) { fputs(line, f); fclose(f); }
}

// ---------------------------------------------------------------- modules
static void refresh_modules(void)
{
  // CreateToolhelp32Snapshot(SNAPMODULE) fails intermittently with
  // ERROR_BAD_LENGTH while modules are loading - and silently returning left
  // the table at 20 entries, which is why half the samples looked like they
  // were nowhere. Retry, and ask for 32-bit modules explicitly.
  HANDLE snap = INVALID_HANDLE_VALUE;
  for (int attempt = 0; attempt < 12; attempt++) {
    snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
                                    GetCurrentProcessId());
    if (snap != INVALID_HANDLE_VALUE) break;
    if (GetLastError() != ERROR_BAD_LENGTH) return;
    Sleep(20);
  }
  if (snap == INVALID_HANDLE_VALUE) return;
  MODULEENTRY32 me; me.dwSize = sizeof(me);
  int n = 0;
  if (Module32First(snap, &me)) {
    do {
      if (n >= MAX_MODULES) break;
      g_mods[n].base = (DWORD)me.modBaseAddr;
      g_mods[n].size = me.modBaseSize;
      lstrcpynA(g_mods[n].name, me.szModule, sizeof(g_mods[n].name));
      n++;
    } while (Module32Next(snap, &me));
  }
  CloseHandle(snap);
  EnterCriticalSection(&g_lock);
  g_nmods = n;
  LeaveCriticalSection(&g_lock);
}

// Resolve against the CACHED table only. No API calls - see the header note.
static int mod_of(DWORD addr, DWORD *rva)
{
  for (int i = 0; i < g_nmods; i++)
    if (addr >= g_mods[i].base && addr < g_mods[i].base + g_mods[i].size) {
      *rva = addr - g_mods[i].base;
      return i;
    }
  return -1;
}

// ---------------------------------------------------------------------------
// FINE HISTOGRAM - 64-byte resolution over ONE configured range.
//
// WHY: the 4 KB page report says `Objects.dll +0x17D000` is the hottest code in
// the game, but that page holds SEVENTEEN functions. Attributing the page's
// heat to any one of them by reading disassembly is guesswork, and guesswork
// has been wrong three times today. 64 bytes separates them.
//
// O(1) per sample - a direct index, no scan - so it cannot perturb what it is
// measuring. Set FINE_BASE/FINE_LEN to the range of interest and rebuild.
// ---------------------------------------------------------------------------
// FULL-MODULE MAP: 1 KB buckets across an entire module, so the report is a
// complete distribution rather than a top-15 list. The question it exists to
// answer: half the frame is in code that never ranks - is that genuinely
// smeared across the whole module (unfixable by any single change), or is
// there concentration nobody has looked at yet? The coverage curve below
// answers that directly: how many buckets to reach 50 / 80 / 95%.
static const char *FULL_MOD   = "Objects.dll";
static const int   FULL_SHIFT = 10;          // 1 KB buckets
static __int64 g_full[4096];                 // covers 4 MB of .text
static __int64 g_full_total;

// jm 2026-08-26: re-aimed at ntdll's SYSCALL STUB TABLE. 20.6% of the whole
// frame lands in ntdll +0x076000..+0x078FFF, which is the Nt*/Zw* thunks -
// each stub is exactly 16 bytes, so 16-byte buckets name the exact syscall.
// A 4 KB page here holds 256 different syscalls, which is why the page-level
// report could only say "a syscall" and not which one.
static const char *FINE_MOD  = "ntdll.dll";
static const DWORD FINE_BASE = 0x076000;    // syscall stub table
static const DWORD FINE_LEN  = 0x03000;     // 12 KB - the three hot pages
static const int   FINE_SHIFT = 4;          // 16-byte buckets = one stub each
static __int64 g_fine[FINE_LEN >> FINE_SHIFT];
static __int64 g_fine_total;

// ---------------------------------------------------------------------------
// CALLER ATTRIBUTION for the syscall stubs.  jm 2026-08-26
//
// 20% of the frame sits in ntdll's Nt*/Zw* stubs, and half of THAT is one
// call: NtWaitForAlertByThreadId - the Win10 futex under SRW locks, modern
// critical sections and std::mutex.  The instruction pointer alone cannot say
// WHOSE lock it is: the game's own code, DXVK's, or the driver's.
//
// So when a sample lands in the stub range, walk the captured stack and find
// the first word that looks like a return address into some module OTHER than
// ntdll.  That names the caller.  Heuristic, not a real unwind - a stack word
// can be a stale value rather than a live return address - so read the result
// as a ranking, not proof.  Anything below a few percent here is noise.
static const DWORD STK_LO = 0x076000, STK_HI = 0x079000;   // the stub range
static __int64 g_caller_hits[MAX_MODULES];
static __int64 g_caller_total, g_caller_none;
struct CallerB { int mod; DWORD rva; __int64 hits; };
static CallerB g_cb[512]; static int g_ncb;

static void record_caller(const DWORD *stk, int n)
{
  for (int i = 0; i < n; i++) {
    DWORD rva; int m = mod_of(stk[i], &rva);
    if (m < 0) continue;
    if (strcmp(g_mods[m].name, "ntdll.dll") == 0) continue;   // skip ntdll internals
    if (strcmp(g_mods[m].name, "tvt_prof.dll") == 0) continue; // never ourselves
    // KERNELBASE/kernel32 are the Win32 wrapper layer, not a caller: every
    // WaitForSingleObject, RegOpenKeyEx and CreateFile passes through them.
    // Skip to reach the module that actually wanted the lock.
    if (_stricmp(g_mods[m].name, "KERNELBASE.dll") == 0) continue;
    if (_stricmp(g_mods[m].name, "KERNEL32.DLL")   == 0) continue;
    if (_stricmp(g_mods[m].name, "kernel.appcore.dll") == 0) continue;
    g_caller_hits[m]++; g_caller_total++;
    DWORD bk = rva & ~0xFFFu;
    for (int j = 0; j < g_ncb; j++)
      if (g_cb[j].mod == m && g_cb[j].rva == bk) { g_cb[j].hits++; return; }
    if (g_ncb < 512) { g_cb[g_ncb].mod=m; g_cb[g_ncb].rva=bk; g_cb[g_ncb].hits=1; g_ncb++; }
    return;                       // first non-ntdll frame only
  }
  g_caller_none++;
}

static void record(DWORD eip)
{
  g_total++;
  DWORD rva;
  int m = mod_of(eip, &rva);
  if (m < 0) { g_unknown++; record_unknown(eip); return; }
  g_mod_hits[m]++;
  if ((rva >> FULL_SHIFT) < 4096 && strcmp(g_mods[m].name, FULL_MOD) == 0) {
    g_full[rva >> FULL_SHIFT]++;
    g_full_total++;
  }
  if (rva - FINE_BASE < FINE_LEN && strcmp(g_mods[m].name, FINE_MOD) == 0) {
    g_fine[(rva - FINE_BASE) >> FINE_SHIFT]++;
    g_fine_total++;
  }
  DWORD bucket = rva & ~0xFFFu;
  for (int i = 0; i < g_nbuckets; i++)
    if (g_buckets[i].mod == m && g_buckets[i].rva == bucket) {
      g_buckets[i].hits++; return;
    }
  if (g_nbuckets < MAX_BUCKETS) {
    g_buckets[g_nbuckets].mod = m;
    g_buckets[g_nbuckets].rva = bucket;
    g_buckets[g_nbuckets].hits = 1;
    g_nbuckets++;
  }
}

// ---------------------------------------------------------------- report
static void report(void)
{
  plog("");
  plog("================ %I64d samples over ~%d s ================",
       g_total, REPORT_SECS);
  if (!g_total) { plog("  no samples yet"); return; }

  // Modules first: this alone usually names the culprit. Engine.dll heavy
  // means the game's own code; d3d9.dll heavy means the graphics wrapper;
  // ntdll/win32u heavy means waiting on something.
  plog("  BUSY THREADS (CPU burned in the last second)");
  for (int i = 0; i < g_nthr; i++)
    if (g_thr[i].hot)
      plog("    thread %-6u  %6.1f ms/s%s", g_thr[i].id,
           g_thr[i].delta / 10000.0, "");
  plog("  WHERE THE TIME GOES, by module (busy threads only, %d modules known)", g_nmods);
  for (int pass = 0; pass < 12; pass++) {
    int best = -1; __int64 bh = 0;
    for (int i = 0; i < g_nmods; i++)
      if (g_mod_hits[i] > bh) { bh = g_mod_hits[i]; best = i; }
    if (best < 0 || bh == 0) break;
    plog("    %-22s %7.2f%%   %I64d", g_mods[best].name,
         100.0 * bh / g_total, bh);
    g_mod_hits[best] = -g_mod_hits[best];      // mark as printed
  }
  for (int i = 0; i < g_nmods; i++)
    if (g_mod_hits[i] < 0) g_mod_hits[i] = -g_mod_hits[i];
  if (g_unknown)
    plog("    %-22s %7.2f%%   %I64d", "(outside any module)",
         100.0 * g_unknown / g_total, g_unknown);

  if (g_unknown) {
    plog("  THE UNKNOWN HALF - what that memory actually is");
    for (int pass = 0; pass < 8; pass++) {
      int best = -1; __int64 bh = 0;
      for (int i = 0; i < g_nregions; i++)
        if (g_regions[i].hits > bh) { bh = g_regions[i].hits; best = i; }
      if (best < 0 || bh == 0) break;
      // Name it. Safe here: report time, nothing suspended, so taking the
      // loader lock cannot deadlock against a frozen thread.
      char nm[MAX_PATH] = "";
      if (g_regions[best].type == MEM_IMAGE)
        GetModuleFileNameA((HMODULE)g_regions[best].base, nm, MAX_PATH);
      const char *leaf = nm;
      for (const char *c = nm; *c; c++) if (*c == 92) leaf = c + 1;
      plog("    base %08X  %6.2f%%  %-22s %s",
           g_regions[best].base, 100.0 * bh / g_total,
           *leaf ? leaf : type_name(g_regions[best].type),
           *leaf ? "" : "(unnamed)");
      g_regions[best].hits = -g_regions[best].hits;
    }
    for (int i = 0; i < g_nregions; i++)
      if (g_regions[i].hits < 0) g_regions[i].hits = -g_regions[i].hits;
  }

  // Then the hot 4 KB pages, which is where to point a disassembler.
  plog("  HOTTEST ADDRESSES (4 KB pages)");
  for (int pass = 0; pass < 15; pass++) {
    int best = -1; __int64 bh = 0;
    for (int i = 0; i < g_nbuckets; i++)
      if (g_buckets[i].hits > bh) { bh = g_buckets[i].hits; best = i; }
    if (best < 0 || bh == 0) break;
    plog("    %-22s +0x%06X   %6.2f%%   %I64d",
         g_mods[g_buckets[best].mod].name, g_buckets[best].rva,
         100.0 * bh / g_total, bh);
    g_buckets[best].hits = -g_buckets[best].hits;
  }
  for (int i = 0; i < g_nbuckets; i++)
    if (g_buckets[i].hits < 0) g_buckets[i].hits = -g_buckets[i].hits;
  if (g_full_total) {
    // rank a copy so the coverage curve and the listing agree
    static __int64 sorted[4096];
    int n = 0;
    for (int i = 0; i < 4096; i++) if (g_full[i]) sorted[n++] = g_full[i];
    for (int a = 1; a < n; a++) {            // insertion sort, descending
      __int64 v = sorted[a]; int b = a - 1;
      while (b >= 0 && sorted[b] < v) { sorted[b+1] = sorted[b]; b--; }
      sorted[b+1] = v;
    }
    plog("  FULL MAP of %s  (1 KB buckets, %I64d samples in %d live buckets)",
         FULL_MOD, g_full_total, n);
    __int64 run = 0; int at50 = -1, at80 = -1, at95 = -1;
    for (int i = 0; i < n; i++) {
      run += sorted[i];
      if (at50 < 0 && run * 100 >= g_full_total * 50) at50 = i + 1;
      if (at80 < 0 && run * 100 >= g_full_total * 80) at80 = i + 1;
      if (at95 < 0 && run * 100 >= g_full_total * 95) at95 = i + 1;
    }
    plog("    CONCENTRATION: 50%% of this module is in %d KB, 80%% in %d KB, 95%% in %d KB",
         at50, at80, at95);
    plog("    (few KB = concentrated and attackable; hundreds = smeared, no single fix)");
    for (int pass = 0; pass < 20; pass++) {
      int best = -1; __int64 bh = 0;
      for (int i = 0; i < 4096; i++) if (g_full[i] > bh) { bh = g_full[i]; best = i; }
      if (best < 0 || bh == 0) break;
      plog("    +0x%06X   %6.2f%% of all   %6.2f%% of module   %I64d",
           best << FULL_SHIFT, 100.0 * bh / g_total,
           100.0 * bh / g_full_total, bh);
      g_full[best] = -g_full[best];
    }
    for (int i = 0; i < 4096; i++) if (g_full[i] < 0) g_full[i] = -g_full[i];
  }
  if (g_fine_total) {
    // Who is actually holding the lock. See record_caller().
  if (g_caller_total) {
    plog("  WHO CALLS THE SYSCALLS  (first non-ntdll frame on the stack, %I64d attributed, %I64d unattributed)",
         g_caller_total, g_caller_none);
    static char shown_m[MAX_MODULES]; memset(shown_m, 0, sizeof(shown_m));
    for (int pass = 0; pass < 8; pass++) {
      int best = -1; __int64 bh = 0;
      for (int i = 0; i < g_nmods; i++)
        if (!shown_m[i] && g_caller_hits[i] > bh) { bh = g_caller_hits[i]; best = i; }
      if (best < 0 || bh == 0) break;
      plog("    %-22s %7.2f%% of syscall time   %I64d", g_mods[best].name,
           100.0 * bh / g_caller_total, bh);
      shown_m[best] = 1;
    }
    plog("    -- caller pages --");
    static char shown_c[512]; memset(shown_c, 0, sizeof(shown_c));
    for (int pass = 0; pass < 8; pass++) {
      int best = -1; __int64 bh = 0;
      for (int i = 0; i < g_ncb; i++)
        if (!shown_c[i] && g_cb[i].hits > bh) { bh = g_cb[i].hits; best = i; }
      if (best < 0 || bh == 0) break;
      plog("    %-18s +0x%06X   %6.2f%%   %I64d", g_mods[g_cb[best].mod].name,
           g_cb[best].rva, 100.0 * bh / g_caller_total, bh);
      shown_c[best] = 1;
    }
  }
  plog("  FINE (%d-byte buckets in %s +0x%06X..+0x%06X, %I64d samples)",
         1 << FINE_SHIFT, FINE_MOD, FINE_BASE, FINE_BASE + FINE_LEN, g_fine_total);
    for (int pass = 0; pass < 12; pass++) {
      int best = -1; __int64 bh = 0;
      for (int i = 0; i < (int)(FINE_LEN >> FINE_SHIFT); i++)
        if (g_fine[i] > bh) { bh = g_fine[i]; best = i; }
      if (best < 0 || bh == 0) break;
      plog("    +0x%06X   %6.2f%% of all   %6.2f%% of range   %I64d",
           FINE_BASE + (best << FINE_SHIFT),
           100.0 * bh / g_total, 100.0 * bh / g_fine_total, bh);
      g_fine[best] = -g_fine[best];
    }
    for (int i = 0; i < (int)(FINE_LEN >> FINE_SHIFT); i++)
      if (g_fine[i] < 0) g_fine[i] = -g_fine[i];
  }
  plog("========================================================");
}

// ---------------------------------------------------------------- sampler
static DWORD WINAPI Sampler(LPVOID)
{
  DWORD me = GetCurrentThreadId(), pid = GetCurrentProcessId();
  DWORD last_refresh = 0, last_report = GetTickCount(), last_rank = 0;
  const DWORD period = 1000 / SAMPLE_HZ;

  for (;;) {
    DWORD now = GetTickCount();
    if (now - last_refresh > MODULE_REFRESH_MS) {
      refresh_modules();               // outside any suspend, deliberately
      last_refresh = now;
    }

    // Re-rank threads by CPU burn every refresh. A thread that used no CPU
    // since last time is asleep and is not what we are looking for.
    if (now - last_rank > 1000) {
      HANDLE ts = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
      if (ts != INVALID_HANDLE_VALUE) {
        THREADENTRY32 t; t.dwSize = sizeof(t);
        int n = 0;
        if (Thread32First(ts, &t)) {
          do {
            if (t.th32OwnerProcessID != pid || t.th32ThreadID == me) continue;
            if (n >= 64) break;
            HANDLE h = OpenThread(THREAD_QUERY_INFORMATION, FALSE, t.th32ThreadID);
            if (!h) continue;
            __int64 c = cpu_of(h);
            CloseHandle(h);
            // carry the previous reading for this id if we have it
            __int64 prev = 0;
            for (int k = 0; k < g_nthr; k++)
              if (g_thr[k].id == t.th32ThreadID) { prev = g_thr[k].last_cpu; break; }
            g_thr[n].id = t.th32ThreadID;
            g_thr[n].delta = prev ? (c - prev) : 0;
            g_thr[n].last_cpu = c;
            g_thr[n].hot = false;
            n++;
          } while (Thread32Next(ts, &t));
        }
        CloseHandle(ts);
        g_nthr = n;
        // Mark every thread that burned at least 5 ms in the last second.
        // That keeps the render thread AND any real worker, and drops the
        // parked ones.
        for (int k = 0; k < g_nthr; k++)
          if (g_thr[k].delta > 50000) g_thr[k].hot = true;   // 5 ms in 100ns units
      }
      last_rank = now;
    }

    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snap != INVALID_HANDLE_VALUE) {
      THREADENTRY32 te; te.dwSize = sizeof(te);
      if (Thread32First(snap, &te)) {
        do {
          if (te.th32OwnerProcessID != pid) continue;
          if (te.th32ThreadID == me) continue;
          // Only threads actually burning CPU.
          bool hot = false;
          for (int k = 0; k < g_nthr; k++)
            if (g_thr[k].id == te.th32ThreadID) { hot = g_thr[k].hot; break; }
          if (!hot) continue;
          HANDLE h = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT,
                                FALSE, te.th32ThreadID);
          if (!h) continue;
          if (SuspendThread(h) != (DWORD)-1) {
            CONTEXT ctx; ctx.ContextFlags = CONTEXT_CONTROL;
            DWORD eip = 0;
            static const int STK_WORDS = 256;
            DWORD stk[STK_WORDS]; int nstk = 0;
            if (GetThreadContext(h, &ctx)) {
              eip = ctx.Eip;
              // Copy the top of the stack while the thread is frozen. Plain
              // reads guarded by SEH - no API call, so no lock the suspended
              // thread could be holding, which is the deadlock this whole
              // profiler is built to avoid.
              DWORD rva; int mm = mod_of(eip, &rva);
              if (mm >= 0 && rva - STK_LO < (STK_HI - STK_LO)
                  && strcmp(g_mods[mm].name, "ntdll.dll") == 0) {
                __try {
                  const DWORD *sp = (const DWORD *)ctx.Esp;
                  for (int w = 0; w < STK_WORDS; w++) stk[w] = sp[w];
                  nstk = STK_WORDS;
                } __except (EXCEPTION_EXECUTE_HANDLER) { nstk = 0; }
              }
            }
            ResumeThread(h);            // resume BEFORE doing anything else
            if (eip) {
              EnterCriticalSection(&g_lock);
              record(eip);
              if (nstk) record_caller(stk, nstk);
              LeaveCriticalSection(&g_lock);
            }
          }
          CloseHandle(h);
        } while (Thread32Next(snap, &te));
      }
      CloseHandle(snap);
    }

    if (now - last_report > (DWORD)REPORT_SECS * 1000) {
      EnterCriticalSection(&g_lock);
      report();
      LeaveCriticalSection(&g_lock);
      last_report = now;
    }
    Sleep(period);
  }
  // Unreachable, but SEH in the loop stops the compiler proving that.
  return 0;
}

// ---------------------------------------------------------------- attach
// Same opt-in rail as the line-of-sight hook: the allow list lives beside the
// DLL, never inside a game folder, or any install could authorise itself.
static bool allowed(const char *root)
{
  char self[MAX_PATH], list[MAX_PATH];
  GetModuleFileNameA(GetModuleHandleA("tvt_prof.dll"), self, MAX_PATH);
  char *slash = 0;
  for (char *c = self; *c; c++) if (*c == 92) slash = c;
  if (!slash) return false;
  *slash = 0;
  _snprintf(list, MAX_PATH, "%s%ctvt_los_allow.txt", self, 92);
  FILE *f = fopen(list, "rb");
  if (!f) return false;
  char line[MAX_PATH];
  bool ok = false;
  while (fgets(line, sizeof(line), f)) {
    char *p = line;
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '#' || *p == '\r' || *p == '\n' || !*p) continue;
    int n = (int)strlen(p);
    while (n && (p[n-1] == '\r' || p[n-1] == '\n' || p[n-1] == ' ')) p[--n] = 0;
    if (_stricmp(p, root) == 0) { ok = true; break; }
  }
  fclose(f);
  return ok;
}

static DWORD WINAPI Boot(LPVOID)
{
  char exe[MAX_PATH];
  GetModuleFileNameA(NULL, exe, MAX_PATH);
  lstrcpynA(g_root, exe, MAX_PATH);
  char *slash = 0;
  for (char *c = g_root; *c; c++) if (*c == 92) slash = c;
  if (slash) *slash = 0;
  _snprintf(g_log, MAX_PATH, "%s%ctvt_prof.log", g_root, 92);

  FILE *f = fopen(g_log, "w"); if (f) fclose(f);   // fresh each run

  plog("tvt_prof attached to %s", exe);
  plog("install root: %s", g_root);
  if (!allowed(g_root)) {
    plog("NOT in tvt_los_allow.txt beside the DLL - standing down, nothing sampled.");
    return 0;
  }
  plog("sampling at %d Hz, report every %d s", SAMPLE_HZ, REPORT_SECS);
  plog("read-only: threads are suspended and resumed, never written to");

  refresh_modules();
  plog("modules cached: %d", g_nmods);
  CreateThread(NULL, 0, Sampler, NULL, 0, NULL);
  return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID)
{
  if (reason == DLL_PROCESS_ATTACH) {
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    CreateThread(NULL, 0, Boot, NULL, 0, NULL);
  }
  return TRUE;
}
