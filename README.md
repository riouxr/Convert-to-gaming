# BB Convert to Gaming - Blender Addon

## What's New in v2.1.4

### New Features
- ✅ **Transfer UVs button** - Automatically adds Data Transfer modifiers to High collection objects
- ✅ Transfers UV data from Low collection objects back to High collection
- ✅ Uses Nearest Face Interpolated mapping for accurate UV transfer
- ✅ Matches objects by name (removes _high, adds _low to find corresponding object)

## What's New in v2.1.1

### Bug Fixes
- ✅ **Fixed naming issue** - Objects like `screw_0001_high` now correctly become `screw_0001_low` (not `screw_0001_high.001_low`)
- ✅ Properly strips Blender auto-numbering (.001, .002, etc.) and _high suffix before adding _low

## What's New in v2.1

### New Features
- ✅ **Add _High Suffix button** - Quickly add "_high" suffix to all objects in High collection
- ✅ Improved workflow with optional naming step

## What's New in v2.0

### Code Quality Improvements
- ✅ Added comprehensive docstrings to all functions
- ✅ Reduced excessive console logging (only important messages shown)
- ✅ Added explanatory comments for magic numbers and constants
- ✅ Cleaned up inconsistent metadata
- ✅ Removed commented-out code
- ✅ Improved error handling consistency

### Functional Changes
- ✅ **Now applies ALL remaining modifiers** (not just Mirror/Bevel) after removing Subsurf/Smooth
- ✅ Added helpful UI instructions in the panel
- ✅ Updated panel header to "BB Convert to Gaming"
- ✅ Improved weighted normal settings (keep_sharp=True, weight=50)

## Description

Automates the conversion of high-poly 3D models into optimized low-poly versions suitable for gaming, with UV transfer capabilities.

## Installation

1. Download `BB_Convert_to_Gaming_v2.1.5.zip`
2. In Blender: Edit → Preferences → Add-ons → Install
3. Select the downloaded ZIP file
4. Enable "BB Convert to Gaming" in the addon list

## How to Use

### Setup
1. Create a collection named **"High"** in your scene
2. Place all your high-poly objects in the "High" collection

### Workflow

**Step 0: Add _High Suffix (Optional)**
- Click the **"Add _High Suffix"** button to add "_high" suffix to all objects
- If an object already has "_high" suffix, it will be skipped
- If an object has a different suffix, "_high" will be added after it
- This helps organize your naming convention

**Step 1: Convert**
- Click the **"Convert"** button in the Tool panel (N-panel sidebar)
- This will:
  - Duplicate all objects from "High" to a new "Low" collection
  - Add "_low" suffix to object names
  - Remove Subdivision Surface and Smooth modifiers
  - Apply ALL remaining modifiers (Mirror, Bevel, Array, etc.)
  - Add a planar Decimate modifier (0.5° angle threshold)
  - Hide the "High" collection

**Step 2: Adjust Decimate Settings (Optional)**
- Select objects in the "Low" collection
- In the Modifiers panel, find the "DecimatePlanar" modifier
- Adjust the **Angle Limit** slider to control decimation strength:
  - Lower values (0.1° - 0.5°): More aggressive, removes more faces
  - Higher values (1° - 5°): More conservative, preserves more detail
- Preview the result in the viewport before applying

**Step 3: Fix nGones**
- Click the **"Fix nGones"** button
- This will:
  - Apply the Decimate modifier to reduce polygons
  - Triangulate large n-gons (faces with >5 edges)
  - Convert triangles back to quads where possible
  - Add and apply Weighted Normal modifier for better shading

**Step 4: Transfer UVs**
- Click the **"Transfer UVs"** button
- This will:
  - Add Data Transfer modifiers to all objects in the "High" collection
  - Set the source object to the corresponding "_low" object
  - Configure Face Corner Data with UV transfer
  - Use Nearest Face Interpolated mapping for accurate UV projection
  - Automatically apply all Data Transfer modifiers to bake the UVs
- Use this after unwrapping UVs on your low-poly models to transfer them back to high-poly

### Result
You'll have optimized low-poly models in the "Low" collection, and can transfer their UVs back to the high-poly originals for baking!

## Technical Details

### Constants
- `PLANAR_ANGLE_DEGREES = 0.5` - Angle threshold for dissolving coplanar faces
- `NGON_EDGE_THRESHOLD = 5` - Faces with more edges are triangulated first

### Modifier Processing
1. **Removed**: Subdivision Surface, Smooth (add polygons unnecessarily)
2. **Applied**: ALL other modifiers (Mirror, Bevel, Array, Solidify, etc.)
3. **Added**: Planar Decimate (DISSOLVE type)
4. **Final**: Weighted Normal for improved low-poly shading

### Data Transfer Settings
- **Face Corner Data**: Enabled (Face Data disabled)
- **Data Type**: UVs only
- **Mapping**: Nearest Face Interpolated (POLYINTERP_NEAREST)
- **Object Matching**: Removes "_high" suffix and adds "_low" to find source object

### Collection Structure
```
Scene Collection
├── High (hidden after Convert, receives UV data)
│   └── [Original high-poly objects with _high suffix]
└── Low
    └── [Optimized low-poly objects with _low suffix]
```

## Typical Workflow for Game Assets

1. Model your high-poly assets and place them in "High" collection
2. Add "_high" suffix using the button (optional but recommended)
3. Click "Convert" to create low-poly versions
4. Adjust decimate settings if needed
5. Click "Fix nGones" to finalize low-poly geometry
6. Unwrap UVs on the low-poly models
7. Click "Transfer UVs" to copy UVs back to high-poly models
8. Bake textures from high to low using the shared UV layout

## Requirements

- Blender 4.2.0 or higher

## License

GPL-3.0-or-later

## Authors

- Blender Bob
- Claude.ai

## Support

For issues or questions, visit: https://github.com/riouxr/Convert-to-gaming
