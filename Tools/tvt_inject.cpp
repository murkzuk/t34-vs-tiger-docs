// tvt_inject.exe - launches the sandboxed game with tvt_probe.dll loaded.
//
// Starts the target suspended and injects before any engine code runs, so the
// probe is resident in time to watch Behavior.dll arrive. Refuses to run
// against anything outside the sandbox.

#include <windows.h>
#include <stdio.h>
#include <string.h>

// Last path separator, either kind - a path may arrive with forward slashes
// and looking for only one of them silently yields the wrong folder.
static char *last_sep(char *p)
{
  char *a = strrchr(p, 92);   // backslash, by code, to keep escapes out
  char *b = strrchr(p, 47);      // forward slash
  return (a > b) ? a : b;
}

// The allow list lives beside the DLL being injected, so the injector and the
// DLL agree without either of them hardcoding an install path.
static bool install_is_allowed(const char *exe, const char *dll, char *root_out)
{
  char root[MAX_PATH];
  lstrcpynA(root, exe, MAX_PATH);
  char *slash = last_sep(root);          // backslash by code, no escapes
  if (slash) *slash = 0;
  lstrcpynA(root_out, root, MAX_PATH);

  char allow[MAX_PATH];
  lstrcpynA(allow, dll, MAX_PATH);
  slash = last_sep(allow);
  if (slash) *slash = 0;
  strncat(allow, "\\tvt_los_allow.txt", MAX_PATH - strlen(allow) - 1);

  FILE *f = fopen(allow, "r");
  if (!f) {
    printf("REFUSED: no allow list at %s\n", allow);
    return false;                            // fail safe
  }
  char line[MAX_PATH];
  bool ok = false;
  while (!ok && fgets(line, sizeof(line), f)) {
    char *t = line;
    while (*t == ' ' || *t == 9) t++;
    if (*t == 35 || *t == 59 || *t == 10 || *t == 13 || !*t) continue;
    int n = (int)strlen(t);
    while (n > 0 && (t[n-1] == 10 || t[n-1] == 13 || t[n-1] == 32 || t[n-1] == 92))
      t[--n] = 0;
    if (n && _stricmp(t, root) == 0) ok = true;
  }
  fclose(f);
  if (!ok)
    printf("REFUSED: %s is not listed in %s\n"
           "  Add it on a line of its own to opt in.\n", root, allow);
  return ok;
}

int main(int argc, char **argv)
{
  const char *exe = (argc > 1) ? argv[1]
                  : "M:\\TvT_INJECT_SANDBOX\\TvsT_fullLOD_HARD_4GB.exe";
  // MULTIPLE DLLs. Every argument after the exe is a DLL to inject, in order.
  // The engine hooks are independent - line of sight patches Behavior.dll, the
  // map cache patches Objects.dll - so there is no reason to make the user
  // choose between them, and one injector call can carry both.
  const char *dlls[8];
  int ndll = 0;
  for (int i = 2; i < argc && ndll < 8; i++) dlls[ndll++] = argv[i];
  if (ndll == 0) dlls[ndll++] = "K:\\tvt_probe\\tvt_probe.dll";
  const char *dll = dlls[0];   // the first one owns the allow-list folder

  for (int i = 0; i < ndll; i++) {
    if (GetFileAttributesA(dlls[i]) == INVALID_FILE_ATTRIBUTES) {
      printf("ERROR: DLL not found: %s\n", dlls[i]);
      return 3;
    }
  }
  // Opt-in rail. The DLL checks the same list again on the other side.
  // Opt-in rail, checked PER DLL against the allow list beside THAT DLL, so
  // each one still has to authorise itself. Every DLL checks the same list
  // again on its own side.
  char root[MAX_PATH];
  for (int i = 0; i < ndll; i++)
    if (!install_is_allowed(exe, dlls[i], root))
      return 2;

  char dir[MAX_PATH];
  strncpy(dir, exe, MAX_PATH - 1);
  dir[MAX_PATH - 1] = 0;
  char *slash = strrchr(dir, '\\');
  if (slash) *slash = 0;

  printf("target : %s\n", exe);
  for (int i = 0; i < ndll; i++)
    printf("dll %d  : %s\n", i + 1, dlls[i]);
  printf("workdir: %s\n\n", dir);

  STARTUPINFOA si;
  PROCESS_INFORMATION pi;
  memset(&si, 0, sizeof(si));
  si.cb = sizeof(si);
  memset(&pi, 0, sizeof(pi));

  if (!CreateProcessA(exe, NULL, NULL, NULL, FALSE,
                      CREATE_SUSPENDED, NULL, dir, &si, &pi)) {
    printf("CreateProcess failed: %lu\n", GetLastError());
    return 4;
  }
  printf("launched suspended, pid=%lu\n", pi.dwProcessId);

  // kernel32 sits at the same base in every process of this architecture,
  // so our LoadLibraryA address is valid in the target too.
  HMODULE k32 = GetModuleHandleA("kernel32.dll");
  FARPROC loadlib = GetProcAddress(k32, "LoadLibraryA");
  printf("LoadLibraryA @ %p\n", (void *)loadlib);

  // One LoadLibraryA per DLL, each completed before the next begins, so a DLL
  // that arms a loader notification is in place before the following one
  // loads. The process stays suspended throughout.
  for (int i = 0; i < ndll; i++) {
    size_t n = strlen(dlls[i]) + 1;
    void *remote = VirtualAllocEx(pi.hProcess, NULL, n, MEM_COMMIT, PAGE_READWRITE);
    if (!remote) {
      printf("VirtualAllocEx failed: %lu\n", GetLastError());
      TerminateProcess(pi.hProcess, 1);
      return 5;
    }
    if (!WriteProcessMemory(pi.hProcess, remote, dlls[i], n, NULL)) {
      printf("WriteProcessMemory failed: %lu\n", GetLastError());
      TerminateProcess(pi.hProcess, 1);
      return 5;
    }
    HANDLE th = CreateRemoteThread(pi.hProcess, NULL, 0,
                                   (LPTHREAD_START_ROUTINE)loadlib, remote, 0, NULL);
    if (!th) {
      printf("CreateRemoteThread failed: %lu\n", GetLastError());
      TerminateProcess(pi.hProcess, 1);
      return 5;
    }
    WaitForSingleObject(th, 10000);
    DWORD hmod = 0;
    GetExitCodeThread(th, &hmod);
    CloseHandle(th);
    if (!hmod) {
      printf("INJECTION FAILED for %s - LoadLibraryA returned NULL\n", dlls[i]);
      TerminateProcess(pi.hProcess, 1);
      return 5;
    }
    printf("INJECTED OK - %s base = 0x%08X\n", dlls[i], hmod);
  }

  ResumeThread(pi.hThread);
  printf("resumed. Game is running; log:\n  %s\\tvt_los.log\n", root);
  CloseHandle(pi.hThread);
  CloseHandle(pi.hProcess);
  return 0;
}
