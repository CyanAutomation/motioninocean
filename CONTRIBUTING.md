# Contributing to motion-in-ocean

Thanks for your interest in contributing to **motion-in-ocean**! 🌊📷  
This is a small open-source project focused on making Raspberry Pi CSI camera streaming reliable and easy to deploy in Docker-based homelabs.

Even small contributions (docs fixes, examples, typos) are genuinely appreciated.

---

## Ways to contribute

You can help by:

- Improving documentation (README, examples, deployment notes)
- Adding homelab integration examples (Home Assistant, OctoPrint, Uptime Kuma, Homepage, etc.)
- Improving device discovery / mapping reliability across Pi models
- Adding CI/CD workflows (multi-arch builds, release tagging)
- Bug fixes and small feature improvements
- Reporting bugs with clear logs and reproduction steps

---

## Before you start

Please check:

- Existing issues (you may find your idea already tracked)
- Project goals in the README
- Any open PRs that might overlap

If you're unsure whether a change will be accepted, open an issue first to discuss it.

---

## Development workflow

### Prerequisites

- Docker + Docker Compose
- Raspberry Pi OS (Bookworm) + ARM64 recommended for real camera testing
- Non-Pi systems are supported for API/dev work using mock mode

### Local build & run

```bash
docker compose build
docker compose up
