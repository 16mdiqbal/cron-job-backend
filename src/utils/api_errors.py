from __future__ import annotations

from flask import current_app


def safe_error_message(exc: Exception, default_message: str = "Internal server error") -> str:
    """
    Return a client-safe error message.

    - In development: returns the exception string to speed up debugging.
    - In production: returns a generic message to avoid leaking internals.
    """
    try:
        if bool(current_app.config.get("EXPOSE_ERROR_DETAILS")):
            return str(exc)
    except Exception:
        # If current_app is unavailable (rare), default to safe message.
        pass
    return default_message

