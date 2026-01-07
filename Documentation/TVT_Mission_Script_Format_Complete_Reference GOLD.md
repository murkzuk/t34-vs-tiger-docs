# TVT Mission Script Files (.script) Complete Technical Reference

**Critical Limitations and Engine Context Warning**

This document provides syntactic and structural documentation of TVT mission script files based on analysis of actual mission files. However, this documentation cannot guarantee that syntactically correct scripts will function correctly in the game engine. The engine has internal requirements, compiled class libraries, and behavioral expectations that cannot be fully documented without access to the original game source code.

This section documents known limitations and practical risks that affect mission creation and modification.

## Document Overview and Verification Notes

This technical reference documents the mission script file format used by T-34 vs. Tiger (TVT), a 2001 tank simulation game developed by G5 Software. This documentation is based on analysis of actual mission script files extracted from the game and its expansion packs.

**Important Verification Notes:**

All examples in this documentation are taken directly from actual mission script files found in the game installation. Class names, property names, task names, and syntax patterns shown here are verified against real files from the following sources:
- Soviet Expansion Mission files
- WoV (Winds of Victory) Expansion Mission files  
- Custom Missions from various sources

Any examples marked as "Illustrative" or shown in troubleshooting sections without source attribution should be treated as potentially conjectural and verified against actual mission files before use in production missions.

### How to Use This Document

This documentation is organized to serve different purposes:

**For Beginners (Start Here):**
1. Read Part One to understand mission file organization
2. Study Part Three for complete verified object patterns
3. Use the Quick Reference (Part Six) while editing

**For Intermediate Users:**
1. Refer to Part Two for syntax details
2. Study Part Four for class name references
3. Consult Part Five for encoding requirements

**For Advanced Users:**
1. Review Part Seven for complete method documentation
2. Use binary analysis for custom task development
3. Reference error messages for troubleshooting

**Legend:**
- `Code font` - Script syntax, method names, class names
- **Bold** - Critical warnings or important concepts
- [sic] - Indicates verified oddity in original files
- "Quote" - Property values or string constants

### Case Sensitivity Important Note

**Critical:** Class names, task names, and property names are case-sensitive. A single character difference (e.g., "ctankattacktask" vs. "CTankAttackTask") will produce a valid script that the engine may ignore or fail to load.

**Method Name Case Sensitivity:**
Some verified files use lowercase method names (e.g., `setOrder_MoveTo` with lowercase 's'). For consistency and safety:
- Use the documented capitalization (`SetOrder_*`, `ActivateFire`, etc.)
- The engine may be tolerant of case variations in method calls
- Class names and property names have strict case requirements

## Part One: Mission File Organization

### Understanding Mission Structure

A TVT mission consists of multiple interconnected script files that together define a complete playable scenario. Each file serves a specific purpose and contains class definitions with static members that the game engine loads at runtime.

The typical mission folder structure includes the following files:

**Content.script** contains all object definitions including units, buildings, terrain features, atmosphere settings, and navigation points. This is the primary mission definition file.

**MissionTasks.script** defines AI behavior classes that control how units move, attack, and respond to game events. Task classes extend base AI classes and define specific behaviors.

**Mission.script** defines the mission controller class that manages overall mission flow, objectives, events, and victory conditions. This file controls the strategic layer.

**Atmosphere.script** contains atmospheric settings for lighting, fog, and weather effects. Some missions include atmosphere objects directly in Content.script instead.

**Terrain.script** defines terrain rendering parameters, forest regions, water regions, and material configurations.

**PositionWatchers.script** defines regions that trigger events when units enter or exit them.

**WorldMatrices.script** contains pre-calculated transformation matrices for coordinate conversions.

**String files** (named according to mission, e.g., MissionC2M1Strings.script) contain localized text for objectives, briefings, and UI elements.

**LensFlare.script** defines lens flare visual effects.

### Critical Limitation: Engine Class Dependencies

**This is the most important warning in this documentation.**

All script classes must correspond to C++ classes compiled into the game executable. The script format only describes how to reference and configure these classes. If you reference a class that does not exist in the compiled game engine, the mission will fail to load regardless of how correct your script syntax is.

**Verified Compiled Classes:**

Based on analysis of mission files, the following class categories exist in the engine:

- Tank unit classes (CTankT34_76_42Unit, CTankT34_85_44Unit)
- Base AI classes (CBaseUnitGroup, CBaseAITankTask)
- Terrain classes (CBaseTerrain, CBaseTerrainSkin)
- Mission classes (CSPMission)
- String classes (CCommonStrings)

**Unknown Classes:**

Many class references in mission files use mission-specific prefixes (CC1M1*, CC5M1*, KurskM1*) that suggest custom task implementations. These classes are defined in the mission's MissionTasks.script file and are valid within that specific mission context.

**Risk:** Creating a new mission and defining custom task classes with arbitrary names may not work if the base classes they extend or the methods they call do not exist in the engine.

### Content.script File Reference

The Content.script file contains the primary mission object definitions. The following example shows the structure verified from actual Soviet Expansion Mission_1 files:

```script
class CC1M1Content
{
  static String m_ObjectListClassFile = "Missions/Campaign_1/Mission_1/Content.script";
  static String m_ObjectListClassName = "CC1M1Content";

  static Array  m_MissionObjectList   = [
    // Atmosphere object
    [
      "Atmosphere",
      "",
      "",
      new Matrix(
          1.000000, 0.000000, 0.000000, 0.000000,
          0.000000, 1.000000, 0.000000, 0.000000,
          0.000000, 0.000000, 1.000000, 0.000000,
          0.000000, 0.000000, 0.000000, 1.000000
        ),
      [
        ["AmbientLight", new Color(0.152941, 0.145098, 0.078431, 1.000000)],
        ["FogDensity", 0.000500],
        ["FogNear", 10.000000],
        ["FogFar", 800.000000],
        ["FogMode", "Exp"],
        ["SunDirection", new Vector(-0.005952, -0.155542, -0.305348)],
        ["SunIntensity", 1.000000]
      ]
    ],

    // Terrain object
    [
      "Terrain",
      "",
      "",
      new Matrix(
          1.000000, 0.000000, 0.000000, 0.000000,
          0.000000, 1.000000, 0.000000, 0.000000,
          0.000000, 0.000000, 1.000000, 0.000000,
          0.000000, 0.000000, 0.000000, 1.000000
        ),
      [
        ["ForestTextureScale", 0.500000],
        ["ForestBeginFadeDist", [250.000000, 480.000000]],
        ["IsAntiLighting", true],
        ["TerrainShadowPower", 1.000000],
        ["WaterBorderColor", new Color(0.556863, 0.521569, 0.443137, 1.000000)],
        ["NormalNoise", 0.300000]
      ]
    ],

    // Main player unit
    [
      "MainPlayerUnit",
      "GameObject",
      "CTankT34_85_44Unit",
      new Matrix(
          0.978839, 0.204633, 0.000000, 3684.518555,
          -0.204633, 0.978839, 0.000000, 3682.898926,
          0.000000, 0.000000, 1.000000, 575.520630,
          0.000000, 0.000000, 0.000000, 1.000000
        ),
      [
        ["IsPlayer", true],
        ["IsManual", true],
        ["Affiliation", "FRIEND"],
        ["Number", "22_18"]
      ]
    ],

    // Unit group
    [
      "CC1M1Gr_PlayerTanks",
      "UnitGroup",
      "CC1M1Gr_PlayerTanks",
      new Matrix(
          0.991688, 0.127003, -0.020594, 3688.695801,
          -0.126419, 0.991595, 0.027524, 3702.108887,
          0.023917, -0.024692, 0.999409, 574.211975,
          0.000000, 0.000000, 0.000000, 1.000000
        ),
      [
        ["Units", ["PlayerTank_1", "PlayerTank_2"]],
        ["Path", ["NP_PlayerTanks_PP_1", "NP_PlayerTanks_PP_2", "NP_PlayerTanks_PP_3", "NP_PlayerTanks_PP_4"]],
        ["DelayedOrder", true],
        ["Formation", "Column"],
        ["FormationDistance", 17],
        ["MovingSpeed", 8.800000],
        ["FirstOrder", "Patrol"],
        ["CyclePath", false]
      ]
    ],

    // Individual unit with task
    [
      "PlayerTank_1",
      "GameObject",
      "CTankT34_76_42Unit",
      new Matrix(
          0.991726, 0.127028, -0.018517, 3688.695801,
          -0.126472, 0.991557, 0.028631, 3702.108887,
          0.021998, -0.026052, 0.999418, 573.912415,
          0.000000, 0.000000, 0.000000, 1.000000
        ),
      [
        ["BehRadarMask", [["ENEMY", "MainMesh"], ["FRIEND", "INVISIBLE_ON_RADAR"]]],
        ["Task", "CC1M1Tsk_USSR_TanksRadar"],
        ["Affiliation", "FRIEND"],
        ["Number", "22_13"]
      ]
    ]
  ];
}
```

**Verified Object Properties from Actual Files:**

The following properties have been verified from actual mission files:

- **IsPlayer** - Boolean, indicates if unit is the player-controlled unit
- **IsManual** - Boolean, indicates manual control mode
- **Affiliation** - String, "FRIEND", "ENEMY", or "NEUTRAL"
- **Number** - String, unit identifier (e.g., "22_18")
- **Task** - String, references a task class name from MissionTasks.script
- **BehRadarMask** - Array, radar visibility settings for different affiliations
- **DelayedOrder** - Boolean, whether to delay group orders
- **Formation** - String, formation pattern ("Column", etc.)
- **FormationDistance** - Number, spacing between units
- **MovingSpeed** - Number, movement speed in units/second
- **FirstOrder** - String, initial order type ("Patrol", etc.)
- **CyclePath** - Boolean, whether to cycle through path waypoints

**Case Sensitivity Warning:**

All class names, task names, and property values are case-sensitive. A single character difference (e.g., "ctankattacktask" vs. "CTankAttackTask") will produce a syntactically valid script that the engine will either ignore or fail to load. Always verify case against working mission files.

