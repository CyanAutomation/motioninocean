#!/usr/bin/python3

import os
import cv2
import io
import logging
import json
import time
import numpy as np
from collections import deque
from threading import Condition
from flask import Flask, Response, render_template, jsonify
from datetime import datetime

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.array import MappedArray

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
resolution_str = os.environ.get("RESOLUTION", "640x480")
edge_detection_str = os.environ.get("EDGE_DETECTION", "false")
fps_str = os.environ.get("FPS", "0")  # 0 = use camera default
mock_camera_str = os.environ.get("MOCK_CAMERA", "false")
jpeg_quality_str = os.environ.get("JPEG_QUALITY", "100")

mock_camera = mock_camera_str.lower() in ('true', '1', 't')
logger.info(f"Mock camera enabled: {mock_camera}")

# Parse resolution
try:
    resolution = tuple(map(int, resolution_str.split('x')))
    # Validate resolution dimensions
    if len(resolution) != 2 or resolution[0] <= 0 or resolution[1] <= 0:
        logger.warning(f"Invalid RESOLUTION dimensions {resolution}. Using default 640x480.")
        resolution = (640, 480)
    elif resolution[0] > 4096 or resolution[1] > 4096:
        logger.warning(f"RESOLUTION {resolution} exceeds maximum 4096x4096. Using default 640x480.")
        resolution = (640, 480)
    else:
        logger.info(f"Camera resolution set to {resolution}")
except (ValueError, TypeError):
    logger.warning("Invalid RESOLUTION format. Using default 640x480.")
    resolution = (640, 480)

# Parse edge detection flag
edge_detection = edge_detection_str.lower() in ('true', '1', 't')
logger.info(f"Edge detection: {edge_detection}")

# Parse FPS
try:
    fps = int(fps_str)
    # Validate FPS value
    if fps < 0:
        logger.warning(f"FPS cannot be negative ({fps}). Using camera default.")
        fps = 0
    elif fps > 120:
        logger.warning(f"FPS {fps} exceeds recommended maximum of 120. Using 120.")
        fps = 120
    else:
        logger.info(f"Frame rate limited to {fps} FPS" if fps > 0 else "Using camera default FPS")
except (ValueError, TypeError):
    logger.warning("Invalid FPS format. Using camera default.")
    fps = 0

# Parse JPEG quality
try:
    jpeg_quality = int(jpeg_quality_str)
    # Validate JPEG quality value
    if jpeg_quality < 1 or jpeg_quality > 100:
        logger.warning(f"JPEG_QUALITY {jpeg_quality} out of range (1-100). Using default 100.")
        jpeg_quality = 100
    else:
        logger.info(f"JPEG quality set to {jpeg_quality}")
except (ValueError, TypeError):
    logger.warning("Invalid JPEG_QUALITY format. Using default 100.")
    jpeg_quality = 100

def apply_edge_detection(request):
    try:
        with MappedArray(request, "main") as m:
            # Convert to grayscale
            grey = cv2.cvtColor(m.array, cv2.COLOR_BGR2GRAY)
            # Apply Canny edge detection
            edges = cv2.Canny(grey, 100, 200)
            # Convert back to BGR so it can be encoded as JPEG
            edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            # Copy the result back to the mapped array
            np.copyto(m.array, edges_bgr)
    except Exception as e:
        logger.error(f"Edge detection processing failed: {e}", exc_info=True)

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.frame_times = deque(maxlen=30)  # Fixed-size deque prevents memory leak

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.frame_count += 1
            # Track frame timing for FPS calculation
            now = time.time()
            self.frame_times.append(now)  # deque automatically maintains maxlen=30
            self.condition.notify_all()

    def get_fps(self):
        """Calculate actual FPS from frame times"""
        if len(self.frame_times) < 2:
            return 0.0
        time_span = self.frame_times[-1] - self.frame_times[0]
        if time_span == 0:
            return 0.0
        return (len(self.frame_times) - 1) / time_span

    def get_status(self):
        """Return current streaming status"""
        return {
            "frames_captured": self.frame_count,
            "current_fps": round(self.get_fps(), 2),
            "resolution": resolution,
            "edge_detection": edge_detection
        }

