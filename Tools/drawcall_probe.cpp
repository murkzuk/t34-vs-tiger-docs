// ---------------------------------------------------------------------------
// drawcall_probe - what is the GPU side of a TvT frame actually spending on?
//
// THE QUESTION THIS EXISTS TO ANSWER
//
// Turning grass off doubled the framerate (36-40 -> 70-90) but the CPU sampling
// profiler only ever saw ~10% of CPU in the grass code, and the game's main
// thread never exceeds ~58% busy. So the limit is NOT CPU work. It is one of:
//
//   (a) FILL RATE     - the GPU shading the same pixels over and over, because
//                       you are looking through many layers of alpha-blended
//                       grass. Nothing in C++ can fix this. Only less grass.
//   (b) DRAW CALLS    - thousands of tiny batches; per-call driver overhead.
//                       Fixable: batch bigger.
//   (c) LOCK STALLS   - the engine locks a small dynamic vertex buffer over and
//                       over; the driver blocks until the GPU is done with it.
//                       Fixable, and cheaply.
//
// These look identical from outside and have completely different fixes, so
// guessing between them is exactly the mistake that has already cost a day.
//
// HOW IT TELLS THEM APART
//
// It times where the game's own thread actually sits:
//
//   time inside Present()  -> the CPU waiting for the GPU        => (a)
//   time inside Lock()     -> the CPU waiting for a buffer       => (c)
//   many calls, little time in either, but frame time high       => (b)
//
// Plus the raw shape of the frame: draw calls, triangles, buffer locks and
// bytes, state changes.
//
// HOW TO USE IT
//
// Run it twice - grass slider at MAX, then grass slider OFF - and diff the two
// reports. No attribution logic is needed inside the probe that way, and no
// assumption about which buffer is "the grass one" can be wrong.
//
// READ-ONLY. It counts and times. It never changes a render state, never
// alters a draw, and returns every value the game asked for unchanged.
//
// Vtable slots (IDirect3DDevice9, d3d9.h declaration order):
//    17 Present            26 CreateVertexBuffer    57 SetRenderState
//    65 SetTexture         81 DrawPrimitive         82 DrawIndexedPrimitive
//    83 DrawPrimitiveUP    84 DrawIndexedPrimitiveUP
//   100 SetStreamSource
// IDirect3DVertexBuffer9:  11 Lock
// IDirect3D9:              16 CreateDevice
// ---------------------------------------------------------------------------

#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define LOG_PATH   "K:\\TvTDeepseek\\drawcall_probe\\drawcall_probe.log"
#define ALLOW_PATH "K:\\TvTDeepseek\\drawcall_probe\\tvt_los_allow.txt"

static const double REPORT_SECS = 5.0;   // one summary line block per 5 s

// ---------------------------------------------------------------------------
// Logging. The draw path never takes this lock - only report blocks do.
// ---------------------------------------------------------------------------
static FILE *g_log;
static CRITICAL_SECTION g_lock;

static void llog(const char *fmt, ...)
{
  if (!g_log) return;
  EnterCriticalSection(&g_lock);
  va_list ap; va_start(ap, fmt);
  vfprintf(g_log, fmt, ap);
  va_end(ap);
  fputc('\n', g_log);
  fflush(g_log);
  LeaveCriticalSection(&g_lock);
}

static void llog_try(const char *fmt, ...)
{
  if (!g_log) return;
  if (!TryEnterCriticalSection(&g_lock)) return;
  va_list ap; va_start(ap, fmt);
  vfprintf(g_log, fmt, ap);
  va_end(ap);
  fputc('\n', g_log);
  fflush(g_log);
  LeaveCriticalSection(&g_lock);
}

