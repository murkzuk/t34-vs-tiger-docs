// Offline check of terrain.h, so bugs are found here rather than by burning a
// game run. Loads a mission the same way the DLL does and prints ground
// heights, zone codes and march verdicts for comparison against canopy_los.py.
//
//   test_terrain.exe <mission_dir> [ax ay bx by]
//
// The DLL and this share terrain.h verbatim: if the numbers here match the
// Python, the DLL's copy is right too.

#include <stdio.h>
#include "terrain.h"

// terrain.h declares this; the DLL defines it. The test harness needs its
// own copy so it can be linked standalone.
float g_sight_scale = 1.0f;

int main(int argc, char **argv)
{
  const char *dir = argc > 1 ? argv[1]
      : "M:\\TvT_INJECT_SANDBOX\\Missions\\Campaign_1\\Mission_2";

  char pat[MAX_PATH], zbmp[MAX_PATH] = "";
  _snprintf(pat, MAX_PATH, "%s\\TerrainZone*.bmp", dir);
  WIN32_FIND_DATAA fd;
  HANDLE h = FindFirstFileA(pat, &fd);
  if (h == INVALID_HANDLE_VALUE) { printf("no TerrainZone bmp in %s\n", dir); return 1; }
  _snprintf(zbmp, MAX_PATH, "%s\\%s", dir, fd.cFileName);
  FindClose(h);

  Terrain t;
  if (!load_terrain(&t, dir, zbmp)) { printf("load failed\n"); return 1; }
  printf("%s\n  hmap %dx%d cell %.4f   zones %dx%d cell %.4f stride %d\n",
         dir, t.hdim, t.hdim, t.hcell, t.zw, t.zh, t.zcell, t.zstride);

  // Spot heights and zones, to be diffed against the Python.
  static const float PX[] = { 4689.0f, 4581.4f, 5562.4f, 4731.1f, 500.0f, 8500.0f };
  static const float PY[] = { 3226.1f, 3804.1f, 3211.0f, 3165.1f, 500.0f, 8500.0f };
  printf("\n  %-22s %10s %6s\n", "position", "ground", "zone");
  for (int i = 0; i < 6; i++)
    printf("  (%7.1f,%7.1f) %10.3f %6d\n",
           PX[i], PY[i], t.ground(PX[i], PY[i]), t.zone(PX[i], PY[i]));

  float ax = 5562.4f, ay = 3211.0f, bx = 4731.1f, by = 3165.1f;
  if (argc > 5) {
    ax = (float)atof(argv[2]); ay = (float)atof(argv[3]);
    bx = (float)atof(argv[4]); by = (float)atof(argv[5]);
  }
  Sight s = march(&t, ax, ay, t.ground(ax, ay) + 2.0f,
                  bx, by, t.ground(bx, by) + 1.3f);
  printf("\n  march (%.1f,%.1f) -> (%.1f,%.1f):  factor %.3f  %s  at %.0f m\n",
         ax, ay, bx, by, s.factor, s.why, s.lost_at);
  return 0;
}
