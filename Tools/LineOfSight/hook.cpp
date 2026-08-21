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
// OPT-IN ONLY. Refuses to arm unless the host install is listed in
// tvt_los_allow.txt, which sits beside this DLL - never inside a game folder,
// so an install cannot authorise itself.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <math.h>
#include "terrain.h"

static const DWORD VISION_RVA = 0x000C9E50;

// CAutoShooterComponent::Update - vtable slot 7 of the primary vtable at RVA
// 0x249258. This is the PLAYER's gunner, which does not use the AI vision
// function at all. Field offsets on that object, from its property loader at
// 0x1004AA80..0x1004ABC5:  +0x144 RadarMaxDistance (3000.0 by default),
// +0x148 ViewAngle in RADIANS, +0xE0 touched 13 times in the update and most
// likely the current target.
static const DWORD CREW_RVA = 0x0004B1E0;
static const DWORD CREW_VTABLE_RVA = 0x00249258;   // primary, this_offset 0

// The `call 0x1000ef80` at the heart of the range gate. Patching the CALL SITE
// rather than the function keeps this to one address; the function itself has
// 80 callers and is a generic 3D vector length.
static const DWORD GATE_CALL_RVA = 0x0004B400;
static const DWORD VECLEN_RVA    = 0x0000EF80;
// CAutoCommanderComponent - the OTHER half of the player's crew. It picks
// targets; CAutoShooterComponent only keeps them. Its Update is taken from the
// same slot 7 of its primary vtable, resolved at runtime rather than by
// address, so nothing here depends on a disassembly being right.
static const DWORD CMDR_VTABLE_RVA = 0x00248D98;
static const int   UPDATE_SLOT = 7;

static const DWORD CREW_RADAR_MAX = 0x144;
static const DWORD CREW_VIEW_ANGLE = 0x148;
// Filled in at attach from the running executable and this DLL's own location.
// Nothing here is a fixed install path any more.
static char g_root[MAX_PATH];       // the game folder hosting us
static char g_log_path[MAX_PATH];   // <root>\tvt_los.log
static char g_ini_path[MAX_PATH];   // <root>\tvt_los.ini
static char g_allow_path[MAX_PATH]; // <dll folder>\tvt_los_allow.txt
#define SANDBOX   g_root
#define LOG_PATH  g_log_path
#define INI_PATH  g_ini_path

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

static bool     g_crew_watch;       // hook the player's gunner tick
static bool g_clip_cursor = true;   // keep the mouse inside the game window
static bool g_gate_probe;       // watch the range gate's call site
static bool g_gate_enforce;     // and actually reject blocked candidates
static __int64 g_gate_denied, g_gate_nopair;
static __int64 g_gate_calls, g_gate_logged;
static __int64 g_cmdr_calls;   // CAutoCommanderComponent::Update, watch pass
// True once execution.log shows mission objects loading. Until then the game
// is sitting in a menu and the identification budget must not be spent.
static volatile bool g_saw_objects = false;
static bool g_announced_mode_los = false;

// Self-timing. The march is the only part of this that scales with anything -
// it walks the line at half a zone cell per step, so a 5 km sight line on an
// 18 km map is around 500 steps. Whether that matters is a measurement, not an
// opinion: these accumulate raw performance-counter ticks and the summary
// turns them into a share of wall time.
static __int64 g_march_ticks, g_march_count;
static __int64 g_qpc_freq;

static inline __int64 tick()
{
  LARGE_INTEGER t;
  QueryPerformanceCounter(&t);
  return t.QuadPart;
}
static __int64  g_crew_calls, g_crew_logged;

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

