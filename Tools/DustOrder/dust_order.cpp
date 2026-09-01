// dust_order - pin the mechanism behind "dust makes wheat see-through".
//
// WHY THIS EXISTS
// dustfix.cpp (2026-08-28) proved WHAT the states are (wheat = WZAT, writes depth
// while alpha-blended; dust = -ZAT, writes none) but NOT the mechanism, because its
// ring buffer dumps only the LAST 16384 texture changes - which is always the wheat
// loop at the end of the frame. Verified 2026-09-01: that window contains ZERO dust
// draws. Three fixes were attempted against a mechanism nobody had observed.
//
// The open contradiction: if dust never writes depth AND draws before the wheat,
// it cannot punch a hole in the wheat. So either the ordering is not what we think,
// or a render state set for the dust LEAKS into the wheat draws that follow.
//
// WHAT THIS DOES
// Trigger capture. When a dust-signature draw appears (ZWRITE=0, ALPHABLEND=1,
// ALPHATEST=1) it freezes a window of texture-change events around it - PRE before,
// POST after - and keeps the first WINDOWS of them, so they survive to the log
// instead of scrolling away. Every entry carries a frame number, so frame
// boundaries and any interleaving are visible.
//
// Tracks the three states that would each produce a "hole" if they leaked into the
// wheat draws: ZFUNC, COLORWRITEENABLE, CULLMODE - alongside ALPHAREF/ALPHAFUNC.
//
// PURE OBSERVATION - changes nothing, just logs.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <d3d9.h>

static const char LOG_PATH[] = "K:\\TvTDeepseek\\dust_order\\dust_order.log";

static CRITICAL_SECTION g_lock;
static FILE *g_log;

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

