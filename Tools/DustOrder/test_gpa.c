// test_gpa - prove the GetProcAddress interception fires, WITHOUT launching the game.
//
// Mimics what the engine does: load dust_order.dll, then resolve Direct3DCreate9
// dynamically out of d3d9.dll. If the IAT hook works, dust_order.log will contain
// the "[intercepted]" line and the returned pointer will point into dust_order.dll.
//
//   test_gpa        load the probe AND both d3d9 DLLs
//   test_gpa p      load ONLY the probe (isolates whose crash it is at shutdown)

#include <windows.h>
#include <stdio.h>

int main(int argc, char **argv)
{
  int probe_only = (argc > 1 && argv[1][0] == 'p');

  HMODULE probe = LoadLibraryA("K:\\TvTDeepseek\\dust_order\\dust_order.dll");
  printf("dust_order.dll      : %p\n", (void *)probe);
  if (!probe) { printf("  FAILED to load probe (err %lu)\n", GetLastError()); return 1; }

  if (probe_only) {
    printf("probe-only: no d3d9 loaded at all\n");
    FreeLibrary(probe);
    printf("done\n");
    return 0;
  }

  const char *paths[2];
  paths[0] = "M:\\T34vsTiger\\d3d9.dll";
  paths[1] = "C:\\Windows\\SysWOW64\\d3d9.dll";

  for (int i = 0; i < 2; i++) {
    HMODULE d3d = LoadLibraryA(paths[i]);
    printf("%-28s: %p%s\n", paths[i], (void *)d3d, d3d ? "" : " (load failed)");
    if (!d3d) continue;
    FARPROC p = GetProcAddress(d3d, "Direct3DCreate9");
    printf("  Direct3DCreate9   : %p\n", (void *)p);
    FARPROC q = GetProcAddress(d3d, "D3DPERF_EndEvent");   /* control - must pass through */
    printf("  D3DPERF_EndEvent  : %p  (control)\n", (void *)q);
  }

  FreeLibrary(probe);   /* triggers the DETACH dump */
  printf("done - now read dust_order.log\n");
  return 0;
}
