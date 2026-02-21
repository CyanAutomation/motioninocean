# ---- Build Arguments ----
# DEBIAN_SUITE: Base Debian release for builder and final stages (default: trixie)
# RPI_SUITE: Raspberry Pi repository suite (default: bookworm)
# Canonical build example:
#   docker build --build-arg DEBIAN_SUITE=trixie --build-arg RPI_SUITE=bookworm .
#
# Intentional suite split:
# - Debian base can track newer releases (e.g., trixie) for core userspace.
# - Raspberry Pi camera repo stays on bookworm until trixie camera packages are fully resolvable.
# INCLUDE_MOCK_CAMERA: Include Pillow for mock camera test frames (default: true)
# ALLOW_BOOKWORM_FALLBACK: Allow fallback to Bookworm if primary suite fails (default: false)
#   Set to true ONLY for compatibility builds where mixing suites is acceptable
#   When false, build fails with clear message if primary suite packages unavailable
#   Fallback retries camera package installation with RPI_SUITE=bookworm
ARG DEBIAN_SUITE=trixie
ARG RPI_SUITE=bookworm
ARG INCLUDE_MOCK_CAMERA=true
ARG ALLOW_BOOKWORM_FALLBACK=false

# ---- Builder Stage ----
# This stage is responsible for adding the Raspberry Pi repository and building Python packages.
# Using debian:${DEBIAN_SUITE}-slim with system Python to ensure compatibility with apt-installed python3-picamera2
FROM debian:${DEBIAN_SUITE}-slim AS builder

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

