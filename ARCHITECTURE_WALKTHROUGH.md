# GitPDM Architecture - How Button Clicks Execute Git Commands

## Current Architecture (With Actions Layer)

### The Full Flow - Example: Commit Button

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: UI / BUTTONS (panel.py)                                    │
│                                                                      │
│  self.commit_push_btn = QtWidgets.QPushButton("Commit and Push")   │
│  self.commit_push_btn.clicked.connect(                             │
│      self._commit_push.commit_push_clicked  ← CONNECTS HERE        │
│  )                                                                  │
│                                                                      │
│  Total: 1 line to wire button                                      │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2: HANDLER (action_commit_push.py)                           │
│                                                                      │
│  class ActionCommitPushHandler:                                     │
│      def commit_push_clicked(self):                                 │
│          # 1. Check if busy                                         │
│          # 2. Get repo_root from panel                              │
│          # 3. Get commit message from UI                            │
│          # 4. Check lock violations                                 │
│          # 5. Start async commit                                    │
│                                                                      │
│      def _start_commit_async(self, repo_root, message):            │
│          ctx = create_action_context(                               │
│              git_client=self._git_client,                           │
│              repo_root=repo_root                                    │
│          )                                                          │
│          result = commit_changes(ctx, message, stage_all=True)  ← CALLS ACTION │
│          # Handle result                                            │
│                                                                      │
│  Total: 15-20 lines per button operation                           │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 3: ACTION LAYER (actions/commit_push.py)                     │
│                                                                      │
│  def commit_changes(ctx, message, stage_all):                      │
│      # 1. Validate inputs (repo_root, message, git available)      │
│      # 2. Stage files if needed                                    │
│      if stage_all:                                                  │
│          stage_result = ctx.git.stage_all(repo_root)  ← USES BACKEND │
│                                                                      │
│      # 3. Execute commit                                            │
│      commit_result = ctx.git.commit(repo_root, message)  ← USES BACKEND │
│                                                                      │
│      # 4. Return ActionResult (success/error)                       │
│      return ActionResult.success("Committed")                       │
│                                                                      │
│  Total: 25-30 lines of business logic                              │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 4: BACKEND (git/client.py OR actions/script_backend.py)     │
│                                                                      │
│  Option A: GitClient (Python subprocess)                            │
│  ┌────────────────────────────────────────────────────────┐        │
│  │ class GitClient:                                        │        │
│  │     def commit(self, repo_root, message):              │        │
│  │         cmd = [self._git_exe, "commit", "-m", message] │        │
│  │         result = subprocess.run(cmd, ...)  ← EXECUTES GIT │     │
│  │         return CmdResult(ok=True, stdout=...)          │        │
│  └────────────────────────────────────────────────────────┘        │
│                                                                      │
│  Option B: ScriptBackend (PowerShell scripts)                       │
│  ┌────────────────────────────────────────────────────────┐        │
│  │ class ScriptBackend:                                    │        │
│  │     def commit(self, repo_root, message):              │        │
│  │         script = self.scripts_dir / "git_commit.ps1"   │        │
│  │         cmd = ["powershell", "-File", script,          │        │
│  │                "-RepoPath", repo_root,                 │        │
│  │                "-Message", message]                    │        │
│  │         result = subprocess.run(cmd, ...)  ← EXECUTES SCRIPT │  │
│  └────────────────────────────────────────────────────────┘        │
│                                                                      │
│  Total: 10-15 lines per git operation                              │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 5: EXECUTION                                                  │
│                                                                      │
│  Option A: Git Command (via GitClient)                              │
│      subprocess.run(["git", "commit", "-m", "message"])            │
│                                                                      │
│  Option B: PowerShell Script (via ScriptBackend)                    │
│      subprocess.run(["powershell", "-File", "git_commit.ps1"])     │
│          ↓                                                          │
│      # Inside git_commit.ps1:                                       │
│      Push-Location $RepoPath                                       │
│      git add -A                                                    │
│      git commit -m $Message                                        │
│      Pop-Location                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Total Lines: ~60-75 lines from button to git command

---

## Alternative: Direct Script Approach (Available but not currently wired)

