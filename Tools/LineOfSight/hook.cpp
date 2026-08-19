// tvt_los_hook - give TvT's AI line of sight.
//
// Target: Behavior.dll + 0xC9E50 (FUN_100c9e50 at the DLL's preferred base
// 0x10000000). That one function IS TvT's vision model. Decoded from its
// disassembly:
//
//     visibility  = 1.0                       (or [this+0x110] if target changed)
//     visibility *= stateTable[target->GetState()]          // [this+0x114][i]
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
// Two dimensions throughout: the observer's transform is passed in and its Z
// is never read. No ray cast, no terrain sample, no foliage test anywhere.
//
// Measured live: 31 calls a second, dt between 3 and 89 s. This is a slow AI
// tick, not a per-frame poll, so a 20-50 lookup march costs about 1,200
// lookups a second. There is no performance problem here.
//
// Also measured live: 70% of the engine's positive sightings are through solid
// ground or woodland.
//
// THE ONE RULE: this may only ever turn a SEEN into a miss. The engine's own
// "not seen" is usually just its detection dice failing on that tick and says
// nothing about geometry, so promoting one to a sighting would invent
// information. Occlusion subtracts; it never adds.
//
// SANDBOX ONLY. Refuses to arm anywhere but M:\TvT_INJECT_SANDBOX.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <math.h>
#include "terrain.h"

static const DWORD VISION_RVA = 0x000C9E50;
static const char *SANDBOX  = "M:\\TvT_INJECT_SANDBOX";
static const char *LOG_PATH = "M:\\TvT_INJECT_SANDBOX\\tvt_los.log";
static const char *INI_PATH = "M:\\TvT_INJECT_SANDBOX\\tvt_los.ini";

// The first instruction is `mov eax, fs:[0]` - six bytes, one instruction, and
// it carries no relocation. That is why a 5-byte JMP is safe here without a
// length disassembler: copy exactly those six bytes to the trampoline and jump
// back to target+6. Nothing is split, nothing needs fixing up.
static const int PATCH_LEN = 6;

// Scales every vegetation sight-through distance. Below 1.0 makes woods
// denser. Defined here rather than in terrain.h so the header stays pure data.
float g_sight_scale = 1.0f;

enum Mode { MODE_WATCH, MODE_DENY_FAR, MODE_LOS };
static Mode  g_mode = MODE_WATCH;
static float g_deny_beyond = 400.0f;

static CRITICAL_SECTION g_lock;
static FILE *g_log;
static __int64 g_calls, g_true, g_denied, g_logged;
static DWORD g_tick0;
static float g_dt_min = 1e30f, g_dt_max = -1e30f;
static Terrain g_terrain;
static volatile LONG g_ready;       // terrain loaded, enforcement live
static volatile LONG g_giveup;      // identification failed, do not enforce
static __int64 g_gap_denied;        // sightings refused while waiting
static int g_last_total;            // object loads seen on the last attempt

static void llog(const char *fmt, ...)
{
  if (!g_log) return;
  va_list ap; va_start(ap, fmt);
  vfprintf(g_log, fmt, ap); va_end(ap);
  fputc('\n', g_log); fflush(g_log);
}

static bool readable(const void *p, size_t n)
{
  MEMORY_BASIC_INFORMATION mbi;
  if (!VirtualQuery(p, &mbi, sizeof(mbi))) return false;
  if (mbi.State != MEM_COMMIT) return false;
  if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return false;
  return (const BYTE *)p + n <= (const BYTE *)mbi.BaseAddress + mbi.RegionSize;
}

// Our own generator. The engine's detection roll uses the CRT rand() in
// Behavior.dll and its sequence is part of the behaviour being observed -
// borrowing it would perturb the very thing under test.
static DWORD g_seed = 0x13579BDF;
static float frand()
{
  g_seed = g_seed * 1103515245u + 12345u;
  return ((g_seed >> 16) & 0x7FFF) / 32767.0f;
}