// ---------------------------------------------------------------------------
// Allow list - same rail as the LOS hook. The file sits beside this DLL, never
// inside a game folder, so no install can authorise itself.
// ---------------------------------------------------------------------------
static bool host_is_allowed(void)
{
  char exe[MAX_PATH] = "";
  if (!GetModuleFileNameA(NULL, exe, MAX_PATH)) return false;
  char *slash = NULL;
  for (char *c = exe; *c; c++) if (*c == '\\') slash = c;
  if (!slash) return false;
  *slash = 0;                                  // exe -> its folder

  FILE *f = fopen(ALLOW_PATH, "r");
  if (!f) { llog("allow list missing (%s) - not arming", ALLOW_PATH); return false; }

  char line[MAX_PATH];
  bool ok = false;
  while (fgets(line, sizeof line, f)) {
    char *p = line;
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '#' || *p == '\r' || *p == '\n' || !*p) continue;
    int n = (int)strlen(p);
    while (n > 0 && (p[n-1]=='\r'||p[n-1]=='\n'||p[n-1]==' '||p[n-1]=='\t')) p[--n]=0;
    if (n > 0 && _stricmp(p, exe) == 0) { ok = true; break; }
  }
  fclose(f);
  llog("host %s -> %s", exe, ok ? "ALLOWED" : "not listed, not arming");
  return ok;
}

// ---------------------------------------------------------------------------
// Counters. Plain volatile LONG with interlocked adds - the draw path must stay
// cheap, or the probe changes the thing it is measuring.
// ---------------------------------------------------------------------------
static volatile LONG  g_frames;
static volatile LONG  g_dp, g_dip, g_dpup, g_dipup;
static volatile LONG  g_tris_lo, g_tris_hi;      // 64-bit triangle count, split
static volatile LONG  g_locks, g_locks_discard, g_locks_nooverwrite;
static volatile LONG  g_lockbytes_kb;
static volatile LONG  g_srs, g_settex, g_setstream;
static volatile LONG  g_vbs_created;

// Times in QPC ticks, accumulated as 64-bit under interlocked exchange-add.
static volatile LONGLONG g_t_present;
static volatile LONGLONG g_t_lock;

static LARGE_INTEGER g_freq;
static LONGLONG      g_t_window_start;

static void add64(volatile LONGLONG *dst, LONGLONG v)
{
  // InterlockedExchangeAdd64 is available on x86 via the intrinsic; use the
  // compare-exchange form so this builds on the 2022 x86 toolchain either way.
  LONGLONG old, want;
  do { old = *dst; want = old + v; }
  while (InterlockedCompareExchange64((volatile LONGLONG *)dst, want, old) != old);
}

static void add_tris(LONG n)
{
  LONG old = InterlockedExchangeAdd(&g_tris_lo, n);
  if ((DWORD)old + (DWORD)n < (DWORD)old) InterlockedIncrement(&g_tris_hi);
}

static double ticks_ms(LONGLONG t) { return 1000.0 * (double)t / (double)g_freq.QuadPart; }

// ---------------------------------------------------------------------------
// Vtable slot patch - identical to the fog probe's. A slot is just a pointer,
// so there is no code to copy; the "trampoline" is the saved original.
// ---------------------------------------------------------------------------
static bool patch_slot(void **vt, int slot, void *hook, void **orig,
                       const char *what)
{
  DWORD old;
  if (!VirtualProtect(&vt[slot], sizeof(void *), PAGE_EXECUTE_READWRITE, &old))
    return false;
  if (vt[slot] == hook) {           // already ours - a second device on the
    VirtualProtect(&vt[slot], sizeof(void *), old, &old);  // same vtable
    return true;
  }
  if (vt[slot] != hook) *orig = vt[slot];   // never record our own hook as
  vt[slot] = hook;                          // the original: infinite recursion
  VirtualProtect(&vt[slot], sizeof(void *), old, &old);
  FlushInstructionCache(GetCurrentProcess(), &vt[slot], sizeof(void *));
  llog("hook: %-28s slot %3d -> %08X (orig %08X)",
       what, slot, (DWORD)hook, (DWORD)*orig);
  return true;
}

static bool patch_jump(BYTE *target, int len, void *hook, void **orig,
                       const char *what)
{
  BYTE *tramp = (BYTE *)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE);
  if (!tramp) return false;
  memcpy(tramp, target, len);
  tramp[len] = 0xE9;
  *(DWORD *)(tramp + len + 1) = (DWORD)(target + len) - (DWORD)(tramp + len + 5);
  *orig = tramp;
  DWORD old;
  if (!VirtualProtect(target, len, PAGE_EXECUTE_READWRITE, &old)) return false;
  target[0] = 0xE9;
  *(DWORD *)(target + 1) = (DWORD)hook - (DWORD)(target + 5);
  for (int i = 5; i < len; i++) target[i] = 0x90;
  VirtualProtect(target, len, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, len);
  llog("hook: %s patched at %08X", what, (DWORD)target);
  return true;
}

