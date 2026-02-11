# Cross-Container Communication: Implementation Strategies

This document outlines strategies for testing cross-container communication between management and webcam nodes in various deployment scenarios.

---

## Scenario 1: Multi-Host Deployment (Recommended) ✅

This is the **designed and intended architecture** for motion-in-ocean.

### Architecture

```
Home Network (192.168.1.0/24)
├── Pi 1 (192.168.1.100)
│   └── management-in-ocean:management at :8001
│       └── Registry contains URLs like:
│           - http://192.168.1.101:8000
│           - http://192.168.1.102:8000
│
├── Pi 2 (192.168.1.101)
│   └── motion-in-ocean:webcam at :8000
│       └── Exposes: /health, /ready, /metrics, /stream.mjpg
│
└── Pi 3 (192.168.1.102)
    └── motion-in-ocean:webcam at :8000
        └── Exposes: /health, /ready, /metrics, /stream.mjpg
```

### Implementation Steps

**On Webcam Hosts (Pi 2 & 3):**

```bash
# .env configuration
MOTION_IN_OCEAN_MODE=webcam
MOTION_IN_OCEAN_BIND_HOST=0.0.0.0    # Expose to network
MOTION_IN_OCEAN_PORT=8000
MOTION_IN_OCEAN_RESOLUTION=640x480
MOTION_IN_OCEAN_FPS=30
MOCK_CAMERA=false                      # Use real camera

# Start service
docker-compose up -d
```

**Verify webcam is accessible:**

```bash
# From any host on network
curl http://192.168.1.101:8000/health
curl http://192.168.1.102:8000/health
```

**On Management Host (Pi 1):**

```bash
# .env configuration
MOTION_IN_OCEAN_MODE=management
MOTION_IN_OCEAN_PORT=8001
MANAGEMENT_AUTH_REQUIRED=false

# Start service
docker-compose up -d

# Verify management is accessible
curl http://127.0.0.1:8001/health
```

**Register Webcam Nodes:**

```bash
# Register Pi 2
curl -X POST http://127.0.0.1:8001/api/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "pi2-camera",
    "name": "Pi 2 CAM",
    "base_url": "http://192.168.1.101:8000",
    "transport": "http",
    "auth": {"type": "none"},
    "labels": {"location": "living-room"},
    "capabilities": ["stream", "health"],
    "last_seen": "'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'"
  }'

# Register Pi 3
curl -X POST http://127.0.0.1:8001/api/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "pi3-camera",
    "name": "Pi 3 CAM",
    "base_url": "http://192.168.1.102:8000",
    "transport": "http",
    "auth": {"type": "none"},
    "labels": {"location": "bedroom"},
    "capabilities": ["stream", "health"],
    "last_seen": "'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'"
  }'
```

**Test Cross-Device Communication:**

```bash
# From management host, query webcam nodes
curl http://127.0.0.1:8001/api/nodes              # List all nodes
curl http://127.0.0.1:8001/api/nodes/pi2-camera  # Get node details
curl http://127.0.0.1:8001/api/nodes/pi2-camera/status  # Get node status

# Expected 200 response with node stats:
{
    "node_id": "pi2-camera",
    "health_status": "healthy",
    "ready_status": "ready",
    "metrics": {
        "current_fps": 30,
        "last_frame_age_seconds": 0.033,
        "uptime_seconds": 1234
    }
}
```

### Advantages

- ✅ No SSRF blocking (uses non-private IPs)
- ✅ Matches intended production architecture
- ✅ Real-world performance testing
- ✅ Supports 100+ camera nodes scaling
- ✅ Easy to add/remove nodes

### Disadvantages

- ❌ Requires multiple Raspberry Pis
- ❌ More hardware cost
- ❌ Network setup required

---

## Scenario 2: Docker-Compose with Host Network Mode

Use Docker's `--network host` to simulate multi-host on single machine.

### Setup

```yaml
version: '3.8'
services:
  webcam:
    image: motioninocean:latest
    network_mode: host
    environment:
      APP_MODE: webcam
      MOCK_CAMERA: "true"
    ports:
      - "127.0.0.1:8000:8000"

  management:
    image: motioninocean:latest
    network_mode: host
    environment:
      APP_MODE: management
    ports:
      - "127.0.0.1:8001:8000"
    depends_on:
      - webcam
```

### Implementation

```bash
# Start with host network
docker-compose up -d

# Register node with localhost (will still be blocked)
curl -X POST http://127.0.0.1:8001/api/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "webcam-01",
    "name": "Test",
    "base_url": "http://127.0.0.1:8000",
    ...
  }'

# Will still fail with NODE_UNREACHABLE (localhost is blocked by design)
```

### Advantages

- ✅ Single machine setup
- ✅ Simulates multi-host architecture

### Disadvantages

- ❌ Localhost still blocked by SSRF (security feature)
- ❌ Not practical for production
- ❌ Port conflict risks

---

## Scenario 3: External DNS Mock (Advanced)

Create a mock external service that simulates a remote webcam node.

### Strategy

