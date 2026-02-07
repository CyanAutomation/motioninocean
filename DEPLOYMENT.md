# Motion in Ocean - Multi-Host Deployment Guide

This guide covers deploying Motion in Ocean across multiple hosts on a local network, with management mode on one host coordinating webcam mode instances on remote hosts.

## Table of Contents

- [Architecture](#architecture)
- [Scenario 1: HTTP-Based Remote Access](#scenario-1-http-based-remote-access-recommended)
- [Scenario 2: Docker Socket Proxy](#scenario-2-docker-socket-proxy-advanced)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

---

## Architecture

Motion in Ocean supports a hub-and-spoke architecture where:

- **Management Host**: Runs `management` profile; provides control plane and web UI
- **Webcam Hosts**: Run `webcam` profile; stream video and provide health/status endpoints
- **Communication**: Management mode probes remote endpoints and aggregates status via HTTP

```
┌─────────────────────────────────────────────────────────────────┐
│ Local Network (192.168.1.0/24)                                  │
├──────────────────────────────────────┬──────────────────────────┤
│                                      │                          │
│  Management Host                     │  Webcam Host 1           │
│  (192.168.1.100)                     │  (192.168.1.101)         │
│  ┌──────────────────────────┐        │  ┌──────────────────┐    │
│  │  Motion in Ocean         │        │  │  Motion in Ocean │    │
│  │  Management Mode         │        │  │  Webcam Mode     │    │
│  │  - Web UI (port 8001)    │        │  │  - Stream        │    │
│  │  - API (port 8001)       │        │  │    (port 8000)   │    │
│  │  - Node Registry         │        │  │  - Health Check  │    │
│  │  ◄──── HTTP GET/POST ─────┼─HTTP──────► /health          │    │
│  └──────────────────────────┘        │  │  /ready          │    │
│                                      │  │  /metrics        │    │
│  ┌──────────────────────────┐        │  └──────────────────┘    │
│  │  Browser / Client        │        │                          │
│  │  http://192.168.1.100:   │        └──────────────────────────┘
│  │  8001/management         │
│  └──────────────────────────┘        ┌──────────────────────────┐
│                                      │  Webcam Host 2           │
│                                      │  (192.168.1.102)         │
│                                      │  ┌──────────────────┐    │
│                                      │  │  Motion in Ocean │    │
│                                      │  │  Webcam Mode     │    │
│                                      │  │  - Stream        │    │
│                                      │  │    (port 8000)   │    │
│                                      │  └──────────────────┘    │
│                                      └──────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: HTTP-Based Remote Access (Recommended)

HTTP-based access is the recommended approach for most deployments:

- ✅ Simple setup, no special configuration needed beyond binding to network interface
- ✅ Works across any network (local, VPN, etc.)
- ✅ Full support for management operations (status, health checks)
- ✅ Built-in SSRF protections

### Prerequisites

- Management host and webcam hosts on same local network or accessible via routing
- No firewall rules blocking port 8000 (or custom port) between hosts
- Network connectivity confirmed (`ping` between hosts)

### Step 1: Configure Webcam Host

On **each webcam host**, expose the service to the network:

```bash
# Set environment variables to expose service beyond localhost
export MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
export MOTION_IN_OCEAN_PORT=8000

# Start webcam mode
docker-compose --profile webcam up -d
```

Or using `.env` file:

```bash
# .env on webcam host
MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
MOTION_IN_OCEAN_PORT=8000
MOTION_IN_OCEAN_RESOLUTION=640x480
MOTION_IN_OCEAN_FPS=30
MOTION_IN_OCEAN_JPEG_QUALITY=90
```

Then:

```bash
docker-compose --profile webcam up -d
```

### Step 2: Verify Webcam Host Connectivity

From the management host, test connectivity to the webcam host:

```bash
# Test basic connectivity (replace 192.168.1.101 with actual IP)
curl -X GET http://192.168.1.101:8000/health

# Expected response: {"status": "ok"}
```

Test the ready endpoint:

```bash
curl -X GET http://192.168.1.101:8000/ready

# Expected response: {"status": "ready"} (or "waiting" if camera not yet streaming)
```

### Step 3: Configure Management Host

On the **management host**, set up management mode:

```bash
# .env on management host
MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
MOTION_IN_OCEAN_MANAGEMENT_PORT=8001
```

Then:

```bash
docker-compose --profile management up -d
```

### Step 4: Add Nodes via Management UI

1. Open browser to `http://<management-host-ip>:8001/management`
   - Example: `http://192.168.1.100:8001/management`

2. Navigate to "Nodes" or "Add Node" section

3. Create a new node with these details:

   ```json
   {
     "name": "Camera 1",
     "base_url": "http://192.168.1.101:8000",
     "transport": "http",
     "auth": {
       "type": "none"
     },
     "labels": {
       "location": "living-room",
       "device": "pi3"
     }
   }
   ```

   Or via API:

   ```bash
   curl -X POST http://192.168.1.100:8001/api/nodes \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Camera 1",
       "base_url": "http://192.168.1.101:8000",
       "transport": "http",
       "labels": {"location": "living-room"}
     }'
   ```

### Step 5: Verify Node Status

Check if management can reach the node:

```bash
curl -X GET http://192.168.1.100:8001/api/nodes/<node_id>/status

# Expected response includes: "stream_available": true/false, "status": "ok"/"error"
```

Or access management overview:

```bash
curl -X GET http://192.168.1.100:8001/api/management/overview

# Shows summary of all nodes and stream availability
```

---

## Scenario 2: Docker Socket Proxy (Advanced)

Docker Socket Proxy enables management mode to communicate with remote Docker hosts via the Docker API. This is useful in Docker-native environments where you want direct API access.

⚠️ **Advanced feature**: Only use if you need Docker API access; HTTP transport is simpler for most use cases.

### Prerequisites

- Docker running on both management and webcam hosts
- Both hosts accessible via Docker socket proxy
- Admin role token configured (if using auth)

### Step 1: Enable docker-socket-proxy on Webcam Host

On **each webcam host**, enable docker-socket-proxy:

```bash
# .env on webcam host
ENABLE_DOCKER_SOCKET_PROXY=true
DOCKER_PROXY_PORT=2375
MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
```

Then:

```bash
# Start webcam mode AND docker-socket-proxy service
docker-compose --profile webcam --profile docker-socket-proxy up -d
```

### Step 2: Verify docker-socket-proxy Access

From management host, test docker-socket-proxy connectivity:

```bash
# Replace 192.168.1.101 with actual webcam host IP
curl -X GET http://192.168.1.101:2375/version

# Expected response: {"Version": "...", "Os": "...", ...}
```

### Step 3: Configure Management Host

On **management host**, enable docker socket mounting (required for docker transport):

Uncomment the docker socket volume in `docker-compose.override.yaml`:

```yaml
services:
  motion-in-ocean-management:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

Then start management mode:

```bash
# .env on management host
MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
MOTION_IN_OCEAN_MANAGEMENT_PORT=8001

docker-compose --profile management up -d
```

### Step 4: Add Docker-Based Node

Create a node with docker transport type:

```bash
curl -X POST http://192.168.1.100:8001/api/nodes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "name": "Docker Node 1",
    "base_url": "docker://192.168.1.101:2375",
    "transport": "docker",
    "auth": {"type": "none"},
    "labels": {"environment": "docker-swarm"}
  }'
```

### Step 5: Status Limitations (Docker Transport)

⚠️ **Note**: Docker transport nodes currently return `TRANSPORT_UNSUPPORTED` for status endpoints. This is a planned feature. Use HTTP transport for production status checks.

---

## Troubleshooting

### Nodes Not Connecting

**Symptom**: Management UI shows node as "unavailable" or error when fetching status

**Diagnosis**:

1. Verify network connectivity:

   ```bash
   # From management host to webcam host
   ping 192.168.1.101
   ```

2. Verify port is open:

   ```bash
   # Test port 8000 on webcam host from management host
   nc -zv 192.168.1.101 8000
   # or with curl
   curl -v http://192.168.1.101:8000/health
   ```

3. Check firewall rules:

   ```bash
   # On webcam host
   sudo ufw status  # Ubuntu/Debian
   sudo firewall-cmd --list-ports  # RedHat/CentOS
   ```

4. Verify MOTION_IN_OCEAN_BIND_HOST is set to 0.0.0.0 or correct interface

**Solution**:

```bash
# On webcam host, ensure port is not localhost-only
export MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
docker-compose --profile webcam restart
```

### Management Cannot Reach Webcam (Connection Refused)

**Symptom**: 
```
curl: (7) Failed to connect to 192.168.1.101 port 8000: Connection refused
```

**Diagnosis**:

1. Verify container is running:

   ```bash
   # On webcam host
   docker ps | grep motion-in-ocean
   ```

2. Check container logs:

   ```bash
   docker logs motion-in-ocean
   ```

3. Verify port binding:

   ```bash
   docker port motion-in-ocean
   # Should show: 8000/tcp -> 0.0.0.0:8000 (or specific interface)
   ```

**Solution**:

- Ensure `MOTION_IN_OCEAN_BIND_HOST` is set to 0.0.0.0, not 127.0.0.1
- Restart container: `docker-compose --profile webcam restart`

### Health/Ready Endpoint Returns 503

**Symptom**:
```
curl http://192.168.1.101:8000/ready
{"status": "waiting"}  # or error
```

**Diagnosis**:

1. Camera may not be initialized or streaming yet
2. Camera device not found or misconfigured
3. Run `./detect-devices.sh` to verify device availability

**Solution**:

- Wait 30-60 seconds for camera initialization
- Check `docker logs motion-in-ocean` for device errors
- See [pi-camera-troubleshooting skill](/.github/skills/pi-camera-troubleshooting/SKILL.md) for detailed camera diagnostics

### Docker Socket Proxy Permission Denied

**Symptom**:
```
curl: (7) Failed to connect to 192.168.1.101 port 2375: Permission denied
```

**Diagnosis**:

1. Verify docker-socket-proxy container is running:

   ```bash
   docker ps | grep docker-socket-proxy
   ```

2. Check docker socket permissions on host:

   ```bash
   ls -l /var/run/docker.sock
   # Should be readable by docker group
   ```

3. Verify port binding:

   ```bash
   docker port docker-socket-proxy
   ```

**Solution**:

```bash
# Re-enable docker-socket-proxy with correct permissions
export ENABLE_DOCKER_SOCKET_PROXY=true
docker-compose --profile docker-socket-proxy up -d docker-socket-proxy
```

### Node Registry File Not Found

**Symptom**:
```
ERROR: Node registry file not found at /data/node-registry.json
```

**Diagnosis**:

1. Verify volume is mounted:

   ```bash
   docker inspect motion-in-ocean-management | grep Mounts -A 10
   ```

2. Check data directory permissions:

   ```bash
   ls -ld /data  # On host
   ```

**Solution**:

```bash
# Ensure /data directory exists and has correct permissions
mkdir -p /data
chmod 755 /data
docker-compose --profile management restart
```

---

## Security Considerations

### Default Security Posture

Motion in Ocean uses **security-first defaults**:

1. **Localhost Binding**: Services bind to `127.0.0.1` by default
   - Prevents accidental exposure to network
   - Explicit opt-in required via `MOTION_IN_OCEAN_BIND_HOST=0.0.0.0`

2. **SSRF Protection**: Management mode blocks requests to:
   - Localhost and loopback addresses
   - Private/RFC1918 address ranges
   - Link-local addresses
   - Reserved address ranges
   - Metadata services (e.g., AWS, GCP metadata endpoints)

3. **No Authentication by Default**: On trusted local networks, authentication is optional
   - Enable `MANAGEMENT_AUTH_REQUIRED=true` for multi-tenant scenarios

### Recommendations for Local Network Deployment

1. **Firewall Configuration**:
   - Restrict port access to trusted hosts/subnets
   - Example (UFW):
     ```bash
     sudo ufw allow from 192.168.1.0/24 to any port 8000
     sudo ufw allow from 192.168.1.0/24 to any port 8001
     sudo ufw allow from 192.168.1.0/24 to any port 2375
     ```

2. **Network Segmentation**:
   - Keep management and webcam hosts on same VLAN
   - Isolate from guest/untrusted networks

3. **Authentication for Production**:
   - Enable bearer token roles:
     ```bash
     MANAGEMENT_AUTH_REQUIRED=true
     MANAGEMENT_TOKEN_ROLES="token1:admin,token2:user"
     ```
   - Include tokens in node registry for HTTP transport nodes
   - Require admin role for docker transport

4. **Docker Socket Proxy Hardening**:
   - Only enable on trusted hosts
   - Use UFW or similar to restrict proxy port access
   - Consider running docker-socket-proxy in separate network namespace

### DO NOT

- ❌ Expose management/webcam ports to the internet without strong authentication
- ❌ Use docker transport on untrusted networks
- ❌ Store credentials in plaintext in docker-compose.yaml (use .env with gitignore)
- ❌ Run with `--privileged` flag unless absolutely necessary

---

## See Also

- [README.md](README.md) - Quick start guide
- [README.md#multi-host-deployment](README.md#multi-host-deployment) - Quick reference
- [SECURITY.md](SECURITY.md) - Security policy and reporting
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development and testing
- [pi-camera-troubleshooting skill](/.github/skills/pi-camera-troubleshooting/SKILL.md) - Camera diagnostics

