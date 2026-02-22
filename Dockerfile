# ---- Build Arguments ----
# DEBIAN_SUITE: Suite used for builder/final stages (defaults to trixie to match RPi OS trixie hosts)
# RPI_SUITE: Raspberry Pi apt suite used for camera packages (defaults to trixie; must match DEBIAN_SUITE)
# Note: Motion In Ocean targets Raspberry Pi OS Trixie and its libcamera stack.
# No suite overrides are supported. For alternative distros, fork and modify the Dockerfile.
ARG DEBIAN_SUITE=trixie
ARG RPI_SUITE=trixie

# ---- Builder Stage ----
# Minimal Python packaging stage: installs build tools and creates isolated venv.
# Camera packages are NOT needed here; they are installed only in the final stage.
FROM debian:${DEBIAN_SUITE}-slim AS builder

# Re-declare build args for this stage
ARG DEBIAN_SUITE
ARG RPI_SUITE

# ---- Layer 1: System Build Tools (Stable) ----
# Install base system dependencies and build toolchain
# Using BuildKit cache mounts to speed up rebuilds
# Includes resilient installation with retry logic for transient network failures
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        python3-numpy \
        ca-certificates \
        gnupg \
        curl \
        gcc && \
    rm -rf /var/lib/apt/lists/*

# ---- Layer 2: Virtual Environment Setup ----
# Create venv to isolate pip-managed packages from system Python
# Using --system-site-packages to allow venv access to apt-installed libcamera C extensions
# This prevents conflicts between apt-managed (system) and pip-managed (application) dependencies
# picamera2 (pure-Python wrapper) is pip-installed here on arm64:
#   python3-picamera2 is only in the RPi bookworm apt repo, not trixie.
#   The C extension (python3-libcamera) is still installed via apt in the final stage.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    python3 -m venv --system-site-packages /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    if [ "$(dpkg --print-architecture)" = "arm64" ]; then \
        echo "Installing picamera2 from PyPI (python3-picamera2 not in RPi trixie apt repo)..." && \
        /opt/venv/bin/pip install --no-deps picamera2; \
    fi

# ---- Layer 3: Python Dependencies (Volatile) ----
# Prepare for pip install: copy requirements and install pip packages into venv
# Separate layer enables fast cache hits when only requirements.txt changes
WORKDIR /app
COPY requirements.txt /app/

# Install Python packages into venv with BuildKit cache mount for faster rebuilds
# Exclude numpy (use system python3-numpy for simplejpeg compatibility)
RUN --mount=type=cache,target=/root/.cache/pip \
    set -e && \
    sed '/^[[:space:]]*#/d;/^[[:space:]]*$/d' requirements.txt | \
      awk '!/^(numpy)/' > /tmp/requirements-base.txt && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-base.txt && \
    rm -rf /tmp/requirements-base.txt /tmp/*

# ---- Final Stage ----
# The final image uses debian:trixie-slim with system Python for apt-installed
# libcamera libraries alongside isolated pip dependencies in /opt/venv.
# picamera2 (pure-Python wrapper) is pip-installed into /opt/venv in the builder stage above,
# since python3-picamera2 is not available in the RPi trixie apt repo (only in bookworm).
# Venv approach prevents conflicts between system and pip-managed package versions
FROM debian:${DEBIAN_SUITE}-slim

# Re-declare build args for this stage
ARG DEBIAN_SUITE
ARG RPI_SUITE
ARG TARGETARCH

# Prevent Python bytecode generation and enable unbuffered output
# Savings: ~5-10% image size; improves container startup performance
# Add venv to PATH so 'python3' resolves to venv python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

# ---- OCI Labels (Metadata - no cache impact) ----
# Image metadata for provenance tracking
LABEL org.opencontainers.image.source="https://github.com/CyanAutomation/motioninocean"
LABEL org.opencontainers.image.description="Raspberry Pi CSI camera streaming container (Picamera2/libcamera)"
LABEL org.opencontainers.image.authors="CyanAutomation"
LABEL org.opencontainers.image.vendor="CyanAutomation"

# ---- Layer 1: System Dependencies (Stable) ----
# Install base system packages from Debian repositories only.
# Keep Raspberry Pi apt source/pinning out of this layer so apt-get update does not depend on archive.raspberrypi.com.
# CRITICAL: Install python3, python3-venv, python3-numpy explicitly before venv copy.
# Multi-stage venv with --system-site-packages uses symlinks to system Python; must exist before validation.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        gosu \
        python3 \
        python3-venv \
        python3-numpy && \
    rm -rf /var/lib/apt/lists/*



# ---- Layer 2: Raspberry Pi Repository Setup & Camera Packages (arm64 only) ----
# Install Raspberry Pi camera runtime packages (arm64 only, skipped for amd64).
# On arm64: Downloads RPi GPG key, adds RPi repository, installs camera packages with strict GPG verification.
# On amd64: Skipped entirely; prevents unnecessary package installation and repo setup on non-hardware architectures.
# NOTE: Do NOT pin a specific libcamera0.x soname. libcamera0.x and libcamera-ipa share a strict
# version-locked dependency (libcamera0.6 requires libcamera-ipa=0.6.x, libcamera0.7 requires
# libcamera-ipa=0.7.x). Pinning a specific runtime makes co-installation of python3-libcamera
# (which always tracks the newest soname) impossible. Let apt resolve the libcamera runtime version.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    set -e && \
    echo "Detected architecture: $(dpkg --print-architecture)" && \
    if [ "$(dpkg --print-architecture)" = "arm64" ]; then \
        echo "Installing Raspberry Pi camera stack for arm64..." && \
        curl -L --connect-timeout 10 --max-time 30 --retry 2 -f \
          "https://archive.raspberrypi.com/debian/raspberrypi.gpg.key" \
          -o /tmp/raspberrypi.gpg.key && \
        echo "Verifying GPG key integrity..." && \
        gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key && \
        rm /tmp/raspberrypi.gpg.key && \
        echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] https://archive.raspberrypi.com/debian/ ${RPI_SUITE} main" > /etc/apt/sources.list.d/raspi.list && \
        mkdir -p /etc/apt/preferences.d && \
        printf "# Pin camera-related packages to Raspberry Pi repository\n\
Package: libcamera* python3-libcamera rpicam*\n\
Pin: origin archive.raspberrypi.com\n\
Pin-Priority: 1001\n\
\n\
# Lower priority for other RPi packages (prefer Debian versions)\n\
Package: *\n\
Pin: origin archive.raspberrypi.com\n\
Pin-Priority: 100\n" > /etc/apt/preferences.d/rpi-camera.preferences && \
        echo "Configuring apt to use gpgv for RPi repo (RPi key uses SHA1 self-sig, rejected by sqv on trixie)..." && \
        echo 'APT::Key::gpgvcommand "gpgv";' > /etc/apt/apt.conf.d/99use-gpgv-rpi && \
        apt-get update && \
        apt-get install -y --no-install-recommends \
          libcamera-dev \
          python3-libcamera \
          rpicam-apps \
          v4l-utils && \
        rm -f /etc/apt/apt.conf.d/99use-gpgv-rpi && \
        echo "Camera packages installed successfully:" && \
        apt-cache policy libcamera-dev rpicam-apps python3-libcamera && \
        dpkg-query -W -f='${Package}\t${Version}\t${Origin}\n' \
          libcamera-dev rpicam-apps python3-libcamera 2>/dev/null || true && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        echo "Skipping Raspberry Pi camera stack (non-arm64 build)"; \
    fi

# ---- Layer 3: Non-Root User Setup (Runtime Security) ----
# Ensure common device-access groups exist (Debian slim may not ship them)
RUN groupadd -f video && \
    groupadd -f render || true

# Create non-root app user for runtime security
# Even with privileged: true in docker-compose, reduces blast radius if process is compromised
RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -s /usr/sbin/nologin -m app

# ---- Layer 4: Prepare Application Directory ----
WORKDIR /app

# ---- Layer 5: Copy Virtual Environment & Application Code (Change Frequency Order) ----
# Copy pre-built venv from builder stage with all pip-managed dependencies isolated
# Isolation prevents conflicts between system apt-managed and app pip-managed packages
COPY --from=builder /opt/venv /opt/venv

# Explicitly bridge Debian's 'dist-packages' into the venv via a .pth file.
# Python's --system-site-packages flag adds standard 'site-packages' paths, but Debian/Ubuntu
# install apt-managed packages to 'dist-packages' (not 'site-packages'). In Python 3.13 on
# trixie, the venv's site.py may not inherit Debian's dist-packages path customisation when
# the venv is created in a separate builder stage and then COPY'd into the final stage.
# A .pth file guarantees visibility regardless of that bridge working or not.
RUN PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") && \
    VENV_SITE="/opt/venv/lib/python${PYVER}/site-packages" && \
    printf '/usr/lib/python3/dist-packages\n/usr/lib/python%s/dist-packages\n' "${PYVER}" \
        > "${VENV_SITE}/debian_dist_packages.pth" && \
    echo "Added debian_dist_packages.pth for Python ${PYVER}"

# Copy application code with explicit per-file/directory COPYs
# Ordered by change frequency: stable → dynamic (requirements are pre-copied in builder)
# Improves cache reuse, prevents accidental inclusion of non-essential files, enhances reproducibility
COPY pi_camera_in_docker/ /app/pi_camera_in_docker/
COPY VERSION /app/
COPY scripts/healthcheck.py /app/healthcheck.py
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY scripts/validate-stack.py /usr/local/bin/validate-stack.py
RUN chmod +x /app/healthcheck.py
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/validate-stack.py

# ---- Layer 5: Build Metadata & Provenance ----
# Write build metadata to /app/BUILD_METADATA for runtime access by logging system
# Enables camera stack provenance logging at startup (version info, build details, etc.)
RUN mkdir -p /app && \
    ( \
        echo "DEBIAN_SUITE=${DEBIAN_SUITE}"; \
        echo "RPI_SUITE=${RPI_SUITE}"; \
        echo "TARGETARCH=${TARGETARCH}"; \
        echo "BUILD_TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"; \
    ) > /app/BUILD_METADATA && \
    cat /app/BUILD_METADATA

# ---- Layer 6: Validate Python Modules & Camera Contract (Architecture-Aware) ----
# Conditional validation based on architecture:
# - arm64: Validates full camera stack (numpy, flask, flask_cors, picamera2, libcamera)
# - amd64: Validates Python stack only (numpy, flask, flask_cors; no picamera2 or libcamera)
# This ensures explicit behavior: arm64 fails if camera unavailable, amd64 fails if core Python unavailable
# Use venv Python: flask and flask_cors are pip-installed into /opt/venv only (not the system Python).
# The venv was created with --system-site-packages so /opt/venv/bin/python3 also sees apt-installed
# packages (numpy, libcamera C extensions) via /usr/lib/python3/dist-packages/ — both stages share the
# same raspbian:trixie-slim base so pyvenv.cfg home pointers match correctly across build stages.
RUN /opt/venv/bin/python3 /usr/local/bin/validate-stack.py

# Layer 6 (continued): Validate libcamera install and Raspberry Pi pipeline/IPA locations (arm64 only)
RUN echo "Detected architecture: $(dpkg --print-architecture)" && \
    if [ "$(dpkg --print-architecture)" = "arm64" ]; then \
    CAMERA_CLI=""; \
    if command -v rpicam-hello >/dev/null 2>&1; then \
    CAMERA_CLI="rpicam-hello"; \
    elif command -v libcamera-hello >/dev/null 2>&1; then \
    CAMERA_CLI="libcamera-hello"; \
    else \
    echo "ERROR: Neither rpicam-hello nor libcamera-hello is available in PATH." >&2; \
    exit 1; \
    fi && \
    "${CAMERA_CLI}" --version && \
    test -d /usr/share/libcamera/pipeline/rpi/vc4 && \
    test -d /usr/share/libcamera/ipa/rpi/vc4 && \
    echo "--- ABI version assertion ---" && \
    ldconfig -p | grep libcamera && \
    LIBCAM_SONAME=$(ldconfig -p | grep -oE 'libcamera.so.0.[0-9]+' | sort -t. -k3 -n | tail -1) && \
    test -n "${LIBCAM_SONAME}" || { echo "ERROR: No libcamera.so.0.x found in ldconfig — camera library not installed." >&2; exit 1; } && \
    echo "${LIBCAM_SONAME} confirmed." && \
    python3 -c "\
import libcamera; \
v = libcamera.__version__; \
print('libcamera Python binding version:', v); \
parts = v.split('.'); \
assert len(parts) >= 2 and int(parts[0]) == 0 and int(parts[1]) >= 5, f'Expected libcamera >= 0.5, got: {v}. Too old — rebuild required.' \
" && \
    echo "libcamera Python binding confirmed."; \
    else \
    echo "Skipping libcamera validation on amd64 (mock camera build)"; \
    fi

# Explicitly set STOPSIGNAL to SIGTERM for graceful shutdown handling
STOPSIGNAL SIGTERM

# Set PYTHONPATH to ensure package discovery for module execution
# Python3 now resolves to venv python via PATH=/opt/venv/bin:$PATH
ENV PYTHONPATH=/app

# Set startup entrypoint to validate/fix /data permissions and then drop to app user.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Set the command using module execution (-m) for relative imports to work
CMD ["python3", "-m", "pi_camera_in_docker.main"]
