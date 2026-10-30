// ---------------------------------------------------------------------------
// maplookup_memo - a one-entry cache in front of TvT's hottest function.
//
// TARGET: Objects.dll + 0x17DAB0, MSVC std::map::lower_bound. Measured at
// **41,000 calls per frame** and 7.59% of the entire frame - the single most
// concentrated cost in the game. And measured, across 23 report blocks with no
// spread at all (67.0 - 67.5%):
//
//     67.2% of calls repeat the IMMEDIATELY PREVIOUS key.
//
// So the caller loops over things that share a key and re-walks the tree for
// each one. A one-entry cache turns that into a single walk per group - which
// is hoisting the lookup out of the loop, done from outside the engine without
// touching the loop.
//
// EXPECTED: +2 to +4 fps from 69. The noise floor on this machine is +-4%
// (+-2.8 fps), so this may land at or below what can be proven. That is the
// honest expectation and it is written here so the result cannot be
// rationalised afterwards.
//
// ---------------------------------------------------------------------------
// WHY THIS IS SAFE: IT VALIDATES ITSELF BEFORE IT DOES ANYTHING
//
// A stale cache in front of a container lookup returns a dangling iterator, and
// the game corrupts or crashes. Reasoning about MSVC's std::map layout is not
// good enough - and six theories died today from reasoning.
//
// So the cache does not trust itself. It starts in VERIFY mode:
//
//   VERIFY  - always calls the real function, AND computes what the cache would
//             have returned, and compares. Counts agreements and disagreements.
//             Costs a little speed, changes no behaviour whatsoever.
//   FAST    - entered ONLY after VERIFY_QUOTA consecutive agreements with zero
//             disagreements. Now it can actually skip the tree walk.
//   DISABLED- entered instantly and permanently on the FIRST disagreement, and
//             logged loudly. From then on it is a pure pass-through.
//
// So a wrong guess about the map's layout produces a log line and a normal
// game, never a corrupted one.
//
// THE GUARD. A cache hit requires all four to match the previous call:
//     this pointer      - same map
//     key               - same lookup
//     root node         - *(this->_Myhead + 4); changes on rebalance
//     size              - *(this + 4); changes on ANY insert or erase
// Two loads instead of a tree descent. The size field is the important one -
// no insert or erase can leave it unchanged - and VERIFY mode is what proves
// the offset is right rather than assumed.
//
// CALLING CONVENTION. The target is __thiscall:
//     Iterator* __thiscall lower_bound(map* this, Iterator* ret, const int* key)
// MSVC cannot declare a __thiscall function pointer, but __fastcall with a
// dummy second parameter is ABI-identical: arg1 in ecx, arg2 in edx (unused),
// the rest on the stack, callee cleans up. The original ends in `ret 8`, which
// is exactly what __fastcall expects for two stack arguments.
//
// Objects.dll RELOCATES. The address is always GetModuleHandleA + RVA, and the
// six prologue bytes are verified before anything is written.
// ---------------------------------------------------------------------------

#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define LOG_PATH   "K:\\TvTDeepseek\\maplookup_memo\\maplookup_cache.log"
#define ALLOW_PATH "K:\\TvTDeepseek\\maplookup_memo\\tvt_los_allow.txt"

static const DWORD TARGET_RVA = 0x17DAB0;
static const char *TARGET_MOD = "Objects.dll";
static const BYTE  EXPECT[6]  = { 0x51, 0x8B, 0x09, 0x8B, 0x41, 0x04 };

static const __int64 VERIFY_QUOTA = 400000;   // agreements needed before FAST
static const double  REPORT_SECS  = 5.0;

// ---------------------------------------------------------------------------
static FILE *g_log;
static CRITICAL_SECTION g_lock;

static void llog(const char *fmt, ...)
{
  if (!g_log) return;
  EnterCriticalSection(&g_lock);
  va_list ap; va_start(ap, fmt);
  vfprintf(g_log, fmt, ap); va_end(ap);
  fputc('\n', g_log); fflush(g_log);
  LeaveCriticalSection(&g_lock);
}

