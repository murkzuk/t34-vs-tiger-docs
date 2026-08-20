// Mission terrain for the LOS march: ground heightfield + vegetation zones.
//
// Everything here mirrors canopy_los.py, which was validated against the
// missions on disk and then against live engine positions. The conventions are
// awkward and each one cost a debugging session, so they are restated where
// they are used rather than assumed:
//
//   - hmap.raw is 2049x2049 uint16 LE stored FLIPPED: row 0 is world y = MAX.
//     Height = raw * 0.07.
//   - The zone bitmaps are the OPPOSITE: row 0 is world y = 0, no flip,
//     despite a positive BMP height field which by spec means bottom-up.
//   - The world is NOT a fixed size. Each mission folder carries its own
//     WorldMatricies.script with MatrixWidth in metres, and the shipped
//     missions run 9000, 12000, 18000, 20002 and 36000. Assuming 9000 puts
//     every lookup in the wrong place on the larger maps, silently. On a
//     9000 m map a 1024 zone cell is 8.789 m and a 2049 height sample 4.395 m;
//     on any other map those scale with it.
//
// The DLL works out which mission is loaded by itself - see identify() - so
// there is nothing to configure and nothing to keep in step with the game.

#pragma once
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

// Only a fallback, for a mission folder with no WorldMatricies.script of its
// own. It matches CWorldMatrices::MatrixWidth in Scripts\Common, the value a
// mission inherits when it overrides nothing. Every shipped mission does
// override it, so this should never be the value actually used.
static const float DEFAULT_WORLD_M = 10000.0f;

// Pull MatrixWidth out of a mission's WorldMatricies.script. Text search
// rather than a parser: the line is always of the form
//   final static float MatrixWidth  = 18000.0; // meters
// and a real parser for this language does not exist outside the engine.
static float read_world_size(const char *folder)
{
  char p[MAX_PATH];
  _snprintf(p, MAX_PATH, "%s\\WorldMatricies.script", folder);
  FILE *f = fopen(p, "rb");
  if (!f) return 0.0f;
  char buf[8192];
  size_t n = fread(buf, 1, sizeof(buf) - 1, f);
  fclose(f);
  buf[n] = 0;
  const char *k = strstr(buf, "MatrixWidth");
  if (!k) return 0.0f;
  const char *eq = strchr(k, '=');
  if (!eq) return 0.0f;
  float v = (float)atof(eq + 1);
  // A plausible map is between a hamlet and the biggest thing the engine
  // ships. Anything outside that is a misparse, and silently using it would
  // be worse than falling back.
  if (v < 500.0f || v > 100000.0f) return 0.0f;
  return v;
}
static const float HEIGHT_FACTOR = 0.07f;

struct Veg {
  float canopy;   // metres, treetop height above ground
  float sight;    // metres, the e-folding depth: after this much vegetation
                  // roughly 63% of the line is obscured, after 3x it is 95%.
                  // NOT a hard budget - see march().
};

// Zone code -> canopy height and metres-of-sight-before-opaque.
//
// CANOPY HEIGHTS are the engine's own: every stock Terrain.script registers a
// 17 m vertical forest for Forest01 (zone 11), and the rest are weighted means
// of TreeSize in BaseSTTree.script over each zone's species mix.
//
// SIGHT DISTANCES are calibrated, not derived, and are e-folding depths for
// Beer-Lambert extinction, not hard budgets. They were recalibrated twice
// against play. The first set was seeded from intuition about forest
// visibility and came out about three times too generous: an observer 132 m
// away in the open saw a tank 13 m inside a dense conifer stand with only 29%
// masking. BaseForest places CMiddleForest at MinDistance 2.0 m with 90% of
// the mix as real trees; even at 0.6 m of effective blocking width per trunk
// that is roughly 0.15 extinction per metre, so 13 m in should be most of the
// way to concealed. Scaled by a third throughout.
//
// g_sight_scale (sight_scale in the ini) multiplies all of them at load, so
// this can be tuned between runs without a rebuild.
extern float g_sight_scale;

