"""
Thumbnail generation for GitPDM previews.

Handles capturing PNG thumbnails from FreeCAD 3D views with configurable
camera settings, projections, and background colors.
"""

from pathlib import Path
from typing import Any, Dict, Optional


def set_view_for_thumbnail(view, preset: Dict[str, Any]) -> bool:
    """
    Configure view for thumbnail capture according to preset.

    Args:
        view: FreeCAD view object
        preset: Preset configuration dictionary

    Returns:
        True if view was configured successfully, False otherwise
    """
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


def save_thumbnail(view, preset: Dict[str, Any], out_path: Path) -> Optional[str]:
    """
    Save thumbnail PNG from FreeCAD view.

    Args:
        view: FreeCAD view object
        preset: Preset configuration dictionary
        out_path: Output path for PNG file

    Returns:
        None on success, error message string on failure
    """
    size = preset.get("thumbnail", {}).get("size", [512, 512])
    w, h = int(size[0]), int(size[1])
    bg = preset.get("thumbnail", {}).get("background", "transparent")

    # Handle transparent background
    if bg.lower() in ["transparent", "none", ""]:
        # Set view background to transparent before capturing
        orig_bg_color = None
        try:
            # Try to get and set background color
            try:
                orig_bg_color = view.getBackgroundColor()
            except Exception:
                pass

            # Set transparent/white background (FreeCAD doesn't support true transparency in viewport)
            # We'll make it transparent in the image processing
            try:
                view.setBackgroundColor(1.0, 1.0, 1.0, 0.0)  # RGBA with alpha=0
            except Exception:
                # Fallback: set to white, we'll process it
                try:
                    view.setBackgroundColor(1.0, 1.0, 1.0)
                except Exception:
                    pass

            pm = view.getPixmap(w, h)

            # Restore original background
            if orig_bg_color is not None:
                try:
                    if len(orig_bg_color) == 4:
                        view.setBackgroundColor(*orig_bg_color)
                    elif len(orig_bg_color) == 3:
                        view.setBackgroundColor(*orig_bg_color)
                except Exception:
                    pass

            try:
                from PySide6.QtGui import QImage, QColor
                from PySide6.QtCore import Qt
            except Exception:
                try:
                    from PySide6.QtGui import QImage, QColor
                    from PySide6.QtCore import Qt
                except Exception as e:
                    return f"Thumbnail requires FreeCAD GUI ({e})"

            try:
                # Create image with alpha channel
                img = QImage(w, h, QImage.Format_ARGB32)
                # Fill with transparent background
                img.fill(Qt.transparent)

                # Convert pixmap to image for processing
                pm_img = pm.toImage().convertToFormat(QImage.Format_ARGB32)

                # Make white/near-white background pixels transparent
                # This processes the image to remove white backgrounds
                width = pm_img.width()
                height = pm_img.height()

                for y in range(height):
                    for x in range(width):
                        pixel = pm_img.pixel(x, y)
                        color = QColor(pixel)
                        # If pixel is very close to white (all RGB > 250), make it transparent
                        if (
                            color.red() > 250
                            and color.green() > 250
                            and color.blue() > 250
                        ):
                            pm_img.setPixel(x, y, 0x00FFFFFF)  # Transparent white

                # Save the processed image
                pm_img.save(str(out_path), "PNG")
                return None
            except Exception as e:
                return f"Transparent thumbnail export failed: {e}"
        except Exception as e:
            return f"Thumbnail requires FreeCAD GUI ({e})"

    # Try native screenshot API first (for solid backgrounds)
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
                from PySide6.QtGui import QImage, QPainter, QColor
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
                from PySide6.QtCore import QRect
            p.drawPixmap(QRect(0, 0, w, h), pm)
            p.end()
            img.save(str(out_path), "PNG")
            return None
        except Exception as e2:
            return f"Thumbnail export failed: {e2}"
