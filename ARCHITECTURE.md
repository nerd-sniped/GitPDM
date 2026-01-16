# GitPDM Architecture Reference Card

## 🎯 Quick Architecture Overview

```
┌──────────────────────────────────────┐
│         Button Click (UI)            │
│         panel.py                     │
└──────────────┬───────────────────────┘
               │ .clicked.connect()
               ▼
┌──────────────────────────────────────┐
│    Handler Method (2-5 lines)        │
│    direct_script_handler.py          │
│    - Get inputs                      │
│    - Call script                     │
│    - Show result                     │
└──────────────┬───────────────────────┘
               │ script_*() or execute_script()
               ▼
┌──────────────────────────────────────┐
│      Script Executor                 │
│      script_executor.py              │
│      - Build command                 │
│      - Execute subprocess            │
│      - Return ScriptResult           │
└──────────────┬───────────────────────┘
               │ PowerShell/Bash
               ▼
┌──────────────────────────────────────┐
│    Git Script (15-20 lines)          │
│    scripts/git_*.ps1                 │
│    - Navigate to repo                │
│    - Run git command                 │
│    - Handle errors                   │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         Git Command                  │
└──────────────────────────────────────┘
```

## 📋 Component Responsibilities

| Component | Purpose | Lines | Language |
|-----------|---------|-------|----------|
| **Button** | User interaction | 1 | Python |
| **Handler** | UI logic & orchestration | 2-5 | Python |
| **Executor** | Script execution wrapper | N/A | Python |
| **Script** | Git operation logic | 15-20 | PowerShell/Bash |
| **Git** | Version control | N/A | Git CLI |

## 🔧 Adding a New Git Operation

### 1️⃣ Create Script (15-20 lines)
```powershell
# freecad/gitpdm/scripts/git_my_operation.ps1
param([Parameter(Mandatory=$true)][string]$RepoPath)

Push-Location $RepoPath
try {
    git my-operation
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
```

### 2️⃣ Add Handler (3-5 lines)
```python
# In direct_script_handler.py
def my_operation_clicked(self):
    result = script_my_operation(self.panel._current_repo_root)
    self._show_result(result, "My Operation")
```

### 3️⃣ Wire Button (1 line)
```python
# In panel.py
self.my_btn.clicked.connect(self._script_handler.my_operation_clicked)
```

**Total: ~20-25 lines for complete feature**

## 📁 File Locations

```
GitPDM/
├── freecad/gitpdm/
│   ├── scripts/
│   │   └── git_*.ps1              ← Add scripts here
│   ├── core/
│   │   └── script_executor.py     ← Script wrappers
│   └── ui/
│       ├── direct_script_handler.py  ← Add handlers here
│       └── panel.py                   ← Wire buttons here
└── docs/
    └── BUTTON_API.md              ← Complete guide
```

## 🎨 Code Patterns

### Simple Operation (Fetch)
```python
def fetch_clicked(self):
    result = script_fetch(self.panel._current_repo_root)
    self._show_result(result, "Fetch")
```
**2 lines total**

### With Input (Commit)
```python
def commit_clicked(self):
    msg = self.panel.commit_message.toPlainText().strip()
    if not msg:
        return
    result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
    self._show_result(result, "Commit")
```
**4 lines total**

### Chained Operations (Commit + Push)
```python
def commit_and_push_clicked(self):
    msg = self.panel.commit_message.toPlainText().strip()
    if not msg:
        return
    
    result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
    if not result.success:
        self._show_result(result, "Commit")
        return
    
    result = script_push(self.panel._current_repo_root)
    self._show_result(result, "Commit & Push")
```
**9 lines total**

## 🚫 Anti-Patterns

### ❌ Don't: Add abstraction layers
```python
# NO - Don't create action classes
class CommitAction:
    def execute(self, ctx):
        # Complex abstraction...
```

### ❌ Don't: Put Git logic in Python
```python
# NO - Git logic belongs in scripts
def commit_clicked(self):
    subprocess.run(['git', 'add', '-A'])
    subprocess.run(['git', 'commit', '-m', msg])
```

### ❌ Don't: Create multiple handler patterns
```python
# NO - One handler class only
class AlternativeCommitHandler:
    # Competing pattern...
```

### ✅ Do: Keep handlers simple
```python
# YES - Direct, simple, clear
def commit_clicked(self):
    result = script_commit(repo_root, message, stage_all=True)
    self._show_result(result, "Commit")
```

## 🧪 Testing Checklist

- [ ] Script runs independently from command line
- [ ] Handler method is 2-10 lines max
- [ ] Button wired with single `.connect()` call
- [ ] Result displayed with `_show_result()`
- [ ] Input validation done in handler
- [ ] Git logic in script, not Python

## 📖 Documentation Reference

| Document | Purpose |
|----------|---------|
| [BUTTON_API.md](docs/BUTTON_API.md) | Complete guide with examples |
| [CHEATSHEET.md](docs/CHEATSHEET.md) | Quick reference for developers |
| [README.md](README.md) | Project overview |
| direct_script_handler.py | Working examples |

## 💡 Key Principles

1. **Keep Python Simple** - UI logic only, 2-5 lines per operation
2. **Scripts Do Work** - All Git logic in PowerShell/Bash scripts
3. **Direct Flow** - No middleware, no abstraction layers
4. **Testable** - Scripts runnable from command line
5. **Single Pattern** - One way to do things (DirectScriptHandler)

## 🎯 Success Criteria

Your operation is well-designed if:
- ✅ Handler method is under 10 lines
- ✅ Script can be tested independently
- ✅ No Git commands in Python code
- ✅ Follows existing handler patterns
- ✅ Uses `_show_result()` for feedback

## 🆘 Getting Help

1. Read [BUTTON_API.md](docs/BUTTON_API.md) for detailed guide
2. Study existing handlers in `direct_script_handler.py`
3. Test scripts independently before wiring
4. Check [CHEATSHEET.md](docs/CHEATSHEET.md) for patterns

---

**Architecture:** 3 layers (UI → Handler → Script)  
**Pattern:** DirectScriptHandler only  
**Philosophy:** Simple Python, powerful scripts  
**Lines per feature:** ~20-25 total
