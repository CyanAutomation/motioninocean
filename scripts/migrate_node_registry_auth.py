#!/usr/bin/env python3
"""One-off migration for NODE_REGISTRY_PATH auth schema.

Converts deprecated auth payloads to bearer token format when possible.
Fails with actionable errors for entries that cannot be migrated safely.
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pi_camera_in_docker.node_registry import NodeValidationError, validate_node


def migrate_registry(path: Path, dry_run: bool = False) -> bool:
    if not path.exists():
        raise FileNotFoundError(f"registry file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise NodeValidationError("registry root must be a JSON object with a 'nodes' array")

    nodes = raw.get("nodes", [])
    if not isinstance(nodes, list):
        raise NodeValidationError("registry field 'nodes' must be an array")

    migrated_nodes = []
    changed = False

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise NodeValidationError(f"node at index {index} must be an object")
        migrated = validate_node(node)
        migrated_nodes.append(migrated)
        if migrated != node:
            changed = True

    if changed and not dry_run:
        path.write_text(json.dumps({"nodes": migrated_nodes}, indent=2) + "\n", encoding="utf-8")

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate NODE_REGISTRY_PATH auth fields to bearer tokens")
    parser.add_argument(
        "--path",
        default=os.environ.get("NODE_REGISTRY_PATH", "/data/node-registry.json"),
        help="Path to registry JSON (default: NODE_REGISTRY_PATH or /data/node-registry.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and report changes without writing")
    args = parser.parse_args()

    registry_path = Path(args.path)

    try:
        changed = migrate_registry(registry_path, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"[ERROR] invalid JSON in {registry_path}: {exc}")
        return 2
    except NodeValidationError as exc:
        print(f"[ERROR] migration blocked: {exc}")
        return 1

    action = "would be updated" if args.dry_run else "updated"
    if changed:
        print(f"[OK] registry {action}: {registry_path}")
    else:
        print(f"[OK] no changes needed: {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
