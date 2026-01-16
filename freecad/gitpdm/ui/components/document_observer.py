"""
Document Observer Component
Sprint 5 Phase 1: Monitors FreeCAD document saves

Extracted from monolithic panel.py to improve maintainability.
"""

# Qt compatibility layer
from PySide6 import QtCore

import os
from freecad.gitpdm.core import log


class DocumentObserver:
    """
    Observer to detect document saves and trigger panel refresh.
    
    This class monitors FreeCAD's document save events and notifies
    the panel when a document inside the current repository is saved,
    triggering automatic status refresh and preview generation.
    """

    def __init__(self, panel):
        """
        Initialize document observer.
        
        Args:
            panel: GitPDMDockWidget instance to notify on saves
        """
        self._panel = panel
        
        # Bind timer to the panel (Qt QObject) so it lives on the UI thread
        self._refresh_timer = QtCore.QTimer(panel)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(500)  # 500ms debounce
        self._refresh_timer.timeout.connect(self._do_refresh)
        
        log.debug("DocumentObserver created")

    def slotFinishSaveDocument(self, doc, filename):
        """
        Called after a document is saved by FreeCAD.
        
        This is a FreeCAD callback method that gets invoked when any
        document finishes saving. We check if it's in our repo and
        trigger appropriate refreshes.
        
        Args:
            doc: FreeCAD document object
            filename: Path to saved file
        """
        log.info(f"Document saved: {filename}")

        if not self._panel._current_repo_root:
            log.debug("No repo configured, skipping refresh")
            return

        try:
            filename = os.path.normpath(filename)
            repo_root = os.path.normpath(self._panel._current_repo_root)

            log.debug(f"Checking if {filename} is in {repo_root}")

            # Check if file is in repository
            # Note: This only triggers for .FCStd files. For other file types,
            # users need to click Refresh button to see changes.
            if filename.startswith(repo_root):
                log.info(f"Document saved in repo, scheduling refresh")

                # Reset working directory to repo to ensure next Save As defaults correctly
                self._panel._set_freecad_working_directory(repo_root)

                # Stop/start the timer on its owning thread to avoid
                # cross-thread timer operations (Qt enforces thread affinity)
                try:
                    QtCore.QMetaObject.invokeMethod(
                        self._refresh_timer,
                        "stop",
                        QtCore.Qt.QueuedConnection,
                    )
                    QtCore.QMetaObject.invokeMethod(
                        self._refresh_timer,
                        "start",
                        QtCore.Qt.QueuedConnection,
                    )
                except Exception as e:
                    # Fallback: best-effort direct calls
                    log.debug(f"Queued timer restart failed, using direct: {e}")
                    try:
                        self._refresh_timer.stop()
                        self._refresh_timer.start()
                    except Exception as e2:
                        log.error(f"Failed to restart refresh timer: {e2}")
                
                # Also schedule automatic preview generation for saved FCStd
                self._panel._schedule_auto_preview_generation(filename)
            else:
                log.debug(f"Document outside repo, no refresh")
                
        except Exception as e:
            log.error(f"Error in save handler: {e}")

    def _do_refresh(self):
        """
        Execute the actual panel refresh after debounce timer expires.
        
        This is called 500ms after the last save event to avoid
        excessive refreshes during rapid saves.
        """
        try:
            log.debug("Executing deferred panel refresh after document save")
            if hasattr(self._panel, '_refresh_status_views'):
                self._panel._refresh_status_views(self._panel._current_repo_root)
            else:
                log.warning("Panel does not have _refresh_status_views method")
        except Exception as e:
            log.error(f"Error refreshing panel after save: {e}")
