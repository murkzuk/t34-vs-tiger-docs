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

## 2026-08-25 — We disassembled the hot code. The trees were guilty after all.

Short version: a sampling profiler told us *which DLL* was eating the frame.
This week we went one level down and disassembled the actual addresses to find
out *what code*.

**First, we had to correct ourselves.** The profiler's counters turned out to be
cumulative since injection — never reset — so the numbers we quoted were session
averages that included mission *loading*. The early reports were 65% `ntdll`,
which is just file I/O and allocation, and that dragged everything else down.
Recovering the per-window deltas gives the real steady-state gameplay mix:

```
Objects.dll   50-54%      <- the game's object/entity code
Engine.dll    20-24%      <- rendering
d3dx9_30       5-8%
Service.dll    5-6%
J5Script       ~2%        <- the .script interpreter
Behavior.dll   ~0.5%      <- ALL of the AI
D3D9.DLL       0.0%       <- the graphics wrapper
```

Three things fall out of that, and all three are more useful than the number we
started with:

- **DXVK vs dgVoodoo does not matter.** The wrapper is 0.0% of frame time.
  That argument is now settled with a measurement rather than an opinion.
- **The script interpreter is not the bottleneck.** 2%. Anyone optimising
  `.script` files for speed is polishing the wrong thing.
- **The AI is free.** `Behavior.dll` is half a percent — which includes the
  line-of-sight and occlusion work. No performance reason to hold back on AI
  features, ever.

**Then the disassembly.** Engine.dll's hot pages all cluster in one contiguous
90 KB block. Every string referenced from that block says the same thing:

```
RenderedTrees   TreeMapSize   ShadowLOD   RootSystem
CSTDynamicVB    CSTDynamicIB  FillBillPrimitiveVertexBuffer
```

`CSTDynamicVB`/`IB` are SpeedTree's dynamic vertex and index buffers. It is the
tree draw path — **6.28% of total frame time in five 4 KB pages alone**.

Which independently confirms something we had already found the crude way:
pulling the tree `ModelLOD` distances back was worth 8 fps, and now we know
exactly why.

The hottest single function is a 2.3 KB routine with a 740-byte stack frame that
walks a list of 68-byte instance records, reads a one-byte material ID from
offset `+0x40`, and skips the expensive render-state setup whenever the material
matches the previous record — a textbook material-sorted batch loop. You can
read that straight off the assembly, including the `fmul 255.0` converting a
float colour for the vertex format.

**Still open:** Objects.dll is over half the frame time and we have no
address-level data for it, because the profiler's module table was capped at 128
entries and hit that cap exactly. Raised to 512; one more run will produce it.

Waiting for us when it does: an RTTI map already extracted from the shipped
DLLs — **4,778 named virtual functions across 300 classes** in Objects.dll
alone, with real names like `CAnyComponentNE@g5` and `IPositionable@g5`. So the
next run turns raw addresses into class names and vtable slots immediately,
with no guessing.

*Tooling note: `pefile` + `capstone`, not Ghidra. These 2008 DLLs shipped with
full MSVC RTTI intact, which is a far better lever than decompilation for
"what is this address".*

*Disassembly and analysis by Claude (Opus 5).*

---

## 2026-08-25 — Where the framerate actually goes, measured one thing at a time

Sat at 26 fps and couldn't say when it dropped. So: bisect. Same mission, same
spot, one change per run.

| change | fps |
|---|---|
| as found | **26** |
| trees drawn in 3D: 720 m → 250 m | **34** |
| shadows: 1050 m → 560 m | 36 |
| fog back to stock density | 40 |

**Trees are the expensive one.** That mission generates **77,888 of them**, and
how far out they're drawn in full 3D before dropping to billboards is worth
**eight frames** on its own.

**Shadows barely matter** — two frames for nearly halving the distance. I'd
expected more, especially at dawn where a 10° sun throws a 17-metre shadow off
every tank.

**Fog is the interesting one, because it's backwards.** Thicker fog is *faster*
— you draw less. But at the stock density you can see **5% at a kilometre**, and
the log proved what that means: every sight line in the run was under **711 m**,
and **the AI gunner never fired once**. Nothing was ever far enough away to be
worth a decision.

Settled on a middle value. Same mission then gave a median sight line of **867 m**
and a max of **1049 m**, with the gunner engaging normally again — about 340 m
of engagement range bought back for a couple of frames.

So it's a dial, not a setting: **see further, or run faster.** Worth knowing
which way you'd rather have it.

