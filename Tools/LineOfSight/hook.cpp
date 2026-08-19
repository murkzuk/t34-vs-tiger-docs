// tvt_los_hook - watch TvT's entire AI vision model from the inside.
//
// Target: Behavior.dll + 0xC9E50 (FUN_100c9e50 with the DLL at its preferred
// base 0x10000000). This one function IS TvT's vision. Decoded from its
// disassembly, it computes:
//
//     visibility  = 1.0                       (or [this+0x110] if target changed)
//     visibility *= stateTable[target->GetState()]      // [this+0x114][i]
//     visibility *= angleCurve(dot(dirToTarget, forward))   // curve at this+0xEC
//     visibility *= rangeCurve(distance)                    // curve at this+0xF8
//     if (visibility <= 0) return false
//     for each 0x1c-byte modifier in [this+0x104 .. this+0x108):
//         if (predicate) visibility *= modifier.factor      // modifier+0x18
//         if (visibility <= 0) return false
//     cache[key] = visibility
//     if (visibility >= 1.0) return true
//     return rand()/32767.0 < 1 - pow(1 - visibility, dt)
//
// (0x1018BC30 is textbook MSVC rand(), LCG 0x343FD/0x269EC3 & 0x7FFF;
//  0x1018D0A0 is pow; 0x10042CB0 is a piecewise-linear curve evaluator;
//  0x1003DE80 is a 2-component vector product. Constants 0.0/1.0/32767.0.)
//
// Two dimensions throughout. No ray, no terrain sample, no foliage test.
//
// WHAT THIS BUILD DOES: nothing but watch. It calls the original, records what
// was asked and what was answered, and returns the original's answer unchanged.
// Proving the hook is stable and reading real traffic comes before changing a
// single decision - wiring new work into a per-frame AI call on a 2001 engine
// is exactly the kind of thing that wrecks performance or destabilises the AI,
// and none of that is proven yet.
//
// The insertion point for occlusion is already obvious from the model above:
// it is one more multiplier of zero, the same shape as the modifier records the
// engine already walks. The architecture does not have to be fought.
//
// SANDBOX ONLY. Refuses to arm anywhere but M:\TvT_INJECT_SANDBOX.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>

static const DWORD VISION_RVA = 0x000C9E50;
static const char *LOG_PATH   = "M:\\TvT_INJECT_SANDBOX\\tvt_los.log";
static const char *SANDBOX    = "M:\\TvT_INJECT_SANDBOX";

// The first instruction is `mov eax, fs:[0]` - six bytes, one instruction, and
// it carries no relocation. That is the whole reason a 5-byte JMP is safe here
// without a length disassembler: copy exactly those six bytes to the
// trampoline and jump back to target+6. Nothing is split, nothing is fixed up.
static const int PATCH_LEN = 6;

static CRITICAL_SECTION g_lock;
static FILE *g_log;
static __int64 g_calls, g_true, g_logged;
static DWORD g_tick0;
static float g_dt_min = 1e30f, g_dt_max = -1e30f;

static void llog(const char *fmt, ...)
{
  if (!g_log) return;
  va_list ap; va_start(ap, fmt);
  vfprintf(g_log, fmt, ap);
  va_end(ap);
  fputc('\n', g_log);
  fflush(g_log);
}

static bool readable(const void *p, size_t n)
{
  MEMORY_BASIC_INFORMATION mbi;
  if (!VirtualQuery(p, &mbi, sizeof(mbi))) return false;
  if (mbi.State != MEM_COMMIT) return false;
  if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return false;
  return (const BYTE *)p + n <= (const BYTE *)mbi.BaseAddress + mbi.RegionSize;
}

// __fastcall with a dummy second parameter is bit-for-bit __thiscall: arg1 in
// ECX, arg2 in EDX (unused), the remaining seven dwords pushed, callee cleans
// 0x1c. That lets the hook and the trampoline both be ordinary C functions and
// keeps hand-written assembly out of this entirely.
//
// Everything is typed as a dword and the floats are bit-cast, so no float ABI
// question can arise on the way through.
typedef char (__fastcall *VisFn)(void *self, void *pad,
                                 DWORD dt, DWORD *tgt, DWORD key, DWORD *a4,
                                 float *pos, float *mat, DWORD dist);

static VisFn g_orig;          // -> trampoline
static BYTE *g_target;

static float F(DWORD u) { float f; memcpy(&f, &u, 4); return f; }