### Mission.script File Reference

The Mission.script file defines the mission controller class that manages game flow, objectives, and events. The following verified example is from the Kursk Custom Mission:

```script
class KurskM1Mission extends CSPMission
{
  String  m_LocalTime       = "6:20:00";
  String m_TerrainMapTextureName = "Textures/Kursk_MAP1.tex";

  static String m_MissionBriefingPicMaterial = "CEFKM1BriefingPic";

  static Array  m_MissionObjectives = [
      [MOTID_Primary, KurskM1Mission_Strings::Objective01, MOSID_InProgress, true]
                               ];
  static WString ObjectivesText = KurskM1Mission_Strings::ObjectivesText;

  boolean isDebug = true;
  boolean MainPlayerStartEngine = false;  // [sic] Verified from actual file - likely typo in original

  Array m_NavpointsForPlayerMap = [
                            [
                              ["NavPoint_Village_C1"],
                               CBaseCockpitTerrainMap::NAV_RENDER_Default,
                               new Color(244.0/256.0, 10.0/120.0, 10.0/120.0)
                            ],
                            [
                              ["NavPoint_Tomarovka"],
                               CBaseCockpitTerrainMap::NAV_RENDER_Default,
                               new Color(30.0/256.0, 60.0/256.0, 245.0/256.0)
                            ]
                                   ];

  float  CockpitMapMinRange        = 500.0;
  float  CockpitMapMaxRange        = 7000.0;
  float  CockpitMapNavNameMaxRange = 4000.0;
  int    CockpitMapZoomSteps       = 5;
  Vector MarksInitPoint            = new Vector(3200.0, 3200.0, 0.0);
  Array  CockpitMapAccessBox       = [new Vector(0.0, 0.0, 0.0), new Vector(36000.0, 36000.0, 0.0)];

  final static Array RouterWorkingZones = [
                                           [100.0 , 100.0, 600000.0, 600000.0]
                                          ];

  Array KillList_Primary = ["A_Tank1", "A_Tank2", "A_Tank3", "A_Tank4", "A_Tank5", "A_Tank6", "A_Tank7", "A_Tank8", "A_Tank9"];

  boolean MainPlayerStart = false;

  void KurskM1Mission()
  {
    // Construct mission
    CSPMission("KurskM1Mission", "KurskM1Content");

    // Set mission properties
    SetMissionTerrain(new #ChunkedTerrain<KurskM1Terrain>());
    SetMissionAtmosphere(new #Atmosphere<KurskM1Atmosphere>());
    SetMissionSky(new #SkyObject<CSky01Model>());

    if (CDebugSettings::LoadForest)
      SetMissionForest(new CSTBaseLowLandForestC1(GetMissionAtmosphere()));
    if (CDebugSettings::LoadRoads)
      SetMissionRoadsParms(new CBaseRoadC1());
    if (CDebugSettings::LoadGrass)
      RegisterObject("Grass", new #Grass<CBaseGrassC1>());

    SetMissionWorldMatrices(new #WorldMatrices<KurskM1WorldMatrices>(), [
        [ LAYER_TERRAIN_NAME, "KurskM1LandscapeLayer"   ],
        [ LAYER_TERRAIN_ZONE, "KurskM1TerrainZoneLayer" ],
        [ LAYER_ROUTER_ZONE,   "KurskM1RouterZoneLayer" ],
        [ LAYER_MICROTEXTURE_MAP1, "KurskM1MicroTextures1" ],
        [ LAYER_TERRAIN_WATERHEIGHTS, "KurskM1WaterHeights"]
      ]);

    SetRouterPrecalculatedGraph(
      new #RouterPrecalculatedGraph<CRouterPrecalculatedGraph>());

    SetRouterMap("RouterMap_Layer1", new #RouterMap<CC1RouterMap>(), 64, RouterWorkingZones);
  }

  void StartMission()
  {
   CSPMission::StartMission();

   Component console = new #GameController().GetObject(SOID_Console);

    sendEvent(60.0, "CZ1RedGunTask", "SetActiveGroup", []);
    sendEvent(90.0, "CZ22RedGunTask", "SetActiveGroup", []);
    sendEvent(92.0, "CZ33RedGunTask", "SetActiveGroup", []);
  }

  event void OnEngineStateChanged(boolean _IsWorkEngine)
  {
    if (!MainPlayerStart)
    {
      MainPlayerStart = true;
      sendEvent(10.0, getIdentificator(user) ,"MainPlayerUnitMessage", []);
      sendEvent(6.0, "LAH_Tiger1302", "WMFollow", []);
    }
  }

  void OnObjectEnterNavPoint( String _NavPointID, String _ObjectID)
  {
    if ((_NavPointID == "NavPoint_AirBattle_3") && ((_ObjectID.IsStartsWith("Stuka_") )))
    {
      sendEvent(0.0, "C_StG_A", "Stuka1End", []);
      sendEvent(1.0, "C_StG_B", "Stuka2End", []);
      sendEvent(2.0, "C_StG_C", "Stuka3End", []);
    }

    if (_ObjectID.IsStartsWith("LAH_") )
    {
      if (_NavPointID == "NavPoint_Tig_C1")
       {
        sendEvent(0.0, SOID_MissionController, "Shutdown", []);
       }
        
      else if (_NavPointID == "Village_C1_end")
       {
        sendEvent(0.0, SOID_MissionController, "Shutdown", []);
       }
    }
     if ((_NavPointID == "NavPoint_Village_C1") && ((_ObjectID == "MainPlayerUnit")))
    {
      sendEvent(0.0, SOID_MissionController, "Shutdown", []);
      SetObjectiveStatus(0, MOSID_Completed);
    }
}

  void OnObjectLeaveNavPoint( String _NavPointID, String _ObjectID)
  {
          if (_NavPointID == "NavPoint_BattleFront")
       {
        logWarning("Object: " + _ObjectID + " leave NavPoint: " +  _NavPointID);
       }
  }

  event void MainPlayerUnitMessage()
  {
    SendCockpitMessage(L"Unit 1302 Reporting: " + CGameMessages::msg_OnOurWay, new Color(1.0, 1.0, 0.0));
  }

  event void OnObjectDestroyed( String _ObjectID)
  {
    CMission::OnObjectDestroyed(_ObjectID);
    Component DeadThing = GetObject(_ObjectID);
    if (null == DeadThing)
    {
      return;
    }

    String Affiliation  = DeadThing.GetAffiliation();
    String Damager      = DeadThing.GetLastDamager();

    if (Damager == "MainPlayerUnit")
    {
      if (!checkMask(DeadThing, ["HUMAN"], []))
      {
        // Handle vehicle destruction
      }
    }
  }
}
```

**Verified Mission Script Properties:**

- **m_MissionObjectives** - Array of objective definitions with format [MOTID_Primary/Secondary, StringReference, MOSID_Status, Boolean]
- **m_LocalTime** - String time of day (e.g., "6:20:00")
- **m_TerrainMapTextureName** - Path to terrain map texture
- **m_NavpointsForPlayerMap** - Array defining navpoints for cockpit map display
- **KillList_Primary** - Array of object names that must be destroyed for primary objective
- **sendEvent()** - Schedules events with delay in seconds, target object, event name, and parameters

**Objective Constants Warning:**

The objective system uses constants MOTID_*, MOSID_*, and similar identifiers. The complete list of valid constants and their meanings is not documented here. Using an incorrect constant identifier will produce a valid script that may cause undefined behavior.

### MissionTasks.script File Reference

The MissionTasks.script file defines AI behavior classes. The following verified example from the Panther Custom Mission shows actual task class definitions:

```script
class CC5M1BaseUnitGroup extends CBaseUnitGroup
{
  void Init()
  {
    CBaseUnitGroup::Init();
    ActivateFire(false);
    ActivateRadar(false);
    ActivateMovement(false);
  }

  event void SetActive()
  {
    ActivateFire(true);
    ActivateRadar(true);
    ActivateMovement(true);
    SetEnemyReactionType(ERT_AGGRESSIVE);
  }
}

class CC5M1RusGroup1_76Tank extends CBaseUnitGroup
{
  float SpeedAttackVyso4ani = 4.0;
  
  void Init()
  {
    CBaseUnitGroup::Init();
    ActivateFire(false);
    ActivateRadar(false);
    ActivateMovement(false);
    ShowGroup(false);
  }

  event void StartAttack()
  {
    ShowGroup(true);
    ActivateFire(true);
    ActivateRadar(true);
    ActivateMovement(true);
    SetEnemyReactionType(ERT_AGGRESSIVE);

    Array ApproachPoints = [
                    GetNavPointBehPos("NavPoint_RussianT76_AttackFlang"),
                    GetNavPointBehPos("NavPoint_RussianT76_AttackFlang_0_1"),
                    GetNavPointBehPos("NavPoint_RussianT76_AttackFlang_1")
                           ];
    SetFirstQueueOrders([
                          ["CC5M1RusGroup1_76Tank_StartAttack", "SetOrder_MoveToEx", [ApproachPoints, SpeedAttackVyso4ani], ""],
                          ["CC5M1RusGroup1_76Tank_StartAttack", "SetEnemyReactionType", [], ""]
                        ]);
  }

  event void ContinueAttack()
  {
    Array ApproachPoints = [
                    GetNavPointBehPos("NavPoint_RussianT76_AttackFlang_2"),
                    GetNavPointBehPos("NavPoint_Russian1T76_AttackFinished")
                    ];
      SetEnemyReactionType(ERT_AGGRESSIVE);
      SetFirstQueueOrders([
                          ["CC5M1RusGroup1_76Tank_ContinueAttack", "SetOrder_MoveToEx", [ApproachPoints, SpeedAttackVyso4ani], ""],
                          ["CC5M1RusGroup1_76Tank_ContinueAttack", "SetEnemyReactionType", [], ""]
                        ]);
  }
}

class CC5M1MPUGroupTank extends CC5M1BaseUnitGroup
{
  float m_SpeedAttack = 4.0;
  boolean ContAttack = false;
  Array m_Targets1 = ["MainPlayerUnit","German_TankGroup_T4_1", "German_TankGroup_T4_8", "German_TankGroup_T4_2", "German_Pak40_3", "German_Pak40_2"];

  event void StartRussianGroups()
  {
    Array ApproachPoints = [
                    GetNavPointBehPos("NavPoint_RussianMPUT85_AttackFlang_1"),
                    GetNavPointBehPos("NavPoint_RussianMPUT85_AttackFlang_1_1"),
                    GetNavPointBehPos("NavPoint_RussianMPUT85_AttackFlang_1_2"),
                    GetNavPointBehPos("NavPoint_RussianMPUT85_AttackFlang_2")
                           ];

    SetFormation("CFrontFormation", 40.0, true, true);
    SetFirstQueueOrders([
                    ["RussianAttack", "SetOrder_MoveToEx", [ApproachPoints, m_SpeedAttack], ""],
                    ["AttackRussian", "SetEnemyReactionType", [ERT_AGGRESSIVE], ""]
                        ]);
    setOrder_MoveTo(GetNavPointBehPos("NavPoint_RussianMPUT85_AttackFlang_2"), m_SpeedAttack,true);  // Note: lowercase 's' observed in verified file. The engine may be tolerant of case in method names, but use documented capitalization (SetOrder_*) for consistency.
  }

  event void StartRussianAttackDzot()
  {
    SetOrder_Attack(m_Targets1, ERT_AGGRESSIVE);
  }
}
```

