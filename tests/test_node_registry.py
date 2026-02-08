from pi_camera_in_docker.node_registry import FileNodeRegistry, NodeValidationError


def _node(node_id: str, name: str) -> dict:
    return {
        "id": node_id,
        "name": name,
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": "2024-01-01T00:00:00",
        "capabilities": ["stream"],
        "transport": "http",
    }


def test_update_node_raises_keyerror_when_target_missing(tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))
    registry.create_node(_node("node-1", "One"))

    try:
        registry.update_node("missing", {"name": "Updated"})
        assert False, "Expected KeyError"
    except KeyError as exc:
        assert exc.args == ("missing",)


def test_update_node_detects_id_collision(tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))
    registry.create_node(_node("node-1", "One"))
    registry.create_node(_node("node-2", "Two"))

    try:
        registry.update_node("node-1", {"id": "node-2"})
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert str(exc) == "node node-2 already exists"
