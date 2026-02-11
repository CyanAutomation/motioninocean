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


def test_create_node_rejects_basic_auth_without_convertible_token(tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))
    node = _node("node-1", "One")
    node["auth"] = {"type": "basic", "username": "camera", "password": "secret"}

    try:
        registry.create_node(node)
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert "auth.type='basic' cannot be auto-migrated without an API token" in str(exc)


def test_create_node_migrates_legacy_auth_with_token(tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))
    node = _node("node-1", "One")
    node["auth"] = {
        "type": "basic",
        "token": "new-api-token",
        "username": "legacy",
        "password": "legacy",
    }

    created = registry.create_node(node)
    assert created["auth"] == {"type": "bearer", "token": "new-api-token"}


def test_create_node_requires_bearer_token(tmp_path):
    registry = FileNodeRegistry(str(tmp_path / "registry.json"))
    node = _node("node-1", "One")
    node["auth"] = {"type": "bearer"}

    try:
        registry.create_node(node)
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert str(exc) == "auth.token is required for auth.type='bearer'"


def test_load_migrates_legacy_auth_from_registry_file(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        """
{
  "nodes": [
    {
      "id": "node-legacy",
      "name": "Legacy",
      "base_url": "http://example.com",
      "auth": {
        "type": "basic",
        "token": "api-token",
        "username": "old-user"
      },
      "labels": {},
      "last_seen": "2024-01-01T00:00:00",
      "capabilities": ["stream"],
      "transport": "http"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    registry = FileNodeRegistry(str(registry_path))
    listed = registry.list_nodes()
    assert listed[0]["auth"] == {"type": "bearer", "token": "api-token"}


def test_load_rejects_unmigratable_legacy_auth(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        """
{
  "nodes": [
    {
      "id": "node-legacy",
      "name": "Legacy",
      "base_url": "http://example.com",
      "auth": {
        "type": "basic",
        "username": "old-user",
        "password": "old-pass"
      },
      "labels": {},
      "last_seen": "2024-01-01T00:00:00",
      "capabilities": ["stream"],
      "transport": "http"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    registry = FileNodeRegistry(str(registry_path))
    try:
        registry.list_nodes()
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert "uses deprecated auth fields" in str(exc)


def test_load_raises_validation_error_for_corrupted_registry_json(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    registry = FileNodeRegistry(str(registry_path))
    try:
        registry.list_nodes()
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert "node registry file is corrupted and cannot be parsed" in str(exc)
