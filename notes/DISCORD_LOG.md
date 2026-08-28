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

## 2026-08-28 - Fog finally reaches the tanks

For twenty-five years, a tank at distance in this game has floated as a bright,
sharp silhouette against the misted terrain — because the engine turned fog
**off** for the distant level-of-detail pass, while leaving it on for everything
close.

The fix wasn't a shader rewrite. The distant-LOD vertex shader had been
computing a fog factor the whole time — the engine was just discarding it. A
small injected hook flips fog back on for those draws, reusing the engine's own
fog density and colour, so a distant tank now fades into the haze at exactly the
same rate as the ground beneath it.

AI-assisted reverse engineering, confirmed by playing. It's the first thing you
notice in a forest: no more floating, unfogged hulls at range. Real fog, the
engine's own, all the way to the horizon.

## 2026-08-26 - Why you have never seen the sun in this game

Three findings from a day on lighting, and they interlock.

**1. You cannot look up.** The commander's view is hard-limited:

```c
CommanderCameraLink.SetMaxVertAngle(Math_PI*(10.0f/180.0f));
```

Ten degrees. That is the ceiling, everywhere - the unit declarations agree at
`MaxVertAngle = 0.17` radians. So anything higher in the sky simply cannot be
seen from a tank.

**2. Every campaign mission puts the sun at 63-67 degrees.** Which is why nobody
has ever seen it. It has been up there for twenty years, permanently out of
frame. The one mission where someone got the sun to appear had tuned it to
*exactly* 10.0 degrees - not luck, that is the view limit.

**3. And the sun vectors are not unit length.** They run 0.34 to 1.25. That
matters because the sun billboard is placed along `SunDirection * DistanceToSun`,
and `DistanceToSun` is 2000 in every mission - so a vector of length 0.34 puts
the sun at **680 m instead of 2000 m**, close enough to sit inside the fog or
below the skyline. Brightness is a completely separate `SunIntensity` field, so
normalising moves the sun; it does not brighten it.

All twelve campaign missions normalised, and eight given an actual time of day.
Shadows in the sunny missions are now about three times longer, which is the
part you *can* see - because shadow length responds at any sun elevation, even
one you cannot look at.

---

**Then a complaint that turned into a proper hunt:** *"tank shadows are so dark
they crush all detail"*.

It turns out TvT has **three separate shadow systems**:

```
StencilShadowColor    vehicles - the real cast shadow
ShadowColor           terrain and buildings
FakeShadow            a cheap dark blob under a vehicle, per model
```

plus `AmbientLight`, which is not a shadow setting at all - it is the fill light,
what lights a surface the sun is not hitting. Two different mechanisms produce
what you would call a shadow:

```
facing AWAY from the sun    -> AmbientLight only
facing the sun but BLOCKED  -> sun x ShadowColor / StencilShadowColor
```

**Six of the twelve missions never set `StencilShadowColor` at all**, so vehicle
shadows fall back to the engine default of `(0.3, 0.3, 0.3)` - the darkest value
anywhere in the game and dead neutral grey. Nobody chose that. It is what you get
when nobody sets it.

The two missions anyone actually finished have `ShadowColor` and
`StencilShadowColor` set to *identical* values. Every mismatch is an unfinished
mission. That is now a documented rule: they are the same physical shadow drawn
by two renderers, and if they differ a tank and the ground beside it cast
visibly different shadows.

*(Tint them blue, incidentally. What fills a real shadow is skylight. The
finished missions do exactly that.)*

---

**A bug the log will never tell you about.** No Tiger in the game gets a fake
shadow. `FakeShadows.script` sets it on `Cu_veh_PzVI_MAINModel` - but every
Tiger uses `Cu_veh_PzVI_LATEModel`, and `LATE` appears zero times in that file.
G5 wired the MAIN model, switched the units to LATE, and never updated the
shadow config.

It never errors, because it is a perfectly valid assignment to a class nothing
instantiates. The only way to find it is to cross-check configured model classes
against the ones units actually ask for. There is a second bug of exactly this
shape in the same area, already fixed.

---

**And the thing that was never a lighting problem at all.** After four rounds of
lifting shadow values, the tank commander was still nearly black. So we measured
his texture instead of theorising about it:

```
hum_German_Tankman.tex    22% average luminance   <- the commander
u_veh_PzVI_MAIN1.tex      62%                      hull
u_veh_PzVI_MAIN2.tex      53%                      turret
```

German panzer crews wore black, and G5 painted him accordingly - average texel
RGB(60, 56, 44). Light is *multiplied* by texture, so at 22% base no ambient
value will make him bright without washing out the entire scene. He is supposed
to be a dark figure.

Four rounds of pulling lighting levers before checking the texture. The lesson is
the finding: **measure the thing before reasoning about it.**

