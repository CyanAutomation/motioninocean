====================================================
Motion In Ocean - Camera Streaming Documentation
====================================================

Welcome to Motion In Ocean documentation! This guide covers the Docker-first
Raspberry Pi CSI camera streaming solution with multi-node management.

**Latest Version:** 1.0.0

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   README
   guides/DEPLOYMENT
   guides/FEATURE_FLAGS
   guides/MIGRATION
   guides/RELEASE
   ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE
   DOCUMENTATION_GUIDE

.. toctree::
   :maxdepth: 2
   :caption: Python API

   modules/main
   modules/modes_webcam
   modules/management_api
   modules/discovery
   modules/configuration

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   CHANGELOG
   product/PRD-backend
   product/PRD-core
   product/PRD-frontend

Project policies:

* `Contributing guide <https://github.com/CyanAutomation/motioninocean/blob/main/CONTRIBUTING.md>`_
* `Agent guidance <https://github.com/CyanAutomation/motioninocean/blob/main/AGENTS.md>`_
* `Security policy <https://github.com/CyanAutomation/motioninocean/blob/main/SECURITY.md>`_

Quick Links
===========

- **GitHub:** https://github.com/CyanAutomation/motioninocean
- **Issues:** https://github.com/CyanAutomation/motioninocean/issues
- **Releases:** https://github.com/CyanAutomation/motioninocean/releases

Architecture
============

Motion In Ocean supports two deployment modes:

**Webcam Mode** (port 8000)
   Streams camera output via MJPEG, exposes REST API for settings and actions.
   Runs on Raspberry Pi with CSI camera.

**Management Mode** (port 8001)
   Hub that discovers and manages remote webcam nodes, aggregates status,
   manages node registry. Coordinates multi-Pi deployments.

Key Features
============

- 🎥 Real-time MJPEG streaming with frame statistics
- 🔍 Auto-discovery and multi-node management via hub
- 🔐 Bearer token authentication for both modes
- ⚙️ Runtime settings with file-based persistence
- 🛡️ SSRF protection with DNS pinning
- 📊 Prometheus-style metrics export
- 🧪 API test mode for deterministic testing
- 🐳 Docker/Docker Compose ready

Documentation Structure
=======================

- **Python API:** Auto-generated from Google-style docstrings
- **JavaScript API:** Auto-generated from JSDoc comments
- **Guides:** Deployment patterns, feature flags, environment variables
- **Standards:** Documentation, code quality, testing

For more information, see the individual module documentation below.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
