"""
retry.py — Retry Logic and Fallback System

Provides retry logic with exponential backoff and fallback
mechanisms for MCP server calls.
"""

import asyncio
import logging
from typing import Any, Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger("nexus")

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        exponential_base: float = 2.0,
        retriable_exceptions: tuple = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        ),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retriable_exceptions = retriable_exceptions


# Default retry config
DEFAULT_RETRY_CONFIG = RetryConfig()


def with_retry(config: RetryConfig = DEFAULT_RETRY_CONFIG):
    """
    Decorator to add retry logic to async functions.

    Usage:
        @with_retry(RetryConfig(max_attempts=3))
        async def call_api():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)

                except config.retriable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = min(
                            config.base_delay * (config.exponential_base**attempt),
                            config.max_delay,
                        )
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}"
                        )

            # If all retries failed, raise the last exception
            if last_exception:
                raise last_exception

            # This should never happen but satisfies type checker
            raise RuntimeError("Retry logic failed unexpectedly")

        return wrapper

    return decorator


def with_fallback(fallback_value: Any = None, log_fallback: bool = True):
    """
    Decorator to provide fallback value when function fails.

    Usage:
        @with_fallback(fallback_value={"error": "unavailable"})
        async def call_api():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_fallback:
                    logger.warning(f"Falling back for {func.__name__}: {e}")
                return fallback_value

        return wrapper

    return decorator


class FallbackChain:
    """
    Chain multiple fallback functions.
    Tries each function in order until one succeeds.

    Usage:
        chain = FallbackChain([
            lambda: real_api_call(),
            lambda: cache_get(),
            lambda: return_default(),
        ])
        result = await chain.execute()
    """

    def __init__(self, fallbacks: list[Callable]):
        self.fallbacks = fallbacks

    async def execute(self) -> Any:
        """Execute fallback chain, return first successful result."""
        last_error = None

        for i, fallback in enumerate(self.fallbacks):
            try:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback()
                else:
                    return fallback()
            except Exception as e:
                last_error = e
                logger.debug(f"Fallback {i + 1} failed: {e}")
                continue

        # All fallbacks failed
        if last_error:
            raise last_error

        raise RuntimeError("All fallback chain methods failed")


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    After consecutive failures exceed threshold, circuit opens
    and immediately fails fast without trying the failing operation.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.is_open = False

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        import time

        # Check if circuit should be reset
        if self.is_open and self.last_failure_time:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("Circuit breaker: attempting to reset")
                self.is_open = False
                self.failure_count = 0

        # If circuit is open, fail fast
        if self.is_open:
            raise Exception("Circuit breaker is open - failing fast")

        try:
            result = func(*args, **kwargs)
            # On success, reset failure count
            self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise e


# Utility for MCP servers
async def mcp_call_with_retry(
    func: Callable, *args, max_attempts: int = 3, fallback: Any = None, **kwargs
) -> Any:
    """
    Utility function to call MCP methods with retry and fallback.

    Usage:
        result = await mcp_call_with_retry(
            search_mcp.search,
            "query",
            max_attempts=3,
            fallback=[]
        )
    """
    config = RetryConfig(max_attempts=max_attempts)

    try:
        wrapped = with_retry(config)(func)
        return await wrapped(*args, **kwargs)
    except Exception as e:
        logger.warning(f"MCP call failed after retries: {e}")
        if fallback is not None:
            return fallback
        raise
