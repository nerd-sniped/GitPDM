# -*- coding: utf-8 -*-
"""
GitPDM Settings Module
Sprint 0: Persist settings using FreeCAD parameter store
"""

import FreeCAD
from freecad_gitpdm.core import log

# Parameter group path in FreeCAD's parameter tree
PARAM_GROUP_PATH = "User parameter:BaseApp/Preferences/Mod/GitPDM"


def get_param_group():
    """
    Get the FreeCAD parameter group for GitPDM settings
    
    Returns:
        ParameterGrp object for GitPDM settings
    """
    return FreeCAD.ParamGet(PARAM_GROUP_PATH)


def save_repo_path(path):
    """
    Save the repository path to persistent storage
    
    Args:
        path: Repository path string
    """
    try:
        param_group = get_param_group()
        param_group.SetString("RepoPath", path)
        log.info(f"Saved repo path: {path}")
    except Exception as e:
        log.error(f"Failed to save repo path: {e}")


def load_repo_path():
    """
    Load the repository path from persistent storage
    
    Returns:
        Repository path string (empty if not set)
    """
    try:
        param_group = get_param_group()
        path = param_group.GetString("RepoPath", "")
        if path:
            log.info(f"Loaded repo path: {path}")
        return path
    except Exception as e:
        log.error(f"Failed to load repo path: {e}")
        return ""


def save_setting(key, value):
    """
    Save a generic string setting
    
    Args:
        key: Setting key name
        value: Setting value (string)
    """
    try:
        param_group = get_param_group()
        param_group.SetString(key, str(value))
        log.debug(f"Saved setting {key}={value}")
    except Exception as e:
        log.error(f"Failed to save setting {key}: {e}")


def load_setting(key, default=""):
    """
    Load a generic string setting
    
    Args:
        key: Setting key name
        default: Default value if not found
        
    Returns:
        Setting value string
    """
    try:
        param_group = get_param_group()
        return param_group.GetString(key, default)
    except Exception as e:
        log.error(f"Failed to load setting {key}: {e}")
        return default


def save_bool_setting(key, value):
    """
    Save a boolean setting
    
    Args:
        key: Setting key name
        value: Boolean value
    """
    try:
        param_group = get_param_group()
        param_group.SetBool(key, bool(value))
        log.debug(f"Saved bool setting {key}={value}")
    except Exception as e:
        log.error(f"Failed to save bool setting {key}: {e}")


def load_bool_setting(key, default=False):
    """
    Load a boolean setting
    
    Args:
        key: Setting key name
        default: Default value if not found
        
    Returns:
        Boolean value
    """
    try:
        param_group = get_param_group()
        return param_group.GetBool(key, default)
    except Exception as e:
        log.error(f"Failed to load bool setting {key}: {e}")
        return default
