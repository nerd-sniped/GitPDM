# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Generic token-bucket rate limiter with circuit breaker.

Relocated verbatim from `providers/github/rate_limiter.py` — that module
never contained any GitHub-specific logic (no GitHub URLs, headers, or
response shapes; it only deals in abstract "tokens" and an opaque
`user_id` string). `providers/github/rate_limiter.py` now re-exports from
here under its original names so nothing that imports the old path breaks.

Callers should prefix `user_id` with their provider id (e.g.
`f"{provider_id}:{hash(token)}"`) when calling `RateLimiter.get_instance()`
so per-user buckets stay isolated per host on this shared, process-wide
singleton. The global 100/min bucket is intentionally shared across all
providers combined — it's app-level abuse prevention, not a per-host API
limit.

Implements:
- Global rate limiting across all users
- Per-user/installation rate limiting for fairness
- Automatic backoff with exponential jitter
- Circuit breaker pattern to prevent retry storms
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states for API clients."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Tripped; rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting a specific scope (user/global)."""

    capacity: int  # Maximum tokens
    tokens: float  # Current tokens available
    refill_rate: float  # Tokens per second
    last_refill: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def try_acquire(self, cost: int = 1) -> bool:
        with self.lock:
            self._refill()
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def wait_time(self, cost: int = 1) -> float:
        with self.lock:
            self._refill()
            if self.tokens >= cost:
                return 0.0
            deficit = cost - self.tokens
            return deficit / self.refill_rate


@dataclass
class CircuitBreaker:
    """
    Circuit breaker to prevent retry storms.

    Opens after N consecutive failures, stays open for cooldown period,
    then enters half-open to test recovery.
    """

    failure_threshold: int = 5
    cooldown_s: float = 30.0
    success_threshold: int = 2

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self):
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self):
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
                self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.opened_at = time.time()

    def can_attempt(self) -> tuple[bool, Optional[float]]:
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True, None
            elif self.state == CircuitState.OPEN:
                elapsed = time.time() - self.opened_at
                if elapsed >= self.cooldown_s:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True, None
                else:
                    return False, self.cooldown_s - elapsed
            else:  # HALF_OPEN
                return True, None


class RateLimiter:
    """
    Multi-level, process-wide rate limiter shared across all provider API
    clients.

    - Global limit: 100 req/min across all users and all hosts
    - Per-user limit: 30 req/min per (provider-prefixed) user id
    - Per-user circuit breaker to isolate failures
    """

    _instance: Optional["RateLimiter"] = None
    _lock = threading.Lock()

    GLOBAL_CAPACITY = 100
    GLOBAL_REFILL_RATE = 100 / 60.0

    PER_USER_CAPACITY = 30
    PER_USER_REFILL_RATE = 30 / 60.0

    def __init__(self):
        """Use RateLimiter.get_instance() instead of direct instantiation."""
        self._global_bucket = RateLimitBucket(
            capacity=self.GLOBAL_CAPACITY,
            tokens=self.GLOBAL_CAPACITY,
            refill_rate=self.GLOBAL_REFILL_RATE,
        )
        self._user_buckets: Dict[str, RateLimitBucket] = {}
        self._user_circuits: Dict[str, CircuitBreaker] = {}
        self._user_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "RateLimiter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_user_bucket(self, user_id: str) -> RateLimitBucket:
        with self._user_lock:
            if user_id not in self._user_buckets:
                self._user_buckets[user_id] = RateLimitBucket(
                    capacity=self.PER_USER_CAPACITY,
                    tokens=self.PER_USER_CAPACITY,
                    refill_rate=self.PER_USER_REFILL_RATE,
                )
            return self._user_buckets[user_id]

    def _get_circuit_breaker(self, user_id: str) -> CircuitBreaker:
        with self._user_lock:
            if user_id not in self._user_circuits:
                self._user_circuits[user_id] = CircuitBreaker()
            return self._user_circuits[user_id]

    def can_proceed(self, user_id: str = "anonymous", cost: int = 1) -> bool:
        circuit = self._get_circuit_breaker(user_id)
        can_attempt, _ = circuit.can_attempt()
        if not can_attempt:
            return False

        if not self._global_bucket.try_acquire(cost):
            return False

        user_bucket = self._get_user_bucket(user_id)
        if not user_bucket.try_acquire(cost):
            with self._global_bucket.lock:
                self._global_bucket.tokens = min(
                    self._global_bucket.capacity, self._global_bucket.tokens + cost
                )
            return False

        return True

    def wait_time(self, user_id: str = "anonymous", cost: int = 1) -> float:
        circuit = self._get_circuit_breaker(user_id)
        can_attempt, circuit_wait = circuit.can_attempt()
        if not can_attempt and circuit_wait:
            return circuit_wait

        global_wait = self._global_bucket.wait_time(cost)
        user_bucket = self._get_user_bucket(user_id)
        user_wait = user_bucket.wait_time(cost)

        return max(global_wait, user_wait)

    def record_success(self, user_id: str = "anonymous"):
        circuit = self._get_circuit_breaker(user_id)
        circuit.record_success()

    def record_failure(self, user_id: str = "anonymous"):
        circuit = self._get_circuit_breaker(user_id)
        circuit.record_failure()

    def is_circuit_open(self, user_id: str = "anonymous") -> bool:
        circuit = self._get_circuit_breaker(user_id)
        with circuit.lock:
            return circuit.state == CircuitState.OPEN

    def get_status(self, user_id: str = "anonymous") -> Dict[str, object]:
        circuit = self._get_circuit_breaker(user_id)
        user_bucket = self._get_user_bucket(user_id)

        with self._global_bucket.lock:
            self._global_bucket._refill()
            global_tokens = self._global_bucket.tokens

        with user_bucket.lock:
            user_bucket._refill()
            user_tokens = user_bucket.tokens

        with circuit.lock:
            circuit_state = circuit.state.value
            failure_count = circuit.failure_count

        return {
            "global_tokens": round(global_tokens, 2),
            "global_capacity": self.GLOBAL_CAPACITY,
            "user_tokens": round(user_tokens, 2),
            "user_capacity": self.PER_USER_CAPACITY,
            "circuit_state": circuit_state,
            "circuit_failures": failure_count,
        }
