# -*- coding: utf-8 -*-
"""
Tests for core.settings module - FCStd git-friendly compression handling
"""

from unittest.mock import call

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


class TestCompressionScope:
    """
    Test the G3 scoped compression enter/exit pair (core/settings.py),
    which replaced the old ensure_git_friendly_fcstd_compression() that
    silently flipped the global preference with no way to restore it
    (R1.2 regression fix).
    """

    def test_enter_scope_sets_level_and_records_prior(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = False  # scope not active yet
        param_group.GetInt.return_value = 3

        settings.enter_git_friendly_compression_scope()

        param_group.SetInt.assert_called_once_with("CompressionLevel", 0)
        param_group.SetString.assert_any_call(settings._PRIOR_COMPRESSION_KEY, "3")
        param_group.SetBool.assert_any_call(
            settings._COMPRESSION_SCOPE_ACTIVE_KEY, True
        )

    def test_enter_scope_is_idempotent_when_already_zero(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = False
        param_group.GetInt.return_value = 0

        settings.enter_git_friendly_compression_scope()

        param_group.SetInt.assert_not_called()

    def test_enter_scope_does_not_reread_prior_when_already_active(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = True  # scope already active
        param_group.GetInt.return_value = 3

        settings.enter_git_friendly_compression_scope()

        # Must not clobber the already-recorded prior value
        assert (
            call(settings._PRIOR_COMPRESSION_KEY, "3")
            not in param_group.SetString.call_args_list
        )

    def test_enter_scope_swallows_errors(self, mock_freecad):
        mock_freecad.ParamGet.side_effect = Exception("boom")

        # Should not raise
        settings.enter_git_friendly_compression_scope()

    def test_exit_scope_restores_prior_value(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = True
        param_group.GetString.return_value = "3"

        settings.exit_git_friendly_compression_scope()

        param_group.SetInt.assert_called_once_with("CompressionLevel", 3)
        param_group.SetBool.assert_any_call(
            settings._COMPRESSION_SCOPE_ACTIVE_KEY, False
        )

    def test_exit_scope_is_noop_when_not_active(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = False

        settings.exit_git_friendly_compression_scope()

        param_group.SetInt.assert_not_called()

    def test_recover_stuck_scope_restores_when_active(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = True
        param_group.GetString.return_value = "3"

        settings.recover_stuck_compression_scope()

        param_group.SetInt.assert_called_once_with("CompressionLevel", 3)

    def test_recover_stuck_scope_is_noop_when_not_active(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = False

        settings.recover_stuck_compression_scope()

        param_group.SetInt.assert_not_called()
