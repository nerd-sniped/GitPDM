# -*- coding: utf-8 -*-
"""
3D model export for GitPDM previews.

Handles mesh generation and export to various formats (GLB, OBJ, STL)
with configurable tessellation parameters and bounding box calculation.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from freecad_gitpdm.core import log
from freecad_gitpdm.export.stl_converter import obj_to_stl


def compute_bbox_mm(doc) -> Optional[Tuple[float, float, float]]:
    """
    Compute bounding box size in mm (robust across API variants).
    
    Args:
        doc: FreeCAD document
    
    Returns:
        Tuple of (width, height, depth) in mm, or None if computation fails
    """
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


def export_glb(
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
    
    Returns:
        Tuple of (error_message, mesh_stats_dict). error_message is None on success.
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
