# How big the engine really is, and what it remembers

*2026-08-19. Two questions answered by reading the files rather than assuming:
how large a world the G5 engine actually supports, and whether anything can
carry between missions. Both came out of a "just for giggles" look at Whirlwind
over Vietnam, and both are more encouraging than expected.*

---

## 1. TvT runs at 1/81 of the engine's shipped world size

| | world | height grid | cell | relief | mean gradient |
|---|---|---|---|---|---|
| **WoV** | **81,000 m** | **4097** | 19.8 m | **881 m** | 4.8% |
| ZW2015 (reworked maps) | 18,000 m | 2049 | 8.8 m | 306 m | 6.0% |
| TvT / REDUX | 9,000 m | 2049 | 4.4 m | 232 m | 7.2% |

Whirlwind over Vietnam — same engine, same `.script` language, released a year
earlier — ships **81 km square** maps on a **4097** height grid. That is 6,561
km² against TvT's 81, and a 33.5 MB heightmap against TvT's 8.4 MB.

So the 9 km map is not an engine limit. It is a decision G5 took for a tank game
and nobody has revisited in twenty years.

### And WoV shares one terrain across a whole campaign

```
G:\WoV\Missions\Campaign_1\hmap_c1.raw          33,570,818 bytes
G:\WoV\Missions\Campaign_1\Mission_1\WorldMatricies.script:
    ImageFileName = "Missions/Campaign_1/hmap_c1.raw"
```

Not `Mission_1/hmap.raw` — **`Campaign_1/hmap_c1.raw`**. All **eleven** missions
in that campaign sit on one 81 km terrain at different places on it.

TvT abandoned that. Every TvT mission gets its own private 9 km island, which is
why the generated Kursk missions all share one byte-identical heightmap — there
was no better option available.

### What ZeeWolf actually did, since the question came up

Not a blanket 2× scale. Three campaign missions (C1M2, C1M3, C1M4) have
heightmaps **byte-identical to stock** and are still declared at 9000 m —
untouched. The nine he reworked carry genuinely new height data at 18,000 m.

And he compensated properly: `FloatValueFactor` is unchanged at `0.07 × 257`,
but the per-sample height variation is nearly doubled (0.53 m against 0.32 m),
so the gradient lands at ~6% against stock's ~7%. A naive stretch would have
halved the slopes and produced a pool table. This did not.

One oddity: two different ZW maps bottom out at **exactly 374.8 m**, while the
stock maps they replace sit at 532.0 and 526.3 with no relation to each other.
That suggests a common baseline or a shared generation step.

---

## 2. Nothing carries between missions — but the parts to make it are all here

### What does not exist

Checked and absent in both TvT and WoV:

- **`Campaigns.rsr`** holds localised names only. WoV's has mission titles;
  TvT's is 264 bytes of "USSR. Summer 1944."
- **`IPersistent`** (`Common\BasePersistence.script`) is real — `GetToken()`,
  `GetState()`, `SetState(variant)` — and WoV uses it more widely than TvT
  (cockpit, passenger units, player unit). But it is object-level save and
  restore *within* a session, not between missions.
- No save files, no profile data, nothing under `HKCU\Software\G5 Software`.

WoV's one-map campaign is therefore a **content** decision, not a dynamic
campaign. Missions share ground; nothing carries forward.

### What does exist, and is better than expected

`Common\Mission.script` has a death handler that fires for **every object**:

```
Component DeadThing = GetObject(_ObjectID);
String Killer = DeadThing.GetLastDamager();
if (Killer == MainPlayerID)
{
  if (checkMask(DeadThing, ["TANK"],[]) || checkMask(DeadThing, ["HEAVYTANK"],[]))
    m_PlayerVictims_Tanks++;
  else if (checkMask(DeadThing, ["ANTITANK"],[]) ...
```

Three things matter here:

1. **The event is unfiltered.** It fires for everything that dies, with its
   object ID. Only the *counters* are gated on the player.
2. **`GetLastDamager()` gives attribution** — not just what died, but what
   killed it.
3. **The totals already reach the UI.** `Menus\EndMissionMenu.script` reads
   `Mission.m_PlayerHits`, `m_PlayerVictims_Tanks` and the rest to draw the
   debriefing.

So the engine tracks deaths, attributes them, and exposes them to script. It
simply never writes them down. The counters are player-only, but the *event* is
not — the information is all there and unlogged.

---

## 3. What a one-map dynamic campaign would actually take

The idea: one large terrain, start at one end, and where the next mission
begins depends on how the last one went.

| piece | status |
|---|---|
| A world big enough | **engine-supported** — WoV runs 81 km on a 4097 grid |
| One terrain shared by many missions | **engine-supported** — WoV does exactly this |
| Generating missions onto it | **built** — `Tools/MissionGen/gen_mission.py` |
| A menu that lists more than seven | **fixed** — see the mission authoring notes |
| Reading the outcome | **~5 lines** |

That last one is a `logMessage` inside the existing death handler, before the
`Killer == MainPlayerID` test:

```
logMessage("[CASUALTY] " + _ObjectID + " killed by " + Killer);
```

Every death, both sides, named, with attribution, into `execution.log` — a file
the tooling here already parses routinely.

The campaign layer then lives entirely outside the game: read the casualties,
work out who survived and where the line ended, write the next mission's
`Content.script` on the same terrain with what is left. No engine work at all.

**The honest gap** is that survivors' final *positions* are not logged, only
deaths. Either log those too from the mission script, or accept that each
mission starts from planned lines rather than exactly where the last one
stopped — which is arguably how a real staff would do it anyway.
