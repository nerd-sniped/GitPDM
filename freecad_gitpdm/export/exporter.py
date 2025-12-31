# -*- coding: utf-8 -*-
"""
Deterministic preview exporter (PNG + JSON manifest).

Constraints:
- Only stdlib + FreeCAD shipped modules
- No shell=True; use subprocess via JobRunner only for git staging
- JSON sorted keys; LF endings; fixed precision for stats
"""

import json
import hashlib
import time
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from freecad_gitpdm.core import log
from freecad_gitpdm.core import paths as core_paths
from freecad_gitpdm.export.preset import load_preset
from freecad_gitpdm.export.mapper import to_preview_dir_rel, stl_root_path_rel
from freecad_gitpdm.export.stl_converter import obj_to_stl


@dataclass
class ExportResult:
    ok: bool
    png_path: Optional[Path]
    json_path: Optional[Path]
    glb_path: Optional[Path]
    rel_dir: Optional[str]
    message: Optional[str]
    thumbnail_error: Optional[str]
    glb_error: Optional[str]
    mesh_stats: Optional[Dict[str, Any]]
    warnings: List[str]
    preset_used: Dict[str, Any]


def _freecad_version_string() -> str:
    try:
        import FreeCAD
        v = getattr(FreeCAD, "Version", None)
        if callable(v):
            ver = v()
            # FreeCAD.Version() may return a tuple or dict-like
            try:
                return str(ver)
            except Exception:
                pass
        return f"{getattr(FreeCAD, 'Version', 'unknown')}"
    except Exception:
        return "unknown"


def _doc_and_view() -> Tuple[Any, Any]:
    try:
        import FreeCAD, FreeCADGui
        doc = FreeCAD.ActiveDocument
        view = None
        try:
            view = FreeCADGui.ActiveDocument.ActiveView
        except Exception:
            try:
                view = FreeCADGui.ActiveDocument.ActiveView
            except Exception:
                view = None
        return doc, view
    except Exception:
        return None, None


def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log.warning(f"SHA256 failed: {e}")
        return None


def _move_fcbak_to_previews(source_fcstd: Path, preview_dir: Path, part_name: str, max_backups: int = 3) -> bool:
    """
    Move FCBak file from source directory to preview folder.
    FreeCAD creates FCBak files during save with timestamps (e.g., filename.20251230-213417.FCBak).
    This function waits briefly for the file to appear before moving it.
    Also cleans up old backups keeping only the most recent max_backups files.
    
    Args:
        source_fcstd: Path to the source FCStd file
        preview_dir: Directory where previews are stored
        part_name: Name of the part (used for searching backups)
        max_backups: Maximum number of backup files to keep (default: 3)
    
    Returns True if FCBak was moved, False otherwise.
    """
    parent = source_fcstd.parent
    stem = source_fcstd.stem  # Get filename without extension
    
    log.info(f"Looking for FCBak files matching: {stem}.*.FCBak in {parent}")
    log.info(f"Max backups to keep: {max_backups}")
    
    # Wait up to 2 seconds for FCBak to appear (FreeCAD creates it asynchronously)
    max_attempts = 20
    wait_interval = 0.1  # 100ms
    
    moved_successfully = False
    
    for attempt in range(max_attempts):
        try:
            # Search for FCBak files matching the pattern: filename.*.FCBak
            # FreeCAD creates files like "Square Test.20251230-213417.FCBak"
            pattern = f"{stem}.*.FCBak"
            fcbak_files = list(parent.glob(pattern))
            
            if fcbak_files:
                # Get the most recent FCBak file (in case there are multiple)
                fcbak_source = max(fcbak_files, key=lambda p: p.stat().st_mtime)
                log.info(f"Found FCBak file: {fcbak_source}")
                
                try:
                    # Create Backup subfolder inside preview directory
                    backup_dir = preview_dir / "Backup"
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Keep the timestamped name in the backup folder
                    fcbak_dest = backup_dir / fcbak_source.name
                    # Remove existing FCBak if present (Windows won't overwrite on rename)
                    if fcbak_dest.exists():
                        fcbak_dest.unlink()
                    # Move FCBak to the part's preview/Backup folder
                    fcbak_source.rename(fcbak_dest)
                    log.info(f"FCBak moved to previews/Backup: {fcbak_dest.name}")
                    moved_successfully = True
                    
                    # Clean up old backups - keep only the most recent max_backups files
                    # Skip cleanup if max_backups is -1 (unlimited) or 0 (no backups)
                    if max_backups > 0:
                        _cleanup_old_backups(backup_dir, stem, max_backups)
                    
                    return True
                except Exception as e:
                    log.warning(f"Failed to move FCBak: {e}")
                    return False
        except Exception as e:
            log.warning(f"Error searching for FCBak: {e}")
        
        # Wait a bit before checking again
        if attempt < max_attempts - 1 and not moved_successfully:
            time.sleep(wait_interval)
    
    # FCBak file never appeared (this is normal if FreeCAD didn't create one)
    log.debug(f"No FCBak file found matching {stem}.*.FCBak")
    return False


