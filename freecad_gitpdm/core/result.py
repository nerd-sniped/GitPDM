from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Dict, Any


T = TypeVar("T")


@dataclass(frozen=True)
class AppError:
    """Structured error information safe for UI and logs.

    `details` should avoid secrets/tokens.
    `meta` can hold non-sensitive context (status codes, retry-after, etc.).
    """

    code: str
    message: str
    details: str = ""
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[AppError] = None

    @staticmethod
    def success(value: T) -> "Result[T]":
        return Result(ok=True, value=value, error=None)

    @staticmethod
    def failure(
        code: str,
        message: str,
        details: str = "",
        meta: Optional[Dict[str, Any]] = None,
    ) -> "Result[T]":
        return Result(
            ok=False,
            value=None,
            error=AppError(code=code, message=message, details=details, meta=meta),
        )

    def unwrap_or(self, default: T) -> T:
        return self.value if self.ok and self.value is not None else default