// Last path separator, either kind - a path may arrive with forward slashes
// and looking for only one of them silently yields the wrong folder.
static char *last_sep(char *p)
{
  char *a = strrchr(p, 92);   // backslash, by code, to keep escapes out
  char *b = strrchr(p, 47);      // forward slash
  return (a > b) ? a : b;
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
static HINSTANCE g_self;

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
// unit's origin sits a fixed height above ground for its class, so every
// offset should be positive and they should all be CLOSE TO EACH OTHER.
//
// Judge by that agreement, not by an absolute band. The first version required
// every offset under 3.0 m, which was the band REDUX's own models happen to
// occupy (+0.85 m soldier, +1.41 m T-34/76, +1.65 m Tiger). ZW's models sit
// higher: its first run measured +3.30..+3.31 m and the check threw away a
// terrain that was demonstrably correct, dropping to watch mode for the whole
// session. A spread of 0.01 m across three separated tanks cannot happen on
// the wrong map.
//
// What a genuinely wrong terrain looks like: the shared-terrain experiment
// failed at -75.90 m. Wrong maps miss by tens of metres and disagree with each
// other. So the test is agreement plus a sanity range, with the band wide
// enough to hold any tank anyone models.
static bool terrain_fits()
{
  float lo = 1e30f, hi = -1e30f;
  for (int i = 0; i < g_nprobe; i++) {
    float d = g_pz[i] - g_terrain.ground(g_px[i], g_py[i]);
    if (d < lo) lo = d;
    if (d > hi) hi = d;
  }
  float spread = hi - lo;
  // Slightly negative is possible where a tank straddles a bilinear cell on a
  // slope; metres below ground is not.
  bool ok = lo > -1.5f && hi < 12.0f && spread < 3.0f;
  llog("  fit check over %d observer positions: offsets %+.2f..%+.2f m "
       "(spread %.2f m) - %s",
       g_nprobe, lo, hi, spread, ok ? "consistent, terrain accepted" : "REJECTED");
  return ok;
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
    // A mission folder is one that declares a world, not one that happens to
    // contain a file called hmap.raw. ZW names its heightfields hmap1.raw and
    // declares the path in the script, so the old test skipped them entirely.
    char wm[MAX_PATH];
    _snprintf(wm, MAX_PATH, "%s\\WorldMatricies.script", sub);
    if (GetFileAttributesA(wm) != INVALID_FILE_ATTRIBUTES) {
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
  if (n < 10) {
    // No mission objects in the log yet. This is the MENU, not a slow load,
    // and the watcher must not count it against the give-up budget - see
    // g_saw_objects below.
    return false;
  }
  g_saw_objects = true;

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

  // Same mission as last time - nothing to do. This runs every two seconds
  // for the life of the process, so it must be quiet and cheap in the common
  // case.
  if (g_terrain.valid() && !strcmp(g_terrain.name, best))
    return true;

  if (g_terrain.valid()) {
    llog("");
    llog("MISSION CHANGED - reloading terrain");
    InterlockedExchange(&g_ready, 0);   // deny rather than use the old map
    free_terrain(&g_terrain);
    g_nprobe = 0;
    g_checked = false;
  }

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
  // Print the world size. It is read from the mission's own
  // WorldMatricies.script and the shipped missions are not all the same size,
  // so a wrong one here is the first thing to suspect if sight lines look
  // nonsensical rather than merely wrong.
  llog("  world %.0f m across", g_terrain.world);
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
  int misses = 0;
  bool announced = false;
  for (;;) {
    // Deliberately NOT "if (g_mode != MODE_LOS) return" any more: a give-up
    // sets watch mode, and the watcher is what un-does that.
    if (g_mode == MODE_DENY_FAR) return 0;

    if (identify()) {
      if (g_mode != MODE_LOS && g_announced_mode_los == false) {
        // Recovered after a give-up: arm properly rather than stay in watch.
        g_mode = MODE_LOS;
        InterlockedExchange(&g_giveup, 0);
        g_announced_mode_los = true;
        llog("  mission identified after all - occlusion is ON from here");
      }
      if (!g_ready) {
        InterlockedExchange(&g_ready, 1);
        llog("  enforcement live");
      }
      announced = false;
      misses = 0;
      // Settled. Keep looking, but slowly: the only thing left to catch is the
      // player quitting to the menu and loading a different mission, which
      // would otherwise leave us enforcing against the wrong map forever.
      Sleep(2000);
      continue;
    }

    // Not identified.
    //
    // The budget is only spent while a mission is actually LOADING. The first
    // version counted from the moment the DLL attached, so a player who spent
    // twenty seconds in the menus - which is normal - used the whole budget
    // before the mission existed, and the run had no occlusion at all. That
    // happened, and it looked exactly like the AI seeing through hills again.
    if (!g_saw_objects) { Sleep(200); continue; }

    if (!g_terrain.valid() && ++misses >= 150) {
      if (!announced) {
        InterlockedExchange(&g_giveup, 1);
        llog("could not identify the mission within 30 s of its objects "
             "loading - watch behaviour for now, still retrying");
        g_mode = MODE_WATCH;
        announced = true;
      }
      // Do NOT return. Quitting to the menu and loading another mission must
      // still arm. Keep looking, slowly.
      Sleep(2000);
      continue;
    }
    Sleep(200);
  }
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
      // And the player's gunner with it. These are two separate hooks against
      // ONE terrain: if that terrain is not trusted, neither may use it. The
      // first ZW run had the AI stand down while the gate went on refusing
      // targets for another 2000 checks.
      if (g_gate_enforce) {
        llog("  the player-gunner gate stands down for the same reason.");
        g_gate_enforce = false;
      }
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
      __int64 t0 = tick();
      Sight s = march(&g_terrain, ox, oy, gz + 2.0f,
                      tx, ty, g_terrain.ground(tx, ty) + 1.3f);
      g_march_ticks += tick() - t0;
      g_march_count++;
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
    // Carry the gate counters here too. Their own summary only fires every
    // 2000 checks, which left it impossible to tell "ran a few hundred times
    // with nothing to refuse" from "never ran at all".
    llog("---   gate: %I64d checks, %I64d refused, %I64d unmatched",
         g_gate_calls, g_gate_denied, g_gate_nopair);
    if (g_crew_watch)
      llog("---   commander: %I64d updates", g_cmdr_calls);
    // What the marching actually cost. If this is not a visible fraction of
    // wall time, the DLL is not the reason for a framerate.
    if (g_qpc_freq > 0 && g_march_count > 0) {
      double march_s = (double)g_march_ticks / (double)g_qpc_freq;
      llog("---   march: %I64d lines, %.0f us each, %.2f s total = %.2f%% of "
           "wall time", g_march_count,
           march_s * 1e6 / (double)g_march_count, march_s,
           secs > 0 ? 100.0 * march_s / secs : 0.0);
    } else if (g_march_count == 0) {
      llog("---   march: not run - the line is only walked in los mode");
    }
    llog("--- %I64d calls, %I64d seen (%.1f%%), %I64d denied by LOS "
         "(%I64d before terrain was ready), %.0f s, %.0f calls/s, dt %.3f..%.3f",
         g_calls, g_true, 100.0 * g_true / g_calls, g_denied, g_gap_denied, secs,
         secs > 0 ? g_calls / secs : 0.0, g_dt_min, g_dt_max);
  }

  LeaveCriticalSection(&g_lock);
  return out;
}

// __fastcall(this, edx, arg) is exactly what the disassembly shows: ecx holds
// `this`, edx is stored to a local and passed onward, and the function ends
// `ret 4` for a single stack argument.
typedef void (__fastcall *CrewFn)(void *self, void *edx, DWORD arg);
static CrewFn g_crew_orig;

// Does this dword look like one of the values we know the script set?
static const char *known_value(float f)
{
  if (f > 2999.0f && f < 3001.0f)   return "RadarMaxDistance 3000";
  if (f > 1499.0f && f < 1501.0f)   return "RadarMaxDistance 1500 (commander)";
  if (f > 0.2090f && f < 0.2099f)   return "ViewAngle 12 deg in radians";
  if (f > 11.99f  && f < 12.01f)    return "ViewAngle 12 deg";
  if (f > 1.999f  && f < 2.001f)    return "RadarUpdateTime 2.0";
  // CAutoCommander, read out of ZW's Common\AutoCommander.script. Deducing
  // offsets statically was wrong four times on the shooter; searching the live
  // object for values the script sets found them immediately.
  if (f > 3099.0f && f < 3101.0f)   return "RadarMaxDistance 3100 (ZW)";
  if (f > 3.999f  && f < 4.001f)    return "RadarUpdateTime 4.0 (commander)";
  if (f > 129.9f  && f < 130.1f)    return "FrontDanger angle 130";
  if (f > 119.9f  && f < 120.1f)    return "BackDanger angle 120";
  if (f > 29.99f  && f < 30.01f)    return "LastTargetDangerAdd 30";
  if (f > 999.0f  && f < 1001.0f)   return "PreferedTargets distance 1000";
  if (f > 9999.0f && f < 10001.0f)  return "PreferedTargets range max 10000";
  return NULL;
}

static void __fastcall CrewHook(void *self, void *edx, DWORD arg)
{
  g_crew_orig(self, edx, arg);

  EnterCriticalSection(&g_lock);
  g_crew_calls++;
  // The opening burst, then thin right out - this is a per-tick update and the
  // point of this pass is confirmation, not volume.
  // The update bails early most of the time and the range gate sits deep
  // inside it. These are the three flags it tests on the way in - logging them
  // says WHICH gate is closing, rather than leaving it to be guessed:
  //   1004B225  cmp [esi+0x44], edi   je exit
  //   1004B22E  mov al, [esi+0x11c]   test al,al  je  exit   (must be non-zero)
  //   1004B248  mov al, [esi+0x118]   test al,al  jne exit    (must be zero)
  if ((g_crew_calls & 0x7F) == 1) {
    const BYTE *o = (const BYTE *)self;
    // The gating virtual is UI.dll+0x199650, which is nothing but
    //     mov al, [ecx+0x9cd] ; ret
    // on the CTankAutoThingControl at [esi+0x5c]. Read that byte and its
    // neighbours directly: the auto driver / gunner / commander flags should
    // sit together, and whichever bytes track the seat identify themselves.
    DWORD ctl = readable(o + 0x5c, 4) ? *(const DWORD *)(o + 0x5c) : 0;
    if (ctl && readable((void *)(ctl + 0x9C0), 0x20)) {
      const BYTE *c = (const BYTE *)ctl;
      char line[160]; int n = 0;
      for (DWORD k = 0x9C4; k <= 0x9D8; k++)
        n += _snprintf(line + n, sizeof(line) - n, "%s%02X",
                       k == 0x9CD ? "[" : " ", c[k]);
      llog("[CTRL %5I64d] CTankAutoThingControl +0x9C4..+0x9D8: %s"
           "   (the gate reads +0x9CD)", g_crew_calls, line);
    }
    if (readable(o + 0x11c, 4))
      llog("[CREW %5I64d] flags: +0x118 %d (want 0)  +0x11c %d (want non-zero)"
           "  +0x44 %08X  +0xE0 %08X",
           g_crew_calls, o[0x118], o[0x11c],
           *(const DWORD *)(o + 0x44), *(const DWORD *)(o + 0xE0));
  }

  // What ARE the objects this component holds? The update only proceeds when a
  // virtual on [esi+0x5c] returns true, and knowing its class tells us what
  // that test means - a timer, a weapon-ready check, an enable flag. Resolving
  // RTTI at runtime beats guessing, which has been wrong three times today.
  if (g_crew_calls == 1) {
    HMODULE bm = GetModuleHandleA("Behavior.dll");
    const BYTE *o = (const BYTE *)self;
    static const DWORD OFFS[] = { 0x34, 0x5c, 0x60, 0x68, 0xE0, 0xE4 };
    llog("[CREW] classes of the objects this component holds:");
    for (int k = 0; k < 6; k++) {
      DWORD off = OFFS[k];
      if (!readable(o + off, 4)) continue;
      DWORD obj = *(const DWORD *)(o + off);
      if (obj < 0x10000 || !readable((void *)obj, 4)) continue;
      DWORD vt = *(const DWORD *)obj;
      if (!readable((void *)(vt - 4), 4)) { llog("        +0x%02X -> %08X (no vtable)", off, obj); continue; }
      DWORD col = *(const DWORD *)(vt - 4);
      const char *nm = "?";
      if (col > (DWORD)bm && readable((void *)(col + 0x0C), 4)) {
        DWORD td = *(const DWORD *)(col + 0x0C);
        if (readable((void *)(td + 8), 64)) nm = (const char *)(td + 8);
      }
      DWORD slot10 = readable((void *)(vt + 0x28), 4) ? *(const DWORD *)(vt + 0x28) : 0;
      // These vtables live in OTHER modules - Behavior.dll is only one of ten
      // engine DLLs - so resolve the owning module and give an RVA that can be
      // looked up in the right file afterwards.
      char vmod[64] = "?", fmod[64] = "?";
      DWORD vrva = 0, frva = 0;
      MEMORY_BASIC_INFORMATION mbi;
      char path[MAX_PATH];
      if (VirtualQuery((void *)vt, &mbi, sizeof(mbi)) && mbi.AllocationBase &&
          GetModuleFileNameA((HMODULE)mbi.AllocationBase, path, MAX_PATH)) {
        const char *b = last_sep(path)   /* backslash, by code, to keep escapes out of it */;
        lstrcpynA(vmod, b ? b + 1 : path, 63);
        vrva = vt - (DWORD)mbi.AllocationBase;
      }
      if (slot10 && VirtualQuery((void *)slot10, &mbi, sizeof(mbi)) && mbi.AllocationBase &&
          GetModuleFileNameA((HMODULE)mbi.AllocationBase, path, MAX_PATH)) {
        const char *b = last_sep(path)   /* backslash, by code, to keep escapes out of it */;
        lstrcpynA(fmod, b ? b + 1 : path, 63);
        frva = slot10 - (DWORD)mbi.AllocationBase;
      }
      llog("        +0x%02X -> %08X  vtable %s+0x%06X   slot[0x28] = %s+0x%06X",
           off, obj, vmod, vrva, fmod, frva);
    }
  }

  // Once only: confirm the object, then hunt the known values through it.
  if (g_crew_logged == 0)
  {
    g_crew_logged++;
    const BYTE *o = (const BYTE *)self;
    HMODULE beh = GetModuleHandleA("Behavior.dll");
    DWORD want = (DWORD)beh + CREW_VTABLE_RVA, got = 0;
    if (readable(o, 4)) memcpy(&got, o, 4);
    llog("[CREW] this %08X  vtable %08X  expected %08X  %s",
         (DWORD)self, got, want,
         got == want ? "MATCH - right object" : "MISMATCH - wrong object");

    llog("[CREW] searching the first 0x400 bytes for values the script set:");
    int found = 0;
    for (DWORD off = 0; off < 0x400; off += 4) {
      if (!readable(o + off, 4)) break;
      float f; memcpy(&f, o + off, 4);
      const char *what = known_value(f);
      if (what) { llog("        +0x%03X = %10.4f   <- %s", off, f, what); found++; }
    }
    if (!found)
      llog("        nothing found - the values live behind a pointer, so dump "
           "the pointer fields next");

    // Pointers into the heap are the candidates for that indirection.
    llog("[CREW] pointer-looking fields, for following next time:");
    for (DWORD off = 0; off < 0x160; off += 4) {
      if (!readable(o + off, 4)) break;
      DWORD v; memcpy(&v, o + off, 4);
      if (v > 0x00100000 && v < 0x7FFF0000 && (v & 3) == 0 && readable((void *)v, 4))
        llog("        +0x%03X -> %08X", off, v);
    }
  }
  LeaveCriticalSection(&g_lock);
}

// ---------------------------------------------------------------------------
// The range gate's call site.
//
// __thiscall with no stack args: ecx holds the delta vector, the result comes
// back in st(0). Declaring it __fastcall with a dummy second parameter gives
// exactly that, and returning float puts the answer where the caller's
// `fstp [esp+0x1c]` expects it.
// ---------------------------------------------------------------------------

typedef float (__fastcall *VecLenFn)(const float *v, void *edx);
static VecLenFn g_veclen;

// Does this look like a position on this mission's map, whose ground sits near
// 600 m,
// rather than a delta, a normal, or noise?
static bool looks_like_world_pos(const float *v)
{
  const float w = g_terrain.valid() ? g_terrain.world : DEFAULT_WORLD_M;
  return v[0] > 1.0f && v[0] < w &&
         v[1] > 1.0f && v[1] < w &&
         v[2] > -50.0f && v[2] < 2000.0f;
}

// Find the observer and target in the caller's frame by matching their
// difference against the delta we were handed. Self-validating: no other pair
// of world-looking vectors in that window can satisfy the arithmetic.
static bool find_endpoints(const float *v, float *obs, float *tgt)
{
  if (!readable(v, 12)) return false;
  const float dx = v[0], dy = v[1], dz = v[2];
  const BYTE *base = (const BYTE *)v - 0x100;

  for (int i = 0; i < 128; i++) {
    const float *a = (const float *)(base + i * 4);
    if (!readable(a, 12) || !looks_like_world_pos(a)) continue;
    for (int j = 0; j < 128; j++) {
      const float *b = (const float *)(base + j * 4);
      if (i == j || !readable(b, 12) || !looks_like_world_pos(b)) continue;
      if (fabsf((b[0] - a[0]) - dx) < 0.05f &&
          fabsf((b[1] - a[1]) - dy) < 0.05f &&
          fabsf((b[2] - a[2]) - dz) < 0.05f) {
        obs[0] = a[0]; obs[1] = a[1]; obs[2] = a[2];
        tgt[0] = b[0]; tgt[1] = b[1]; tgt[2] = b[2];
        return true;
      }
    }
  }
  return false;
}

static float __fastcall GateProbe(const float *v, void *edx)
{
  float len = g_veclen(v, edx);

  EnterCriticalSection(&g_lock);
  g_gate_calls++;

  // Enforcement. Only ever pushes a candidate OUT of range - never in.
  if (g_gate_enforce && g_ready && g_terrain.valid()) {
    float obs[3], tgt[3];
    if (find_endpoints(v, obs, tgt)) {
      // Both endpoints off the heightfield, as on the AI side: the authored Z
      // is mid-model, not ground contact, so adding an eye height to it would
      // put the gunner a metre and a half too high.
      __int64 tg0 = tick();
      Sight sg = march(&g_terrain, obs[0], obs[1], g_terrain.ground(obs[0], obs[1]) + 2.0f,
                       tgt[0], tgt[1], g_terrain.ground(tgt[0], tgt[1]) + 1.3f);
      g_march_ticks += tick() - tg0;
      g_march_count++;
      if (sg.factor <= 0.0f || frand() > sg.factor) {
        g_gate_denied++;
        if (g_gate_logged < 60) {
          g_gate_logged++;
          llog("[GATE] REFUSED (%7.1f,%7.1f) -> (%7.1f,%7.1f) at %6.0f m, "
               "%s, %.0f%% masked", obs[0], obs[1], tgt[0], tgt[1], len,
               sg.why, (1.0f - sg.factor) * 100.0f);
        }
        LeaveCriticalSection(&g_lock);
        return 1.0e9f;      // beyond any RadarMaxDistance, so it is discarded
      }
    } else {
      g_gate_nopair++;      // could not identify the pair; leave it alone
    }
  }

  if ((g_gate_calls % 2000) == 0)
    llog("--- gate: %I64d checks, %I64d refused, %I64d unmatched",
         g_gate_calls, g_gate_denied, g_gate_nopair);
  if (!g_gate_enforce && g_gate_logged < 24)
  {
    g_gate_logged++;
    float dx = 0, dy = 0, dz = 0;
    if (readable(v, 12)) { dx = v[0]; dy = v[1]; dz = v[2]; }
    llog("[GATE %4I64d] delta (%9.2f,%9.2f,%9.2f)  len %8.2f",
         g_gate_calls, dx, dy, dz, len);

    // The march needs a real world position, and a delta alone will not do.
    // Sweep a window of the caller's stack for anything that reads like one.
    const float *sp = (const float *)((BYTE *)&v - 0x20);
    int found = 0;
    for (int i = 0; i < 64 && found < 6; i++) {
      const float *c = sp + i;
      if (!readable(c, 12)) continue;
      if (looks_like_world_pos(c)) {
        llog("          stack+0x%02X world-ish (%8.1f,%8.1f,%7.1f)",
             i * 4, c[0], c[1], c[2]);
        found++;
      }
    }
    if (!found)
      llog("          no world position on the stack near the call - the "
           "observer's position must come from the component instead");
  }
  LeaveCriticalSection(&g_lock);
  return len;
}

// Patch a CALL instruction to point somewhere else, leaving everything around
// it untouched. Five bytes at one address, so no other caller is affected.
static bool patch_call(BYTE *site, void *dest, void **orig, const char *what)
{
  if (site[0] != 0xE8) { llog("%s: not a call at %08X", what, (DWORD)site); return false; }
  DWORD old_target = (DWORD)(site + 5) + *(DWORD *)(site + 1);
  *orig = (void *)old_target;

  DWORD prot;
  if (!VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &prot)) {
    llog("%s: VirtualProtect failed", what); return false;
  }
  *(DWORD *)(site + 1) = (DWORD)dest - (DWORD)(site + 5);
  VirtualProtect(site, 5, prot, &prot);
  FlushInstructionCache(GetCurrentProcess(), site, 5);
  llog("%s: call at %08X redirected from %08X to %08X",
       what, (DWORD)site, old_target, (DWORD)dest);
  return true;
}

