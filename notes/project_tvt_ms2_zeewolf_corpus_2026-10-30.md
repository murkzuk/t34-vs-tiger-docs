# ZeeWolf's library: the first corpus we did not author ourselves

2026-10-30. Every format check until today used G5's 2005 exports plus files we wrote
ourselves. `M:\T34vsTiger_ZW2015` is ZeeWolf's mod - models he authored through the Maya 5
path while it was current, plus the G5 models he kept or re-authored. It is the first
independent corpus available, and it is bigger than the original game's:

    M:\T34vsTiger_ZW2015\Models    184 .ms2, 502 MB
      120 unique to ZW               never seen by our reader
       56 byte-identical to G5       left alone
        8 re-authored G5 models      same name, different content

## Results

    walk every file to exact EOF                184 of 184
    import -> export untouched, byte-identical  184 of 184, 0 differ, 0 errors

Then three subjects end to end - import in Blender, edit, export, load in the sandbox:

| subject | provenance | result |
|---|---|---|
| `4MeterBox.ms2` | his re-author of a G5 prop | untouched identical; pyramid added; **loads** - hierarchy shows his `ROOT` + `pCube1` |
| `u_veh_t34_85_44_2.ms2` | his T-34/85, 12.9 MB, 219 nodes | untouched identical; pyramids on `Body` and `Body_LOD1`; **loads with both** |
| `bld_BermPlacement.ms2` | **his own - G5 never shipped one** | untouched identical; pyramid added; **loads as `Cbld_BermPlacementModel`** with his script and textures |

The third one is the strongest of the three: an asset that does not exist in our install at
all, brought in as `Models\bld_BermPlacement.ms2` + his `.script` + his `.tex` files, and
drawn by the engine with his materials.

## What his files do that G5's do not

* **An empty `ROOT` node carrying data.** His props have a `ROOT` with bbox
  `FLT_MAX/-FLT_MAX`, **one** animation frame, bind poses `n=1`, and flags `0x00010001`.
  Two bits in his mesh nodes - `0x100000` and `0x400000` - are ones this project has never
  modelled; the walk is exact on all 184 files, so they gate no blocks there, but what the
  engine does with them is unknown.
* **`d_count = 1` exists in the wild.** A one-frame track is demonstrably legal, since his
  models load in his own install. `d_count = 0` remains untested - relevant to anyone adding a
  brand-new node rather than growing an existing one.
* **Node names are his, not G5's.** His T-34/85 reads `Body`, `GearR`, `GearL`, `Corner_LR`,
  `Corner_RR`, `Vapor_L`, `Smoke_1`, `HullEngine`, `HullGunner`, `HullDriver`,
  `Body_driver`, `Body_commander` - there is no `Turret_A` or `Weapon_A`. Anything that
  addresses nodes **by name** (turret traverse, gun elevation, damage effects) will look for
  G5's names and silently attach to nothing. A model can therefore load, look perfect, and
  have some behaviour quietly dead. Not a format issue, but it is the next trap.
* **A model's script names more textures than the diffuse map.** `bld_BermPlacement.script`
  references `BermPlacement1.tex` **and** `BermPlacement1_NRM.tex`; copying only the diffuse
  map leaves the console reporting
  `Unable to load texture file Textures\BermPlacement1_NRM.tex`.

## Bringing in a new asset, in full

    Models\<name>.ms2          the model
    Models\<name>.script       material table AND the class name - this is what makes it
                                appear in the Asset Browser as C<name>Model
    Textures\*.tex             every texture the script mentions, bump maps included

To *place* it in a mission as well, it needs a unit script and a `Scripts/Editor/MenuConfig.script`
entry - the difference between "the engine can draw it" and "you can build with it".

## The near-miss worth recording

The first run of the corpus sweep reported **131 of 131 byte-identical** - which was 66 + 65,
the two G5 folders, because a copied script kept its hard-coded paths and printed a clean pass
on the wrong input. Same shape as everything else that went wrong today: the result was
green, confident, and about the wrong thing.
