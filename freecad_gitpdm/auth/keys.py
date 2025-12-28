# -*- coding: utf-8 -*-
"""
GitPDM Credential Key Naming
Sprint OAUTH-0: Helper for OS credential storage key conventions

This module defines the naming convention for credential keys
stored in the OS credential manager (future sprint). No actual
storage happens in this sprint.
"""


def credential_target_name(host="github.com", account=None):
    """
    Generate credential storage target name for OAuth tokens.
    
    Args:
        host: GitHub host (default "github.com")
        account: GitHub username (optional, for multi-account)
        
    Returns:
        str: Target name for credential storage
        
    Examples:
        >>> credential_target_name()
        'GitPDM:github.com:oauth'
        >>> credential_target_name(account="octocat")
        'GitPDM:github.com:octocat:oauth'
        >>> credential_target_name(host="github.enterprise.com")
        'GitPDM:github.enterprise.com:oauth'
    """
    parts = ["GitPDM", host]
    if account:
        parts.append(account)
    parts.append("oauth")
    return ":".join(parts)
