"""Unit tests for registry corruption handling in FileWebcamRegistry."""

from pi_camera_in_docker.node_registry import FileWebcamRegistry, NodeValidationError


def test_load_raises_corruption_error_when_top_level_is_not_object(tmp_path):
    """Malformed top-level JSON type raises explicit corruption error."""
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("[]", encoding="utf-8")

    registry = FileWebcamRegistry(str(registry_path))

    try:
        registry.list_webcams()
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        message = str(exc)
        assert "webcam registry file is corrupted and cannot be parsed" in message
        assert str(registry_path) in message
        assert "expected top-level object shaped like {'nodes': []}" in message


def test_load_raises_corruption_error_when_nodes_is_not_list(tmp_path):
    """Malformed nodes field type raises explicit corruption error."""
    registry_path = tmp_path / "registry.json"
    registry_path.write_text('{"nodes": {"id": "node-a"}}', encoding="utf-8")

    registry = FileWebcamRegistry(str(registry_path))

    try:
        registry.list_webcams()
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        message = str(exc)
        assert "webcam registry file is corrupted and cannot be parsed" in message
        assert str(registry_path) in message
        assert "expected top-level object shaped like {'nodes': []}" in message