static bool host_is_allowed(void)
{
  char exe[MAX_PATH] = "";
  if (!GetModuleFileNameA(NULL, exe, MAX_PATH)) return false;
  char *slash = NULL;
  for (char *c = exe; *c; c++) if (*c == '\\') slash = c;
  if (!slash) return false;
  *slash = 0;
  FILE *f = fopen(ALLOW_PATH, "r");
  if (!f) { llog("allow list missing (%s) - not arming", ALLOW_PATH); return false; }
  char line[MAX_PATH]; bool ok = false;
  while (fgets(line, sizeof line, f)) {
    char *p = line;
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '#' || *p == '\r' || *p == '\n' || !*p) continue;
    int n = (int)strlen(p);
    while (n > 0 && (p[n-1]=='\r'||p[n-1]=='\n'||p[n-1]==' '||p[n-1]=='\t')) p[--n] = 0;
    if (n > 0 && _stricmp(p, exe) == 0) { ok = true; break; }
  }
  fclose(f);
  llog("host %s -> %s", exe, ok ? "ALLOWED" : "not listed, not arming");
  return ok;
}

// ---------------------------------------------------------------------------
typedef void * (__fastcall *LowerBoundFn)(void *self, void *edx_unused,
                                          void **ret, const int *key);
static LowerBoundFn g_orig;

enum Mode { MODE_VERIFY = 0, MODE_FAST = 1, MODE_DISABLED = 2, MODE_BYPASS = 3 };
static volatile LONG g_mode = MODE_VERIFY;

// the single cache entry
static void    *c_self;
static int      c_key;
static unsigned c_root, c_size;
static void    *c_node;
static bool     c_valid;

// counters
static __int64 g_calls, g_hits, g_verified, g_mismatch;

static void __cdecl on_mismatch(void *self, int key, void *got, void *cached)
{
  InterlockedExchange(&g_mode, MODE_DISABLED);
  g_mismatch++;
  llog("");
  llog("*** CACHE DISABLED - the guard is not sufficient ***");
  llog("    map %08X  key %d   real result %08X   cache would have said %08X",
       (DWORD)self, key, (DWORD)got, (DWORD)cached);
  llog("    This is the verify mode doing its job: the game is unaffected and");
  llog("    the hook is now a pass-through. The guard (this/key/root/size) does");
  llog("    not fully describe when the answer can change, so the assumption");
  llog("    about the map layout or about mutation between calls is wrong.");
  llog("");
}

static void * __fastcall memo_hook(void *self, void *edx_unused,
                                   void **ret, const int *key)
{
  g_calls++;

  if (g_mode == MODE_DISABLED || !self || !ret || !key)
    return g_orig(self, edx_unused, ret, key);

  const int      k    = *key;
  const unsigned root = *(unsigned *)(*(char **)self + 4);   // _Myhead->_Parent
  const unsigned size = *(unsigned *)((char *)self + 4);     // _Mysize

  const bool guard_matches =
      c_valid && self == c_self && k == c_key &&
      root == c_root && size == c_size;

  // FAST: the whole point - skip the tree walk entirely.
  if (g_mode == MODE_FAST && guard_matches) {
    *ret = c_node;
    g_hits++;
    return ret;
  }

  // Always do the real lookup in VERIFY, and on any miss.
  void *r = g_orig(self, edx_unused, ret, key);
  void *node = *ret;

  if (g_mode == MODE_VERIFY && guard_matches) {
    if (node != c_node) { on_mismatch(self, k, node, c_node); }
    else {
      g_verified++;
      if (g_verified >= VERIFY_QUOTA && g_mismatch == 0) {
        InterlockedExchange(&g_mode, MODE_FAST);
        llog("");
        llog("*** VERIFY PASSED - cache is now LIVE ***");
        llog("    %I64d consecutive agreements, 0 disagreements.", g_verified);
        llog("    The guard correctly predicts the answer, so the tree walk can");
        llog("    now actually be skipped, and stays that way for the session.");
        llog("");
      }
    }
  }

  c_self = self; c_key = k; c_root = root; c_size = size;
  c_node = node; c_valid = true;
  return r;
}

// ---------------------------------------------------------------------------
static BYTE *g_tramp;

