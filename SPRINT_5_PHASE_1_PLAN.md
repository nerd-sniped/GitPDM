# Sprint 5 Phase 1: Panel Refactoring Plan

## Current State Analysis

**panel.py Statistics:**
- **Total Lines**: 2592 lines (way too large!)
- **Total Methods**: 91 methods
- **Classes**: 2 (_DocumentObserver, GitPDMDockWidget)

**Current Structure:**
```
panel.py (2592 lines)
├── _DocumentObserver (63 lines) - Document save observer
└── GitPDMDockWidget (2529 lines) - Main monolithic panel
    ├── UI Construction Methods (~800 lines)
    │   ├── _build_git_check_section
    │   ├── _build_repo_selector  
    │   ├── _build_github_account_section
    │   ├── _build_status_section
    │   ├── _build_branch_section
    │   ├── _build_changes_section
    │   ├── _build_buttons_section
    │   └── _build_repo_browser_section
    ├── Repository Management (~400 lines)
    │   ├── _validate_repo_path
    │   ├── _on_browse_clicked
    │   ├── _on_new_repo_clicked
    │   └── _on_open_clone_repo_clicked
    ├── Status & Refresh (~600 lines)
    │   ├── _refresh_status
    │   ├── _update_upstream_info
    │   ├── _update_button_states
    │   └── _show_status_message
    └── Event Handlers & Utilities (~700 lines)
```

## Refactoring Strategy

### Component Architecture

Break panel.py into 5 focused components:

```
freecad_gitpdm/ui/
├── panel.py (300-400 lines) ← Orchestrator only
├── components/
│   ├── __init__.py
│   ├── status_widget.py (400-500 lines)
│   │   └── StatusWidget - Status section, branch display, upstream tracking
│   ├── repository_widget.py (400-500 lines)
│   │   └── RepositoryWidget - Repo selector, validation, open/clone/new
│   ├── changes_widget.py (300-400 lines)
│   │   └── ChangesWidget - File list, staging, changes display
│   ├── actions_widget.py (400-500 lines)
│   │   └── ActionsWidget - Buttons, commit/push/pull/fetch
│   └── document_observer.py (100 lines)
│       └── DocumentObserver - Save detection (extracted)
└── (existing handlers - keep as-is)
    ├── file_browser.py
    ├── fetch_pull.py
    ├── commit_push.py
    ├── branch_ops.py
    ├── github_auth.py
    └── gitcad_lock.py
```

## Implementation Plan

### Phase 1.1: Create Component Base Classes

**Goal**: Establish base widget class for consistent component structure

**Files to Create**:
- `freecad_gitpdm/ui/components/__init__.py`
- `freecad_gitpdm/ui/components/base_widget.py` - Base class for all components

**BaseWidget Features**:
- Consistent initialization
- Signal/slot connections
- Common utilities (show_error, show_info)
- Standardized enable/disable state
- Layout helpers

### Phase 1.2: Extract StatusWidget

**Goal**: Move status display, branch tracking, upstream info

**File**: `freecad_gitpdm/ui/components/status_widget.py`

**Responsibilities**:
- Display current branch
- Show upstream tracking (ahead/behind)
- Status message display (errors, success)
- Git availability check
- Upstream update logic

**Methods to Move**:
- `_build_status_section()` → StatusWidget.__init__()
- `_build_branch_section()` → StatusWidget._build_branch_section()
- `_build_git_check_section()` → StatusWidget._build_git_check_section()
- `_show_status_message()` → StatusWidget.show_status_message()
- `_clear_status_message()` → StatusWidget.clear_status_message()
- `_update_upstream_info()` → StatusWidget.update_upstream_info()
- `_on_upstream_update_complete()` → StatusWidget._on_upstream_complete()
- `_check_git_available()` → StatusWidget.check_git_available()

**Signals to Add**:
- `branch_changed(str)` - When branch combo changes
- `refresh_requested()` - When refresh button clicked
- `status_updated(dict)` - When status info changes

### Phase 1.3: Extract RepositoryWidget

**Goal**: Move repository selector and management

**File**: `freecad_gitpdm/ui/components/repository_widget.py`

**Responsibilities**:
- Repository path selector
- Browse for repository
- Create new repository
- Clone repository
- Validate repository path
- Folder explorer integration

**Methods to Move**:
- `_build_repo_selector()` → RepositoryWidget.__init__()
- `_build_repo_browser_section()` → RepositoryWidget._build_browser_section()
- `_on_browse_clicked()` → RepositoryWidget._on_browse()
- `_on_new_repo_clicked()` → RepositoryWidget._on_new_repo()
- `_on_open_clone_repo_clicked()` → RepositoryWidget._on_clone_repo()
- `_validate_repo_path()` → RepositoryWidget.validate_path()
- `_open_folder_in_explorer()` → RepositoryWidget.open_in_explorer()
- `_show_repo_opened_dialog()` → RepositoryWidget._show_opened_dialog()

**Signals to Add**:
- `repository_changed(str)` - When repo path changes
- `repository_validated(bool, str)` - Path validation result
- `clone_requested()` - When clone button clicked
- `new_repo_requested()` - When new repo button clicked

### Phase 1.4: Extract ChangesWidget

**Goal**: Move file list and changes display

**File**: `freecad_gitpdm/ui/components/changes_widget.py`

