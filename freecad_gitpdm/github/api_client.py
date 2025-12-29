# -*- coding: utf-8 -*-
"""
GitHub REST API Client (stdlib-only)
Sprint OAUTH-2: Identity verification + session handling
Sprint OAUTH-6: Retry logic, rate limit handling, structured errors

Implements a minimal JSON client using urllib.request with:
- Structured error classification (via errors.py)
- Safe retry policy (transient errors only)
- Rate limit parsing and guidance
- No token/credential exposure in logs

Security: never logs Authorization headers or tokens.
"""

from __future__ import annotations

import json
import ssl
import socket
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from urllib import request, error

from freecad_gitpdm.core import log
from freecad_gitpdm.github.errors import GitHubApiError, GitHubApiNetworkError


@dataclass
class _Response:
    status: int
    json: Optional[Dict[str, Any]]
    headers: Dict[str, str]


class GitHubApiClient:
    """
    Minimal GitHub JSON client with retry and rate limit handling.

    - Base URL: https://api.github.com
    - Headers include User-Agent and Accept
    - Authorization bearer token added when provided
    - Retry policy: max 3 attempts, exponential backoff (0.5s, 1.0s, 2.0s)
    - Rate limit parsing: provides reset time to caller
    - Robust error handling and JSON parsing
    - Never exposes tokens or Authorization headers in logs
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF = [0.5, 1.0, 2.0]  # seconds for attempt 1, 2, 3
    
    # Error codes that should NOT be retried (non-transient)
    NO_RETRY_CODES = {401, 403, 422, 400}

    def __init__(self, host: str, token: str, user_agent: str):
        self._base_url = f"https://{host}"
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
        Perform an HTTP request with retry logic.
        
        Returns:
            (status, parsed_json, headers) tuple
            
        Raises:
            GitHubApiError: For HTTP errors with classified code (after retries exhausted)
            GitHubApiNetworkError: For network-level errors (after retries exhausted)
        """
        attempt = 0
        last_error: Optional[Exception] = None
        
        while attempt < self.MAX_RETRIES:
            try:
                status, body_data, resp_headers = self._request_json_once(
                    method, url, headers, body, timeout_s
                )
                
                # Check if we should retry based on status
                if status not in self.NO_RETRY_CODES and status >= 500:
                    # Transient error (5xx), could retry
                    if attempt < self.MAX_RETRIES - 1:
                        wait_s = self.RETRY_BACKOFF[attempt]
                        log.debug(
                            f"GitHub API {status}, retrying after {wait_s}s "
                            f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                        )
                        time.sleep(wait_s)
                        attempt += 1
                        continue
                
                # Success or non-retryable error
                return status, body_data, resp_headers
                
            except GitHubApiNetworkError as e:
                # Network errors are potentially transient; retry
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_s = self.RETRY_BACKOFF[attempt]
                    log.debug(
                        f"GitHub network error, retrying after {wait_s}s: {e.message}"
                    )
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                # Exhausted retries
                raise e
                
            except GitHubApiError as e:
                # Non-transient errors are not retried
                if e.code not in ("NETWORK", "TIMEOUT"):
                    raise e
                # If NETWORK/TIMEOUT but max retries reached
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_s = self.RETRY_BACKOFF[attempt]
                    log.debug(
                        f"GitHub transient error, retrying after {wait_s}s: {e.message}"
                    )
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                raise e
        
        # Should not reach here, but handle just in case
        if last_error:
            raise last_error
        raise GitHubApiError(
            code="UNKNOWN",
            message="Request failed after retries.",
            details="Max retry attempts exhausted"
        )

    def _request_json_once(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]],
        body: Optional[Dict[str, Any]],
        timeout_s: int,
    ) -> Tuple[int, Optional[Dict[str, Any]], Dict[str, str]]:
        """
        Perform a single HTTP request without retry logic.
        
        Raises:
            GitHubApiError: For HTTP errors
            GitHubApiNetworkError: For network-level errors
        """
        # Compose absolute URL if relative path provided
        target = url
        if url.startswith("/"):
            target = f"https://api.github.com{url}"
        elif url.startswith("http://") or url.startswith("https://"):
            target = url
        else:
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
                raise GitHubApiError(
                    code="BAD_RESPONSE",
                    message="Failed to prepare request.",
                    details=str(e)
                )

        req = request.Request(target, data=data, method=(method or "GET").upper())
        for k, v in req_headers.items():
            # Authorization header set on req directly without logging
            req.add_header(k, v)

        # Perform HTTP request
        status = 0
        raw_headers: Dict[str, str] = {}
        raw: bytes = b""
        
        try:
            ctx = ssl.create_default_context()
            with request.urlopen(req, timeout=float(timeout_s), context=ctx) as resp:
                status = getattr(resp, "status", 0)
                raw_headers = {k: v for k, v in resp.headers.items()}
                raw = resp.read()
        except error.HTTPError as e:
            status = e.code
            raw_headers = {k: v for k, v in getattr(e, "headers", {}).items()} if getattr(e, "headers", None) else {}
            raw = e.read() if hasattr(e, "read") else b""
        except (error.URLError, ssl.SSLError, socket.timeout, socket.error) as e:
            # Map to friendly network error
            raise GitHubApiNetworkError(str(e)) from e

        # Parse JSON if possible
        parsed: Optional[Dict[str, Any]] = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception as e:
                # JSON parse error; don't fail, just log
                log.debug(f"GitHub API response parse error: {e}")
                parsed = None

        # Log status only (never logs Authorization)
        log.debug(f"GitHub API {method} {url} -> {status}")

        # Check for HTTP errors and raise if needed
        if status < 200 or status >= 300:
            raise GitHubApiError.from_http_error(
                status, raw_headers, raw.decode("utf-8", errors="replace")
            )

        return status, parsed, raw_headers