*Honest footnote: this only explains about half the drop. The rest predates the
changes we were testing, and the next step is a proper sampling profiler rather
than more guessing. Measured with Claude.*

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

## 2026-08-24 — A bigger map is free to make and costs you every hill worth hiding behind

If you ever wondered why some maps feel flat and exposed while others give you
proper hull-down spots, this is why — and it's not the map size, it's what the
map size is *made of*.

Making a TvT map bigger costs nothing. You keep the same 2049×2049 heightfield,
put a larger number in `MatrixWidth`, and the engine stretches it. No new terrain
files, no new work, one number.

But stretching doesn't *add* terrain. It spreads the same samples thinner:

| map | world | heightfield | metres between height samples |
|---|---|---|---|
| REDUX Berezov | 9 km | 2049² | **4.39 m** |
| ZW Zitadelle M4 | 18 km | 2049² | 8.79 m |
| ZW Zitadelle M1 | 36 km | **4097²** | 8.79 m |
| ZW Zitadelle M2/M3 | 36 km | 2049² | **17.58 m** |

At 17.6 metres between samples, **every fold of ground smaller than a football
pitch has been averaged out of existence.** Dead ground, reverse slopes, the
little rise you'd back a Tiger behind — none of it is in the data any more.

It shows up in play. From the line-of-sight logs, what actually blocks a sight
line:

| | blocked by terrain | blocked by trees |
|---|---|---|
| Berezov (4.4 m samples) | **59%** | 41% |
| Zitadelle M1 (8.8 m samples) | 24% | **76%** |

On the fine map the *ground* hides tanks. On the coarse one it barely can, so the
trees end up doing the hiding instead. That's the difference you feel and can't
name.

**ZeeWolf clearly knew.** Zitadelle M1 is the only mission in his entire set with
a 4097² heightfield — he doubled the terrain data specifically to hold 8.79 m
across a 36 km world. (It's also the 32 MB that made that map crash on a 2 GB
executable, but that's another post.)

One last thing, for scale: Zitadelle M1's 482 fighting units sit in a box about
**14 × 10.7 km — 11.6% of the map**, and not even centred. The other 1,150 km²
is empty. The size was never driven by the battle. It's just nearly free, and
you pay for it in detail rather than in files.

*Measured with Claude, by reading each mission's own `WorldMatricies.script` and
parsing unit positions straight out of `Content.script`.*

---

## 2026-08-24 — The tree desync everyone laughed at, and why tanks never sit in shade

Two findings that turn out to be the same finding.

**First: a tank parked under a tree stays fully lit.** The tree's shadow lands on
the ground and stops there. It never falls on the hull.

That isn't a bug, it's two separate shadow systems that were never joined up:

- **Stencil shadows** are the only ones that can land on *another object*. They're
  cast by whatever is listed in `StencilShadowSettings` in `Settings.script` —
  tanks, guns, buildings, inventory items. **Trees aren't in the list.**
- **Tree shadows** are drawn by a completely different pass that only paints onto
  terrain, distance-capped by `TreeShadowLodDistance`.

The reason trees aren't in the first list: they don't go through the engine's
object pipeline at all. The vegetation is **SpeedTree** — the original
`SpeedTreeRT.dll` and `STTree.dll` are still sitting in the game root, with the
`.spt` tree definitions in `Models\Trees\`. SpeedTree draws its own projected
ground shadow, so a tree never enters the engine's stencil pass and has no way
to reach a tank.

Not fixable in script. The shadow pass lives in the compiled renderer.

**Second — and this is the one that'll ring a bell: it explains the multiplayer
tree desync.**

Those `.spt` files are 6–15 KB. That's not tree geometry, it's a tree *recipe* —
SpeedTree **generates the trees at runtime, on each machine**. Nothing about the
resulting layout is sent over the wire.

So every client grew its own forest. You'd drive a clean line through a gap that
existed on your screen, while on someone else's machine you were ploughing
through trunks — and they'd watch trees fall where you could see none. It got
ridiculed at the time and nobody outside the studio knew why.

It was never a netcode bug. **The trees were never synchronised because they
were never sent** — each copy of the game invented its own.

One nice detail: the game files show trees are *both* things people argued about.
Real 3D geometry for trunk and branches, billboards for the leaves, and a full
billboard impostor at distance.

*Found with DeepSeek, by reading the shipped DLL exports and the shadow settings
rather than guessing.*

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