static bool patch_target(void)
{
  HMODULE m = GetModuleHandleA(TARGET_MOD);
  if (!m) return false;
  BYTE *t = (BYTE *)m + TARGET_RVA;

  if (memcmp(t, EXPECT, 6) != 0) {
    llog("REFUSING to patch: prologue at %08X is %02X %02X %02X %02X %02X %02X",
         (DWORD)t, t[0], t[1], t[2], t[3], t[4], t[5]);
    return false;
  }

  BYTE *tr = (BYTE *)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE,
                                  PAGE_EXECUTE_READWRITE);
  if (!tr) return false;
  memcpy(tr, t, 6);
  tr[6] = 0xE9;
  *(DWORD *)(tr + 7) = (DWORD)(t + 6) - (DWORD)(tr + 6 + 5);
  g_tramp = tr;
  g_orig = (LowerBoundFn)tr;

  DWORD old;
  if (!VirtualProtect(t, 6, PAGE_EXECUTE_READWRITE, &old)) return false;
  t[0] = 0xE9;
  *(DWORD *)(t + 1) = (DWORD)memo_hook - (DWORD)(t + 5);
  t[5] = 0x90;
  VirtualProtect(t, 6, old, &old);
  FlushInstructionCache(GetCurrentProcess(), t, 6);

  llog("hooked %s+0x%06X at %08X (base %08X), trampoline %08X",
       TARGET_MOD, TARGET_RVA, (DWORD)t, (DWORD)m, (DWORD)tr);
  llog("mode: VERIFY - the real function still runs every time. %I64d clean",
       VERIFY_QUOTA);
  llog("agreements are needed before the cache is allowed to skip anything.");
  return true;
}

// ---------------------------------------------------------------------------
static void report(double secs)
{
  static __int64 last_calls, last_hits;
  __int64 calls = g_calls - last_calls, hits = g_hits - last_hits;
  last_calls = g_calls; last_hits = g_hits;
  if (!calls) return;

  const char *mode = g_mode == MODE_FAST ? "FAST (cache live)"
                   : g_mode == MODE_VERIFY ? "VERIFY (still checking)"
                   : "DISABLED (pass-through)";
  llog("[%.0fs] %-24s calls %9I64d (%7.0f/s)  hits %8I64d (%5.1f%%)"
       "  MISMATCHES %I64d",
       secs, mode, calls, calls / secs, hits, 100.0 * hits / calls, g_mismatch);
}

static DWORD WINAPI boot(LPVOID)
{
  for (int i = 0; i < 1500; i++) {
    if (GetModuleHandleA(TARGET_MOD)) { if (!patch_target()) return 0; break; }
    Sleep(20);
  }
  if (!g_tramp) { llog("%s never appeared", TARGET_MOD); return 0; }
  for (;;) { Sleep((DWORD)(REPORT_SECS * 1000)); report(REPORT_SECS); }
}

// ---------------------------------------------------------------------------
// SELF-A/B. The in-game F9 counter costs frames of its own, and eyeballing two
// separate runs cannot rule out standing somewhere slightly different or the
// +-3 fps of run-to-run drift. Both problems vanish if the DLL measures its own
// framerate and toggles its own cache: same scene, same session, same position,
// one variable.
//
// Every AB_SECS the cache flips between FAST and BYPASS. BYPASS is a pure
// pass-through - it still refreshes the cache entry, it just never uses it - so
// flipping is instant and free. Present is hooked only to count frames.
//
// Direct3DCreate9 must be patched DURING d3d9.dll's load, via a loader
// notification. A polling thread loses that race - it did exactly that on the
// first version of the counting probe, and the whole run produced nothing.
// ---------------------------------------------------------------------------
static const double AB_SECS = 10.0;

typedef IDirect3D9 * (WINAPI *D3D9CreateFn)(UINT);
typedef HRESULT (STDMETHODCALLTYPE *CreateDeviceFn)(
    IDirect3D9 *, UINT, D3DDEVTYPE, HWND, DWORD, D3DPRESENT_PARAMETERS *, IDirect3DDevice9 **);
typedef HRESULT (STDMETHODCALLTYPE *PresentFn)(
    IDirect3DDevice9 *, const RECT *, const RECT *, HWND, const RGNDATA *);

static D3D9CreateFn   g_orig_create;
static CreateDeviceFn g_orig_cd;
static PresentFn      g_orig_present;
static void **g_d3d9_vt;
static void **g_dev_vt;
static bool   g_d3d_hooked;
static LARGE_INTEGER g_qfreq;
static LONGLONG g_phase_start;
static __int64  g_phase_frames;
static __int64  g_mark_calls, g_mark_hits;
static double   g_fast_fps[64], g_byp_fps[64];
static int      g_nfast, g_nbyp;