// __fastcall with a dummy second parameter is bit-for-bit __thiscall: arg1 in
// ECX, arg2 in EDX (unused), the remaining seven dwords pushed, callee cleans
// 0x1c. That lets the hook and the trampoline both be ordinary C functions and
// keeps hand-written assembly out of this entirely. Everything is typed as a
// dword and floats are bit-cast, so no float ABI question can arise.
typedef char (__fastcall *VisFn)(void *self, void *pad,
                                 DWORD dt, DWORD *tgt, DWORD key, DWORD *a4,
                                 float *pos, float *mat, DWORD dist);
static VisFn g_orig;

static float F(DWORD u) { float f; memcpy(&f, &u, 4); return f; }

// ---------------------------------------------------------------------------
// Which mission is loaded?
//
// Nothing needs configuring, and this does not guess. The engine names every
// object it loads in its own log:
//
//     [MissionController] Object CC1M2Gr_NUSSR_Tanks successfully loaded at 17379
//
// Those names are unique to a mission and appear verbatim in exactly one
// Content.script, so the folder can be found by exact string match.
//
// A statistical approach was tried first - match observer heights against each
// candidate heightfield and take the tightest fit - and it does not work.
// Several missions share most of a base heightfield with only local edits, so
// Campaign_1/Mission_2, CF3Mission and DM5Mission returned IDENTICAL ground at
// all nine probe points despite being different files. Heights cannot separate
// maps that are identical where you are standing. Their ZONE maps do differ,
// which is what makes picking the wrong one harmful rather than harmless.
//
// The height probe is kept, but demoted to what it is good for: checking after
// the fact that the loaded terrain actually fits, and saying so in the log.
// ---------------------------------------------------------------------------

static const int NPROBE = 12;
static float g_px[NPROBE], g_py[NPROBE], g_pz[NPROBE];
static int   g_nprobe;
static bool  g_checked;   // fit check done

static bool find_zone_bmp(const char *folder, char *out)
{
  char pat[MAX_PATH];
  _snprintf(pat, MAX_PATH, "%s\\TerrainZone*.bmp", folder);
  WIN32_FIND_DATAA fd;
  HANDLE h = FindFirstFileA(pat, &fd);
  if (h == INVALID_HANDLE_VALUE) return false;
  _snprintf(out, MAX_PATH, "%s\\%s", folder, fd.cFileName);
  FindClose(h);
  return true;
}

