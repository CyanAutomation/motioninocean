# ---- Builder Stage ----
# This stage is responsible for adding the Raspberry Pi repository and building Python packages.
# Using debian:bookworm-slim with system Python to ensure compatibility with apt-installed python3-picamera2
FROM debian:bookworm-slim AS builder

# Build argument to control Pillow installation for mock camera support
# Set to "false" to exclude mock camera support (~5-7MB savings)
# Default is "true" for development and testing flexibility
ARG INCLUDE_MOCK_CAMERA=true

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
        python3-numpy \
        ca-certificates \
        gnupg \
        curl \
        gcc && \
    rm -rf /var/lib/apt/lists/*

# ---- Layer 2: Raspberry Pi Repository & Camera Packages (Stable) ----
# Configure Raspberry Pi repository and install picamera2 system packages
# Both stages require this setup; duplication is necessary in multi-stage builds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    # Function to download GPG key with retry logic (exponential backoff)
    download_gpg_key() { \
        local url="$1" \
        local output="$2" \
        local max_attempts=5 \
        local attempt=1 \
        local backoff=2; \
        while [ $attempt -le $max_attempts ]; do \
            echo "[Attempt $attempt/$max_attempts] Downloading Raspberry Pi GPG key from $url..."; \
            if curl -L --connect-timeout 10 --max-time 60 --retry 3 --retry-all-errors --retry-delay 2 -f "$url" -o "$output" 2>&1; then \
                if [ -s "$output" ]; then \
                    size=$(stat -c%s "$output" 2>/dev/null || stat -f%z "$output" 2>/dev/null || echo "unknown"); \
                    echo "✓ GPG key downloaded successfully ($size bytes)"; \
                    return 0; \
                else \
                    echo "ERROR: GPG key file is empty"; \
                    rm -f "$output"; \
                fi; \
            else \
                echo "ERROR: curl failed with exit code $? for URL: $url"; \
            fi; \
            if [ $attempt -lt $max_attempts ]; then \
                echo "Retrying in ${backoff}s..."; \
                sleep $backoff; \
                backoff=$((backoff * 2)); \
            fi; \
            attempt=$((attempt + 1)); \
        done; \
        echo "FATAL: Failed to download GPG key after $max_attempts attempts"; \
        return 1; \
    } && \
    # Add Raspberry Pi repository with resilient GPG key download
    download_gpg_key "https://archive.raspberrypi.org/debian/raspberrypi.gpg.key" "/tmp/raspberrypi.gpg.key" || \
    download_gpg_key "http://archive.raspberrypi.org/debian/raspberrypi.gpg.key" "/tmp/raspberrypi.gpg.key" || \
    (echo "ERROR: Failed to download GPG key from all sources"; exit 1) && \
    gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key && \
    test -s /usr/share/keyrings/raspberrypi.gpg || (echo "ERROR: GPG dearmor produced empty file"; exit 1) && \
    echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
    rm /tmp/raspberrypi.gpg.key && \
    apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 && \
    apt-get install -y --no-install-recommends -o Acquire::Retries=3 \
        python3-libcamera \
        python3-picamera2 && \
    rm -rf /var/lib/apt/lists/*

# ---- Layer 3: Python Dependencies (Volatile) ----
# Prepare for pip install: copy requirements and install pip packages
# Separate layer enables fast cache hits when only requirements.txt changes
WORKDIR /app
COPY requirements.txt /app/

# Install Python packages with BuildKit cache mount for faster rebuilds
# Exclude numpy (use system python3-numpy for simplejpeg compatibility)
# Conditionally install Pillow for mock camera support (controlled by INCLUDE_MOCK_CAMERA)
RUN --mount=type=cache,target=/root/.cache/pip \
    grep -v "numpy" requirements.txt | grep -v "Pillow" > /tmp/requirements-base.txt && \
    pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements-base.txt && \
    if [ "$INCLUDE_MOCK_CAMERA" = "true" ]; then \
        echo "Installing Pillow for mock camera support..." && \
        grep "Pillow" requirements.txt | pip3 install --break-system-packages --no-cache-dir -r /dev/stdin; \
    else \
        echo "Skipping Pillow installation (INCLUDE_MOCK_CAMERA=false)"; \
    fi && \
    rm -rf /tmp/requirements-base.txt /tmp/*

# ---- Final Stage ----
# The final image uses debian:bookworm-slim with system Python to ensure apt-installed
# python3-picamera2 is available in the same Python environment used by the application
# Python 3.11 from system packages (Bookworm); aligned with requires-python >=3.9 in pyproject.toml
FROM debian:bookworm-slim

# ---- OCI Labels (Metadata - no cache impact) ----
LABEL org.opencontainers.image.source="https://github.com/CyanAutomation/motioninocean"
LABEL org.opencontainers.image.description="Raspberry Pi CSI camera streaming container (Picamera2/libcamera)"
LABEL org.opencontainers.image.authors="CyanAutomation"
LABEL org.opencontainers.image.vendor="CyanAutomation"

# ---- Layer 1: System Dependencies (Stable) ----
# Install base system packages. Mirrored from builder stage (required for both image construction and runtime)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        gnupg \
        curl \
        gosu && \
    rm -rf /var/lib/apt/lists/*

# ---- Layer 2: Raspberry Pi Repository & Camera Packages (Stable) ----
# Configure RPi repository and install camera runtime packages
# Note: Duplication with builder stage is necessary (each stage needs its own repo setup in multi-stage builds)
# Note: OpenCV not installed (edge detection feature was removed)
# Note: python3-flask removed (duplicate - installed via pip), libcap-dev and libcamera-dev removed (dev libraries not needed in runtime)
# Note: pykms/python3-kms not installed as DrmPreview functionality is not used in headless streaming mode
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -e && \
    # Function to download GPG key with retry logic (exponential backoff)
    download_gpg_key() { \
        local url="$1" \
        local output="$2" \
        local max_attempts=5 \
        local attempt=1 \
        local backoff=2; \
        while [ $attempt -le $max_attempts ]; do \
            echo "[Attempt $attempt/$max_attempts] Downloading Raspberry Pi GPG key from $url..."; \
            if curl -L --connect-timeout 10 --max-time 60 --retry 3 --retry-all-errors --retry-delay 2 -f "$url" -o "$output" 2>&1; then \
                if [ -s "$output" ]; then \
                    size=$(stat -c%s "$output" 2>/dev/null || stat -f%z "$output" 2>/dev/null || echo "unknown"); \
                    echo "✓ GPG key downloaded successfully ($size bytes)"; \
                    return 0; \
                else \
                    echo "ERROR: GPG key file is empty"; \
                    rm -f "$output"; \
                fi; \
            else \
                echo "ERROR: curl failed with exit code $? for URL: $url"; \
            fi; \
            if [ $attempt -lt $max_attempts ]; then \
                echo "Retrying in ${backoff}s..."; \
                sleep $backoff; \
                backoff=$((backoff * 2)); \
            fi; \
            attempt=$((attempt + 1)); \
        done; \
        echo "FATAL: Failed to download GPG key after $max_attempts attempts"; \
        return 1; \
    } && \
    download_gpg_key "https://archive.raspberrypi.org/debian/raspberrypi.gpg.key" "/tmp/raspberrypi.gpg.key" || \
    download_gpg_key "http://archive.raspberrypi.org/debian/raspberrypi.gpg.key" "/tmp/raspberrypi.gpg.key" || \
    (echo "ERROR: Failed to download GPG key from all sources"; exit 1) && \
    gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key && \
    test -s /usr/share/keyrings/raspberrypi.gpg || (echo "ERROR: GPG dearmor produced empty file"; exit 1) && \
    echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
    rm /tmp/raspberrypi.gpg.key && \
    apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=60 -o Acquire::https::Timeout=60 && \
    apt-get install -y --no-install-recommends -o Acquire::Retries=3 \
        python3 \
        python3-numpy \
        python3-libcamera \
        python3-picamera2 && \
    rm -rf /var/lib/apt/lists/*

# ---- Layer 3: Non-Root User Setup (Runtime Security) ----
# Create non-root app user for runtime security
# Even with privileged: true in docker-compose, reduces blast radius if process is compromised
RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -s /usr/sbin/nologin -m app

# ---- Layer 4: Prepare Application Directory ----
WORKDIR /app

# ---- Layer 5: Copy Pip Packages & Application Code (Change Frequency Order) ----
# Copy pre-compiled Python packages from builder stage
# Debian Bookworm uses Python 3.11 by default
COPY --from=builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages

# Copy application code with explicit per-file/directory COPYs
# Ordered by change frequency: stable → dynamic (requirements are pre-copied in builder)
# Improves cache reuse, prevents accidental inclusion of non-essential files, enhances reproducibility
COPY pi_camera_in_docker/ /app/pi_camera_in_docker/
COPY VERSION /app/
COPY scripts/healthcheck.py /app/healthcheck.py
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /app/healthcheck.py
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

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

# Explicitly set STOPSIGNAL to SIGTERM for graceful shutdown handling
STOPSIGNAL SIGTERM

# Set PYTHONPATH to ensure package discovery for module execution
ENV PYTHONPATH=/app

# Set startup entrypoint to validate/fix /data permissions and then drop to app user.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Set the command using module execution (-m) for relative imports to work
CMD ["python3", "-m", "pi_camera_in_docker.main"]
