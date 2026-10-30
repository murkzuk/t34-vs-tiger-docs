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
#include <tlhelp32.h>
#include <d3d9.h>

// Per-PID log. A fixed path meant a throwaway regression run silently overwrote a
// real gameplay capture (2026-09-01 - 175 KB of the user's run, lost). Never again.
static char g_log_path[MAX_PATH];

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
// Gameplay gate. The first run spent all 8 windows on MENU draws (frames 2-466)
// while the user played 34,576 frames. A window is only armed inside a frame that
// actually drew wheat, and windows now roll so the LAST qualifying ones survive.
static volatile LONG g_frame_wheat, g_prev_frame_wheat, g_trigger_total;
static LONG g_win_wheat[WINDOWS];
#define WHEAT_MIN 200

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

  bool is_dust  = (!g_z_write && g_alpha_blend && g_alpha_test);
  bool is_wheat = ( g_z_write &&  g_alpha_blend && g_alpha_test && primCount <= 8);
  if (is_dust)  InterlockedIncrement(&g_dust_draws);
  if (is_wheat) InterlockedIncrement(&g_frame_wheat);

  if (tex != g_last_tex) {
    Ev e; fill_ev(&e, tex, primCount);
    g_last_tex = tex;

    EnterCriticalSection(&g_lock);
    if (g_capturing) {
      if (g_cap_fill < WINSZ) g_win[g_cap_idx][g_cap_fill++] = e;
      g_win_len[g_cap_idx] = g_cap_fill;
      if (g_cap_fill >= WINSZ) g_capturing = 0;
    } else if (is_dust && g_prev_frame_wheat >= WHEAT_MIN) {
      g_cap_idx = (LONG)(g_trigger_total % WINDOWS);   // roll - keep the LAST 8
      g_trigger_total++;
      if (g_win_count < WINDOWS) g_win_count++;
      g_win_wheat[g_cap_idx] = g_prev_frame_wheat;
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
  InterlockedExchange(&g_prev_frame_wheat, g_frame_wheat);
  InterlockedExchange(&g_frame_wheat, 0);
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

static volatile LONG g_hook_installed, g_logged_missing, g_logged_prologue;

static void patch_create9(BYTE *create)
{
  if (g_hook_installed) return;
  static const BYTE MSVC_PROLOGUE[5] = { 0x8B, 0xFF, 0x55, 0x8B, 0xEC };
  static const BYTE GCC_PROLOGUE[5]  = { 0x55, 0x89, 0xE5, 0x56, 0x53 };
  const char *n = NULL;
  if (memcmp(create, MSVC_PROLOGUE, 5) == 0) n = "msvc";
  else if (memcmp(create, GCC_PROLOGUE, 5) == 0) n = "gcc";
  if (!n) {
    // Log ONCE, with the actual bytes. The 2026-09-01 run flooded a 328 MB log
    // because this logged on every retry of a spinning boot thread.
    if (!InterlockedExchange(&g_logged_prologue, 1)) {
      llog("Direct3DCreate9 prologue NOT recognized at %08X - falling back to the GetProcAddress hook", (DWORD)create);
      llog("  runtime bytes: %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X",
           create[0],create[1],create[2],create[3],create[4],create[5],create[6],create[7],
           create[8],create[9],create[10],create[11],create[12],create[13],create[14],create[15]);
    }
    return;
  }
  llog("Direct3DCreate9 prologue verified (%s)", n);
  if (patch_jump(create, 5, (void *)HookD3D9Create, (void **)&g_orig_d3d9create, "Direct3DCreate9"))
    InterlockedExchange(&g_hook_installed, 1);
}

// --- prologue-agnostic path: intercept GetProcAddress ------------------------
// The game imports NO d3d9 statically (checked 2026-09-01: not the exe, not
// Engine/Objects/Controls/Behavior/Service/J5Script/STTree). It resolves
// Direct3DCreate9 dynamically, and the shipped d3d9.dll is a packed wrapper whose
// on-disk bytes do not match what runs. So patch the IAT slot for GetProcAddress
// in every module instead - no byte patterns anywhere.

typedef FARPROC (WINAPI *GetProcAddressFn)(HMODULE, LPCSTR);
static GetProcAddressFn g_real_gpa = GetProcAddress;
static volatile LONG g_gpa_hits;

static FARPROC WINAPI HookGetProcAddress(HMODULE mod, LPCSTR name)
{
  FARPROC real = g_real_gpa(mod, name);
  // ordinals have a zero high word - only inspect real string names
  if (real && name && ((DWORD_PTR)name >> 16) != 0 && strcmp(name, "Direct3DCreate9") == 0) {
    if (!g_orig_d3d9create) {
      g_orig_d3d9create = (D3D9CreateFn)real;
      InterlockedExchange(&g_hook_installed, 1);
      llog("GetProcAddress(\"Direct3DCreate9\") -> %08X  [intercepted, hook #%ld]",
           (DWORD)real, InterlockedIncrement(&g_gpa_hits));
    }
    return (FARPROC)HookD3D9Create;
  }
  return real;
}

// patch the kernel32!GetProcAddress slot in one module's import table.
//
// Every RVA is bounds-checked against SizeOfImage and the whole walk sits inside
// SEH: a module can be notified while still mid-initialisation, and a PACKED
// module (the shipped d3d9.dll is one) may have no valid import table at that
// moment. Without this the probe access-violated - caught 2026-09-01 in
// test_gpa.exe rather than in the user's game.
static HMODULE g_self;

// Every IAT slot we redirect, so DETACH can restore it. Without this the slots keep
// pointing into this DLL after it unloads and the process access-violates during
// shutdown - caught 2026-09-01 in test_gpa.exe, and it would have crashed the game
// on exit, exactly when the log is written.
#define MAXSLOTS 256
static DWORD_PTR *g_slot_addr[MAXSLOTS];
static GetProcAddressFn g_slot_prev[MAXSLOTS];
static LONG g_slot_count;

static void remember_slot(DWORD_PTR *addr, GetProcAddressFn prev)
{
  if (g_slot_count >= MAXSLOTS) return;
  g_slot_addr[g_slot_count] = addr;
  g_slot_prev[g_slot_count] = prev;
  g_slot_count++;
}

static void restore_slots(void)
{
  int n = 0;
  for (LONG i = 0; i < g_slot_count; i++) {
    if (!g_slot_addr[i] || !g_slot_prev[i]) continue;
    __try {
      DWORD old;
      if (VirtualProtect(g_slot_addr[i], sizeof(void *), PAGE_READWRITE, &old)) {
        if (*g_slot_addr[i] == (DWORD_PTR)HookGetProcAddress) {
          *g_slot_addr[i] = (DWORD_PTR)g_slot_prev[i];
          n++;
        }
        VirtualProtect(g_slot_addr[i], sizeof(void *), old, &old);
      }
    } __except (EXCEPTION_EXECUTE_HANDLER) { }
  }
  llog("IAT: restored %d of %ld GetProcAddress slot(s)", n, g_slot_count);
}

static int patch_iat_gpa(BYTE *base)
{
  if (!base || (HMODULE)base == g_self) return 0;   // never patch our own imports
  int patched = 0;
  __try {
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return 0;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return 0;
    DWORD imgsz = nt->OptionalHeader.SizeOfImage;
    IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    DWORD irva = dir->VirtualAddress;
    if (!irva || irva >= imgsz) return 0;

    IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + irva);
    for (; imp->Name; imp++) {
      if ((BYTE *)imp + sizeof(*imp) > base + imgsz) break;
      DWORD orva = imp->OriginalFirstThunk, frva = imp->FirstThunk;
      if (!frva || frva >= imgsz) continue;
      if (orva >= imgsz) orva = 0;
      IMAGE_THUNK_DATA *oft = (IMAGE_THUNK_DATA *)(base + (orva ? orva : frva));
      IMAGE_THUNK_DATA *ft  = (IMAGE_THUNK_DATA *)(base + frva);
      for (; oft->u1.AddressOfData; oft++, ft++) {
        if ((BYTE *)oft + sizeof(*oft) > base + imgsz) break;
        if ((BYTE *)ft  + sizeof(*ft)  > base + imgsz) break;
        if (oft->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
        DWORD nrva = (DWORD)oft->u1.AddressOfData;
        if (nrva + sizeof(IMAGE_IMPORT_BY_NAME) >= imgsz) continue;   // bound import / garbage
        IMAGE_IMPORT_BY_NAME *ibn = (IMAGE_IMPORT_BY_NAME *)(base + nrva);
        if (strcmp((const char *)ibn->Name, "GetProcAddress") != 0) continue;
        if ((void *)ft->u1.Function == (void *)HookGetProcAddress) continue;
        DWORD old;
        if (VirtualProtect(&ft->u1.Function, sizeof(void *), PAGE_READWRITE, &old)) {
          GetProcAddressFn was = (GetProcAddressFn)ft->u1.Function;
          if (was && was != (GetProcAddressFn)HookGetProcAddress) g_real_gpa = was;
          ft->u1.Function = (DWORD_PTR)HookGetProcAddress;
          VirtualProtect(&ft->u1.Function, sizeof(void *), old, &old);
          remember_slot(&ft->u1.Function, was);   // so DETACH can put it back
          patched++;
        }
      }
    }
  }
  __except (EXCEPTION_EXECUTE_HANDLER) {
    return patched;   // malformed or mid-load module - skip it, do not take the game down
  }
  return patched;
}

// walk every currently-loaded module (toolhelp snapshot - documented, no PEB structs)
static void patch_iat_all(const char *when)
{
  int total = 0, mods = 0;
  HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
  if (snap == INVALID_HANDLE_VALUE) { llog("IAT: snapshot failed (%s)", when); return; }
  MODULEENTRY32 me; me.dwSize = sizeof(me);
  if (Module32First(snap, &me)) {
    do {
      mods++;
      total += patch_iat_gpa((BYTE *)me.modBaseAddr);
    } while (Module32Next(snap, &me));
  }
  CloseHandle(snap);
  llog("IAT: patched %d GetProcAddress slot(s) across %d modules (%s)", total, mods, when);
}

typedef VOID (CALLBACK *MyDllNotificationFn)(ULONG, MY_LDR_DLL_NOTIFICATION_DATA*, PVOID);
typedef LONG (NTAPI *LdrRegisterDllNotificationFn)(ULONG, MyDllNotificationFn, PVOID, PVOID*);
typedef LONG (NTAPI *LdrUnregisterDllNotificationFn)(PVOID);
static PVOID g_ldr_cookie;   // MUST be unregistered on DETACH - see below

static VOID CALLBACK dll_notify(ULONG reason, MY_LDR_DLL_NOTIFICATION_DATA *data, PVOID)
{
  if (reason != 1) return;
  if (!data || !data->DllBase) return;
  patch_iat_gpa((BYTE *)data->DllBase);   // every new module gets the GetProcAddress hook
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
  // Sleep between retries. Without it this spun and logged millions of times -
  // the 2026-09-01 run produced a 328 MB log and captured nothing.
  DWORD start = GetTickCount();
  int sweeps = 0;
  while (!g_hook_installed) {
    install_hook();
    if (g_hook_installed) break;
    if ((sweeps++ % 10) == 0) patch_iat_all("boot retry");
    if (GetTickCount() - start > 60000) { llog("boot thread giving up after 60s"); break; }
    Sleep(50);
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
    g_self = h;
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    _snprintf(g_log_path, sizeof(g_log_path) - 1,
              "K:\\TvTDeepseek\\dust_order\\dust_order_pid%lu.log", GetCurrentProcessId());
    g_log_path[sizeof(g_log_path) - 1] = 0;
    g_log = fopen(g_log_path, "w");
    llog("=== dust_order attached (pid %lu) ===", GetCurrentProcessId());
    llog("trigger = a draw with ZWRITE=0 & ALPHABLEND=1 & ALPHATEST=1 (the dust signature)");
    llog("capturing %d rolling windows of %d events (%d before, %d after), armed only in frames with >=%d wheat draws", WINDOWS, WINSZ, PRE, POST, WHEAT_MIN);
    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    if (ntdll) {
      LdrRegisterDllNotificationFn reg = (LdrRegisterDllNotificationFn)
          GetProcAddress(ntdll, "LdrRegisterDllNotification");
      if (reg) { reg(0, dll_notify, NULL, &g_ldr_cookie); llog("loader notification armed (cookie %08X)", (DWORD)g_ldr_cookie); }
    }
    patch_iat_all("attach");
    install_hook();
    if (!g_hook_installed) { HANDLE t = CreateThread(NULL, 0, boot_thread, NULL, 0, NULL); if (t) CloseHandle(t); }
  }
  else if (reason == DLL_PROCESS_DETACH) {
    // Unregister the loader callback BEFORE anything else. Leaving it armed means
    // the loader calls into this DLL after it has unloaded - an access violation at
    // process exit, which is exactly when the log is written. Caught 2026-09-01 by
    // test_gpa.exe in probe-only mode (crashed with no d3d9 loaded at all).
    // NOTE: dustfix.cpp has this same defect.
    if (g_ldr_cookie) {
      HMODULE nt = GetModuleHandleA("ntdll.dll");
      if (nt) {
        LdrUnregisterDllNotificationFn unreg = (LdrUnregisterDllNotificationFn)
            GetProcAddress(nt, "LdrUnregisterDllNotification");
        if (unreg) { unreg(g_ldr_cookie); llog("loader notification unregistered"); }
      }
      g_ldr_cookie = NULL;
    }
    restore_slots();   // put the IAT back BEFORE we unload, or shutdown crashes
    llog("=== totals: %ld draws, %ld dust-signature draws, %ld frames ===", g_total_draws, g_dust_draws, g_frame);
    llog("=== %ld triggers fired in wheat-heavy frames (>=%d wheat draws); keeping the last %ld ===",
         g_trigger_total, WHEAT_MIN, g_win_count);
    LONG nw = g_win_count; if (nw > WINDOWS) nw = WINDOWS;
    for (LONG w = 0; w < nw; w++) {
      llog("%s", "");
      llog("=== window %ld  (trigger at row %ld, %ld wheat draws in the previous frame) ===",
           w, g_win_trigger[w], g_win_wheat[w]);
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
