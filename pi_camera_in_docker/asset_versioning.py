"""Version and cache static frontend assets."""

import hashlib
from pathlib import Path

from flask import Flask, request


IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
REVALIDATE_CACHE_CONTROL = "no-cache"


def derive_asset_version(static_directory: Path) -> str:
    """Derive a stable version from every file in the static asset tree.

    Including both relative paths and contents means that adding, removing,
    renaming, or editing an asset changes the version.

    Args:
        static_directory: Root directory containing frontend assets.

    Returns:
        A shortened SHA-256 digest suitable for use in an asset URL.
    """
    digest = hashlib.sha256()
    for path in sorted(item for item in static_directory.rglob("*") if item.is_file()):
        digest.update(path.relative_to(static_directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as asset:
            for chunk in iter(lambda: asset.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def register_asset_versioning(app: Flask) -> str:
    """Add asset versions to generated URLs and configure their cache policy.

    Args:
        app: Flask application whose ``static`` endpoint should be versioned.

    Returns:
        Content-derived asset version registered on the application.

    Raises:
        RuntimeError: If the Flask application has no static directory.
    """
    if app.static_folder is None:
        message = "Asset versioning requires a Flask static directory"
        raise RuntimeError(message)

    version = derive_asset_version(Path(app.static_folder))
    app.config["ASSET_VERSION"] = version

    @app.url_defaults
    def _add_asset_version(endpoint: str, values: dict[str, object]) -> None:
        if endpoint == "static":
            values.setdefault("v", version)

    @app.after_request
    def _set_static_cache_policy(response):
        if request.endpoint != "static":
            return response
        if request.args.get("v") == version:
            response.headers["Cache-Control"] = IMMUTABLE_CACHE_CONTROL
        else:
            response.headers["Cache-Control"] = REVALIDATE_CACHE_CONTROL
        return response

    return version
