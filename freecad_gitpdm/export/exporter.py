# -*- coding: utf-8 -*-
"""
Deterministic preview exporter (PNG + JSON manifest).

Constraints:
- Only stdlib + FreeCAD shipped modules
- No shell=True; use subprocess via JobRunner only for git staging
- JSON sorted keys; LF endings; fixed precision for stats
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.core import paths as core_paths
from freecad_gitpdm.export.preset import load_preset
from freecad_gitpdm.export.mapper import to_preview_dir_rel, stl_root_path_rel
from freecad_gitpdm.export.view_helper import doc_and_view
from freecad_gitpdm.export.manifest import freecad_version_string, sha256_file
from freecad_gitpdm.export.thumbnail import set_view_for_thumbnail, save_thumbnail
from freecad_gitpdm.export.model_export import export_glb, compute_bbox_mm
from freecad_gitpdm.export.backup_manager import move_fcbak_to_previews


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


def export_active_document(repo_root: str) -> ExportResult:
    """
    Export previews for the active FreeCAD document.
    Returns ExportResult with file paths and any thumbnail error.
    """
    try:
        doc, view = doc_and_view()
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
                set_view_for_thumbnail(view, preset)
                thumb_err = save_thumbnail(view, preset, png_path)
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
        glb_err, mesh_stats = export_glb(doc, glb_path, preset, part_name)

        # Determine which model file actually exists (prefer OBJ; STL as converted)
        # OBJ and GLB stay in the part folder
        # STL gets moved to the previews root folder
        model_file = None
        obj_path = glb_path.with_suffix(".obj")
        stl_path_in_part = glb_path.with_suffix(
            ".stl"
        )  # Where STL is generated initially

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
        move_fcbak_to_previews(Path(file_name), out_dir, part_name, max_backups)

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
        bbox = compute_bbox_mm(doc)
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
        src_hash = sha256_file(Path(file_name))

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
            "freecadVersion": freecad_version_string(),
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