static bool patch_slot(void **vt, int slot, void *hook, void **orig, const char *what)
{
  DWORD old;
  if (!VirtualProtect(&vt[slot], 4, PAGE_EXECUTE_READWRITE, &old)) return false;
  *orig = vt[slot]; vt[slot] = hook;
  VirtualProtect(&vt[slot], 4, old, &old);
  FlushInstructionCache(GetCurrentProcess(), &vt[slot], 4);
  llog("hook: %-16s slot %3d", what, slot);
  return true;
}

static double med(double *a, int n)
{
  if (!n) return 0.0;
  for (int i = 1; i < n; i++) {
    double v = a[i]; int j = i - 1;
    while (j >= 0 && a[j] > v) { a[j+1] = a[j]; j--; }
    a[j+1] = v;
  }
  return (n & 1) ? a[n/2] : 0.5 * (a[n/2 - 1] + a[n/2]);
}

static void end_phase(double secs)
{
  if (g_phase_frames < 30) return;
  double fps = g_phase_frames / secs;
  bool was_fast = (g_mode == MODE_FAST);
  if (was_fast) { if (g_nfast < 64) g_fast_fps[g_nfast++] = fps; }
  else          { if (g_nbyp  < 64) g_byp_fps [g_nbyp++ ] = fps; }

  __int64 calls = g_calls - g_mark_calls;
  __int64 hits  = g_hits  - g_mark_hits;
  llog("[A/B] %-6s  %6.1f fps   %I64d frames   lookups %I64d   hits %I64d (%.1f%%)",
       was_fast ? "CACHE" : "BYPASS", fps, g_phase_frames, calls, hits,
       calls ? 100.0 * hits / calls : 0.0);

  if (g_nfast >= 2 && g_nbyp >= 2) {
    double a[64], b[64];
    memcpy(a, g_fast_fps, sizeof(double) * g_nfast);
    memcpy(b, g_byp_fps,  sizeof(double) * g_nbyp);
    double mf = med(a, g_nfast), mb = med(b, g_nbyp);
    llog("      -> median CACHE %.1f vs BYPASS %.1f  =  %+.1f fps  (%+.1f%%)  [%d/%d phases]",
         mf, mb, mf - mb, 100.0 * (mf - mb) / mb, g_nfast, g_nbyp);
  }
}

static HRESULT STDMETHODCALLTYPE HookPresent(
    IDirect3DDevice9 *s, const RECT *a, const RECT *b, HWND c, const RGNDATA *d)
{
  HRESULT r = g_orig_present(s, a, b, c, d);
  g_phase_frames++;
  LARGE_INTEGER t; QueryPerformanceCounter(&t);
  double secs = (double)(t.QuadPart - g_phase_start) / (double)g_qfreq.QuadPart;
  if (secs >= AB_SECS) {
    if (g_mode == MODE_FAST || g_mode == MODE_BYPASS) {
      end_phase(secs);
      InterlockedExchange(&g_mode, g_mode == MODE_FAST ? MODE_BYPASS : MODE_FAST);
    }
    g_phase_start = t.QuadPart;
    g_phase_frames = 0;
    g_mark_calls = g_calls;
    g_mark_hits  = g_hits;
  }
  return r;
}

static HRESULT STDMETHODCALLTYPE HookCreateDevice(
    IDirect3D9 *s, UINT a, D3DDEVTYPE t, HWND w, DWORD f,
    D3DPRESENT_PARAMETERS *pp, IDirect3DDevice9 **pd)
{
  HRESULT r = g_orig_cd(s, a, t, w, f, pp, pd);
  if (SUCCEEDED(r) && pd && *pd && !g_dev_vt) {
    g_dev_vt = *(void ***)(*pd);
    patch_slot(g_dev_vt, 17, (void *)HookPresent, (void **)&g_orig_present, "Present");
    QueryPerformanceCounter((LARGE_INTEGER *)&g_phase_start);
  }
  return r;
}

static IDirect3D9 * WINAPI HookD3D9Create(UINT sdk)
{
  IDirect3D9 *d = g_orig_create(sdk);
  if (d && !g_d3d9_vt) {
    g_d3d9_vt = *(void ***)d;
    patch_slot(g_d3d9_vt, 16, (void *)HookCreateDevice, (void **)&g_orig_cd, "CreateDevice");
  }
  return d;
}