def _cleanup_old_backups(backup_dir: Path, part_stem: str, max_backups: int):
    """
    Remove old backup files, keeping only the most recent max_backups files.
    
    Args:
        backup_dir: Directory containing backup files
        part_stem: Stem of the part name (e.g., "Square Test")
        max_backups: Maximum number of backups to keep
    """
    try:
        # Find all backup files for this part
        pattern = f"{part_stem}.*.FCBak"
        backup_files = list(backup_dir.glob(pattern))
        
        if len(backup_files) <= max_backups:
            return  # Nothing to clean up
        
        # Sort by modification time, newest first
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Remove old backups beyond the limit
        files_to_remove = backup_files[max_backups:]
        for old_backup in files_to_remove:
            try:
                old_backup.unlink()
                log.info(f"Removed old backup: {old_backup.name}")
            except Exception as e:
                log.warning(f"Failed to remove old backup {old_backup.name}: {e}")
    except Exception as e:
        log.warning(f"Failed to cleanup old backups: {e}")


def _compute_bbox_mm(doc) -> Optional[Tuple[float, float, float]]:
    """Compute bounding box size in mm (robust across API variants)."""
    try:
        # Best effort recompute once
        try:
            doc.recompute()
        except Exception:
            pass

        # Prefer object named "Export"
        target = None
        try:
            obj = doc.getObject("Export")
            if obj and getattr(obj, "Shape", None):
                target = [obj]
        except Exception:
            target = None

        objs: List[Any] = []
        if target:
            objs = target
        else:
            # Aggregate visible objects with Shape
            try:
                for o in doc.Objects:
                    vo = getattr(o, "ViewObject", None)
                    vis = True
                    try:
                        vis = bool(getattr(vo, "Visibility", True))
                    except Exception:
                        vis = True
                    if vis and getattr(o, "Shape", None):
                        objs.append(o)
            except Exception:
                # Fallback: first object with Shape
                try:
                    for o in doc.Objects:
                        if getattr(o, "Shape", None):
                            objs.append(o)
                            break
                except Exception:
                    pass

        if not objs:
            return None

        # Combine min/max extents manually for robustness
        x_min = y_min = z_min = None
        x_max = y_max = z_max = None
        for o in objs:
            shp = getattr(o, "Shape", None)
            if not shp:
                continue
            try:
                b = shp.BoundBox
                xm, ym, zm = float(b.XMin), float(b.YMin), float(b.ZMin)
                xM, yM, zM = float(b.XMax), float(b.YMax), float(b.ZMax)
            except Exception:
                continue
            x_min = xm if x_min is None else min(x_min, xm)
            y_min = ym if y_min is None else min(y_min, ym)
            z_min = zm if z_min is None else min(z_min, zm)
            x_max = xM if x_max is None else max(x_max, xM)
            y_max = yM if y_max is None else max(y_max, yM)
            z_max = zM if z_max is None else max(z_max, zM)

        if None in (x_min, y_min, z_min, x_max, y_max, z_max):
            return None

        dx = float(x_max - x_min)
        dy = float(y_max - y_min)
        dz = float(z_max - z_min)
        return (dx, dy, dz)
    except Exception as e:
        log.warning(f"BBox compute failed: {e}")
        return None


