// atmos_wysiwyg - LIVE atmosphere editor (slider-panel driven).
//
// Injects into T-34 vs Tiger (game or editor). Hooks CAtmosphere::SetSunDirection's
// helper to capture the live CAtmosphere object, then a background thread polls a
// state file (atmos_state.txt) written by atmos_server.py and applies every value
// to the running engine on change. No reload, no console.
//
// Reverse-engineered 2026-08-30 (Objects.dll, image base 0x10000000, RVA==file offset):
//   SetSunDirection = helper 0x5CFA0 (thiscall this + const float* vec3)
//                     then recompute sky 0x5B5A0 (thiscall, no args)
//                     then recompute light 0x5BE50 (thiscall, no args)
//   CAtmosphere members (direct write):
//     SunDirection +0x70 (vec3)      AmbientLight +0x90 (RGBA)
//     SunColor     +0xA0 (RGBA)      FogNear +0x104, FogFar +0x108, FogDensity +0x110
//     FogColorXPos +0x114, XNeg +0x124, YPos +0x134, YNeg +0x144 (RGBA each)
//   Engine clamps sun elevation to ~20 deg minimum.
//   Wind is a SEPARATE class (CWind), not in CAtmosphere - not wired here.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <math.h>

#define HELPER_RVA  0x5CFA0
#define RECOMP1_RVA 0x5B5A0
#define RECOMP2_RVA 0x5BE50
#define FOGCOLOR_RVA 0x5BBB0   // CAtmosphere::ComputeFogColor (thiscall, 3 float args)

#define OFF_AMBIENT  0x90
#define OFF_SUNCOLOR 0xA0
#define OFF_FOGNEAR  0x104
#define OFF_FOGFAR   0x108
#define OFF_FOGDENS  0x110
#define OFF_FOGC0    0x114   // XPos
#define OFF_FOGC1    0x124   // XNeg
#define OFF_FOGC2    0x134   // YPos
#define OFF_FOGC3    0x144   // YNeg
#define OFF_FOGMIX   0x178   // cached blended fog colour (RGBA) - what the renderer reads

static const char LOG_PATH[]  = "K:\\TvTDeepseek\\atmos_wysiwyg\\atmos_wysiwyg.log";
static const char STATE_PATH[] = "K:\\TvTDeepseek\\atmos_wysiwyg\\atmos_state.txt";

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

typedef struct _MY_UNICODE_STRING { USHORT Length; USHORT MaximumLength; PWSTR Buffer; } MY_UNICODE_STRING;
typedef struct _MY_LDR_DLL_NOTIFICATION_DATA { ULONG Flags; MY_UNICODE_STRING *FullDllName; MY_UNICODE_STRING *BaseDllName; PVOID DllBase; ULONG SizeOfImage; } MY_LDR_DLL_NOTIFICATION_DATA;

static bool basename_is_objects(MY_UNICODE_STRING *s)
{
  if (!s || !s->Buffer || s->Length != 22) return false;
  static const WCHAR want[] = L"objects.dll";
  for (int i = 0; i < 11; i++) {
    WCHAR c = s->Buffer[i];
    if (c >= L'A' && c <= L'Z') c = (WCHAR)(c + 32);
    if (c != want[i]) return false;
  }
  return true;
}

typedef void (__thiscall *SetSunDirFn)(void *self, const float *vec);
typedef void (__thiscall *NoArgFn)(void *self);
typedef void (__thiscall *ComputeFogColorFn)(void *self, float x, float y, float z);
static SetSunDirFn g_orig;
static NoArgFn g_recomp1, g_recomp2;
static ComputeFogColorFn g_fogcolor;
static void *g_atmos;
static volatile LONG g_captured;
static volatile LONG g_hook_installed;

static const BYTE EXPECT[6] = { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 };

