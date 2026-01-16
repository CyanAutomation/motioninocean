# ---- Builder Stage ----
# This stage is responsible for adding the Raspberry Pi repository and its keys.
FROM debian:bookworm AS builder

# Install dependencies needed for fetching RPi packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Add Raspberry Pi repository
RUN curl -Lfs https://archive.raspberrypi.org/debian/raspberrypi.gpg.key -o /tmp/raspberrypi.gpg.key && \
    gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg /tmp/raspberrypi.gpg.key && \
    echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list && \
    rm /tmp/raspberrypi.gpg.key

# ---- Final Stage ----
# The final image is based on debian:bookworm-slim to reduce size.
FROM debian:bookworm-slim

# Copy Raspberry Pi repository and keys from builder
COPY --from=builder /usr/share/keyrings/raspberrypi.gpg /usr/share/keyrings/raspberrypi.gpg
COPY --from=builder /etc/apt/sources.list.d/raspi.list /etc/apt/sources.list.d/raspi.list

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-opencv \
        python3-flask \
        python3-pip \
        curl && \
    pip3 install --break-system-packages picamera2 && \
    apt-get clean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the application code
COPY pi_camera_in_docker /app

# Set the entry point
CMD ["python3", "/app/main.py"]