// Read a file the game may still have open for writing.
static char *slurp(const char *path, long *len)
{
  HANDLE h = CreateFileA(path, GENERIC_READ,
                         FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                         NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
  if (h == INVALID_HANDLE_VALUE) return NULL;
  DWORD sz = GetFileSize(h, NULL);
  if (sz == INVALID_FILE_SIZE || sz == 0) { CloseHandle(h); return NULL; }
  char *buf = (char *)malloc(sz + 1);
  if (!buf) { CloseHandle(h); return NULL; }
  DWORD got = 0;
  ReadFile(h, buf, sz, &got, NULL);
  CloseHandle(h);
  buf[got] = 0;
  if (len) *len = (long)got;
  return buf;
}

// After loading, confirm the terrain actually fits where the units are. A
// unit's origin sits a fixed height above ground for its class - measured
// +0.85 m for a soldier, +1.41 m for a T-34/76, +1.65 m for a Tiger - so every
// offset should land in a narrow positive band. If it does not, the wrong
// terrain is loaded and enforcing against it would be worse than not enforcing.
static bool terrain_fits()
{
  float lo = 1e30f, hi = -1e30f;
  for (int i = 0; i < g_nprobe; i++) {
    float d = g_pz[i] - g_terrain.ground(g_px[i], g_py[i]);
    if (d < lo) lo = d;
    if (d > hi) hi = d;
  }
  llog("  fit check over %d observer positions: offsets %+.2f..%+.2f m",
       g_nprobe, lo, hi);
  return lo > 0.0f && hi < 3.0f;
}


static const int NNAMES = 200, NAMELEN = 96, MAXOBJ = 1024;

// The engine names every object it loads in its own log:
//     [MissionController] Object CC1M2Gr_NUSSR_Tanks successfully loaded at 17379
//
// Collect the last NNAMES DISTINCT names by walking BACKWARDS. Taking the last
// NNAMES entries and de-duplicating afterwards does not work: objects load
// units-first and scenery-last, so the tail is all "_3", "_4", "fence_11" -
// names half the missions in the game share. Walking back until enough
// distinct names are held reaches into the unit names, which are specific.
static int collect_names(char names[NNAMES][NAMELEN])
{
  char p[MAX_PATH];
  _snprintf(p, MAX_PATH, "%s\\execution.log", SANDBOX);
  char *buf = slurp(p, NULL);
  if (!buf) {
    // Worth saying loudly: if the engine holds its own log open without
    // FILE_SHARE_READ, this identification route is closed entirely.
    llog("could not read execution.log (error %lu)", GetLastError());
    return 0;
  }

  static const char TAG[] = "[MissionController] Object ";
  char (*all)[NAMELEN] = (char (*)[NAMELEN])malloc((size_t)MAXOBJ * NAMELEN);
  if (!all) { free(buf); return 0; }

  int total = 0;
  for (char *c = buf; (c = strstr(c, TAG)) != NULL; c += sizeof(TAG) - 1) {
    char *t = c + sizeof(TAG) - 1;
    char *sp = strchr(t, ' ');
    if (!sp || sp - t >= NAMELEN) continue;
    memcpy(all[total % MAXOBJ], t, sp - t);
    all[total % MAXOBJ][sp - t] = 0;
    total++;
  }
  free(buf);

  int have = total < MAXOBJ ? total : MAXOBJ;
  int n = 0;
  for (int i = 0; i < have && n < NNAMES; i++) {
    const char *src = all[((total - 1 - i) % MAXOBJ + MAXOBJ) % MAXOBJ];
    bool dup = false;
    for (int j = 0; j < n; j++) if (!strcmp(names[j], src)) { dup = true; break; }
    if (!dup) strncpy(names[n++], src, NAMELEN - 1);
  }
  free(all);
  g_last_total = total;
  return n;
}

static int score_folder(const char *folder, char names[NNAMES][NAMELEN], int n)
{
  char p[MAX_PATH];
  _snprintf(p, MAX_PATH, "%s\\Content.script", folder);
  char *buf = slurp(p, NULL);
  if (!buf) return 0;
  int k = 0;
  char quoted[NAMELEN + 4];
  for (int i = 0; i < n; i++) {
    _snprintf(quoted, sizeof(quoted), "\"%s\"", names[i]);
    if (strstr(buf, quoted)) k++;
  }
  free(buf);
  return k;
}

static void score_tree(const char *root, char names[NNAMES][NAMELEN], int n,
                       char best[MAX_PATH], int *bestk, int *secondk, int depth)
{
  if (depth > 3) return;
  char pat[MAX_PATH];
  _snprintf(pat, MAX_PATH, "%s\\*", root);
  WIN32_FIND_DATAA fd;
  HANDLE h = FindFirstFileA(pat, &fd);
  if (h == INVALID_HANDLE_VALUE) return;
  do {
    if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) continue;
    if (fd.cFileName[0] == '.') continue;
    char sub[MAX_PATH];
    _snprintf(sub, MAX_PATH, "%s\\%s", root, fd.cFileName);
    char hmap[MAX_PATH];
    _snprintf(hmap, MAX_PATH, "%s\\hmap.raw", sub);
    if (GetFileAttributesA(hmap) != INVALID_FILE_ATTRIBUTES) {
      int k = score_folder(sub, names, n);
      if (k > *bestk) {
        *secondk = *bestk; *bestk = k;
        strncpy(best, sub, MAX_PATH - 1);
      } else if (k > *secondk) *secondk = k;
    }
    score_tree(sub, names, n, best, bestk, secondk, depth + 1);
  } while (FindNextFileA(h, &fd));
  FindClose(h);
}