static inline const Veg *veg_for(int zone)
{
  switch (zone) {
    // Bush01..Bush04 are NOT bushes. BaseForest.script's CellTemplates maps
    // them to the variable-density forest templates, so they are woodland:
    //   27 CExtraLightForest  28 CLightForest  29 CMiddleForest  30 CLargeForest
    // They were missing from this table entirely, which silently treated real
    // forest as open ground - Campaign_1/Mission_3 has units standing in 27.
    case 27: { static const Veg v = {    3.2f,   60.0f }; return &v; }  // scattered holly, 45% occupied
    case 28: { static const Veg v = {    4.6f,   44.0f }; return &v; }  // as Forest02
    case 29: { static const Veg v = {  20.0f,   12.0f }; return &v; }  // as Forest01
    case 30: { static const Veg v = {  23.9f,   24.0f }; return &v; }  // as Forest04
    case 11: { static const Veg v = {  17.0f,   12.0f }; return &v; }  // Forest01, dense conifer
    case 12: { static const Veg v = {    4.6f,   44.0f }; return &v; }  // Forest02, scrub
    case 13: { static const Veg v = {  17.0f,   32.0f }; return &v; }  // Forest03, live oak
    case 14: { static const Veg v = {  23.9f,   24.0f }; return &v; }  // Forest04, tall but half empty
    case 20: { static const Veg v = {  28.0f,   56.0f }; return &v; }  // RoadForest
    case 49: { static const Veg v = {    5.0f,   20.0f }; return &v; }
    case 50: { static const Veg v = {    3.5f,   24.0f }; return &v; }
    case 51: { static const Veg v = {    3.0f,   28.0f }; return &v; }
    case 52: { static const Veg v = {  28.0f, 112.0f }; return &v; }
    case 60: case 61: { static const Veg v = {  8.0f,   32.0f }; return &v; }
    case 62: { static const Veg v = {    7.5f,   36.0f }; return &v; }
  }
  return NULL;
}

struct Terrain
{
  unsigned short *h;   // hmap, flipped rows
  int   hdim;
  float hcell;

  unsigned char *z;    // zone bitmap pixels, top-down
  int   zw, zh, zstride;
  float zcell;

  float world;         // metres across, from the mission's MatrixWidth

  char  name[MAX_PATH];

  Terrain() : h(0), hdim(0), hcell(0), z(0), zw(0), zh(0), zstride(0), zcell(0),
              world(DEFAULT_WORLD_M)
  { name[0] = 0; }

  bool valid() const { return h && z; }

  // Bilinear. Nearest-neighbour on a 4.4 m grid builds staircase ridges that
  // block sight lines which are actually open.
  float ground(float x, float y) const
  {
    float fx = x / hcell;
    float fy = (world - y) / hcell;            // flipped: row 0 is world y = MAX
    int ix = (int)fx, iy = (int)fy;
    if (ix < 0) ix = 0;
    if (iy < 0) iy = 0;
    if (ix > hdim - 2) ix = hdim - 2;
    if (iy > hdim - 2) iy = hdim - 2;
    float tx = fx - ix, ty = fy - iy;
    const unsigned short *r0 = h + (size_t)iy * hdim + ix;
    const unsigned short *r1 = r0 + hdim;
    float top = r0[0] + (r0[1] - r0[0]) * tx;
    float bot = r1[0] + (r1[1] - r1[0]) * tx;
    return (top + (bot - top) * ty) * HEIGHT_FACTOR;
  }

  int zone(float x, float y) const
  {
    int cx = (int)(x / zcell), cy = (int)(y / zcell);
    if (cx < 0 || cy < 0 || cx >= zw || cy >= zh) return 0;
    return z[(size_t)cy * zstride + cx];
  }
};

