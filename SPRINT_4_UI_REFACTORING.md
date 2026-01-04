# Sprint 4: UI Refactoring & Polish

**Duration:** 5-7 days  
**Goal:** Refactor monolithic UI components, improve user experience, and create a cohesive interface

---

## Overview

The GitPDM UI has grown organically, resulting in a 2592-line `panel.py` file that violates single responsibility principle. This sprint breaks it into focused, maintainable components and polishes the user experience.

## Objectives

✅ Refactor `panel.py` (2592 lines → <500 lines)  
✅ Create dedicated UI components for each feature  
✅ Unify GitCAD/GitPDM interfaces  
✅ Improve visual consistency  
✅ Add status indicators and feedback  
✅ Polish error handling and messaging

---

## Task Breakdown

### Task 4.1: Analyze UI Architecture
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Analyze `panel.py` to understand component boundaries:

**Current Structure:**
```
panel.py (2592 lines)
├── GitPDMDockWidget - Main panel class
├── _DocumentObserver - Save handler
├── File browser logic
├── Git operations (fetch, pull, push, commit)
├── GitHub authentication
├── Branch operations
├── Lock management
├── Export/publish logic
└── Settings management
```

**Target Component Structure:**
```
ui/
├── panel.py (<500 lines)          # Main panel orchestration
├── components/
│   ├── file_tree.py               # File browser widget
│   ├── status_bar.py              # Repository status
│   ├── commit_panel.py            # Commit UI
│   ├── branch_selector.py         # Branch dropdown
│   ├── lock_panel.py              # Lock status & controls
│   ├── export_panel.py            # Export options
│   └── toolbar.py                 # Action buttons
├── dialogs/
│   ├── commit_dialog.py
│   ├── settings_dialog.py
│   ├── lock_dialog.py
│   └── export_dialog.py
└── handlers/ (already exists)
    ├── github_auth.py
    ├── fetch_pull.py
    ├── commit_push.py
    └── branch_ops.py
```

**Deliverables:**
- [ ] Component responsibility matrix
- [ ] Dependency graph
- [ ] Refactoring plan

**Acceptance Criteria:**
- Clear component boundaries defined
- No circular dependencies
- Team agrees on architecture

---

### Task 4.2: Create UI Component Framework
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Create base classes and patterns for UI components:

```python
# freecad_gitpdm/ui/components/base.py

from PySide6 import QtWidgets, QtCore
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path

class PanelComponent(QtWidgets.QWidget):
    """Base class for panel components."""
    
    # Signals
    repo_changed = QtCore.Signal(Path)  # Emitted when repo changes
    refresh_requested = QtCore.Signal()  # Emitted when refresh needed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo_root: Optional[Path] = None
        self._setup_ui()
        self._connect_signals()
        
    @abstractmethod
    def _setup_ui(self):
        """Setup the component UI."""
        pass
        
    def _connect_signals(self):
        """Connect internal signals."""
        pass
        
    def set_repository(self, repo_root: Optional[Path]):
        """Update the repository context."""
        self._repo_root = repo_root
        self._on_repo_changed()
        
    def _on_repo_changed(self):
        """Called when repository changes. Override in subclass."""
        pass
        
    def refresh(self):
        """Refresh component state. Override in subclass."""
        pass
```

**Deliverables:**
- [ ] `components/base.py` with PanelComponent base class
- [ ] Signal/slot architecture
- [ ] Layout helpers
- [ ] Style utilities

**Acceptance Criteria:**
- Base class is reusable
- Signal-based communication
- Consistent patterns

---

### Task 4.3: Extract File Browser Component
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Extract file browser from `panel.py` into dedicated component:

**Current:** 300+ lines scattered in `panel.py`  
**Target:** `components/file_tree.py` (200-250 lines)

