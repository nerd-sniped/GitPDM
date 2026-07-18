# -*- coding: utf-8 -*-
"""
Generic stdlib-only (no `requests` dependency) JSON REST client with retry,
rate limiting, and circuit breaking, shared across provider API clients.

Extracted from `providers/github/api_client.py`'s `GitHubApiClient` (left
untouched, to avoid any regression risk to the one fully-verified
provider). One bug from the original is fixed here rather than replicated:
GitHub's client took a `host` constructor argument but then hardcoded
`https://api.github.com` in its URL-resolution logic instead of actually
using it — this class uses `self._base_url` for real, which matters once
`base_url` varies per host (GitLab, a self-hosted Gitea instance, ...).

Subclasses customize:
- `error_cls` — the `ProviderApiError` subclass to raise/return (each host
  gets its own for host-specific `from_http_error` status-code mapping).
- `provider_id` — prefixes the rate-limiter's `user_id` so per-user buckets
  don't collide across hosts on the shared process-wide `RateLimiter`.
- `_auth_headers()` — override if the host doesn't use
  `Authorization: Bearer <token>` (e.g. GitLab wants `PRIVATE-TOKEN`).
- `_default_headers()` — override to add Accept/API-version headers.
"""

from __future__ import annotations

import json
import ssl
import socket
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Type

from urllib import request, error

from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result
from freecad_gitpdm.providers.shared.errors import (
    ProviderApiError,
    ProviderApiNetworkError,
)
from freecad_gitpdm.providers.shared.rate_limiter import RateLimiter


@dataclass
class _Response:
    status: int
    json: Optional[Dict[str, Any]]
    headers: Dict[str, str]