app = Flask(__name__, static_folder='static', static_url_path='/static')
output = StreamingOutput()
app.start_time = datetime.now()
picam2_instance = None
recording_started = False  # Track if camera recording has actually started

@app.route('/')
def index():
    return render_template("index.html", width=resolution[0], height=resolution[1])

@app.route('/health')
def health():
    """Health check endpoint - returns 200 if service is running"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

@app.route('/ready')
def ready():
    """Readiness probe - checks if camera is actually streaming"""
    global recording_started
    
    if not recording_started:
        return jsonify({
            "status": "not_ready",
            "reason": "Camera not initialized or recording not started",
            "timestamp": datetime.now().isoformat()
        }), 503
    
    return jsonify({
        "status": "ready",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - app.start_time).total_seconds(),
        **output.get_status()
    }), 200

def gen():
    try:
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except Exception as e:
        logger.warning(f'Streaming client disconnected: {e}')

@app.route('/stream.mjpg')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    picam2_instance = None
    if mock_camera:
        logger.info("MOCK_CAMERA enabled. Skipping Picamera2 initialization and generating dummy frames.")
        # Create a dummy black image
        dummy_image = np.zeros((resolution[1], resolution[0], 3), dtype=np.uint8)
        dummy_image_jpeg = cv2.imencode('.jpg', dummy_image)[1].tobytes()

        # Simulate camera streaming for the StreamingOutput
        def generate_mock_frames():
            global recording_started
            recording_started = True  # Mark as started for mock mode
            while True:
                time.sleep(1 / (fps if fps > 0 else 10)) # Simulate FPS
                output.write(dummy_image_jpeg)
        
        import threading
        mock_thread = threading.Thread(target=generate_mock_frames)
        mock_thread.daemon = True
        mock_thread.start()

        # Start the Flask app
        logger.info("Starting Flask server on 0.0.0.0:8000 with mock camera.")
        app.run(host='0.0.0.0', port=8000, threaded=True)

    else:
        try:
            logger.info("Initializing Picamera2...")
            picam2_instance = Picamera2()
            
            logger.info(f"Configuring video: resolution={resolution}, format=BGR888, fps={fps if fps > 0 else 'default'}")
            # Configure for BGR format for opencv
            config_params = {"size": resolution, "format": "BGR888"}
            if fps > 0:
                config_params["framerate"] = fps
            video_config = picam2_instance.create_video_configuration(
                main=config_params
            )
            picam2_instance.configure(video_config)

            if edge_detection:
                logger.info("Enabling edge detection preprocessing")
                picam2_instance.pre_callback = apply_edge_detection
            
            logger.info("Starting camera recording...")
            # Start recording with configured JPEG quality
            picam2_instance.start_recording(JpegEncoder(q=jpeg_quality), FileOutput(output))
            
            # Mark recording as started only after start_recording succeeds
            global recording_started
            recording_started = True
            logger.info(f"Camera recording started successfully (JPEG quality: {jpeg_quality})")

            # Start the Flask app
            logger.info("Starting Flask server on 0.0.0.0:8000")
            app.run(host='0.0.0.0', port=8000, threaded=True)
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing camera device: {e}")
            logger.error("Ensure the container has proper device access (--device mappings or --privileged)")
            raise
        except RuntimeError as e:
            logger.error(f"Camera initialization failed: {e}")
            logger.error("Verify camera is enabled on the host and working (rpicam-hello test)")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}", exc_info=True)
            raise
        finally:
            # Stop recording safely
            if picam2_instance is not None:
                try:
                    if picam2_instance.started:
                        logger.info("Stopping camera recording...")
                        picam2_instance.stop_recording()
                        logger.info("Camera recording stopped")
                except Exception as e:
                    logger.error(f"Error during camera shutdown: {e}", exc_info=True)
            logger.info("Application shutdown complete")