static bool identify()
{
  static char names[NNAMES][NAMELEN];   // 19 KB - not on the stack
  int n = collect_names(names);
  if (n < 10)
    return false;          // mission still loading; the watcher retries

  char root[MAX_PATH], best[MAX_PATH] = "";
  _snprintf(root, MAX_PATH, "%s\\Missions", SANDBOX);
  int bestk = 0, secondk = 0;
  score_tree(root, names, n, best, &bestk, &secondk, 0);

  // Insist on a real margin. Generic object names ("AllVillageNavPoints")
  // appear in several missions, so a narrow win means the answer is not known.
  // A near-tie early on usually just means the mission is still loading, so
  // this is a retry rather than a failure.
  if (!best[0] || bestk * 10 < n * 6 || bestk * 4 < secondk * 5)
    return false;

  llog("read %d object loads from execution.log, %d distinct names used",
       g_last_total, n);
  llog("mission match: %d/%d names, runner-up %d  ->  %s",
       bestk, n, secondk, best);
  char zbmp[MAX_PATH];
  if (!find_zone_bmp(best, zbmp) || !load_terrain(&g_terrain, best, zbmp)) {
    llog("  could not load its terrain");
    return false;
  }
  llog("  MISSION: %s", best);
  llog("  hmap %dx%d cell %.3f m ; zones %dx%d cell %.3f m",
       g_terrain.hdim, g_terrain.hdim, g_terrain.hcell,
       g_terrain.zw, g_terrain.zh, g_terrain.zcell);
  return true;
}

// Poll for the mission from the moment the DLL attaches. Objects load before
// gameplay starts, so terrain is ready before the first vision call and there
// is no window in which sightings go unexamined.
static DWORD WINAPI MissionWatcher(LPVOID)
{
  for (int i = 0; i < 100; i++) {          // 100 x 200 ms = 20 s
    if (g_mode != MODE_LOS) return 0;
    if (identify()) {
      InterlockedExchange(&g_ready, 1);
      llog("  enforcement live");
      return 0;
    }
    Sleep(200);
  }
  InterlockedExchange(&g_giveup, 1);
  llog("could not identify the mission within 20 s - no occlusion this run "
       "(watch behaviour, nothing denied)");
  g_mode = MODE_WATCH;
  return 0;
}

// ---------------------------------------------------------------------------

