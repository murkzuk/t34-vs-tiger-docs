# The two checkouts — how they stay in step

Set up 2026-08-25. Read this before wondering why the other AI can't see your work.

## The problem it solves

Two AIs work on this project from **two separate checkouts of the same repo**:

| | path | has GitHub? |
|---|---|---|
| Claude | `C:\Users\Jeff\t34-vs-tiger-docs` | yes (`origin`) |
| DeepSeek | `K:\TvTDeepseek\t34-vs-tiger-docs` | no network |

Their histories had diverged with **no way to reconcile** — 35 commits of
DeepSeek's work sat on a branch neither GitHub nor Claude's checkout could see.
Left alone that drifts until the two are describing different games.

## The fix: each checkout is a git remote of the other, by local path

Both folders are on the same machine, so **no network is needed**. Git happily
uses a filesystem path as a remote.

```
Claude's checkout:    remote "deepseek" -> K:/TvTDeepseek/t34-vs-tiger-docs
DeepSeek's checkout:  remote "claude"   -> C:/Users/Jeff/t34-vs-tiger-docs
```

DeepSeek's 35 commits are now merged into `main` and pushed to GitHub.

## How to use it

**To see the other agent's work:**

```
git fetch deepseek        (from Claude's checkout)
git fetch claude          (from DeepSeek's checkout)
git log --oneline main..deepseek/<branch>
```

**To take it in:**

```
git merge deepseek/<branch>
```

**Claude is the hub.** Only Claude's checkout has GitHub, so anything that
should end up on the remote goes: DeepSeek branch -> fetch -> merge into
Claude's `main` -> `git push origin main`.

**DeepSeek can pull `main` back** with `git fetch claude && git merge claude/main`
whenever it wants Claude's side.

## Gotcha that already bit once

The merge aborted because an **untracked** file existed in Claude's checkout with
the same name as one DeepSeek had committed (`FINDINGS_2026-08-21_log_sweep.md`),
with different content. Git refuses to clobber untracked files — correctly.

Claude's copy was parked in `K:\TvTDeepseek\rollback\` rather than deleted.

**So:** before merging, `git status` and deal with untracked files first. Don't
leave working notes loose in a checkout — either commit them or keep them in
`K:\TvTDeepseek\notes\`.

## Notes live in ONE place

`K:\TvTDeepseek\notes\` is the **master copy** and is shared — both agents read
and write it. The in-repo `notes/` folder is a mirror for version history.

Write to the master first. A note that exists only in one agent's checkout is
invisible to the other, which is the whole problem this file exists to prevent.

Same rule for `DISCORD_LOG.md` and any session snapshot.

## Who owns what — agreed directly, 2026-08-25

Claude and DeepSeek spoke directly through the harness and split it. This is
the live answer, not a guess:

| Work | Owner |
|---|---|
| **Fog technique selection** (why the engine picks `vs_1_1`) | **DeepSeek** — its domain, it built the probe; chasing the DXVK-caps hypothesis first |
| **Pz IV G rollout** (13 missions) | **DeepSeek** |
| **5 stock-noon atmosphere missions** | **DeepSeek** |
| **`GetGeometry` Y-scale** (tree height) | **free** — DeepSeek is not starting it, judged low value-per-effort next to fog. Claude's if wanted |

DeepSeek also confirmed: it will **work from `main`**, stop committing to the
stale `deepseek/atmosphere-dawn-fog` branch, and leave `DISCORD_LOG.md`
uncommitted (Claude's drafts). Its first move each session is pull-and-confirm
before touching any game file.

Revisit this table whenever either side finishes something.

## Suggested division of labour (not enforced, just sensible)

Nothing stops both agents editing the same file, and nothing will warn you. The
cheapest protection is not to.

- Whoever starts a piece of work **owns those files** until it lands.
- Say so in your session snapshot: what you touched, what you left alone.
- Game files under `M:\` are **not** version controlled — that is what
  `K:\TvTDeepseek\rollback\` is for. Back up before editing, always.
