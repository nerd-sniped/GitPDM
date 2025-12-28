# -*- coding: utf-8 -*-
"""
GitHub REST API Client (stdlib-only)
Sprint OAUTH-2: Identity verification + session handling

Implements a minimal JSON client using urllib.request.
Security: never logs Authorization headers or tokens.
"""

from __future__ import annotations

import json
import ssl
import socket
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from urllib import request, error

from freecad_gitpdm.core import log


class GitHubApiError(Exception):
    """Base error for GitHub API client."""


class GitHubApiNetworkError(GitHubApiError):
    """Network-related error (timeout, DNS, SSL)."""


@dataclass
class _Response:
    status: int
    json: Optional[Dict[str, Any]]
    headers: Dict[str, str]


class GitHubApiClient:
    """
    Minimal GitHub JSON client.

    - Base URL: https://api.github.com
    - Headers include User-Agent and Accept
    - Authorization bearer token added when provided
    - Robust error handling and JSON parsing
    """

    def __init__(self, host: str, token: str, user_agent: str):
        self._base_url = f"https://{host}"
        # If host is api.github.com or enterprise API base differs, callers
        # should pass host="api.github.com"; we still prefix https://
        self._token = token or ""
        self._user_agent = user_agent or "GitPDM/1.0"

    def request_json(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]],
        body: Optional[Dict[str, Any]],
        timeout_s: int,
    ) -> Tuple[int, Optional[Dict[str, Any]], Dict[str, str]]:
        """
        Perform an HTTP request and return status, parsed JSON (or None), and headers.

        - Does not log Authorization headers.
        - Network errors raise GitHubApiNetworkError.
        - JSON parse errors are handled gracefully (json=None).
        """
        # Compose absolute URL if relative path provided
        target = url
        if url.startswith("/"):
            # For GitHub REST, base should be https://api.github.com
            base = self._base_url
            if not base.endswith("/api.github.com") and base.endswith("api.github.com"):
                # Common case: host="api.github.com"
                pass
            target = f"https://api.github.com{url}"
        elif url.startswith("http://") or url.startswith("https://"):
            target = url
        else:
            # Treat as path
            target = f"https://api.github.com/{url.lstrip('/')}"

        req_headers: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self._user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            # Do NOT log or expose this header
            req_headers["Authorization"] = f"Bearer {self._token}"

        # Merge caller-provided non-sensitive headers (excluding Authorization)
        if headers:
            for k, v in headers.items():
                if k.lower() == "authorization":
                    # Ignore to avoid accidental leaks
                    continue
                req_headers[k] = v

        data: Optional[bytes] = None
        if body is not None:
            try:
                data = json.dumps(body).encode("utf-8")
                req_headers["Content-Type"] = "application/json"
            except Exception as e:
                raise GitHubApiError(f"Invalid JSON body: {e}")

        req = request.Request(target, data=data, method=(method or "GET").upper())
        for k, v in req_headers.items():
            # Authorization header set on req directly without logging
            req.add_header(k, v)

        try:
            # Use default SSL context (verify certificates)
            ctx = ssl.create_default_context()
            with request.urlopen(req, timeout=float(timeout_s), context=ctx) as resp:
                status = getattr(resp, "status", 0)
                raw_headers = {k: v for k, v in resp.headers.items()}
                raw = resp.read()
        except error.HTTPError as e:
            status = e.code
            raw_headers = {k: v for k, v in getattr(e, "headers", {}).items()} if getattr(e, "headers", None) else {}
            raw = e.read() if hasattr(e, "read") else b""
        except (error.URLError, ssl.SSLError, socket.timeout) as e:
            # Map to friendly network error
            raise GitHubApiNetworkError(str(e)) from e

        # Parse JSON if possible; handle gracefully
        parsed: Optional[Dict[str, Any]] = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception:
                parsed = None

        # Never log raw headers containing Authorization; we didn't add to raw_headers
        # Log only status for debug
        log.debug(f"GitHub API {method} {target} -> {status}")

        return status, parsed, raw_headers
