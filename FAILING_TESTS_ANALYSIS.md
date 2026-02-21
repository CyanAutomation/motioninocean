# Failing Tests Analysis - Motion In Ocean

## Overview

This document provides detailed analysis of 2 failing tests in the Motion In Ocean test suite, with root cause identification and recommended fixes.

---

## Test 1: `test_webcam_compose_contract_basics`

### Test Location

- **File**: [tests/test_config.py](tests/test_config.py)
- **Lines**: 14-36
- **Test Class**: N/A (module-level function)
- **Method**: `test_webcam_compose_contract_basics(workspace_root)`

### Test Code

```python
def test_webcam_compose_contract_basics(workspace_root):
    """Webcam compose file should parse and expose core service runtime contracts."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"
    assert compose_file.exists(), "docker-compose.yaml not found"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert "services" in config
    assert "motion-in-ocean" in config["services"]

    service = config["services"]["motion-in-ocean"]
    required_fields = ["image", "restart", "ports", "healthcheck"]

    for field in required_fields:
        assert field in service, f"Missing required field: {field}"

    assert "environment" in service or "env_file" in service

    healthcheck = service.get("healthcheck", {})
    assert "test" in healthcheck, "Missing healthcheck test"
    assert "/health" in str(healthcheck.get("test")), "Healthcheck should use /health endpoint"
```

### What the Test Expects

1. The docker-compose.yaml should exist and parse as valid YAML
2. The `motion-in-ocean` service should have: `image`, `restart`, `ports`, and `healthcheck` fields
3. The service should have either `environment` or `env_file`
4. **Key Assertion**: The healthcheck `test` field should contain the string `/health`

### What It Actually Gets

The healthcheck in the docker-compose.yaml is:

```yaml
healthcheck:
  test:
    [
      "CMD-SHELL",
      'python3 -c "import socket; socket.create_connection((''localhost'', 8000), timeout=3)" 2>/dev/null || exit 1',
    ]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

**Actual healthcheck test string**:

```
['CMD-SHELL', 'python3 -c "import socket; socket.create_connection((\'localhost\', 8000), timeout=3)" 2>/dev/null || exit 1']
```

**Does it contain `/health`?** ❌ No - it uses a socket connection test instead.

### Error Output

```
AssertionError: Healthcheck should use /health endpoint
assert '/health' in '[\'CMD-SHELL\', \'python3 -c "import socket; socket.create_connection((\\\'localhost\\\', 8000), timeout=3)" 2>/dev/null || exit 1\']'
```

### Root Cause Analysis

| Category           | Finding                                                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Issue Type**     | TEST/CODE MISMATCH                                                                                                                                                       |
| **Root Cause**     | The test expects the healthcheck to query the `/health` endpoint, but the docker-compose.yaml uses a socket connection test that directly checks port 8000 availability. |
| **Responsibility** | This is a design/contract mismatch between test expectations and actual implementation.                                                                                  |
| **Impact**         | The healthcheck works correctly (tests basic connectivity), but doesn't validate the application's actual `/health` endpoint.                                            |

### Is This a Bug?

**In the Test?** It depends on architectural intent:

- If the healthcheck **should** query the `/health` endpoint (to validate app readiness, not just port availability), then the **test is correct** and the **docker-compose.yaml is wrong**.
- If a socket-level connectivity check is intentional, then the **test is too strict**.

**In the Code?** The docker-compose.yaml implementation (socket check) is valid Docker-Compose syntax and does test connectivity.

### Recommended Fix

**Option A: Update docker-compose.yaml to use /health endpoint** ✅ (STRONGLY RECOMMENDED)

The Flask app already exposes a `/health` endpoint ([pi_camera_in_docker/shared.py](pi_camera_in_docker/shared.py) lines 299-308) that returns:

```json
{ "status": "healthy", "timestamp": "...", "app_mode": "webcam" }
```

The Docker image has `curl` installed ([Dockerfile](Dockerfile) line 26), so this will work:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

This approach:

- ✅ Validates actual app readiness (not just port availability)
- ✅ Uses available tools (curl is installed)
- ✅ Matches the test's expectations
- ✅ Provides better health diagnostics

**Option B: Update test to accept socket connection healthcheck** (Less Preferred)

If socket-level connectivity is intentionally sufficient:

```python
# Replace the assertion at line 36:
assert "test" in healthcheck, "Missing healthcheck test"
assert (
    "/health" in str(healthcheck.get("test")) or
    "socket.create_connection" in str(healthcheck.get("test")),
    "Healthcheck should test /health endpoint or port connectivity"
)
```

This approach is less desirable because:

- ❌ Socket connection doesn't validate application state
- ❌ Port open ≠ application ready (e.g., app could be deadlocked)

---

## Test 2: `test_announcer_thread_lifecycle`

### Test Location

- **File**: [tests/test_discovery_integration.py](tests/test_discovery_integration.py)
- **Lines**: 153-186
- **Test Class**: `TestDiscoveryAnnounceIntegration`
- **Method**: `test_announcer_thread_lifecycle(self)`

### Test Code

```python
def test_announcer_thread_lifecycle(self):
    """Verify announcer thread starts and stops correctly."""
    from discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    payload = {"webcam_id": "node-test-5"}

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        announcer = DiscoveryAnnouncer(
            management_url="http://management.local:8001",
            token="test-token",
            interval_seconds=0.05,  # Very short interval
            webcam_id=payload["webcam_id"],
            payload=payload,
            shutdown_event=shutdown_event,
        )

        # Verify thread not started yet
        assert announcer._thread is None or not announcer._thread.is_alive()

        # Start and verify thread is running
        announcer.start()
        assert announcer._thread is not None
        assert announcer._thread.is_alive()

        # Stop and verify thread is dead
        announcer.stop()
        time.sleep(0.2)  # Give thread time to exit
        assert not announcer._thread.is_alive()  # ← FAILS HERE