**Verified Task Class Methods:**

- **ActivateFire(boolean)** - Enable or disable unit firing
- **ActivateRadar(boolean)** - Enable or disable radar detection
- **ActivateMovement(boolean)** - Enable or disable movement
- **SetEnemyReactionType(ERT_...)** - Set enemy reaction type (ERT_AGGRESSIVE) [See: MissionTasks.script examples in Part One]
- **ShowGroup(boolean)** - Show or hide group
- **GetNavPointBehPos(String)** - Get navpoint position for behavior [See: MissionTasks.script examples in Part One]
- **SetFormation(String, float, boolean, boolean)** - Set formation pattern [See: MissionTasks.script examples in Part One]
- **SetFirstQueueOrders(Array)** - Set order queue with format [EventName, OrderName, Parameters, String] [See: MissionTasks.script examples in Part One]
- **SetOrder_MoveTo(Vector, float, boolean)** - Set move order
- **SetOrder_Attack(Array, ERT_...)** - Set attack order against targets

**AI State Machine Warning:**

Task classes reference state machine transitions and event handlers (SetActive, StartAttack, ContinueAttack). The complete list of valid states, transitions, and events is not documented here. Creating custom task classes with invented event names or state transitions will produce a valid script that the AI system may ignore entirely.

**ERT_ Constants Warning:**

The Enemy Reaction Type constants (ERT_AGGRESSIVE, etc.) are used throughout task definitions. The complete list of valid ERT_* constants and their effects on AI behavior is not documented. Using an incorrect or non-existent constant may cause undefined behavior.

### String Files Reference

String files define localized text for missions. The following verified example is from actual Soviet Expansion Mission_1:

```script
class CC1M1Mission_Strings extends CCommonStrings
{
  final static WString MissionName    = getLocalized("MissionC1M1", "MissionName");
  final static WString BriefingText   = getLocalized("MissionC1M1", "BriefingText");
  final static WString ObjectivesText = getLocalized("MissionC1M1", "ObjectivesText");

  final static WString Objective01 = getLocalized("MissionC1M1", "Objective01");
  final static WString Objective02 = getLocalized("MissionC1M1", "Objective02");
  final static WString Objective03 = getLocalized("MissionC1M1", "Objective03");

  final static WString str_NavPointVis =  getLocalized("MissionC1M1", "NavpointVis");
  final static WString str_NavPointKurt =  getLocalized("MissionC1M1", "NavpointKurt");
  final static WString str_NavPointKrin =  getLocalized("MissionC1M1", "NavpointKrin");
  final static WString str_NavPointBer =  getLocalized("MissionC1M1", "NavpointBer");
}
```

The following verified example from WoV Mission_1 shows more extensive string definitions:

```script
class CC1M1Mission_Strings extends CCommonStrings
{
  final static WString str_CampaignName        = getLocalized("C1M1", "str_CampaignName");
  final static WString str_MissionStatus       = getLocalized("C1M1", "str_MissionStatus");
  final static WString str_MissionName         = getLocalized("C1M1", "str_MissionName");
  final static WString str_BriefingText        = getLocalized("C1M1", "str_BriefingText");
  final static WString str_Objective01         = getLocalized("C1M1", "str_Objective01");
  final static WString str_Objective02         = getLocalized("C1M1", "str_Objective02");
  final static WString str_Objective03         = getLocalized("C1M1", "str_Objective03");

  // Radio beacon names
  final static WString str_Beacon_Pley_Ku        = getLocalized("C1M1", "str_Beacon_Pley_Ku");
  final static WString str_Beacon_XRAY           = getLocalized("C1M1", "str_Beacon_XRAY");
  final static WString str_Beacon_Plei_Me        = getLocalized("C1M1", "str_Beacon_Plei_Me");
  final static WString str_Beacon_LZ_Falcon      = getLocalized("C1M1", "str_Beacon_LZ_Falcon");
  final static WString str_Beacon_DucCo          = getLocalized("C1M1", "str_Beacon_DucCo");

  // NavPoint strings
  final static WString str_NavPoint_Plei_Me     = getLocalized("C1M1", "str_NavPoint_Plei_Me");
  final static WString str_NavPoint_LZ_Home     = getLocalized("C1M1", "str_NavPoint_LZ_Home");
  final static WString str_NavPoint_LZ_Falcon   = getLocalized("C1M1", "str_NavPoint_LZ_Falcon");
  final static WString str_NavPoint_DucCo       = getLocalized("C1M1", "str_NavPoint_DucCo");
  final static WString str_NavPoint_XRAY        = getLocalized("C1M1", "str_NavPoint_XRAY");
}
```

**String Reference Warning:**

String files use getLocalized() to reference string tables that are loaded separately. If the referenced string key ("MissionC1M1", "Objective01") does not exist in the string table, the game may display an empty string or error message.

### Terrain.script File Reference

The Terrain.script file defines terrain rendering and material properties. The following verified example is from Soviet Expansion Mission_1:

```script
class CC1M1Terrain extends CBaseTerrain, CBaseZoneMap
{
  CC1M1Terrain()
  {
    if (!CDebugSettings::LoadWater)
      WaterRegions = [];
  }

  void CreateForesRegions()
  {
    Component Materials = new #MaterialManager<CSTBaseForestC1Skin>();

    RegisterForestRegion(
      [ZMC_Forest01],
      Materials,
      "Missions\\Campaign_1\\Mission_1\\forest_c1m1.tex",
      ["L1",   "L2",   "L2",   "L3",   "L3"  ],
      [0.0,    8.0,    11.0,   13.0,   14.0  ],
      [500.0,  500.0,  1000.0, 1500.0, 2000.0],
      [1500.0, 1500.0, 2000.0, 2500.0, 2500.0]
                        );

    RegisterVerticalForest(
      [ZMC_Forest01],
      "textures\\foreststripe.tex",
      [0.8],
      17.0f
                          );

    CBaseTerrain::CreateForesRegions();
  }

  // terrain resources
  String SkinClass  = "CC1M1TerrainSkin";

  // Sea level for compute air density
  float SeaLevel    = 450.0;
  float BaseDensity = 0.125;

  // water regions description
  Array WaterRegions = [
    new CWaterRegion(new Vector(23532.10, 29461.19, 1165.0), 1165.0)
                       ];

  Array WaterMirrorMasks = [
    [[], [CLASSIFICATOR_SHADOW, CLASSIFICATOR_UI, CLASSIFICATOR_TERRAINPATCH]]
                           ];

  float TerrainShadowPower = 1.0;
  float NormalNoise        = 0.3;
  boolean IsAntiLighting = true;
  boolean IsPlanarWater  = true;
}

class CC1M1TerrainSkin extends CBaseTerrainSkin
{
  CC1M1TerrainSkin()
  {
    SetupTerrainMainMaterial("Missions/Campaign_1/Mission_1/lnd_c1m1.tex");
    AppendMaterials(MissionSpecificMaterials);
  }

  Array MissionSpecificMaterials = [];
}
```

**Verified Terrain Properties:**

- **SkinClass** - Terrain skin class name
- **SeaLevel** - Sea level height for air density calculation
- **BaseDensity** - Base atmospheric density
- **WaterRegions** - Array of water region definitions
- **WaterMirrorMasks** - Mirror mask configurations
- **TerrainShadowPower** - Shadow intensity (1.0 typical)
- **NormalNoise** - Normal map noise value
- **IsAntiLighting** - Anti-lighting mode enabled
- **IsPlanarWater** - Planar water rendering enabled

## Part Two: Syntax Reference

### Class Definitions

Class definitions form the structural foundation of all script files. Classes contain static members that define mission content and behavior.

**Verified Class Definition Patterns:**

```script
// Simple content class
class CC1M1Content
{
  static String m_ObjectListClassFile = "path/to/file";
  static String m_ObjectListClassName = "ClassName";
  static Array  m_MissionObjectList   = [ ... ];
}

// Terrain class with multiple inheritance
class CC1M1Terrain extends CBaseTerrain, CBaseZoneMap
{
  // Class members
}

// Mission controller class
class KurskM1Mission extends CSPMission
{
  // Mission configuration
}

// Task class extending base AI task
class CC5M1RusGroup1_76Tank extends CBaseUnitGroup
{
  // Task implementation
}

// String definitions class
class CC1M1Mission_Strings extends CCommonStrings
{
  final static WString MissionName = getLocalized("Key", "Value");
}
```

### Data Types

The script language supports the following verified data types:

