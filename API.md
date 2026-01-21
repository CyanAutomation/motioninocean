# API Documentation

This document describes the HTTP endpoints provided by motion-in-ocean.

## Base URL

When running locally:
```
http://localhost:8000
```

When running in Docker (default):
```
http://127.0.0.1:8000
```

## Endpoints

### GET /

Main web interface for viewing the camera stream.

**Response:**
- HTML page with embedded video stream

**Example:**
```bash
curl http://localhost:8000/
```

---

### GET /health

Health check endpoint for liveness probes. Returns 200 if the service is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-21T10:00:00.000000"
}
```

**Status Codes:**
- `200 OK` - Service is running

**Example:**
```bash
curl http://localhost:8000/health
```

**Use Case:**
- Docker/Kubernetes liveness probes
- Load balancer health checks
- Monitoring systems

---

### GET /ready

Readiness probe endpoint. Checks if the camera is initialized and streaming.

**Response (Ready):**
```json
{
  "status": "ready",
  "timestamp": "2026-01-21T10:00:00.000000",
  "uptime_seconds": 123.45,
  "frames_captured": 1234,
  "current_fps": 30.5,
  "resolution": [640, 480],
  "edge_detection": false
}
```

**Response (Not Ready):**
```json
{
  "status": "not_ready",
  "reason": "Camera not initialized or recording not started",
  "timestamp": "2026-01-21T10:00:00.000000"
}
```

**Status Codes:**
- `200 OK` - Camera is ready and streaming
- `503 Service Unavailable` - Camera not yet initialized

**Example:**
```bash
curl http://localhost:8000/ready
```

**Use Case:**
- Kubernetes readiness probes
- Ensuring camera is operational before routing traffic
- Deployment verification

---

### GET /metrics

Metrics endpoint providing operational metrics in JSON format.

**Response:**
```json
{
  "camera_active": true,
  "frames_captured": 1234,
  "current_fps": 30.5,
  "uptime_seconds": 123.45,
  "resolution": [640, 480],
  "edge_detection": false,
  "timestamp": "2026-01-21T10:00:00.000000"
}
```

**Status Codes:**
- `200 OK` - Always returns metrics

**Example:**
```bash
curl http://localhost:8000/metrics
```

**Use Case:**
- Prometheus monitoring (convert to Prometheus format if needed)
- Grafana dashboards
- Operational monitoring
- Performance tracking

---

### GET /stream.mjpg

MJPEG video stream from the camera.

**Response:**
- Content-Type: `multipart/x-mixed-replace; boundary=frame`
- Continuous stream of JPEG frames

**Example:**
```bash
# View in a browser
open http://localhost:8000/stream.mjpg

# Download stream with curl (Ctrl+C to stop)
curl http://localhost:8000/stream.mjpg > stream.mjpg

# View with ffplay
ffplay -f mjpeg http://localhost:8000/stream.mjpg

# View with VLC
vlc http://localhost:8000/stream.mjpg
```

**Use Case:**
- Embedding in web pages
- Consuming in video clients (VLC, ffmpeg)
- OctoPrint camera integration
- Home Assistant camera integration

---

## Environment Configuration

Endpoints are affected by these environment variables:

| Variable | Default | Description | Affects Endpoints |
|----------|---------|-------------|-------------------|
| `RESOLUTION` | `640x480` | Camera resolution | `/ready`, `/metrics`, `/stream.mjpg` |
| `FPS` | `0` (camera default) | Frame rate limit | `/ready`, `/metrics`, `/stream.mjpg` |
| `EDGE_DETECTION` | `false` | Enable edge detection | `/ready`, `/metrics`, `/stream.mjpg` |
| `MOCK_CAMERA` | `false` | Use mock camera | All endpoints |
| `JPEG_QUALITY` | `100` | JPEG compression quality (1-100) | `/stream.mjpg` |
| `TZ` | System default | Timezone for timestamps | `/health`, `/ready`, `/metrics` |

## CORS

All endpoints support CORS (Cross-Origin Resource Sharing) to allow consumption from web applications on different origins.

**Headers:**
```
Access-Control-Allow-Origin: *
```

## Error Responses

### 404 Not Found

Returned when accessing an undefined endpoint.

```json
{
  "error": "Not Found"
}
```

### 503 Service Unavailable

Returned by `/ready` when camera is not initialized.

See `/ready` endpoint documentation above.

## Integration Examples

### Docker Compose Healthcheck

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Home Assistant Camera

```yaml
camera:
  - platform: mjpeg
    name: Pi Camera
    mjpeg_url: http://raspberry-pi:8000/stream.mjpg
```

### Prometheus Monitoring

The `/metrics` endpoint returns JSON. To convert to Prometheus format, use a JSON exporter or transform the data:

```python
import requests
from prometheus_client import Gauge, generate_latest

metrics = requests.get('http://localhost:8000/metrics').json()

frames_gauge = Gauge('camera_frames_captured', 'Total frames captured')
fps_gauge = Gauge('camera_fps', 'Current FPS')

frames_gauge.set(metrics['frames_captured'])
fps_gauge.set(metrics['current_fps'])
```

### Grafana Dashboard Query

If using Prometheus:
```promql
# Current FPS
camera_fps

# Frame rate over time
rate(camera_frames_captured[5m])
```

## Security Considerations

1. **Network Exposure**: By default, the service binds to `0.0.0.0:8000` for Docker compatibility. In production:
   - Use `127.0.0.1:8000:8000` in docker-compose for localhost-only access
   - Put behind a reverse proxy (nginx, Caddy, Traefik) with authentication
   - Never expose directly to the internet without authentication

2. **CORS**: The wide-open CORS policy (`origins: *`) is suitable for trusted networks. For production, restrict to specific origins:
   ```python
   CORS(app, resources={r"/*": {"origins": ["https://your-domain.com"]}})
   ```

3. **Authentication**: The endpoints have no built-in authentication. Add authentication via:
   - Reverse proxy (nginx basic auth, OAuth2 proxy)
   - Flask middleware
   - API gateway

## Rate Limiting

No built-in rate limiting is provided. For production, implement rate limiting via:
- Reverse proxy (nginx `limit_req_zone`)
- Flask-Limiter extension
- API gateway

## Monitoring Best Practices

1. Monitor `/health` for liveness
2. Monitor `/ready` for readiness
3. Track metrics from `/metrics`:
   - `current_fps` - Ensure it matches expected FPS
   - `frames_captured` - Verify continuous operation
   - `uptime_seconds` - Track service stability
4. Alert on:
   - FPS drops below threshold
   - Service not ready for extended period
   - Camera initialization failures (check logs)
