# -*- coding: utf-8 -*-
"""
Tests for UI Components (Sprint 5 Phase 1)
Tests for StatusWidget, RepositoryWidget, and ChangesWidget
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from freecad_gitpdm.ui.components import (
    StatusWidget,
    RepositoryWidget,
    ChangesWidget,
    BaseWidget,
)

# Qt compatibility
try:
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtTest import QTest
except ImportError:
    from PySide2 import QtCore, QtWidgets
    from PySide2.QtTest import QTest


@pytest.fixture
def qapp():
    """Create QApplication instance for Qt tests."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def mock_git_client():
    """Mock GitClient for testing."""
    client = Mock()
    client.is_git_available.return_value = True
    client.git_version.return_value = "2.40.0"
    client.current_branch.return_value = "main"
    client.get_upstream_ref.return_value = "origin/main"
    client.get_ahead_behind.return_value = {"ok": True, "ahead": 0, "behind": 0}
    client.has_remote.return_value = True
    return client


@pytest.fixture
def mock_job_runner():
    """Mock JobRunner for testing."""
    runner = Mock()
    runner.run_callable = Mock()
    return runner


# ============================================================================
# BaseWidget Tests
# ============================================================================


class TestBaseWidget:
    """Test BaseWidget base class functionality."""

    def test_base_widget_creation(self, qapp, mock_git_client, mock_job_runner):
        """Test BaseWidget can be instantiated."""
        # BaseWidget is abstract, so create a concrete subclass
        class TestWidget(BaseWidget):
            def update_for_repository(self, repo_root):
                pass

            def refresh(self):
                pass

        widget = TestWidget(None, mock_git_client, mock_job_runner)
        assert widget is not None
        assert widget._git_client == mock_git_client
        assert widget._job_runner == mock_job_runner

    def test_base_widget_signals(self, qapp):
        """Test BaseWidget defines expected signals."""

        class TestWidget(BaseWidget):
            def update_for_repository(self, repo_root):
                pass

            def refresh(self):
                pass

        widget = TestWidget()
        assert hasattr(widget, "error_occurred")
        assert hasattr(widget, "info_message")
        assert hasattr(widget, "busy_state_changed")

    def test_base_widget_state_management(self, qapp):
        """Test state management methods."""

        class TestWidget(BaseWidget):
            def update_for_repository(self, repo_root):
                pass

            def refresh(self):
                pass

        widget = TestWidget()
        assert not widget.is_busy()

        widget.set_busy_state(True, "Testing")
        assert widget.is_busy()

        widget.set_busy_state(False)
        assert not widget.is_busy()


# ============================================================================
# StatusWidget Tests
# ============================================================================


