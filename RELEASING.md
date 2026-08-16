# Releasing a patch

The game fixes people actually download live in `Patches/` (hotfix zips) and
`Executables/` (the 4GB LAA patched exe). To make a patch publicly downloadable,
cut a **GitHub Release** rather than pointing people at raw files.

## Manual (web UI)

1. Go to the repo → **Releases** → **Draft a new release**.
2. Choose or type a tag, e.g. `v0.0.2` (must start with `v` for the automation below).
3. Title it like the changelog entry (e.g. `TvT REDUX Hotfix 2026-07-02`).
4. Attach the zips from `Patches/` and `Executables/`.
5. Publish.

## Automatic (GitHub Actions)

A `.github/workflows/release.yml` runs whenever a tag starting with `v` is
pushed. It creates the release and attaches everything in `Patches/` and
`Executables/` automatically, with auto-generated release notes from the commit
history.

To trigger it from the command line:

```bash
git tag v0.0.2
git push origin v0.0.2
```

Or run the workflow manually from the **Actions** tab (it's also set up for
`workflow_dispatch`).

## Naming

Keep the changelog entry in `CHANGELOG.md` and the release title in sync — the
changelog is the human-readable "confirmed fixes" list; the release is its
downloadable mirror.
