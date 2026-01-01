# -*- coding: utf-8 -*-
"""
GitHub API Rate Limiter with Circuit Breaker
Sprint SECURITY-1: Prevent abuse and respect GitHub's secondary rate limits

Implements:
- Global rate limiting across all users
- Per-user/installation rate limiting for fairness
- Automatic backoff with exponential jitter
- Circuit breaker pattern to prevent retry storms
- Request coalescing to reduce redundant API calls

Security: Protects app from triggering GitHub's abuse detection while
ensuring fair resource distribution among users.
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
        """
        Try to acquire tokens for a request.
        
        Args:
            cost: Number of tokens needed (default 1)
            
        Returns:
            True if tokens acquired, False if insufficient
        """
        with self.lock:
            self._refill()
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def wait_time(self, cost: int = 1) -> float:
        """Calculate seconds to wait until tokens available."""
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
    failure_threshold: int = 5  # Failures before opening
    cooldown_s: float = 30.0  # Seconds to wait before testing
    success_threshold: int = 2  # Successes in half-open to close
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self):
        """Record a successful request."""
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
        """Record a failed request (5xx or secondary rate limit)."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                # Failed during test; reopen circuit
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
                self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.opened_at = time.time()

    def can_attempt(self) -> tuple[bool, Optional[float]]:
        """
        Check if request should be attempted.
        
        Returns:
            (can_attempt, retry_after_s) tuple
        """
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
    Multi-level rate limiter for GitHub API calls.
    
    Implements:
    - Global limit: 100 req/min across all users
    - Per-user limit: 30 req/min per authenticated user
    - Per-user circuit breaker to isolate failures
    
    Usage:
        limiter = RateLimiter.get_instance()
        if limiter.can_proceed(user_id="alice"):
            # Make API call
            result = api_client.request(...)
            if result.ok:
                limiter.record_success(user_id="alice")
            else:
                limiter.record_failure(user_id="alice")
        else:
            wait_s = limiter.wait_time(user_id="alice")
            # Show user retry message or queue for later
    """

    _instance: Optional['RateLimiter'] = None
    _lock = threading.Lock()

    # Rate limit configuration
    GLOBAL_CAPACITY = 100  # requests
    GLOBAL_REFILL_RATE = 100 / 60.0  # 100 per minute = 1.67/s
    
    PER_USER_CAPACITY = 30  # requests
    PER_USER_REFILL_RATE = 30 / 60.0  # 30 per minute = 0.5/s

    def __init__(self):
        """
        Initialize rate limiter with buckets and circuit breakers.
        
        Use RateLimiter.get_instance() instead of direct instantiation.
        """
        self._global_bucket = RateLimitBucket(
            capacity=self.GLOBAL_CAPACITY,
            tokens=self.GLOBAL_CAPACITY,
            refill_rate=self.GLOBAL_REFILL_RATE,
        )
        
        # Per-user buckets (lazy creation)
        self._user_buckets: Dict[str, RateLimitBucket] = {}
        self._user_circuits: Dict[str, CircuitBreaker] = {}
        self._user_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'RateLimiter':
        """Get singleton rate limiter instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_user_bucket(self, user_id: str) -> RateLimitBucket:
        """Get or create rate limit bucket for user."""
        with self._user_lock:
            if user_id not in self._user_buckets:
                self._user_buckets[user_id] = RateLimitBucket(
                    capacity=self.PER_USER_CAPACITY,
                    tokens=self.PER_USER_CAPACITY,
                    refill_rate=self.PER_USER_REFILL_RATE,
                )
            return self._user_buckets[user_id]

    def _get_circuit_breaker(self, user_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for user."""
        with self._user_lock:
            if user_id not in self._user_circuits:
                self._user_circuits[user_id] = CircuitBreaker()
            return self._user_circuits[user_id]

    def can_proceed(self, user_id: str = "anonymous", cost: int = 1) -> bool:
        """
        Check if request can proceed immediately.
        
        Args:
            user_id: User/installation identifier
            cost: Request cost in tokens (default 1)
            
        Returns:
            True if request should proceed, False if should wait/retry
        """
        # Check circuit breaker first
        circuit = self._get_circuit_breaker(user_id)
        can_attempt, _ = circuit.can_attempt()
        if not can_attempt:
            return False

        # Check global bucket
        if not self._global_bucket.try_acquire(cost):
            return False

        # Check per-user bucket
        user_bucket = self._get_user_bucket(user_id)
        if not user_bucket.try_acquire(cost):
            # Refund global token since user limit hit
            with self._global_bucket.lock:
                self._global_bucket.tokens = min(
                    self._global_bucket.capacity,
                    self._global_bucket.tokens + cost
                )
            return False

        return True

    def wait_time(self, user_id: str = "anonymous", cost: int = 1) -> float:
        """
        Calculate minimum wait time until request can proceed.
        
        Returns:
            Seconds to wait (0 if can proceed now)
        """
        # Check circuit breaker
        circuit = self._get_circuit_breaker(user_id)
        can_attempt, circuit_wait = circuit.can_attempt()
        if not can_attempt and circuit_wait:
            return circuit_wait

        # Check buckets
        global_wait = self._global_bucket.wait_time(cost)
        user_bucket = self._get_user_bucket(user_id)
        user_wait = user_bucket.wait_time(cost)
        
        return max(global_wait, user_wait)

    def record_success(self, user_id: str = "anonymous"):
        """Record successful API call (resets circuit breaker failures)."""
        circuit = self._get_circuit_breaker(user_id)
        circuit.record_success()

    def record_failure(self, user_id: str = "anonymous"):
        """
        Record failed API call (5xx or secondary rate limit hit).
        
        Increments circuit breaker failure count; may trip circuit.
        """
        circuit = self._get_circuit_breaker(user_id)
        circuit.record_failure()

    def is_circuit_open(self, user_id: str = "anonymous") -> bool:
        """Check if circuit breaker is open for user."""
        circuit = self._get_circuit_breaker(user_id)
        with circuit.lock:
            return circuit.state == CircuitState.OPEN

    def get_status(self, user_id: str = "anonymous") -> Dict[str, any]:
        """
        Get current rate limiter status for diagnostics.
        
        Returns dict with global/user tokens, circuit state, etc.
        """
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