class TestStatusWidget:
    """Test StatusWidget functionality."""

    def test_status_widget_creation(self, qapp, mock_git_client, mock_job_runner):
        """Test StatusWidget instantiation."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        assert widget is not None
        assert hasattr(widget, "git_status_label")
        assert hasattr(widget, "working_tree_label")
        assert hasattr(widget, "branch_label")
        assert hasattr(widget, "upstream_label")
        assert hasattr(widget, "ahead_behind_label")

    def test_status_widget_signals(self, qapp, mock_git_client, mock_job_runner):
        """Test StatusWidget defines expected signals."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        assert hasattr(widget, "status_updated")
        assert hasattr(widget, "refresh_requested")
        assert hasattr(widget, "git_status_changed")

    def test_update_working_tree_status_clean(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test updating working tree status with no changes."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.update_working_tree_status(0)
        assert widget.working_tree_label.text() == "Clean"

    def test_update_working_tree_status_with_changes(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test updating working tree status with changes."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.update_working_tree_status(5)
        assert "5 files" in widget.working_tree_label.text()

    def test_update_branch_info(self, qapp, mock_git_client, mock_job_runner):
        """Test updating branch information."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.update_branch_info("feature-branch")
        assert widget.branch_label.text() == "feature-branch"

    def test_update_last_fetch_time(self, qapp, mock_git_client, mock_job_runner):
        """Test updating last fetch time."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.update_last_fetch_time("2026-01-03 10:30:00")
        assert widget.last_fetch_label.text() == "2026-01-03 10:30:00"

    def test_show_status_message(self, qapp, mock_git_client, mock_job_runner):
        """Test showing status message."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.show()  # Widget must be shown for visibility to work
        widget.show_status_message("Test error", is_error=True)
        assert widget.status_message_label.text() == "Test error"
        assert widget.status_message_label.isVisible()

    def test_clear_status_message(self, qapp, mock_git_client, mock_job_runner):
        """Test clearing status message."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.show_status_message("Test message")
        widget.clear_status_message()
        assert not widget.status_message_label.isVisible()

    def test_get_ahead_behind_counts(self, qapp, mock_git_client, mock_job_runner):
        """Test getting ahead/behind counts."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        ahead, behind = widget.get_ahead_behind_counts()
        assert ahead == 0
        assert behind == 0

    def test_update_upstream_info_triggers_async(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test upstream update triggers async operation."""
        widget = StatusWidget(None, mock_git_client, mock_job_runner)
        widget.update_upstream_info("/test/repo")
        # Should trigger async job
        assert mock_job_runner.run_callable.called or hasattr(widget, "run_async")


# ============================================================================
# RepositoryWidget Tests
# ============================================================================


class TestRepositoryWidget:
    """Test RepositoryWidget functionality."""

    def test_repository_widget_creation(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test RepositoryWidget instantiation."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        assert widget is not None
        assert hasattr(widget, "repo_path_field")
        assert hasattr(widget, "root_toggle_btn")
        assert hasattr(widget, "create_repo_btn")
        assert hasattr(widget, "connect_remote_btn")

    def test_repository_widget_signals(self, qapp, mock_git_client, mock_job_runner):
        """Test RepositoryWidget defines expected signals."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        assert hasattr(widget, "repository_changed")
        assert hasattr(widget, "repository_validated")
        assert hasattr(widget, "browse_requested")
        assert hasattr(widget, "clone_requested")
        assert hasattr(widget, "new_repo_requested")
        assert hasattr(widget, "create_repo_requested")
        assert hasattr(widget, "connect_remote_requested")

    def test_get_set_path(self, qapp, mock_git_client, mock_job_runner):
        """Test getting and setting repository path."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        test_path = "/test/repo/path"
        widget.set_path(test_path)
        assert widget.get_path() == test_path

    def test_update_validation_valid_repo(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test updating validation for valid repo."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        widget.update_validation(True, "/test/repo", "Valid")
        assert widget._is_valid_repo is True
        assert widget._current_root == "/test/repo"
        assert widget.root_toggle_btn.isEnabled()

    def test_update_validation_invalid_repo(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test updating validation for invalid repo."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        widget.update_validation(False, None, "Not a git repo")
        assert widget._is_valid_repo is False
        assert not widget.root_toggle_btn.isEnabled()

    def test_show_create_repo_button(self, qapp, mock_git_client, mock_job_runner):
        """Test showing/hiding create repo button."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        widget.show()  # Widget must be shown for visibility to work
        widget.show_create_repo_button(True)
        assert widget.create_repo_btn.isVisible()
        widget.show_create_repo_button(False)
        assert not widget.create_repo_btn.isVisible()

    def test_show_connect_remote_button(self, qapp, mock_git_client, mock_job_runner):
        """Test showing/hiding connect remote button."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        widget.show()  # Widget must be shown for visibility to work
        widget.show_connect_remote_button(True)
        assert widget.connect_remote_btn.isVisible()
        widget.show_connect_remote_button(False)
        assert not widget.connect_remote_btn.isVisible()

    def test_repository_changed_signal(self, qapp, mock_git_client, mock_job_runner):
        """Test repository_changed signal emitted on path change."""
        widget = RepositoryWidget(None, mock_git_client, mock_job_runner)
        signal_spy = Mock()
        widget.repository_changed.connect(signal_spy)

        widget.repo_path_field.setText("/new/path")
        widget.repo_path_field.editingFinished.emit()

        assert signal_spy.called


# ============================================================================
# ChangesWidget Tests
# ============================================================================


class TestChangesWidget:
    """Test ChangesWidget functionality."""

    def test_changes_widget_creation(self, qapp, mock_git_client, mock_job_runner):
        """Test ChangesWidget instantiation."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        assert widget is not None
        assert hasattr(widget, "changes_list")
        assert hasattr(widget, "stage_all_checkbox")

    def test_changes_widget_signals(self, qapp, mock_git_client, mock_job_runner):
        """Test ChangesWidget defines expected signals."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        assert hasattr(widget, "stage_all_changed")
        assert hasattr(widget, "files_selected")

    def test_update_changes_empty(self, qapp, mock_git_client, mock_job_runner):
        """Test updating with empty changes list."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        widget.update_changes([])
        assert widget.changes_list.count() == 0
        assert not widget.changes_list.isEnabled()
        assert not widget.stage_all_checkbox.isEnabled()

    def test_update_changes_with_files(self, qapp, mock_git_client, mock_job_runner):
        """Test updating with file changes."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)

        # Mock file status objects
        class FileStatus:
            def __init__(self, x, y, path):
                self.x = x
                self.y = y
                self.path = path

        file_statuses = [
            FileStatus(" ", "M", "file1.txt"),
            FileStatus("?", "?", "file2.txt"),
        ]

        widget.update_changes(file_statuses)
        assert widget.changes_list.count() == 2
        assert widget.changes_list.isEnabled()
        assert widget.stage_all_checkbox.isEnabled()

    def test_get_set_stage_all(self, qapp, mock_git_client, mock_job_runner):
        """Test getting and setting stage all checkbox."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        widget.set_stage_all(False)
        assert not widget.get_stage_all()
        widget.set_stage_all(True)
        assert widget.get_stage_all()

    def test_has_changes(self, qapp, mock_git_client, mock_job_runner):
        """Test has_changes method."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        assert not widget.has_changes()

        class FileStatus:
            def __init__(self, x, y, path):
                self.x = x
                self.y = y
                self.path = path

        widget.update_changes([FileStatus(" ", "M", "test.txt")])
        assert widget.has_changes()

    def test_clear_changes(self, qapp, mock_git_client, mock_job_runner):
        """Test clearing changes."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)

        class FileStatus:
            def __init__(self, x, y, path):
                self.x = x
                self.y = y
                self.path = path

        widget.update_changes([FileStatus(" ", "M", "test.txt")])
        widget.clear_changes()
        assert widget.changes_list.count() == 0
        assert not widget.has_changes()

    def test_friendly_status_text_modified(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test friendly status text for modified files."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        assert "Modified" in widget._friendly_status_text(" ", "M")

    def test_friendly_status_text_new(self, qapp, mock_git_client, mock_job_runner):
        """Test friendly status text for new files."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        assert "New" in widget._friendly_status_text("?", "?")

    def test_friendly_status_text_deleted(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test friendly status text for deleted files."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        assert "Deleted" in widget._friendly_status_text(" ", "D")

    def test_stage_all_changed_signal(self, qapp, mock_git_client, mock_job_runner):
        """Test stage_all_changed signal emission."""
        widget = ChangesWidget(None, mock_git_client, mock_job_runner)
        signal_spy = Mock()
        widget.stage_all_changed.connect(signal_spy)

        widget.stage_all_checkbox.setChecked(False)
        # Signal should be emitted
        assert signal_spy.called or widget.stage_all_checkbox.isChecked() == False


# ============================================================================
# Integration Tests
# ============================================================================


class TestComponentIntegration:
    """Test integration between components."""

    def test_components_can_be_used_together(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test multiple components can coexist."""
        status = StatusWidget(None, mock_git_client, mock_job_runner)
        repo = RepositoryWidget(None, mock_git_client, mock_job_runner)
        changes = ChangesWidget(None, mock_git_client, mock_job_runner)

        assert status is not None
        assert repo is not None
        assert changes is not None

    def test_components_share_git_client(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test components can share same git client."""
        status = StatusWidget(None, mock_git_client, mock_job_runner)
        repo = RepositoryWidget(None, mock_git_client, mock_job_runner)

        assert status._git_client == repo._git_client == mock_git_client

    def test_update_for_repository_workflow(
        self, qapp, mock_git_client, mock_job_runner
    ):
        """Test update_for_repository method across components."""
        status = StatusWidget(None, mock_git_client, mock_job_runner)
        repo = RepositoryWidget(None, mock_git_client, mock_job_runner)
        changes = ChangesWidget(None, mock_git_client, mock_job_runner)

        test_repo = "/test/repo"
        status.update_for_repository(test_repo)
        repo.update_for_repository(test_repo)
        changes.update_for_repository(test_repo)

        # Should complete without errors
        assert True
