"""Stable application errors for the submission-safe API."""


class SafeWebError(Exception):
    """An expected API error with a stable client-facing code."""

    def __init__(self, code, status=400, details=None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.details = details or {}
