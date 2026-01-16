# GitPDM Button Action API

## Quick Start Guide for Adding New Git Operations

This guide shows you how to add new buttons that execute Git commands in the GitPDM FreeCAD extension.

---

## Architecture Overview

```
┌─────────────────┐
│  Button Click   │  1. User clicks button in FreeCAD UI
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Handler Method  │  2. DirectScriptHandler method (2-5 lines)
└────────┬────────┘     - Gets input from UI
         │              - Calls script executor
         ▼
┌─────────────────┐
│ Script Executor │  3. Executes PowerShell/Bash script
└────────┬────────┘     - Passes parameters to script
         │              - Returns result
         ▼
┌─────────────────┐
│  Git Command    │  4. Script runs git command
└─────────────────┘
```

**Key Benefits:**
- **Simple**: 3-5 lines of Python per operation
- **Direct**: No middleware or abstraction layers
- **Testable**: Scripts can be run from command line
- **Cross-platform**: PowerShell for Windows, Bash for Linux/Mac

---

## Step-by-Step: Adding a New Git Operation

### 1. Create the Script

Create a new PowerShell script in `freecad/gitpdm/scripts/`:

```powershell
# freecad/gitpdm/scripts/git_my_operation.ps1

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath,
    
    [Parameter(Mandatory=$false)]
    [string]$MyParameter
)

# Change to repository directory
Push-Location $RepoPath

try {
    # Execute git command
    git my-operation $MyParameter
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Git operation failed"
        exit 1
    }
    
    Write-Output "Operation completed successfully"
    exit 0
    
} finally {
    Pop-Location
}
```

### 2. Add Script Wrapper (Optional)

If you want a convenient Python wrapper, add to `freecad/gitpdm/core/script_executor.py`:

```python
def script_my_operation(repo_path: str, my_parameter: str) -> ScriptResult:
    """
    Execute my git operation.
    
    Args:
        repo_path: Repository root path
        my_parameter: My parameter value
        
    Returns:
        ScriptResult with success/output/error
    """
    return execute_script(
        "git_my_operation.ps1",
        repo_path=repo_path,
        my_parameter=my_parameter
    )
```

### 3. Add Handler Method

Add a method to `DirectScriptHandler` in `freecad/gitpdm/ui/direct_script_handler.py`:

```python
def my_operation_clicked(self):
    """Handle my operation button click."""
    # Get input from UI
    param = self.panel.my_input_field.text().strip()
    if not param:
        return
    
    # Execute script
    result = script_my_operation(self.panel._current_repo_root, param)
    
    # Show result
    self._show_result(result, "My Operation")
```

**That's it! Only 3-5 lines of code.**

### 4. Wire the Button

In `panel.py`, connect your button to the handler:

```python
# In _build_buttons_section() or wherever you create buttons:
self.my_operation_btn = QtWidgets.QPushButton("My Operation")
self.my_operation_btn.clicked.connect(self._script_handler.my_operation_clicked)
```

---

## Real Examples

### Example 1: Simple Operation (Fetch)

**Handler** (`direct_script_handler.py`):
```python
def fetch_clicked(self):
    """Handle fetch button click."""
    result = script_fetch(self.panel._current_repo_root)
    self._show_result(result, "Fetch")
```

**Wiring** (`panel.py`):
```python
self.fetch_btn.clicked.connect(self._script_handler.fetch_clicked)
```

**Total: 2 lines in handler + 1 line to wire = 3 lines**

---

### Example 2: Operation with Input (Commit)

**Handler** (`direct_script_handler.py`):
```python
def commit_clicked(self):
    """Handle commit button click."""
    msg = self.panel.commit_message.toPlainText().strip()
    if not msg:
        return
    
    result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
    self._show_result(result, "Commit")
```

**Wiring** (`panel.py`):
```python
self.commit_btn.clicked.connect(self._script_handler.commit_clicked)
```

**Total: 4 lines in handler + 1 line to wire = 5 lines**

---

### Example 3: Dialog Input (Add Remote)

**Handler** (`direct_script_handler.py`):
```python
def add_remote_clicked(self):
    """Handle add remote button click - prompts for URL."""
    url, ok = QtWidgets.QInputDialog.getText(
        self.panel, "Add Remote", "Enter remote URL:"
    )
    if not ok or not url:
        return
    
    result = execute_script(
        "git_add_remote.ps1",
        repo_path=self.panel._current_repo_root,
        name="origin",
        url=url
    )
    self._show_result(result, "Add Remote")
```

