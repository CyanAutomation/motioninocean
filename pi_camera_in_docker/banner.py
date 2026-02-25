"""Startup banner for Motion In Ocean.

Prints Mio (the project mascot) as ASCII art to stderr when the application
starts.  Writing directly to stderr — like the docker-entrypoint.sh does for
its own provenance lines — keeps the output out of the structured logging
pipeline so it never corrupts JSON-formatted log streams consumed by aggregators
such as Loki or CloudWatch.

In JSON log mode (``MIO_LOG_FORMAT=json``) a compact single-line fallback is
emitted instead of the multi-line art so that machines always see version and
mode metadata without having to parse decorated text.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Mio ASCII art
# ---------------------------------------------------------------------------
# Mio is the kawaii shark mascot of Motion In Ocean.  The art captures his
# defining features: round body, prominent camera-lens eye, dorsal fin, tiny
# nose dots, and a gentle smile.
# ---------------------------------------------------------------------------

MIO_ASCII: str = r"""
           /\
     .----/  \----.
    /   (      )   \
   |  .-------.     |
   | /  /---\  \    |
   ||  | (@) |  | . |
   | \  \---/  /  . |
   |  '-------'  ~  |
    \              /
     '--.______.--'
          |  |
         /    \
"""

_REPO_URL = "https://github.com/CyanAutomation/motioninocean"
_SEPARATOR = "-" * 54


def print_startup_banner(
    version: str,
    mode: str,
    host: str,
    port: int,
) -> None:
    """Print the Mio startup banner to stderr.

    Checks the ``MIO_LOG_FORMAT`` environment variable to decide which format
    to emit:

    * ``text`` (default) — full multi-line ASCII art block with version, mode,
      address, and repository URL printed to ``sys.stderr``.
    * ``json`` — a single compact line so that machine-readable log pipelines
      always receive version and mode metadata without multi-line noise.

    Writing to ``sys.stderr`` ensures the banner appears in ``docker logs``
    output regardless of whether the Python logging system has been configured
    to suppress informational messages.

    Args:
        version: Application version string (e.g. ``"1.19.5"``).
        mode: Application mode — ``"webcam"`` or ``"management"``.
        host: Bind host address (e.g. ``"0.0.0.0"`` or ``"127.0.0.1"``).
        port: Bind port number (e.g. ``8000`` or ``8001``).

    Returns:
        None

    Examples:
        >>> print_startup_banner("1.19.5", "webcam", "0.0.0.0", 8000)
        # (writes to stderr)
    """
    log_format = os.environ.get("MIO_LOG_FORMAT", "text").lower().strip()

    if log_format == "json":
        # Single-line fallback — parseable but not decorative.
        line = (
            f"# Motion In Ocean v{version} | mode={mode} | "
            f"http://{host}:{port} | {_REPO_URL}"
        )
        print(line, file=sys.stderr, flush=True)
        return

    # Full text-mode banner
    banner_lines = [
        _SEPARATOR,
        MIO_ASCII.rstrip("\n"),
        f"  Motion In Ocean  v{version}",
        f"  Mode     : {mode}",
        f"  Address  : http://{host}:{port}",
        f"  Repo     : {_REPO_URL}",
        _SEPARATOR,
        "",
    ]
    print("\n".join(banner_lines), file=sys.stderr, flush=True)