```

### What the Test Expects

1. Thread is `None` or not alive initially
2. After `start()`: Thread exists and is alive
3. After `stop()`: Thread is not alive (still exists but stopped)

### What It Actually Gets

After `stop()` is called, the `_thread` attribute becomes `None` due to this code in [pi_camera_in_docker/discovery.py](pi_camera_in_docker/discovery.py) lines 127-133:

```python
def stop(self, timeout_seconds: float = 3.0) -> None:
    """Stop the discovery announcement daemon thread gracefully."""
    with self._thread_lock:
        self.shutdown_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)
        if self._thread and not self._thread.is_alive():
            self._thread = None  # ← This sets _thread to None
```

When the test tries to call `.is_alive()` on `None`, it raises:

```
AttributeError: 'NoneType' object has no attribute 'is_alive'
```

### Error Output

```
tests/test_discovery_integration.py:185: in test_announcer_thread_lifecycle
    assert not announcer._thread.is_alive()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'NoneType' object has no attribute 'is_alive'
```

### Root Cause Analysis

| Category           | Finding                                                                                                                                                                                              |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Issue Type**     | TEST BUG                                                                                                                                                                                             |
| **Root Cause**     | The test assumes `announcer._thread` will still reference the thread object after `stop()`, but the `stop()` method sets `_thread = None` after joining. The test doesn't account for this behavior. |
| **Code Behavior**  | The `DiscoveryAnnouncer.stop()` method is designed to clean up the thread reference after stopping. This is defensive programming to prevent accidental reuse of a dead thread.                      |
| **Test Behavior**  | The test expects the thread object to persist but be in an "not alive" state. It doesn't check for the cleanup behavior.                                                                             |
| **Responsibility** | 100% test bug - the test assumptions don't match the actual implementation contract.                                                                                                                 |

### Is This a Bug?

**In the Test?** ✅ **YES** - The test makes an invalid assumption that `_thread` will exist and be checkable after `stop()`.

**In the Code?** ❌ **NO** - The `stop()` method is correctly implemented. Setting `_thread = None` after cleanup is good practice.

### Implementation Contract

The `DiscoveryAnnouncer` class contract is:

- After `stop()`, the `_thread` attribute is `None`
- This allows safe restart via `start()` again
- This prevents accidentally checking/accessing a dead thread object

### Recommended Fix

**Update the test to match the actual implementation contract** (RECOMMENDED):

```python
# Stop and verify thread is dead
announcer.stop()
time.sleep(0.2)  # Give thread time to exit
assert announcer._thread is None, "Thread should be cleaned up after stop()"
```

**Alternative (less preferred)**: Modify the `stop()` method to NOT set `_thread = None`:

```python
def stop(self, timeout_seconds: float = 3.0) -> None:
    """Stop the discovery announcement daemon thread gracefully."""
    with self._thread_lock:
        self.shutdown_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)
        # Don't set to None - allow checking if thread is alive
```

However, this is less clean from a resource management perspective.

---

## Quick Fix Examples

### Fix 1a: Update docker-compose.yaml (Recommended for Test 1)

**File**: [containers/motion-in-ocean-webcam/docker-compose.yaml](containers/motion-in-ocean-webcam/docker-compose.yaml)

**Current (lines 65-71)**:

```yaml
healthcheck:
  test:
    [
      "CMD-SHELL",
      'python3 -c "import socket; socket.create_connection((''localhost'', 8000), timeout=3)" 2>/dev/null || exit 1',
    ]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

**Replace with**:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

### Fix 2: Update test assertion (Recommended for Test 2)

**File**: [tests/test_discovery_integration.py](tests/test_discovery_integration.py)

**Current (line 185)**:

```python
            # Stop and verify thread is dead
            announcer.stop()
            time.sleep(0.2)  # Give thread time to exit
            assert not announcer._thread.is_alive()
```

**Replace with**:

```python
            # Stop and verify thread is dead
            announcer.stop()
            time.sleep(0.2)  # Give thread time to exit
            assert announcer._thread is None, "Thread should be cleaned up after stop()"
```

---

| Test                                  | Issue Type         | Severity | Root Cause                                                           | Recommended Fix                                |
| ------------------------------------- | ------------------ | -------- | -------------------------------------------------------------------- | ---------------------------------------------- |
| `test_webcam_compose_contract_basics` | Test/Code Mismatch | Medium   | Test expects `/health` endpoint check; code uses socket connection   | Update docker-compose OR update test assertion |
| `test_announcer_thread_lifecycle`     | Test Bug           | High     | Test assumes `_thread` exists after `stop()`; code sets it to `None` | Change assertion to check `_thread is None`    |

---

## Related Code References

### For Test 1 (Healthcheck)

- **Flask healthcheck endpoint**: [pi_camera_in_docker/shared.py](pi_camera_in_docker/shared.py) - should have `GET /health`
- **Docker compose config**: [containers/motion-in-ocean-webcam/docker-compose.yaml](containers/motion-in-ocean-webcam/docker-compose.yaml) lines 65-71
- **Test file**: [tests/test_config.py](tests/test_config.py) lines 14-36

### For Test 2 (Thread Lifecycle)

- **DiscoveryAnnouncer implementation**: [pi_camera_in_docker/discovery.py](pi_camera_in_docker/discovery.py) lines 73-247
- **stop() method**: [pi_camera_in_docker/discovery.py](pi_camera_in_docker/discovery.py) lines 124-133
- **Test file**: [tests/test_discovery_integration.py](tests/test_discovery_integration.py) lines 153-186