static char __fastcall Hook(void *self, void *pad,
                            DWORD dt, DWORD *tgt, DWORD key, DWORD *a4,
                            float *pos, float *mat, DWORD dist)
{
  char r = g_orig(self, pad, dt, tgt, key, a4, pos, mat, dist);

  EnterCriticalSection(&g_lock);
  g_calls++;
  if (r) g_true++;

  float dtf = F(dt), distf = F(dist);
  if (dtf < g_dt_min) g_dt_min = dtf;
  if (dtf > g_dt_max) g_dt_max = dtf;

  // arg6 is a 4x4 row-major matrix: position in the 4th column, forward in the
  // first. Confirmed against Content.script to the digit on live traffic.
  float ox = 0, oy = 0, oz = 0;
  bool haveobs = readable(mat, 48);
  if (haveobs) { ox = mat[3]; oy = mat[7]; oz = mat[11]; }
  float tx = 0, ty = 0;
  bool havetgt = readable(pos, 8);
  if (havetgt) { tx = pos[0]; ty = pos[1]; }

  // Keep probes spatially separated. Consecutive calls are one observer
  // against many targets, so twelve in a row are twelve copies of the same
  // tank - and a fit check against a single point proves almost nothing.
  if (haveobs && g_nprobe < NPROBE && oz > 1.0f) {
    bool tooclose = false;   // "near" is an MSVC keyword
    for (int i = 0; i < g_nprobe; i++) {
      float ddx = g_px[i] - ox, ddy = g_py[i] - oy;
      if (ddx * ddx + ddy * ddy < 2500.0f) { tooclose = true; break; }
    }
    if (!tooclose) {
      g_px[g_nprobe] = ox; g_py[g_nprobe] = oy; g_pz[g_nprobe] = oz;
      g_nprobe++;
    }
  }
  // The fit check is a safety net, not part of identification: it confirms
  // afterwards that the terrain we loaded is the one these units are standing
  // on. Run it once enough spatially distinct positions exist.
  if (g_ready && !g_checked && g_nprobe >= 3) {
    g_checked = true;
    if (!terrain_fits()) {
      llog("  FIT FAILED - that is not the terrain these units are standing "
           "on. Dropping to watch mode rather than enforcing against the "
           "wrong map.");
      g_mode = MODE_WATCH;
    }
  }

  char out = r;
  const char *note = "";
  float factor = 1.0f;
  Sight sight = { 1.0f, "clear", 0.0f, 0.0f, 0 };

  // Occlusion may only subtract. If the engine already said no, leave it.
  if (r && haveobs && havetgt)
  {
    if (g_mode == MODE_DENY_FAR) {
      // Not a model of anything - a deliberately crude, unmistakable effect, to
      // prove a decision can be influenced at all before trusting a subtle one.
      if (distf > g_deny_beyond) { out = 0; factor = 0.0f; note = " DENIED(far)"; }
    }
    else if (g_mode == MODE_LOS && !g_ready && !g_giveup) {
      // Terrain not loaded yet, so we cannot say whether this is visible -
      // refuse it. Letting it through is what produced x-ray vision through
      // woodland for the first thirteen seconds of a mission, and a target
      // acquired in that window stays acquired long after it closes.
      out = 0; factor = 0.0f; note = " DENIED(not ready)";
      g_gap_denied++;
    }
    else if (g_mode == MODE_LOS && g_ready) {
      // Both endpoints come from the heightfield. The engine's Z is mid-model,
      // not ground contact, so adding an eye height to it would put the gunner
      // a metre and a half too high.
      float gz = g_terrain.ground(ox, oy);
      Sight s = march(&g_terrain, ox, oy, gz + 2.0f,
                      tx, ty, g_terrain.ground(tx, ty) + 1.3f);
      factor = s.factor;
      sight = s;
      if (factor <= 0.0f || frand() > factor) {
        out = 0;
        note = (s.why[0] == 't') ? " DENIED(terrain)" : " DENIED(foliage)";
      }
    }
    if (!out) g_denied++;
  }

  bool want = (g_calls <= 60) || ((g_calls & 0xFF) == 1) || (note[0] != 0 && g_logged < 200);
  if (want && g_logged < 800)
  {
    g_logged++;
    llog("[%6I64d] obs (%7.1f,%7.1f,%6.1f) fwd (%5.2f,%5.2f)  tgt (%7.1f,%7.1f)"
         "  dist %8.1f  dt %.4f  -> %s%s",
         g_calls, ox, oy, oz, haveobs ? mat[0] : 0.0f, haveobs ? mat[4] : 0.0f,
         tx, ty, distf, dtf, r ? "SEEN" : "-", note);
    // The march returns a fraction, not a verdict. Recording it shows how much
    // of the effect is partial cover - a turret over a crest - rather than
    // total masking, which is what decides whether the fraction is earning its
    // keep or could be a plain bool.
    if (g_mode == MODE_LOS && r && haveobs && havetgt &&
        (factor < 1.0f || sight.veg_metres > 0.0f))
    {
      char veg[64];
      if (sight.veg_metres > 0.0f)
        _snprintf(veg, sizeof(veg), "%.0f m of vegetation, mostly zone %d",
                  sight.veg_metres, sight.veg_zone);
      else
        strcpy(veg, "no vegetation on the line");
      llog("           masked %.0f%%  |  %s",
           (1.0f - factor) * 100.0f, veg);
    }
  }

  if ((g_calls % 5000) == 0) {
    double secs = (GetTickCount() - g_tick0) / 1000.0;
    llog("--- %I64d calls, %I64d seen (%.1f%%), %I64d denied by LOS "
         "(%I64d before terrain was ready), %.0f s, %.0f calls/s, dt %.3f..%.3f",
         g_calls, g_true, 100.0 * g_true / g_calls, g_denied, g_gap_denied, secs,
         secs > 0 ? g_calls / secs : 0.0, g_dt_min, g_dt_max);
  }

  LeaveCriticalSection(&g_lock);
  return out;
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
  // of the target changes, another thread can be inside Hook; if g_orig were
  // still null it would call address zero.
  g_orig = (VisFn)tramp;

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

static void read_ini()
{
  char buf[64];
  GetPrivateProfileStringA("los", "mode", "watch", buf, sizeof(buf), INI_PATH);
  if (!_stricmp(buf, "los")) g_mode = MODE_LOS;
  else if (!_stricmp(buf, "deny_far")) g_mode = MODE_DENY_FAR;
  else g_mode = MODE_WATCH;
  g_deny_beyond = (float)GetPrivateProfileIntA("los", "deny_beyond", 400, INI_PATH);
  int pct = GetPrivateProfileIntA("los", "sight_scale", 100, INI_PATH);
  if (pct < 10) pct = 10;
  if (pct > 500) pct = 500;
  g_sight_scale = pct / 100.0f;
}

static DWORD WINAPI Boot(LPVOID)
{
  char exe[MAX_PATH];
  GetModuleFileNameA(NULL, exe, MAX_PATH);
  if (!strstr(exe, SANDBOX)) {
    // A hook that silently arms in the live install is how a good install gets
    // ruined. Say so, do nothing.
    g_log = fopen(LOG_PATH, "a");
    llog("REFUSING to arm: %s is outside %s", exe, SANDBOX);
    if (g_log) fclose(g_log);
    return 0;
  }

  g_log = fopen(LOG_PATH, "w");
  g_tick0 = GetTickCount();
  read_ini();
  llog("tvt_los_hook attached to %s", exe);
  llog("mode = %s%s",
       g_mode == MODE_LOS ? "los" : g_mode == MODE_DENY_FAR ? "deny_far" : "watch",
       g_mode == MODE_DENY_FAR ? "" : "");
  if (g_mode == MODE_DENY_FAR)
    llog("  will refuse every sighting beyond %.0f m", g_deny_beyond);
  if (g_mode == MODE_LOS)
    llog("  sight_scale %.2f (dense conifer opaque at %.0f m)",
         g_sight_scale, 15.0f * g_sight_scale);

  // Behavior.dll relocates - +237, +252 and +241 MB observed on different runs.
  // Resolving at runtime rather than hardcoding is what makes this work at all.
  HMODULE beh = NULL;
  for (int i = 0; i < 600 && !beh; i++) {
    beh = GetModuleHandleA("Behavior.dll");
    if (!beh) Sleep(100);
  }
  if (!beh) { llog("Behavior.dll never loaded"); return 0; }

  BYTE *target = (BYTE *)beh + VISION_RVA;
  llog("Behavior.dll at %08X (preferred 10000000, delta %+d MB); vision fn at %08X",
       (DWORD)beh, ((int)(DWORD)beh - 0x10000000) / (1024 * 1024), (DWORD)target);

  // Verify before patching. If the bytes are not what the disassembly said,
  // the RVA is wrong or the build differs, and patching would corrupt a live
  // function.
  static const BYTE EXPECT[8] = { 0x64,0xA1,0x00,0x00,0x00,0x00,0x6A,0xFF };
  if (!readable(target, 8) || memcmp(target, EXPECT, 8) != 0) {
    llog("prologue mismatch - NOT patching");
    return 0;
  }
  llog("prologue verified");
  install(target);
  if (g_mode == MODE_LOS)
    CreateThread(NULL, 0, MissionWatcher, NULL, 0, NULL);
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
