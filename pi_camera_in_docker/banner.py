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
from pathlib import Path
from typing import Optional

from pi_camera_in_docker.version_info import read_app_version


# ---------------------------------------------------------------------------
# Mio ASCII art
# ---------------------------------------------------------------------------
# Mio is the kawaii shark mascot of Motion In Ocean.  The art captures his
# defining features: round body, prominent camera-lens eye, dorsal fin, tiny
# nose dots, and a gentle smile.
# ---------------------------------------------------------------------------

MIO_ASCII: str = r"""


                                                                           .
                                                                     @@@@,/(#@@
                                                               .  @@@,,/////##@@
                                                               @@@,,,///////##@@
                                                             @@@,,,///(/((//##@@
                                                         . ,@@,,,////(///((###@@
                                      &@@@@@@@@@@@(       @@#,,//(/(/(((/((###@@
                              @@@@@@#(((((///////((/#@@@@@@(((((((/(((((((####@@
                         %@@@@((//(((((((//(((((///(///((//(%@@@(/(((((((####@@@
                      &@@@(///,,,,,,,,,,,,,,,,,,,,,,,,,//////////@@@#((((####@@
                    @@@(//,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,/////(/(@@#######@@
                  .@@(((,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,*////((#@####@@@@
               . @@@((*,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,//((((#@##@###@@@
              . @@@((,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,.,,,,,/(((/#@#(//(((&@@
               %@@((/,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,.   ,,,,(/(/(###((((((@@
               @@(((,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,/////###(((#%@@
            . @@@(((,,,,,,,,,,,,,,,,,,,,,,,,@@@@@@@#,,,,,,,,,,,,,,,,,,,/(((####&@@@
             @@#((((*,,,,,,,,,,,,,,,,,,,,@#/@@@@@@/@@@@,,,,,,,,,,,,,,,,/((((#######@@@
            @@(((%@@@//(,     .,,,,,,,,,@/@   @@@@@@#@@@,,,,,,,,,,,,,,,,/(((###(((((#@@(
         . @@((((@@@@                  @@&@@@@@@@@%@,@@@,,,,,,,,,,,,,,,/((((###(((((((@@
           @@(   #@@@                   @,@&%@@@###,@@@@,,,,,,,,,,,,,,,/(((###/(((((((@@
         . @@                            @@,,/@&,,&@@@,,,,,,,,,,,,,,,,(/((####(((###@@@
            @@           &      @            &@@@@,,,,,,,,,,,,,,,,,,,//((#######@@@@
             @@            @@@@.                   ,,,,,,,,,,,,,,,,//(##.###((((((@@
              @@@.                                        ,,,,,*//    ..###(((((((@@&
                @@@..                                               ..,##((((((((@@@
                  @@@....                                        .../#########@@@@
                     @@@@.....                              .....*###@@@@@@@@@
                         @@@@#...........        ...........,@@######%@@
                              @@@@@@@&,.............%@@@@@@#####/((/##@@
                                        *@@@@@@@@@@##########///((///#@@
                                                . *@@###(((((((((((((#@@
                                                    @@@(((((((((/(((((@@
                                                      .@@@(((((((((((@@@
                                                         @@@@((((((((@@
                                                             @@@@@@@@@


"""

MOTION_IN_OCEAN_ASCII: str = r"""╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                   _   _                   _                                          ║
║   _ __ ___   ___ | |_(_) ___  _ __       (_)_ __         ___   ___ ___  __ _ _ __    ║
║  | '_ ` _ \ / _ \| __| |/ _ \| '_ \ _____| | '_ \ _____ / _ \ / __/ _ \/ _` | '_ \   ║
║  | | | | | | (_) | |_| | (_) | | | |_____| | | | |_____| (_) | (_|  __/ (_| | | | |  ║
║  |_| |_| |_|\___/ \__|_|\___/|_| |_|     |_|_| |_|      \___/ \___\___|\__,_|_| |_|  ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝"""

_REPO_URL = "https://github.com/CyanAutomation/motioninocean"
_SEPARATOR = "-" * 54

# Candidate paths for the VERSION file: Docker image path first, then repo root.
_VERSION_FILE_CANDIDATES = [
    Path("/app/VERSION"),
    Path(__file__).parent.parent / "VERSION",
]


def _read_app_version() -> str:
    """Read the application version from configured VERSION file candidates.

    Returns:
        Version string (e.g. ``"1.19.5"``), or ``"unknown"`` if no readable
        file is found.
    """
    return read_app_version(_VERSION_FILE_CANDIDATES)


def print_startup_banner(
    mode: str,
    host: str,
    port: int,
    version: Optional[str] = None,
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
        mode: Application mode — ``"webcam"`` or ``"management"``.
        host: Bind host address (e.g. ``"0.0.0.0"`` or ``"127.0.0.1"``).
        port: Bind port number (e.g. ``8000`` or ``8001``).
        version: Application version string.  If ``None`` (default) the version
            is read automatically from the ``VERSION`` file via
            :func:`_read_app_version`.

    Returns:
        None

    Examples:
        >>> print_startup_banner("webcam", "0.0.0.0", 8000, version="1.19.5")
        # (writes to stderr)
    """
    resolved_version = version if version is not None else _read_app_version()
    log_format = os.environ.get("MIO_LOG_FORMAT", "text").lower().strip()

    if log_format == "json":
        # Single-line fallback — parseable but not decorative.
        line = (
            f"# Motion In Ocean v{resolved_version} | mode={mode} | "
            f"http://{host}:{port} | {_REPO_URL}"
        )
        print(line, file=sys.stderr, flush=True)  # noqa: T201
        return

    # Full text-mode banner
    banner_lines = [
        _SEPARATOR,
        MIO_ASCII.rstrip("\n"),
        MOTION_IN_OCEAN_ASCII,
        f"  Motion In Ocean  v{resolved_version}",
        f"  Mode     : {mode}",
        f"  Address  : http://{host}:{port}",
        f"  Repo     : {_REPO_URL}",
        _SEPARATOR,
        "",
    ]
    print("\n".join(banner_lines), file=sys.stderr, flush=True)  # noqa: T201
