# PRD Core: motion-in-ocean

## Purpose

This document captures shared product context used by both backend and frontend PRDs. Domain-specific requirements live in:

- [PRD-backend.md](PRD-backend.md)
- [PRD-frontend.md](PRD-frontend.md)

## Problem Statement

Running a Raspberry Pi CSI camera in a Dockerized homelab setup is operationally complex. Users need a system that is easy to deploy, provides reliable live-stream visibility, and communicates health/readiness clearly so failures can be detected and recovered quickly.

## Cross-Cutting Goals

- **Reliable end-to-end streaming:** The system provides a usable live camera experience when camera hardware is available.
- **Clear service state semantics:** Liveness and readiness are understandable to both operators and UI users.
- **Low-friction deployment and operation:** Setup, upgrades, and diagnostics are straightforward for homelab operators.
- **Observable behavior:** Status and runtime signals are exposed in machine-readable and human-readable form.
- **Resilient user experience:** Temporary failures are surfaced clearly and recover without manual intervention where possible.

## Shared Constraints

- Primary deployment target is Raspberry Pi + CSI camera in Docker.
- Solution should work in headless environments and local/LAN-first topologies.
- Runtime behavior is environment-driven/configurable rather than hard-coded.
- Stream and status endpoints must degrade gracefully when camera/device dependencies are unavailable.

## Shared Non-Goals

- Internet-hardened production platform (e.g., full zero-trust posture, enterprise IAM).
- Multi-protocol media platform beyond current scoped transports (e.g., full HLS/RTSP suite by default).
- Heavy orchestration dependencies for baseline single-node use.
- Rich media management workflows (recording library, editing, archival pipeline).