```python
# freecad_gitpdm/ui/components/file_tree.py

from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui
from .base import PanelComponent
from freecad_gitpdm.git.client import GitClient

class FileTreeWidget(PanelComponent):
    """File browser component for repository files."""
    
    # Signals
    file_selected = QtCore.Signal(Path)  # File clicked
    file_double_clicked = QtCore.Signal(Path)  # File double-clicked
    files_staged = QtCore.Signal(list)  # Files staged for commit
    
    def __init__(self, parent=None):
        self._git_client = GitClient()
        self._file_status = {}  # path -> status (modified, staged, etc.)
        super().__init__(parent)
        
    def _setup_ui(self):
        """Setup tree view."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Search bar
        self._search_bar = QtWidgets.QLineEdit()
        self._search_bar.setPlaceholderText("Search files...")
        layout.addWidget(self._search_bar)
        
        # Tree view
        self._tree = QtWidgets.QTreeView()
        self._tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        layout.addWidget(self._tree)
        
        # Model
        self._model = QtWidgets.QFileSystemModel()
        self._model.setReadOnly(True)
        self._tree.setModel(self._model)
        
    def _connect_signals(self):
        """Connect signals."""
        self._tree.clicked.connect(self._on_file_clicked)
        self._tree.doubleClicked.connect(self._on_file_double_clicked)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._search_bar.textChanged.connect(self._on_search_changed)
        
    def _on_repo_changed(self):
        """Update file browser when repo changes."""
        if self._repo_root:
            self._model.setRootPath(str(self._repo_root))
            self._tree.setRootIndex(self._model.index(str(self._repo_root)))
            self._refresh_file_status()
            
    def refresh(self):
        """Refresh file status (modified, staged, etc.)."""
        self._refresh_file_status()
        self._update_file_decorations()
        
    def _refresh_file_status(self):
        """Query git for file status."""
        if not self._repo_root:
            return
            
        result = self._git_client.run_command(
            self._repo_root,
            ["status", "--porcelain"]
        )
        
        if result.ok:
            self._file_status = self._parse_git_status(result.value)
            
    def _update_file_decorations(self):
        """Update file icons/colors based on status."""
        # Add color coding for modified/staged/untracked files
        pass
        
    def _show_context_menu(self, position):
        """Show context menu for file operations."""
        menu = QtWidgets.QMenu()
        
        index = self._tree.indexAt(position)
        if not index.isValid():
            return
            
        file_path = Path(self._model.filePath(index))
        
        # Add context menu actions
        if file_path.suffix.lower() == '.fcstd':
            menu.addAction("Open in FreeCAD", lambda: self._open_fcstd(file_path))
            menu.addAction("Export to Uncompressed", lambda: self._export_fcstd(file_path))
            menu.addSeparator()
            menu.addAction("Lock File", lambda: self._lock_file(file_path))
            
        menu.addAction("Stage File", lambda: self._stage_file(file_path))
        menu.addAction("Unstage File", lambda: self._unstage_file(file_path))
        menu.addSeparator()
        menu.addAction("View Diff", lambda: self._view_diff(file_path))
        
        menu.exec_(self._tree.viewport().mapToGlobal(position))
```

**Deliverables:**
- [ ] `file_tree.py` with FileTreeWidget
- [ ] Git status integration
- [ ] Context menus
- [ ] File decorations (icons for modified/staged)
- [ ] Search functionality

**Acceptance Criteria:**
- Shows repository files
- Git status indicators
- Context menu works
- Emits selection signals

---

### Task 4.4: Extract Status Bar Component
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Create status bar showing repo state:

```python
# freecad_gitpdm/ui/components/status_bar.py

from .base import PanelComponent

class StatusBar(PanelComponent):
    """Status bar showing repository information."""
    
    def _setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        
        # Branch label
        self._branch_label = QtWidgets.QLabel("No branch")
        layout.addWidget(self._branch_label)
        
        # Lock status
        self._lock_icon = QtWidgets.QLabel()
        layout.addWidget(self._lock_icon)
        
        # Sync status
        self._sync_label = QtWidgets.QLabel("Up to date")
        layout.addWidget(self._sync_label)
        
        layout.addStretch()
        
    def _on_repo_changed(self):
        """Update status when repo changes."""
        self._update_branch()
        self._update_locks()
        self._update_sync_status()
        
    def set_branch(self, branch_name: str):
        """Update branch display."""
        self._branch_label.setText(f"Branch: {branch_name}")
        
    def set_lock_count(self, count: int):
        """Update lock count."""
        if count > 0:
            self._lock_icon.setText(f"🔒 {count} locked files")
        else:
            self._lock_icon.setText("")
            
    def set_sync_status(self, behind: int, ahead: int):
        """Update sync status."""
        if behind == 0 and ahead == 0:
            self._sync_label.setText("✓ Up to date")
        elif behind > 0 and ahead == 0:
            self._sync_label.setText(f"↓ {behind} commits behind")
        elif behind == 0 and ahead > 0:
            self._sync_label.setText(f"↑ {ahead} commits ahead")
        else:
            self._sync_label.setText(f"↕ {ahead} ahead, {behind} behind")
```

