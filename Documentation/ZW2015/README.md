# ZeeWolf 2015 (ZW)

Notes on the **ZeeWolf 2015** payware mod, kept separate from the main
documentation on purpose.

**What belongs here:** anything that is true because of choices ZeeWolf made —
his map sizes, his forest painting, his mission inventory, the state of his
install, calibration that only applies to his content.

**What does NOT belong here:** engine behaviour. ZW's `Behavior.dll`,
`Engine.dll` and `UI.dll` are **SHA-256 identical to REDUX's**, so anything
found in the engine through ZW is equally true of REDUX and belongs in the main
`Documentation/` tree. The wingman `Follow`/`Formation` order conflict is the
example worth remembering: it surfaced in ZW, but it is a `CWingmanTask` bug
that REDUX carries too, so it is written up in
[`../TvT_AI_Engagement_Logic.md`](../TvT_AI_Engagement_Logic.md), not here.

The test: **would this still be true if ZeeWolf had never existed?** If yes, it
goes in the main tree.

---

## Contents

| | |
|---|---|
| [Mission_Inventory.md](Mission_Inventory.md) | every ZW mission: world size, heightfield, zone map, how much of it is painted vegetation |
| [Line_Of_Sight.md](Line_Of_Sight.md) | running the LOS hook on ZW, and why its forests needed a 13x calibration |
| [Rendering_And_Framerate.md](Rendering_And_Framerate.md) | the white-terrain fix, the CPU floor, the graphics wrappers, and the LAA flag |
| [Mission_script_dumps/](Mission_script_dumps) | flattened script dumps of ZW's own missions, for reading and diffing |

---

## The install

`M:\T34vsTiger_ZW2015`. A separate install from the live REDUX one at
`M:\T34vsTiger` — see the main project map. Both are on the same engine
binaries; everything else diverges.

**Launch `TvsT_fullLOD_HARD_4GB.exe`.** Every other executable in that folder
is limited to 2 GB and will fail on the larger maps. See
[Rendering_And_Framerate.md](Rendering_And_Framerate.md).