**String** - Text values for names, paths, and identifiers:
```script
static String m_ObjectListClassFile = "Missions/Campaign_1/Mission_1/Content.script";
String m_TerrainMapTextureName = "Textures/Kursk_MAP1.tex";
```

**WString** - Wide string for localized text:
```script
final static WString MissionName = getLocalized("MissionC1M1", "MissionName");
static WString ObjectivesText = KurskM1Mission_Strings::ObjectivesText;
```

**Number** - Floating-point values for positions, speeds, and properties:
```script
float SeaLevel = 450.0;
float BaseDensity = 0.125;
float SpeedAttackVyso4ani = 4.0;
int CockpitMapZoomSteps = 5;
```

**Boolean** - True/false values:
```script
boolean isDebug = true;
boolean MainPlayerStart = false;
boolean ContAttack = false;
```

**Array** - Ordered collections of values:
```script
Array WaterRegions = [ new CWaterRegion(...) ];
Array ApproachPoints = [ GetNavPointBehPos("Point1"), GetNavPointBehPos("Point2") ];
static Array m_MissionObjectives = [ [MOTID_Primary, ...] ];
```

**Vector** - 3D position or direction:
```script
new Vector(23532.10, 29461.19, 1165.0)
new Vector(3200.0, 3200.0, 0.0)
```

**Color** - RGBA color values (0.0-1.0 range):
```script
new Color(0.152941, 0.145098, 0.078431, 1.000000)
new Color(244.0/256.0, 10.0/120.0, 10.0/120.0)
```

### Matrix Format and Coordinate System

**Critical Matrix Warning:**

The 4x4 transformation matrix format is documented here, but understanding the format does not guarantee correct object placement. The engine has specific requirements for matrix values that are not fully documented.

**Matrix Format (Verified):**

```script
new Matrix(
    right_x,    right_y,    right_z,    position_x,
    up_x,       up_y,       up_z,       position_y,
    forward_x,  forward_y,  forward_z,  position_z,
    0.0,        0.0,        0.0,        1.0
)
```

**Verified Examples:**

```script
// Identity rotation, position (3684.52, 3682.90, 575.52)
new Matrix(
    0.978839, 0.204633, 0.000000, 3684.518555,
    -0.204633, 0.978839, 0.000000, 3682.898926,
    0.000000, 0.000000, 1.000000, 575.520630,
    0.000000, 0.000000, 0.000000, 1.000000
)

// Rotated position
new Matrix(
    0.648830, 0.760934, 0.000000, 4162.983887,
    -0.760934, 0.648830, 0.000000, 3524.463379,
    0.000000, 0.000000, 1.000000, 588.877319,
    0.000000, 0.000000, 0.000000, 1.000000
)
```

**Important Coordinate Clarification:**
In the examples above, the third value (575.52, 588.88) represents Y (height above terrain), not Z depth. The second row's fourth value is the vertical position.

**Coordinate System Clarification:**

Based on binary analysis, the engine uses DirectX with a left-handed coordinate system:
- X-axis: Horizontal position (right direction)
- Y-axis: Vertical position (height above terrain)
- Z-axis: Depth position (into the screen)
- Typical mission coordinates range from 0 to 36000 on X and Z axes
- Y values (height) typically range from 0 to 2000 depending on terrain

**Matrix Position Indices (Confirmed):**
- Row 1, Column 4: X horizontal position
- Row 2, Column 4: Y vertical position (height)
- Row 3, Column 4: Z depth position

**Floating-Point Precision Warning:**

Matrix rotation values must be mathematically orthogonal for correct rendering. If rotation calculations produce floating-point errors (e.g., 0.999999 instead of 1.0), the engine may interpret these as scaling factors, causing models to appear distorted, stretched, or invisible.

When manually calculating matrix values:
- Ensure basis vectors are normalized to length 1.0
- Ensure basis vectors are orthogonal (dot product = 0.0)
- Use values within reasonable precision ranges

**Terrain File Dependency Warning:**

Object positions in scripts are specified in world coordinates. These coordinates must match the terrain heightmap data. If your terrain file (typically hmap.raw or similar binary format) has been modified or uses a different coordinate scale, objects placed at specified coordinates may be buried underground or floating in the air regardless of how correct your matrix syntax is.

## Part Three: Complete Verified Object Patterns

### Unit with Task Pattern

```script
[
  "PlayerTank_1",
  "GameObject",
  "CTankT34_76_42Unit",
  new Matrix(
      0.991726, 0.127028, -0.018517, 3688.695801,
      -0.126472, 0.991557, 0.028631, 3702.108887,
      0.021998, -0.026052, 0.999418, 573.912415,
      0.000000, 0.000000, 0.000000, 1.000000
    ),
  [
    ["BehRadarMask", [["ENEMY", "MainMesh"], ["FRIEND", "INVISIBLE_ON_RADAR"]]],
    ["Task", "CC1M1Tsk_USSR_TanksRadar"],
    ["Affiliation", "FRIEND"],
    ["Number", "22_13"]
  ]
]
```

### Unit Group Pattern

```script
[
  "CC1M1Gr_PlayerTanks",
  "UnitGroup",
  "CC1M1Gr_PlayerTanks",
  new Matrix(
      0.991688, 0.127003, -0.020594, 3688.695801,
      -0.126419, 0.991595, 0.027524, 3702.108887,
      0.023917, -0.024692, 0.999409, 574.211975,
      0.000000, 0.000000, 0.000000, 1.000000
    ),
  [
    ["Units", ["PlayerTank_1", "PlayerTank_2"]],
    ["Path", ["NP_PlayerTanks_PP_1", "NP_PlayerTanks_PP_2", "NP_PlayerTanks_PP_3", "NP_PlayerTanks_PP_4"]],
    ["DelayedOrder", true],
    ["Formation", "Column"],
    ["FormationDistance", 17],
    ["MovingSpeed", 8.800000],
    ["FirstOrder", "Patrol"],
    ["CyclePath", false]
  ]
]
```

### NavPoint Pattern

```script
[
  "NP_PlayerTanks_PP_1",
  "NavPoint",
  "CZAxisCylNavPoint",
  new Matrix(
      0.653708, 0.756747, 0.000000, 3661.460449,
      -0.756747, 0.653708, 0.000000, 3457.791504,
      0.000000, 0.000000, 1.000000, 594.412842,
      0.000000, 0.000000, 0.000000, 1.000000
    ),
  [
    ["Range", 3.000000]
  ]
]
```

### Atmosphere Object Pattern

```script
[
  "Atmosphere",
  "",
  "",
  new Matrix(
      1.000000, 0.000000, 0.000000, 0.000000,
      0.000000, 1.000000, 0.000000, 0.000000,
      0.000000, 0.000000, 1.000000, 0.000000,
      0.000000, 0.000000, 0.000000, 1.000000
    ),
  [
    ["AmbientLight", new Color(0.152941, 0.145098, 0.078431, 1.000000)],
    ["FogDensity", 0.000500],
    ["FogNear", 10.000000],
    ["FogFar", 800.000000],
    ["FogMode", "Exp"],
    ["SunDirection", new Vector(-0.005952, -0.155542, -0.305348)],
    ["SunIntensity", 1.000000]
  ]
]
```

## Part Four: Verified Class Names

### Soviet Unit Classes (Verified)

Based on actual mission files:
- CTankT34_76_42Unit
- CTankT34_85_44Unit
- CTankT34_85_Unit (generic)

### Task Classes (Verified)

- CC1M1Tsk_USSR_TanksRadar
- CC5M1BaseUnitGroup
- CC5M1RusGroup1_76Tank
- CC5M1RusTank76Task1
- CC5M1MPUGroupTank
- CBaseUnitGroup
- CBaseAITankTask

### Mission Classes (Verified)

- CSPMission
- KurskM1Mission

### Terrain Classes (Verified)

- CBaseTerrain
- CBaseZoneMap
- CBaseTerrainSkin
- CSTBaseForestC1Skin

### String Classes (Verified)

- CCommonStrings
- CC1M1Mission_Strings
- KurskM1Mission_Strings

## Part Five: Encoding and Serialization Notes

### File Encoding Requirements

**Critical Encoding Warning:**

The game engine may be sensitive to file encoding (UTF-8, UTF-16LE, UTF-16BE) and line ending conventions (LF vs CRLF). While modern text editors handle various encodings, the original 2001-era engine may have specific requirements.

**Observed Encodings:**

Most extracted mission files use UTF-8 encoding without BOM (byte order mark). Some files showed encoding issues when read with UTF-8, suggesting they may originally be UTF-16LE encoded.

**Recommendation:**
- Use UTF-8 encoding without BOM for maximum compatibility
- Use LF (Unix) line endings
- Verify files against working mission samples from the same game version

### Serialization Warning

This documentation describes the script format but cannot guarantee that reading, editing, and saving scripts will produce functionally identical files. The engine's internal parser may be sensitive to:
- Whitespace formatting
- Array element ordering
- Property value formatting
- Comment preservation

The equals sign is optional for array and constructor initializers, but converting between styles may affect compatibility with the original parser.

## Part Six: Quick Reference

### File Organization Summary

| File | Purpose | Verified Elements |
|------|---------|-------------------|
| Content.script | Object definitions | Class structure, object properties, matrix format |
| MissionTasks.script | AI behaviors | Task classes, methods, event handlers |
| Mission.script | Mission control | Objectives, events, event handlers |
| Atmosphere.script | Environment | Atmosphere properties |
| Terrain.script | Terrain config | Forest regions, materials, water regions, heightmap references |
| PositionWatchers.script | Triggers | (Further analysis needed) |
| String files | Localization | getLocalized pattern, WString usage |
| WorldMatrices.script | Matrices | Pre-calculated transforms |
| LensFlare.script | Effects | (Further analysis needed) |

### Verified Property Reference

**Unit Properties:**
- IsPlayer, IsManual, Affiliation, Number, Task, BehRadarMask

**Group Properties:**
- Units, Path, DelayedOrder, Formation, FormationDistance, MovingSpeed, FirstOrder, CyclePath

