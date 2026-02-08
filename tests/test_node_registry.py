from node_registry import FileNodeRegistry, NodeValidationError


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


def test_update_node_raises_keyerror_when_target_missing_in_latest(monkeypatch, tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))

    snapshots = [
        {"nodes": [_node("node-1", "One")]},
        {"nodes": []},
    ]

    def fake_load():
        return snapshots.pop(0)

    monkeypatch.setattr(registry, "_load", fake_load)

    try:
        registry.update_node("node-1", {"name": "Updated"})
        assert False, "Expected KeyError"
    except KeyError as exc:
        assert exc.args == ("node-1",)


def test_update_node_detects_collision_against_latest_snapshot(monkeypatch, tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))

    snapshots = [
        {"nodes": [_node("node-1", "One")]},
        {"nodes": [_node("node-1", "One"), _node("node-2", "Two")]},
    ]

    def fake_load():
        return snapshots.pop(0)

    monkeypatch.setattr(registry, "_load", fake_load)

    try:
        registry.update_node("node-1", {"id": "node-2"})
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert str(exc) == "node node-2 already exists"