static bool patch_jump(BYTE *target, int len, void *hook, void **orig, const char *what)
{
  BYTE *tramp = (BYTE *)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
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

static bool patch_slot(void **vt, int slot, void *hook, void **orig, const char *what)
{
  DWORD old;
  if (!VirtualProtect(&vt[slot], sizeof(void *), PAGE_EXECUTE_READWRITE, &old)) return false;
  *orig = vt[slot];
  vt[slot] = hook;
  VirtualProtect(&vt[slot], sizeof(void *), old, &old);
  FlushInstructionCache(GetCurrentProcess(), &vt[slot], sizeof(void *));
  llog("hook: %s vtable slot %d -> %08X", what, slot, (DWORD)hook);
  return true;
}

static BYTE *find_export(BYTE *base, const char *name)
{
  if (!base) return NULL;
  IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
  if (dos->e_magic != IMAGE_DOS_SIGNATURE) return NULL;
  IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
  if (nt->Signature != IMAGE_NT_SIGNATURE) return NULL;
  IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
  if (!dir->VirtualAddress || !dir->Size) return NULL;
  IMAGE_EXPORT_DIRECTORY *exp = (IMAGE_EXPORT_DIRECTORY *)(base + dir->VirtualAddress);
  DWORD *names = (DWORD *)(base + exp->AddressOfNames);
  WORD  *ords  = (WORD  *)(base + exp->AddressOfNameOrdinals);
  DWORD *funcs = (DWORD *)(base + exp->AddressOfFunctions);
  for (DWORD i = 0; i < exp->NumberOfNames; i++) {
    const char *n = (const char *)(base + names[i]);
    if (strcmp(n, name) == 0) return base + funcs[ords[i]];
  }
  return NULL;
}

typedef struct _MY_UNICODE_STRING { USHORT Length; USHORT MaximumLength; PWSTR Buffer; } MY_UNICODE_STRING;
typedef struct _MY_LDR_DLL_NOTIFICATION_DATA { ULONG Flags; MY_UNICODE_STRING *FullDllName; MY_UNICODE_STRING *BaseDllName; PVOID DllBase; ULONG SizeOfImage; } MY_LDR_DLL_NOTIFICATION_DATA;

static bool basename_is_d3d9(MY_UNICODE_STRING *s)
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

// --- tracked render state ---
static volatile LONG g_alpha_blend, g_z_write, g_z_enable, g_alpha_test;
static volatile LONG g_srcblend, g_destblend, g_cur_tex;
static volatile LONG g_alpharef, g_alphafunc, g_stencil;
static volatile LONG g_zfunc, g_colorwrite, g_cullmode;   // NEW - the leak candidates
static volatile LONG g_frame;                             // NEW - frame counter

struct Ev {
  DWORD frame, tex, flags, blend, ref;
  DWORD zfunc, colorwrite, cullmode, prims;
};

// rolling pre-trigger history
#define PRE 64
static Ev g_pre[PRE];
static LONG g_pre_head;

// frozen capture windows
#define WINDOWS 8
#define POST 224
#define WINSZ (PRE + POST)
static Ev   g_win[WINDOWS][WINSZ];
static LONG g_win_len[WINDOWS];
static LONG g_win_trigger[WINDOWS];
static LONG g_win_count;
static LONG g_capturing;
static LONG g_cap_idx, g_cap_fill;

static DWORD g_last_tex;
static volatile LONG g_total_draws, g_dust_draws;

struct TexRec { DWORD tex; LONG count; DWORD flags; DWORD srcblend, destblend; LONG prims; };
static TexRec g_tex[768];
static volatile LONG g_tex_count;

typedef HRESULT (STDMETHODCALLTYPE *SetRenderStateFn)(IDirect3DDevice9*, D3DRENDERSTATETYPE, DWORD);
static SetRenderStateFn g_orig_set_render_state;

static HRESULT STDMETHODCALLTYPE HookSetRenderState(IDirect3DDevice9 *self, D3DRENDERSTATETYPE State, DWORD Value)
{
  switch (State) {
    case D3DRS_ALPHABLENDENABLE: InterlockedExchange(&g_alpha_blend, (LONG)Value); break;
    case D3DRS_ZWRITEENABLE:     InterlockedExchange(&g_z_write,     (LONG)Value); break;
    case D3DRS_ZENABLE:          InterlockedExchange(&g_z_enable,    (LONG)Value); break;
    case D3DRS_ALPHATESTENABLE:  InterlockedExchange(&g_alpha_test,  (LONG)Value); break;
    case D3DRS_SRCBLEND:         InterlockedExchange(&g_srcblend,    (LONG)Value); break;
    case D3DRS_DESTBLEND:        InterlockedExchange(&g_destblend,   (LONG)Value); break;
    case D3DRS_ALPHAREF:         InterlockedExchange(&g_alpharef,    (LONG)Value); break;
    case D3DRS_ALPHAFUNC:        InterlockedExchange(&g_alphafunc,   (LONG)Value); break;
    case D3DRS_STENCILENABLE:    InterlockedExchange(&g_stencil,     (LONG)Value); break;
    case D3DRS_ZFUNC:            InterlockedExchange(&g_zfunc,       (LONG)Value); break;
    case D3DRS_COLORWRITEENABLE: InterlockedExchange(&g_colorwrite,  (LONG)Value); break;
    case D3DRS_CULLMODE:         InterlockedExchange(&g_cullmode,    (LONG)Value); break;
    default: break;
  }
  return g_orig_set_render_state(self, State, Value);
}

typedef HRESULT (STDMETHODCALLTYPE *SetTextureFn)(IDirect3DDevice9*, DWORD, IDirect3DBaseTexture9*);
static SetTextureFn g_orig_set_texture;

static HRESULT STDMETHODCALLTYPE HookSetTexture(IDirect3DDevice9 *self, DWORD Sampler, IDirect3DBaseTexture9 *pTexture)
{
  if (Sampler == 0) InterlockedExchange(&g_cur_tex, (LONG)(DWORD)pTexture);
  return g_orig_set_texture(self, Sampler, pTexture);
}

static void fill_ev(Ev *e, DWORD tex, DWORD prims)
{
  e->frame      = (DWORD)g_frame;
  e->tex        = tex;
  e->flags      = (g_z_write?1:0) | (g_z_enable?2:0) | (g_alpha_blend?4:0) | (g_alpha_test?8:0) | (g_stencil?16:0);
  e->blend      = ((DWORD)g_srcblend << 16) | (DWORD)g_destblend;
  e->ref        = ((DWORD)g_alpharef << 8) | (DWORD)g_alphafunc;
  e->zfunc      = (DWORD)g_zfunc;
  e->colorwrite = (DWORD)g_colorwrite;
  e->cullmode   = (DWORD)g_cullmode;
  e->prims      = prims;
}

static void record_draw(DWORD primCount)
{
  InterlockedIncrement(&g_total_draws);
  DWORD tex = (DWORD)g_cur_tex;
  if (!tex) return;

  bool is_dust = (!g_z_write && g_alpha_blend && g_alpha_test);
  if (is_dust) InterlockedIncrement(&g_dust_draws);

  if (tex != g_last_tex) {
    Ev e; fill_ev(&e, tex, primCount);
    g_last_tex = tex;

    EnterCriticalSection(&g_lock);
    if (g_capturing) {
      if (g_cap_fill < WINSZ) g_win[g_cap_idx][g_cap_fill++] = e;
      g_win_len[g_cap_idx] = g_cap_fill;
      if (g_cap_fill >= WINSZ) g_capturing = 0;
    } else if (is_dust && g_win_count < WINDOWS) {
      g_cap_idx = g_win_count++;
      LONG n = 0;
      LONG have = (g_pre_head < PRE) ? g_pre_head : PRE;
      for (LONG i = have; i > 0; i--) {
        LONG k = ((g_pre_head - i) % PRE + PRE) % PRE;
        g_win[g_cap_idx][n++] = g_pre[k];
      }
      g_win_trigger[g_cap_idx] = n;
      g_win[g_cap_idx][n++] = e;
      g_cap_fill = n;
      g_win_len[g_cap_idx] = n;
      g_capturing = 1;
    }
    g_pre[((g_pre_head % PRE) + PRE) % PRE] = e;
    g_pre_head++;
    LeaveCriticalSection(&g_lock);
  }

  LONG n = g_tex_count, idx = -1;
  for (LONG i = 0; i < n; i++) { if (g_tex[i].tex == tex) { idx = i; break; } }
  if (idx < 0 && n < 768) {
    idx = InterlockedIncrement(&g_tex_count) - 1;
    if (idx < 768) {
      g_tex[idx].tex = tex; g_tex[idx].count = 0; g_tex[idx].flags = 0;
      g_tex[idx].srcblend = 0; g_tex[idx].destblend = 0; g_tex[idx].prims = 0;
    }
  }
  if (idx < 0 || idx >= 768) return;
  InterlockedIncrement(&g_tex[idx].count);
  InterlockedAdd(&g_tex[idx].prims, (LONG)primCount);
  DWORD f = 0;
  if (g_z_write)     f |= 1;
  if (g_z_enable)    f |= 2;
  if (g_alpha_blend) f |= 4;
  if (g_alpha_test)  f |= 8;
  InterlockedOr((LONG *)&g_tex[idx].flags, (LONG)f);
  g_tex[idx].srcblend  = (DWORD)g_srcblend;
  g_tex[idx].destblend = (DWORD)g_destblend;
}

typedef HRESULT (STDMETHODCALLTYPE *DrawIndexedPrimitiveFn)(
    IDirect3DDevice9*, D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT);
static DrawIndexedPrimitiveFn g_orig_dip;

static HRESULT STDMETHODCALLTYPE HookDrawIndexedPrimitive(
    IDirect3DDevice9 *self, D3DPRIMITIVETYPE PrimitiveType,
    INT BaseVertexIndex, UINT MinVertexIndex, UINT NumVertices,
    UINT startIndex, UINT primCount)
{
  record_draw(primCount);
  return g_orig_dip(self, PrimitiveType, BaseVertexIndex, MinVertexIndex,
                    NumVertices, startIndex, primCount);
}

typedef HRESULT (STDMETHODCALLTYPE *PresentFn)(IDirect3DDevice9*, const RECT*, const RECT*, HWND, const RGNDATA*);
static PresentFn g_orig_present;

static HRESULT STDMETHODCALLTYPE HookPresent(IDirect3DDevice9 *self, const RECT *a, const RECT *b, HWND c, const RGNDATA *d)
{
  InterlockedIncrement(&g_frame);
  g_last_tex = 0;   // force a fresh texture event at the start of each frame
  return g_orig_present(self, a, b, c, d);
}

typedef HRESULT (STDMETHODCALLTYPE *CreateDeviceRealFn)(
    IDirect3D9*, UINT, D3DDEVTYPE, HWND, DWORD, D3DPRESENT_PARAMETERS*, IDirect3DDevice9**);
static CreateDeviceRealFn g_orig_create_device_real;
static IDirect3DDevice9 *g_device;

static HRESULT STDMETHODCALLTYPE HookCreateDeviceReal(
    IDirect3D9 *self, UINT Adapter, D3DDEVTYPE DeviceType, HWND hFocusWindow,
    DWORD BehaviorFlags, D3DPRESENT_PARAMETERS *pp, IDirect3DDevice9 **ppRet)
{
  HRESULT r = g_orig_create_device_real(self, Adapter, DeviceType, hFocusWindow, BehaviorFlags, pp, ppRet);
  if (SUCCEEDED(r) && !g_device && ppRet && *ppRet) {
    g_device = *ppRet;
    void **vt = *(void ***)g_device;
    patch_slot(vt, 17, (void *)HookPresent,              (void **)&g_orig_present,          "Present");
    patch_slot(vt, 57, (void *)HookSetRenderState,       (void **)&g_orig_set_render_state, "SetRenderState");
    patch_slot(vt, 65, (void *)HookSetTexture,           (void **)&g_orig_set_texture,      "SetTexture");
    patch_slot(vt, 82, (void *)HookDrawIndexedPrimitive, (void **)&g_orig_dip,              "DrawIndexedPrimitive");
  }
  return r;
}

typedef IDirect3D9 *(WINAPI *D3D9CreateFn)(UINT);
static D3D9CreateFn g_orig_d3d9create;
static void **g_d3d9_vt;

static IDirect3D9 *WINAPI HookD3D9Create(UINT SDKVersion)
{
  IDirect3D9 *d = g_orig_d3d9create(SDKVersion);
  llog("Direct3DCreate9(%u) -> %08X", SDKVersion, (DWORD)d);
  if (d && !g_d3d9_vt) {
    g_d3d9_vt = *(void ***)d;
    patch_slot(g_d3d9_vt, 16, (void *)HookCreateDeviceReal, (void **)&g_orig_create_device_real, "IDirect3D9::CreateDevice");
  }
  return d;
}

static volatile LONG g_hook_installed, g_logged_missing;

static void patch_create9(BYTE *create)
{
  if (g_hook_installed) return;
  static const BYTE MSVC_PROLOGUE[5] = { 0x8B, 0xFF, 0x55, 0x8B, 0xEC };
  static const BYTE GCC_PROLOGUE[5]  = { 0x55, 0x89, 0xE5, 0x56, 0x53 };
  const char *n = NULL;
  if (memcmp(create, MSVC_PROLOGUE, 5) == 0) n = "msvc";
  else if (memcmp(create, GCC_PROLOGUE, 5) == 0) n = "gcc";
  if (!n) { llog("Direct3DCreate9 prologue not recognized - NOT patching"); return; }
  llog("Direct3DCreate9 prologue verified (%s)", n);
  if (patch_jump(create, 5, (void *)HookD3D9Create, (void **)&g_orig_d3d9create, "Direct3DCreate9"))
    InterlockedExchange(&g_hook_installed, 1);
}

typedef VOID (CALLBACK *MyDllNotificationFn)(ULONG, MY_LDR_DLL_NOTIFICATION_DATA*, PVOID);
typedef LONG (NTAPI *LdrRegisterDllNotificationFn)(ULONG, MyDllNotificationFn, PVOID, PVOID*);

static VOID CALLBACK dll_notify(ULONG reason, MY_LDR_DLL_NOTIFICATION_DATA *data, PVOID)
{
  if (reason != 1 || g_hook_installed) return;
  if (!data || !data->DllBase) return;
  if (!basename_is_d3d9(data->BaseDllName)) return;
  BYTE *create = find_export((BYTE *)data->DllBase, "Direct3DCreate9");
  if (!create) return;
  llog("notify: d3d9.dll at %08X", (DWORD)data->DllBase);
  patch_create9(create);
}

static void install_hook(void)
{
  if (g_hook_installed) return;
  HMODULE d3d9 = GetModuleHandleA("d3d9.dll");
  if (!d3d9) { if (!InterlockedExchange(&g_logged_missing, 1)) llog("d3d9.dll not loaded yet"); return; }
  BYTE *create = (BYTE *)GetProcAddress(d3d9, "Direct3DCreate9");
  if (!create) { llog("Direct3DCreate9 export not found"); return; }
  patch_create9(create);
}

static DWORD WINAPI boot_thread(LPVOID)
{
  DWORD start = GetTickCount();
  while (!g_hook_installed) {
    install_hook();
    if (g_hook_installed) break;
    if (GetTickCount() - start > 30000) break;
  }
  return 0;
}

static void sort_tex(void)
{
  LONG n = g_tex_count; if (n > 768) n = 768;
  for (LONG i = 1; i < n; i++) {
    TexRec key = g_tex[i]; LONG j = i - 1;
    while (j >= 0 && g_tex[j].count < key.count) { g_tex[j + 1] = g_tex[j]; j--; }
    g_tex[j + 1] = key;
  }
}

static const char *decode_zfunc(DWORD z)
{
  switch (z) {
    case 1: return "NEVER";  case 2: return "LESS";     case 3: return "EQUAL";
    case 4: return "LESSEQ"; case 5: return "GREATER";  case 6: return "NOTEQUAL";
    case 7: return "GREATEREQ"; case 8: return "ALWAYS"; default: return "unset";
  }
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID)
{
  if (reason == DLL_PROCESS_ATTACH) {
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    g_log = fopen(LOG_PATH, "w");
    llog("=== dust_order attached (pid %lu) ===", GetCurrentProcessId());
    llog("trigger = a draw with ZWRITE=0 & ALPHABLEND=1 & ALPHATEST=1 (the dust signature)");
    llog("capturing %d windows of %d events (%d before the trigger, %d after)", WINDOWS, WINSZ, PRE, POST);
    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    if (ntdll) {
      LdrRegisterDllNotificationFn reg = (LdrRegisterDllNotificationFn)
          GetProcAddress(ntdll, "LdrRegisterDllNotification");
      if (reg) { PVOID c = NULL; reg(0, dll_notify, NULL, &c); llog("loader notification armed"); }
    }
    install_hook();
    if (!g_hook_installed) { HANDLE t = CreateThread(NULL, 0, boot_thread, NULL, 0, NULL); if (t) CloseHandle(t); }
  }
  else if (reason == DLL_PROCESS_DETACH) {
    llog("=== totals: %ld draws, %ld dust-signature draws, %ld frames, %ld windows captured ===",
         g_total_draws, g_dust_draws, g_frame, g_win_count);
    LONG nw = g_win_count; if (nw > WINDOWS) nw = WINDOWS;
    for (LONG w = 0; w < nw; w++) {
      llog("%s", "");
      llog("=== window %ld  (trigger at row %ld) ===", w, g_win_trigger[w]);
      llog("   row  frame  texture   WZATS  blend  aref/afn  zfunc      cwrite cull prims");
      for (LONG i = 0; i < g_win_len[w]; i++) {
        Ev *e = &g_win[w][i];
        llog("%s%4ld %6lu  %08X  %d%d%d%d%d  %2d,%-2d  %02X/%d      %-10s %02X    %d   %lu",
             (i == g_win_trigger[w]) ? ">>" : "  ",
             i, e->frame, e->tex,
             (e->flags>>0)&1, (e->flags>>1)&1, (e->flags>>2)&1, (e->flags>>3)&1, (e->flags>>4)&1,
             (e->blend>>16)&0xFFFF, e->blend&0xFFFF,
             (e->ref>>8)&0xFF, e->ref&0xFF,
             decode_zfunc(e->zfunc), e->colorwrite, e->cullmode, e->prims);
      }
    }
    sort_tex();
    LONG n = g_tex_count; if (n > 768) n = 768;
    llog("%s", "");
    llog("=== dump: %ld total draws, %ld distinct textures ===", g_total_draws, n);
    llog("count / prims / flags(ZWRITE|ZENABLE|ALPHABLEND|ALPHATEST) / srcblend,destblend / texture");
    for (LONG i = 0; i < n; i++) {
      TexRec *r = &g_tex[i];
      if (!r->tex || !r->count) continue;
      llog("%8ld  %9ld  %c%c%c%c  %d,%d  0x%08X", r->count, r->prims,
           (r->flags & 1)?'W':'-', (r->flags & 2)?'Z':'-',
           (r->flags & 4)?'A':'-', (r->flags & 8)?'T':'-',
           r->srcblend, r->destblend, r->tex);
    }
    if (g_log) { fflush(g_log); fclose(g_log); g_log = NULL; }
    DeleteCriticalSection(&g_lock);
  }
  return TRUE;
}