// ---------------------------------------------------------------------------
// Original function pointers.
// ---------------------------------------------------------------------------
typedef IDirect3D9 * (WINAPI *D3D9CreateFn)(UINT);
typedef HRESULT (STDMETHODCALLTYPE *CreateDeviceFn)(
    IDirect3D9 *, UINT, D3DDEVTYPE, HWND, DWORD, D3DPRESENT_PARAMETERS *,
    IDirect3DDevice9 **);
typedef HRESULT (STDMETHODCALLTYPE *PresentFn)(
    IDirect3DDevice9 *, const RECT *, const RECT *, HWND, const RGNDATA *);
typedef HRESULT (STDMETHODCALLTYPE *DrawPrimFn)(
    IDirect3DDevice9 *, D3DPRIMITIVETYPE, UINT, UINT);
typedef HRESULT (STDMETHODCALLTYPE *DrawIdxPrimFn)(
    IDirect3DDevice9 *, D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT);
typedef HRESULT (STDMETHODCALLTYPE *DrawPrimUPFn)(
    IDirect3DDevice9 *, D3DPRIMITIVETYPE, UINT, const void *, UINT);
typedef HRESULT (STDMETHODCALLTYPE *DrawIdxPrimUPFn)(
    IDirect3DDevice9 *, D3DPRIMITIVETYPE, UINT, UINT, UINT, const void *,
    D3DFORMAT, const void *, UINT);
typedef HRESULT (STDMETHODCALLTYPE *CreateVBFn)(
    IDirect3DDevice9 *, UINT, DWORD, DWORD, D3DPOOL, IDirect3DVertexBuffer9 **,
    HANDLE *);
typedef HRESULT (STDMETHODCALLTYPE *SetRenderStateFn)(
    IDirect3DDevice9 *, D3DRENDERSTATETYPE, DWORD);
typedef HRESULT (STDMETHODCALLTYPE *SetTextureFn)(
    IDirect3DDevice9 *, DWORD, IDirect3DBaseTexture9 *);
typedef HRESULT (STDMETHODCALLTYPE *SetStreamSourceFn)(
    IDirect3DDevice9 *, UINT, IDirect3DVertexBuffer9 *, UINT, UINT);
typedef HRESULT (STDMETHODCALLTYPE *VBLockFn)(
    IDirect3DVertexBuffer9 *, UINT, UINT, void **, DWORD);

static D3D9CreateFn       g_orig_d3d9create;
static CreateDeviceFn     g_orig_create_device;
static PresentFn          g_orig_present;
static DrawPrimFn         g_orig_dp;
static DrawIdxPrimFn      g_orig_dip;
static DrawPrimUPFn       g_orig_dpup;
static DrawIdxPrimUPFn    g_orig_dipup;
static CreateVBFn         g_orig_create_vb;
static SetRenderStateFn   g_orig_srs;
static SetTextureFn       g_orig_settex;
static SetStreamSourceFn  g_orig_setstream;
static VBLockFn           g_orig_vb_lock;

static void **g_d3d9_vt, **g_device_vt, **g_vb_vt;
static bool   g_armed, g_hook_installed;
static int    g_ndevices;

// ---------------------------------------------------------------------------
// Triangle arithmetic: PrimitiveCount is already the primitive count, but a
// triangle strip/fan of N primitives is N triangles, same as a list. So the
// primitive count IS the triangle count for the three triangle types, and we
// simply do not count line/point draws as triangles.
// ---------------------------------------------------------------------------
static LONG tris_of(D3DPRIMITIVETYPE t, UINT primCount)
{
  switch (t) {
    case D3DPT_TRIANGLELIST:
    case D3DPT_TRIANGLESTRIP:
    case D3DPT_TRIANGLEFAN:
      return (LONG)primCount;
    default:
      return 0;                     // points and lines - not fill
  }
}