**Deliverables:**
- [ ] `status_bar.py` with StatusBar component
- [ ] Branch display
- [ ] Lock count
- [ ] Sync status

**Acceptance Criteria:**
- Shows current branch
- Shows lock status
- Shows sync status
- Updates in real-time

---

### Task 4.5: Extract Lock Panel Component
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P1

**Description:**
Create dedicated lock management panel:

```python
# freecad_gitpdm/ui/components/lock_panel.py

from .base import PanelComponent
from freecad_gitpdm.core.lock_manager import LockManager

class LockPanel(PanelComponent):
    """Panel showing locked files and lock controls."""
    
    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header
        header = QtWidgets.QLabel("Locked Files")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
        
        # Lock list
        self._lock_list = QtWidgets.QListWidget()
        layout.addWidget(self._lock_list)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self._lock_btn = QtWidgets.QPushButton("Lock Selected")
        self._unlock_btn = QtWidgets.QPushButton("Unlock Selected")
        self._refresh_btn = QtWidgets.QPushButton("Refresh")
        btn_layout.addWidget(self._lock_btn)
        btn_layout.addWidget(self._unlock_btn)
        btn_layout.addWidget(self._refresh_btn)
        layout.addLayout(btn_layout)
        
    def _connect_signals(self):
        self._lock_btn.clicked.connect(self._on_lock)
        self._unlock_btn.clicked.connect(self._on_unlock)
        self._refresh_btn.clicked.connect(self.refresh)
        
    def refresh(self):
        """Refresh lock list."""
        if not self._repo_root:
            return
            
        lock_manager = LockManager(self._repo_root)
        result = lock_manager.get_locks()
        
        if result.ok:
            self._lock_list.clear()
            locks = result.value
            
            for lock in locks:
                item = QtWidgets.QListWidgetItem(
                    f"🔒 {lock.fcstd_path} (locked by {lock.owner})"
                )
                self._lock_list.addItem(item)
```

**Deliverables:**
- [ ] `lock_panel.py` with LockPanel component
- [ ] Lock list display
- [ ] Lock/unlock buttons
- [ ] Owner information
- [ ] Refresh functionality

**Acceptance Criteria:**
- Shows all locked files
- Can lock/unlock from panel
- Shows lock owner
- Updates automatically

---

### Task 4.6: Refactor Main Panel
**Owner:** [Assign]  
**Estimate:** 2 days  
**Priority:** P0 (Blocking)

**Description:**
Refactor `panel.py` to orchestrate components:

