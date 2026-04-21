"""Circuit breaker pattern implementation for TTS engines.

This module provides fault tolerance by tracking engine failures and
automatically opening the circuit when failure threshold is reached.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from loguru import logger


class CircuitState(str, Enum):
    """Circuit breaker states.
    
    - CLOSED: Normal state, requests are allowed
    - OPEN: Circuit is open, requests are blocked
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration parameters."""

    failure_threshold: int = 5  # Number of failures before opening circuit
    success_threshold: int = 2  # Successes needed in HALF_OPEN to close
    timeout_seconds: int = 60  # Time to wait before trying HALF_OPEN
    half_open_timeout: int = 30  # Time to wait in HALF_OPEN before reopening


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    state: CircuitState = CircuitState.CLOSED


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.
    
    Tracks engine failures and automatically blocks requests to failing
    engines, allowing the system to fail fast and recover gracefully.
    
    Example:
        >>> breaker = CircuitBreaker()
        >>> 
        >>> if breaker.is_available("openai"):
        ...     try:
        ...         result = await call_openai()
        ...         breaker.record_success("openai")
        ...     except Exception:
        ...         breaker.record_failure("openai")
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.stats: Dict[str, CircuitStats] = {}

    def get_state(self, engine_name: str) -> CircuitState:
        """Get current state of the circuit for an engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            Current circuit state
        """
        if engine_name not in self.stats:
            self.stats[engine_name] = CircuitStats()

        stats = self.stats[engine_name]
        current_time = time.time()

        # Check if OPEN circuit should transition to HALF_OPEN
        if stats.state == CircuitState.OPEN:
            time_since_failure = current_time - stats.last_failure_time
            if time_since_failure > self.config.timeout_seconds:
                logger.info(
                    f"Circuit breaker for {engine_name} entering HALF_OPEN state "
                    f"after {time_since_failure:.1f}s"
                )
                stats.state = CircuitState.HALF_OPEN
                stats.success_count = 0

        return stats.state

    def is_available(self, engine_name: str) -> bool:
        """Check if engine is available (circuit not OPEN).
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            True if engine is available, False if circuit is OPEN
        """
        state = self.get_state(engine_name)
        return state != CircuitState.OPEN

    def record_success(self, engine_name: str) -> None:
        """Record a successful operation.
        
        Args:
            engine_name: Name of the engine
        """
        if engine_name not in self.stats:
            self.stats[engine_name] = CircuitStats()

        stats = self.stats[engine_name]
        stats.success_count += 1
        stats.last_success_time = time.time()

        # HALF_OPEN: Check if we can close the circuit
        if stats.state == CircuitState.HALF_OPEN:
            if stats.success_count >= self.config.success_threshold:
                logger.info(
                    f"Circuit breaker for {engine_name} recovered to CLOSED "
                    f"after {stats.success_count} successes"
                )
                stats.state = CircuitState.CLOSED
                stats.failure_count = 0

        # CLOSED: Reset failure count on success
        elif stats.state == CircuitState.CLOSED:
            stats.failure_count = 0

    def record_failure(self, engine_name: str) -> None:
        """Record a failed operation.
        
        Args:
            engine_name: Name of the engine
        """
        if engine_name not in self.stats:
            self.stats[engine_name] = CircuitStats()

        stats = self.stats[engine_name]
        stats.failure_count += 1
        stats.last_failure_time = time.time()

        # CLOSED: Check if we should open the circuit
        if stats.state == CircuitState.CLOSED:
            if stats.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker OPENED for {engine_name} "
                    f"after {stats.failure_count} consecutive failures"
                )
                stats.state = CircuitState.OPEN

        # HALF_OPEN: Any failure reopens the circuit
        elif stats.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"Circuit breaker for {engine_name} reopened "
                f"due to failure in HALF_OPEN state"
            )
            stats.state = CircuitState.OPEN

    def reset(self, engine_name: str) -> None:
        """Reset circuit breaker for an engine.
        
        Args:
            engine_name: Name of the engine
        """
        if engine_name in self.stats:
            self.stats[engine_name] = CircuitStats()
            logger.info(f"Circuit breaker reset for {engine_name}")

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        self.stats.clear()
        logger.info("All circuit breakers reset")

    def get_stats(self) -> Dict[str, dict]:
        """Get statistics for all engines.
        
        Returns:
            Dictionary mapping engine names to their stats
        """
        return {
            name: {
                "state": stats.state.value,
                "failure_count": stats.failure_count,
                "success_count": stats.success_count,
                "last_failure": stats.last_failure_time,
                "last_success": stats.last_success_time,
            }
            for name, stats in self.stats.items()
        }


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()
