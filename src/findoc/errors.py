from __future__ import annotations


class FinDocError(Exception):
    """Base class for user-facing, safe-to-display errors."""


class ConfigurationError(FinDocError):
    """Missing or invalid configuration (e.g., no GROQ_API_KEY)."""


class VectorStoreError(FinDocError):
    """Vector store missing, unreadable, or empty."""


class GenerationError(FinDocError):
    """LLM call failed (timeout, rate limit, network, etc.)."""