// ---------------------------------------------------------------------------
// The report. Called from Present once the window has elapsed.
// ---------------------------------------------------------------------------
static void report(double wall_ms)
{
  LONG frames = InterlockedExchange(&g_frames, 0);
  LONG dp     = InterlockedExchange(&g_dp, 0);
  LONG dip    = InterlockedExchange(&g_dip, 0);
  LONG dpup   = InterlockedExchange(&g_dpup, 0);
  LONG dipup  = InterlockedExchange(&g_dipup, 0);
  LONG tlo    = InterlockedExchange(&g_tris_lo, 0);
  LONG thi    = InterlockedExchange(&g_tris_hi, 0);
  LONG locks  = InterlockedExchange(&g_locks, 0);
  LONG ldis   = InterlockedExchange(&g_locks_discard, 0);
  LONG lnov   = InterlockedExchange(&g_locks_nooverwrite, 0);
  LONG lkb    = InterlockedExchange(&g_lockbytes_kb, 0);
  LONG srs    = InterlockedExchange(&g_srs, 0);
  LONG stex   = InterlockedExchange(&g_settex, 0);
  LONG sstr   = InterlockedExchange(&g_setstream, 0);

  LONGLONG tp = g_t_present; add64(&g_t_present, -tp);
  LONGLONG tl = g_t_lock;    add64(&g_t_lock,    -tl);

  if (frames <= 0) return;

  double present_ms = ticks_ms(tp);
  double lock_ms    = ticks_ms(tl);
  double f          = (double)frames;
  ULONGLONG tris    = ((ULONGLONG)(DWORD)thi << 32) | (DWORD)tlo;
  LONG draws        = dp + dip + dpup + dipup;

  llog("");
  llog("======== %.1f s, %ld frames, %.1f fps ========", wall_ms/1000.0, frames, f/(wall_ms/1000.0));
  llog("  PER FRAME");
  llog("    draw calls        %8.0f   (DP %.0f  DIP %.0f  DP_UP %.0f  DIP_UP %.0f)",
       draws/f, dp/f, dip/f, dpup/f, dipup/f);
  llog("    triangles         %8.0f", (double)tris/f);
  llog("    vertex-buf locks  %8.0f   (DISCARD %.0f  NOOVERWRITE %.0f)",
       locks/f, ldis/f, lnov/f);
  llog("    locked KB         %8.0f", lkb/f);
  llog("    SetRenderState    %8.0f", srs/f);
  llog("    SetTexture        %8.0f", stex/f);
  llog("    SetStreamSource   %8.0f", sstr/f);
  llog("  WHERE THE GAME THREAD SITS  (frame is %.2f ms)", wall_ms/f);
  llog("    inside Present()  %8.2f ms/frame   %5.1f%%   <- waiting for the GPU",
       present_ms/f, 100.0*present_ms/wall_ms);
  llog("    inside Lock()     %8.2f ms/frame   %5.1f%%   <- waiting for a buffer",
       lock_ms/f, 100.0*lock_ms/wall_ms);
  llog("    everything else   %8.2f ms/frame   %5.1f%%",
       (wall_ms-present_ms-lock_ms)/f,
       100.0*(wall_ms-present_ms-lock_ms)/wall_ms);
  llog("  VERDICT");
  bool any = false;
  if (100.0*present_ms/wall_ms > 45.0) {
    llog("    GPU-BOUND. Most of the frame is spent waiting on the GPU, so this");
    llog("    is fill rate / shading cost. C++ cannot fix it - only less on screen.");
    any = true;
  }
  if (100.0*lock_ms/wall_ms > 15.0) {
    llog("    LOCK STALLS. Significant time blocked in Lock() - the dynamic buffer");
    llog("    pattern is the problem, and that IS fixable in a hook.");
    any = true;
  }
  if (draws/f > 3000.0) {
    llog("    DRAW-CALL HEAVY. %.0f calls/frame is a lot for a 2008 D3D9 engine;", draws/f);
    llog("    per-call driver overhead is worth attacking by batching.");
    any = true;
  }
  if (!any)
    llog("    No single cause dominates - compare this block against the other run.");
  llog("================================================");
}