*Analysis by Claude (Opus 5). All of it is now in the mission authoring
reference rather than in a session that scrolls away.*

---

## 2026-08-25 — A twenty-year-old crash, and the fix that was sitting in a folder

Campaign 1 Mission 2 crashes to desktop. Here is what the game's own log says,
6,451 times, just before it dies:

```
Possible stack overflow in function RepeatOrder,      stack depth 1389
Possible stack overflow in function OnPathEndReached, stack depth 1390
Possible stack overflow in function PopOrder,         stack depth 1391
```

One AI group — the German infantry patrol — reaches the end of its route and
then eats its own tail:

```
OnOrderFulfilled -> restore "Patrol" -> RepeatOrder
   -> already at end of path -> OnPathEndReached
   -> mission script re-arms the attack -> ContinueOrder -> round again
```

That group appears **1,395 times** in the log. The next worst appears 45 times.

**The cause is a fix.** A change made a week earlier let groups resume their
patrol after being interrupted by a fight — a genuine improvement. But it
resumed the patrol even when the patrol was already *finished*, and that closed
the loop. So the fix is one condition: only resume if there is road left.

```
   if (!m_CurrentOrder.m_PatrolPath.isEmpty()
+      && m_CurrentOrder.m_NextPatrolPoint < m_CurrentOrder.m_PatrolPath.size())
```

An exhausted patrol now falls through into the branch below, which parks the
group and deliberately does not call `RepeatOrder()` again.

**Results, from a full mission played to a proper ending:**

```
stack overflows       6,451  ->  0
that group's log      1,395  ->  11 lines
alarms                  143  ->  4  (two unrelated tank groups)
outcome               crash  ->  clean exit
```

**The part worth copying:** that file is shared by *every mission in the game*,
so it was applied and tested completely alone — game launched normally, no
hooks, no probes, nothing else changed. And the specific regression to rule out
was obvious in advance: make the guard too strict and groups go inert after
combat, undoing the very improvement that caused the bug. So that got measured
rather than eyeballed — **80 patrol resumptions, 0 groups parked.** Mid-patrol
groups still pick their route back up.

**Now the embarrassing bit, which is the actual lesson.** None of that diagnosis
was new. It was worked out four days earlier, written up and reviewed three days
earlier, and then parked in a `patches\` folder and recorded on no list
anywhere. It sat there until it crashed a live session.

Worse: an experimental performance hook happened to be attached at the time, so
the crash looked like it might have been self-inflicted, and real effort went
into clearing that before anyone read far enough down the game's own log to find
`Possible stack overflow` staring back.

A diagnosed, written, reviewed fix that isn't on the board does not exist.

*(Also fixed while in there: `ActivateMove` — a command that does not exist and
never has — should be `ActivateMovement`. It had been logging an error on every
single mission load. The same typo is still sitting in Campaign 2 Mission 3.)*

*Diagnosis, patch and verification by Claude (Opus 5).*

---

## 2026-08-25 — We made a 2001 engine 6% faster, and proved it

Follow-on to the profiling work. Short version: the hottest single function in
T-34 vs Tiger is a `std::map` lookup, it gets called **41,000 times per frame**,
and two-thirds of those calls ask for the same thing as the call before.

Here is the measurement that made it obvious:

```
lookups                  2,857,139 per second   (~41,400 per frame)
key repeats previous          67.2%
```

That 67.2% held to within half a percent across 23 separate reporting blocks. It
is not noise — it is structural. The caller loops over things that share a key
and re-walks a red-black tree for every single one.

So: a one-entry cache in front of it. Which is really just hoisting the lookup
out of the loop, except done from outside the engine without touching the loop.

**The result:**

```
CACHE     124.2  126.5  123.9  116.6      median 124.2
BYPASS    117.1  117.1  115.6  116.5      median 116.8
                                          -------------
                                          +7.4 fps   +6.3%
