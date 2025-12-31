# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures for GitPDM tests
"""

import sys
from unittest.mock import MagicMock
import pytest


@pytest.fixture(autouse=True)
def mock_freecad():
    """Auto-mock FreeCAD module for all tests"""
    # Create mock FreeCAD module
    freecad_mock = MagicMock()
    freecad_mock.Version.return_value = ["0", "21", "0", "12345"]
    freecad_mock.ParamGet.return_value = MagicMock()

    # Mock Console
    console_mock = MagicMock()
    freecad_mock.Console = console_mock

    # Inject into sys.modules
    sys.modules["FreeCAD"] = freecad_mock
    sys.modules["FreeCADGui"] = MagicMock()

    yield freecad_mock

    # Cleanup (optional, but good practice)
    if "FreeCAD" in sys.modules:
        del sys.modules["FreeCAD"]
    if "FreeCADGui" in sys.modules:
        del sys.modules["FreeCADGui"]


@pytest.fixture
def mock_qt():
    """Mock Qt modules"""
    pyside_mock = MagicMock()
    sys.modules["PySide6"] = pyside_mock
    sys.modules["PySide6.QtCore"] = MagicMock()
    sys.modules["PySide6.QtWidgets"] = MagicMock()
    sys.modules["PySide6.QtGui"] = MagicMock()

    yield pyside_mock

    for module in ["PySide6", "PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui"]:
        if module in sys.modules:
            del sys.modules[module]


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository for testing"""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    return repo_path


@pytest.fixture
def sample_token():
    """Sample OAuth token for testing"""
    return {
        "access_token": "ghp_test_token_12345",
        "token_type": "bearer",
        "scope": "repo read:user",
    }