// ---------------------------------------------------------------------------
// Hooks. Every one of these forwards unchanged - the probe alters nothing.
// ---------------------------------------------------------------------------
static HRESULT STDMETHODCALLTYPE HookPresent(
    IDirect3DDevice9 *self, const RECT *a, const RECT *b, HWND c,
    const RGNDATA *d)
{
  LARGE_INTEGER t0, t1;
  QueryPerformanceCounter(&t0);
  HRESULT r = g_orig_present(self, a, b, c, d);
  QueryPerformanceCounter(&t1);

  add64(&g_t_present, t1.QuadPart - t0.QuadPart);
  InterlockedIncrement(&g_frames);

  // jm 2026-08-26: CROSS-CHECK THE CLOCK.  F9, ReShade and the DXVK HUD all
  // report ~50 fps in C2M1 where this probe reports ~117 - a 2.3x gap. Either
  // the game presents 2.3x per displayed frame, or this QPC arithmetic is
  // wrong. GetTickCount is an independent clock, so if the two disagree the
  // fault is here; if they agree, the frame COUNT is the inflated part.
  double wall_ms = ticks_ms(t1.QuadPart - g_t_window_start);
  if (wall_ms >= REPORT_SECS * 1000.0) {
    static DWORD tick_prev;
    DWORD tick_now = GetTickCount();
    double tick_ms = tick_prev ? (double)(tick_now - tick_prev) : wall_ms;
    tick_prev = tick_now;
    llog("CLOCK CHECK: QPC says %.2f s, GetTickCount says %.2f s%s",
         wall_ms / 1000.0, tick_ms / 1000.0,
         (tick_ms > wall_ms * 1.25 || tick_ms < wall_ms * 0.8)
           ? "   <<< THE CLOCKS DISAGREE - the QPC maths is wrong"
           : "   (clocks agree - so the FRAME COUNT is the inflated part)");
    g_t_window_start = t1.QuadPart;
    report(wall_ms);
  }
  return r;
}

static HRESULT STDMETHODCALLTYPE HookDP(
    IDirect3DDevice9 *self, D3DPRIMITIVETYPE t, UINT start, UINT primCount)
{
  InterlockedIncrement(&g_dp);
  add_tris(tris_of(t, primCount));
  return g_orig_dp(self, t, start, primCount);
}

static HRESULT STDMETHODCALLTYPE HookDIP(
    IDirect3DDevice9 *self, D3DPRIMITIVETYPE t, INT base, UINT minIdx,
    UINT numVerts, UINT startIdx, UINT primCount)
{
  InterlockedIncrement(&g_dip);
  add_tris(tris_of(t, primCount));
  return g_orig_dip(self, t, base, minIdx, numVerts, startIdx, primCount);
}

static HRESULT STDMETHODCALLTYPE HookDPUP(
    IDirect3DDevice9 *self, D3DPRIMITIVETYPE t, UINT primCount,
    const void *data, UINT stride)
{
  InterlockedIncrement(&g_dpup);
  add_tris(tris_of(t, primCount));
  return g_orig_dpup(self, t, primCount, data, stride);
}

static HRESULT STDMETHODCALLTYPE HookDIPUP(
    IDirect3DDevice9 *self, D3DPRIMITIVETYPE t, UINT minIdx, UINT numVerts,
    UINT primCount, const void *idx, D3DFORMAT fmt, const void *data,
    UINT stride)
{
  InterlockedIncrement(&g_dipup);
  add_tris(tris_of(t, primCount));
  return g_orig_dipup(self, t, minIdx, numVerts, primCount, idx, fmt, data, stride);
}

static HRESULT STDMETHODCALLTYPE HookVBLock(
    IDirect3DVertexBuffer9 *self, UINT offset, UINT size, void **ppb,
    DWORD flags)
{
  LARGE_INTEGER t0, t1;
  QueryPerformanceCounter(&t0);
  HRESULT r = g_orig_vb_lock(self, offset, size, ppb, flags);
  QueryPerformanceCounter(&t1);

  add64(&g_t_lock, t1.QuadPart - t0.QuadPart);
  InterlockedIncrement(&g_locks);
  if (flags & D3DLOCK_DISCARD)     InterlockedIncrement(&g_locks_discard);
  if (flags & D3DLOCK_NOOVERWRITE) InterlockedIncrement(&g_locks_nooverwrite);
  InterlockedExchangeAdd(&g_lockbytes_kb, (LONG)(size / 1024));
  return r;
}

static HRESULT STDMETHODCALLTYPE HookSRS(
    IDirect3DDevice9 *self, D3DRENDERSTATETYPE s, DWORD v)
{
  InterlockedIncrement(&g_srs);
  return g_orig_srs(self, s, v);
}