// Both hooks share this shape; only the patch length differs, because each
// target's first whole instructions add up differently.
static bool patch_jump(BYTE *target, int len, void *hook, void **orig,
                       const char *what)
{
  BYTE *tramp = (BYTE *)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE);
  if (!tramp) { llog("%s: VirtualAlloc failed", what); return false; }

  memcpy(tramp, target, len);
  tramp[len] = 0xE9;
  *(DWORD *)(tramp + len + 1) =
      (DWORD)(target + len) - (DWORD)(tramp + len + 5);

  *orig = tramp;                      // publish before the jump goes in

  DWORD old;
  if (!VirtualProtect(target, len, PAGE_EXECUTE_READWRITE, &old)) {
    llog("%s: VirtualProtect failed", what); return false;
  }
  target[0] = 0xE9;
  *(DWORD *)(target + 1) = (DWORD)hook - (DWORD)(target + 5);
  for (int i = 5; i < len; i++) target[i] = 0x90;
  VirtualProtect(target, len, old, &old);
  FlushInstructionCache(GetCurrentProcess(), target, len);

  llog("%s hooked: target %08X  trampoline %08X", what,
       (DWORD)target, (DWORD)tramp);
  return true;
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
  // The ceiling was 500, which was fine while every map was one of REDUX's.
  // ZW's Kursk map paints a THIRD of a 36 km world as forest and then plants
  // 335 trees per square kilometre in it - one per 2985 m2, a tree every 55 m.
  // REDUX's Berezov is 4310 per square kilometre, one per 232 m2. That is a
  // factor of THIRTEEN, so a map like that needs a scale around 1300 and the
  // old ceiling silently clamped it to a quarter of what it needed.
  int pct = GetPrivateProfileIntA("los", "sight_scale", 100, INI_PATH);
  if (pct < 10) pct = 10;
  if (pct > 5000) pct = 5000;
  g_sight_scale = pct / 100.0f;
  GetPrivateProfileStringA("los", "crew", "off", buf, sizeof(buf), INI_PATH);
  g_crew_watch = (_stricmp(buf, "watch") == 0);
  GetPrivateProfileStringA("los", "gate", "off", buf, sizeof(buf), INI_PATH);
  g_gate_enforce = (_stricmp(buf, "los") == 0);

  // clip_cursor: keep the mouse inside the game window on a multi-monitor
  // desktop. Defaults ON - it releases the moment the game loses focus, so it
  // cannot strand the desktop.
  GetPrivateProfileStringA("los", "clip_cursor", "on", buf, sizeof(buf),
                           g_ini_path);
  g_clip_cursor = (_stricmp(buf, "off") != 0 && _stricmp(buf, "0") != 0);
  g_gate_probe = g_gate_enforce || (_stricmp(buf, "probe") == 0);
}

