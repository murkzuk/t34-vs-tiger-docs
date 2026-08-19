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
//   - World is 9000 x 9000 m, so a 1024 zone cell is 8.789 m and a 2049 height
//     sample is 4.395 m.
//
// The DLL works out which mission is loaded by itself - see identify() - so
// there is nothing to configure and nothing to keep in step with the game.

#pragma once
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const float WORLD_M = 9000.0f;
static const float HEIGHT_FACTOR = 0.07f;

struct Veg { float canopy; float sight; };

// Zone code -> canopy height and metres-of-sight-before-opaque.
//
// CANOPY HEIGHTS are the engine's own: every stock Terrain.script registers a
// 17 m vertical forest for Forest01 (zone 11), and the rest are weighted means
// of TreeSize in BaseSTTree.script over each zone's species mix.
//
// SIGHT DISTANCES are calibrated, not derived, and were recalibrated once
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
    case 27: { static const Veg v = {    3.2f,  75.0f }; return &v; }  // scattered holly, 45% occupied
    case 28: { static const Veg v = {    4.6f,  55.0f }; return &v; }  // as Forest02
    case 29: { static const Veg v = {  20.0f,  15.0f }; return &v; }  // as Forest01
    case 30: { static const Veg v = {  23.9f,  30.0f }; return &v; }  // as Forest04
    case 11: { static const Veg v = {  17.0f,  15.0f }; return &v; }  // Forest01, dense conifer
    case 12: { static const Veg v = {    4.6f,  55.0f }; return &v; }  // Forest02, scrub
    case 13: { static const Veg v = {  17.0f,  40.0f }; return &v; }  // Forest03, live oak
    case 14: { static const Veg v = {  23.9f,  30.0f }; return &v; }  // Forest04, tall but half empty
    case 20: { static const Veg v = {  28.0f,  70.0f }; return &v; }  // RoadForest
    case 49: { static const Veg v = {    5.0f,  25.0f }; return &v; }
    case 50: { static const Veg v = {    3.5f,  30.0f }; return &v; }
    case 51: { static const Veg v = {    3.0f,  35.0f }; return &v; }
    case 52: { static const Veg v = {  28.0f, 140.0f }; return &v; }
    case 60: case 61: { static const Veg v = {  8.0f,  40.0f }; return &v; }
    case 62: { static const Veg v = {    7.5f,  45.0f }; return &v; }
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

  char  name[MAX_PATH];

  Terrain() : h(0), hdim(0), hcell(0), z(0), zw(0), zh(0), zstride(0), zcell(0)
  { name[0] = 0; }

  bool valid() const { return h && z; }

  // Bilinear. Nearest-neighbour on a 4.4 m grid builds staircase ridges that
  // block sight lines which are actually open.
  float ground(float x, float y) const
  {
    float fx = x / hcell;
    float fy = (WORLD_M - y) / hcell;          // flipped: row 0 is world y = MAX
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

// Read only a handful of height samples without loading the file, so every
// candidate mission can be tested cheaply during identification.
static bool probe_heights(const char *hmap, const float *xs, const float *ys,
                          int n, float *out)
{
  FILE *f = fopen(hmap, "rb");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long bytes = ftell(f);
  int dim = 0;
  while ((long)dim * dim * 2 < bytes) dim++;
  if ((long)dim * dim * 2 != bytes) { fclose(f); return false; }
  float cell = WORLD_M / (dim - 1);

  for (int i = 0; i < n; i++) {
    int ix = (int)(xs[i] / cell);
    int iy = (int)((WORLD_M - ys[i]) / cell);
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

static bool load_terrain(Terrain *t, const char *folder, const char *zonebmp)
{
  char p[MAX_PATH];
  _snprintf(p, MAX_PATH, "%s\\hmap.raw", folder);
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
  t->hcell = WORLD_M / (dim - 1);

  t->z = load_bmp8(zonebmp, &t->zw, &t->zh, &t->zstride);
  if (!t->z) { free(t->h); t->h = NULL; return false; }
  t->zcell = WORLD_M / t->zw;
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
  float budget = 1.0f;
  float worst = 0.0f;

  for (int i = 1; i < n; i++) {
    float d = i * step;
    float x = ax + ux * d, y = ay + uy * d;
    float rz = az + dz * (d * inv);
    float g = t->ground(x, y);

    if (rz < g) {
      // How far below the crest the line runs decides how much of the target
      // is masked. A target 1.3 m tall hidden by 1.3 m of ground is gone; by
      // 0.3 m it is a turret showing over a rise, and still shootable.
      float depth = g - rz;
      float f = 1.0f - depth / 1.3f;
      s.factor = f > 0.0f ? f : 0.0f;
      s.why = "terrain";
      s.lost_at = d;
      if (s.factor <= 0.0f) return s;
      continue;
    }

    int zc = t->zone(x, y);
    const Veg *v = veg_for(zc);
    if (v && rz < g + v->canopy) {
      // Record what the vegetation actually cost, so the sight-through
      // distances - the one quantity here that was tuned rather than read out
      // of the game's own data - can be judged against real engagements
      // instead of adjusted by feel.
      float spend = step / (v->sight * g_sight_scale);
      budget -= spend;
      s.veg_metres += step;
      if (spend > worst) { worst = spend; s.veg_zone = zc; }
      if (budget <= 0.0f) {
        s.factor = 0.0f; s.why = "foliage"; s.lost_at = d;
        return s;
      }
    }
  }
  if (budget < s.factor) { s.factor = budget; s.why = "foliage"; }
  return s;
}