static void __fastcall HookSetSunDir(void *self, void *edxDummy, const float *vec)
{
  if (InterlockedCompareExchange(&g_captured, 1, 0) == 0) {
    g_atmos = self;
    llog("captured CAtmosphere this=%08X", (DWORD)self);
  }
  g_orig(self, vec);
}

// ---------------------------------------------------------------------------
// state file parsing + apply
// ---------------------------------------------------------------------------
typedef struct {
  long version;
  float sun_azimuth, sun_elevation;
  float sun_color[3], ambient[3];
  float fog_near, fog_far, fog_density;
  float fog_color[3];
} State;

static bool parse_state(State *s)
{
  FILE *f = fopen(STATE_PATH, "r");
  if (!f) return false;
  char line[256];
  bool got_version = false;
  memset(s, 0, sizeof *s);
  while (fgets(line, sizeof line, f)) {
    if      (sscanf(line, "version=%ld", &s->version) == 1) got_version = true;
    else if (sscanf(line, "sun_azimuth=%f", &s->sun_azimuth) == 1) {}
    else if (sscanf(line, "sun_elevation=%f", &s->sun_elevation) == 1) {}
    else if (sscanf(line, "sun_color=%f,%f,%f", &s->sun_color[0], &s->sun_color[1], &s->sun_color[2]) == 3) {}
    else if (sscanf(line, "ambient=%f,%f,%f", &s->ambient[0], &s->ambient[1], &s->ambient[2]) == 3) {}
    else if (sscanf(line, "fog_near=%f", &s->fog_near) == 1) {}
    else if (sscanf(line, "fog_far=%f", &s->fog_far) == 1) {}
    else if (sscanf(line, "fog_density=%f", &s->fog_density) == 1) {}
    else if (sscanf(line, "fog_color=%f,%f,%f", &s->fog_color[0], &s->fog_color[1], &s->fog_color[2]) == 3) {}
  }
  fclose(f);
  return got_version;
}

static void put_rgba(BYTE *a, int off, const float rgb[3])
{
  float v[4] = { rgb[0], rgb[1], rgb[2], 1.0f };
  memcpy(a + off, v, 16);
}

static void apply_state(const State *s)
{
  if (!g_atmos) return;
  BYTE *a = (BYTE *)g_atmos;

  // sun direction (azimuth from north, elevation above horizon)
  float az = s->sun_azimuth * 3.14159265f / 180.0f;
  float el = s->sun_elevation * 3.14159265f / 180.0f;
  float dir[3] = { cosf(az) * cosf(el), -sinf(az) * cosf(el), -sinf(el) };
  g_orig(g_atmos, dir);   // store + normalize
  g_recomp1(g_atmos);     // sky recompute

  // colours + fog (direct member writes)
  put_rgba(a, OFF_SUNCOLOR, s->sun_color);
  put_rgba(a, OFF_AMBIENT, s->ambient);
  *(float *)(a + OFF_FOGNEAR) = s->fog_near;
  *(float *)(a + OFF_FOGFAR)  = s->fog_far;
  *(float *)(a + OFF_FOGDENS) = s->fog_density;
  put_rgba(a, OFF_FOGC0, s->fog_color);
  put_rgba(a, OFF_FOGC1, s->fog_color);
  put_rgba(a, OFF_FOGC2, s->fog_color);
  put_rgba(a, OFF_FOGC3, s->fog_color);
  // The directional blend (ComputeFogColor) is unnecessary when all four colours
  // are equal; write the cached blended colour directly instead (avoids the
  // degenerate-direction crash in that recompute).
  put_rgba(a, OFF_FOGMIX, s->fog_color);

  g_recomp2(g_atmos);     // lighting recompute
}