// One file beside the DLL, one install root per line, # for comments. Kept out
// of the game folders deliberately: a file living there would let any install
// authorise itself, which is no rail at all.
static bool install_is_allowed()
{
  FILE *f = fopen(g_allow_path, "r");
  if (!f) {
    llog("no allow list at %s", g_allow_path);
    return false;                       // fail safe: no list, no arming
  }
  char line[MAX_PATH];
  bool ok = false;
  while (!ok && fgets(line, sizeof(line), f)) {
    char *t = line;
    while (*t == ' ' || *t == '\t') t++;
    if (*t == '#' || *t == ';' || *t == '\n' || *t == '\r' || !*t) continue;
    int n = (int)strlen(t);
    while (n > 0 && (t[n-1] == '\n' || t[n-1] == '\r' ||
                     t[n-1] == ' '  || t[n-1] == 92)) t[--n] = 0;
    if (n && _stricmp(t, g_root) == 0) ok = true;
  }
  fclose(f);
  return ok;
}

// Hold the cursor inside the game's own window while the game has focus, and
// let it go the moment it does not - so alt-tab still works and a crash or a
// breakpoint can never leave the desktop with a trapped mouse.
//
// Only windows belonging to THIS process are considered, and the rectangle is
// re-read every pass, so a resolution change or a mode switch is picked up
// without any bookkeeping.
static BOOL CALLBACK pick_window(HWND w, LPARAM lp)
{
  DWORD pid = 0;
  GetWindowThreadProcessId(w, &pid);
  if (pid == GetCurrentProcessId() && IsWindowVisible(w)) {
    RECT r;
    if (GetClientRect(w, &r) && (r.right - r.left) > 320) {
      *(HWND *)lp = w;
      return FALSE;          // first big visible one is the game
    }
  }
  return TRUE;
}

