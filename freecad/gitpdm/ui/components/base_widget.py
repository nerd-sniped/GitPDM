"""
Base Widget for UI Components
Sprint 5 Phase 1: Common functionality for all panel components

This base class provides consistent structure, utilities, and patterns
for all GitPDM UI components.
"""

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "PySide6 not found. FreeCAD installation may be incomplete."
        ) from e

from freecad.gitpdm.core import log


class BaseWidget(QtWidgets.QWidget):
    """
    Base class for GitPDM UI components.
    
    Provides:
    - Consistent initialization
    - Common signal patterns
    - Utility methods (show_error, show_info, etc.)
    - Layout helpers
    - Enable/disable state management
    
    All component widgets should inherit from this class.
    """
    
    # Common signals that components might emit
    error_occurred = QtCore.Signal(str, str)  # (title, message)
    info_message = QtCore.Signal(str, str)  # (title, message)
    busy_state_changed = QtCore.Signal(bool)  # True when busy
    
    def __init__(self, parent=None, git_client=None, job_runner=None):
        """
        Initialize base widget.
        
        Args:
            parent: Parent widget (usually the main panel)
            git_client: GitClient instance for git operations
            job_runner: JobRunner instance for background tasks
        """
        super().__init__(parent)
        self._parent_panel = parent
        self._git_client = git_client
        self._job_runner = job_runner
        self._is_enabled = True
        self._is_busy = False
        
        # Font sizes (consistent with original panel)
        self._meta_font_size = 9
        self._strong_font_size = 11
        
        log.debug(f"{self.__class__.__name__} initialized")
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def set_enabled_state(self, enabled: bool):
        """
        Enable or disable this component.
        
        Args:
            enabled: True to enable, False to disable
        """
        self._is_enabled = enabled
        self.setEnabled(enabled)
        log.debug(f"{self.__class__.__name__} enabled={enabled}")
    
    def set_busy_state(self, busy: bool, message: str = ""):
        """
        Set busy state for this component.
        
        Args:
            busy: True if component is busy
            message: Optional message describing what's happening
        """
        self._is_busy = busy
        self.busy_state_changed.emit(busy)
        
        if busy and message:
            log.debug(f"{self.__class__.__name__} busy: {message}")
        elif not busy:
            log.debug(f"{self.__class__.__name__} ready")
    
    def is_busy(self) -> bool:
        """Check if component is currently busy."""
        return self._is_busy
    
    # =========================================================================
    # Messaging Utilities
    # =========================================================================
    
    def show_error(self, title: str, message: str):
        """
        Show an error message to the user.
        
        Args:
            title: Error dialog title
            message: Error message
        """
        log.error(f"{title}: {message}")
        self.error_occurred.emit(title, message)
        
        # Show dialog if we have a parent
        if self._parent_panel:
            QtWidgets.QMessageBox.critical(
                self._parent_panel,
                title,
                message,
                QtWidgets.QMessageBox.Ok
            )
    
    def show_info(self, title: str, message: str):
        """
        Show an informational message to the user.
        
        Args:
            title: Info dialog title
            message: Info message
        """
        log.info(f"{title}: {message}")
        self.info_message.emit(title, message)
        
        # Show dialog if we have a parent
        if self._parent_panel:
            QtWidgets.QMessageBox.information(
                self._parent_panel,
                title,
                message,
                QtWidgets.QMessageBox.Ok
            )
    
    def show_warning(self, title: str, message: str):
        """
        Show a warning message to the user.
        
        Args:
            title: Warning dialog title
            message: Warning message
        """
        log.warning(f"{title}: {message}")
        
        # Show dialog if we have a parent
        if self._parent_panel:
            QtWidgets.QMessageBox.warning(
                self._parent_panel,
                title,
                message,
                QtWidgets.QMessageBox.Ok
            )
    
    def ask_confirmation(self, title: str, message: str) -> bool:
        """
        Ask user for confirmation.
        
        Args:
            title: Dialog title
            message: Confirmation message
            
        Returns:
            bool: True if user confirmed, False otherwise
        """
        if self._parent_panel:
            reply = QtWidgets.QMessageBox.question(
                self._parent_panel,
                title,
                message,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            return reply == QtWidgets.QMessageBox.Yes
        return False
    
    # =========================================================================
    # Layout Helpers
    # =========================================================================
    
    def create_group_box(self, title: str) -> QtWidgets.QGroupBox:
        """
        Create a styled group box.
        
        Args:
            title: Group box title
            
        Returns:
            QGroupBox: Configured group box
        """
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 0.5em;
                padding-top: 0.5em;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        return group
    
    def create_meta_label(self, text: str, color: str = "gray") -> QtWidgets.QLabel:
        """
        Create a small metadata label.
        
        Args:
            text: Label text
            color: Text color
            
        Returns:
            QLabel: Styled label
        """
        label = QtWidgets.QLabel(text)
        label.setStyleSheet(f"color: {color}; font-size: {self._meta_font_size}px;")
        return label
    
    def create_strong_label(self, text: str, color: str = "black") -> QtWidgets.QLabel:
        """
        Create an emphasized label.
        
        Args:
            text: Label text
            color: Text color
            
        Returns:
            QLabel: Styled label
        """
        label = QtWidgets.QLabel(text)
        label.setStyleSheet(
            f"font-weight: bold; color: {color}; font-size: {self._strong_font_size}px;"
        )
        return label
    
    def create_horizontal_separator(self) -> QtWidgets.QFrame:
        """
        Create a horizontal line separator.
        
        Returns:
            QFrame: Horizontal line
        """
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line
    
    # =========================================================================
    # Job Runner Utilities
    # =========================================================================
    
    def run_async(self, job_name: str, callable_func, on_success=None, on_error=None):
        """
        Run a function asynchronously using the job runner.
        
        Args:
            job_name: Unique job identifier
            callable_func: Function to run in background
            on_success: Callback for successful completion
            on_error: Callback for errors
        """
        if not self._job_runner:
            log.error(f"Cannot run async job '{job_name}': no job runner")
            return
        
        self.set_busy_state(True, f"Running {job_name}")
        
        def _on_complete(result):
            self.set_busy_state(False)
            if on_success:
                on_success(result)
        
        def _on_error(error):
            self.set_busy_state(False)
            log.error(f"Job '{job_name}' failed: {error}")
            if on_error:
                on_error(error)
            else:
                self.show_error("Operation Failed", str(error))
        
        self._job_runner.run_callable(
            job_name,
            callable_func,
            on_success=_on_complete,
            on_error=_on_error
        )
    
    # =========================================================================
    # Abstract Methods (Override in Subclasses)
    # =========================================================================
    
    def update_for_repository(self, repo_root: str):
        """
        Update component when repository changes.
        
        Override this in subclasses to handle repository changes.
        
        Args:
            repo_root: Path to new repository root (or None if no repo)
        """
        pass
    
    def refresh(self):
        """
        Refresh component data/display.
        
        Override this in subclasses to implement refresh logic.
        """
        pass
