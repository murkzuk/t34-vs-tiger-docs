# Discord log — postable findings

A running list of things worth telling the old TvT modders' chat, newest first.
**Each entry is written to be pasted as-is** — short, plain, no jargon that needs
a footnote, and honest about what was AI-assisted.

## How this gets used

- **Any AI working on this project appends here** when a result lands that a
  reader outside the project would find interesting. Don't wait to be asked.
- Not every fix belongs. The bar: *would someone who hasn't touched TvT in ten
  years read this and go "huh"?*
- Keep the credit accurate. The user is a non-coder; the reverse engineering is
  AI-assisted and the posts say so. Claiming otherwise gets spotted and is worse
  than saying nothing.
- Entries are **drafts**. The user edits or bins them freely.

---

## 2026-08-25 — Why distant tanks never fade into the fog

Long-standing niggle: the ground hazes out with distance but tanks stay dark and
sharp, so a distant tank is an easy spot and an easy kill.

Hooked the D3D9 renderer and counted **2.7 million draw calls**, tagging each one
with which shader drew it and whether fog was on. The result is about as clean as
these things get:

```
skinned vs_1_1 :        0 fogged   1,353,075 unfogged
skinned vs_2_0 : 1,364,628 fogged           0 unfogged
```

**Not one exception.** The game ships two versions of every tank shader — an old
`vs_1_1` one and a newer `vs_2_0` one — and only the newer one can do fog at all
(the old one has no fog input in its constant table). The engine runs *both*, on
the same tanks, roughly 50/50. Half your tanks fog. Half can't.

The good part: the fogged version of every affected material is **already sitting
in the game files, unused**. So this isn't "we'd need the shader source" — it's
"why is the engine picking the old one?"

Not fixed yet. But it went from a vague "fog looks wrong" to a precise question
in one measurement.

*Reverse engineering done with Claude; the D3D9 probe is a small injected DLL
that only reads, never changes anything.*

---

## 2026-08-24 — The sun was in the wrong place for twenty years

The original devs shipped sun direction vectors that weren't unit length. The
engine normalises them, but the mismatch produced real glare and an **invisible
sun disc** — you could never actually see the sun in the sky.

Fixed by normalising the vectors. The sun is now visible in TvT for the first
time. Several missions also had no sun direction at all (defaulting to noon
overhead) despite being scripted as dawn or 19:30 sunset — those now have proper
low sun in the right compass direction.

*Found and fixed with DeepSeek.*

---

## 2026-08-24 — TvT is sitting on a pile of features that were switched off, not removed

We all knew TvT shipped unfinished — the publisher went under during release.
What we maybe didn't know is how much of the missing stuff **is still in there,
commented out**.

Someone did a systematic diff of TvT's scripts against Whirlwind over Vietnam,
the helicopter game on the same engine. About **twenty features are live in WoV
and commented out in TvT**. Not deleted. Commented.

The one that stopped me:

**Radio chatter.** `Common\Dialogs.script` in TvT is an empty array with a single
commented-out example line. In WoV the same file has **around 129 active dialog
classes**. There's a matching `SoundsTable.script` for speaking numbers aloud —
also emptied, also present in WoV with full voice tables. So the whole scripted
radio/dialog subsystem is in the engine, wired up and working. They just took
the WW2 content out.

Others, all still in the files with `//` in front of them:

- **Troop transport** — mount and dismount. The system lives in `Common\`
  (`SetOrder_Load` / `SetOrder_Unload`, loader joints, `IsTransport`) fully
  intact. It's unplugged at the *unit* level: one commented line per soldier.
- **Vehicle track and movement sound** — commented out on the Tiger.
- **Gun recoil animation** on the Nebelwerfer; **muzzle flash and smoke** on the
  ZIS-3.
- **End-of-mission briefing text** — the call that fills it in is commented, which
  is why that screen is blank.
- **Tactical map cursor and navpoints**.
- **Weapon minimum/maximum engagement range** on the Pz IV.

## The honest caveat

That list came out of an automated sweep and **one entry has already been
disproven**. "Infantry fire silently" looked like a bug — the burst-fire sound is
commented out on every rifleman. Turns out TvT's rifles use a different sound
path entirely (`FireSoundId`, properly registered), and the WoV comparison was
apples to oranges because WoV's "rifle" is an M16 firing bursts.

So: every one of these needs checking against the actual files before anyone
uncomments anything. A commented line means nothing if the effect or class it
points at was also stripped.

Still — the interesting part stands. **The engine can do more than the game
does**, and most of it is a one-line change away rather than a rewrite.

*Diff work done with DeepSeek; false positive caught by verifying the mechanism
rather than trusting the grep.*

---

## 2026-08-22 — ZeeWolf's "4GB" executable was never 4GB

`TvsT_fullLOD_HARD_4GB.exe` in the ZW build was compiled **without the
large-address-aware flag** — so despite the name it was capped at 2 GB, same as
every other exe in the folder.

That's why the big Kursk map (36 km, 155,000 trees) crashed during load. Setting
one bit in the PE header fixed it; the map now loads in 17 seconds and plays.

---

## 2026-08-21 — The AI can't see through hills any more

TvT's AI never had line of sight. Its vision check is a 2D distance-and-angle
roll — ridges, hills and woods simply aren't in the calculation, which is why
you get shot through a hillside.

An injected DLL now hooks that function and does a real terrain and foliage
check. **Between 74% and 90% of sightings get refused**, depending on the map.
It runs on both REDUX and the ZeeWolf 2015 build.

Cost: **8 to 12 microseconds per sight line, under 1% of frame time**, measured
at up to 894 vision checks a second on a 36 km map. It is not what's eating your
framerate.

Nothing on disk is modified — the hook lives in memory for that session only.

*Built with Claude.*

---

## 2026-08-21 — ZeeWolf's forests are thirteen times thinner than they look

Calibrating the above turned up something odd. Painted forest area versus trees
actually planted:

| map | trees per km² | one tree every |
|---|---|---|
| REDUX Berezov | 4,310 | 232 m² |
| ZW Kursk | 335 | 2,985 m² |

**A tree every 55 metres** — that's parkland, not woodland. But 29% of that map
is painted as dense conifer, so a naive line-of-sight model refuses everything.
Worth knowing if you ever paint forest zones.

---

## 2026-08-20 — Your wingman's lurching is one number

The AI wingman constantly surges then stops. Three theories were wrong before
anyone measured it. A 10 Hz position trace, holding station:

```
wingman 1.14 m/s     leader 0.92 m/s     fully stopped in 10% of samples
```

It travels a quarter faster than you, then halts. Its cruise speed was set to
**80% of maximum** — about 9 m/s for a Tiger, while you crawl at 1. It has no
gear between "much faster than you" and "stopped".

Also worth knowing: the wingman formation values are **leftovers from Whirlwind
over Vietnam**. REDUX still carries them — 200 m spacing with a `z` of 30, which
is *altitude*. The devs never retuned them for tanks.

---

## Older / not yet written up

- Map size is paid for in terrain detail — stretching a heightfield over a bigger
  world is free to author and costs you every fold of ground smaller than a
  football pitch. Numbers in `project_tvt_map_size_vs_detail`.
- Trees are SpeedTree v1 and cast shadows onto **terrain only**, never onto
  tanks — two separate shadow systems, by design.
