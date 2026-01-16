# GitPDM Actions - Quick Reference Cheat Sheet

## 📦 Import

```python
from freecad.gitpdm.actions import (
    create_action_context,      # Setup helper
    validate_repo,              # Repository
    init_repo,
    refresh_status,             # Status
    get_file_changes,
    commit_changes,             # Commit/Push
    push_changes,
    fetch_from_remote,          # Fetch/Pull
    pull_from_remote,
    add_remote,                 # Remote
)
```

## 🔧 Setup (Once)

```python
# In your UI __init__:
self._ctx = create_action_context(
    git_client=self._git_client,
    repo_root="/path/to/repo"
)

# Update when repo changes:
self._ctx.repo_root = new_path
```

## 🎯 Button Patterns

### Simple Button
```python
def on_button_clicked(self):
    result = action_function(self._ctx, inputs...)
    
    if result.ok:
        self.show_success(result.message)
    else:
        self.show_error(result.message)
```

### With Error Handling
```python
def on_button_clicked(self):
    result = action_function(self._ctx, inputs...)
    
    if result.ok:
        self.show_success(result.message)
    else:
        # Specific error handling
        if result.error_code == "no_remote":
            self.show_add_remote_dialog()
        else:
            self.show_error(result.message)
```

### Chain Actions
```python
def on_publish_clicked(self):
    # Commit
    commit_result = commit_changes(self._ctx, message, True)
    if not commit_result.ok:
        return self.show_error(commit_result.message)
    
    # Push
    push_result = push_changes(self._ctx)
    if push_result.ok:
        self.show_success("Published!")
    else:
        self.show_error(push_result.message)
```

## 📋 Action Reference

| Action | Inputs | Returns |
|--------|--------|---------|
| `validate_repo(ctx, path)` | `path: str` | `repo_root` in details |
| `init_repo(ctx, path)` | `path: str` | `repo_root` in details |
| `refresh_status(ctx)` | None | `branch`, `upstream`, `ahead`, `behind` |
| `get_file_changes(ctx)` | None | `files`, counts |
| `commit_changes(ctx, msg, stage_all)` | `message: str`, `stage_all: bool` | Success/error |
| `push_changes(ctx, force)` | `force: bool` (optional) | `remote`, `branch` |
| `fetch_from_remote(ctx)` | None | Updates timestamp |
| `pull_from_remote(ctx)` | None | Updates timestamp |
| `add_remote(ctx, name, url)` | `name: str`, `url: str` | `name`, `url` |

## 🚨 Common Error Codes

| Code | Meaning | Suggested Action |
|------|---------|------------------|
| `no_repo` | No repository path | Set `ctx.repo_root` |
| `git_not_found` | Git not on PATH | Install Git |
| `not_a_repo` | Path is not a repo | Initialize or select different path |
| `no_message` | Missing commit message | Prompt user |
| `no_remote` | Remote not configured | Show add remote dialog |
| `auth_failed` | Authentication failed | Check credentials |
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