static BYTE *find_export(BYTE *base, const char *name)
{
  if (!base) return NULL;
  IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
  if (dos->e_magic != IMAGE_DOS_SIGNATURE) return NULL;
  IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
  IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
  if (!dir->VirtualAddress) return NULL;
  IMAGE_EXPORT_DIRECTORY *e = (IMAGE_EXPORT_DIRECTORY *)(base + dir->VirtualAddress);
  DWORD *nm = (DWORD *)(base + e->AddressOfNames);
  WORD  *od = (WORD  *)(base + e->AddressOfNameOrdinals);
  DWORD *fn = (DWORD *)(base + e->AddressOfFunctions);
  for (DWORD i = 0; i < e->NumberOfNames; i++)
    if (strcmp((const char *)(base + nm[i]), name) == 0) return base + fn[od[i]];
  return NULL;
}

static void try_patch_d3d(BYTE *c)
{
  if (!c || g_d3d_hooked) return;
  static const BYTE msvc[5]  = {0x8B,0xFF,0x55,0x8B,0xEC};
  static const BYTE mingw[5] = {0x55,0x89,0xE5,0x56,0x53};
  if (memcmp(c, msvc, 5) && memcmp(c, mingw, 5)) {
    llog("Direct3DCreate9 prologue unrecognised - no frame counting this run");
    return;
  }
  BYTE *tr = (BYTE *)VirtualAlloc(NULL, 32, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
  if (!tr) return;
  memcpy(tr, c, 5); tr[5] = 0xE9;
  *(DWORD *)(tr + 6) = (DWORD)(c + 5) - (DWORD)(tr + 5 + 5);
  g_orig_create = (D3D9CreateFn)tr;
  DWORD old;
  if (!VirtualProtect(c, 5, PAGE_EXECUTE_READWRITE, &old)) return;
  c[0] = 0xE9; *(DWORD *)(c + 1) = (DWORD)HookD3D9Create - (DWORD)(c + 5);
  VirtualProtect(c, 5, old, &old);
  FlushInstructionCache(GetCurrentProcess(), c, 5);
  g_d3d_hooked = true;
  llog("Direct3DCreate9 patched (frame counting armed)");
}

typedef struct { USHORT Length, MaximumLength; PWSTR Buffer; } MY_USTR;
typedef struct { ULONG Flags; MY_USTR *Full, *Base; PVOID DllBase; ULONG Size; } MY_LDR;
typedef NTSTATUS (NTAPI *LdrRegFn)(ULONG, void *, void *, void **);

static bool is_d3d9(MY_USTR *s)
{
  if (!s || !s->Buffer || s->Length != 16) return false;
  static const WCHAR want[] = L"d3d9.dll";
  for (int i = 0; i < 8; i++) {
    WCHAR ch = s->Buffer[i];
    if (ch >= L'A' && ch <= L'Z') ch = (WCHAR)(ch + 32);
    if (ch != want[i]) return false;
  }
  return true;
}

static VOID CALLBACK dll_notify(ULONG reason, MY_LDR *d, PVOID)
{
  if (reason != 1 || !d || !is_d3d9(d->Base)) return;
  try_patch_d3d(find_export((BYTE *)d->DllBase, "Direct3DCreate9"));
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID)

{
  if (reason == DLL_PROCESS_ATTACH) {
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    g_log = fopen(LOG_PATH, "a");
    llog("");
    llog("=== maplookup_cache attached (pid %lu) - PLAY build ===", GetCurrentProcessId());
    if (!host_is_allowed()) return TRUE;
    QueryPerformanceFrequency(&g_qfreq);
    // PLAY BUILD: d3d9 is deliberately NOT hooked. Frame counting only existed
    // to drive the A/B toggle; for actual play the cache simply stays on, and
    // not touching the graphics DLL means DXVK and dgVoodoo are untouched too.
    llog("PLAY build - cache stays on once verified, no A/B toggling.");
    HANDLE t = CreateThread(NULL, 0, boot, NULL, 0, NULL);
    if (t) CloseHandle(t);
  }
  else if (reason == DLL_PROCESS_DETACH) {
    if (g_log) {
      fprintf(g_log, "=== detach: %I64d calls, %I64d cache hits, %I64d verified,"
                     " %I64d mismatches, final mode %ld ===\n",
              g_calls, g_hits, g_verified, g_mismatch, g_mode);
      fflush(g_log); fclose(g_log); g_log = NULL;
    }
  }
  return TRUE;
}
