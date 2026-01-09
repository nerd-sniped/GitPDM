# GitPDM Actions Layer - Phase 1

## Overview

The actions layer separates **business logic** from **UI code**, making GitPDM easier to:
- Understand (each action is a single-purpose function)
- Test (no Qt/FreeCAD dependencies)
- Modify (change git → script backend without touching UI)
- Minimize (delete unwanted actions without breaking UI)

## Architecture

```
┌─────────────────────────────────────────┐
│  UI Layer (panel.py, dialogs, etc.)    │
│  - Gathers inputs                       │
│  - Calls actions                        │
│  - Displays results                     │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Actions Layer (freecad/gitpdm/actions) │
│  - Pure functions                       │
│  - ActionContext → ActionResult         │
│  - No Qt/UI imports                     │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Backend (GitClient or ScriptRunner)    │
│  - Actual git execution                 │
│  - Swappable via protocol               │
└─────────────────────────────────────────┘
```

## Key Components

### 1. `ActionContext` (types.py)
Contains everything an action needs to run:
- `git`: Backend that runs git commands
- `settings`: Settings provider (optional)
- `repo_root`: Repository path
- `remote_name`: Remote name (e.g., "origin")

### 2. `ActionResult` (types.py)
Standard return type for all actions:
- `ok`: True if successful
- `message`: Human-readable message
- `details`: Dictionary with extra data
- `error_code`: Machine-readable error identifier

### 3. `GitBackend` Protocol (types.py)
Interface that backends must implement:
- `is_git_available()`, `get_repo_root()`, etc.
- Currently implemented by `GitClientBackend`
- Future: `ScriptBackend` for bash scripts

## Available Actions

### Repository Actions (`repository.py`)
- `validate_repo(ctx, path)` - Check if path is a valid git repo
- `init_repo(ctx, path)` - Initialize new repository
- `clone_repo(ctx, url, dest_path)` - Clone from remote

### Status Actions (`status.py`)
- `refresh_status(ctx)` - Get branch, upstream, ahead/behind
- `get_file_changes(ctx)` - Get list of modified/staged files

### Commit/Push Actions (`commit_push.py`)
- `commit_changes(ctx, message, stage_all)` - Create commit
- `push_changes(ctx, force)` - Push to remote

### Fetch/Pull Actions (`fetch_pull.py`)
- `fetch_from_remote(ctx)` - Fetch from remote
- `pull_from_remote(ctx)` - Pull with fast-forward only

### Remote Actions (`remote.py`)
- `add_remote(ctx, name, url)` - Add a remote
- `check_remote_exists(ctx, name)` - Check if remote exists

## Usage Pattern

### Step 1: Create Context (Once)
```python
from freecad.gitpdm.actions import create_action_context

# In your UI __init__ or setup:
self._action_ctx = create_action_context(
    git_client=self._git_client,  # Reuse existing client
    settings=settings,             # Settings module
    repo_root="/path/to/repo",     # Current repo
    remote_name="origin"           # Remote name
)
```

### Step 2: Call Actions (In Button Handlers)
```python
from freecad.gitpdm.actions import commit_changes, push_changes

def on_commit_button_clicked(self):
    # 1. Gather inputs
    message = self.commit_message_field.text()
    stage_all = self.stage_all_checkbox.isChecked()
    
    # 2. Call action
    result = commit_changes(self._action_ctx, message, stage_all)
    
    # 3. Display result
    if result.ok:
        self.show_success(result.message)
    else:
        self.show_error(result.message)
```

### Step 3: Update Context (When Repo Changes)
```python
# When user selects different repository:
self._action_ctx.repo_root = new_repo_path
```

## Benefits for "Super Easy to Work On"

### ✅ Predictable Pattern
Every button handler becomes 3 lines:
1. Gather inputs
2. Call action
3. Display result

### ✅ Single Responsibility
Each action does ONE thing:
- `commit_changes()` just commits
- `push_changes()` just pushes
- Chain them in UI if you want both

### ✅ Easy to Delete
Want to remove "clone" feature?
1. Delete `clone_repo()` from `repository.py`
2. Remove button from UI
3. Done! No hidden dependencies

### ✅ Easy to Test
```python
# Test without FreeCAD/Qt:
ctx = ActionContext(git=FakeBackend(), repo_root="/tmp/test")
result = commit_changes(ctx, "test commit")
assert result.ok
```

### ✅ Easy to Swap Backend
```python
# Today: Python git
ctx = ActionContext(git=GitClientBackend())

# Tomorrow: Bash scripts
ctx = ActionContext(git=ScriptBackend())

# UI code stays the same!
```

## Next Steps (Phase 2)

1. **Create ScriptBackend**
   - Implement `GitBackend` protocol
   - Runs scripts from `scripts/` directory
   - Parses JSON output

2. **Add Script Stubs**
   - `scripts/commit.sh`, `scripts/push.sh`, etc.
   - Simple interface: args in, JSON out

3. **Configuration Switch**
   - Toggle between GitClient and Scripts
   - No UI changes needed

## Error Handling

Actions use consistent error codes:
- `no_repo` - No repository path
- `git_not_found` - Git not available
- `no_message` - Missing commit message
- `auth_failed` - Authentication failed
- `push_rejected_behind` - Behind remote
- And more...

UI can handle errors specifically:
```python
result = push_changes(ctx)
if not result.ok:
    if result.error_code == "no_remote":
        # Offer to add remote
        self.show_add_remote_dialog()
    elif result.error_code == "push_rejected_behind":
        # Suggest pulling first
        self.show_pull_suggestion()
    else:
        # Generic error
        self.show_error(result.message)
```

## File Organization

```
freecad/gitpdm/actions/
├── __init__.py           # Public API exports
├── types.py              # ActionContext, ActionResult, protocols
├── backend.py            # GitClientBackend adapter
├── helpers.py            # create_action_context() helper
├── repository.py         # validate, init, clone
├── status.py             # refresh status, get changes
├── commit_push.py        # commit, push
├── fetch_pull.py         # fetch, pull
├── remote.py             # add remote, check remote
├── EXAMPLE_USAGE.py      # Code examples
└── README.md             # This file
```

## Migration Guide (For Existing Code)

### Before (Old Way)
```python
# In panel.py button handler:
def on_commit_clicked(self):
    repo_root = self._current_repo_root
    message = self.commit_message.toPlainText()
    
    # Lots of git logic here...
    if not self._git_client.is_git_available():
        self.show_error("Git not available")
        return
    
    result = self._git_client.commit(repo_root, message)
    if not result.ok:
        if "nothing to commit" in result.stderr:
            self.show_info("No changes")
        else:
            self.show_error(f"Failed: {result.stderr}")
    else:
        self.show_success("Committed")
    
    # More status refresh logic...
    self._refresh_status()
```

### After (New Way)
```python
# In panel.py button handler:
def on_commit_clicked(self):
    message = self.commit_message.toPlainText()
    result = commit_changes(self._action_ctx, message, stage_all=True)
    
    if result.ok:
        self.show_success(result.message)
    else:
        self.show_error(result.message)
```

## Summary

The actions layer gives you:
- **Simplicity**: Button code is tiny and obvious
- **Flexibility**: Swap backends without touching UI
- **Testability**: Test logic without FreeCAD
- **Maintainability**: Add/remove features cleanly
- **Portability**: Easy to port to bash scripts (Phase 2)

This is Phase 1 foundation. Phase 2 will add script support while keeping this same clean interface.