// Find the mission's heightfield. It is NOT always <folder>\hmap.raw:
// WorldMatricies.script declares an ImageFileName per layer, relative to the
// game root and with forward slashes, and ZW's missions use names like
// hmap1.raw. A mission may also point at another mission's terrain, which is
// exactly what sharing one map between missions would rely on.
//
// The height layer is the first .raw that is not the water layer - hwater by
// convention in every mission on disk, in both builds.
static bool find_height_file(const char *folder, char *out)
{
  char p[MAX_PATH];
  _snprintf(p, MAX_PATH, "%s\\WorldMatricies.script", folder);
  FILE *f = fopen(p, "rb");
  char rel[MAX_PATH] = "";
  if (f) {
    char buf[16384];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = 0;
    const char *k = buf;
    while ((k = strstr(k, "ImageFileName")) != NULL) {
      const char *q1 = strchr(k, '"');
      if (!q1) break;
      const char *q2 = strchr(q1 + 1, '"');
      if (!q2) break;
      size_t len = (size_t)(q2 - q1 - 1);
      if (len > 0 && len < MAX_PATH) {
        char val[MAX_PATH];
        memcpy(val, q1 + 1, len);
        val[len] = 0;
        // basename, for the .raw and hwater tests
        const char *base = val;
        for (const char *c = val; *c; c++)
          if (*c == 47 || *c == 92) base = c + 1;
        size_t bl = strlen(base);
        bool is_raw = bl > 4 && _stricmp(base + bl - 4, ".raw") == 0;
        if (is_raw && _strnicmp(base, "hwater", 6) != 0) {
          strncpy(rel, val, MAX_PATH - 1);
          break;
        }
      }
      k = q2 + 1;
    }
  }

  if (rel[0]) {
    // Forward slashes to backslashes.
    for (char *c = rel; *c; c++) if (*c == 47) *c = 92;

    // The path is relative to the GAME ROOT, and the mission folder is
    // <root>\Missions\... - so cut the folder at its "\Missions\" to
    // recover the root rather than requiring the caller to pass it.
    char root[MAX_PATH];
    strncpy(root, folder, MAX_PATH - 1);
    root[MAX_PATH - 1] = 0;
    char *cut = NULL;
    for (char *c = root; *c; c++)
      if (*c == 92 && _strnicmp(c, "\\Missions\\", 10) == 0) cut = c;
    if (cut) {
      *cut = 0;
      _snprintf(out, MAX_PATH, "%s\\%s", root, rel);
      if (GetFileAttributesA(out) != INVALID_FILE_ATTRIBUTES) return true;
    }

    // Declared but not where it said. Try its basename in the mission folder,
    // which covers a mission moved without its script being updated.
    const char *base = rel;
    for (const char *c = rel; *c; c++) if (*c == 92) base = c + 1;
    _snprintf(out, MAX_PATH, "%s\\%s", folder, base);
    if (GetFileAttributesA(out) != INVALID_FILE_ATTRIBUTES) return true;
  }

  // Nothing declared, or nothing found: the original assumption, which is
  // right for every stock REDUX mission.
  _snprintf(out, MAX_PATH, "%s\\hmap.raw", folder);
  return GetFileAttributesA(out) != INVALID_FILE_ATTRIBUTES;
}

// Read only a handful of height samples without loading the file, so every
// candidate mission can be tested cheaply during identification.
static bool probe_heights(const char *hmap, float world,
                          const float *xs, const float *ys,
                          int n, float *out)
{
  FILE *f = fopen(hmap, "rb");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long bytes = ftell(f);
  int dim = 0;
  while ((long)dim * dim * 2 < bytes) dim++;
  if ((long)dim * dim * 2 != bytes) { fclose(f); return false; }
  float cell = world / (dim - 1);

  for (int i = 0; i < n; i++) {
    int ix = (int)(xs[i] / cell);
    int iy = (int)((world - ys[i]) / cell);
    if (ix < 0) ix = 0; if (ix > dim - 1) ix = dim - 1;
    if (iy < 0) iy = 0; if (iy > dim - 1) iy = dim - 1;
    unsigned short v = 0;
    fseek(f, ((long)iy * dim + ix) * 2, SEEK_SET);
    if (fread(&v, 2, 1, f) != 1) { fclose(f); return false; }
    out[i] = v * HEIGHT_FACTOR;
  }
  fclose(f);
  return true;
}

static unsigned char *load_bmp8(const char *path, int *w, int *h, int *stride)
{
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;
  unsigned char hdr[54];
  if (fread(hdr, 1, 54, f) != 54) { fclose(f); return NULL; }
  DWORD off = *(DWORD *)(hdr + 10);
  int W = *(int *)(hdr + 18), H = *(int *)(hdr + 22);
  if (H < 0) H = -H;
  int st = (W + 3) / 4 * 4;
  unsigned char *px = (unsigned char *)malloc((size_t)st * H);
  if (!px) { fclose(f); return NULL; }
  fseek(f, off, SEEK_SET);
  if (fread(px, 1, (size_t)st * H, f) != (size_t)st * H) {
    free(px); fclose(f); return NULL;
  }
  fclose(f);
  *w = W; *h = H; *stride = st;
  return px;
}

static void free_terrain(Terrain *t)
{
  if (t->h) { free(t->h); t->h = NULL; }
  if (t->z) { free(t->z); t->z = NULL; }
  t->name[0] = 0;
}

static bool load_terrain(Terrain *t, const char *folder, const char *zonebmp)
{
  char p[MAX_PATH];
  if (!find_height_file(folder, p)) return false;
  FILE *f = fopen(p, "rb");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long bytes = ftell(f);
  fseek(f, 0, SEEK_SET);
  int dim = 0;
  while ((long)dim * dim * 2 < bytes) dim++;
  if ((long)dim * dim * 2 != bytes) { fclose(f); return false; }
  t->h = (unsigned short *)malloc(bytes);
  if (!t->h) { fclose(f); return false; }
  fread(t->h, 1, bytes, f);
  fclose(f);
  t->hdim = dim;

  float w = read_world_size(folder);
  t->world = (w > 0.0f) ? w : DEFAULT_WORLD_M;
  t->hcell = t->world / (dim - 1);

  t->z = load_bmp8(zonebmp, &t->zw, &t->zh, &t->zstride);
  if (!t->z) { free(t->h); t->h = NULL; return false; }
  t->zcell = t->world / t->zw;
  strncpy(t->name, folder, MAX_PATH - 1);
  return true;
}