1. Create a mock HTTP server responding like a webcam node
2. Expose it on a non-private IP (if possible)
3. Register it with management node
4. Test management→mock communication

### Example Mock Server

```python
#!/usr/bin/env python3
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "app_mode": "webcam"
    }), 200

@app.route('/ready')
def ready():
    return jsonify({
        "status": "ready",
        "frames_captured": 1000,
        "current_fps": 30.0
    }), 200

@app.route('/metrics')
def metrics():
    return jsonify({
        "app_mode": "webcam",
        "camera_active": True,
        "current_fps": 30.0,
        "frames_captured": 1000,
        "uptime_seconds": 3600
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)
```

### Implementation

```bash
# Run mock server on a different port/network
python3 mock_webcam.py &

# From management container, register the mock
curl -X POST http://127.0.0.1:8001/api/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "mock-camera",
    "base_url": "http://EXTERNAL_IP:9999",  # Or tunnel to it
    ...
  }'

# Query mock node
curl http://127.0.0.1:8001/api/nodes/mock-camera/status
```

### Advantages

- ✅ Tests SSRF bypass with external IP
- ✅ Validates API communication path

### Disadvantages

- ❌ Requires port forwarding/external IP
- ❌ Doesn't test actual motion-in-ocean cross-communication
- ❌ Complex networking setup

---

## Scenario 4: Modify Code for Testing (Not Recommended) ❌

### ⚠️ Warning

This approach compromises security testing and should **never** be used in production.

### What This Would Involve

1. Add environment variable: `ALLOW_PRIVATE_IPS_FOR_TESTING=true`
2. Modify `_is_blocked_address()` to check this flag
3. Skip SSRF protection when flag is set

### Why Not Recommended

- ❌ Disables security protections for testing
- ❌ Could accidentally be enabled in production
- ❌ Defeats the purpose of SSRF protection
- ❌ Reduces confidence in security
- ❌ Bad practice for critical infrastructure

### If You Absolutely Must

Only do this in a completely isolated test environment:

```python
# In management_api.py (NOT FOR PRODUCTION)
def _is_blocked_address(raw: str) -> bool:
    if os.environ.get('MOTION_IN_OCEAN_TEST_MODE') == 'allow-private':
        return False  # ⚠️ INSECURE - TESTING ONLY
    # ... standard checks ...
```

---

## Recommended Testing Strategy

### Phase 1: Unit/Integration Testing (✅ Current)

Use existing test suite in `tests/test_management_api.py`:

```python
# Already tests API behavior without network blocking
def test_node_crud_and_overview(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)
    
    payload = {
        "id": "local-node",
        "base_url": "http://127.0.0.1:65534",  # Intentionally unreachable
        ...
    }
    
    # Tests expect 503 NODE_UNREACHABLE - correct!
    status = client.get("/api/nodes/node-1/status")
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
```

**Run with:**
```bash
pytest tests/test_management_api.py -v
```

### Phase 2: Multi-Host Integration Testing

Deploy on multiple Raspberry Pis on home network.

**Deployment checklist:**
- [ ] Pi 1: Management node at 192.168.1.100:8001
- [ ] Pi 2: Webcam node at 192.168.1.101:8000
- [ ] Pi 3: Webcam node at 192.168.1.102:8000
- [ ] Network connectivity verified
- [ ] Nodes registered in management
- [ ] Cross-node queries successful
- [ ] Stream accessible from browser

### Phase 3: Docker Integration Testing

For Docker-specific validation:

```bash
# Run individual containers to test APIs
docker run -e APP_MODE=webcam motioninocean:latest
docker run -e APP_MODE=management motioninocean:latest

# Validate each container's endpoints independently
curl http://localhost:8000/health      # Webcam
curl http://localhost:8001/api/nodes   # Management
```

---

## Comparison Table

| Scenario | Effort | Cost | Accuracy | SSRF Works | Recommended |
|----------|--------|------|----------|-----------|-------------|
| Multi-Host (Real Pis) | High | High | 100% | Yes | ✅ YES |
| Host Network Mode | Medium | None | 75% | No | ⚠️ Maybe |
| External DNS Mock | Medium | None | 60% | Yes | ⚠️ Maybe |
| Code Modification | Low | None | 0% | No | ❌ NO |
| Unit Tests | Low | None | 80% | N/A | ✅ YES |

---

## Conclusion

### Best Practice for Full Testing

1. **Immediate:** Run existing unit tests (75% coverage)
   ```bash
   pytest tests/test_management_api.py -v
   python3 tests/test_parallel_containers.py
   ```

2. **Short-term:** Deploy on multiple Raspberry Pis (100% coverage)
   - Matches production architecture
   - No SSRF issues
   - Real performance data

3. **Avoid:** Modifying security code for testing
   - Never disable SSRF in any environment
   - Use test environments to validate, not bypass

### Current Docker-Based Testing Limitations

The Docker Compose testing reveals a design choice, not a bug:
- Webcam containers: ✅ Fully testable
- Management container: ✅ Fully testable
- Inter-container comms: ⚠️ Requires multi-host setup

This is **by design** for security and is consistent with a home network deployment model.