# ---- Layer 2: Raspberry Pi Repository & Camera Packages (Stable) ----
# Configure Raspberry Pi repository and install picamera2 system packages
# Both stages require this setup; duplication is necessary in multi-stage builds
# 
# Fallback behavior controlled by ALLOW_BOOKWORM_FALLBACK:
# - false (default): fail build if primary RPI_SUITE packages unavailable (prevents silent mismatches)
# - true: automatically fallback to Bookworm if primary suite fails (for compatibility builds)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    # Download Raspberry Pi GPG key with checksum verification
    echo "[Layer 2] Downloading Raspberry Pi GPG key..." && \
    if ! curl -L --connect-timeout 10 --max-time 30 --retry 2 -f \
      "https://archive.raspberrypi.org/debian/raspberrypi.gpg.key" \
      -o /tmp/raspberrypi.gpg.key 2>&1; then \
      echo "[ERROR] GPG key download failed"; exit 1; \
    fi && \
    if [ ! -s "/tmp/raspberrypi.gpg.key" ]; then \
      echo "[ERROR] GPG key is empty after download"; exit 1; \
    fi && \
    echo "[Layer 2] GPG key size: $(stat -c%s /tmp/raspberrypi.gpg.key) bytes" && \
    echo "[Layer 2] Verifying GPG key integrity..." && \
    if ! gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key 2>&1; then \
      echo "[ERROR] GPG dearmor failed"; exit 1; \
    fi && \
    if [ ! -s "/usr/share/keyrings/raspberrypi.gpg" ]; then \
      echo "[ERROR] GPG binary keyring is empty after dearmor"; exit 1; \
    fi && \
    echo "[Layer 2] GPG keyring size: $(stat -c%s /usr/share/keyrings/raspberrypi.gpg) bytes" && \
    echo "[Layer 2] Adding Raspberry Pi repository for suite: ${RPI_SUITE}..." && \
    echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ ${RPI_SUITE} main" > /etc/apt/sources.list.d/raspi.list && \
    rm /tmp/raspberrypi.gpg.key && \
    \
    # Create apt preferences file to pin camera packages to RPi repo, others to Debian
    echo "[Layer 2] Setting apt pinning for camera packages..." && \
    mkdir -p /etc/apt/preferences.d && \
    printf "# Pin camera-related packages to Raspberry Pi repository (higher priority)\n\
Package: libcamera* python3-libcamera python3-picamera2 rpicam*\n\
Pin: origin archive.raspberrypi.org\n\
Pin-Priority: 1001\n\
\n\
# Keep other packages at lower priority from RPi repo (prefer Debian versions)\n\
Package: *\n\
Pin: origin archive.raspberrypi.org\n\
Pin-Priority: 100\n" > /etc/apt/preferences.d/rpi-camera.preferences && \
    echo "[Layer 2] Running apt-get update..." && \
    apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 && \
    REQUIRED_CAMERA_PACKAGES="libcamera-apps python3-libcamera python3-picamera2" && \
    check_camera_preflight() { \
      suite="$1"; \
      missing_packages=""; \
      for pkg in $REQUIRED_CAMERA_PACKAGES; do \
        echo "[Layer 2] Preflight: checking ${pkg} for suite ${suite}"; \
        apt-cache policy "$pkg"; \
        candidate="$(apt-cache policy "$pkg" | awk '/Candidate:/ {print $2; exit}')"; \
        if [ -z "$candidate" ] || [ "$candidate" = "(none)" ]; then \
          missing_packages="$missing_packages $pkg"; \
          continue; \
        fi; \
        if ! apt-cache madison "$pkg" | awk -v suite="$suite" '$0 ~ /archive\.raspberrypi\.org\/debian/ && $0 ~ suite {found=1} END {exit found ? 0 : 1}'; then \
          missing_packages="$missing_packages $pkg"; \
        fi; \
      done; \
      missing_packages="$(echo "$missing_packages" | xargs)"; \
      if [ -n "$missing_packages" ]; then \
        echo "[ERROR] Preflight failed for suite ${suite}. Missing/unavailable package(s): ${missing_packages}"; \
        return 1; \
      fi; \
      echo "[Layer 2] Preflight passed for suite ${suite}"; \
      return 0; \
    } && \
    install_camera_packages() { \
      apt-get install -y --no-install-recommends -o Acquire::Retries=3 \
        libcamera-apps \
        libcamera-dev \
        python3-libcamera \
        python3-picamera2 \
        v4l-utils; \
    } && \
    ACTIVE_RPI_SUITE="${RPI_SUITE}" && \
    if ! check_camera_preflight "$ACTIVE_RPI_SUITE"; then \
      if [ "${ALLOW_BOOKWORM_FALLBACK}" = "true" ] && [ "$ACTIVE_RPI_SUITE" != "bookworm" ]; then \
        echo "[Layer 2] ALLOW_BOOKWORM_FALLBACK=true: switching Raspberry Pi repository to Bookworm for preflight retry..."; \
        echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
        apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 && \
        ACTIVE_RPI_SUITE="bookworm" && \
        if ! check_camera_preflight "$ACTIVE_RPI_SUITE"; then \
          echo "[ERROR] Preflight failed for both ${RPI_SUITE} and Bookworm fallback."; \
          exit 1; \
        fi; \
      else \
        echo "[ERROR] ALLOW_BOOKWORM_FALLBACK=${ALLOW_BOOKWORM_FALLBACK}. Failing fast after preflight check for suite ${ACTIVE_RPI_SUITE}."; \
        exit 1; \
      fi; \
    fi && \
    echo "[Layer 2] Attempting to install libcamera packages for ${ACTIVE_RPI_SUITE}..." && \
    install_camera_packages && \
    echo "[Layer 2] SUCCESS: libcamera packages installed from ${ACTIVE_RPI_SUITE}" && \
    echo "[Layer 2] Package origin verification:" && \
    apt-cache policy libcamera-apps python3-picamera2 python3-libcamera && \
    dpkg-query -W -f='${Package}\t${Version}\t${Origin}\n' \
      libcamera-apps python3-picamera2 python3-libcamera 2>/dev/null || true && \
    rm -rf /var/lib/apt/lists/*

# ---- Layer 3: Virtual Environment Setup (Volatile) ----
# Create venv to isolate pip-managed packages from system Python
# Using --system-site-packages to allow venv access to apt-installed picamera2 and libcamera
# This prevents conflicts between apt-managed (system) and pip-managed (application) dependencies
# while ensuring camera stack visibility (picamera2 is installed via apt, not pip)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    python3 -m venv --system-site-packages /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel

# ---- Layer 4: Python Dependencies (Volatile) ----
# Prepare for pip install: copy requirements and install pip packages into venv
# Separate layer enables fast cache hits when only requirements.txt changes
WORKDIR /app
COPY requirements.txt /app/

# Install Python packages into venv with BuildKit cache mount for faster rebuilds
# Exclude numpy (use system python3-numpy for simplejpeg compatibility)
# Conditionally install Pillow for mock camera support (controlled by INCLUDE_MOCK_CAMERA)
RUN --mount=type=cache,target=/root/.cache/pip \
    set -e && \
    sed '/^[[:space:]]*#/d;/^[[:space:]]*$/d' requirements.txt | \
      awk '!/^(numpy|Pillow)/' > /tmp/requirements-base.txt && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-base.txt && \
    if [ "$INCLUDE_MOCK_CAMERA" = "true" ]; then \
        echo "Installing Pillow for mock camera support..." && \
        grep "^Pillow" requirements.txt | /opt/venv/bin/pip install --no-cache-dir -r /dev/stdin; \
    else \
        echo "Skipping Pillow installation (INCLUDE_MOCK_CAMERA=false)"; \
    fi && \
    rm -rf /tmp/requirements-base.txt /tmp/*

# ---- Final Stage ----
# The final image uses debian:${DEBIAN_SUITE}-slim with system Python to ensure apt-installed
# python3-picamera2 is available alongside isolated pip dependencies in /opt/venv
# Venv approach prevents conflicts between system and pip-managed package versions
# Redeclare build args for use in this stage (Docker scoping rules)
#
# Intentional suite split mirrors top-level build args:
# - Debian base may be newer (e.g., trixie).
# - Raspberry Pi camera repo remains on bookworm until trixie camera stack resolution improves.
ARG DEBIAN_SUITE=trixie
ARG RPI_SUITE=bookworm
ARG INCLUDE_MOCK_CAMERA=true
ARG ALLOW_BOOKWORM_FALLBACK=false
FROM debian:${DEBIAN_SUITE}-slim

# Prevent Python bytecode generation and enable unbuffered output
# Savings: ~5-10% image size; improves container startup performance
# Add venv to PATH so 'python3' resolves to venv python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

# Copy GPG key and apt source list from builder stage
COPY --from=builder /usr/share/keyrings/raspberrypi.gpg /usr/share/keyrings/raspberrypi.gpg
COPY --from=builder /etc/apt/sources.list.d/raspi.list /etc/apt/sources.list.d/raspi.list
COPY --from=builder /etc/apt/preferences.d/rpi-camera.preferences /etc/apt/preferences.d/rpi-camera.preferences

# ---- OCI Labels (Metadata - no cache impact) ----
# Image metadata with build-time arguments for provenance tracking
LABEL org.opencontainers.image.source="https://github.com/CyanAutomation/motioninocean"
LABEL org.opencontainers.image.description="Raspberry Pi CSI camera streaming container (Picamera2/libcamera)"
LABEL org.opencontainers.image.authors="CyanAutomation"
LABEL org.opencontainers.image.vendor="CyanAutomation"
LABEL org.opencontainers.image.build.debian-suite="${DEBIAN_SUITE}"
LABEL org.opencontainers.image.build.rpi-suite="${RPI_SUITE}"
LABEL org.opencontainers.image.build.include-mock-camera="${INCLUDE_MOCK_CAMERA}"

# ---- Layer 1: System Dependencies (Stable) ----
# Install base system packages. Mirrored from builder stage (required for both image construction and runtime)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        gosu && \
    rm -rf /var/lib/apt/lists/*



# ---- Layer 2: Raspberry Pi Camera Packages (Stable) ----
# Install Raspberry Pi camera runtime packages using the copied repository setup
# Note: libcamera-dev excluded from final stage (header files not needed at runtime, saves ~30-50MB)
#
# Fallback behavior controlled by ALLOW_BOOKWORM_FALLBACK:
# - false (default): fail build if primary RPI_SUITE packages unavailable (prevents silent mismatches)
# - true: automatically fallback to Bookworm if primary suite fails (for compatibility builds)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    echo "[Final Stage Layer 2] Running apt-get update..." && \
    apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 && \
    REQUIRED_CAMERA_PACKAGES="libcamera-apps python3-libcamera python3-picamera2" && \
    check_camera_preflight() { \
      suite="$1"; \
      missing_packages=""; \
      for pkg in $REQUIRED_CAMERA_PACKAGES; do \
        echo "[Final Stage Layer 2] Preflight: checking ${pkg} for suite ${suite}"; \
        apt-cache policy "$pkg"; \
        candidate="$(apt-cache policy "$pkg" | awk '/Candidate:/ {print $2; exit}')"; \
        if [ -z "$candidate" ] || [ "$candidate" = "(none)" ]; then \
          missing_packages="$missing_packages $pkg"; \
          continue; \
        fi; \
        if ! apt-cache madison "$pkg" | awk -v suite="$suite" '$0 ~ /archive\.raspberrypi\.org\/debian/ && $0 ~ suite {found=1} END {exit found ? 0 : 1}'; then \
          missing_packages="$missing_packages $pkg"; \
        fi; \
      done; \
      missing_packages="$(echo "$missing_packages" | xargs)"; \
      if [ -n "$missing_packages" ]; then \
        echo "[ERROR] Preflight failed for suite ${suite}. Missing/unavailable package(s): ${missing_packages}"; \
        return 1; \
      fi; \
      echo "[Final Stage Layer 2] Preflight passed for suite ${suite}"; \
      return 0; \
    } && \
    install_camera_packages() { \
      apt-get install -y --no-install-recommends -o Acquire::Retries=3 \
        libcamera-apps \
        python3 \
        python3-numpy \
        python3-libcamera \
        python3-picamera2 \
        v4l-utils; \
    } && \
    ACTIVE_RPI_SUITE="${RPI_SUITE}" && \
    if ! check_camera_preflight "$ACTIVE_RPI_SUITE"; then \
      if [ "${ALLOW_BOOKWORM_FALLBACK}" = "true" ] && [ "$ACTIVE_RPI_SUITE" != "bookworm" ]; then \
        echo "[Final Stage Layer 2] ALLOW_BOOKWORM_FALLBACK=true: switching Raspberry Pi repository to Bookworm for preflight retry..."; \
        echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
        apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 && \
        ACTIVE_RPI_SUITE="bookworm" && \
        if ! check_camera_preflight "$ACTIVE_RPI_SUITE"; then \
          echo "[ERROR] Preflight failed for both ${RPI_SUITE} and Bookworm fallback."; \
          exit 1; \
        fi; \
      else \
        echo "[ERROR] ALLOW_BOOKWORM_FALLBACK=${ALLOW_BOOKWORM_FALLBACK}. Failing fast after preflight check for suite ${ACTIVE_RPI_SUITE}."; \
        exit 1; \
      fi; \
    fi && \
    echo "[Final Stage Layer 2] Attempting to install libcamera packages from ${ACTIVE_RPI_SUITE}..." && \
    install_camera_packages && \
    echo "[Final Stage Layer 2] SUCCESS: libcamera packages installed from ${ACTIVE_RPI_SUITE}" && \
    echo "[Final Stage Layer 2] Package origin verification:" && \
    apt-cache policy libcamera-apps python3-picamera2 python3-libcamera && \
    dpkg-query -W -f='${Package}\t${Version}\t${Origin}\n' \
      libcamera-apps python3-picamera2 python3-libcamera 2>/dev/null || true && \
    rm -rf /var/lib/apt/lists/*

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

# Copy application code with explicit per-file/directory COPYs
# Ordered by change frequency: stable → dynamic (requirements are pre-copied in builder)
# Improves cache reuse, prevents accidental inclusion of non-essential files, enhances reproducibility
COPY pi_camera_in_docker/ /app/pi_camera_in_docker/
COPY VERSION /app/
COPY scripts/healthcheck.py /app/healthcheck.py
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /app/healthcheck.py
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# ---- Layer 6: Build Metadata & Provenance ----
# Write build metadata to /app/BUILD_METADATA for runtime access by logging system
# Enables camera stack provenance logging at startup (version info, build suite, etc.)
RUN mkdir -p /app && \
    ( \
        echo "DEBIAN_SUITE=${DEBIAN_SUITE}"; \
        echo "RPI_SUITE=${RPI_SUITE}"; \
        echo "INCLUDE_MOCK_CAMERA=${INCLUDE_MOCK_CAMERA}"; \
        echo "BUILD_TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"; \
    ) > /app/BUILD_METADATA && \
    cat /app/BUILD_METADATA

# Validate required Python modules and picamera2 camera-info contract in the final image
# Known-good baseline: Raspberry Pi Bookworm repo package for python3-picamera2 (archive.raspberrypi.org/debian)
RUN python3 - <<'PY'
import numpy
import flask
import flask_cors
import picamera2

module_fn = getattr(picamera2, "global_camera_info", None)
picamera2_class = getattr(picamera2, "Picamera2", None)
class_fn = getattr(picamera2_class, "global_camera_info", None) if picamera2_class is not None else None

if callable(module_fn):
    print("All required modules imported successfully; camera-info API via picamera2.global_camera_info")
elif callable(class_fn):
    print("All required modules imported successfully; camera-info API via Picamera2.global_camera_info")
else:
    raise SystemExit(
        "Incompatible python3-picamera2 package revision: expected picamera2.global_camera_info or picamera2.Picamera2.global_camera_info"
    )
PY

# Validate libcamera install and Raspberry Pi pipeline/IPA locations
RUN libcamera-hello --version
RUN test -d /usr/share/libcamera/pipeline/rpi/vc4
RUN test -d /usr/share/libcamera/ipa/rpi/vc4

# Explicitly set STOPSIGNAL to SIGTERM for graceful shutdown handling
STOPSIGNAL SIGTERM

# Set PYTHONPATH to ensure package discovery for module execution
# Python3 now resolves to venv python via PATH=/opt/venv/bin:$PATH
ENV PYTHONPATH=/app

# Set startup entrypoint to validate/fix /data permissions and then drop to app user.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Set the command using module execution (-m) for relative imports to work
CMD ["python3", "-m", "pi_camera_in_docker.main"]
