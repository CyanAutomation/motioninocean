"""Minimal CORS response headers for the app's exact-origin policy."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from flask import Flask, Response, request


if TYPE_CHECKING:
    from collections.abc import Iterable


_ALLOWED_METHODS = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


def register_cors(app: Flask, origins: Iterable[str]) -> None:
    """Register CORS headers for a list of exact origins or a wildcard.

    Args:
        app: Flask application that will receive the headers.
        origins: Exact allowed origins, or ``("*",)`` to allow any origin.
    """
    allowed_origins = {origin.strip() for origin in origins if origin.strip()}
    if not allowed_origins:
        return
    allow_any_origin = "*" in allowed_origins

    @app.after_request
    def _add_cors_headers(response: Response) -> Response:
        origin = request.headers.get("Origin")
        if not origin:
            return response
        if allow_any_origin:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            _append_vary_origin(response)
        else:
            return response

        if request.method == "OPTIONS" and request.headers.get("Access-Control-Request-Method"):
            response.headers["Access-Control-Allow-Methods"] = _ALLOWED_METHODS
            requested_headers = request.headers.get("Access-Control-Request-Headers", "")
            safe_headers = [
                header.strip()
                for header in requested_headers.split(",")
                if _HEADER_NAME.fullmatch(header.strip())
            ]
            if safe_headers:
                response.headers["Access-Control-Allow-Headers"] = ", ".join(safe_headers)
        return response


def _append_vary_origin(response: Response) -> None:
    """Add Origin to Vary while preserving existing response cache keys."""
    vary_values = response.headers.getlist("Vary")
    vary_tokens = {token.strip().lower() for value in vary_values for token in value.split(",")}
    if "*" not in vary_tokens and "origin" not in vary_tokens:
        response.headers.add("Vary", "Origin")