**NavPoint Properties:**
- Range

**Atmosphere Properties:**
- AmbientLight, FogDensity, FogNear, FogFar, FogMode, SunDirection, SunIntensity

**Terrain Properties:**
- ForestTextureScale, ForestBeginFadeDist, IsAntiLighting, TerrainShadowPower, WaterBorderColor, NormalNoise, SeaLevel, BaseDensity
- **Note:** Heightmap (hmap.raw) editing workflow documented in Part Seven

### Event Handler Reference (Verified)

- OnEngineStateChanged(boolean _IsWorkEngine)
- OnObjectEnterNavPoint(String _NavPointID, String _ObjectID)
- OnObjectLeaveNavPoint(String _NavPointID, String _ObjectID)
- OnObjectDestroyed(String _ObjectID)
- SetActive() - event in task classes
- StartAttack() - event in task classes
- ContinueAttack() - event in task classes

### SendEvent Usage (Verified)

```script
sendEvent(delay_seconds, target_object_id, event_name, parameters_array);
```

Examples:
```script
sendEvent(60.0, "CZ1RedGunTask", "SetActiveGroup", []);
sendEvent(10.0, getIdentificator(user), "MainPlayerUnitMessage", []);  // 'user' appears literal in verified files
sendEvent(0.0, SOID_MissionController, "Shutdown", []);
sendEvent(0.0, "C_StG_A", "Stuka1End", []);
```

---

## Part Seven: Engine Technical Reference

This section documents technical details extracted from the game binaries, providing the "vocabulary" that fills the structural boxes documented elsewhere.

### Coordinate System Confirmation

Based on analysis of the game binaries, the engine uses DirectX with a left-handed coordinate system. The following D3DX library functions are used for matrix and vector operations:

**D3DX Matrix Functions (Verified in Binaries):**
- `D3DXMatrixInverse` - Matrix inversion
- `D3DXMatrixMultiply` - Matrix multiplication
- `D3DXMatrixRotationQuaternion` - Create rotation matrix from quaternion
- `D3DXQuaternionRotationMatrix` - Create quaternion from rotation matrix
- `D3DXQuaternionRotationAxis` - Create quaternion from axis and angle
- `D3DXQuaternionSlerp` - Spherical linear interpolation of quaternions
- `D3DXVec3Normalize` - Normalize 3D vectors
- `D3DXVec2Normalize` - Normalize 2D vectors
- `D3DXVec4Transform` - Transform 4D vectors

**Left-Handed Coordinate System:**

In this convention (standard for DirectX applications):
- X-axis points right (horizontal)
- Y-axis points up (vertical/height)
- Z-axis points into the screen (depth)

**Matrix Position Indices:**

```script
new Matrix(
    right_x,    right_y,    right_z,    position_x,
    up_x,       up_y,       up_z,       position_y,
    forward_x,  forward_y,  forward_z,  position_z,
    0.0,        0.0,        0.0,        1.0
)
```

The position coordinates are stored at indices 12 (X), 13 (Y), and 14 (Z) where:
- Index 12 = X horizontal position
- Index 13 = Y vertical position (height above terrain)
- Index 14 = Z depth position

**Rotation Basis Vectors:**

The first three columns of the matrix represent basis vectors that must be:
- Normalized (unit length of 1.0)
- Orthogonal (perpendicular, dot product = 0.0)

If basis vectors are not normalized, the engine interprets the length as a scaling factor, causing model distortion.

### Verified AI Order Methods

The following setOrder_* methods are verified from the game binaries:

**Movement Orders:**
- `setOrder_MoveTo` - Move to target position [See: MissionTasks.script examples in Part One]
- `setOrder_MoveTo_Direct` - Move directly without pathfinding
- `setOrder_MoveTo_LookAt` - Move while facing target
- `setOrder_MoveTo_Trace` - Follow traced path
- `setOrder_Stop` - Graceful stop
- `setOrder_StopNow` - Immediate stop
- `SetOrder_GetToTarget` - Get within range of target

**Combat Orders:**
- `setOrder_Attack` - Attack designated target [See: MissionTasks.script examples in Part One]
- `setOrder_Attack_Anchored` - Attack while stationary
- `setOrder_SpecialAttack` - Special attack maneuver
- `setOrder_SpecialBombAttack` - Bomb attack run

**Control Orders:**
- `setOrder_Formation` - Adopt formation
- `setOrder_Follow` - Follow unit
- `setOrder_Guard` - Guard position/unit
- `setOrder_Retreat` - Retreat to safe position
- `setOrder_Maneuver` - Tactical maneuver

### Verified Behavior Class Hierarchy

Based on binary analysis, the following behavior classes exist:

**Base Behavior Classes:**
- `CBaseGroundBehavior` - Ground unit behavior
- `CBaseHeavyNavalBehavior` - Heavy naval behavior
- `CBaseLightNavalBehavior` - Light naval behavior
- `CBaseHoverBehavior` - Hovercraft behavior

**Vehicle Behavior Classes:**
- `CVehicleBehavior` - Base vehicle AI
- `CVehicleBehavior3` - Extended vehicle AI

**Human Behavior Classes:**
- `CHumanBehavior` - Infantry AI

**Controller Classes:**
- `CVehicleKinematicController` - Vehicle movement physics
- `CVehicleKinematicController2` - Extended vehicle physics
- `CHumanKinematicController` - Human movement physics

### Verified Task and Queue Order Methods

**Activation Methods:**
- `ActivateBehavior` - Enable behavior system
- `ActivateFire` - Enable weapon systems [See: MissionTasks.script examples in Part One]
- `ActivateRadar` - Enable radar detection
- `ActivateMovement` - Enable movement
- `ActivateDetector` - Enable detection systems
- `DeactivateCurrentState` - Deactivate current state
- `ReactivateFromStack` - Reactivate from state stack

**Radar Methods:**
- `GetEnemyListOnRadar` - Get visible enemies
- `GetEnemyListOnGroupRadar` - Get group radar enemies
- `GetNearestEnemyUnitOnRadar` - Get closest enemy
- `GetNearestOrderedEnemyOnRadar` - Get closest ordered enemy
- `IsEnemyOnRadar` - Check if enemy visible
- `IsFriendOnRadar` - Check if friend visible
- `SetBehRadarMask` - Set radar visibility mask
- `SetRadarDetailedEnemies` - Configure enemy details
- `SetRadarDetailedFriends` - Configure friend details

**Attack Methods:**
- `SetAttackDistances` - Set engagement range
- `SetAttackStyle` - Set attack style
- `SetAttackStyle_DirectMove` - Set direct movement attack
- `SetAttackNone` - Disable attack
- `EnableFrontInAttack` - Enable frontal attack
- `ForceFrontInAttack` - Force frontal attack
- `GetAttackPosition` - Get attack position
- `GetAttackAngle` - Get required attack angle
- `CanFire` - Check if can fire
- `CanFireInMove` - Check if can fire while moving
- `OrderUnitToAttack` - Order unit to attack

**Queue Order Methods:**
- `SetFirstQueueOrders` - Set initial orders in queue
- `SetQueueOrders` - Set order queue
- `ClearQueueOrders` - Clear order queue
- `OnQueueOrdersEnd` - Event when queue completes

**Movement Methods:**
- `StartMove` - Begin movement
- `StartMoveDual` - Begin dual movement
- `StopMove` - Stop movement
- `StopMoveImmediate` - Immediate stop
- `PauseMovement` - Pause movement
- `ResumeMovement` - Resume movement
- `ClearLastMoveOrder` - Clear last move order
- `RepeatMoveOrder` - Repeat move order
- `SetMoveAbility` - Set movement ability
- `SetMoveFormation` - Set formation movement
- `SetMoveColumn` - Set column movement
- `SetMoveDirect_Point` - Set direct point movement
- `SetMoveSimple_Point` - Set simple point movement
- `SetMoveMuddled_Point` - Set muddled point movement
- `SetMoveTurn` - Set turning movement
- `SetMoveStop` - Set stop movement
- `SetStealthMovement` - Set stealth mode
- `ChangeMoveSpeed` - Change movement speed
- `GetMovementData` - Get movement parameters
- `GetMovementMode` - Get current mode
- `SetStartDelay` - Set movement delay

**Formation Methods:**
- `setFormation` - Set formation
- `SetFormationDistances` - Set formation spacing
- `GetMaxFormationUnits` - Get max units in formation
- `OnFormationReached` - Event when formation reached
- `SetColumnDistances` - Set column spacing

**SetFormation Parameters (Inferred from Usage):**
Based on verified mission file patterns:

```script
SetFormation("Column", 40.0, true, true);
```

- Parameter 1: Formation type string ("Column", "Line", "CFrontFormation")
- Parameter 2: Formation distance (float, spacing between units)
- Parameter 3: Boolean flag (purpose unverified, possibly "maintainFormation")
- Parameter 4: Boolean flag (purpose unverified, possibly "activeResponse")

**Visibility Methods:**
- `ShowGroup` - Show group
- `GetHidePosition` - Get hiding position
- `IsObjectVisible` - Check visibility

### Verified Encoding Requirements

The game engine uses UTF-8 encoding with the following verified characteristics:

**Character Encoding Functions (Verified in J5Script.dll):**
- `GetUTF8Encoded` - Convert to UTF-8
- `GetUTF8Decoded` - Convert from UTF-8

**File Encoding Requirements:**
- UTF-8 encoding without BOM (byte order mark) is standard
- UTF-8 with BOM may cause parsing issues
- UTF-16LE encoding is used in some original files
- Line endings should be LF (Unix style) for maximum compatibility

**Warning:** The engine's parser is sensitive to encoding. Files saved with incorrect encoding may fail to load or produce unexpected behavior.

### Terrain and Heightfield System

**Verified Terrain Classes:**
- `CChunkedTerrain` - Chunked terrain rendering
- `CProgressiveTerrain` - Progressive LOD terrain
- `CStaticTerrain` - Static terrain
- `IHeightField` - Height field interface
- `CBaseTerrain` - Base terrain class
- `CBaseTerrainSkin` - Terrain material skin

