# Output Structure Changes - Export Refactoring

## Summary
Modified the export output structure to:
1. **Name .obj and .stl files after the part name** instead of hardcoded "model"
2. **Move STL files to the previews root folder** for easier browsing
3. **Keep .obj and .glb files in the part subfolder** (unchanged location)
4. **Keep JSON, PNG, and FCStd/FCBak files in the part subfolder** (unchanged location)

## File Structure Changes

### Before
```
previews/
└── cad/parts/BRK-001/BRK-001/
    ├── preview.png
    ├── preview.json
    ├── model.glb          (or model.obj / model.stl)
    ├── model.obj          (if available)
    ├── model.stl          (if converted from OBJ)
```

### After
```
previews/
├── BRK-001.stl           ← STL moved to root, named after part
├── cad/parts/BRK-001/BRK-001/
│   ├── preview.png
│   ├── preview.json
│   ├── BRK-001.glb       ← Named after part (was: model.glb)
│   ├── BRK-001.obj       ← Named after part (was: model.obj)
```

## Technical Changes

### 1. mapper.py
Added new function `stl_root_path_rel(source_rel: str) -> str`:
- Maps source path to STL file at previews root
- Example: `cad/parts/BRK-001/BRK-001.FCStd` → `previews/BRK-001.stl`

### 2. exporter.py

#### Import changes
- Added import of `stl_root_path_rel` from mapper

#### export_active_document() changes
- Extract `part_name` from source file path using `Path.stem`
- Pass `part_name` to `_export_glb()` function
- Use `part_name` for file naming:
  - `glb_path = out_dir / f"{part_name}.glb"`
  - `obj_path = glb_path.with_suffix(".obj")`
  - `stl_path = glb_path.with_suffix(".stl")`
- Move generated STL files from part folder to previews root:
  - Check if STL exists in part folder
  - Move to root location using `Path.rename()`
  - Handle move failures gracefully with fallback

#### _export_glb() function signature changes
- Added optional parameter: `part_name: str = "model"`
- Function automatically uses this name via `out_path.with_suffix()`
- Maintains backward compatibility with default value

#### Manifest JSON updates
- STL artifact reference now points to root folder path
- Example: `previews/BRK-001.stl` instead of `previews/cad/parts/BRK-001/BRK-001/model.stl`
- Improves readability for users browsing artifacts

## Benefits

1. **Easier Navigation**: Users can see all STL files at root level without diving into folder structure
2. **Clear Part Naming**: Files are named after their parts (BRK-001.stl, wheel.stl) instead of generic "model"
3. **Organized Structure**: JSON/PNG remain with part data in subfolder; STL is at convenient root location
4. **Backward Compatible**: Default parameter values ensure existing code continues to work

## Testing

- STL converter tests pass ✓
- Mapper functions work correctly ✓
- No syntax errors in modified files ✓