// Result of a sight test. Not a bool: the engine's model multiplies visibility
// by each modifier's factor, so partial masking can be expressed honestly as a
// fraction rather than rounded to blocked/clear. Hull-down should be hard to
// spot, not impossible.
struct Sight {
  float factor;
  const char *why;
  float lost_at;
  float veg_metres;   // how much vegetation the line actually crossed
  int   veg_zone;     // the zone code that cost the most of the sight budget
};

// A tank is about three metres tall. The exposed fraction of that is what
// terrain masking returns, so a turret over a crest stays shootable.
static const float TARGET_HEIGHT = 3.0f;

// Start the march clear of the observer's own hull. Ground within a few metres
// is the tank's own footprint and the heightfield's interpolation of it; a
// 20 cm artefact there would otherwise dominate the required-height maximum,
// because dividing by a tiny fraction-along amplifies it enormously.
static const float MARCH_START = 12.0f;

static Sight march(const Terrain *t, float ax, float ay, float az,
                   float bx, float by, float bz)
{
  Sight s = { 1.0f, "clear", 0.0f, 0.0f, 0 };
  float dx = bx - ax, dy = by - ay;
  float flat = (float)sqrt(dx * dx + dy * dy);
  if (flat < 1.0f) return s;

  float step = t->zcell * 0.5f;             // two samples per zone cell
  int n = (int)(flat / step);
  if (n < 2) return s;

  float inv = 1.0f / flat;
  float ux = dx * inv, uy = dy * inv, dz = bz - az;
  float depth_veg = 0.0f;      // accumulated optical depth through vegetation
  float worst = 0.0f;
  // The lowest height at the target's end that would clear every intervening
  // point so far. Starts below any ground, so "nothing in the way" survives.
  float need = -1e9f;

  for (int i = 1; i < n; i++) {
    float d = i * step;
    float x = ax + ux * d, y = ay + uy * d;
    float rz = az + dz * (d * inv);
    float g = t->ground(x, y);

    // How high would the target have to stand for the line to clear THIS
    // point? Keep the worst such demand along the way. This replaces a
    // single ray to the hull centre with the actual silhouette question.
    if (d >= MARCH_START) {
      float tt = d * inv;
      float req = az + (g - az) / tt;
      if (req > need) { need = req; s.lost_at = d; }
    }

    int zc = t->zone(x, y);
    const Veg *v = veg_for(zc);
    if (v && rz < g + v->canopy) {
      // Record what the vegetation actually cost, so the sight-through
      // distances - the one quantity here that was tuned rather than read out
      // of the game's own data - can be judged against real engagements
      // instead of adjusted by feel.
      // Beer-Lambert. The previous version subtracted step/sight from a
      // budget and blocked at zero, which is a cliff: a line clipping two
      // forest cells was as opaque as one through half a kilometre of trees.
      // Accumulate optical depth instead and take the exponential at the end.
      float spend = step / (v->sight * g_sight_scale);
      depth_veg += spend;
      s.veg_metres += step;
      if (spend > worst) { worst = spend; s.veg_zone = zc; }
      if (depth_veg > 6.0f) {          // e^-6 is 0.25%, call it opaque
        s.factor = 0.0f; s.why = "foliage"; s.lost_at = d;
        return s;
      }
    }
  }
  // Terrain: how much of the target's height stands above the worst demand.
  // Fully exposed, a turret only, or nothing - on a continuum.
  float exposed = (bz - 1.3f) + TARGET_HEIGHT - need;   // bz is hull centre
  float terrain_factor = exposed / TARGET_HEIGHT;
  if (terrain_factor > 1.0f) terrain_factor = 1.0f;
  if (terrain_factor < 0.0f) terrain_factor = 0.0f;
  if (terrain_factor < 1.0f) { s.factor = terrain_factor; s.why = "terrain"; }
  if (terrain_factor <= 0.0f) return s;

  // Vegetation multiplies whatever the ground left standing.
  if (depth_veg > 0.0f) {
    float pass = (float)exp(-depth_veg);
    s.factor *= pass;
    if (pass < terrain_factor) s.why = "foliage";
  }
  return s;
}