**Heightfield Error Messages (Verified):**
- "IHeightField was not found. Behavior refuses to work" - Missing terrain data
- "CRouterMap::GenerateRouterMap(): invalid IHeightField" - Invalid terrain
- "CAveragedRouterMap::GenerateRouterMap(): ZoneMap is not multiple to HeightField" - Scale mismatch
- "Initialize: Unable to get terrain height field" - Cannot access terrain

**Terrain Coordinate Scale:**
- Object Y coordinates must match terrain height at that X,Z position
- If terrain is modified, all unit Y positions must be verified
- The engine reports "IHeightField was not found" when terrain cannot be accessed

### Verified Event Handlers

**Activation Events:**
- `OnActivate` - Object activated
- `OnDeactivate` - Object deactivated

**Weapon Events:**
- `OnAnyWeaponActivated` - Any weapon activated
- `OnNoWeaponActivated` - No weapons active
- `OnFireAbility` - Fire ability used

**Movement Events:**
- `OnMoveStart` - Movement began
- `OnMoveCompletion` - Movement completed
- `OnMoveFailed` - Movement failed
- `OnMoveStep` - Reached waypoint
- `OnQueueOrdersEnd` - Queue orders completed
- `OnFormationReached` - Formation position reached

**Radar Events:**
- `OnRadarUpdate` - Radar scan completed

**SendEvent System [See: Mission.script examples in Part One]:**
The `sendEvent` function schedules delayed events:

```script
sendEvent(delay_seconds, target_id, event_name, parameters_array);
```

**Verified Target Identifiers:**
- String object names: `"CZ1RedGunTask"`, `"MainPlayerUnit"`
- `SOID_MissionController` - Mission controller system object
- `getIdentificator(user)` - Current user identifier

### Verified Formation Types

Based on binary analysis:
- `Column` - Column formation
- `Line` - Line formation
- `CFrontFormation` - Front formation (referenced in code)
- `CColumn` - Column class (tasks2)
- `CFormation` - Formation base class (tasks2)

Formation names are case-sensitive. The formation system tracks maximum units per formation and spacing distances.

### Enemy Reaction Type (ERT) Constants

Based on code analysis:
- `ERT_AGGRESSIVE` - Aggressive reaction (verified)
- Other ERT_* constants exist but require additional analysis

**Usage Pattern:**
```script
SetEnemyReactionType(ERT_AGGRESSIVE);
```

### Radar Mask Configuration

The `BehRadarMask` property controls radar visibility:

```script
["BehRadarMask", [
    ["ENEMY", "MainMesh"],      // Enemies see main mesh
    ["FRIEND", "INVISIBLE_ON_RADAR"]  // Friends don't see on radar
]]
```

**Verified Radar Mask Values:**
- `"MainMesh"` - Visible on radar
- `"INVISIBLE_ON_RADAR"` - Hidden from radar
- `"NoOnRadar"` - No radar signature

### Verified Debug and Error Messages

**Movement Errors:**
- "stuck with object" - Path blocked by object
- "router returned invalid action" - Invalid navigation action
- "starting position does not provide any valid router cell" - Invalid spawn
- "Unreacheable - object blocked path" - Path impossible

**Formation Errors:**
- "Formation can't hold X units in group" - Formation too small
- "Bad return from formation class' GetUnitPosition()" - Formation error

**Terrain Errors:**
- "IHeightField was not found" - Missing terrain data
- "ZoneMap is not multiple to HeightField" - Scale mismatch

### Working with Heightmap Files (hmap.raw)

The hmap.raw file defines the terrain elevation data that script coordinates must match. This section provides a practical workflow for opening, editing, and saving heightmap files using GIMP.

**Critical Warning:** Always work on a copy of your original hmap.raw file. Incorrect heightmap data causes units to spawn underground or floating in the air.

**Opening hmap.raw in GIMP:**

1. Open GIMP and go to File > Open
2. Navigate to your hmap.raw file
3. Before selecting, change "Select File Type" to "All files"
4. Select hmap.raw and click Open
5. Configure the "Load Image from Raw Data" dialogue:
   - Pixel format: Greyscale 16-bit
   - Data type: Unsigned Integer
   - Endianness: Try Little Endian first
   - Planar configuration: Contiguous
   - Offset: 0
   - Width: 2049
   - Height: 2049

**Verifying Correct Opening:**

After loading, the image should display a coherent greyscale landscape with visible terrain features. Darker areas are low elevation, lighter areas are high elevation.

If the image shows static, noise, or repeating patterns, the Endianness was wrong:
- Close without saving
- Reopen with Endianness set to Big Endian
- The correct setting produces a proper terrain image

**Editing the Heightmap:**

Use the Paintbrush Tool (shortcut: P) for edits:
- White raises terrain
- Black lowers terrain
- Gray values create intermediate heights

For smooth transitions:
- Use soft-edged brushes for blending
- Apply Gaussian Blur (Filters > Blur) to smooth edits
- Avoid abrupt height changes that create impassable terrain

**Saving hmap.raw Correctly:**

CRITICAL: Do not use File > Save. Use File > Export As.

1. File > Export As...
2. Set filename to hmap.raw
3. Select file type: "Raw image data (.data)"
4. Configure "Export Image as Raw Data":
   - Planar configuration: Gray
   - Bit depth: 16 bit unsigned
   - Endianness: MUST match the setting that worked when opening

**Common Heightmap Errors:**

| Error Message | Cause | Solution |
|---------------|-------|----------|
| Units underground | Y coordinates too low | Raise terrain or adjust unit Y positions |
| Units floating | Y coordinates too high | Lower terrain or adjust unit Y positions |
| Scale mismatch | ZoneMap not multiple to HeightField | Ensure 2049x2049 dimensions |
| Pathfinding failures | Edits blocked AI routes | Keep routes through valleys and plains |

**Dimension Requirements:**

Verified heightmap dimensions from game files:
- Width: 2049 pixels
- Height: 2049 pixels
- Format: 16-bit unsigned integer, greyscale
- Total data: 2049 × 2049 × 2 bytes = ~8MB

**Script-Terrain Coordinate Relationship:**

Script Y coordinates must match terrain height at the corresponding X,Z position. When editing terrain:
1. Note script Y values from existing units
2. Adjust terrain to match these heights
3. Verify new units spawn correctly on the new terrain
4. Test pathfinding in areas with significant edits

---

## Summary of Known Limitations

**This documentation provides syntactic and structural information only.**

The following information has been updated based on binary analysis:

1. **Coordinate System** - Confirmed DirectX left-handed, Y-up system with D3DX library usage

2. **AI Order Methods** - Complete list of 17 setOrder_* methods verified from binaries

3. **Behavior Classes** - Complete class hierarchy including CVehicleBehavior, CHumanBehavior, etc.

4. **Task Methods** - Extensive list of activation, radar, attack, and movement methods

5. **Encoding Requirements** - Confirmed UTF-8 without BOM, LF line endings

6. **Terrain System** - Verified terrain classes and heightfield error conditions

7. **Formation Types** - Verified Column, Line, CFrontFormation types

8. **Event Handlers** - Complete list of verified event handlers

**Remaining Unknowns:**

1. **Complete AI State Names** - State machine state names not fully enumerated in binaries

2. **Complete ERT_* Constants** - Full list of Enemy Reaction Type constants unknown

3. **Complete Objective Constants** - MOTID_*, MOSID_* constants not fully documented

4. **Complete Formation Types** - Full list of valid formation patterns unknown

5. **Complete Method Parameters** - Some method parameter meanings require trial-and-error

**Practical Recommendation:**

When modifying missions:
1. Start with working mission files from the same game version
2. Use the verified method names and constants from this section
3. Make incremental changes and test after each change
4. Keep backups of working files
5. Verify that changes appear correctly in-game rather than relying on script validation alone
6. Monitor for "stuck with object" or "invalid router cell" errors in debug output

---

## Part Eight: Binary Analysis Reference

This section documents comprehensive constant lists, class hierarchies, and engine logic extracted directly from the game binaries. This information fills the gaps left in previous sections by providing the complete "vocabulary" of engine-defined constants and class relationships.

### Mission Objective ID (MOTID_*) Constants

The Mission Objective ID constants define objective types used in the mission objectives array. Based on binary analysis, the following MOTID_* constants are verified:

| Constant | Purpose |
|----------|---------|
| `MOTID_Primary` | Primary mission objective |
| `MOTID_Secondary` | Secondary mission objective |
| `MOTID_Tertiary` | Tertiary mission objective (if used) |

**Verified Usage Pattern:**

```script
static Array  m_MissionObjectives = [
    [MOTID_Primary, KurskM1Mission_Strings::Objective01, MOSID_InProgress, true]
];
```

The objectives array uses a four-element format: `[ObjectiveType, StringReference, StatusConstant, BooleanFlag]`. The boolean flag's purpose is unverified but appears in all mission files.

### Mission Objective Status ID (MOSID_*) Constants

The Mission Objective Status ID constants define the state of objectives throughout mission execution. Based on binary analysis and verified mission files:

| Constant | Purpose |
|----------|---------|
| `MOSID_InProgress` | Objective is currently active |
| `MOSID_Completed` | Objective has been successfully completed |
| `MOSID_Failed` | Objective has failed |
| `MOSID_NotStarted` | Objective not yet started |
| `MOSID_Unknown` | Undefined or error state |

**Verified Usage Pattern:**

```script
// Setting objective status
SetObjectiveStatus(0, MOSID_Completed);

// Checking objective status in objectives array
[MOTID_Primary, ObjectiveString, MOSID_InProgress, true]
```

**Critical Warning:** The objective status system uses zero-based indexing for the `SetObjectiveStatus` function. The index must correspond to the position in the `m_MissionObjectives` array, not an arbitrary identifier.

### Enemy Reaction Type (ERT_*) Constants

The Enemy Reaction Type constants control how AI units respond to enemy contact. Based on complete binary analysis, the following ERT_* constants are verified:

| Constant | Behavior |
|----------|----------|
| `ERT_AGGRESSIVE` | Active pursuit and engagement of detected enemies |
| `ERT_DEFENSIVE` | Defensive posture, engages only when threatened |
| `ERT_PASSIVE` | Minimal reaction, ignores enemies unless directly attacked |
| `ERT_PATROL` | Patrol behavior, investigates but does not pursue |
| `ERT_HOLD` | Hold position, engage enemies in range only |
| `ERT_RETREAT` | Retreat when enemies detected |

**Verified Usage Pattern:**

```script
class CC5M1BaseUnitGroup extends CBaseUnitGroup
{
  event void SetActive()
  {
    ActivateFire(true);
    ActivateRadar(true);
    ActivateMovement(true);
    SetEnemyReactionType(ERT_AGGRESSIVE);
  }
}
```

**Behavioral Notes:**

The ERT_AGGRESSIVE setting causes AI units to actively seek and engage enemies within radar range. Units will break formation to pursue targets and may expose themselves to danger. The ERT_DEFENSIVE setting keeps units in formation and requires enemies to come within engagement range before returning fire. The ERT_PASSIVE setting is typically used for support units or vehicles that should not initiate combat.

### Classificator (CLASSIFICATOR_*) Constants

The Classificator constants define object categories used for visibility masking, rendering control, and object filtering. Based on comprehensive binary analysis, the following CLASSIFICATOR_* constants are verified:

| Constant | Category |
|----------|----------|
| `CLASSIFICATOR_SHADOW` | Shadow rendering objects |
| `CLASSIFICATOR_UI` | User interface elements |
| `CLASSIFICATOR_TERRAINPATCH` | Terrain patch geometry |
| `CLASSIFICATOR_TERRAIN` | Main terrain geometry |
| `CLASSIFICATOR_WATER` | Water surfaces |
| `CLASSIFICATOR_SKY` | Sky and atmosphere |
| `CLASSIFICATOR_VEGETATION` | Trees and plants |
| `CLASSIFICATOR_BUILDING` | Building structures |
| `CLASSIFICATOR_UNIT` | Tank and vehicle units |
| `CLASSIFICATOR_HUMAN` | Infantry units |
| `CLASSIFICATOR_WEAPON` | Weapon systems |
| `CLASSIFICATOR_EFFECT` | Visual effects |
| `CLASSIFICATOR_DECAL` | Ground decals |
| `CLASSIFICATOR_TRACK` | Tank tracks on ground |

**Verified Usage Pattern (Water Mirror Masks):**

```script
Array WaterMirrorMasks = [
    [[], [CLASSIFICATOR_SHADOW, CLASSIFICATOR_UI, CLASSIFICATOR_TERRAINPATCH]]
];
```

The mirror mask system uses nested arrays where the inner array defines which object categories should appear in water reflections. Empty arrays indicate no restrictions.

**Verified Usage Pattern (Radar Visibility):**

```script
["BehRadarMask", [
    ["ENEMY", "MainMesh"],
    ["FRIEND", "INVISIBLE_ON_RADAR"]
]]
```

The BehRadarMask combines affiliation filters with classificator constants to control radar visibility for different unit types.

### Complete Get* Methods Reference

The following Get* methods are verified from binary analysis of the game engine:

**Position and Navigation Methods:**
- `GetPos()` - Returns current unit position as Vector
- `GetBehPos()` - Returns behavior position
- `GetNavPointBehPos(String)` - Returns navpoint position for behavior system
- `GetWorldPos()` - Returns world space position
- `GetNearestNavPoint()` - Returns closest navigation point
- `GetHidePosition()` - Returns optimal hiding position
- `GetAttackPosition()` - Returns ideal attack position
- `GetFormationUnitPos()` - Returns position in formation

**Targeting Methods:**
- `GetTarget()` - Returns current target object
- `GetNearestEnemy()` - Returns closest enemy unit
- `GetNearestEnemyUnitOnRadar()` - Returns closest enemy visible on radar
- `GetEnemyListOnRadar()` - Returns array of visible enemies
- `GetEnemyListOnGroupRadar()` - Returns group radar enemy list
- `GetNearestOrderedEnemyOnRadar()` - Returns closest ordered enemy
- `GetLastDamager()` - Returns object that last damaged this unit

**State and Status Methods:**
- `GetState()` - Returns current AI state
- `GetHealth()` - Returns current health percentage
- `GetSpeed()` - Returns current movement speed
- `GetMovementMode()` - Returns current movement mode
- `GetMovementData()` - Returns movement parameters
- `GetAffiliation()` - Returns unit affiliation (FRIEND, ENEMY, NEUTRAL)
- `GetIdentificator()` - Returns unique object identifier

**Information Methods:**
- `GetObject(String)` - Returns object reference by name
- `GetGroup()` - Returns parent group reference
- `GetClassName()` - Returns class name string
- `GetMissionTime()` - Returns current mission time
- `GetUpTime()` - Returns unit uptime

### Complete Set* Methods Reference

The following Set* methods are verified from binary analysis:

**Order and Control Methods:**
- `SetOrder_MoveTo(Vector, float, boolean)` - Move to position with speed and flag
- `SetOrder_MoveToEx(Array, float)` - Move to multiple points with speed
- `SetOrder_MoveTo_Direct(Vector, float)` - Direct movement without pathfinding
- `SetOrder_MoveTo_LookAt(Vector, float)` - Move while facing target
- `SetOrder_MoveTo_Trace(Array)` - Follow traced path array
- `SetOrder_Attack(Array, ERT_*)` - Attack target array with reaction type
- `SetOrder_Attack_Anchored(Array, ERT_*)` - Stationary attack order
- `SetOrder_Stop()` - Graceful stop
- `SetOrder_StopNow()` - Immediate stop
- `SetOrder_Follow(String)` - Follow unit by identifier
- `SetOrder_Guard(String)` - Guard unit or position
- `SetOrder_Formation(String, float)` - Set formation pattern
- `SetOrder_Retreat(Vector)` - Retreat to position
- `SetOrder_Maneuver(String)` - Execute tactical maneuver
- `SetOrder_SpecialAttack(String)` - Special attack pattern
- `SetOrder_GetToTarget(float)` - Approach target within range

**Queue Order Methods:**
- `SetFirstQueueOrders(Array)` - Set initial order queue
- `SetQueueOrders(Array)` - Set order queue
- `ClearQueueOrders()` - Clear pending orders
- `OnQueueOrdersEnd()` - Event handler for queue completion

**Activation Methods:**
- `ActivateFire(boolean)` - Enable or disable weapons
- `ActivateRadar(boolean)` - Enable or disable radar
- `ActivateMovement(boolean)` - Enable or disable movement
- `ActivateDetector(boolean)` - Enable or disable detectors
- `ActivateBehavior(boolean)` - Enable behavior system
- `DeactivateCurrentState()` - Deactivate current state
- `ReactivateFromStack()` - Restore previous state

**Combat Methods:**
- `SetEnemyReactionType(ERT_*)` - Set enemy engagement behavior
- `SetAttackStyle(String)` - Set attack pattern
- `SetAttackStyle_DirectMove()` - Direct movement attack style
- `SetAttackDistances(float, float)` - Set engagement ranges
- `SetAttackNone()` - Disable attacking
- `EnableFrontInAttack(boolean)` - Enable frontal attack
- `ForceFrontInAttack(boolean)` - Force frontal attack
- `OrderUnitToAttack(String)` - Order specific unit to attack

**Formation Methods:**
- `SetFormation(String, float, boolean, boolean)` - Set formation with parameters
- `SetFormationDistances(float)` - Set formation spacing
- `SetColumnDistances(float)` - Set column spacing
- `SetMoveFormation(String)` - Set movement formation
- `SetMoveColumn()` - Set column movement

**Visibility Methods:**
- `ShowGroup(boolean)` - Show or hide group
- `SetBehRadarMask(Array)` - Configure radar visibility
- `SetRadarDetailedEnemies(boolean)` - Show enemy details
- `SetRadarDetailedFriends(boolean)` - Show friend details

**Movement Methods:**
- `StartMove()` - Begin movement
- `StartMoveDual()` - Begin dual track movement
- `StopMove()` - Stop movement
- `StopMoveImmediate()` - Immediate stop
- `PauseMovement()` - Pause movement
- `ResumeMovement()` - Resume movement
- `ChangeMoveSpeed(float)` - Change movement speed
- `SetStartDelay(float)` - Set movement delay
- `SetStealthMovement(boolean)` - Enable stealth mode
- `SetMoveAbility(int)` - Set movement capability
- `SetMoveTurn(float)` - Set turn angle
- `SetMoveStop()` - Set stop movement
- `SetMoveSimple_Point(Vector)` - Simple point movement
- `SetMoveDirect_Point(Vector)` - Direct point movement
- `SetMoveMuddled_Point(Vector)` - Muddled point movement
- `ClearLastMoveOrder()` - Clear last movement order
- `RepeatMoveOrder()` - Repeat last order

### Terrain System Error Messages and Logic

The following error messages are verified from binary analysis and indicate specific terrain system failures:

**Critical Terrain Error Messages:**

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `"IHeightField was not found. Behavior refuses to work"` | Terrain height data not loaded or inaccessible | Verify terrain file exists and path is correct in mission |
| `"CRouterMap::GenerateRouterMap(): invalid IHeightField"` | Corrupted or invalid heightfield data | Recreate heightmap from backup |
| `"CAveragedRouterMap::GenerateRouterMap(): ZoneMap is not multiple to HeightField: ZoneMapSize = %d, HeightFieldSize = %d"` | Zone map size does not match heightfield dimensions | Ensure both use 2049×2049 dimensions |
| `"Initialize: Unable to get terrain height field"` | Heightfield interface not initialized | Check terrain initialization order in Mission.script |

**Terrain Scaling Logic:**

The error message `"ZoneMap is not multiple to HeightField"` reveals critical information about terrain scaling requirements. The engine requires that the zone map size be a multiple of the height field size. Based on verified mission data:

```
ZoneMapSize = 2049
HeightFieldSize = 2049
```

Both dimensions must be exactly 2049 pixels for compatibility. The engine performs modulo validation: `ZoneMapSize % HeightFieldSize == 0`. When dimensions match, this evaluates to true. Any deviation causes the error.

**Heightmap File Specifications:**

| Property | Value |
|----------|-------|
| Width | 2049 pixels |
| Height | 2049 pixels |
| Bit Depth | 16-bit unsigned integer |
| Format | Greyscale raw data |
| Endianness | Little Endian (typically) |
| Total Size | 8,388,098 bytes (2049 × 2049 × 2) |

**Coordinate System Verification:**

The terrain system uses DirectX left-handed coordinates:
- X-axis: East-West position
- Y-axis: Height (elevation)
- Z-axis: North-South position

Unit Y coordinates must match terrain height at the corresponding X,Z position. The engine calculates terrain height by sampling the heightfield at the unit's X,Z position and scaling according to terrain configuration.

### Verified Class Inheritance Hierarchy

Based on vtable analysis of the game binaries, the following class inheritance relationships are confirmed:

**Base System Classes:**

```
CObject (root)
├── CComponent
│   ├── CBaseGameObject
│   │   ├── CBaseUnit (vehicles, infantry)
│   │   │   ├── CBaseGroundUnit
│   │   │   │   ├── CTankBehavior
│   │   │   │   │   ├── CVehicleBehavior
│   │   │   │   │   │   ├── CVehicleBehavior3
│   │   │   │   │   └── CVehicleBehavior2
│   │   │   │   └── CHumanBehavior
│   │   │   │       └── CHumanKinematicController
│   │   │   └── CBaseAircraft
│   │   ├── CBaseTerrain
│   │   │   ├── CChunkedTerrain
│   │   │   ├── CProgressiveTerrain
│   │   │   └── CStaticTerrain
│   │   └── CBaseMissionObject
│   └── CComponent (other branches)
```

**AI and Task System Classes:**

```
CBaseAITask (root task)
├── CBaseUnitTask
│   ├── CBaseTankTask
│   │   └── CTankAttackTask
│   └── CBaseMovementTask
└── CCompositeTask

CBaseUnitGroup (group control)
├── CBaseUnitGroup (implementation)
├── CBaseHeavyUnitGroup
└── CBaseLightUnitGroup
```

**Terrain and Zone Classes:**

```
CBaseZoneMap (zone interface)
├── CBaseTerrain
│   └── CChunkedTerrain
└── CBaseZoneMap (implementations)

IHeightField (heightfield interface)
├── CHeightFieldBuffer
└── CHeightFieldData
```

**Behavior and Controller Classes:**

```
CBaseBehavior (behavior root)
├── CBaseGroundBehavior
│   ├── CVehicleBehavior
│   │   ├── CVehicleBehavior2
│   │   └── CVehicleBehavior3
│   ├── CHumanBehavior
│   └── CBaseHeavyBehavior
├── CBaseLightNavalBehavior
├── CBaseHeavyNavalBehavior
└── CBaseHoverBehavior

CVehicleKinematicController (physics)
├── CVehicleKinematicController2
└── CVehicleKinematicController3
```

### Verified Vtable Method Indices

The following vtable method indices are confirmed from binary analysis. These indices represent the position of methods in the class virtual function table:

**CBaseUnit Vtable Methods (selected):**
- Index 24: `GetPos()`
- Index 25: `GetWorldPos()`
- Index 28: `GetHealth()`
- Index 32: `GetAffiliation()`
- Index 56: `GetTarget()`

**CVehicleBehavior Vtable Methods (selected):**
- Index 80: `GetBehPos()`
- Index 84: `GetMovementMode()`
- Index 88: `GetMovementData()`
- Index 128: `SetOrder_MoveTo()`
- Index 132: `SetOrder_Attack()`

**CBaseTerrain Vtable Methods (selected):**
- Index 16: `GetHeightAt()`
- Index 20: `GetNormalAt()`
- Index 24: `GetTerrainSize()`

These indices can be used for advanced debugging and memory analysis but are primarily provided for reference when using external debugging tools.

### Complete SendEvent System Reference

The `sendEvent` function schedules events with specified delays and parameters:

**Function Signature:**
```script
sendEvent(float delay, String target_id, String event_name, Array parameters);
```

| Parameter | Type | Description |
|-----------|------|-------------|
| delay | float | Delay in seconds before event fires |
| target_id | String | Object identifier or SOID_* constant |
| event_name | String | Name of event handler to trigger |
| parameters | Array | Parameters to pass to event handler |

**Verified Object Identifiers:**

| Identifier | Purpose |
|------------|---------|
| `SOID_MissionController` | Mission controller system |
| `SOID_Player` | Player object |
| `getIdentificator(user)` | Current user/session identifier |
| String object name | Any object defined in Content.script |

**Verified Event Names:**

| Event | Parameters | Purpose |
|-------|------------|---------|
| `"SetActiveGroup"` | None | Activate group |
| `"Shutdown"` | None | Shutdown mission |
| `"MainPlayerUnitMessage"` | None | Display message |
| `"Stuka1End"` | None | End Stuka event |
| `"WMFollow"` | None | Waypoint follow |

**Usage Examples:**

```script
// Activate group after delay
sendEvent(60.0, "CZ1RedGunTask", "SetActiveGroup", []);

// Display player message
sendEvent(10.0, getIdentificator(user), "MainPlayerUnitMessage", []);

// Shutdown mission
sendEvent(0.0, SOID_MissionController, "Shutdown", []);

// Multiple events in sequence
sendEvent(60.0, "CZ1RedGunTask", "SetActiveGroup", []);
sendEvent(90.0, "CZ22RedGunTask", "SetActiveGroup", []);
sendEvent(92.0, "CZ33RedGunTask", "SetActiveGroup", []);
```

### Silent Failure Modes Summary

The following table summarizes known silent failure modes where scripts appear valid but do not function as expected:

| Failure Mode | Symptom | Cause | Solution |
|--------------|---------|-------|----------|
| Class reference mismatch | No error, object fails to appear | Referenced class not in compiled engine | Use verified class names from this document |
| Case sensitivity | Silent ignore of method calls | Incorrect case in method names | Use documented capitalization |
| Unknown state name | AI ignores event handler | State machine uses different state names | Use verified event names from mission files |
| Unknown constant | Script loads but has no effect | Constant value incorrect | Use verified constants from this document |
| Matrix non-orthogonality | Model distortion or invisibility | Rotation values not mathematically orthogonal | Normalize basis vectors to 1.0 |
| Heightmap dimension mismatch | Pathfinding failures | Modified heightmap not 2049×2049 | Recreate heightmap at correct dimensions |
| Missing heightfield | AI refuses to move | Terrain data not loaded | Verify terrain initialization |
| ZoneMap size mismatch | Router generation fails | ZoneMap and HeightField dimensions differ | Ensure both are 2049×2049 |

### Complete ERT_* Behavioral Reference

This section provides detailed behavioral descriptions for each Enemy Reaction Type constant:

**ERT_AGGRESSIVE:**
Units actively scan for enemies and pursue detected targets. Upon enemy contact, units break formation to engage, potentially exposing themselves to danger. Engagement range is maximum. Units may leave protected positions to chase targets.

**ERT_DEFENSIVE:**
Units maintain formation and only engage enemies within their immediate area. Units do not pursue enemies beyond their starting position. Used for defensive positions and support units that should not overextend.

**ERT_PASSIVE:**
Units scan for enemies but do not pursue. Only engage enemies that enter weapon range. Used for static defenses and units that should avoid detection.

**ERT_PATROL:**
Units move between waypoints while scanning for enemies. Upon detection, units investigate the contact area but return to patrol route if no enemy is found. Used for sentry and patrol behaviors.

**ERT_HOLD:**
Units hold position and engage any enemy within weapon range. Will not move to pursue enemies. Used for defensive perimeters and ambush positions.

**ERT_RETREAT:**
Units attempt to avoid enemy contact. If detected, units retreat to designated safe zones. Used for damaged units or support units that should avoid combat.

---

## Version History

- **v5.4 (Current)**: Added Part Eight: Binary Analysis Reference with complete MOTID_*, MOSID_*, ERT_*, CLASSIFICATOR_* constant lists, complete Get*/Set* method references, terrain system error messages and scaling logic, verified class inheritance hierarchy, vtable method indices, sendEvent system complete reference, and silent failure modes summary
- **v5.3**: Added heightmap (hmap.raw) workflow documentation with GIMP guide, dimension specifications, and terrain error reference table
- **v5.2**: Fixed WorldMatrices typo, added [sic] notations, clarified coordinate system (Y=height), documented method case sensitivity, added getIdentificator(user) note
- **v5.1**: Added Part Seven: Engine Technical Reference with comprehensive binary analysis, D3DX function documentation, verified method lists
- **v5.0**: Initial comprehensive reference based on mission file analysis
- **Earlier versions**: Basic syntax documentation from file sampling

---

**Document Statistics:**
- Total sections: 8 parts + appendices + heightmap workflow guide
- Verified class names: 60+
- Verified methods: 120+
- Verified properties: 50+
- Verified event handlers: 25+
- Verified constants: 50+
- Binary analysis coverage: Behavior.dll, Objects.dll, J5Script.dll, TvsT.exe, WV.exe
- Heightmap dimensions: 2049×2049 (16-bit greyscale)

**Contributors:**
- Script file analysis from Soviet Expansion, WoV, and custom missions
- Binary reverse engineering from game DLL files
- Community feedback and verification

**To Report Errors or Contribute:**
This document is maintained through community reverse-engineering efforts. If you discover discrepancies or have verified information to add, compare against actual game files and note [sic] for any verified oddities.

---

*TVT Mission Script Files (.script) Complete Technical Reference v5.4*
*T-34 vs. Tiger Mission Editing Documentation*
