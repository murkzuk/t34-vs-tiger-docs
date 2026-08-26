# Unshipped and half-finished content

## The extended vehicle roster is ZEEWOLF'S, not G5's

Checked 2026-08-26, because "G5 planned a Tiger II" is a natural assumption and
it is wrong.

```
Original (G5, 2001)   12 death strings in Messages.rsr - exactly the 12 that shipped
ZW 2015               41 - Panther, KV-85, KV-1, KV-1S, SU-122, SU-152, Nashorn,
                           Hummel, Wespe, Marder II, PzII C, PzIII L24/L60,
                           StuG F8, Sturm Haubitz, sIG33B, Studebaker... and KingTiger II
REDUX                 41 - inherited from ZW
```

**The original install has no Tiger II anywhere** - not in `Messages.rsr`, not in
`Piercing.script`, not in `Models/`. G5's own unfinished business is elsewhere
(see the WoV engine lineage notes); the big roster is ZeeWolf's, and he shipped
working unit classes for nearly all of it.

**Reading `.rsr` files:** they are **UTF-16LE**, not CP1251. `strings` and a
CP1251 grep both return nothing, which is why this went unnoticed. Use
`iconv -f UTF-16LE -t UTF-8`.

## THE KING TIGER IS ~90% BUILT AND ONE FILE FROM WORKING

In `M:\T34vsTiger_ZW2015`. Everything a tank needs exists except the unit class.

| piece | state |
|---|---|
| `Models/u_veh_KingTiger.ms2` | 11.9 MB mesh, Nov 2013 |
| `.rmap` | present - pathfinding footprint done |
| `Models/u_veh_KingTiger.script` | full material/skin definition |
| `Textures/` | 16 King Tiger textures |
| `Armour.script` | full per-facet table, real values |
| `HitPoints.script` | 8 entries |
| `Bullets.script` | gun, MG and debris control classes |
| `Explosions.script` | 28 entries |
| `Messages.rsr` | `str_DeathKingTiger = "KingTiger II"` |
| `Editor/MenuConfig.script` | placement entries written but **COMMENTED OUT** (lines 229-230) |
| **unit class** | **MISSING** - `CTankPzVI_KingTigerIIUnit` is referenced and never defined |

Armour is properly entered, not placeholder:

```
turret front 185 mm    turret rear/sides 81 mm    turret top 41 mm
```

Two variants were intended: `CTankPzVI_KingTigerIIUnit` and
`CTankPzVI_KingTigerII_WUnit` (winter).

### The gun is already there, and it is the correct one

`Piercing.script` has no `KingTiger` constants - but it does not need them.
**The KwK 43 L/71 is ballistically the same weapon as the towed Pak 43**, and
`GunHvyPaK43*` is fully defined. The engine already shares guns this way (the
SU-85 uses the T-34/85's 85 mm).

**But the Pak 43 penetration table is flat and should be fixed if it is reused:**

```
GunHvyPaK43    100 m: 247    500 m: 247    1000 m: 247    1500 m: 247    8800 m: 144
TankT34_85_44  100 m: 115    500 m: 105    1000 m: 100    1500 m: 92     2000 m: 85
```

The near columns were filled with `1.0` and left. `MaxDistance` is also 8800 m -
right for a towed gun in an artillery role, wrong for a tank gun.

### No further build is coming from upstream

**ZeeWolf has died.** The user recalls he was further along with the Tiger II
than what survives here, but that work is not on these drives - searched
2026-08-26 across all 19 TvT folders on `M:` plus every archive
(`- Original.zip`, `REDUX0.001/0.002.zip`, `T34vsTiger.7z`, `MODS.7z`). Only
`T34vsTiger_ZW2015` and its `- Copy` hold King Tiger files, both with the same
three model files and **no unit class in either**.

So what is documented above is the complete surviving state. Finishing it means
completing his work, not waiting for it.

### How deeply it was wired in - the system side is DONE

Beyond the model and armour data, `CTankPzVI_KingTigerIIUnit` is referenced by
name throughout the shared code:

```
PlayerUnit.script:175   crew-voice table - gunner calls it a heavy target and
                        asks for AP. Names Cu_veh_PzVI_KingTigerII_PlayableModel
PlayerUnit.script:240   death-message mapping
Mission.script:193      sits in the GERMAN UNIT ROSTER, between the Panthers and
                        the Tiger E1s, alongside every unit that works
Strings.script:131      msg_DeathKingTigerII -> str_DeathKingTiger
```

**`Cu_veh_PzVI_KingTigerII_PlayableModel` is named once and never defined.** The
shipped mesh's class is `Cu_veh_KingTigerModel` - the external/AI model. There
is no interior mesh.

### The Panther is the finished version of the same plan

```
Panther D    u_veh_Panther_D.ms2  +  _D_Playable.ms2  +  _D_Inside.ms2
             Tank_Panther_D.script + Tank_Panther_D_Playable.script + AI + winter

King Tiger   u_veh_KingTiger.ms2 ONLY
             no Playable mesh, no Inside mesh, no unit class
```

Use the Panther as the template - it is the same author solving the same
problem, completed.

### TWO DIFFERENT JOBS - do not conflate them

**An AI-only King Tiger is genuinely one file.** External mesh, rmap, 16
textures, armour, hitpoints, bullets, explosions, death string, roster entry and
editor lines all exist. Write the unit class, uncomment
`Editor/MenuConfig.script:229-230`, clear the cache.

**A PLAYABLE King Tiger needs two more meshes** - `_Playable` and `_Inside`.
That is 3D work, an interior modelled from scratch, not scripting. He wired the
entire system side and stopped before the cockpit.

### What building the AI version would actually involve

1. Copy `Scripts/Units/TankPzVIAusfEUnit.script` as the template - it is the
   closest existing heavy.
2. Point `getMeshObjectName()` at `Cu_veh_KingTigerModel`.
3. Reference `CPiercing::GunHvyPaK43*` for the main gun, and give it a real
   penetration falloff rather than the flat table above.
4. Uncomment the two editor lines in `Scripts/Editor/MenuConfig.script`.
5. Clear `Cache\Scripts.cache` and place one in a test mission.

**A session's work for the AI version, not a project** - the expensive parts
(mesh, textures, armour, router map) are all done. The playable version is a
different and much larger job, see above. `Bullets.script:67` carries a `//jeff`
comment, so the user has been through this before.
