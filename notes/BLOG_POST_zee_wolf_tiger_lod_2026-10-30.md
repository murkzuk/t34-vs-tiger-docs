# Giving ZeeWolf's Tiger I a level of detail

*T-34 vs Tiger is a 2001 tank sim that people are still modding. ZeeWolf's Tiger I is one of
the best-looking things in it. It also has no level of detail, which means the game draws every
one of its ~68,000 triangles at every range — including when the tank is three pixels wide.
This is the story of adding one, and of the three things the file format doesn't tell you.*

## What a level of detail is

When a tank is close, you want detail: bolts, grilles, track links. When it's 300 metres away,
you want the same silhouette and almost nothing else. So games ship several versions of the same
model and swap between them by distance. G5, the original developers, did this everywhere — their
Tiger I has 165 extra "level" meshes. ZeeWolf's Tiger has none, so it is drawn in full detail no
matter how far away it is.

Fixing that means writing these extra meshes into his model file, in a format nobody documented.

## The format, briefly

A `.ms2` model is a list of parts. Each part has a name, some geometry, and a parent — the joint
it hangs from. A part can have extra siblings whose names end in `_LOD1`, `_LOD2` and so on: those
are the cheaper copies. The game picks one by distance and draws that.

So in principle you add a `Body_Hull_LOD1` next to `Body_Hull`, make it simpler, and you're done.
In practice we added four of them and the game ignored all four.

## Thing one: that zero in the header is not a flag

Every part record starts with a small number that, for twenty years, everyone has written down as
"a flag, always zero". It is not a flag. **It is the level number.** Zero means "this is the
full-detail mesh".

We had written four new levels with that field set to zero, because every tool ever written did.
As far as the game was concerned, we had added four more full-detail meshes and given it nothing
to switch to. It read the file perfectly, the geometry was correct, the file even round-tripped
byte-for-byte. It just did nothing.

Checking G5's own files settled it: on the model whose levels visibly work, every level mesh has
that field equal to its number — `_LOD1` is 1, `_LOD4` is 4 — and 96% of all the other parts in
both game installs have zero. Written correctly, the levels appeared.

## Thing two: a level mesh sits at the origin

A level mesh hangs off its parent part, and the parent already knows where it is. If you copy the
transform onto the level as well, it gets applied twice.

The first build had every new level floating away from the part it belonged to. The hull sat
sunk into the ground and both tracks were a couple of metres out from the wheels. G5's files show
the rule plainly once you look: their level meshes all sit at exactly zero, and their parents
carry the real offsets.

## Thing three: the dark panel wasn't a hole

With the geometry in place it rendered with what looked for all the world like a hole punched
through the front plate — a rectangular black patch where a grille should be. The natural reading
is "the simplifier tore the armour open", and that would have sent us off rewriting the
simplification.

The test that settled it: render with a flat, unlit material. If the black patch survives, it is
missing geometry. It didn't. 754 pixels out of 410,000 differed, and all of them were on the
outline, where the silhouette had moved by a pixel. **There was no hole.**

The panel was black because it was being *lit* as if it faced away from the sun. Levels need the
original model's surface directions carried over, and at a recess the nearest bit of original
surface can belong to a different face, pointing the other way. Keeping the original direction
only where it agrees with the geometry it was put on took the brightness difference between the
two levels from 8 levels out of 255 down to 0.4.

## Cutting the triangles without wrecking the tank

The obvious tool is a simplifier: merge triangles until you have half as many. That went badly
at first. These models are not solid objects — they're piles of separate armour plates, and every
edge is stored twice, once for each side. Simplify aggressively and the plates either tear open
or round off into pillows.

What worked was restraint: halve the triangles, leave the texture coordinates alone, carry the
surface directions over, and accept that details finer than the new triangle size simply go.

## The result

| | triangles | vertices |
|---|---|---|
| Full detail | 68,105 | 85,149 |
| **With LOD1** | **35,073** | **55,896** |

**48.5% fewer triangles** at distance, and the tank's brightness matches to within half a level
out of 255, so switching levels doesn't flash.

All 95 parts that are actually drawn now have a cheaper version — including the tracks, which are
skinned to the wheels and can't be simplified safely, so they're copied verbatim and simply stay
full detail. The 190 original parts are byte-for-byte untouched.

What you lose: the grille slats disappear into a solid panel, the road wheels lose their rim
relief. At the range a level of detail is drawn, neither reads.

## What's still missing

The model *has* a level of detail now. The game doesn't necessarily *use* it: his four playable
Tiger variants all set their switch distances to `[0]`, which is ZeeWolf deliberately turning
level-of-detail off because his model had nothing to switch to. That's the next job — and then
the same recipe twice more for LOD2 and LOD3.

The tools are in the project repo: a Blender add-on that imports and exports `.ms2`, plus the
handful of scripts that built this ladder.