static HRESULT STDMETHODCALLTYPE HookSetTex(
    IDirect3DDevice9 *self, DWORD stage, IDirect3DBaseTexture9 *tex)
{
  InterlockedIncrement(&g_settex);
  return g_orig_settex(self, stage, tex);
}

static HRESULT STDMETHODCALLTYPE HookSetStream(
    IDirect3DDevice9 *self, UINT n, IDirect3DVertexBuffer9 *vb, UINT off,
    UINT stride)
{
  InterlockedIncrement(&g_setstream);
  return g_orig_setstream(self, n, vb, off, stride);
}

// CreateVertexBuffer is hooked for one reason only: every vertex buffer shares
// one vtable, so the first one created gives us the Lock slot to patch.
static HRESULT STDMETHODCALLTYPE HookCreateVB(
    IDirect3DDevice9 *self, UINT len, DWORD usage, DWORD fvf, D3DPOOL pool,
    IDirect3DVertexBuffer9 **ppvb, HANDLE *shared)
{
  HRESULT r = g_orig_create_vb(self, len, usage, fvf, pool, ppvb, shared);
  InterlockedIncrement(&g_vbs_created);
  if (SUCCEEDED(r) && ppvb && *ppvb && !g_vb_vt) {
    g_vb_vt = *(void ***)(*ppvb);
    llog("first vertex buffer: %u bytes, usage %08X, pool %d - patching Lock",
         len, usage, (int)pool);
    patch_slot(g_vb_vt, 11, (void *)HookVBLock,
               (void **)&g_orig_vb_lock, "IDirect3DVertexBuffer9::Lock");
  }
  return r;
}

static void reapply_device_hooks(bool quiet)
{
  void **vt = g_device_vt;
  if (!vt) return;
  patch_slot(vt,  17, (void *)HookPresent,   (void **)&g_orig_present,    "Present");
  patch_slot(vt,  26, (void *)HookCreateVB,  (void **)&g_orig_create_vb,  "CreateVertexBuffer");
  patch_slot(vt,  57, (void *)HookSRS,       (void **)&g_orig_srs,        "SetRenderState");
  patch_slot(vt,  65, (void *)HookSetTex,    (void **)&g_orig_settex,     "SetTexture");
  patch_slot(vt,  81, (void *)HookDP,        (void **)&g_orig_dp,         "DrawPrimitive");
  patch_slot(vt,  82, (void *)HookDIP,       (void **)&g_orig_dip,        "DrawIndexedPrimitive");
  patch_slot(vt,  83, (void *)HookDPUP,      (void **)&g_orig_dpup,       "DrawPrimitiveUP");
  patch_slot(vt,  84, (void *)HookDIPUP,     (void **)&g_orig_dipup,      "DrawIndexedPrimitiveUP");
  patch_slot(vt, 100, (void *)HookSetStream, (void **)&g_orig_setstream,  "SetStreamSource");
}

