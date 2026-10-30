# AI gunner target acquisition — PARKED 2026-08-25, with what was ruled OUT

The goal: the AI is now blind behind terrain, but the **player's own gunner**
still tracks targets through hills. Closing that means finding where the chosen
target is stored, then vetoing a choice with no line of sight.

**Not achieved.** Parked after three wrong field identifications in one session.
This note exists so none of them is tried again.

## RULED OUT — do not re-test these

| Candidate | Why it was believed | How it was disproven |
|---|---|---|
| `CAutoCommanderComponent` fields `+0xD8..+0xF4` | It is the acquisition class, and the block held object pointers | **6 changes at init, then NOTHING across 153,545 updates.** `+0xE0` there is a `CStringVariable`. Static infrastructure, not state |
| `CAutoShooterComponent +0xE0` = the target | An older note inferred it from a static read count ("touched 13 times in the update") | **Held ONE value (2AF61D40) across all 1040 samples** while many targets were engaged. It is a **`CWeapon`** — the component's own gun |
| `CAutoShooterComponent +0x060` = the target | Cycled null → object → null 17 times, resolved to `CAnimatedObject` with real map coordinates | The observer hunt killed it: it sits **0–3 m from `+0xE0`, the weapon**. Two things 3 m apart are parts of the same vehicle. It is almost certainly the **gun's aiming animation** starting and stopping |
| `+0x0D4` / `+0x0DC` | Changed constantly, passed a naive pointer filter | **Floats**, drifting around 0.6287. The filter was a range check; a float like `12.0f` is `0x41400000` and passes it |

## What IS solid

- `CAutoCommanderComponent::Update` = **vtable slot 7, RVA `+0x041120`**. Hooked,
  stable, ~460k calls a session. It is a **small dispatcher** — no float member
  reads, and **no calls to the vector-length helper** the gunner's range gate
  hangs off. So the gate fix is NOT copyable here.
- Commander fields, from a live-object scan: `RadarMaxDistance +0x64` (3100),
  `RadarUpdateTime +0x60` (4.0), `ViewAngle +0x31C`, `PreferedTargets` distance
  `+0x320`. Two tiny getters at `+0x132220` / `+0x132F50` are
  `fld [ecx+0x64]; ret`.
- On the shooter: `+0x118` clears 1 → 0 and the UI byte `+0x9CD` goes 0 → 1
  when the AI gunner is working. Those ARE the gates, and they open.
- `+0xE4` is a **`CWeapon2`** which sat **572 m** from the gun — the only field
  found so far that is plausibly at a different vehicle. **Unexamined. Start
  here next time.**

## The method that stalled, and why

"Search the live object for values the script sets" cracked
`CAutoShooterComponent` in one run. It did **not** converge here, because the
target is a *pointer that changes*, not a *constant the script wrote* — there is
no known value to search for. Watching for change instead produced three
plausible-but-wrong candidates.

**Two traps worth remembering:**

1. **A range check is not an object test.** Floats pass it. `is_object()` (in
   `hook.cpp`) now also demands the first word be a readable vtable pointer.
2. **The sweep locks onto the FIRST component instance it sees** — and *every AI
   tank has one*. There is no proof the watched instance was the player's. That
   alone could explain everything above.

## The better route, for whoever picks this up

**Do not hunt the field. Use the endpoints the gate already proves.**

`hook.cpp`'s range-gate filter finds observer and target **by arithmetic** — it
searches the caller's frame for the pair whose difference equals the delta it was
handed. Self-validating, and it recorded **0 unmatched** over 6000 checks. That
is a *known-good* source of both positions, already working, no offsets guessed.

The gate does not always run, but when it does the positions are trustworthy.
Logging them alongside whatever the shooter holds would identify the target field
by correlation rather than by guesswork.

## Status

**PARKED.** The AI half of line of sight is done and shipped; this is the
player's-crew half and it is not blocking anything. Related:
[[project-tvt-player-crew-vision]], [[project-tvt-two-vision-systems]].
