#!/usr/bin/env python3
"""Comprehensive rebrand script: node -> webcam terminology throughout motion-in-ocean."""

from pathlib import Path


# Define all replacements as tuples of (old, new, description)
# These are raw string replacements - order matters for some patterns
REPLACEMENTS = {
    # HTML template replacements (1st - all UI text and IDs)
    "pi_camera_in_docker/templates/management.html": [
        ("Node Management", "Webcam Management", "Page title"),
        (
            "Manage webcam nodes and monitor node health.",
            "Manage webcam hosts and monitor webcam health.",
            "Subtitle",
        ),
        ("Add node", "Add webcam host", "Form heading"),
        ("node-form-panel-container", "webcam-form-panel-container", "Form panel container ID"),
        ('class="node-form-panel', 'class="webcam-form-panel', "Form panel class"),
        ("toggle-node-form-panel-btn", "toggle-webcam-form-panel-btn", "Toggle button ID"),
        (
            'aria-label="Collapse node form panel"',
            'aria-label="Collapse webcam form panel"',
            "ARIA label",
        ),
        (
            'aria-controls="node-form-content"',
            'aria-controls="webcam-form-content"',
            "ARIA control ref",
        ),
        ("node-form-content", "webcam-form-content", "Form content ID"),
        ("node-form-content-wrapper", "webcam-form-content-wrapper", "Form wrapper ID"),
        ('id="node-form"', 'id="webcam-form"', "Form ID"),
        ("editing-node-id", "editing-webcam-id", "Editing state input"),
        ('for="node-id"', 'for="webcam-id"', "Label for"),
        ('id="node-id"', 'id="webcam-id"', "Node ID input ID"),
        (">Node ID<", ">Webcam ID<", "Node ID label text"),
        ('for="node-name"', 'for="webcam-name"', "Name label for"),
        ('id="node-name"', 'id="webcam-name"', "Name input ID"),
        (">Name<", ">Webcam name<", "Name label text"),
        ('for="node-base-url"', 'for="webcam-base-url"', "Base URL label for"),
        ('id="node-base-url"', 'id="webcam-base-url"', "Base URL input ID"),
        ('for="node-transport"', 'for="webcam-transport"', "Transport label for"),
        ('id="node-transport"', 'id="webcam-transport"', "Transport select ID"),
        ('for="node-auth-type"', 'for="webcam-auth-type"', "Auth type label for"),
        ('id="node-auth-type"', 'id="webcam-auth-type"', "Auth type select ID"),
        ('for="node-auth-token"', 'for="webcam-auth-token"', "Auth token label for"),
        ('id="node-auth-token"', 'id="webcam-auth-token"', "Auth token input ID"),
        (">Remote Node Token", ">Remote Webcam Token", "Auth token label text"),
        (
            'placeholder="Set to the remote node',
            'placeholder="Set to the remote webcam',
            "Auth token placeholder",
        ),
        (
            "For webcam nodes, use the same token configured in that node's",
            "For webcam hosts, use the same token configured in that host's",
            "Auth helper text",
        ),
        ('for="node-capabilities"', 'for="webcam-capabilities"', "Capabilities label for"),
        ('id="node-capabilities"', 'id="webcam-capabilities"', "Capabilities input ID"),
        ('for="node-labels"', 'for="webcam-labels"', "Labels label for"),
        ('id="node-labels"', 'id="webcam-labels"', "Labels textarea ID"),
        ("Save node", "Save webcam host", "Save button text"),
        ('class="node-list-panel', 'class="webcam-list-panel', "List panel class"),
        (">Registered nodes<", ">Registered webcams<", "Registered heading"),
        ("refresh-nodes-btn", "refresh-webcams-btn", "Refresh button ID"),
        ("node-table-wrap", "webcam-table-wrap", "Table wrap ID"),
        ('class="node-table"', 'class="webcam-table"', "Table class"),
        (
            'aria-label="Registered node list"',
            'aria-label="Registered webcam list"',
            "Table ARIA label",
        ),
        ("><th>Node<", "><th>Webcam<", "Table header"),
        (">No nodes registered.<", ">No webcams registered.<", "Empty state"),
        ("nodes-table-body", "webcams-table-body", "Table body ID"),
        (
            'aria-label="Node diagnostics panel"',
            'aria-label="Webcam diagnostics panel"',
            "Diagnostics ARIA label",
        ),
        (">Node: <", ">Webcam: <", "Diagnostic meta"),
        ("diagnostic-node-id", "diagnostic-webcam-id", "Diagnostic node ID span"),
        ("Run Diagnose on a node", "Run Diagnose on a webcam", "Diagnostic messages"),
    ],
}


def apply_replacements(file_path: str, replacements: list) -> int:
    """Apply all replacements to a file and return count."""
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return 0

    content = full_path.read_text()
    original = content
    count = 0

    for old, new, desc in replacements:
        if old in content:
            content = content.replace(old, new)
            count += 1
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc} (pattern not found: '{old[:50]}...')")

    if content != original:
        full_path.write_text(content)
        print(f"  → Wrote {count} changes\n")
    else:
        print("  → No changes made\n")

    return count


def main():
    """Run all replacements."""
    print("=" * 70)
    print("REBRAND: node -> webcam terminology")
    print("=" * 70)
    print()

    total_changes = 0

    for file_path, replacements in REPLACEMENTS.items():
        print(f"📁 {file_path}")
        changes = apply_replacements(file_path, replacements)
        total_changes += changes

    print("=" * 70)
    print(f"✅ Total replacements: {total_changes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
