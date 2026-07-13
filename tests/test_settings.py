# -*- coding: utf-8 -*-
"""
Tests for core.settings module - FCStd git-friendly compression handling
"""

from freecad_gitpdm.core import settings


class TestFcstdCompressionLevel:
    """Test reading/writing FreeCAD's document compression preference"""

    def test_get_fcstd_compression_level_returns_current_value(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetInt.return_value = 3

        level = settings.get_fcstd_compression_level()

        mock_freecad.ParamGet.assert_called_with(settings.DOCUMENT_PARAM_GROUP_PATH)
        param_group.GetInt.assert_called_with("CompressionLevel", 3)
        assert level == 3

    def test_get_fcstd_compression_level_handles_errors(self, mock_freecad):
        mock_freecad.ParamGet.side_effect = Exception("boom")

        assert settings.get_fcstd_compression_level() is None

    def test_ensure_git_friendly_sets_level_when_not_zero(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetInt.return_value = 3

        settings.ensure_git_friendly_fcstd_compression()

        param_group.SetInt.assert_called_once_with("CompressionLevel", 0)

    def test_ensure_git_friendly_is_idempotent(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetInt.return_value = 0

        settings.ensure_git_friendly_fcstd_compression()

        param_group.SetInt.assert_not_called()

    def test_ensure_git_friendly_swallows_errors(self, mock_freecad):
        mock_freecad.ParamGet.side_effect = Exception("boom")

        # Should not raise
        settings.ensure_git_friendly_fcstd_compression()