static char __fastcall Hook(void *self, void *pad,
                            DWORD dt, DWORD *tgt, DWORD key, DWORD *a4,
                            float *pos, float *mat, DWORD dist)
{
  char r = g_orig(self, pad, dt, tgt, key, a4, pos, mat, dist);

  EnterCriticalSection(&g_lock);
  g_calls++;
  if (r) g_true++;

  // dt turned out to be the most interesting number in the first run: the very
  // first call arrived with dt = 3.0, i.e. this is a slow AI tick, not a
  // per-frame poll. If that holds, the cost budget for a ray march is enormous
  // and the whole "do not add CPU work to a CPU-bound game" worry shrinks to
  // almost nothing. So track its range rather than assuming.
  float dtf = F(dt);
  if (dtf < g_dt_min) g_dt_min = dtf;
  if (dtf > g_dt_max) g_dt_max = dtf;

  // The first run logged exactly one sample line, because one-in-4096 was
  // calibrated for a call rate this function does not have. Log the opening
  // burst verbatim, then thin out.
  bool want = (g_calls <= 60) || ((g_calls & 0xFF) == 1);
  if (want && g_logged < 600)
  {
    g_logged++;
    // arg6 is a 4x4 row-major matrix: position in the 4th column
    // (m[0][3], m[1][3], m[2][3]) and forward in the first column
    // (m[0][0], m[1][0]).
    float ox = 0, oy = 0, oz = 0, fx = 0, fy = 0;
    if (readable(mat, 48)) {
      ox = mat[3]; oy = mat[7]; oz = mat[11];
      fx = mat[0]; fy = mat[4];
    }
    float tx = 0, ty = 0;
    if (readable(pos, 8)) { tx = pos[0]; ty = pos[1]; }

    llog("[%6I64d] obs (%7.1f,%7.1f,%6.1f) fwd (%5.2f,%5.2f)  tgt (%7.1f,%7.1f)"
         "  dist %8.1f  dt %.4f  -> %s",
         g_calls, ox, oy, oz, fx, fy, tx, ty, F(dist), F(dt),
         r ? "SEEN" : "-");
  }

  if ((g_calls % 5000) == 0) {
    double secs = (GetTickCount() - g_tick0) / 1000.0;
    llog("--- %I64d calls, %I64d seen (%.1f%%), %.0f s elapsed, %.0f calls/s, "
         "dt %.3f..%.3f",
         g_calls, g_true, 100.0 * g_true / g_calls, secs,
         secs > 0 ? g_calls / secs : 0.0, g_dt_min, g_dt_max);
  }

  LeaveCriticalSection(&g_lock);
  return r;
}

static bool install(BYTE *target)
{
  BYTE *tramp = (BYTE *)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE);
  if (!tramp) { llog("VirtualAlloc failed"); return false; }

  memcpy(tramp, target, PATCH_LEN);
  tramp[PATCH_LEN] = 0xE9;
  *(DWORD *)(tramp + PATCH_LEN + 1) =
      (DWORD)(target + PATCH_LEN) - (DWORD)(tramp + PATCH_LEN + 5);

  // Publish the trampoline BEFORE the jump goes in. The moment the first byte
  // of the target changes, another thread can be inside Hook - and this is a
  // function the AI calls every tick for every observer against every
  // candidate, so "unlikely" is not a defence. If g_orig were still null it
  // would call address zero.
  g_orig = (VisFn)tramp;
  g_target = target;

  DWORD old;
  if (!VirtualProtect(target, PATCH_LEN, PAGE_EXECUTE_READWRITE, &old)) {
    llog("VirtualProtect failed"); return false;
  }
  target[0] = 0xE9;
  *(DWORD *)(target + 1) = (DWORD)Hook - (DWORD)(target + 5);
  for (int i = 5; i < PATCH_LEN; i++) target[i] = 0x90;
  VirtualProtect(target, PATCH_LEN, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, PATCH_LEN);
  llog("hooked: target %08X  trampoline %08X  hook %08X",
       (DWORD)target, (DWORD)tramp, (DWORD)Hook);
  return true;
}

static DWORD WINAPI Boot(LPVOID)
{
  char exe[MAX_PATH];
  GetModuleFileNameA(NULL, exe, MAX_PATH);
  if (!strstr(exe, SANDBOX)) {
    // Not the sandbox. Say so and do nothing - a hook that silently arms in
    // the live install is how a good install gets ruined.
    g_log = fopen(LOG_PATH, "a");
    llog("REFUSING to arm: %s is outside %s", exe, SANDBOX);
    if (g_log) fclose(g_log);
    return 0;
  }

  g_log = fopen(LOG_PATH, "w");
  g_tick0 = GetTickCount();
  llog("tvt_los_hook attached to %s", exe);

  // Behavior.dll relocates - it has landed +237MB, +252MB and +234MB from its
  // preferred base on different runs. Resolving at runtime rather than
  // hardcoding is what makes this work at all; a hardcoded address is what
  // killed the November 2025 attempt.
  HMODULE beh = NULL;
  for (int i = 0; i < 600 && !beh; i++) {
    beh = GetModuleHandleA("Behavior.dll");
    if (!beh) Sleep(100);
  }
  if (!beh) { llog("Behavior.dll never loaded"); return 0; }

  BYTE *target = (BYTE *)beh + VISION_RVA;
  llog("Behavior.dll at %08X (preferred 10000000, delta %+d MB); vision fn at %08X",
       (DWORD)beh, ((int)(DWORD)beh - 0x10000000) / (1024 * 1024), (DWORD)target);

  // Verify before patching. The expected first six bytes are
  // `mov eax, fs:[0]` = 64 A1 00 00 00 00, followed by `push -1` = 6A FF.
  // If the bytes are not what the disassembly said, the RVA is wrong or the
  // build differs, and patching would corrupt a live function.
  static const BYTE EXPECT[8] = { 0x64,0xA1,0x00,0x00,0x00,0x00,0x6A,0xFF };
  if (!readable(target, 8) || memcmp(target, EXPECT, 8) != 0) {
    llog("prologue mismatch - NOT patching. found:");
    if (readable(target, 8))
      llog("  %02X %02X %02X %02X %02X %02X %02X %02X",
           target[0],target[1],target[2],target[3],
           target[4],target[5],target[6],target[7]);
    return 0;
  }
  llog("prologue verified");

  install(target);
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
