# GitPDM Development Cheat Sheet

## 🚀 Quick Reference for Developers

This cheatsheet provides quick access to common development tasks in GitPDM.

---

## Adding New Git Operations

**See [BUTTON_API.md](BUTTON_API.md) for complete guide.**

**Quick Pattern:**

1. Create script in `freecad/gitpdm/scripts/git_operation.ps1`
2. Add handler method to `DirectScriptHandler`
3. Wire button in `panel.py`

```python
# Handler (3-5 lines)
def my_operation_clicked(self):
    result = script_my_operation(self.panel._current_repo_root, params)
    self._show_result(result, "My Operation")

# Wiring (1 line)
self.my_btn.clicked.connect(self._script_handler.my_operation_clicked)
```

---

## Architecture Layers

```
UI Layer (panel.py)
    ↓
Handler Layer (direct_script_handler.py)
    ↓
Script Executor (script_executor.py)
    ↓
PowerShell/Bash Scripts (scripts/*.ps1)
    ↓
Git Commands
```

**Keep it simple**: Business logic belongs in scripts, not Python.

---

## Common Operations

### Execute a Git Script

```python
from freecad.gitpdm.core.script_executor import execute_script

result = execute_script(
    "git_commit.ps1",
    repo_path=repo_root,
    message="My commit",
    stage_all=True
)

if result.success:
    print(result.output)
else:
    print(result.error)
```

### Pre-built Script Functions

```python
from freecad.gitpdm.core.script_executor import (
    script_commit,
    script_push,
    script_fetch,
    script_pull,
    script_validate
)

# Use directly
result = script_commit(repo_path, message, stage_all=True)
result = script_push(repo_path)
result = script_fetch(repo_path)
```

---

## File Organization

| Directory | Purpose |
|-----------|---------|
| `freecad/gitpdm/scripts/` | PowerShell/Bash git scripts |
| `freecad/gitpdm/core/script_executor.py` | Script execution wrapper |
| `freecad/gitpdm/ui/direct_script_handler.py` | Button click handlers |
| `freecad/gitpdm/ui/panel.py` | Main UI panel |
| `freecad/gitpdm/ui/components/` | Reusable UI widgets |
| `freecad/gitpdm/git/client.py` | Git client (direct commands) |
| `freecad/gitpdm/github/` | GitHub API integration |
| `freecad/gitpdm/export/` | Export and preview generation |

---

## UI Components

### StatusWidget
Displays git status, branch, upstream info.

```python
from freecad.gitpdm.ui.components import StatusWidget

status = StatusWidget(parent, git_client, job_runner)
status.status_updated.connect(on_status_changed)
```

### RepositoryWidget
Repository selection and management.

```python
from freecad.gitpdm.ui.components import RepositoryWidget

repo = RepositoryWidget(parent, git_client, job_runner)
repo.repository_changed.connect(on_repo_changed)
```

### ChangesWidget
File changes list and staging.

```python
from freecad.gitpdm.ui.components import ChangesWidget

changes = ChangesWidget(parent, git_client, job_runner)
changes.stage_all_changed.connect(on_stage_changed)
```

---

## Git Client Direct Usage

For operations not using scripts:

```python
from freecad.gitpdm.git.client import GitClient

git = GitClient()

# Check if git is available
if not git.is_git_available():
    print("Git not found")

# Get repo root
repo_root = git.get_repo_root("/some/path")

# Get status
status = git.get_status_porcelain(repo_root)

# Current branch
branch = git.current_branch(repo_root)

# Commit
result = git.commit(repo_root, "My message")
if result.ok:
    print("Committed!")
```

---

## GitHub Integration

```python
from freecad.gitpdm.github.api_client import GitHubAPIClient

# Initialize (handles authentication)
client = GitHubAPIClient()

# Check authentication
if client.is_authenticated():
    user = client.get_user()
    print(f"Logged in as {user['login']}")

# List repositories
repos = client.get_user_repos()

# Create repository
result = client.create_repo("my-repo", "Description", private=True)
```

---

## Export and Previews

```python
from freecad.gitpdm.export import exporter

# Export active document
result = exporter.export_active_document(repo_root)

if result.ok:
    print(f"Exported to {result.rel_dir}")
    print(f"Files: {result.files}")
```

---

## Logging

```python
from freecad.gitpdm.core import log

log.debug("Debug message")
log.info("Info message")
log.warning("Warning message")
log.error("Error message")
```

---

## Settings

```python
from freecad.gitpdm.core import settings

# Get/set repository
repo = settings.get_last_repo_path()
settings.save_last_repo_path("/path/to/repo")

# Remote name
remote = settings.get_remote_name()  # Default: "origin"
settings.save_remote_name("upstream")

# Preview settings
settings.save_last_preview_at(iso_timestamp)
preview_dir = settings.get_last_preview_dir()
```

---

## Testing

### Test Scripts Manually

```powershell
# Windows
.\freecad\gitpdm\scripts\git_commit.ps1 -RepoPath "C:\repo" -Message "test"
```

```bash
# Linux/Mac
bash freecad/gitpdm/scripts/git_commit.sh /path/to/repo "test"
```

### Test Handler Methods

