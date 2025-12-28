# Output Structure Changes - Export Refactoring

## Summary
Modified the export output structure to:
1. **Name .obj and .stl files after the part name** instead of hardcoded "model"
2. **Move STL files to the previews root folder** for easier browsing
3. **Move FCBak files to the part's preview subfolder** to keep source directories clean
4. **Keep .obj and .glb files in the part subfolder** (unchanged location)
5. **Keep JSON and PNG files in the part subfolder** (unchanged location)

## File Structure Changes

### Before
```
cad/parts/BRK-001/
├── BRK-001.FCStd         (source file)
├── BRK-001.FCBak         (backup file)

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
cad/parts/BRK-001/
└── BRK-001.FCStd         ← Only source file remains!

previews/
├── BRK-001.stl           ← STL moved to root, named after part
└── cad/parts/BRK-001/BRK-001/
    ├── preview.png
    ├── preview.json
    ├── BRK-001.glb       ← Named after part (was: model.glb)
    ├── BRK-001.obj       ← Named after part (was: model.obj)
    ├── BRK-001.FCBak     ← Backup moved here
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
  - Remove any existing STL at destination (ensures updates replace old files)
  - Move to root location using `Path.rename()`
  - Handle move failures gracefully with fallback
- Move FCBak files from source directory to preview folder:
  - Detect FCBak file alongside source FCStd
  - Wait up to 2 seconds for FCBak to appear (FreeCAD creates it asynchronously)
  - Remove any existing FCBak at destination (ensures updates replace old files)
  - Move to part's preview subfolder with part name
  - Silent failure (debug log only) if FCBak doesn't exist after waiting

#### _export_glb() function signature changes
- Added optional parameter: `part_name: str = "model"`
- Function automatically uses this name via `out_path.with_suffix()`
- Maintains backward compatibility with default value

#### Manifest JSON updates
- STL artifact reference now points to root folder path
- Example: `previews/BRK-001.stl` instead of `previews/cad/parts/BRK-001/BRK-001/model.stl`
- Improves readability for users browsing artifacts

## Benefits

1. **Cleaner Source Directories**: Only FCStd files remain in source folders; FCBak backups moved to previews
2. **Easier Navigation**: Users can see all STL files at root level without diving into folder structure
3. **Clear Part Naming**: Files are named after their parts (BRK-001.stl, wheel.stl) instead of generic "model"
4. **Organized Structure**: JSON/PNG/backups remain with part data in subfolder; STL is at convenient root location
5. **Backward Compatible**: Default parameter values ensure existing code continues to work

## Testing

- STL converter tests pass ✓
- Mapper functions work correctly ✓
- No syntax errors in modified files ✓
