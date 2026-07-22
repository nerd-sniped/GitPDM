# -*- coding: utf-8 -*-
"""
Regression test for the Open/Clone repo-picker's `on_connect_requested`
callback wiring.

`GitPDMDockWidget._on_open_clone_repo_clicked` (ui/panel.py) passes a
callback into `RepoPickerDialog` that the picker later invokes with zero
arguments when the user clicks Connect/Reconnect (ui/repo_picker.py). A
prior refactor moved the GitHub connect handler out of the dock widget and
into `ConnectionsDialog` but missed updating this call site, leaving it
pointing at `self._on_github_connect_clicked` -- an attribute that no
longer exists on `GitPDMDockWidget`, silently swallowed by the flow's own
try/except and surfaced only as a runtime `AttributeError` in the log.

`ui/panel.py` subclasses `QtWidgets.QDockWidget` and `ui/connections_dialog.py`
subclasses `QtWidgets.QDialog`; under this repo's Qt auto-mocking
(conftest.py mocks the `PySide` modules with `MagicMock()`), using a
`MagicMock()` attribute as a class base does not produce a real class, so
these modules can't be meaningfully imported/instantiated in tests. Instead
this test parses the source directly and checks the callback's attribute
chain actually resolves to a real method, which is what would have caught
this bug.
"""

import ast
from pathlib import Path

PANEL_PATH = Path(__file__).parent.parent / "freecad_gitpdm" / "ui" / "panel.py"
CONNECTIONS_DIALOG_PATH = (
    Path(__file__).parent.parent / "freecad_gitpdm" / "ui" / "connections_dialog.py"
)


def _find_class(tree, class_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"class {class_name} not found")


def _find_method(class_node, method_name):
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"method {method_name} not found on class {class_node.name}")


def _attribute_chain(node):
    """Render an `ast.Attribute`/`ast.Name` chain like `self._x.y` as a string."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _on_connect_requested_value():
    tree = ast.parse(PANEL_PATH.read_text(encoding="utf-8"))
    dock_widget = _find_class(tree, "GitPDMDockWidget")
    method = _find_method(dock_widget, "_on_open_clone_repo_clicked")

    for call_node in ast.walk(method):
        if not isinstance(call_node, ast.Call):
            continue
        callee = call_node.func
        if isinstance(callee, ast.Name) and callee.id == "RepoPickerDialog":
            for kw in call_node.keywords:
                if kw.arg == "on_connect_requested":
                    return kw.value
    raise AssertionError(
        "RepoPickerDialog(...) call with on_connect_requested= not found in "
        "_on_open_clone_repo_clicked"
    )


class TestOpenCloneConnectCallbackResolves:
    def test_callback_is_not_the_removed_dock_widget_method(self):
        """Guards against the exact regression: pointing at a method that
        was moved off GitPDMDockWidget during the ConnectionsDialog split."""
        chain = _attribute_chain(_on_connect_requested_value())
        assert chain != "self._on_github_connect_clicked"

    def test_callback_resolves_to_a_real_connections_dialog_method(self):
        """The callback must be a zero-arg-callable attribute path rooted at
        `self._connections_dialog` (the dock widget's real, always-constructed
        ConnectionsDialog instance) that names a method that actually exists
        on that class."""
        chain = _attribute_chain(_on_connect_requested_value())
        prefix = "self._connections_dialog."
        assert chain.startswith(prefix), (
            f"on_connect_requested={chain!r} is not routed through the dock "
            "widget's _connections_dialog instance"
        )
        method_name = chain[len(prefix) :]
        assert "." not in method_name

        dialog_tree = ast.parse(CONNECTIONS_DIALOG_PATH.read_text(encoding="utf-8"))
        connections_dialog = _find_class(dialog_tree, "ConnectionsDialog")
        # Raises AssertionError with a clear message if the method is missing.
        _find_method(connections_dialog, method_name)
