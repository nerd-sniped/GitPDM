# -*- coding: utf-8 -*-
"""
Input Validation and Sanitization
Sprint SECURITY-5: Prevent injection attacks in repo operations

Validates and sanitizes user-controlled inputs that flow into:
- Repository names and owners
- File paths (commit operations, exports)
- Commit messages
- Branch names
- Git URLs

Security: Prevents command injection, path traversal, and other
injection attacks when working with Git and GitHub APIs.
"""

from __future__ import annotations

import re
import os
from pathlib import Path, PurePosixPath
from typing import Tuple, Optional


# Safe patterns for Git/GitHub identifiers
REPO_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")
OWNER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
BRANCH_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9/_.-]+$")

# Unsafe characters for commit messages (control chars, null bytes)
UNSAFE_COMMIT_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Maximum lengths to prevent DoS
MAX_REPO_NAME_LENGTH = 100
MAX_OWNER_NAME_LENGTH = 39  # GitHub username max
MAX_BRANCH_NAME_LENGTH = 255
MAX_COMMIT_MESSAGE_LENGTH = 50000  # GitHub API limit
MAX_PATH_COMPONENT_LENGTH = 255  # Filesystem limit


def validate_repo_name(name: str) -> Tuple[bool, str]:
    """
    Validate repository name for safety.

    Args:
        name: Repository name to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if not name:
        return False, "Repository name cannot be empty"

    if len(name) > MAX_REPO_NAME_LENGTH:
        return False, f"Repository name too long (max {MAX_REPO_NAME_LENGTH} chars)"

    if not REPO_NAME_PATTERN.match(name):
        return (
            False,
            "Repository name contains invalid characters (use only letters, numbers, dots, hyphens, underscores)",
        )

    # Prevent special cases
    if name in (".", "..", ".git"):
        return False, "Repository name is reserved"

    if name.startswith(".") or name.endswith("."):
        return False, "Repository name cannot start or end with a dot"

    return True, ""


def validate_owner_name(owner: str) -> Tuple[bool, str]:
    """
    Validate repository owner/username for safety.

    Args:
        owner: Owner/username to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if not owner:
        return False, "Owner name cannot be empty"

    if len(owner) > MAX_OWNER_NAME_LENGTH:
        return False, f"Owner name too long (max {MAX_OWNER_NAME_LENGTH} chars)"

    if not OWNER_NAME_PATTERN.match(owner):
        return (
            False,
            "Owner name contains invalid characters (use only letters, numbers, hyphens, underscores)",
        )

    if owner.startswith("-") or owner.endswith("-"):
        return False, "Owner name cannot start or end with a hyphen"

    return True, ""


def validate_branch_name(branch: str) -> Tuple[bool, str]:
    """
    Validate Git branch name for safety.

    Args:
        branch: Branch name to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if not branch:
        return False, "Branch name cannot be empty"

    if len(branch) > MAX_BRANCH_NAME_LENGTH:
        return False, f"Branch name too long (max {MAX_BRANCH_NAME_LENGTH} chars)"

    if not BRANCH_NAME_PATTERN.match(branch):
        return False, "Branch name contains invalid characters"

    # Git ref name restrictions
    if branch.startswith("/") or branch.endswith("/"):
        return False, "Branch name cannot start or end with slash"

    if branch.endswith(".lock"):
        return False, "Branch name cannot end with .lock"

    if ".." in branch or "@{" in branch:
        return False, "Branch name contains invalid sequences"

    return True, ""


def sanitize_commit_message(message: str) -> str:
    """
    Sanitize commit message by removing unsafe characters.

    Args:
        message: Raw commit message

    Returns:
        Sanitized commit message
    """
    if not message:
        return ""

    # Truncate to max length
    if len(message) > MAX_COMMIT_MESSAGE_LENGTH:
        message = message[:MAX_COMMIT_MESSAGE_LENGTH]

    # Remove control characters and null bytes
    sanitized = UNSAFE_COMMIT_CHARS.sub("", message)

    # Normalize line endings to \n
    sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")

    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()

    return sanitized


def validate_file_path(
    file_path: str, repo_root: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validate file path for safety (prevent path traversal).

    Args:
        file_path: File path to validate
        repo_root: Repository root path (optional, for absolute path validation)

    Returns:
        (is_valid, error_message) tuple
    """
    if not file_path:
        return False, "File path cannot be empty"

    try:
        # Convert to Path for normalization
        path = Path(file_path)

        # Check for path traversal attempts
        parts = path.parts
        if ".." in parts:
            return False, "File path contains parent directory references (..)"

        # Check component lengths
        for part in parts:
            if len(part) > MAX_PATH_COMPONENT_LENGTH:
                return (
                    False,
                    f"Path component too long (max {MAX_PATH_COMPONENT_LENGTH} chars)",
                )

        # If repo_root provided, ensure file is inside repo
        if repo_root:
            try:
                repo_path = Path(repo_root).resolve()
                file_abs = Path(file_path).resolve()

                # Check if file_abs is under repo_path
                try:
                    file_abs.relative_to(repo_path)
                except ValueError:
                    return False, "File path is outside repository"
            except (OSError, RuntimeError):
                return False, "Could not resolve file path"

        # Check for null bytes (common injection technique)
        if "\0" in file_path:
            return False, "File path contains null bytes"

        return True, ""

    except (ValueError, OSError) as e:
        return False, f"Invalid file path: {e}"


def validate_github_url(url: str) -> Tuple[bool, str]:
    """
    Validate GitHub URL for safety.

    Args:
        url: GitHub URL to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if not url:
        return False, "URL cannot be empty"

    # Must be HTTPS (never HTTP or git://)
    if not url.startswith("https://"):
        return False, "URL must use HTTPS"

    # Must be github.com or github enterprise instance
    # (for now, we only support github.com)
    if not url.startswith("https://github.com/"):
        return False, "URL must be a github.com URL"

    # Check for null bytes and control chars
    if "\0" in url or UNSAFE_COMMIT_CHARS.search(url):
        return False, "URL contains invalid characters"

    # Basic length check
    if len(url) > 2000:
        return False, "URL too long"

    return True, ""


def sanitize_for_shell_display(text: str, max_length: int = 200) -> str:
    """
    Sanitize text for safe display in shell/log output.

    Does NOT make text safe for shell execution - use proper
    argument passing (subprocess with list args) instead.

    Args:
        text: Text to sanitize
        max_length: Maximum length to display

    Returns:
        Sanitized text suitable for display only
    """
    if not text:
        return ""

    # Remove control characters
    sanitized = UNSAFE_COMMIT_CHARS.sub("", text)

    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def validate_full_repo_identifier(owner: str, name: str) -> Tuple[bool, str]:
    """
    Validate full repository identifier (owner/name).

    Args:
        owner: Repository owner
        name: Repository name

    Returns:
        (is_valid, error_message) tuple
    """
    valid_owner, owner_err = validate_owner_name(owner)
    if not valid_owner:
        return False, f"Invalid owner: {owner_err}"

    valid_name, name_err = validate_repo_name(name)
    if not valid_name:
        return False, f"Invalid repository name: {name_err}"

    return True, ""