static DWORD WINAPI CursorKeeper(LPVOID)
{
  bool clipped = false;
  for (;;) {
    Sleep(120);
    if (!g_clip_cursor) {
      if (clipped) { ClipCursor(NULL); clipped = false; }
      continue;
    }

    HWND fg = GetForegroundWindow();
    DWORD pid = 0;
    if (fg) GetWindowThreadProcessId(fg, &pid);

    if (fg && pid == GetCurrentProcessId()) {
      HWND target = fg;
      RECT c;
      if (!GetClientRect(target, &c) || (c.right - c.left) < 320) {
        HWND found = NULL;
        EnumWindows(pick_window, (LPARAM)&found);
        if (found) target = found;
      }
      RECT r;
      if (GetClientRect(target, &r)) {
        POINT tl = { r.left, r.top }, br = { r.right, r.bottom };
        ClientToScreen(target, &tl);
        ClientToScreen(target, &br);
        RECT s = { tl.x, tl.y, br.x, br.y };
        ClipCursor(&s);
        clipped = true;
      }
    }
    else if (clipped) {
      // Focus is elsewhere - release immediately.
      ClipCursor(NULL);
      clipped = false;
    }
  }
  return 0;
}

// ---- CAutoCommanderComponent watch -------------------------------------
typedef void (__fastcall *CmdrFn)(void *, void *, DWORD);
static CmdrFn g_cmdr_orig;