**Total: 7 lines in handler + 1 line to wire = 8 lines**

---

### Example 4: Chained Operations (Commit + Push)

**Handler** (`direct_script_handler.py`):
```python
def commit_and_push_clicked(self):
    """Handle combined commit and push button click."""
    msg = self.panel.commit_message.toPlainText().strip()
    if not msg:
        return
    
    # Commit first
    result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
    if not result.success:
        self._show_result(result, "Commit")
        return
    
    # Then push
    result = script_push(self.panel._current_repo_root)
    self._show_result(result, "Commit & Push")
```

**Total: 9 lines in handler + 1 line to wire = 10 lines**

---

## Available Script Functions

Pre-built script wrappers in `script_executor.py`:

```python
# Basic operations
script_commit(repo_path, message, stage_all=False)
script_push(repo_path)
script_fetch(repo_path)
script_pull(repo_path)
script_validate(repo_path)

# Generic execution
execute_script(script_name, repo_path=None, **kwargs)
```

---

## Script Parameter Convention

Scripts use PowerShell parameter naming:

```python
# Python call:
execute_script("git_my_script.ps1", 
    repo_path="/path/to/repo",
    my_parameter="value",
    enable_feature=True
)

# Becomes PowerShell:
# git_my_script.ps1 -RepoPath "/path/to/repo" -MyParameter "value" -EnableFeature
```

**Rules:**
- `repo_path` → `-RepoPath` (required for most operations)
- `my_parameter` → `-MyParameter` (underscores removed, title cased)
- Boolean `True` → flag included, Boolean `False` → flag omitted

---

## Best Practices

### ✅ Do:
- Keep handler methods short (2-10 lines)
- Put complex logic in scripts, not Python
- Use `_show_result()` to display outcomes consistently
- Check for required inputs before calling scripts
- Return early on validation failures

### ❌ Don't:
- Add business logic to handlers
- Create intermediate abstraction layers
- Parse git output in Python (do it in scripts)
- Call git commands directly from Python

---

## Testing Your Operation

### 1. Test Script Directly

```powershell
# Windows
.\freecad\gitpdm\scripts\git_my_operation.ps1 -RepoPath "C:\path\to\repo" -MyParameter "value"
```

```bash
# Linux/Mac
bash freecad/gitpdm/scripts/git_my_operation.sh /path/to/repo value
```

### 2. Test from Python Console

```python
from freecad.gitpdm.core.script_executor import execute_script

result = execute_script("git_my_operation.ps1", 
    repo_path="/path/to/repo",
    my_parameter="value"
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Error: {result.error}")
```

### 3. Test from FreeCAD

1. Load the GitPDM extension
2. Click your new button
3. Check the result dialog

---

## Troubleshooting

### Script Not Found
- Check script exists in `freecad/gitpdm/scripts/`
- Verify filename matches what you're calling

### Permission Denied
- On Linux/Mac: `chmod +x script_name.sh`
- On Windows: Check PowerShell execution policy

### Git Command Fails
- Test git command manually in terminal first
- Check repository path is correct
- Verify git is in PATH

### Wrong Parameters
- Check parameter naming (underscores → title case)
- Verify script accepts the parameters you're passing
- Check parameter types (string vs bool)

---

## File Locations

```
GitPDM/
├── freecad/gitpdm/
│   ├── scripts/              # PowerShell/Bash scripts
│   │   ├── git_commit.ps1
│   │   ├── git_push.ps1
│   │   └── git_my_operation.ps1  ← Add your script here
│   ├── core/
│   │   └── script_executor.py    ← Add wrapper functions here
│   └── ui/
│       ├── direct_script_handler.py  ← Add handler methods here
│       └── panel.py                   ← Wire buttons here
└── docs/
    └── BUTTON_API.md            ← This file
```

---

## Summary

Adding a new Git operation is simple:

1. **Create script** (15-20 lines of PowerShell/Bash)
2. **Add handler** (3-5 lines of Python)
3. **Wire button** (1 line in panel.py)

**Total: ~20-25 lines of code for a complete feature**

The key is keeping Python simple and putting Git logic in scripts where it belongs.

---

## Questions?

- Check existing operations in `direct_script_handler.py` for examples
- Review scripts in `freecad/gitpdm/scripts/` for patterns
- Test scripts independently before wiring to UI
