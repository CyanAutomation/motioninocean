# ---- Builder Stage ----
# This stage is responsible for adding the Raspberry Pi repository and building Python packages.
# Using debian:bookworm-slim with system Python to ensure compatibility with apt-installed python3-picamera2
FROM debian:bookworm-slim AS builder

# Build argument to control opencv-python-headless installation
# Set to "true" to include edge detection support (~40MB larger image)
# Default is "false" for minimal image size
ARG INCLUDE_OPENCV=false

# Install dependencies needed for fetching RPi packages and building Python packages
# Using BuildKit cache mounts to speed up rebuilds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        python3-numpy \
        gnupg \
        curl \
        ca-certificates \
        gcc && \
    rm -rf /var/lib/apt/lists/*

# Add Raspberry Pi repository
RUN curl -Lfs https://archive.raspberrypi.org/debian/raspberrypi.gpg.key -o /tmp/raspberrypi.gpg.key && \
    gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key && \
    echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
    rm /tmp/raspberrypi.gpg.key

# Install picamera2 and libcamera from Raspberry Pi repository (to system Python)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-libcamera \
        python3-picamera2 && \
    rm -rf /var/lib/apt/lists/*

# Set up Python virtual environment and install dependencies
# Copy requirements.txt first for better layer caching
WORKDIR /app
COPY requirements.txt /app/
# Using BuildKit cache mount to speed up pip installs
# Install base requirements, then conditionally install opencv
# Using --break-system-packages flag required for pip on Debian 12+
# Exclude numpy from pip installation (using python3-numpy from apt for binary compatibility with simplejpeg)
RUN --mount=type=cache,target=/root/.cache/pip \
    grep -v "opencv-python-headless" requirements.txt | grep -v "numpy" > /tmp/requirements-base.txt && \
    pip3 install --break-system-packages -r /tmp/requirements-base.txt && \
    if [ "$INCLUDE_OPENCV" = "true" ]; then \
        echo "Installing opencv-python-headless for edge detection support..." && \
        grep "opencv-python-headless" requirements.txt | pip3 install --break-system-packages -r /dev/stdin; \
    else \
        echo "Skipping opencv-python-headless installation (INCLUDE_OPENCV=false)"; \
    fi

# ---- Final Stage ----
# The final image uses debian:bookworm-slim with system Python to ensure apt-installed
# python3-picamera2 is available in the same Python environment used by the application
FROM debian:bookworm-slim

# Install Python runtime and numpy (for binary compatibility with simplejpeg/picamera2)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-numpy && \
    rm -rf /var/lib/apt/lists/*

# Copy Raspberry Pi repository and keys from builder
COPY --from=builder /usr/share/keyrings/raspberrypi.gpg /usr/share/keyrings/raspberrypi.gpg
COPY --from=builder /etc/apt/sources.list.d/raspi.list /etc/apt/sources.list.d/raspi.list

# Install picamera2 and libcamera from Raspberry Pi repository
# Note: opencv removed from apt (python3-opencv was 250MB), now installed via pip as opencv-python-headless (40MB)
# Note: python3-flask removed (duplicate - installed via pip), libcap-dev and libcamera-dev removed (dev libraries not needed in runtime)
# Note: curl removed (replaced with Python-based healthcheck script)
# Note: pykms/python3-kms not installed as DrmPreview functionality is not used in headless streaming mode
# Using BuildKit cache mounts to speed up rebuilds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-libcamera \
        python3-picamera2 && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy Python packages from builder stage
# Debian Bookworm uses Python 3.11 by default
COPY --from=builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages

# Copy the application code
COPY pi_camera_in_docker /app

# Copy healthcheck script
COPY healthcheck.py /app/healthcheck.py
RUN chmod +x /app/healthcheck.py

# Validate required Python modules are present in the final image
RUN python3 -c "import sys; import numpy; import flask; import flask_cors; import picamera2; print('All required modules imported successfully')"

# Set the entry point
CMD ["python3", "/app/main.py"]
