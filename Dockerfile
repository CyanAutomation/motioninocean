# ---- Builder Stage ----
# This stage is responsible for adding the Raspberry Pi repository and building Python packages.
# Using python:3.11-slim-bookworm provides optimized Python with pip pre-installed
FROM python:3.11-slim-bookworm AS builder

# Install dependencies needed for fetching RPi packages and building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gnupg \
        curl \
        ca-certificates \
        gcc \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Add Raspberry Pi repository
RUN curl -Lfs https://archive.raspberrypi.org/debian/raspberrypi.gpg.key -o /tmp/raspberrypi.gpg.key && \
    gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key && \
    echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
    rm /tmp/raspberrypi.gpg.key

# Set up Python virtual environment and install dependencies
WORKDIR /app
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# ---- Final Stage ----
# The final image is based on python:3.11-slim-bookworm (optimized Python runtime, ~40MB smaller than debian:bookworm-slim + python3)
FROM python:3.11-slim-bookworm

# Copy Raspberry Pi repository and keys from builder
COPY --from=builder /usr/share/keyrings/raspberrypi.gpg /usr/share/keyrings/raspberrypi.gpg
COPY --from=builder /etc/apt/sources.list.d/raspi.list /etc/apt/sources.list.d/raspi.list

# Install only runtime dependencies (no gcc or python3-dev)
# Note: opencv removed from apt (python3-opencv was 250MB), now installed via pip as opencv-python-headless (40MB)
# Note: python3-flask removed (duplicate - installed via pip), libcap-dev and libcamera-dev removed (dev libraries not needed in runtime)
# Note: curl removed (replaced with Python-based healthcheck script)
# Note: python3-pip not needed (included in python:3.11-slim-bookworm base image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-libcamera \
        python3-picamera2 && \
    # Clean up
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Note: pykms/python3-kms not installed as DrmPreview functionality is not used
# in headless streaming mode. Mock modules in main.py handle picamera2 import.
# Note: gcc and python3-dev removed from runtime - built in builder stage

# Set the working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages

# Copy the application code
COPY pi_camera_in_docker /app

# Copy healthcheck script
COPY healthcheck.py /app/healthcheck.py
RUN chmod +x /app/healthcheck.py

# Set the entry point
CMD ["python3", "/app/main.py"]