static void __fastcall CmdrHook(void *self, void *edx, DWORD arg)
{
  g_cmdr_orig(self, edx, arg);

  EnterCriticalSection(&g_lock);
  g_cmdr_calls++;
  if (g_cmdr_calls == 1 || (g_cmdr_calls & 0x3FF) == 1) {
    const BYTE *o = (const BYTE *)self;
    HMODULE beh = GetModuleHandleA("Behavior.dll");
    DWORD want = (DWORD)beh + CMDR_VTABLE_RVA, got = 0;
    if (readable(o, 4)) memcpy(&got, o, 4);
    // Dump the pointer fields. Whatever this component is handing to the
    // gunner is one of them, and comparing the list between a tick with a
    // target and a tick without will say which.
    char line[200]; int n = 0;
    for (DWORD off = 0xD8; off <= 0xF8 && n < 150; off += 4) {
      DWORD v = readable(o + off, 4) ? *(const DWORD *)(o + off) : 0;
      n += _snprintf(line + n, sizeof(line) - n, " +%02X=%08X", off, v);
    }
    // Once only: walk the object for values the script sets. This is how the
    // shooter's fields were finally pinned down, after two failed attempts to
    // read them out of the property loader.
    if (g_cmdr_calls == 1) {
      llog("[CMDR] scanning the live object for values AutoCommander.script sets:");
      int found = 0;
      for (DWORD off = 0; off < 0x400; off += 4) {
        if (!readable(o + off, 4)) break;
        float f; memcpy(&f, o + off, 4);
        const char *what = known_value(f);
        if (what) { llog("        +0x%03X = %10.4f   <- %s", off, f, what); found++; }
      }
      if (!found)
        llog("        nothing found in the first 0x400 bytes - the values are "
             "behind a pointer, dump the pointer fields next");
    }
    llog("[CMDR %6I64d] this %08X vtable %s  radar %.0f %.0f  |%s",
         g_cmdr_calls, (DWORD)self,
         got == want ? "OK" : "MISMATCH",
         readable(o + 0x154, 4) ? *(const float *)(o + 0x154) : -1.0f,
         readable(o + 0x1CC, 4) ? *(const float *)(o + 0x1CC) : -1.0f,
         line);
  }
  LeaveCriticalSection(&g_lock);
}