**Target Structure (500 lines):**
```python
# freecad_gitpdm/ui/panel.py

from PySide6 import QtWidgets, QtCore
from pathlib import Path
from .components.file_tree import FileTreeWidget
from .components.status_bar import StatusBar
from .components.lock_panel import LockPanel
from .components.commit_panel import CommitPanel
from .handlers.github_auth import GitHubAuthHandler
from .handlers.fetch_pull import FetchPullHandler
from .handlers.commit_push import CommitPushHandler

class GitPDMDockWidget(QtWidgets.QDockWidget):
    """Main GitPDM dock panel."""
    
    def __init__(self, services=None):
        super().__init__("Git PDM")
        self._services = services
        self._repo_root = None
        self._setup_ui()
        self._setup_handlers()
        self._connect_signals()
        
    def _setup_ui(self):
        """Setup UI with components."""
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        
        # Toolbar
        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)
        
        # Splitter for main content
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        
        # File browser (top)
        self._file_tree = FileTreeWidget()
        splitter.addWidget(self._file_tree)
        
        # Tabs for different panels (bottom)
        self._tabs = QtWidgets.QTabWidget()
        
        # Commit tab
        self._commit_panel = CommitPanel()
        self._tabs.addTab(self._commit_panel, "Commit")
        
        # Locks tab
        self._lock_panel = LockPanel()
        self._tabs.addTab(self._lock_panel, "Locks")
        
        # Settings tab
        self._settings_panel = SettingsPanel()
        self._tabs.addTab(self._settings_panel, "Settings")
        
        splitter.addWidget(self._tabs)
        layout.addWidget(splitter)
        
        # Status bar (bottom)
        self._status_bar = StatusBar()
        layout.addWidget(self._status_bar)
        
        self.setWidget(central)
        
    def _setup_handlers(self):
        """Setup operation handlers."""
        self._github_auth = GitHubAuthHandler(self, self._services)
        self._fetch_pull = FetchPullHandler(self, self._services)
        self._commit_push = CommitPushHandler(self, self._services)
        
    def _connect_signals(self):
        """Connect component signals."""
        self._file_tree.file_double_clicked.connect(self._on_file_open)
        self._commit_panel.commit_requested.connect(self._on_commit)
        self._lock_panel.lock_requested.connect(self._on_lock_file)
        
    def set_repository(self, repo_path: str):
        """Change active repository."""
        self._repo_root = Path(repo_path)
        
        # Propagate to all components
        self._file_tree.set_repository(self._repo_root)
        self._commit_panel.set_repository(self._repo_root)
        self._lock_panel.set_repository(self._repo_root)
        self._status_bar.set_repository(self._repo_root)
        
        self._refresh_all()
        
    def _refresh_all(self):
        """Refresh all components."""
        self._file_tree.refresh()
        self._commit_panel.refresh()
        self._lock_panel.refresh()
        self._status_bar.refresh()
        
    def _create_toolbar(self):
        """Create main toolbar."""
        toolbar = QtWidgets.QToolBar()
        
        # Actions
        toolbar.addAction("Open Repo", self._on_open_repo)
        toolbar.addSeparator()
        toolbar.addAction("Fetch", self._on_fetch)
        toolbar.addAction("Pull", self._on_pull)
        toolbar.addAction("Push", self._on_push)
        toolbar.addSeparator()
        toolbar.addAction("Refresh", self._refresh_all)
        
        return toolbar
```

**Deliverables:**
- [ ] Refactored `panel.py` (<500 lines)
- [ ] Component composition
- [ ] Signal routing
- [ ] Toolbar integration
- [ ] Menu integration

**Acceptance Criteria:**
- Panel.py < 500 lines
- All components integrated
- All features working
- No regressions

---

### Task 4.7: Unify Visual Design
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P1

**Description:**
Create consistent visual design across all UI:

**Design System:**
```python
# freecad_gitpdm/ui/styles.py

# Color scheme
COLORS = {
    "primary": "#0078D4",      # Actions, links
    "success": "#107C10",      # Success states
    "warning": "#FFC83D",      # Warnings
    "error": "#D13438",        # Errors
    "modified": "#FFA500",     # Modified files
    "staged": "#00AA00",       # Staged files
    "locked": "#FF6B6B",       # Locked files
    "background": "#FFFFFF",   # Background
    "text": "#000000",         # Text
}

# Icon set
ICONS = {
    "lock": "🔒",
    "unlock": "🔓",
    "modified": "●",
    "staged": "✓",
    "branch": "⎇",
    "sync": "⟳",
    "up_to_date": "✓",
}

def get_stylesheet():
    """Get global stylesheet."""
    return f"""
    QPushButton {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 3px;
    }}
    
    QPushButton:hover {{
        background-color: #006CC1;
    }}
    
    QPushButton:pressed {{
        background-color: #005A9E;
    }}
    
    QListWidget::item:selected {{
        background-color: {COLORS['primary']};
    }}
    
    /* More styles... */
    """
```