class BaseApiClient:
    """
    Minimal JSON REST client with retry and rate-limit handling, generic
    across hosts. See module docstring for the subclass hooks.
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF = [0.5, 1.0, 2.0]  # seconds for attempt 1, 2, 3
    NO_RETRY_CODES = {401, 403, 422, 400}

    error_cls: Type[ProviderApiError] = ProviderApiError
    provider_id: str = "base"

    def __init__(self, base_url: str, token: str, user_agent: str = "GitPDM/1.0"):
        self._base_url = (base_url or "").rstrip("/")
        self._token = token or ""
        self._user_agent = user_agent or "GitPDM/1.0"
        self._rate_limiter = RateLimiter.get_instance()
        # Per-provider-prefixed, privacy-preserving user key for rate
        # limiting (hash of the token, never the token itself).
        token_key = str(hash(self._token))[:16] if self._token else "anonymous"
        self._user_id = f"{self.provider_id}:{token_key}"

    # ---- Hooks for subclasses ----

    def _auth_headers(self) -> Dict[str, str]:
        """Default: `Authorization: Bearer <token>`. Override per host."""
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def _default_headers(self) -> Dict[str, str]:
        """Extra headers sent on every request (Accept, API-version, ...)."""
        return {}

    # ---- Request machinery ----

    def request_json(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]],
        body: Optional[Dict[str, Any]],
        timeout_s: int,
    ) -> Tuple[int, Optional[Dict[str, Any]], Dict[str, str]]:
        """
        Perform an HTTP request with retry logic and rate limiting.

        Returns (status, parsed_json, headers).
        Raises `self.error_cls` (network or HTTP errors) after retries
        are exhausted.
        """
        if not self._rate_limiter.can_proceed(user_id=self._user_id):
            wait_s = self._rate_limiter.wait_time(user_id=self._user_id)
            log.debug(f"Rate limit reached, waiting {wait_s:.1f}s")
            raise self.error_cls(
                code="RATE_LIMITED",
                message=f"Rate limit exceeded. Retry after {wait_s:.0f}s.",
                details="Per-user rate limit enforced to prevent abuse",
                retry_after_s=int(wait_s) + 1,
            )

        if self._rate_limiter.is_circuit_open(user_id=self._user_id):
            log.debug(f"Circuit breaker open for user {self._user_id[:8]}...")
            raise self.error_cls(
                code="SERVICE_UNAVAILABLE",
                message="API temporarily unavailable. Please retry later.",
                details="Circuit breaker tripped due to repeated failures",
                retry_after_s=30,
            )

        attempt = 0
        last_error: Optional[Exception] = None

        while attempt < self.MAX_RETRIES:
            try:
                status, body_data, resp_headers = self._request_json_once(
                    method, url, headers, body, timeout_s
                )

                if status not in self.NO_RETRY_CODES and status >= 500:
                    self._rate_limiter.record_failure(user_id=self._user_id)
                    if attempt < self.MAX_RETRIES - 1:
                        wait_s = self.RETRY_BACKOFF[attempt]
                        log.debug(
                            f"API {status}, retrying after {wait_s}s "
                            f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                        )
                        time.sleep(wait_s)
                        attempt += 1
                        continue

                if status in (403, 429):
                    retry_after = resp_headers.get(
                        "Retry-After", resp_headers.get("retry-after")
                    )
                    if retry_after:
                        self._rate_limiter.record_failure(user_id=self._user_id)
                        log.debug(
                            f"Secondary rate limit hit, retry after {retry_after}s"
                        )

                if 200 <= status < 300:
                    self._rate_limiter.record_success(user_id=self._user_id)

                return status, body_data, resp_headers

            except ProviderApiNetworkError as e:
                self._rate_limiter.record_failure(user_id=self._user_id)
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_s = self.RETRY_BACKOFF[attempt]
                    log.debug(f"Network error, retrying after {wait_s}s: {e.message}")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                raise e

            except self.error_cls as e:
                if e.code not in ("NETWORK", "TIMEOUT"):
                    raise e
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait_s = self.RETRY_BACKOFF[attempt]
                    log.debug(f"Transient error, retrying after {wait_s}s: {e.message}")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                raise e

        if last_error:
            raise last_error
        raise self.error_cls(
            code="UNKNOWN",
            message="Request failed after retries.",
            details="Max retry attempts exhausted",
        )

    def _resolve_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("/"):
            return f"{self._base_url}{url}"
        return f"{self._base_url}/{url}"

    def _request_json_once(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]],
        body: Optional[Dict[str, Any]],
        timeout_s: int,
    ) -> Tuple[int, Optional[Dict[str, Any]], Dict[str, str]]:
        """Perform a single HTTP request without retry logic."""
        target = self._resolve_url(url)

        req_headers: Dict[str, str] = {"User-Agent": self._user_agent}
        req_headers.update(self._default_headers())
        # Auth headers set directly on the request without logging.
        req_headers.update(self._auth_headers())

        if headers:
            for k, v in headers.items():
                if k.lower() == "authorization":
                    # Ignore caller-supplied Authorization to avoid
                    # accidentally overriding/leaking the real one.
                    continue
                req_headers[k] = v

        data: Optional[bytes] = None
        if body is not None:
            try:
                data = json.dumps(body).encode("utf-8")
                req_headers["Content-Type"] = "application/json"
            except Exception as e:
                from freecad_gitpdm.core.log import _redact_sensitive

                raise self.error_cls(
                    code="BAD_RESPONSE",
                    message="Failed to prepare request.",
                    details=_redact_sensitive(str(e)),
                )

        req = request.Request(target, data=data, method=(method or "GET").upper())
        for k, v in req_headers.items():
            req.add_header(k, v)

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
            raw_headers = (
                {k: v for k, v in getattr(e, "headers", {}).items()}
                if getattr(e, "headers", None)
                else {}
            )
            raw = e.read() if hasattr(e, "read") else b""
        except (error.URLError, ssl.SSLError, socket.timeout, socket.error) as e:
            raise ProviderApiNetworkError(str(e)) from e

        parsed: Optional[Dict[str, Any]] = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception as e:
                log.debug(f"API response parse error: {e}")
                parsed = None

        log.debug(f"API {method} {url} -> {status}")

        if status < 200 or status >= 300:
            raise self.error_cls.from_http_error(
                status, raw_headers, raw.decode("utf-8", errors="replace")
            )

        return status, parsed, raw_headers

    def request_json_result(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]],
        body: Optional[Dict[str, Any]],
        timeout_s: int,
    ) -> Result[Tuple[int, Optional[Dict[str, Any]], Dict[str, str]]]:
        """Result-returning wrapper around request_json, so exceptions never
        propagate into UI code."""
        try:
            status, js, resp_headers = self.request_json(
                method, url, headers=headers, body=body, timeout_s=timeout_s
            )
            return Result.success((status, js, resp_headers))
        except ProviderApiNetworkError as e:
            return Result.failure(
                "NETWORK_ERROR",
                "Network error. Check connection and try again.",
                details=str(e),
            )
        except self.error_cls as e:
            meta = {
                "status": e.status,
                "retry_after_s": e.retry_after_s,
                "rate_limit_reset_utc": e.rate_limit_reset_utc,
            }
            return Result.failure(
                e.code or "UNKNOWN",
                e.message or "API error",
                details=e.details or "",
                meta=meta,
            )
        except Exception as e:
            from freecad_gitpdm.core.log import _redact_sensitive

            return Result.failure(
                "UNKNOWN",
                "An unexpected error occurred.",
                details=_redact_sensitive(str(e)),
            )