static HRESULT STDMETHODCALLTYPE HookCreateDevice(
    IDirect3D9 *self, UINT adapter, D3DDEVTYPE type, HWND hwnd, DWORD flags,
    D3DPRESENT_PARAMETERS *pp, IDirect3DDevice9 **ppdev)
{
  HRESULT r = g_orig_create_device(self, adapter, type, hwnd, flags, pp, ppdev);
  // jm 2026-08-26: was "!g_device_vt" - hook the FIRST device only. Under DXVK
  // every device shares one vtable so that was invisible. On NATIVE D3D9 the
  // game releases its device and creates another (see execution.log,
  // "Device release counter 1"), and the replacement can sit on a DIFFERENT
  // vtable - pure vs non-pure, hardware vs software vertex processing. The
  // hooks then went dead and the probe logged 16 vertex buffers and nothing
  // else, while the game happily played a full mission. Patch every new one.
  // jm 2026-08-26 SECOND attempt. First fix re-hooked only when the vtable
  // ADDRESS changed. That still missed the real case: the game releases its
  // device and creates another, the freed vtable block is reused at the SAME
  // address, and native D3D9 re-initialises those slots with the original
  // function pointers - silently wiping our hooks. Address unchanged, hooks
  // gone, no re-patch. That is why 16 vertex buffers were counted and then
  // nothing, while the game went on to play a full mission.
  //
  // So: re-patch on EVERY CreateDevice. patch_slot skips any slot already
  // holding our hook, so this is safe to repeat and cannot recurse.
  void **new_vt = (SUCCEEDED(r) && ppdev && *ppdev) ? *(void ***)(*ppdev) : NULL;
  if (new_vt) {
    g_ndevices++;
    if (g_device_vt) llog("device #%d created - re-applying hooks (vtable %08X, first was %08X)",
                          g_ndevices, (DWORD)new_vt, (DWORD)g_device_vt);
    g_device_vt = new_vt;
    llog("device created %08X  (backbuffer %ux%u, vsync interval %u)",
         (DWORD)*ppdev, pp ? pp->BackBufferWidth : 0,
         pp ? pp->BackBufferHeight : 0, pp ? pp->PresentationInterval : 0);
    patch_slot(g_device_vt,  17, (void *)HookPresent,   (void **)&g_orig_present,    "Present");
    patch_slot(g_device_vt,  26, (void *)HookCreateVB,  (void **)&g_orig_create_vb,  "CreateVertexBuffer");
    patch_slot(g_device_vt,  57, (void *)HookSRS,       (void **)&g_orig_srs,        "SetRenderState");
    patch_slot(g_device_vt,  65, (void *)HookSetTex,    (void **)&g_orig_settex,     "SetTexture");
    patch_slot(g_device_vt,  81, (void *)HookDP,        (void **)&g_orig_dp,         "DrawPrimitive");
    patch_slot(g_device_vt,  82, (void *)HookDIP,       (void **)&g_orig_dip,        "DrawIndexedPrimitive");
    patch_slot(g_device_vt,  83, (void *)HookDPUP,      (void **)&g_orig_dpup,       "DrawPrimitiveUP");
    patch_slot(g_device_vt,  84, (void *)HookDIPUP,     (void **)&g_orig_dipup,      "DrawIndexedPrimitiveUP");
    patch_slot(g_device_vt, 100, (void *)HookSetStream, (void **)&g_orig_setstream,  "SetStreamSource");

    QueryPerformanceCounter((LARGE_INTEGER *)&g_t_window_start);
    llog("counting live - a report every %.0f s", REPORT_SECS);
  }
  return r;
}

static IDirect3D9 * WINAPI HookD3D9Create(UINT sdk)
{
  IDirect3D9 *d = g_orig_d3d9create(sdk);
  llog("Direct3DCreate9(%u) -> %08X", sdk, (DWORD)d);
  if (d && !g_d3d9_vt) {
    g_d3d9_vt = *(void ***)d;
    patch_slot(g_d3d9_vt, 16, (void *)HookCreateDevice,
               (void **)&g_orig_create_device, "IDirect3D9::CreateDevice");
  }
  return d;
}

// ---------------------------------------------------------------------------
// Finding and patching the Direct3DCreate9 export without the loader lock.
// Same reasoning and the same two accepted prologues as the fog probe.
// ---------------------------------------------------------------------------
static BYTE *find_export(BYTE *base, const char *name)
{
  if (!base) return NULL;
  IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
  if (dos->e_magic != IMAGE_DOS_SIGNATURE) return NULL;
  IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
  if (nt->Signature != IMAGE_NT_SIGNATURE) return NULL;
  IMAGE_DATA_DIRECTORY *dir =
      &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
  if (!dir->VirtualAddress || !dir->Size) return NULL;
  IMAGE_EXPORT_DIRECTORY *exp = (IMAGE_EXPORT_DIRECTORY *)(base + dir->VirtualAddress);
  DWORD *names = (DWORD *)(base + exp->AddressOfNames);
  WORD  *ords  = (WORD  *)(base + exp->AddressOfNameOrdinals);
  DWORD *funcs = (DWORD *)(base + exp->AddressOfFunctions);
  for (DWORD i = 0; i < exp->NumberOfNames; i++)
    if (strcmp((const char *)(base + names[i]), name) == 0)
      return base + funcs[ords[i]];
  return NULL;
}