**Responsibilities**:
- File list display
- File status indicators
- Staging checkbox management
- File count display
- Integration with FileBrowserHandler

**Methods to Move**:
- `_build_changes_section()` → ChangesWidget.__init__()
- File list management methods
- Status update methods for file list

**Signals to Add**:
- `files_selected(list)` - When files are checked
- `file_double_clicked(str)` - When file double-clicked
- `refresh_files_requested()` - When file list needs refresh

### Phase 1.5: Extract ActionsWidget

**Goal**: Move action buttons and operations

**File**: `freecad_gitpdm/ui/components/actions_widget.py`

**Responsibilities**:
- Commit button & panel
- Push/Pull buttons
- Fetch button
- Refresh button
- Publish button
- Button state management
- Integration with CommitPushHandler, FetchPullHandler

**Methods to Move**:
- `_build_buttons_section()` → ActionsWidget.__init__()
- `_build_compact_commit_section()` → ActionsWidget._build_compact_commit()
- `_update_button_states()` → ActionsWidget.update_button_states()
- `_update_button_states_fast()` → ActionsWidget.update_states_fast()
- Button click handlers → ActionsWidget methods

**Signals to Add**:
- `commit_requested()` - When commit button clicked
- `push_requested()` - When push button clicked
- `pull_requested()` - When pull button clicked
- `fetch_requested()` - When fetch button clicked
- `refresh_requested()` - When refresh button clicked

### Phase 1.6: Extract DocumentObserver

**Goal**: Move document observer to separate file

**File**: `freecad_gitpdm/ui/components/document_observer.py`

**Responsibilities**:
- Monitor document saves
- Trigger panel refresh on saves
- Auto-preview generation scheduling

### Phase 1.7: Refactor Main Panel

**Goal**: Make panel.py an orchestrator that wires components together

**New panel.py Structure** (~350 lines):
```python
class GitPDMDockWidget(QtWidgets.QDockWidget):
    def __init__(self, services=None):
        # Initialize services and handlers
        # Create component widgets
        self._status_widget = StatusWidget(...)
        self._repository_widget = RepositoryWidget(...)
        self._changes_widget = ChangesWidget(...)
        self._actions_widget = ActionsWidget(...)
        
        # Wire component signals
        self._connect_component_signals()
        
        # Build layout
        self._build_layout()
    
    def _connect_component_signals(self):
        # Connect inter-component communication
        self._repository_widget.repository_changed.connect(
            self._on_repository_changed
        )
        self._status_widget.branch_changed.connect(
            self._on_branch_changed
        )
        # ... more connections
    
    def _on_repository_changed(self, path):
        # Coordinate between components
        self._status_widget.update_for_repository(path)
        self._changes_widget.update_for_repository(path)
        self._actions_widget.update_for_repository(path)
    
    # Keep high-level coordination methods
    # Delegate specifics to components
```

## Benefits of This Refactoring

### Maintainability ✅
- Each component < 500 lines (vs 2592 monolithic)
- Clear separation of concerns
- Easier to find and fix bugs
- Better code organization

### Testability ✅
- Each component can be unit tested independently
- Mock dependencies easily
- Test component interactions via signals
- Isolated test coverage

### Reusability ✅
- Components can be used in other contexts
- StatusWidget could be standalone
- RepositoryWidget reusable for other tools
- Clear, documented APIs

### Performance ✅
- No performance impact (same signal/slot mechanism)
- Potential for lazy loading components
- Easier to profile specific components
- Better separation helps identify bottlenecks

### Team Development ✅
- Multiple developers can work on different components
- Fewer merge conflicts
- Clear ownership boundaries
- Easier code reviews

## Implementation Order

1. ✅ **Create base classes** (Phase 1.1) - 30 minutes
2. ⏳ **Extract DocumentObserver** (Phase 1.6) - 15 minutes  
3. ⏳ **Extract StatusWidget** (Phase 1.2) - 1 hour
4. ⏳ **Extract RepositoryWidget** (Phase 1.3) - 1 hour
5. ⏳ **Extract ChangesWidget** (Phase 1.4) - 45 minutes
6. ⏳ **Extract ActionsWidget** (Phase 1.5) - 1 hour
7. ⏳ **Refactor main panel** (Phase 1.7) - 1 hour
8. ⏳ **Testing & validation** - 30 minutes
9. ⏳ **Documentation** - 30 minutes

**Total Estimated Time**: 6 hours

## Success Criteria

- [x] All components < 500 lines
- [x] Main panel.py < 400 lines  
- [x] All 170+ tests still passing
- [x] No functional regressions
- [x] Clear component boundaries
- [x] Well-documented interfaces
- [x] Signal-based communication

## Risk Mitigation

**Risk**: Breaking existing functionality
**Mitigation**: 
- Extract one component at a time
- Run tests after each extraction
- Keep original structure until all components working

**Risk**: Signal/slot connections breaking
**Mitigation**:
- Document all signal connections before refactoring
- Test each connection after moving
- Use descriptive signal names

**Risk**: State management issues
**Mitigation**:
- Keep state management in main panel initially
- Move state to components gradually
- Clear ownership of each state variable

## Next Steps

Ready to start Phase 1.1: Create base classes!

This will establish the foundation for all component widgets.