def _set_view_for_thumbnail(view, preset):
    try:
        if not view:
            return False
        # Projection
        proj = preset.get("thumbnail", {}).get("projection", "orthographic")
        try:
            if proj == "orthographic":
                view.setCameraType("Orthographic")
            else:
                view.setCameraType("Perspective")
        except Exception:
            pass
        # View orientation
        vname = preset.get("thumbnail", {}).get("view", "isometric")
        try:
            if vname == "isometric":
                view.viewIsometric()
            elif vname == "front":
                view.viewFront()
            elif vname == "top":
                view.viewTop()
            elif vname == "right":
                view.viewRight()
        except Exception:
            pass
        # Fit to model
        try:
            view.fitAll()
        except Exception:
            pass
        # Draw style edges/shaded
        try:
            se = bool(preset.get("thumbnail", {}).get("showEdges", False))
            view.setDrawStyle("ShadedWithEdges" if se else "Shaded")
        except Exception:
            pass
        # Hide overlays best-effort
        try:
            view.showAxis(False)
        except Exception:
            pass
        try:
            # Some FreeCADs use showGrid()
            getattr(view, "showGrid", lambda *_: None)(False)
        except Exception:
            pass
        return True
    except Exception:
        return False


def _save_thumbnail(view, preset, out_path: Path) -> Optional[str]:
    size = preset.get("thumbnail", {}).get("size", [512, 512])
    w, h = int(size[0]), int(size[1])
    bg = preset.get("thumbnail", {}).get("background", "#ffffff")
    # Try native screenshot API first
    try:
        # Some versions: saveImage(path, width, height, "White")
        bg_mode = "White" if bg.lower() == "#ffffff" else "Current"
        view.saveImage(str(out_path), w, h, bg_mode)
        return None
    except Exception as e:
        # Fallback using pixmap
        try:
            pm = view.getPixmap(w, h)
            # Ensure background by filling image if possible
            from PySide6.QtGui import QImage, QPainter, QColor
        except Exception:
            try:
                from PySide2.QtGui import QImage, QPainter, QColor
            except Exception:
                return f"Thumbnail requires FreeCAD GUI ({e})"
        try:
            img = QImage(w, h, QImage.Format_ARGB32)
            # Fill background
            color = QColor(bg)
            p = QPainter(img)
            p.fillRect(0, 0, w, h, color)
            # Draw pixmap centered
            try:
                from PySide6.QtCore import QRect
            except Exception:
                from PySide2.QtCore import QRect
            p.drawPixmap(QRect(0, 0, w, h), pm)
            p.end()
            img.save(str(out_path), "PNG")
            return None
        except Exception as e2:
            return f"Thumbnail export failed: {e2}"