static void try_patch_create(BYTE *create)
{
  if (!create || g_hook_installed) return;
  // Two accepted prologues, both exactly 5 bytes of whole instructions.
  static const BYTE msvc[5] = {0x8B,0xFF,0x55,0x8B,0xEC};
  static const BYTE mingw[5]= {0x55,0x89,0xE5,0x56,0x53};
  if (memcmp(create, msvc, 5) && memcmp(create, mingw, 5)) {
    llog("Direct3DCreate9 prologue unrecognised (%02X %02X %02X %02X %02X)"
         " - refusing to patch", create[0],create[1],create[2],create[3],create[4]);
    return;
  }
  if (patch_jump(create, 5, (void *)HookD3D9Create,
                 (void **)&g_orig_d3d9create, "Direct3DCreate9"))
    g_hook_installed = true;
}

typedef struct { USHORT Length, MaximumLength; PWSTR Buffer; } MY_USTR;
typedef struct {
  ULONG Flags; MY_USTR *FullDllName, *BaseDllName; PVOID DllBase; ULONG SizeOfImage;
} MY_LDR_DATA;
typedef NTSTATUS (NTAPI *LdrRegFn)(ULONG, void *, void *, void **);

static bool basename_is_d3d9(MY_USTR *s)
{
  if (!s || !s->Buffer || s->Length != 16) return false;
  static const WCHAR want[] = L"d3d9.dll";
  for (int i = 0; i < 8; i++) {
    WCHAR c = s->Buffer[i];
    if (c >= L'A' && c <= L'Z') c = (WCHAR)(c + 32);
    if (c != want[i]) return false;
  }
  return true;
}

static VOID CALLBACK dll_notify(ULONG reason, MY_LDR_DATA *d, PVOID)
{
  if (reason != 1 || !d || !basename_is_d3d9(d->BaseDllName)) return;
  try_patch_create(find_export((BYTE *)d->DllBase, "Direct3DCreate9"));
}

// jm 2026-08-26: WATCHDOG.  Two separate fixes for "the hooks stop firing on
// native D3D9" both missed, because each assumed a mechanism.  This assumes
// none: once a second, check whether our Present hook is still in the vtable,
// and put every hook back if it is not.  Whatever wipes them - device
// recreation, a vtable rebuild, a driver thunk swap - this recovers from it.
//
// Costs one comparison per second and cannot perturb the measurement.
static void reapply_device_hooks(bool quiet);

static DWORD WINAPI boot_thread(LPVOID)
{
  for (int i = 0; i < 400 && !g_hook_installed; i++) {
    HMODULE m = GetModuleHandleA("d3d9.dll");
    if (m) try_patch_create(find_export((BYTE *)m, "Direct3DCreate9"));
    Sleep(25);
  }
  int restores = 0;
  for (;;) {
    Sleep(1000);
    if (!g_device_vt) continue;
    if (g_device_vt[17] != (void *)HookPresent) {
      restores++;
      llog("WATCHDOG: hooks were wiped (restore #%d) - re-applying", restores);
      reapply_device_hooks(false);
    }
  }
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID)
{
  if (reason == DLL_PROCESS_ATTACH) {
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    QueryPerformanceFrequency(&g_freq);
    g_log = fopen(LOG_PATH, "a");
    llog("");
    llog("=== drawcall_probe attached (pid %lu) ===", GetCurrentProcessId());
    if (!host_is_allowed()) return TRUE;      // attached but inert
    g_armed = true;

    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    if (ntdll) {
      LdrRegFn reg = (LdrRegFn)GetProcAddress(ntdll, "LdrRegisterDllNotification");
      if (reg) { void *ck = NULL; reg(0, (void *)dll_notify, NULL, &ck);
                 llog("loader notification armed for d3d9.dll"); }
    }
    HMODULE m = GetModuleHandleA("d3d9.dll");
    if (m) try_patch_create(find_export((BYTE *)m, "Direct3DCreate9"));
    if (!g_hook_installed) {
      HANDLE t = CreateThread(NULL, 0, boot_thread, NULL, 0, NULL);
      if (t) CloseHandle(t);
    }
  }
  else if (reason == DLL_PROCESS_DETACH) {
    llog_try("=== drawcall_probe detaching (%ld vertex buffers created) ===",
             g_vbs_created);
    if (g_log) { fflush(g_log); fclose(g_log); g_log = NULL; }
  }
  return TRUE;
}