### Minimal Flow - Using DirectScriptHandler

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: UI / BUTTONS (panel.py)                                    │
│                                                                      │
│  from freecad.gitpdm.ui.direct_script_handler import DirectScriptHandler │
│                                                                      │
│  self._script_handler = DirectScriptHandler(self)                  │
│  self.commit_btn.clicked.connect(                                  │
│      self._script_handler.commit_clicked  ← CONNECTS HERE          │
│  )                                                                  │
│                                                                      │
│  Total: 2 lines to wire button                                     │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2: DIRECT HANDLER (ui/direct_script_handler.py)              │
│                                                                      │
│  def commit_clicked(self):                                          │
│      msg = self.panel.commit_message.toPlainText()                 │
│      result = script_commit(                                        │
│          self.panel._current_repo_root, msg, stage_all=True        │
│      )  ← CALLS SCRIPT DIRECTLY                                    │
│      self._show_result(result, "Commit")                           │
│                                                                      │
│  Total: 4 lines per button operation                               │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 3: SCRIPT EXECUTOR (core/script_executor.py)                 │
│                                                                      │
│  def script_commit(repo_path, message, stage_all):                 │
│      return execute_script(                                         │
│          "git_commit.ps1",                                          │
│          repo_path=repo_path,                                       │
│          message=message,                                           │
│          stage_all=stage_all                                        │
│      )  ← EXECUTES SCRIPT                                          │
│                                                                      │
│  Total: 1 function call                                            │
└─────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 4: EXECUTION                                                  │
│                                                                      │
│  subprocess.run([                                                   │
│      "powershell", "-File", "git_commit.ps1",                      │
│      "-RepoPath", repo_path,                                       │
│      "-Message", message,                                           │
│      "-StageAll"                                                   │
│  ])                                                                 │
│      ↓                                                              │
│  # Inside git_commit.ps1:                                           │
│  Push-Location $RepoPath                                           │
│  git add -A                                                        │
│  git commit -m $Message                                            │
│  Pop-Location                                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Total Lines: ~7 lines from button to git command (90% reduction!)

---

## Key Files in Current Architecture

### UI Layer
- **freecad/gitpdm/ui/panel.py** (2,091 lines)
  - Creates all buttons
  - Wires buttons to handlers (1 line each)
  - Example: `self.fetch_btn.clicked.connect(self._fetch_pull.fetch_clicked)`

### Handler Layer (Currently Active)
- **freecad/gitpdm/ui/action_commit_push.py** (416 lines)
  - Handles: Commit, Push, Commit+Push buttons
  - Methods: `commit_clicked()`, `push_clicked()`, `commit_push_clicked()`

- **freecad/gitpdm/ui/action_fetch_pull.py** (318 lines)
  - Handles: Fetch, Pull buttons
  - Methods: `fetch_clicked()`, `pull_clicked()`

- **freecad/gitpdm/ui/action_validation.py** (309 lines)
  - Handles: Validate, Create Repo, Refresh buttons
  - Methods: `validate_repo_path()`, `create_repo_clicked()`, `refresh_clicked()`

### Action Layer
- **freecad/gitpdm/actions/commit_push.py** (132 lines)
  - Functions: `commit_changes()`, `push_changes()`
  - Pure business logic, no UI

- **freecad/gitpdm/actions/fetch_pull.py** (89 lines)
  - Functions: `fetch_from_remote()`, `pull_from_remote()`

- **freecad/gitpdm/actions/repository.py** (103 lines)
  - Functions: `validate_repo()`, `init_repo()`

### Backend Layer
- **freecad/gitpdm/git/client.py** (1,840 lines)
  - Class: `GitClient`
  - Executes git via Python subprocess
  - Methods: `commit()`, `push()`, `fetch()`, `pull()`, etc.

- **freecad/gitpdm/actions/script_backend.py** (249 lines)
  - Class: `ScriptBackend`
  - Executes PowerShell scripts instead of direct git
  - Alternative to GitClient (swappable via protocol)

### Scripts (Available but not wired)
- **freecad/gitpdm/scripts/*.ps1** (9 files)
  - git_commit.ps1, git_push.ps1, git_fetch.ps1, etc.
  - Can be called directly with DirectScriptHandler

---

## Button Wiring Examples

### Current Wiring (In panel.py)

```python
# Line 59-62: Create handlers
self._fetch_pull = ActionFetchPullHandler(self, self._git_client, self._job_runner)
self._commit_push = ActionCommitPushHandler(self, self._git_client, self._job_runner)
self._repo_validator = ActionValidationHandler(self, self._git_client, self._job_runner)

# Line 604: Wire Fetch button
self.fetch_btn.clicked.connect(self._fetch_pull.fetch_clicked)

# Line 613: Wire Pull button  
self.pull_btn.clicked.connect(self._fetch_pull.pull_clicked)

# Line 655: Wire Commit+Push button
self.commit_push_btn.clicked.connect(self._commit_push.commit_push_clicked)
```

### Alternative Direct Script Wiring (Available but commented out)

```python
# To switch to direct scripts, replace handler creation with:
from freecad.gitpdm.ui.direct_script_handler import DirectScriptHandler
self._script_handler = DirectScriptHandler(self)

# Then wire buttons (1 line each):
self.commit_btn.clicked.connect(self._script_handler.commit_clicked)
self.push_btn.clicked.connect(self._script_handler.push_clicked)
self.fetch_btn.clicked.connect(self._script_handler.fetch_clicked)
```

---

## Summary

### Current System (Actions Layer)
✅ **Well structured** - clear separation of concerns  
✅ **Testable** - action layer has no UI dependencies  
✅ **Swappable backend** - can switch Python ↔ PowerShell  
❌ **More code** - ~60-75 lines between button and git  

### Direct Script System (Available)
✅ **Minimal code** - ~7 lines between button and git  
✅ **Simple** - easy to understand and modify  
✅ **PowerShell ready** - uses .ps1 scripts directly  
❌ **Less abstraction** - harder to swap backends  

Both systems exist in the codebase. Current wiring uses the action layer.
To switch to direct scripts, just change the handler wiring in panel.py!