```

Look at the BYPASS column — 115.6 to 117.1 across four separate phases, a 1.5
fps spread. That tightness is the reason to believe the rest.

**How that control got so tight** is the bit worth stealing. The in-game fps
counter costs frames of its own, and comparing two separate runs cannot rule out
standing somewhere slightly different or the ±3 fps of run-to-run drift. So
instead the injected DLL counts its own frames and **toggles its own cache on
and off every ten seconds**, reporting each phase. Same scene, same session,
seconds apart, one variable. Position, drift and observer overhead all cancel.

**On not breaking the game.** A stale cache in front of a container lookup
returns a dangling iterator and you get corruption. The guard depends on where
MSVC puts `_Mysize` in a `std::map`, which was *inferred*, and inference had
already been wrong six times that day. So the cache starts in VERIFY mode: the
real function still runs every time and the cache only *predicts* alongside it
and compares. It is allowed to skip actual work only after 400,000 agreements
with zero disagreements, and one disagreement disables it permanently with a
loud log line.

It passed first time and has now gone **631 million calls across two sessions
without a single disagreement.**

**One nice detail:** the theoretical ceiling was 5.1% — 7.59% of frame time
multiplied by a 67% hit rate. We measured 6.3%. The extra is almost certainly
because skipping 27 million tree walks a second doesn't only save those walks,
it stops them evicting everything else from cache. The code *around* it got
faster too. Worth remembering: for pointer-chasing work, the direct arithmetic
is a floor, not a ceiling.

Next up: the cache holds one entry. The top 16 keys account for up to half of
all lookups, so a 4- or 8-entry table should push the hit rate well past 67%.

*Analysis, hook and A/B harness by Claude (Opus 5). Nothing on disk is modified
— it's an injected DLL, and launching the game normally gives you the stock
build.*

---

## 2026-08-25 — Three theories, three autopsies, and one real target

Spent a day finding out why TvT runs the way it does. Most of it was being
wrong in public, so here is the whole thing including the parts that failed.

**The finding everything else rests on:** TvT is CPU-bound with the GPU idle.
Not "mostly" — measured, every run:

```
inside Present()   0.1%     <- waiting for the GPU
inside Lock()      0.0%     <- waiting for a buffer
everything else   99.8%     <- ~14 ms/frame of pure CPU work
```

322,000 triangles a frame at ~68 fps is about 20M triangles/sec. Your GPU is
asleep. It is waiting for one core of your CPU, and has been for twenty years.

**Then the real result.** The forest detail slider does not do what you think.
Turn it to minimum and a quarter of all draw calls disappear — genuinely, the
probe counted them. And the frame time does not move. At all:

```
page          FOREST MAX  FOREST MIN   change
+0x17D000          7.54%       7.45%    -0.09   <- hottest page in the game
+0x19B000          1.47%       1.38%    -0.09
+0x186000          1.27%       1.38%    +0.11
```

The slider changes what gets **drawn**. It changes nothing about what gets
**computed**. Every tree still goes through the quad-tree walk, the grid query
and the LOD decision every single frame — and when your draw distance is short,
all that work is calculated and then thrown in the bin. About a tenth of your
frame time, every frame, deciding things that do not matter.

We have the function disassembled: a 736-byte routine that converts a world-space
box into forest grid-cell indices with four x87 float-to-int round trips per
query. That is now a real optimisation target rather than a curiosity — it is
CPU work, no setting reduces it, and DLL injection into this engine already
works.

**The three theories that died, in order:**

*Grass is a fill-rate problem.* Alpha-blended billboards, ground-level camera,
massive overdraw — textbook. The GPU was idle at 0.1%. Dead.

*REDUX's AlphaBlendDistanceFactor of 0.8 is too high.* Reverted it to G5's
shipped 0.4 and grass got **more** expensive, plus you could suddenly see tanks
through the grass. So we read the engine instead of theorising, and it computes
`1.0 / (1.0 - factor)` — the value is where the fade **begins**. 0.8 fades over
the last 20% of draw distance, 0.4 over the last 60%. The modded value was right
and the original script was the odd one. Dead, and backwards.

*(Warning for anyone else poking at this: never set that value to 1.0. It is a
divide by zero.)*

*The Tiger shadow bug is worth 28 fps.* We found a genuine twenty-year-old bug —
`ShadowHide.script` sets the late Tiger's shadow cutoff, but the model file never
declared the field, so the assignment failed silently and every Tiger kept the
engine default of 9999, meaning "never hide this shadow". Fixed it, framerate
jumped. Then we put the bug **back** to confirm — and the framerate went *up* 4%.
Noise. The mission has two Tigers in it. Dead.

(The fix stays anyway. It is still wrong, just not expensive. And amusingly
ZeeWolf's copy already had the missing line — ZW was right and the other build
was the odd one out.)

**The most useful number of the day** turned out to be the boring one: three runs
in identical conditions gave 66.8, 69.5 and 68.4 fps. So run-to-run noise is
±4%, and *anything below that is not a result*. That single number retroactively
killed the shadow theory and confirmed the grass one.

**What grass actually costs:** 1.8 ms/frame and 33,751 triangles, for
approximately zero extra draw calls. Real, modest, and the only positive number
any slider produced all day.

**Method note, since it is the actual lesson:** every one of those three theories
was plausible reasoning from real evidence. Plausible reasoning about a 2001
engine is worth approximately nothing. Predict the number *before* the run so the
theory can fail, and treat anything under the noise floor as zero.

*Tooling: a D3D9 draw-call probe built for this, plus RTTI pulled straight out of
the shipped DLLs — 4,778 named virtual functions across 300 classes in
Objects.dll alone, which is what turns a raw address into "CGrass" or
"CSTForest". Analysis and code by Claude (Opus 5).*

---

## 2026-08-25 — We disassembled the hot code. The trees were guilty after all.

> **Later the same day — read the newer entry above before posting this one.**
> Trees are indeed the target, but *not* for the reason this entry implies.
> Tree **rendering** turned out to cost nothing measurable; the cost is the
> per-frame tree **management** that runs whether or not anything is drawn.
> The claim here that the tree draw path is the expense is wrong.


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


---

## 2026-08-26 — TvT REDUX: found a 2.35x framerate win, and it was our own code

Long-standing complaint: the game sat around 70-90 fps and sometimes worse,
with no obvious cause. Turned out the AI line-of-sight hook — our own injected
DLL, ticked on by default in the launcher — was costing **~10.9 ms a frame**.

```
BEFORE   LOS on   51 fps      LOS off  115 fps
AFTER    LOS on  120 fps
```

The cause was embarrassing and simple. A helper called `readable()` validates a
pointer with `VirtualQuery` — which is a **syscall**. Two places called it in
loops:

- `find_endpoints()` — up to **16,512 syscalls per vision check**, in a 128x128
  nested scan, to validate a window that is only **520 bytes wide**. One
  `VirtualQuery` covers the whole thing.
- A `CrewHook` sweep — **256 syscalls per crew tick, ungated**. `g_crew_calls`
  reached 125,185 in a single session, so roughly 32 million syscalls. This was
  reverse-engineering scaffolding written to discover which struct offset moved
  when the gunner slewed onto a target. That question was answered weeks ago.
  It was never switched off.

Both are now fixed and LOS is free — 120 vs 115 is inside the noise floor.
Applies to the ZeeWolf 2015 build too, same injected binary.

**The method failure is the more useful lesson.** The evidence was in hand at
11:40 and got read backwards: comparing a fast run against a slow one, I noticed
the fast run had no LOS log and concluded *"so LOS wasn't the difference"*. Its
absence **was** the difference. The rest of the day went into profiling
renderers, attributing syscalls, and running a native-D3D9-vs-DXVK A/B — all
downstream of that one misreading, and all of it measuring a configuration that
didn't have the problem in it.

**When two runs differ, diff the CONFIGURATIONS first** — which hooks, which
wrapper, which overlay — before profiling either one. An injected DLL is the
largest variable in the room.

Also learned the hard way today: **instrumentation added during RE has to be
gated before it ships.** A discovery sweep is not a feature. Both storms here
were debug code that outlived the question it was written to answer.

Side results from the same day, for anyone chasing similar ghosts:
- **Native D3D9 vs DXVK: identical** (50 vs 48 fps, F9 on both). DXVK is free.
- **A 4 KB profiler page in ntdll holds 256 syscalls** — each `Nt*`/`Zw*` stub
  is exactly 16 bytes. Bucket at 16 bytes to name one. And `KERNELBASE`/
  `kernel32` are never the answer to "who called this".
- **The engine's anti-aliasing is hard-disabled on any NVIDIA card** by a 2001
  string check. Enabling it breaks rendering outright — no terrain, invisible
  tanks, and not one line in any log.


---

## 2026-08-26 — T-34 vs Tiger: the .ms2 model format, fully decoded

Long-standing gap: we had a Blender importer for TvT's `.ms2` meshes that could
read geometry but produced a heap of parts stacked at the origin. It looked
broken enough that it had been shelved since August.

It wasn't broken. It was skipping three things.

**1. UVs are DirectX convention.** V runs 0 to **-1** (V=0 at the top of the
texture); Blender and OpenGL put V=0 at the bottom. 104 of the King Tiger's 138
textured nodes had UVs outside 0..1, every V range negative. The fix is one
character:

```python
loop[uv_layer].uv = (u, -v)
```

Values beyond 1 after flipping are legitimate **tiling** — the track mesh runs
to 8.0, once per track-link repeat. Don't clamp them.

**2. The node transform is frame 0 of an animation track.** The reader was
stepping over `d_count*12 + d_count*16` as "unidentified". It's `d_count`
positions followed by `d_count` quaternions (W first), with `d_count == 161` in
every vehicle — and `161*28+4 = 4512`, exactly the mystery "fallback block" size
recorded in earlier notes without ever being named.

Frame 0 is the rest pose (measured: 199 of 220 nodes at identity rotation there,
more than any other frame). Without it, static parts still look right because
they're baked in world space, but anything animated is authored around its own
pivot and collapses to the origin — turret, gun, road wheels.

The tracks are lovely to read once decoded: road wheels holding position while
their quaternion spins, the gun sliding 0.3 m backwards along its own axis under
recoil, the turret sitting still at 0.7071 — 90 degrees of traverse.

**3. The material index is packed into a 16-byte record** that was also being
skipped: `(packed, 0, vcount, 0)` where `packed = (icount << 16) | material_index`.
The low half indexes the companion `.script`'s ModelSkin array. All 138 geometry
nodes resolve.

Textures turned out to be the easy part — `.tex` files are **plain DDS** with the
extension changed, and materials, texture paths and alpha modes are plain text in
the model's `.script`. Alpha mode matters: markings, unit numbers and the flag
are alpha-keyed, and rendering them opaque puts black rectangles on the hull.

One more rule: **a material with no texture is armour geometry**, not visual —
`HullArmor_*`, `TUR_Armor_*`, the collision facets the game uses for penetration.
Nine of them on this model, rendering as blank plates draped over the tank.

Verified against the real vehicles: the King Tiger imports at **10.21 m** against
a true 10.29 m with the gun forward; the Tiger I at 8.34 m against 8.45 m.

**Two traps that cost more time than the format did.** Blender loads the
*installed* copy of an addon, not the one in your repo — ours was 8 days stale,
so edits silently did nothing until copied across and `__pycache__` deleted. And
`matrix_world` is stale until `view_layer.update()`, which reported the old
unassembled size and made a working fix look like a failed one.

**And the honest bit:** I decoded geometry, transforms and materials by reading
bytes, then rendered the result three times, looked at it, and called it correct.
The user opened the UV editor and spotted the island hanging outside the 0–1
square in about ten seconds. Second time that day their eyes beat my
instrumentation.


---

## 2026-08-26 — T-34 vs Tiger: writing `.ms2` files the engine accepts

Follow-up to decoding the format earlier today. The remaining question was the
only one that mattered: we could *read* G5's model files, but would the engine
accept one we *wrote*?

**It does.** The Level Editor loaded and rendered a `.ms2` produced by our own
code.

### The test

`Models/4MeterBox.ms2` — an original G5 file dated **December 2005**, referenced
by no mission, exposed in the Editor as "Dartboard 4 meters". One node,
`pCube1`, 24 vertices, 12 triangles.

Every Z coordinate multiplied by 3. Vertex and index counts unchanged, file size
unchanged at 4,499 bytes.

Asset View showed `C4MeterBoxModel` as a 3× tall rectangle. Console clean, no
errors. Original restored afterwards and md5-verified.

### The step that made it work first time

Before touching a single vertex, every model in both installs was read and
written back **unedited**, then diffed:

```
249 models    248 byte-identical    0 differ    1 pre-existing reader failure
```

If those bytes hadn't matched, we wouldn't have understood the format well
enough to edit it — and we'd have found that out cheaply instead of debugging a
mystery in the engine. **Round-trip before you edit.** It's the single most
useful hour in any format work.

### How the writer is built, and why it survived contact

It doesn't regenerate a file. It **copies the original byte-for-byte and
substitutes only the geometry span.** Every block of known size and unknown
meaning — the `vcount × 24` data (almost certainly tangents), the 80-byte bind
poses, the 161-frame animation tracks — is preserved verbatim rather than
invented. It also asserts the geometry round-trips before writing anything, and
refuses any edit that changes byte length.

That's a deliberately narrow tool, and the narrowness is why it worked on the
first attempt.

### The limit, stated honestly

**Vertex and index counts must not change.** They feed the `vcount`-sized
blocks, the bounding box and sphere, and a packed
`(icount << 16) | material_index` record.

```
SAFE      move vertices, rescale, rewrite UVs, reshape existing geometry
NOT YET   add or remove geometry
UNTESTED  skinned meshes — the test was a static box
UNTESTED  whether collision / .rmap matters once a shape changes
```

Identifying that `vcount × 24` block is the next real piece of work. Six floats
per vertex on every textured node; if it is tangent + binormal it's computable
from positions, UVs and normals, and adding geometry opens up.

### Two runs lost to the test bed, not the code

The first attempts used a throwaway sandbox install and gave a **grey screen
with no log at all**. Neither cause was the model:

1. **The exe was launched by full path from another directory.** TvT resolves
   `Scripts\`, `Models\` and its log path relative to the **current working
   directory**. Launch it from elsewhere and it finds nothing and has nowhere to
   write. Always `cd` into the game folder first.
2. **The sandbox had drifted** — 25 changed script files from earlier
   experiments, including one that wouldn't compile. A broken test bed produces
   a result that looks exactly like your change failing.

**The Level Editor turned out to be the better test bed**: it loads models
directly rather than through a mission, so there's much less between the file
and the answer.


---

## 2026-08-27 — a King Tiger in T-34 vs Tiger, and why the Germans never shot back

There's a Tiger II in the game now. ZeeWolf built the model years ago — mesh,
textures, armour values, even the kill rings on the barrel — and never wrote the
unit class that turns a model into a tank. That class now exists, in both the
REDUX build and ZeeWolf's, and it's the same file in each: generated from G5's
own Tiger I by renaming the class hierarchy and changing four things — the mesh,
the mass, the LOD list, and the header.

Mass 69,800 kg against the Tiger I's 56,000, on the **same** engine power. The
real Tiger II carried 25% more weight on the same Maybach, so the sluggishness
falls out of the numbers instead of being dialled in.

**The gun needed real ballistics.** The obvious move was to reuse the towed Pak
43's data — same weapon — but its penetration table is flat: 247 mm at 100, 500,
1000 and 1500 m alike. Working out what "correct" looks like meant checking how
G5 built theirs, and that turned up something else:

```
                   REDUX (G5)                  ZeeWolf
