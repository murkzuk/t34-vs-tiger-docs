
## PLAYABLE - it already was (2026-09-01)

Two options were being weighed to get a driveable Tiger II: borrow ZW's Panther
interior (closer match than Tiger I), or skip the interior entirely and use only
the F-key views. **Neither is needed.**

`CTankPzVI_KingTigerIIUnit` **extends `CTankPlayerUnit`** - the same marker the
playable T-34/85 and Tiger I carry - and already has three `CPlayerWeapon` mixins.
AI-only units extend plain `CTankUnit`, which is exactly why the T-34/76 is still
not playable.

| unit | extends | |
|---|---|---|
| `T34_85_44` | `CTankPlayerUnit` | playable |
| `TankPzVIAusfEUnit` | `CTankPlayerUnit` | playable |
| **`TankPzVI_KingTigerIIUnit`** | **`CTankPlayerUnit`** | **playable** |
| `T34_76_42` | `CTankUnit` | AI only (open TODO) |
| `TankPzVI_AI_Unit` (ZW) | `CTankUnit` | AI only |

Its mesh setup is character-for-character what ZeeWolf ships on his own **playable**
Tiger E1 - same borrowed Tiger I interior, same single LOD:

    SetupExtendMesh(getMeshObjectName(), "Cu_veh_PzVI_MAIN_InsideModel");
    GetMeshComponent().SetLods([0]);

So the Tiger I interior is not a compromise to work around - it is the proven
configuration already shipping in a playable tank.

### Set up as the player tank
`Missions\MyMission\BerezovKursk\Content.script` - the mission's player was
already a Tiger I, so it was a one-token swap:

    "MainPlayerUnit", "GameObject", "CTankPzVIAusfEUnit"
      -> "CTankPzVI_KingTigerIIUnit"

+7 bytes, CRLF unchanged (3675), no encoding change. Backup:
`K:\TvTDeepseekollback\BerezovKursk_Content.script.bak.*`. Cache cleared.
The mission still has its original King Tiger placed separately, so there are two.

### Comment corrected
The file's own header claimed "this is an AI unit" and that a playable version
needed a `Cu_veh_PzVI_KingTigerII_PlayableModel` named in `PlayerUnit.script`.
Both were wrong (I wrote them) - `PlayerUnit.script` names no such model. Corrected
in both builds; backups in `K:\TvTDeepseekollback\*_KingTigerII.script.bak.*`.

### Not yet verified
It has not been driven yet. Structurally it matches the playable pattern exactly,
but the proof is loading BerezovKursk and checking `execution.log` is clean.