// Print both crew vtables side by side. Slot 7 of the shooter's is known to be
// its Update (that is what CREW_RVA is), so if the two tables line up the same
// slot on the commander's is the function to watch. This prints rather than
// assumes, because deducing offsets on this pair has been wrong four times.
static DWORD find_commander_update(HMODULE beh)
{
  const DWORD *vs = (const DWORD *)((BYTE *)beh + CREW_VTABLE_RVA);
  const DWORD *vc = (const DWORD *)((BYTE *)beh + CMDR_VTABLE_RVA);
  if (!readable((void *)vs, 64) || !readable((void *)vc, 64)) {
    llog("[CMDR] vtables not readable - skipping");
    return 0;
  }
  llog("[CMDR] crew vtables, as RVAs in Behavior.dll:");
  llog("        slot   CAutoShooter   CAutoCommander");
  for (int i = 0; i < 12; i++) {
    if (!readable((void *)(vs + i), 4) || !readable((void *)(vc + i), 4)) break;
    DWORD s = vs[i] - (DWORD)beh, c = vc[i] - (DWORD)beh;
    llog("        %2d     +0x%06X      +0x%06X%s", i, s, c,
         (s == CREW_RVA) ? "   <- shooter Update" : "");
  }
  DWORD s7 = vs[UPDATE_SLOT] - (DWORD)beh;
  if (s7 != CREW_RVA) {
    llog("[CMDR] slot %d of the shooter vtable is +0x%06X, not the known "
         "Update +0x%06X - NOT hooking on a guess", UPDATE_SLOT, s7, CREW_RVA);
    return 0;
  }
  return vc[UPDATE_SLOT];
}

