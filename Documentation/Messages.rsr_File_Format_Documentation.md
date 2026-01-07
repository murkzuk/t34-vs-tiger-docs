# T-34 vs. Tiger Messages.rsr File Format Documentation

## Table of Contents

1. [Overview](#overview)
2. [Encoding Requirements](#encoding-requirements)
3. [File Structure](#file-structure)
4. [Section Reference](#section-reference)
5. [Common Errors and Solutions](#common-errors-and-solutions)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Examples](#examples)
8. [Best Practices](#best-practices)

---

## Overview

The `Messages.rsr` file is a localized resource file used by the T-34 vs. Tiger game engine to store text strings for user interfaces, mission briefings, weapon names, and control mappings. This document describes the correct format, encoding, and structure required for the file to be properly loaded by the G5 game engine.

The file follows an INI-style configuration format with key-value pairs organized into named sections. Proper formatting is critical - even minor structural errors can cause the entire file to be skipped during game initialization, resulting in missing text throughout the game interface.

This documentation was created to consolidate knowledge gained during debugging sessions, where encoding issues and structural problems were identified and resolved. The information herein represents best practices and lessons learned from fixing real-world errors encountered during development.

---

## Encoding Requirements

### Required Encoding

The Messages.rsr file **must** be saved in **UTF-16 Little Endian (UTF-16LE)** encoding. This is a strict requirement of the G5 game engine's localization system. Using any other encoding will result in the file being rejected during game initialization.

The UTF-16LE encoding uses 2 bytes per character, with the least significant byte stored first. This format includes a Byte Order Mark (BOM) at the beginning of the file, which the engine uses to identify the encoding format. The BOM for UTF-16LE is the byte sequence `FF FE` (hexadecimal).

It is critically important to understand that UTF-16 Big Endian (which uses the BOM `FE FF`) is **not compatible** with this game engine, even though both are valid Unicode encodings. Similarly, UTF-8 encoding, while more common in modern applications, is completely incompatible with this legacy game engine's localization system.

### Byte Order Mark (BOM)

The Byte Order Mark is a 2-byte sequence that appears at the very beginning of the file. For UTF-16LE, this must be `FF FE` (in that order). The game engine reads this signature to determine both that the file is UTF-16 encoded and that it uses little-endian byte ordering.

When a file is saved correctly with UTF-16LE encoding, the BOM is automatically included by the text editor or save routine. You should never manually add or remove the BOM - if the encoding is correct, the BOM will be present automatically.

### Incorrect Encodings to Avoid

Several encoding formats are frequently mistaken for the correct format but will cause errors. UTF-8 is the most common alternative, but the engine explicitly requires UTF-16LE. UTF-8 with BOM (byte sequence `EF BB BF`) and UTF-8 without BOM are both incompatible. UTF-16 Big Endian (BOM `FE FF`) appears similar but has the byte order reversed, causing complete failure to parse. ASCII encoding, while simple, cannot represent non-ASCII characters and will fail for any international characters. Windows-1252 and other single-byte encodings are also incompatible with the engine's requirements.

### How to Save Correctly

**Using Notepad++ (Recommended for Windows):**

To save a file in the correct format using Notepad++, first open your file in the editor. Then navigate to the Encoding menu in the toolbar and select "Encode in UTF-16-LE". You will see the encoding indicator in the status bar change from "ANSI" or "UTF-8" to "UTF-16-LE". Finally, save the file using File → Save or Ctrl+S. The BOM will be automatically included when saving in this encoding.

**Using Python (for programmatic creation):**

```python
# Correct method - includes BOM automatically
with open('Messages.rsr', 'w', encoding='utf-16-le') as f:
    f.write(content)

# Alternative method using codecs
import codecs
with codecs.open('Messages.rsr', 'w', 'utf-16-le') as f:
    f.write(content)
```

**Using Visual Studio Code:**

Open the file in VS Code, click on the encoding indicator in the status bar (bottom right), select "Save with encoding," then choose "UTF-16 LE" from the dropdown list. The encoding will be saved with the proper BOM.

**Using Command Line (Linux/macOS with iconv):**

```bash
# Convert from UTF-8 to UTF-16LE
iconv -f UTF-8 -t UTF-16 Messages.rsr > Messages_new.rsr
```

### Verifying Encoding

After saving a file, you should verify that it has the correct encoding before using it in the game. Several methods exist to check the encoding.

**Using Python:**

```python
with open('Messages.rsr', 'rb') as f:
    bom = f.read(2)
    
if bom == b'\xff\xfe':
    print("✓ Correct: UTF-16 Little Endian with BOM")
elif bom == b'\xfe\xff':
    print("✗ Incorrect: UTF-16 Big Endian")
elif bom == b'\xef\xbb':
    print("✗ Incorrect: UTF-8 with BOM")
else:
    print("? Unknown encoding")
```

**Using hexdump (Linux/macOS):**

```bash
hexdump -C Messages.rsr | head -1
```

The output should show `ff fe` as the first bytes for a correct file.

**Using PowerShell (Windows):**

```powershell
$bytes = [System.IO.File]::ReadAllBytes("Messages.rsr")
if ($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
    Write-Host "✓ Correct: UTF-16LE"
}
```

---

## File Structure

### Basic Structure

The Messages.rsr file uses an INI-style format that has been standard for configuration files in Windows applications for decades. The file consists of sections, each identified by a section name enclosed in square brackets. Within each section, key-value pairs define the actual data stored in the file. Comments can be added using double slashes (`//`) at the beginning of a line.

Each section must be uniquely named - having multiple sections with the same name will cause parsing errors. All key-value pairs must belong to a section; keys defined outside of any section are considered orphaned and will generate warnings or errors.

### Section Syntax

A section is defined by placing the section name within square brackets on its own line. The section name can contain letters, numbers, and underscores, but should not contain spaces or special characters. After the section header, all subsequent lines containing key-value pairs belong to that section until a new section header is encountered or the file ends.

```ini
[SectionName]
key1=value1
key2=value2
```

### Key-Value Syntax

Each line within a section consists of a key name, an equals sign, and a value. The key name identifies the data element, while the value contains the actual data. Key names should be descriptive and follow a consistent naming convention throughout the file.

```ini
str_MainGun=88mm KwK 36 L/56
str_Version=1.0
```

Values can contain spaces, punctuation, and most characters. If a value must contain special characters like line breaks, different methods may be required depending on the engine's capabilities.

### Comments

Comments can be added using double slashes at the beginning of a line. The engine will ignore any line starting with `//`. Comments are useful for documenting the purpose of sections, keys, or providing notes for other developers.

```ini
// This is a comment
[Weapon]
str_MainGun=88mm KwK 36 // Main gun for Tiger
```

### Blank Lines

Blank lines are generally ignored by the parser and can be used to improve readability by separating logical groups of keys. Excessive blank lines do not cause errors but should be used judiciously to maintain a clean file structure.

### Valid Section Names

Based on the T-34 vs. Tiger game, the following section names are commonly used and should be supported by your file. The `[General]` section typically contains game-wide settings such as title, version, and copyright information. The `[Weapon]` section stores weapon names, descriptions, and ammunition types for all vehicles in the game. The `[Action]` section contains control mappings and action descriptions for user input. The `[Messages]` section holds mission-specific text including briefing objectives and unit names. The `[MissionTest]` section is used for mission testing and development purposes. The `[Locale]` section typically contains language-specific settings.

---

## Section Reference

### [General] Section

The General section contains game-wide settings and information. This section is typically small and contains metadata about the game or mod.

**Common Keys:**

The `str_GameTitle` key contains the full name of the game or mod as displayed to the user. The `str_Version` key stores the version number of the file or mod. The `str_Copyright` key contains copyright and authorship information. The `str_Author` key, when present, names the mod author or development team.

**Example:**

```ini
[General]
str_GameTitle=T-34 vs. Tiger REDUX
str_Version=1.0
str_Copyright=Copyright 2024 Murkzuk
str_Author=Murkzuk
```

### [Weapon] Section

The Weapon section defines all weapons available in the game, including main guns, machine guns, and ammunition types. Keys follow a specific naming convention starting with `str_` followed by the weapon identifier and a suffix indicating the type of string.

**Naming Convention:**

The key name structure is `str_{WeaponIdentifier}_{Type}`, where WeaponIdentifier uniquely identifies the weapon and Type indicates the string type. The FullName type contains the complete name of the weapon (e.g., "8.8cm KwK 36 L/56"). The ShortName type contains an abbreviated name (e.g., "88mm"). The Description type provides a detailed description of the weapon. The CalibreHE, CalibreAP, and CalibreSAP types identify specific ammunition types for the weapon.

**Common Weapons:**

The game includes weapons for both the T-34 tank (85mm and 76mm variants) and the Tiger I tank (88mm KwK 36). Machine guns include the DT machine gun used by Soviet vehicles and various German alternatives.

**Example:**

```ini
[Weapon]
str_T344485mmMainGun=8.8cm KwK 36 L/56
str_T344485mmShortName=88mm
str_T344485mmCalibreHE=88mm HE Shell
str_T344485mmCalibreAP=88mm AP Shell
str_T344485mmSubCalibreAP=88mm Sub-Caliber AP
str_T3444CoaxialDT=7.62mm DT Coaxial MG
str_T3444BowDT=7.62mm DT Bow MG
str_T6E88mmMainGun=8.8cm KwK 36 L/56
str_T6E88mmCalibreHE=88mm High Explosive
str_T6E88mmCalibreAP=88mm Armor Piercing
```

### [Action] Section

The Action section defines control mappings and action descriptions for user input. These strings are used in the control settings menu and in-game prompts.

**Naming Convention:**

Action keys follow the pattern `str_{ActionName}`, where ActionName corresponds to a specific game action. Common actions include those for vehicle control (rotate, move, speed), weapon control (fire, aim), and camera control.

**Common Actions:**

The `str_ROTATE_LR_AXIS_ABS` key describes left/right rotation input. The `str_MOVE_FB_AXIS_ABS` key describes forward/backward movement. The `str_MOVE_LR_AXIS_ABS` key describes left/right strafing movement. The `str_SPEED` key describes speed or throttle control. The `str_FIRE` key describes the primary fire control. The `str_AIM` key describes the aiming or turret traverse control.

**Example:**

```ini
[Action]
str_ROTATE_LR_AXIS_ABS=Rotate Left/Right
str_MOVE_FB_AXIS_ABS=Move Forward/Back
str_MOVE_LR_AXIS_ABS=Move Left/Right
str_SPEED=Speed / Throttle
str_FIRE=Fire Main Gun
str_AIM=Turret Aim
```

### [Messages] Section

The Messages section contains mission-specific text including briefing objectives and unit names. This section is critical for mission functionality and must exist for missions to display proper text.

**Common Keys:**

The `MissionName` key contains the display name of the mission. The `BriefingText` key contains the mission briefing text shown at the start. The `Objective01`, `Objective02`, and `Objective03` keys contain individual mission objectives. The `Name` key typically contains a unit or object name.

**Example:**

```ini
[Messages]
MissionName=Operation Citadel
BriefingText=Attack the enemy position at dawn.
Objective01=Destroy the enemy tanks
Objective02=Secure the village
Objective03=Reinforce the forward position
Name=Tiger Command
```

### [MissionTest] Section

The MissionTest section is used for testing and development purposes, containing temporary or test mission strings.

**Common Keys:**

Similar to the [Messages] section, this typically includes `MissionName`, `BriefingText`, and objective keys used during development and testing phases.

**Example:**

```ini
[MissionTest]
MissionName=Test Mission
BriefingText=Testing new features
Objective01=Test objective 1
Objective02=Test objective 2
```

### [Locale] Section

The Locale section contains language and localization settings for the game.

**Common Keys:**

The `Language` key specifies the language code (e.g., "EN" for English, "DE" for German). The `str_LanguageName` key contains the human-readable language name.

**Example:**

```ini[Locale]
Language=EN
str_LanguageName=English
```

---

## Common Errors and Solutions

### Error: "Invalid UTF-16 signature"

**Error Message:**
```
[Locale] File Resources\Messages.rsr has invalid UTF-16 signature, skipping..
```

**Cause:**

This error occurs when the Messages.rsr file is saved in an encoding other than UTF-16 Little Endian. The game engine specifically requires UTF-16LE with the FF FE BOM, and any other encoding will cause the file to be completely skipped during loading.

**Common Incorrect Encodings:**

This error is most commonly caused by saving the file as UTF-8, which is the default encoding for many modern text editors. UTF-16 Big Endian (BE) encoding also produces this error, as the byte order is reversed. Windows-1252 or other single-byte encodings will trigger this error as well. ASCII encoding cannot represent the full Unicode character set needed and will fail.

**Solution:**

Re-save the file in UTF-16 Little Endian encoding. In Notepad++, use Encoding → Encode in UTF-16-LE, then save. In Python, use `encoding='utf-16-le'` when writing the file. Verify the fix by checking that the first two bytes of the file are `FF FE`.

### Error: "Multiply definition of section [X]"

**Error Message:**
```
[Locale] Multiply definition of section [Weapon]
```

**Cause:**

This error occurs when the same section header appears multiple times in the file. The INI parser expects each section to be defined exactly once, with all key-value pairs for that section grouped together.

**Example of Incorrect Structure:**

```ini
[Weapon]
str_MainGun=Gun 1

[Weapon]
str_MachineGun=MG 1
```

**Solution:**

Merge all key-value pairs into a single section definition. Each section should appear only once.

**Correct Structure:**

```ini
[Weapon]
str_MainGun=Gun 1
str_MachineGun=MG 1
```

### Error: "Key X doesn't belong to any section"

**Error Message:**
```
[Locale] Key str_ROTATE_LR_AXIS_ABS doesn't belong to any section
```

**Cause:**

This error occurs when a key-value pair is defined outside of any section. All keys must be placed within a section; keys at the file level (before the first section or between sections) are considered orphaned.

**Example of Incorrect Structure:**

```ini
str_OrphanKey=Some Value

[Weapon]
str_MainGun=Gun
```

**Solution:**

Move the orphaned key into the appropriate section. Determine which section the key belongs to based on its naming convention and purpose, then place it within that section header.

**Correct Structure:**

```ini
[Weapon]
str_MainGun=Gun
str_OrphanKey=Some Value
```

### Error: "There is no section [Messages]"

**Error Message:**
```
[Locale] There is no section [Messages]
[Locale] There is no section [Messages]
[Locale] There is no section [Messages]
(repeated multiple times)
```

**Cause:**

This error occurs when mission scripts or other game systems attempt to access keys from a [Messages] section that does not exist in the file. The repeated errors indicate multiple attempts to access missing data.

**Solution:**

Add a [Messages] section to the file with the required keys. The specific keys needed depend on which missions and scripts are being used. At minimum, include keys referenced in the error messages.

### Error: "Can not assign value (error) to typed variable (String)"

**Error Message:**
```
Can not assign value (error) to typed variable (String)
```

**Cause:**

This runtime error occurs when a script attempts to store a localization string into a string variable, but the string lookup has failed (returning the value "error" or an empty string). This is typically a cascade effect caused by missing keys in the Messages.rsr file.

**Solution:**

Identify the missing keys by checking the error context and the script that triggered the error. Add the missing keys to the appropriate section in Messages.rsr with appropriate values.

### Error: "There is no key X in section [Y]"

**Error Message:**
```
[Locale] There is no key str_T344485mmMainGun in section [Weapon]
```

**Cause:**

This error occurs when a script or game system attempts to access a key that does not exist in the specified section. The key may be misspelled, the wrong section may be specified, or the key may simply not have been defined.

**Solution:**

Either add the missing key to the specified section or, if the key name is incorrect, fix the reference in the code or script that is attempting to access it.

---

## Troubleshooting Guide

### Quick Diagnostic Steps

When encountering errors related to Messages.rsr, follow these diagnostic steps to identify and resolve the issue.

**Step 1: Verify Encoding**

First, check that the file is saved in the correct encoding. Open the file in a hex editor or use Python to check the first two bytes. The bytes should be `FF FE` (UTF-16LE BOM). If you see `EF BB BF` (UTF-8 BOM), `FE FF` (UTF-16BE BOM), or any other sequence, the encoding is incorrect and must be fixed.

**Step 2: Check File Structure**

Open the file in a text editor that can handle UTF-16LE (Notepad++ recommended) and verify the structure. Look for duplicate section headers, orphaned keys (keys outside sections), and missing sections that may be referenced by scripts.

**Step 3: Validate Key Names**

Ensure all keys referenced by scripts exist in the Messages.rsr file with the correct names and are in the correct sections. Typos in key names are a common source of errors.

**Step 4: Check Error Log Context**

Review the game execution log to understand the sequence of errors. The first errors often indicate the root cause, with subsequent errors being cascade effects.

### Diagnostic Script

The following Python script can be used to analyze a Messages.rsr file and identify common issues:

```python
#!/usr/bin/env python3
"""
Messages.rsr Diagnostic Script
Analyzes a Messages.rsr file for common issues.
"""

import re
import sys

def analyze_messages_rsr(filepath):
    """Analyze Messages.rsr file and report issues."""
    
    # Read file
    with open(filepath, 'r', encoding='utf-16-le') as f:
        content = f.read()
    
    issues = []
    warnings = []
    
    # Check for duplicate sections
    sections = re.findall(r'\[([^\]]+)\]', content)
    section_counts = {}
    for section in sections:
        section_counts[section] = section_counts.get(section, 0) + 1
    
    for section, count in section_counts.items():
        if count > 1:
            issues.append(f"Duplicate section [{section}] found {count} times")
    
    # Check for keys outside sections
    lines = content.split('\n')
    current_section = None
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('//'):
            continue
        
        # Check for section header
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
        # Check for key-value pair
        elif '=' in line:
            key = line.split('=')[0].strip()
            if current_section is None:
                issues.append(f"Line {line_num}: Key '{key}' outside any section")
    
    # Report results
    print("=" * 60)
    print("Messages.rsr Analysis Report")
    print("=" * 60)
    print(f"File: {filepath}")
    print(f"Sections found: {len(sections)}")
    print(f"Unique sections: {len(section_counts)}")
    print()
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ No structural issues found")
    
    print()
    print("Sections:")
    for section, count in sorted(section_counts.items()):
        marker = " (duplicate!)" if count > 1 else ""
        print(f"  [{section}]{marker}")
    
    return len(issues) == 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "Messages.rsr"
    
    success = analyze_messages_rsr(filepath)
    sys.exit(0 if success else 1)
```

Save this script as `diagnose_messages.py` and run it with Python:

```bash
python3 diagnose_messages.py Messages.rsr
```

---

## Examples

### Complete Example: Basic Messages.rsr

This example shows a minimal but complete Messages.rsr file with all essential sections:

```ini
// T-34 vs. Tiger REDUX - Messages.rsr
// Encoding: UTF-16 Little Endian (FF FE BOM)

[General]
str_GameTitle=T-34 vs. Tiger REDUX
str_Version=1.0
str_Copyright=Copyright 2024 Murkzuk

[Weapon]
str_T344485mmMainGun=8.8cm KwK 36 L/56
str_T344485mmShortName=88mm
str_T344485mmCalibreHE=88mm High Explosive Shell
str_T344485mmCalibreAP=88mm Armor Piercing Shell
str_T344485mmSubCalibreAP=88mm Sub-Caliber AP
str_T3444CoaxialDT=7.62mm DT Coaxial MG
str_T3444BowDT=7.62mm DT Bow MG
str_T6E88mmMainGun=8.8cm KwK 36 L/56
str_T6E88mmCalibreHE=88mm HE Shell
str_T6E88mmCalibreAP=88mm AP Shell
str_T6ECoaxialMG=7.92mm MG 34 Coaxial
str_T6EBowMG=7.92mm MG 34 Bow
str_Empty_Weapon=No Weapon

[Action]
str_ROTATE_LR_AXIS_ABS=Rotate Left/Right
str_MOVE_FB_AXIS_ABS=Move Forward/Back
str_MOVE_LR_AXIS_ABS=Strafe Left/Right
str_SPEED=Speed / Throttle
str_FIRE=Fire Main Gun
str_AIM=Aim Turret
str_SWITCH_WEAPON=Switch Weapon
str_ZOOM_IN=Zoom In
str_ZOOM_OUT=Zoom Out

[Messages]
MissionName=Securing Kurtenk REDUX
BriefingText=Overall Campaign Situation:\n\nSince the failure of Operation Citadel, the German forces have been pushed back. Secure the village of Kurtenk before the Soviet counterattack.
Objective01=Eliminate enemy resistance in the village
Objective02=Secure all strategic points
Objective03=Hold position until reinforcements arrive
Name=Securing Kurtenk REDUX

[MissionTest]
MissionName=Test Mission
BriefingText=Testing new features and fixes
Objective01=Test objective
```

### Example: Fixing Duplicate Sections

**Before (Incorrect):**

```ini
[Weapon]
str_T344485mmMainGun=88mm Gun

[Weapon]
str_T344485mmCalibreHE=HE Shell

[Weapon]
str_T344485mmCalibreAP=AP Shell
```

**After (Correct):**

```ini
[Weapon]
str_T344485mmMainGun=88mm Gun
str_T344485mmCalibreHE=HE Shell
str_T344485mmCalibreAP=AP Shell
```

### Example: Fixing Orphaned Keys

**Before (Incorrect):**

```ini
str_OrphanKey=This is outside any section

[Weapon]
str_MainGun=Main Gun
```

**After (Correct):**

```ini
[Weapon]
str_OrphanKey=This is now inside the Weapon section
str_MainGun=Main Gun
```

---

## Best Practices

### 1. Always Use Correct Encoding

Never compromise on encoding. UTF-16LE is a strict requirement, and using any other encoding will cause the file to fail loading entirely. Establish a consistent process for creating and editing Messages.rsr files that ensures the correct encoding is always used.

### 2. Maintain Section Uniqueness

Each section should appear exactly once in the file. When adding new keys, place them within the existing appropriate section rather than creating a new section with the same name. This maintains a clean, predictable file structure that is easy to parse and maintain.

### 3. Use Consistent Naming Conventions

Follow established naming conventions for keys. The `str_` prefix indicates a string value. Group related keys with consistent identifiers (e.g., all T-34 weapon keys should follow the same pattern). Use descriptive names that clearly indicate the purpose of each key.

### 4. Document Your Sections

Add comments at the top of each major section to document its purpose and contents. This helps other developers (and your future self) understand the file structure and makes maintenance easier.

### 5. Validate Before Deployment

Before deploying a modified Messages.rsr file to production, run it through a validation script to check for common errors. The diagnostic script provided in this document can catch most issues before they cause problems in the game.

### 6. Version Control Your Files

Keep Messages.rsr files under version control (Git) to track changes over time. This makes it easy to identify when an error was introduced and to roll back problematic changes.

### 7. Backup Before Editing

Always create a backup of your Messages.rsr file before making edits. Simple mistakes can cause the entire file to be rejected by the game engine, and having a backup allows quick recovery.

### 8. Test in the Game

After making changes to Messages.rsr, always test them in the actual game environment. Some errors may only manifest during actual game loading, and visual verification ensures the strings appear correctly in the game interface.

---

## Additional Resources

### Related Documentation

- **TVT Mission Script Format Reference:** `TVT_Mission_Script_Format_Complete_Reference GOLD.md` - Complete reference for mission scripting in T-34 vs. Tiger
- **Tank Unit Scripts:** `TankPzVIAusfEUnit.script` and `TankPzVITigerE1Unit.script` - Examples of tank unit configuration

### Tools for Working with Messages.rsr

**Text Editors:**
- Notepad++ - Recommended for Windows, excellent UTF-16 support
- Visual Studio Code - Good UTF-16 support with encoding detection
- Sublime Text - Can handle UTF-16LE with proper encoding selection

**Hex Editors:**
- HxD (Windows) - Free hex editor for verifying encoding
- hexdump (Linux/macOS) - Command-line tool for viewing file bytes
- Bless (Linux) - Graphical hex editor

**Development Tools:**
- Python 3.x - For programmatic file manipulation and validation
- iconv - Command-line encoding converter for Linux/macOS

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024 | Murkzuk | Initial documentation created from debugging session findings |

---

## License

This documentation is provided for the T-34 vs. Tiger REDUX mod project. Feel free to use and adapt for similar projects using the G5 game engine.

---

*Document generated for the T-34 vs. Tiger REDUX project. For questions or corrections, please refer to the project repository.*