Tiger I KwK 36   120 / 110 / 100 / 93     175 / 175 / 175 / 175
T-34/85          115 / 105 / 100 / 92     145 / 145 / 143 / 136
T-34/76           80 /  70 /  63 /  58     65 /  60 /  43 /  23
```

G5's are the real published figures, and their shell velocities are real muzzle
velocity × 0.8 — KwK 36 Pzgr 39 is 773 m/s and they wrote `770.0*0.8`. The
German gun in the other build is inflated 46% and made immune to range, while
the Soviet 76 mm is gutted past 500 m. So the Tiger II went in on G5's
convention: 202 / 185 / 165 / 148 / 132. Sanity check — that's 1.68× the Tiger I
at 100 m, which is exactly the historical ratio.

### The gun pointed at the ground

First run in-game, the barrel drooped. The model's animation track turned out to
hold two values — the gun's elevation limits — and every G5 tank puts the
positive one in frame 0:

```
G5 Tiger    +6.5  /  -17.0
G5 PzIV     +8.0  /  -20.0
G5 T-34/85  +5.0  /  -20.0
King Tiger  -7.0  /  +20.0      ← backwards
```

Flipping the signs put it in G5's family on both numbers. Worth saying that the
first explanation offered was "different range, not a bug" — and it was shot
down in one sentence: *if that were true, every tank in the game would drive
around drooping.* Quite.

### And then nobody shot at anything

Dropping it into a mission, the whole German side turned out never to fire.
Not the new tank — **none of them, ever.** The log was unambiguous: nine Soviet
groups engaging, zero German attacks.

Three attempts to fix that failed. The mission never sent the German groups an
attack order at all, so that was added — they logged "engaging" and did nothing.
The attack handler turned out to end in this:

```
SetOrder_Attack([GetMission().GetMainPlayerObjectID()], ERT_AGGRESSIVE);
```

**Attack the player** — who is German. That handler was written from the Soviet
side. Telling the German groups to run it told them to attack their own force.
Arming them instead — radar on, fire on, aggressive — logged "engaging" and
still produced zero attacks, because arming a group is not ordering it to fire.

The actual cause is one line in shared script:

```
Array KillList = GetMission().GetPlayerObjectsIDList();
```

The retaliation logic seeds its kill list from **the player's own objects**.
That's fine for the Soviets, for whom the player IS the enemy. For a German
group it resolves to friendlies — and the log shows the German HQ shooting and
killing its own ZugWeidinger units. No German AI group can properly engage in
any mission, because only the side opposite the player ever gets a valid enemy
list.

### One more, if you've ever wondered why the gunner ignores the tank

There's exactly one target-priority table in the game, and it weights purely by
type and distance. Compare what it matches against what units declare:

```
units declare :  TANK  HEAVYTANK  ANTITANK  BTR  VEHICLE  HUMAN  SAU  AIR
table matches :  TANK  ANTITANK  BTR  HUMAN  AIR  TRUCK  ARTILLERY  AA_GUN
```

Trucks are classified `VEHICLE`. The zero-weight row is spelled `TRUCK`, and
**no unit in the game is classified TRUCK** — so trucks never got their intended
weight of zero and fell through to the default. `HEAVYTANK` had no row at all,
so Tigers carried no weight either. `ARTILLERY` and `AA_GUN` carry the two
highest weights in the table and match nothing.

In ZeeWolf's build it's worse: 65 of ~127 unit definitions had no weight at all.
And the Flak 88 is classified `["GER","GROUND"]` with no type at all — the
deadliest anti-tank gun in the game, invisible to target priority.

All of the above with Claude (Anthropic). The recurring lesson, again: the log
line that pointed at the friendly-fire bug was visible in the first log read
that day, noted, and not chased for three more runs.

## 2026-08-27 — one number in a model file, and 87 of 249 models were wrong

We can open T-34 vs Tiger's `.ms2` models in Blender now. Most of them came in
looking right, so we called the format solved. Then I opened ZeeWolf's Hummel
and the fighting compartment was a fan of splinters — hull, tracks, wheels and
the 15cm barrel all perfect, the top half shredded.

The cause turned out to be a block we'd already decoded. Sort of.

Each part of a model can use more than one texture — the Hummel's hull is one
material for the tub and another for the superstructure. The file stores that as
a little 16-byte record per material: how many triangles, which material, where
its triangles start, **and which vertex it starts counting from**.

That last number was the problem. Each chunk numbers its triangles from its own
starting vertex, not from the top of the part. Ignore it and the superstructure's
triangles get aimed at the hull tub's vertices. Hence splinters.

Why it hid so long: 14,817 of the 15,341 parts across both builds only use one
material, and when there's only one chunk that number is always zero. So the
wrong reading is indistinguishable from the right one 97% of the time — and
that's more than enough to look completely solved, and to write a confident code
comment describing the wrong structure. The other 524 parts are in 87 of the 249
models: both T-34s, both Tigers, the StuG, the SU-85, the Panzer IV, the
aircraft, the bridges.

The giveaway, once we looked: the Hummel's hull has 2349 vertices, but its
triangles never referred to anything past 1422. Half the vertices were
unreachable. A mesh that never touches half its own data is telling you
something.

Two side findings:

**One file in the whole library is damaged.** ZW's `u_veh_PnzIV_G_AI_.ms2`
wouldn't parse at all — three places where a `00` byte has become `48`, one of
them turning a count of 242 into 1.2 billion. But look at the filename: it ends
in an underscore. The model the game actually loads is the same name *without*
it. It's an orphan spare sitting in the folder, so nothing in the game was ever
broken. The importer now shrugs at damaged triangles instead of dying on them.

**The exporter had to be left alone.** Writing `.ms2` files back out works by
copying the original byte-for-byte and swapping only the geometry, and it checks
its own work by asserting the bytes round-trip exactly. So the fix could NOT go
where it naturally wanted to go — correcting the numbers on the way in would
have broken export on all 87 models. It's a separate accessor instead. Export
re-verified afterwards at 249 of 249 byte-identical.

Worked out with Claude (Anthropic) this morning. The lesson is one we'd already
learned once and got caught by again: a decoder validated on the common case is
not validated. 97% coverage looked exactly like 100%.

## 2026-08-27 — T-34 vs Tiger: measuring a mod's bias against the original

Long-running suspicion: the ZeeWolf 2015 build of TvT plays as though it has a
thumb on the scale. Settled it by diffing every unit against the **untouched
2001 original**, class by class.

**First, the control.** REDUX (the base I mod) turned out to be the 2001 release
essentially untouched on these fields — one Tiger `MaxPower` nerf and nothing
else. So "REDUX vs ZW" really is "original vs ZW".

**AI main-gun accuracy** (`FireDeviation`, lower = more accurate):

```
German   Pak 40      1.5  -> 0.5     3x better
         Panzer IV   1.5  -> 0.10   15x better
         Tiger I     1.2  -> 0.05   24x better
         StuG III    1.2  -> 0.02   60x better