**Deliverables:**
- [ ] Style guide document
- [ ] Color scheme
- [ ] Icon set
- [ ] Global stylesheet
- [ ] Apply to all components

**Acceptance Criteria:**
- Consistent colors across UI
- Consistent button styles
- Consistent spacing
- Professional appearance

---

### Task 4.8: Improve Error Handling & Feedback
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P1

**Description:**
Improve error messages and user feedback:

**Improvements:**
1. **Progress Indicators** - Show progress for long operations
2. **Better Error Messages** - Clear, actionable error text
3. **Toast Notifications** - Non-blocking notifications
4. **Loading States** - Indicate when operations are in progress
5. **Validation** - Validate inputs before actions

```python
# freecad_gitpdm/ui/feedback.py

from PySide6 import QtWidgets, QtCore

class ToastNotification(QtWidgets.QWidget):
    """Non-blocking notification widget."""
    
    def __init__(self, message: str, type: str = "info", parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.ToolTip)
        
        layout = QtWidgets.QHBoxLayout(self)
        
        # Icon
        icon_map = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
        }
        icon = QtWidgets.QLabel(icon_map.get(type, "ℹ"))
        layout.addWidget(icon)
        
        # Message
        label = QtWidgets.QLabel(message)
        layout.addWidget(label)
        
        # Style based on type
        color_map = {
            "info": "#0078D4",
            "success": "#107C10",
            "warning": "#FFC83D",
            "error": "#D13438",
        }
        self.setStyleSheet(f"""
            background-color: {color_map.get(type, '#0078D4')};
            color: white;
            border-radius: 4px;
            padding: 8px;
        """)
        
        # Auto-hide timer
        QtCore.QTimer.singleShot(3000, self.hide)
        
    @staticmethod
    def show_toast(message: str, type: str = "info", parent=None):
        """Show a toast notification."""
        toast = ToastNotification(message, type, parent)
        toast.show()
        return toast


class ProgressDialog(QtWidgets.QDialog):
    """Progress dialog for long operations."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        self._label = QtWidgets.QLabel("Processing...")
        layout.addWidget(self._label)
        
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self._progress)
        
        self._cancel_btn = QtWidgets.QPushButton("Cancel")
        layout.addWidget(self._cancel_btn)
        
    def set_message(self, message: str):
        """Update progress message."""
        self._label.setText(message)
```

**Deliverables:**
- [ ] Toast notification system
- [ ] Progress dialogs
- [ ] Loading indicators
- [ ] Improved error dialogs
- [ ] Input validation

**Acceptance Criteria:**
- Clear feedback for all operations
- Non-blocking notifications
- Progress shown for long ops
- Errors are actionable

---

### Task 4.9: Accessibility Improvements
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P2

**Description:**
Improve accessibility:
- Keyboard shortcuts
- Tab order
- Screen reader labels
- High contrast mode support

**Deliverables:**
- [ ] Keyboard shortcut guide
- [ ] Proper tab order
- [ ] ARIA labels
- [ ] High contrast theme

---

### Task 4.10: Testing & Polish
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Comprehensive UI testing:

**Test Scenarios:**
- Open repository
- Browse files
- Commit changes
- Lock/unlock files
- Fetch/pull/push
- Branch operations
- Settings changes

**Deliverables:**
- [ ] UI test suite
- [ ] Manual test checklist
- [ ] Bug fixes
- [ ] Performance optimization

**Acceptance Criteria:**
- All workflows tested
- No UI regressions
- Smooth performance
- No crashes

---

## Definition of Done (Sprint 4)

- [x] Panel.py < 500 lines
- [x] Components properly separated
- [x] Consistent visual design
- [x] Improved error handling
- [x] All tests passing
- [x] Documentation updated
- [x] User feedback incorporated

---

## Success Metrics

- ✅ Panel.py reduced from 2592 → <500 lines (80% reduction)
- ✅ Component count increased (better separation)
- ✅ User satisfaction improved
- ✅ UI response time <100ms
- ✅ Zero UI crashes

---

**Next Sprint:** Sprint 5 - Cleanup & Documentation