static DWORD WINAPI Boot(LPVOID)
{
  // Where are we? The game folder comes from the running executable, and the
  // allow list from beside this DLL.
  char exe[MAX_PATH];
  GetModuleFileNameA(NULL, exe, MAX_PATH);
  lstrcpynA(g_root, exe, MAX_PATH);
  char *slash = last_sep(g_root);       // backslash by code, no escapes
  if (slash) *slash = 0;
  _snprintf(g_log_path, MAX_PATH, "%s\\tvt_los.log", g_root);
  _snprintf(g_ini_path, MAX_PATH, "%s\\tvt_los.ini", g_root);

  char dll[MAX_PATH];
  GetModuleFileNameA(g_self, dll, MAX_PATH);
  slash = last_sep(dll);
  if (slash) *slash = 0;
  _snprintf(g_allow_path, MAX_PATH, "%s\\tvt_los_allow.txt", dll);

  g_log = fopen(LOG_PATH, "w");
  {
    LARGE_INTEGER f;
    QueryPerformanceFrequency(&f);
    g_qpc_freq = f.QuadPart;
  }
  llog("tvt_los_hook attached to %s", exe);
  llog("install root: %s", g_root);

  if (!install_is_allowed()) {
    llog("REFUSING to arm. This install is not listed in %s", g_allow_path);
    llog("Add its folder on a line of its own to opt in. A hook that arms "
         "somewhere unintended is how a good install gets ruined.");
    if (g_log) fclose(g_log);
    g_log = NULL;
    return 0;
  }
  g_tick0 = GetTickCount();
  read_ini();
  if (g_clip_cursor)
    llog("  mouse held inside the game window (clip_cursor = on)");
  llog("mode = %s%s",
       g_mode == MODE_LOS ? "los" : g_mode == MODE_DENY_FAR ? "deny_far" : "watch",
       g_mode == MODE_DENY_FAR ? "" : "");
  if (g_mode == MODE_DENY_FAR)
    llog("  will refuse every sighting beyond %.0f m", g_deny_beyond);
  if (g_mode == MODE_LOS)
    llog("  sight_scale %.2f (dense conifer opaque at %.0f m)",
         g_sight_scale, 15.0f * g_sight_scale);
  if (g_crew_watch)
    llog("  crew = watch (the player's own gunner tick, logging only)");
  if (g_gate_enforce)
    llog("  gate = los (the player's own gunner now needs line of sight)");
  else if (g_gate_probe)
    llog("  gate = probe (the range-gate call site, logging only)");

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

  if (g_gate_probe) {
    BYTE *site = (BYTE *)beh + GATE_CALL_RVA;
    DWORD want = (DWORD)beh + VECLEN_RVA;
    if (readable(site, 5) && site[0] == 0xE8 &&
        (DWORD)(site + 5) + *(DWORD *)(site + 1) == want) {
      patch_call(site, (void *)GateProbe, (void **)&g_veclen,
                 "range gate");
    } else {
      llog("range gate: call site at %08X is not the expected call to %08X "
           "- NOT patching", (DWORD)site, want);
    }
  }

  if (g_crew_watch) {
    // push -1 ; push imm32  = 7 bytes, one clean boundary. The pushed value is
    // relocated at load time and the trampoline copies the LIVE bytes, so it
    // carries the fixed-up address.
    BYTE *crew = (BYTE *)beh + CREW_RVA;
    static const BYTE CREW_EXPECT[3] = { 0x6A, 0xFF, 0x68 };
    if (readable(crew, 8) && memcmp(crew, CREW_EXPECT, 3) == 0) {
      llog("crew gunner tick at %08X, prologue verified", (DWORD)crew);
      patch_jump(crew, 7, (void *)CrewHook, (void **)&g_crew_orig,
                 "CAutoShooterComponent::Update");
    } else {
      llog("crew prologue mismatch at %08X - NOT patching", (DWORD)crew);
    }
  }
  // The commander half. Watch only - it is resolved from the vtable, its
  // prologue is checked against the same 7-byte pattern the shooter's Update
  // had, and if either test fails nothing is patched.
  if (g_crew_watch) {
    DWORD upd = find_commander_update(beh);
    if (upd) {
      BYTE *c = (BYTE *)upd;
      static const BYTE EXPECT[3] = { 0x6A, 0xFF, 0x68 };
      llog("[CMDR] CAutoCommanderComponent::Update at %08X (+0x%06X)",
           upd, upd - (DWORD)beh);
      if (readable(c, 8) && memcmp(c, EXPECT, 3) == 0) {
        patch_jump(c, 7, (void *)CmdrHook, (void **)&g_cmdr_orig,
                   "CAutoCommanderComponent::Update");
      } else {
        llog("[CMDR] prologue is %02X %02X %02X, not the expected %02X %02X "
             "%02X - NOT patching", c[0], c[1], c[2],
             EXPECT[0], EXPECT[1], EXPECT[2]);
      }
    }
  }

  if (g_mode == MODE_LOS)
    CreateThread(NULL, 0, MissionWatcher, NULL, 0, NULL);
  if (g_clip_cursor)
    CreateThread(NULL, 0, CursorKeeper, NULL, 0, NULL);
  return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID)
{
  if (reason == DLL_PROCESS_ATTACH) {
    g_self = h;
    DisableThreadLibraryCalls(h);
    InitializeCriticalSection(&g_lock);
    CreateThread(NULL, 0, Boot, NULL, 0, NULL);
  }
  return TRUE;
}