Soviet   T-34/76     1.5  -> 1.6     worse
         T-34/85     1.25 -> 1.55    worse
         SU-85       1.2  -> 1.2     untouched
```

**Player guns — exactly one change in the entire game:** the T-34/85's,
`0.005 -> 0.15`. Thirty times less accurate. Every German player gun untouched.

**The control that removes all doubt:** the StuG III and SU-85 are the same class
of vehicle — casemate tank destroyers, no turret, same role, same era — and G5
set both to **exactly 1.2**. ZW made the StuG **0.02** and left the SU-85 at 1.2.
Sixty times apart from an identical start. There's no balance rationale for that.

Plus: Tiger +24% engine RPM, mass 56 t -> 40 t (real Tiger I is 57 t), fires
every 7 s instead of 12, while the T-34/85's turret traverse was **halved** and
the T-34/76's **cut fivefold**.

**23 values restored to G5's**, verified per class against the original.

### Two things worth passing on

**`FireDeviation` is a gameplay knob, not ballistics.** Machine guns sit at 0.15
and cannons at 1.2 — physically backwards. And the *same weapon* is 0.005 for
the player and 1.2 for the AI, because the player supplies aiming error through
the sight while the AI aims perfectly by definition. So 1.2 shouldn't be defended
as "historically accurate". What's defensible is G5's *relationship*: all AI
gunners inside a 20% band with a small edge to better platforms — roughly a real
German optics and training advantage of 10–30%, not 31×.

**Check what your filter EXCLUDES.** Two classifier bugs in one session produced
two confidently wrong aggregates: a side-classifier whose German list omitted
"German" filed German infantry as Soviet, and a unit filter matching
`Tank`/`SAU`/`Gun` silently dropped both T-34s — which led to declaring the
sensor ranges "even-handed" when they aren't. A partial sample that looks tidy is
more dangerous than an obviously broken one.

That second bug mattered: the Tiger detects at **2600 m** and the T-34/85 not
until **1650 m**, a 950 m window where it shoots and you can't see it. The
T-34/76 is worse — it engages at 2600 m while detecting at 800 m, and it's the
only vehicle in the game whose vision was *reduced*. First Soviet run after the
accuracy fix was still a quick death, and that's the obvious suspect.

Fixing accuracy while leaving a 950-metre detection head start doesn't help much.


---

## 2026-08-27 — T-34 vs Tiger: a 20 fps gunsight, and a mouse bug from 2001

> **AMENDED 2026-08-27, later the same day — read this before posting the
> above.** The gunsight fix is real and the numbers are real, but the
> explanation below is too broad. We then measured the *other* build,
> REDUX, which runs **double** the `FogFarMax` value — and its gunsight is
> **faster** than its external view (107 vs 83 fps). So this is something
> specific to the ZeeWolf build, not a property of the engine. Mission
> content and tree LOD were both checked and ruled out; what is actually
> different is not established. If this gets posted, post it as "here is a
> thing that fixed one build, and we do not yet know why the other build
> never had it" — which is the more honest and, frankly, more interesting
> story anyway.

Two fixes worth writing up, one performance and one that has been wrong since
the game shipped.

### The gunsight ran at 20 fps

External view of a treeline: ~100 fps. Switch to the T-34 gunsight, same
direction, don't move: **~20 fps.** Unaimable — I quit a session over it.

Counterintuitive, because zooming shows *fewer* objects. The drawcall probe
settled it:

```
                external    gunsight