def _export_glb(
    doc, out_path: Path, preset: Dict[str, Any], part_name: str = "model"
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Export GLB mesh artifact. Best-effort across FreeCAD versions.
    Returns (error_msg, mesh_stats).
    
    Args:
        doc: FreeCAD document
        out_path: Output path for model file (base path; extensions vary)
        preset: Export preset configuration
        part_name: Name of the part for file naming (used in .obj/.stl filenames)
    """
    try:
        import FreeCAD
        import Mesh
        import MeshPart
    except Exception as e:
        return f"Mesh module unavailable: {e}", None

    # Gather objects to export
    try:
        export_obj = doc.getObject("Export")
        if export_obj and getattr(export_obj, "Shape", None):
            objs = [export_obj]
        else:
            objs = [
                o for o in doc.Objects
                if getattr(o, "Shape", None)
                and getattr(getattr(o, "ViewObject", None), "Visibility", True)
            ]
    except Exception as e:
        return f"No exportable objects: {e}", None

    if not objs:
        return "No visible shapes to export", None

    # Mesh settings from preset
    mesh_cfg = preset.get("mesh", {})
    lin_def = float(mesh_cfg.get("linearDeflection", 0.1))
    ang_def = float(mesh_cfg.get("angularDeflectionDeg", 15))
    relative = bool(mesh_cfg.get("relative", False))

    # Create mesh (tessellate shapes) using MeshPart.meshFromShape
    try:
        mesh_doc = FreeCAD.newDocument("__mesh_temp__", temp=True)
        for obj in objs:
            try:
                shp = obj.Shape
                mesh_obj = mesh_doc.addObject("Mesh::Feature", "MeshExport")
                mesh_obj.Mesh = MeshPart.meshFromShape(
                    Shape=shp,
                    LinearDeflection=lin_def,
                    AngularDeflection=ang_def,
                    Relative=relative,
                )
            except Exception as e_tess:
                log.debug(f"Tessellate failed for object {getattr(obj,'Name','?')}: {e_tess}")
                continue
        # Best-effort recompute
        try:
            mesh_doc.recompute()
        except Exception:
            pass
    except Exception as e:
        return f"Mesh tessellation failed: {e}", None

    # Compute stats
    stats = None
    try:
        total_tri = 0
        total_vert = 0
        for o in mesh_doc.Objects:
            if hasattr(o, "Mesh"):
                m = o.Mesh
                total_tri += m.CountFacets
                total_vert += m.CountPoints
        if total_tri > 0 or total_vert > 0:
            stats = {"triangles": total_tri, "vertices": total_vert}
    except Exception:
        pass

    # Export to GLB
    try:
        # Get mesh feature objects to export (Mesh::Feature)
        mesh_objs = [o for o in mesh_doc.Objects if hasattr(o, "Mesh")]
        if not mesh_objs:
            FreeCAD.closeDocument(mesh_doc.Name)
            return "No mesh objects to export", stats

        # Default: export as OBJ using Mesh.export on Mesh::Feature objects
        try:
            obj_path = out_path.with_suffix(".obj")
            stl_path = out_path.with_suffix(".stl")
            glb_path = out_path.with_suffix(".glb")
            # Clean old artifacts to avoid stale files (Windows-safe overwrite)
            for old in (obj_path, stl_path, glb_path):
                try:
                    if old.exists():
                        old.unlink()
                except Exception:
                    pass
            Mesh.export(mesh_objs, str(obj_path))
            FreeCAD.closeDocument(mesh_doc.Name)
            if obj_path.exists() and obj_path.stat().st_size > 0:
                # OBJ success; convert to STL for GitHub preview support
                try:
                    stl_err = obj_to_stl(obj_path, stl_path)
                    if stl_err:
                        log.debug(f"STL conversion failed: {stl_err}")
                    else:
                        log.debug(f"STL conversion succeeded: {stl_path}")
                except Exception as e_stl:
                    log.debug(f"STL conversion error: {e_stl}")
                # Return OBJ success regardless of STL conversion (STL is bonus)
                return None, stats
            else:
                raise Exception("OBJ export failed")
        except Exception as e_obj:
            log.debug(f"OBJ export failed: {e_obj}")

        # Secondary: try importGLTF (FreeCAD 0.21+) for GLB
        try:
            import importGLTF

            if not hasattr(importGLTF, 'export') or not callable(importGLTF.export):
                raise Exception("importGLTF.export not available")

            importGLTF.export(mesh_objs, str(out_path))

            if out_path.exists() and out_path.stat().st_size > 100:
                with open(out_path, 'rb') as f:
                    if f.read(4) != b'glTF':
                        out_path.unlink()
                        raise Exception("Invalid GLB header")

                # GLB success
                FreeCAD.closeDocument(mesh_doc.Name)
                return None, stats
            else:
                raise Exception("GLB file missing or too small")
        except Exception as e_glb:
            log.debug(f"GLB export failed: {e_glb}")
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass

        # Last resort: export STL
        try:
            stl_path = out_path.with_suffix(".stl")
            Mesh.export(mesh_objs, str(stl_path))
            FreeCAD.closeDocument(mesh_doc.Name)
            if stl_path.exists() and stl_path.stat().st_size > 0:
                # STL success; return warning to indicate fallback
                return "GLB export not available; exported STL instead", stats
            else:
                return "STL export failed", stats
        except Exception as e_stl:
            FreeCAD.closeDocument(mesh_doc.Name)
            return f"Mesh export failed: {e_stl}", stats

    except Exception as e:
        try:
            FreeCAD.closeDocument(mesh_doc.Name)
        except Exception:
            pass
        return f"GLB export error: {e}", stats


def export_active_document(repo_root: str) -> ExportResult:
    """
    Export previews for the active FreeCAD document.
    Returns ExportResult with file paths and any thumbnail error.
    """
    try:
        doc, view = _doc_and_view()
        if not doc:
            return ExportResult(
                ok=False,
                png_path=None,
                json_path=None,
                glb_path=None,
                rel_dir=None,
                message="No active document",
                thumbnail_error=None,
                glb_error=None,
                mesh_stats=None,
                warnings=[],
                preset_used={},
            )

        # Ensure saved
        file_name = getattr(doc, "FileName", "")
        if not file_name:
            return ExportResult(
                ok=False,
                png_path=None,
                json_path=None,
                glb_path=None,
                rel_dir=None,
                message="Document not saved",
                thumbnail_error=None,
                glb_error=None,
                mesh_stats=None,
                warnings=[],
                preset_used={},
            )

        repo_root_n = core_paths.normalize(repo_root)
        in_repo = core_paths.is_inside_repo(file_name, repo_root_n)
        if not in_repo:
            return ExportResult(
                ok=False,
                png_path=None,
                json_path=None,
                glb_path=None,
                rel_dir=None,
                message="Document saved outside selected repo",
                thumbnail_error=None,
                glb_error=None,
                mesh_stats=None,
                warnings=[],
                preset_used={},
            )

        # Repo-relative source path
        rel = core_paths.to_repo_rel(file_name, repo_root_n)
        if not rel:
            return ExportResult(
                ok=False,
                png_path=None,
                json_path=None,
                glb_path=None,
                rel_dir=None,
                message="Failed to determine repo-relative path",
                thumbnail_error=None,
                glb_error=None,
                mesh_stats=None,
                warnings=[],
                preset_used={},
            )

        # Load preset
        pr = load_preset(Path(repo_root_n))
        preset = pr.preset
        if pr.error:
            log.warning(pr.error)

        # Output dir
        rel_dir = to_preview_dir_rel(rel)
        out_dir = core_paths.safe_join_repo(repo_root_n, rel_dir)
        if not out_dir:
            return ExportResult(
                ok=False,
                png_path=None,
                json_path=None,
                glb_path=None,
                rel_dir=None,
                message="Cannot create output folder (invalid path)",
                thumbnail_error=None,
                glb_error=None,
                mesh_stats=None,
                warnings=[],
                preset_used=preset,
            )
        out_dir.mkdir(parents=True, exist_ok=True)

        # Extract part name from source path for use in file naming
        source_path = Path(rel)
        part_name = source_path.stem

        png_path = out_dir / f"{part_name}.png"
        json_path = out_dir / f"{part_name}.json"
        glb_path = out_dir / f"{part_name}.glb"

        warnings = []

        # Thumbnail (capture and restore original camera/view)
        thumb_err = None
        if view is not None:
            orig_cam = None
            orig_style = None
            try:
                orig_cam = view.getCamera()
            except Exception:
                orig_cam = None
            try:
                # getDrawStyle may not exist everywhere
                orig_style = getattr(view, "getDrawStyle", lambda: None)()
            except Exception:
                orig_style = None
            try:
                # Always apply deterministic view before capture
                _set_view_for_thumbnail(view, preset)
                thumb_err = _save_thumbnail(view, preset, png_path)
            finally:
                try:
                    if orig_cam:
                        view.setCamera(orig_cam)
                except Exception:
                    pass
                try:
                    if orig_style:
                        view.setDrawStyle(orig_style)
                except Exception:
                    pass
        else:
            thumb_err = "Thumbnail requires FreeCAD GUI"

        # GLB Export (Sprint 7)
        glb_err, mesh_stats = _export_glb(doc, glb_path, preset, part_name)
        
        # Determine which model file actually exists (prefer OBJ; STL as converted)
        # OBJ and GLB stay in the part folder
        # STL gets moved to the previews root folder
        model_file = None
        obj_path = glb_path.with_suffix(".obj")
        stl_path_in_part = glb_path.with_suffix(".stl")  # Where STL is generated initially
        
        # STL root path (where it will be placed)
        stl_root_rel = stl_root_path_rel(rel)
        stl_root_abs = core_paths.safe_join_repo(repo_root_n, stl_root_rel)
        
        if obj_path.exists() and obj_path.stat().st_size > 100:
            model_file = rel_dir + f"{part_name}.obj"
        elif glb_path.exists() and glb_path.stat().st_size > 100:
            model_file = rel_dir + f"{part_name}.glb"
        elif stl_path_in_part.exists() and stl_path_in_part.stat().st_size > 100:
            # If no OBJ or GLB, STL is the primary model (still point to root location)
            model_file = stl_root_rel
        
        # Also include STL in artifacts if it was generated (GitHub preview support)
        # STL is stored in the previews root
        model_artifacts = {}
        if model_file:
            model_artifacts["model"] = model_file
        
        # Move STL to root if it was generated in the part folder
        if stl_path_in_part.exists() and stl_path_in_part.stat().st_size > 100:
            try:
                if stl_root_abs:
                    stl_root_abs.parent.mkdir(parents=True, exist_ok=True)
                    # Replace any existing STL in the root (Windows-safe overwrite)
                    if stl_root_abs.exists():
                        stl_root_abs.unlink()
                    try:
                        stl_path_in_part.replace(stl_root_abs)
                    except Exception:
                        # Fallback to copy then delete source
                        shutil.copy2(stl_path_in_part, stl_root_abs)
                        stl_path_in_part.unlink(missing_ok=True)
                    model_artifacts["stl"] = stl_root_rel
                    log.debug(f"STL placed at root: {stl_root_rel}")
            except Exception as e:
                log.warning(f"Failed to move STL to root: {e}")
                model_artifacts["stl"] = rel_dir + f"{part_name}.stl"
            finally:
                # Ensure no stale STL remains in the part folder
                if stl_path_in_part.exists():
                    try:
                        stl_path_in_part.unlink()
                    except Exception:
                        pass
        
        # Move FCBak file to previews folder if it exists
        # FCBak files are FreeCAD's auto-backup files created alongside FCStd
        # This waits briefly for the file to appear since FreeCAD creates it asynchronously
        # Load maxBackups from existing JSON or use default
        max_backups = 3
        if json_path.exists():
            try:
                existing_data = json.loads(json_path.read_text(encoding="utf-8"))
                max_backups = existing_data.get("maxBackups", 3)
            except Exception:
                pass
        _move_fcbak_to_previews(Path(file_name), out_dir, part_name, max_backups)
        
        # Only warn if we had to fall back to STL or nothing was created
        if not model_file:
            if glb_err:
                warnings.append(glb_err)
                log.warning(f"Model export: {glb_err}")
            else:
                warnings.append("No 3D model file was created")
                log.warning("Model export failed - no output file")

        # Manifest JSON
        # Stats (best effort)
        bbox = _compute_bbox_mm(doc)
        precision = int(preset.get("stats", {}).get("precision", 2))
        if bbox:
            stats_bbox = [
                round(float(bbox[0]), precision),
                round(float(bbox[1]), precision),
                round(float(bbox[2]), precision),
            ]
        else:
            stats_bbox = [None, None, None]

        # Source hash
        src_hash = _sha256_file(Path(file_name))
        
        # Load existing maxBackups setting from previous JSON if it exists
        max_backups = 3  # Default value
        if json_path.exists():
            try:
                existing_data = json.loads(json_path.read_text(encoding="utf-8"))
                max_backups = existing_data.get("maxBackups", 3)
            except Exception:
                pass  # Use default if can't read

        manifest: Dict[str, Any] = {
            "schemaVersion": 1,
            "source": {
                "path": rel,
                "sha256": src_hash,
            },
            "generated": {
                "at": datetime.now(timezone.utc).isoformat(),
            },
            "maxBackups": max_backups,
            "freecadVersion": _freecad_version_string(),
            "exportPreset": preset,
            "stats": {
                "bboxMm": stats_bbox,
            },
            "artifacts": model_artifacts,
            "meshStats": mesh_stats,
        }
        if thumb_err:
            manifest["thumbnailError"] = thumb_err
        if warnings:
            manifest["generationWarnings"] = warnings

        # Write JSON with sorted keys and LF endings
        try:
            text = json.dumps(
                manifest,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            json_path.open("w", encoding="utf-8", newline="\n").write(text)
        except Exception as e:
            log.error(f"Failed to write preview.json: {e}")
            return ExportResult(
                ok=False,
                png_path=png_path if png_path.exists() else None,
                json_path=None,
                glb_path=glb_path if glb_path.exists() else None,
                rel_dir=rel_dir,
                message="Failed to write manifest",
                thumbnail_error=thumb_err,
                glb_error=glb_err,
                mesh_stats=mesh_stats,
                warnings=warnings,
                preset_used=preset,
            )

        log.info(
            f"Export finished: {rel_dir} "
            f"(png={'ok' if not thumb_err else 'err'}, "
            f"glb={'ok' if not glb_err else 'err'})"
        )

        return ExportResult(
            ok=True,
            png_path=png_path if png_path.exists() else None,
            json_path=json_path,
            glb_path=glb_path if glb_path.exists() else None,
            rel_dir=rel_dir,
            message=None,
            thumbnail_error=thumb_err,
            glb_error=glb_err,
            mesh_stats=mesh_stats,
            warnings=warnings,
            preset_used=preset,
        )
    except Exception as e:
        log.error(f"Export failed: {e}")
        return ExportResult(
            ok=False,
            png_path=None,
            json_path=None,
            glb_path=None,
            rel_dir=None,
            message="Export failed",
            thumbnail_error=None,
            glb_error=None,
            mesh_stats=None,
            warnings=[],
            preset_used={},
        )
