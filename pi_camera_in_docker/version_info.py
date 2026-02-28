"""Application version metadata helpers.

Provides a single source of truth for resolving application version strings
from VERSION files across runtime components (banner, Sentry, API endpoints).
"""

from pathlib import Path
from typing import Iterable


VERSION_FILE_CANDIDATES: tuple[Path, ...] = (
    Path("/app/VERSION"),
    Path(__file__).resolve().parent.parent / "VERSION",
)


def read_app_version(version_file_candidates: Iterable[Path] | None = None) -> str:
    """Read the application version from the first readable VERSION file.

    Args:
        version_file_candidates: Optional ordered candidate paths. If omitted,
            defaults to Docker image path then repository root fallback.

    Returns:
        Version string when found; otherwise ``"unknown"``.
    """
    candidates = version_file_candidates or VERSION_FILE_CANDIDATES
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return "unknown"


def get_app_version_info() -> dict[str, str]:
    """Get stable version metadata for API responses.

    Returns:
        Dictionary containing ``version`` and ``source`` fields.
    """
    for candidate in VERSION_FILE_CANDIDATES:
        if not candidate.exists():
            continue
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return {"version": version, "source": str(candidate)}

    return {"version": "unknown", "source": "unknown"}
