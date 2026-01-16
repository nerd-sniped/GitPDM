"""
ABSOLUTE MINIMUM: Button → Script in 3 Lines

This is the tightest possible loop - no handlers, no abstractions.
Just direct script execution from button click.
"""

# ============================================================================
# Option 1: Inline in panel.py (ABSOLUTE MINIMUM - 3 lines per button)
# ============================================================================

"""
# In panel.py, import at top:
from freecad.gitpdm.core.script_executor import script_commit, script_push, script_fetch

# Wire buttons with lambda (1 line each):
self.commit_btn.clicked.connect(
    lambda: self._show_script_result(
        script_commit(self._current_repo_root, self.commit_message.toPlainText(), stage_all=True),
        "Commit"
    )
)

self.push_btn.clicked.connect(
    lambda: self._show_script_result(
        script_push(self._current_repo_root),
        "Push"
    )
)

self.fetch_btn.clicked.connect(
    lambda: self._show_script_result(
        script_fetch(self._current_repo_root),
        "Fetch"
    )
)

# Add one helper method (5 lines):
def _show_script_result(self, result, operation):
    if result.success:
        QtWidgets.QMessageBox.information(self, f"{operation} Success", result.output)
    else:
        QtWidgets.QMessageBox.critical(self, f"{operation} Failed", result.error)
"""


# ============================================================================
# Option 2: Even More Minimal with @staticmethod (2 lines per button)
# ============================================================================

"""
# In panel.py:
from freecad.gitpdm.core.script_executor import script_commit

# Define minimal wrappers (2 lines each):
def _commit(self):
    result = script_commit(self._current_repo_root, self.commit_message.toPlainText(), True)
    self._show_script_result(result, "Commit")

def _push(self):
    result = script_push(self._current_repo_root)
    self._show_script_result(result, "Push")

# Wire (1 line):
self.commit_btn.clicked.connect(self._commit)
self.push_btn.clicked.connect(self._push)
"""


# ============================================================================
# Option 3: Ultra-tight with decorators (EXPERIMENTAL)
# ============================================================================

def script_button(script_func, operation_name):
    """
    Decorator to create button handler that executes script.
    
    Usage:
        @script_button(script_commit, "Commit")
        def on_commit(self):
            return self._current_repo_root, self.commit_message.toPlainText(), True
    """
    def decorator(get_args_func):
        def handler(self):
            args = get_args_func(self)
            if isinstance(args, tuple):
                result = script_func(*args)
            else:
                result = script_func(args)
            self._show_script_result(result, operation_name)
        return handler
    return decorator


"""
# Usage with decorator:
from freecad.gitpdm.core.script_executor import script_commit, script_push

@script_button(script_commit, "Commit")
def on_commit_clicked(self):
    return self._current_repo_root, self.commit_message.toPlainText(), True

@script_button(script_push, "Push")
def on_push_clicked(self):
    return self._current_repo_root

# Wire:
self.commit_btn.clicked.connect(self.on_commit_clicked)
self.push_btn.clicked.connect(self.on_push_clicked)
"""


# ============================================================================
# COMPARISON OF MINIMALISM
# ============================================================================

"""
CURRENT (Action Layer):
-----------------------
60-75 lines of Python between button and script

OPTION 1 (Lambda inline):
-------------------------
3 lines per button (lambda + helper)

OPTION 2 (Minimal methods):
---------------------------
2 lines per button (method body)

OPTION 3 (Decorator):
---------------------
3 lines per button (decorator + return args)


RECOMMENDATION: Option 2 (minimal methods)
==========================================
- Most readable
- Easy to debug
- No magic (decorators/lambdas)
- Just 2 lines per button
- Total reduction: 60-75 lines → 2 lines = 97% less code


EXAMPLE for entire commit/push workflow:
==========================================

# Import (1 line):
from freecad.gitpdm.core.script_executor import script_commit, script_push

# Helper (5 lines, shared):
def _show_script_result(self, result, operation):
    if result.success:
        QtWidgets.QMessageBox.information(self, f"{operation} OK", result.output)
    else:
        QtWidgets.QMessageBox.critical(self, f"{operation} Failed", result.error)

# Commit button (2 lines):
def _on_commit(self):
    result = script_commit(self._current_repo_root, self.commit_message.toPlainText(), True)
    self._show_script_result(result, "Commit")

# Push button (2 lines):
def _on_push(self):
    result = script_push(self._current_repo_root)
    self._show_script_result(result, "Push")

# Fetch button (2 lines):
def _on_fetch(self):
    result = script_fetch(self._current_repo_root)
    self._show_script_result(result, "Fetch")

# Pull button (2 lines):
def _on_pull(self):
    result = script_pull(self._current_repo_root)
    self._show_script_result(result, "Pull")

# Wire buttons (4 lines):
self.commit_btn.clicked.connect(self._on_commit)
self.push_btn.clicked.connect(self._on_push)
self.fetch_btn.clicked.connect(self._on_fetch)
self.pull_btn.clicked.connect(self._on_pull)

TOTAL: 18 lines for 4 complete button handlers (vs 240+ lines with action layer)
"""
