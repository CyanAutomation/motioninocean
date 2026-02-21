#!/usr/bin/env python3
"""Comprehensive rebrand script: node -> webcam terminology throughout motion-in-ocean.

This script handles all file replacements across templates, Python code, JavaScript,
CSS, and tests to rename "node" terminology to "webcam".
"""

from pathlib import Path
from typing import Dict, List, Tuple


# Type alias
ReplacementList = List[Tuple[str, str, str]]  # (old, new, description)

REPLACEMENTS: Dict[str, ReplacementList] = {
    # ====== 1. HTML Template ======
    "pi_camera_in_docker/templates/management.html": [
        (
            "motion-in-ocean - Node Management",
            "motion-in-ocean - Webcam Management",
            "Meta description",
        ),
        (">Node Management<", ">Webcam Management<", "Page title"),
        (
            "Manage webcam nodes and monitor node health.",
            "Manage webcam hosts and monitor webcam health.",
            "Subtitle",
        ),
        ("Add node", "Add webcam host", "Form heading"),
        ("node-form-panel-container", "webcam-form-panel-container", "Form container ID"),
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
            "ARIA control",
        ),
        ("node-form-content", "webcam-form-content", "Form content ID"),
        ("node-form-content-wrapper", "webcam-form-content-wrapper", "Form wrapper ID"),
        ('id="node-form"', 'id="webcam-form"', "Form ID"),
        ("editing-node-id", "editing-webcam-id", "Hidden input"),
        ("node-id", "webcam-id", "Node ID field"),
        (">Node ID<", ">Webcam ID<", "Node ID label"),
        ("node-name", "webcam-name", "Name field"),
        ("node-base-url", "webcam-base-url", "Base URL field"),
        ("node-transport", "webcam-transport", "Transport field"),
        ("node-auth-type", "webcam-auth-type", "Auth type field"),
        ("node-auth-token", "webcam-auth-token", "Auth token field"),
        (">Remote Node Token<", ">Remote Webcam Token<", "Auth token label"),
        ("Set to the remote node", "Set to the remote webcam", "Auth placeholder"),
        (
            "For webcam nodes, use the same token configur",
            "For webcam hosts, use the same token configured",
            "Auth helper text",
        ),
        ("node-capabilities", "webcam-capabilities", "Capabilities field"),
        ("node-labels", "webcam-labels", "Labels field"),
        (">Save node<", ">Save webcam host<", "Save button"),
        ('class="node-list-panel', 'class="webcam-list-panel', "List panel class"),
        (">Registered nodes<", ">Registered webcams<", "List heading"),
        ("refresh-nodes-btn", "refresh-webcams-btn", "Refresh button"),
        ("node-table-wrap", "webcam-table-wrap", "Table wrap"),
        ('class="node-table"', 'class="webcam-table"', "Table class"),
        ('aria-label="Registered node', 'aria-label="Registered webcam', "Table ARIA"),
        ("><th>Node<", "><th>Webcam<", "Table column"),
        (">No nodes registered.<", ">No webcams registered.<", "Empty state"),
        ("nodes-table-body", "webcams-table-body", "Table body"),
        ('aria-label="Node diagnostics', 'aria-label="Webcam diagnostics', "Diagnostics ARIA"),
        (">Node: <", ">Webcam: <", "Diagnostic label"),
        ("diagnostic-node-id", "diagnostic-webcam-id", "Diagnostic span"),
        ("Run Diagnose on a node", "Run Diagnose on a webcam", "Diagnostic text"),
    ],
    # ====== 2. Management API (Python) ======
    "pi_camera_in_docker/management_api.py": [
        # Endpoint routes
        ("/api/nodes", "/api/webcams", "API endpoint paths"),
        # Response keys
        ('"nodes":', '"webcams":', "Response nodes key"),
        ('"total_nodes"', '"total_webcams"', "Total count key"),
        ('"unavailable_nodes"', '"unavailable_webcams"', "Unavailable count key"),
        # Error codes - replace systematically
        ("NODE_UNREACHABLE", "WEBCAM_UNREACHABLE", "Error code"),
        ("NODE_UNAUTHORIZED", "WEBCAM_UNAUTHORIZED", "Error code"),
        ("NODE_INVALID_RESPONSE", "WEBCAM_INVALID_RESPONSE", "Error code"),
        ("NODE_API_MISMATCH", "WEBCAM_API_MISMATCH", "Error code"),
        ("NODE_INVALID", "WEBCAM_INVALID", "Error code prefix"),
        ("NODE_REQUEST", "WEBCAM_REQUEST", "Error class prefix"),
        ("node_id", "webcam_id", "Parameter names"),
        ("node ", "webcam ", "Comments/docstrings"),
    ],
    # ====== 3. Node Registry (Python) ======
    "pi_camera_in_docker/node_registry.py": [
        ("class NodeValidationError", "class WebcamValidationError", "Exception class"),
        ("class NodeRegistry", "class WebcamRegistry", "Registry class"),
        ("REQUIRED_NODE_FIELDS", "REQUIRED_WEBCAM_FIELDS", "Constants"),
        ("def validate_node", "def validate_webcam", "Function name"),
        ("def _node_auth", "def _webcam_auth", "Function name"),
        ("node_id", "webcam_id", "Parameter names"),
        ("get_node", "get_webcam", "Method name"),
        ("create_node", "create_webcam", "Method name"),
        ("update_node", "update_webcam", "Method name"),
        ("delete_node", "delete_webcam", "Method name"),
        ("list_nodes", "list_webcams", "Method name"),
        ("NodeRegistry", "WebcamRegistry", "Class reference"),
        ("node ", "webcam ", "Comments"),
    ],
    # ====== 4. Discovery (Python) ======
    "pi_camera_in_docker/discovery.py": [
        ("_stable_node_id", "_stable_webcam_id", "Function name"),
        ("build_node_registration_payload", "build_webcam_registration_payload", "Function name"),
        ("self.node_id", "self.webcam_id", "Instance variable"),
        ("node_id", "webcam_id", "Parameter/local variables"),
        ('"node_id"', '"webcam_id"', "JSON field name"),
        ("node ", "webcam ", "Comments/logs"),
    ],
    # ====== 5. Runtime Config (Python) ======
    "pi_camera_in_docker/runtime_config.py": [
        ("DISCOVERY_NODE_ID", "DISCOVERY_WEBCAM_ID", "Env var"),
        ("NODE_REGISTRY_PATH", "WEBCAM_REGISTRY_PATH", "Env var"),
        ("discovery_node_id", "discovery_webcam_id", "Config key"),
        ("node_registry_path", "webcam_registry_path", "Config key"),
        ("node ", "webcam ", "Comments"),
    ],
    # ====== 6. Management JavaScript ======
    "pi_camera_in_docker/static/js/management.js": [
        # DOM element variables
        ("nodeForm", "webcamForm", "Variable name"),
        ("nodeFormPanelContainer", "webcamFormPanelContainer", "Variable name"),
        ("toggleNodeFormPanelBtn", "toggleWebcamFormPanelBtn", "Variable name"),
        ("nodeFormContentWrapper", "webcamFormContentWrapper", "Variable name"),
        ("nodeFormContent", "webcamFormContent", "Variable name"),
        ("editingNodeIdInput", "editingWebcamIdInput", "Variable name"),
        ("diagnosticNodeId", "diagnosticWebcamId", "Variable name"),
        # State variables
        ("let nodes = ", "let webcams = ", "State array"),
        ("nodeStatusMap", "webcamStatusMap", "State object"),
        ("nodeStatusAggregationMap", "webcamStatusAggregationMap", "State object"),
        # API calls and routes
        ("/api/nodes", "/api/webcams", "API routes"),
        ("api/nodes", "api/webcams", "API routes"),
        # Function names
        ("getDiscoveryInfo(node)", "getDiscoveryInfo(webcam)", "Function param"),
        ("buildNodePayload", "buildWebcamPayload", "Function name"),
        ("normalizeNodeStatusError", "normalizeWebcamStatusError", "Function name"),
        (
            "enrichStatusWithAggregation(nodeId",
            "enrichStatusWithAggregation(webcamId",
            "Function param",
        ),
        ("normalizeNodeStatusForUi", "normalizeWebcamStatusForUi", "Function name"),
        ("fetchNodes", "fetchWebcams", "Function name"),
        # Error codes
        ("NODE_UNREACHABLE", "WEBCAM_UNREACHABLE", "Error code"),
        ("NODE_UNAUTHORIZED", "WEBCAM_UNAUTHORIZED", "Error code"),
        ("NODE_INVALID_RESPONSE", "WEBCAM_INVALID_RESPONSE", "Error code"),
        ("NODE_API_MISMATCH", "WEBCAM_API_MISMATCH", "Error code"),
        # DOM selectors
        ('"#node-id"', '"#webcam-id"', "Selector"),
        ('"#node-name"', '"#webcam-name"', "Selector"),
        ('"#node-base-url"', '"#webcam-base-url"', "Selector"),
        ('"#node-transport"', '"#webcam-transport"', "Selector"),
        ('"#node-auth-type"', '"#webcam-auth-type"', "Selector"),
        ('"#node-auth-token"', '"#webcam-auth-token"', "Selector"),
        ('"#node-capabilities"', '"#webcam-capabilities"', "Selector"),
        ('"#node-labels"', '"#webcam-labels"', "Selector"),
        ('"#node-form"', '"#webcam-form"', "Selector"),
        ('"#node-form-content"', '"#webcam-form-content"', "Selector"),
        ('"#editing-node-id"', '"#editing-webcam-id"', "Selector"),
        ('"#toggle-node-form-panel-btn"', '"#toggle-webcam-form-panel-btn"', "Selector"),
        ('"#save-node-btn"', '"#save-webcam-btn"', "Selector"),
        ('"#refresh-nodes-btn"', '"#refresh-webcams-btn"', "Selector"),
        ('"#nodes-table-body"', '"#webcams-table-body"', "Selector"),
        # Response key access
        ("response.nodes", "response.webcams", "Response parsing"),
        ('response["nodes"]', 'response["webcams"]', "Response parsing"),
        # Variable names
        (" node,", " webcam,", "Loop variable"),
        (" node )", " webcam )", "Loop variable"),
        (" node:", " webcam:", "Loop variable"),
        ("node ", "webcam ", "Comments"),
    ],
    # ====== 7. Management CSS ======
    "pi_camera_in_docker/static/css/management.css": [
        (".node-form-panel", ".webcam-form-panel", "Class selector"),
        (".node-list-panel", ".webcam-list-panel", "Class selector"),
        (".node-table-wrap", ".webcam-table-wrap", "Class selector"),
        (".node-table", ".webcam-table", "Class selector"),
        ("#node-", "#webcam-", "ID selector prefix"),
        ("node-", "webcam-", "Class names in CSS"),
    ],
    # ====== 8. Test: Node Registry ======
    "tests/test_node_registry.py": [
        ("test_", "test_", "Test function prefix - will update manually"),
        ("def _node(", "def _webcam(", "Helper function"),
        ("node_id", "webcam_id", "Variable names"),
        ('response["nodes"]', 'response["webcams"]', "Response key"),
        ('response["node_id"]', 'response["webcam_id"]', "Response key"),
        ("NODE_", "WEBCAM_", "Error code prefix"),
        ("node ", "webcam ", "Comments"),
    ],
    # ====== 9. Test: Management API ======
    "tests/test_management_api.py": [
        ("/api/nodes", "/api/webcams", "API endpoint"),
        ('response["nodes"]', 'response["webcams"]', "Response key"),
        ("node_id", "webcam_id", "Variable names"),
        ("NODE_", "WEBCAM_", "Error code prefix"),
        ("node ", "webcam ", "Comments"),
    ],
    # ====== 10. Test: Integration ======
    "tests/test_integration.py": [
        ("NODE_REGISTRY_PATH", "WEBCAM_REGISTRY_PATH", "Env var"),
        ("node_registry_path", "webcam_registry_path", "Config key"),
    ],
    # ====== 11. Test: Parallel Containers ======
    "tests/test_parallel_containers.py": [
        ("check_management_list_nodes", "check_management_list_webcams", "Function name"),
        ("check_management_register_node", "check_management_register_webcam", "Function name"),
        ("check_management_query_node_ssrf", "check_management_query_webcam_ssrf", "Function name"),
        ("total_nodes", "total_webcams", "Variable names"),
        ("unavailable_nodes", "unavailable_webcams", "Variable names"),
    ],
}


def apply_replacements(file_path: str, replacements: ReplacementList) -> int:
    """Apply all replacements to a file and return count."""
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return 0

    content = full_path.read_text()
    original_content = content
    count = 0

    for old, new, desc in replacements:
        # Skip placeholder entries
        if old == new:
            continue
        if old in content:
            content = content.replace(old, new)
            count += 1
            print(f"  ✓ {desc}")

    if content != original_content:
        full_path.write_text(content)
        print(f"  → Wrote {count} changes\n")
    else:
        print("  → No changes made\n")

    return count


def main():
    """Run all replacements."""
    print("\n" + "=" * 80)
    print("   REBRAND: node -> webcam terminology (motion-in-ocean)")
    print("=" * 80 + "\n")

    total_changes = 0
    successful_files = 0
    failed_files = 0

    for file_path, replacements in REPLACEMENTS.items():
        print(f"📁 {file_path}")
        try:
            changes = apply_replacements(file_path, replacements)
            total_changes += changes
            successful_files += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            failed_files += 1

    print("=" * 80)
    print("✅ SUMMARY")
    print(f"   Total replacements: {total_changes}")
    print(f"   Files processed:    {successful_files}")
    print(f"   Files failed:       {failed_files}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
