# Testing Documentation (Canonical)

This is the **authoritative testing document** for this repository.

- Primary source of truth: `docs/testing/README.md`
- Historical reports: `docs/testing/archive/`
- Legacy entry points kept temporarily at repository root now contain deprecation notices.

## How to run tests

### Core local test suites

```bash
# Run all Python tests
python -m pytest

# Optional: run lint/format checks if configured in your environment
npm run lint
npm run format -- --check
```

### Parallel container / cross-service validation

```bash
# Start dedicated test stack
docker-compose -f docker-compose.test.yaml up -d

# Run automated cross-container test script
python3 tests/test_parallel_containers.py

# Inspect running services and logs
docker-compose -f docker-compose.test.yaml ps
docker-compose -f docker-compose.test.yaml logs

# Tear down
docker-compose -f docker-compose.test.yaml down
```

## Where test results live

- Most current status and guidance: this document.
- Point-in-time or legacy reports: `docs/testing/archive/`.
- Runtime execution output: terminal/CI logs from commands above.

## Latest status (merged summary)

Based on the previously duplicated summaries (`TEST_REPORT.md`, `TESTING_COMPLETE.md`, `TEST_RESULTS_EXECUTIVE_SUMMARY.md`):

- Core automated suites previously reported full pass rates for configuration, integration, and unit tests in their recorded runs.
- Parallel container validation previously reported successful startup/health for webcam and management containers, with one expected limitation: management-to-webcam status checks are blocked when targets resolve to private/loopback ranges due to SSRF protections.
- Overall conclusion from historical reports: **test posture is healthy**, and the cross-container limitation in single-host Docker networking is an intentional security behavior, not an application defect.

## Cross-container tests

### Current expectation

When running both services on one Docker host, node status checks can fail with `NODE_UNREACHABLE` if the webcam node URL resolves to blocked address ranges (e.g., Docker bridge/private IPs, localhost). This is expected with SSRF safeguards enabled.

### Scenario details (consolidated)

1. **Multi-host deployment (recommended):** management and webcam run on separate machines with routable LAN addresses.
2. **Single-host Docker host-network experiments:** useful for local validation, but localhost/private addressing can still trigger SSRF protection.
3. **Advanced mock/external endpoint strategies:** can emulate remote-node behavior for specialized testing.

For the original detailed writeups, see the archived reports in `docs/testing/archive/`.
