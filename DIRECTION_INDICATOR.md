# GPS Direction Indicator

## Overview
A GPS direction indicator has been added to the onroad screen that displays the current heading direction using cardinal directions (N, NE, E, SE, S, SW, W, NW).

## Features
- **Real-time GPS heading**: Uses GPS bearing data to determine the direction the vehicle is pointing
- **Cardinal direction display**: Shows 8 cardinal directions (N, NE, E, SE, S, SW, W, NW)
- **Visual indicator**: Circular indicator with direction text in the top-left corner of the screen
- **GPS validation**: Only displays when GPS has a valid fix
- **Fallback support**: Works with both `gpsLocation` and `gpsLocationExternal` data sources

## Implementation Details

### Files Modified
1. **`openpilot/selfdrive/ui/ui_state.py`**
   - Added GPS data subscriptions (`gpsLocation`, `gpsLocationExternal`)

2. **`openpilot/selfdrive/ui/onroad/hud_renderer.py`**
   - Added GPS heading tracking variables
   - Implemented `_get_direction_text()` method for heading to cardinal direction conversion
   - Added GPS data processing in `_update_state()`
   - Implemented `_draw_direction_indicator()` method for rendering

### Direction Mapping
The heading is converted to cardinal directions using the following ranges:
- **N**: 337.5° - 22.5° (North)
- **NE**: 22.5° - 67.5° (Northeast)
- **E**: 67.5° - 112.5° (East)
- **SE**: 112.5° - 157.5° (Southeast)
- **S**: 157.5° - 202.5° (South)
- **SW**: 202.5° - 247.5° (Southwest)
- **W**: 247.5° - 292.5° (West)
- **NW**: 292.5° - 337.5° (Northwest)

### Visual Design
- **Position**: Top-left corner of the screen
- **Size**: 60px circular indicator
- **Background**: Semi-transparent black circle with white border
- **Text**: Bold white text showing the cardinal direction
- **Visibility**: Only shown when GPS has a valid fix

## Technical Notes
- Heading data comes from GPS `bearingDeg` field
- Supports both internal (`gpsLocation`) and external (`gpsLocationExternal`) GPS sources
- Heading is normalized to 0-360 degrees before conversion
- The indicator automatically updates when GPS data is available
- No performance impact as it only renders when GPS is valid

## Usage
The direction indicator will automatically appear on the onroad screen when:
1. The vehicle is started and onroad
2. GPS has a valid fix
3. Heading data is available

The indicator shows the direction the vehicle is currently pointing, which is useful for navigation and orientation purposes.