draw calls           261       2105     8.1x
triangles        457,269  1,426,768     3.1x
frame time       7.50 ms   36.84 ms
```

**Draw calls up 8x but triangles only 3x** — many more objects, each cheap.
That's not more detail, that's *seeing further*. A magnified view extends draw
distance toward **`FogFarMax`**, which that mission had at **3000 m** against an
external `FogFar` of 500. Area scales with the square of radius, so it was
pulling in **36x the ground**.

Halving `FogFarMax` to 1500 quarters that. Combined with moving SpeedTree wind
from CPU to GPU (this engine is CPU-bound with the GPU idling at 24%, so CPU
wind is the worst available choice), the gunsight went **19.6 → 76.9 fps**.

**Two traps for anyone doing the same:**

`FogFarMax` is set in **both** `Atmosphere.script` and `Content.script`, and
**`Content.script` wins.** Editing the atmosphere file changes nothing and gives
you a false negative.

And **`FOVDistPower` does nothing at all.** It's in the registry, it has a video
menu row, and it sounds exactly like the setting you want. Every reference to it
lives inside that menu — it reads the value, displays it, writes it back, and
*nothing consumes it*. A leftover from Whirlwind over Vietnam, which shares this
engine. I burned two attempts on it.

Three wrong answers came before the right one, and all three were **inferred
from a setting's name** rather than measured. The probe found it in one run.

### The mouse bug — 25 years old

Separately: aiming felt right laterally and too fast vertically.

`Scripts/Common/PlayerUnit.script`:

```c
float MouseSpeed = 0.0015f * CGameSettings::MouseSensitivity / 0.5;
CameraLink.SetMouseSensitivity(MouseSpeed, MouseSpeed);
```

**`SetMouseSensitivity` takes separate horizontal and vertical sensitivities.
The game passes the same value to both.**

A 16:9 monitor's vertical field of view is 1.78x smaller than horizontal, so the
same angular rate crosses it 1.78x sooner. The gun really does move faster
vertically — and it always has. On a 4:3 CRT in 2001 it was 1.33x, so it was
milder, but it was never right.

Fixed with a `MouseVerticalScale` constant, default 0.5625 (1080/1920), applied
at all three camera call sites. 0.75 for 4:3, 0.42 for 21:9.

Worth saying: I found that one **by feel**, not by reading code. "About correct
laterally but faster vertically" turned out to be an exact description of a
1.78x ratio.

### And a warning about editing these files

TvT's scripts are CP1251 *and* CRLF. Reading one with Python's text mode
silently converts the line endings, and writing it back saves LF only — I
damaged **31 files** before noticing, and only noticed because one shrank by
2,773 bytes.

**Edit them as bytes**, and **check the file size after every write.**
`grep -c $'\r'` will happily tell you everything is fine when it isn't.