static DWORD WINAPI poll_thread(LPVOID)
{
  long last_version = -1;
  for (;;) {
    Sleep(100);
    if (!g_captured || !g_atmos) continue;
    State s;
    if (!parse_state(&s)) continue;
    if (s.version != last_version) {
      last_version = s.version;
      apply_state(&s);
      llog("applied v%ld  az=%.0f el=%.0f  sunC(%.2f,%.2f,%.2f)  amb(%.2f,%.2f,%.2f)  fog %.0f/%.0f/%.4f",
           s.version, s.sun_azimuth, s.sun_elevation,
           s.sun_color[0], s.sun_color[1], s.sun_color[2],
           s.ambient[0], s.ambient[1], s.ambient[2],
           s.fog_near, s.fog_far, s.fog_density);
    }
  }
}

// ---------------------------------------------------------------------------
static void patch_objects(BYTE *base)
{
  if (g_hook_installed) return;
  BYTE *t = base + HELPER_RVA;
  if (memcmp(t, EXPECT, 6) != 0) {
    llog("REFUSING to patch: prologue at %08X is %02X %02X %02X %02X %02X %02X",
         (DWORD)t, t[0], t[1], t[2], t[3], t[4], t[5]);
    return;
  }
  patch_jump(t, 6, (void *)HookSetSunDir, (void **)&g_orig, "SetSunDir helper");
  g_recomp1 = (NoArgFn)(base + RECOMP1_RVA);
  g_recomp2 = (NoArgFn)(base + RECOMP2_RVA);
  g_fogcolor = (ComputeFogColorFn)(base + FOGCOLOR_RVA);
  llog("recompute: sky=%08X light=%08X fog=%08X", (DWORD)g_recomp1, (DWORD)g_recomp2, (DWORD)g_fogcolor);
  InterlockedExchange(&g_hook_installed, 1);
  CreateThread(NULL, 0, poll_thread, NULL, 0, NULL);
}

typedef VOID (CALLBACK *MyDllNotificationFn)(ULONG, MY_LDR_DLL_NOTIFICATION_DATA *, PVOID);
typedef LONG (NTAPI *LdrRegisterDllNotificationFn)(ULONG, MyDllNotificationFn, PVOID, PVOID *);

static VOID CALLBACK dll_notify(ULONG reason, MY_LDR_DLL_NOTIFICATION_DATA *data, PVOID)
{
  if (reason != 1 || g_hook_installed) return;
  if (!data || !data->DllBase) return;
  if (!basename_is_objects(data->BaseDllName)) return;
  llog("notify: Objects.dll loaded at %08X", (DWORD)data->DllBase);
  patch_objects((BYTE *)data->DllBase);
}

static void install_hook(void)
{
  if (g_hook_installed) return;
  HMODULE m = GetModuleHandleA("Objects.dll");
  if (!m) return;
  patch_objects((BYTE *)m);
}

static DWORD WINAPI boot_thread(LPVOID)
{
  DWORD start = GetTickCount();
  while (!g_hook_installed) {
    install_hook();
    if (g_hook_installed) break;
    if (GetTickCount() - start > 30000) { llog("boot: Objects.dll never appeared"); break; }
  }
  return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID)
{
  if (reason == DLL_PROCESS_ATTACH) {
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    g_log = fopen(LOG_PATH, "w");
    llog("=== atmos_wysiwyg attached (pid %lu) ===", GetCurrentProcessId());
    llog("panel: http://127.0.0.1:8766  (state: %s)", STATE_PATH);
    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    if (ntdll) {
      LdrRegisterDllNotificationFn reg = (LdrRegisterDllNotificationFn)GetProcAddress(ntdll, "LdrRegisterDllNotification");
      if (reg) { PVOID c = NULL; reg(0, dll_notify, NULL, &c); llog("loader notification armed"); }
    }
    install_hook();
    if (!g_hook_installed) { HANDLE t = CreateThread(NULL, 0, boot_thread, NULL, 0, NULL); if (t) CloseHandle(t); }
  }
  else if (reason == DLL_PROCESS_DETACH) {
    llog("=== atmos_wysiwyg detach ===");
    if (g_log) { fflush(g_log); fclose(g_log); g_log = NULL; }
    DeleteCriticalSection(&g_lock);
  }
  return TRUE;
}