```python
# In FreeCAD Python console
from freecad.gitpdm.ui.panel import GitPDMDockWidget

panel = GitPDMDockWidget()
panel._script_handler.fetch_clicked()
```

---

## Common Patterns

### Show Result Dialog

```python
from PySide6 import QtWidgets

if result.success:
    QtWidgets.QMessageBox.information(
        parent, "Success", result.output
    )
else:
    QtWidgets.QMessageBox.critical(
        parent, "Error", result.error
    )
```

### Get User Input

```python
from PySide6 import QtWidgets

text, ok = QtWidgets.QInputDialog.getText(
    parent, "Title", "Prompt:"
)
if ok and text:
    # Use text
```

### Run Async Job

```python
def _do_work():
    # Long-running operation
    return result

job_runner.run_callable(
    "job_name",
    _do_work,
    on_success=lambda r: print("Done"),
    on_error=lambda e: print(f"Error: {e}")
)
```

---

## Debugging Tips

1. **Check logs**: Look in FreeCAD console for debug output
2. **Test scripts independently**: Run PowerShell/Bash scripts directly
3. **Use print statements**: Add prints in handler methods
4. **Check return values**: Verify `result.success`, `result.output`, `result.error`
5. **Verify paths**: Ensure repo_root is correct

---

## Resources

- [BUTTON_API.md](BUTTON_API.md) - Complete guide to adding new operations
- [README.md](README.md) - Project overview and setup
- `freecad/gitpdm/scripts/` - Example scripts
- `freecad/gitpdm/ui/direct_script_handler.py` - Example handlers

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Add git operation | See [BUTTON_API.md](BUTTON_API.md) |
| Execute script | `execute_script("name.ps1", repo_path=path, **kwargs)` |
| Get repo root | `git_client.get_repo_root(path)` |
| Commit | `git_client.commit(repo_root, message)` |
| Push | `git_client.push(repo_root, remote, branch)` |
| Fetch | `git_client.fetch(repo_root, remote)` |
| Get status | `git_client.get_status_porcelain(repo_root)` |
| Current branch | `git_client.current_branch(repo_root)` |

---

**Remember**: Keep Python simple, put Git logic in scripts!

| `push_rejected_behind` | Behind remote | Pull first |
| `nothing_to_commit` | No changes | Show info message |

## 💡 Common UI Patterns

### Generic Result Handler
```python
def handle_result(self, result):
    """Generic handler for any action result."""
    if result.ok:
        self.status_bar.showMessage(result.message, 3000)
    else:
        self.show_error(result.message)
```

### Check Error Code
```python
if result.error_code == "no_remote":
    # Specific handling
elif result.error_code == "auth_failed":
    # Different handling
else:
    # Generic error
```

### Update UI After Action
```python
result = commit_changes(self._ctx, message, True)
if result.ok:
    self.show_success(result.message)
    self.commit_message.clear()      # Clear input
    self._refresh_status()            # Update UI
```

## 📁 Files to Read

| File | What It Contains |
|------|------------------|
| [freecad/gitpdm/actions/__init__.py](freecad/gitpdm/actions/__init__.py) | Public API imports |
| [freecad/gitpdm/actions/types.py](freecad/gitpdm/actions/types.py) | `ActionContext`, `ActionResult` |
| [freecad/gitpdm/actions/README.md](freecad/gitpdm/actions/README.md) | Full documentation |
| [freecad/gitpdm/actions/EXAMPLE_USAGE.py](freecad/gitpdm/actions/EXAMPLE_USAGE.py) | Working examples |
| [docs/BUTTON_ACTION_MAP.md](docs/BUTTON_ACTION_MAP.md) | Button-to-action mapping |
| [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) | Quick start guide |

## 🧪 Testing Snippet

```python
from freecad.gitpdm.actions import ActionContext, commit_changes
from freecad.gitpdm.actions.backend import GitClientBackend

# Create context
ctx = ActionContext(
    git=GitClientBackend(),
    repo_root="/tmp/test-repo"
)

# Test action
result = commit_changes(ctx, "Test commit", stage_all=True)

# Check result
assert result.ok or result.error_code == "nothing_to_commit"
```

## 🎯 Migration Checklist

- [ ] Import actions in UI file
- [ ] Create `self._ctx` in `__init__`
- [ ] Replace first button handler
- [ ] Test thoroughly
- [ ] Repeat for remaining buttons
- [ ] Delete old handler code
- [ ] Celebrate! 🎉

## ⚡ Pro Tips

1. **Create context once** - Don't recreate on every button click
2. **Update repo_root** - When user selects different repo
3. **Check error codes** - For specific error handling
4. **Chain carefully** - Stop on first error
5. **Keep UI simple** - Just gather/display, don't add logic

## 🔗 Links

- Actions README: [freecad/gitpdm/actions/README.md](freecad/gitpdm/actions/README.md)
- Examples: [freecad/gitpdm/actions/EXAMPLE_USAGE.py](freecad/gitpdm/actions/EXAMPLE_USAGE.py)
- Button Map: [docs/BUTTON_ACTION_MAP.md](docs/BUTTON_ACTION_MAP.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

**TL;DR**: Import actions, create context once, use in 3-line button handlers. Done! 🚀
