import threading

from pi_camera_in_docker.management_api import _manual_discovery_defaults
from pi_camera_in_docker.node_registry import FileWebcamRegistry, NodeValidationError


def _node(webcam_id: str, name: str) -> dict:
    return {
        "id": webcam_id,
        "name": name,
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": "2024-01-01T00:00:00",
        "capabilities": ["stream"],
        "transport": "http",
    }


def test_update_node_raises_keyerror_when_target_missing(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    registry.create_webcam(_node("node-1", "One"))

    try:
        registry.update_webcam("missing", {"name": "Updated"})
        assert False, "Expected KeyError"
    except KeyError as exc:
        assert exc.args == ("missing",)


def test_update_node_detects_id_collision(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    registry.create_webcam(_node("node-1", "One"))
    registry.create_webcam(_node("node-2", "Two"))

    try:
        registry.update_webcam("node-1", {"id": "node-2"})
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert str(exc) == "webcam node-2 already exists"


def test_create_node_rejects_basic_auth_without_convertible_token(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    node = _node("node-1", "One")
    node["auth"] = {"type": "basic", "username": "camera", "password": "secret"}

    try:
        registry.create_webcam(node)
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert "auth.type='basic' cannot be auto-migrated without an API token" in str(exc)


def test_create_node_migrates_legacy_auth_with_token(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    node = _node("node-1", "One")
    node["auth"] = {
        "type": "basic",
        "token": "new-api-token",
        "username": "legacy",
        "password": "legacy",
    }

    created = registry.create_webcam(node)
    assert created["auth"] == {"type": "bearer", "token": "new-api-token"}


def test_create_node_requires_bearer_token(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    node = _node("node-1", "One")
    node["auth"] = {"type": "bearer"}

    try:
        registry.create_webcam(node)
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

    registry = FileWebcamRegistry(str(registry_path))
    listed = registry.list_webcams()
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

    registry = FileWebcamRegistry(str(registry_path))
    try:
        registry.list_webcams()
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert "uses deprecated auth fields" in str(exc)


def test_load_raises_validation_error_for_corrupted_registry_json(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    registry = FileWebcamRegistry(str(registry_path))
    try:
        registry.list_webcams()
        assert False, "Expected NodeValidationError"
    except NodeValidationError as exc:
        assert "webcam registry file is corrupted and cannot be parsed" in str(exc)


def test_upsert_node_is_atomic_for_concurrent_creates(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    barrier = threading.Barrier(2)
    results = []

    def announce(name: str):
        create_value = _node("node-atomic", name)
        patch_value = {
            "name": name,
            "base_url": "http://example.com",
            "transport": "http",
            "capabilities": ["stream"],
            "last_seen": "2024-01-01T00:00:00",
            "labels": {},
            "auth": {"type": "none"},
            "discovery": {
                "source": "discovered",
                "last_announce_at": "2024-01-01T00:00:00",
                "approved": False,
            },
        }
        barrier.wait()
        results.append(registry.upsert_webcam("node-atomic", create_value, patch_value)["upserted"])

    t1 = threading.Thread(target=announce, args=("Node A",))
    t2 = threading.Thread(target=announce, args=("Node B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted(results) == ["created", "updated"]
    nodes = registry.list_webcams()
    assert len(nodes) == 1
    assert nodes[0]["id"] == "node-atomic"


def test_list_webcams_is_serialized_with_concurrent_upserts(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    stop = threading.Event()
    failures = []

    def writer() -> None:
        for i in range(200):
            create_value = _node("node-race", f"Node {i}")
            patch_value = {
                "name": f"Node {i}",
                "base_url": "http://example.com",
                "transport": "http",
                "capabilities": ["stream"],
                "last_seen": "2024-01-01T00:00:00",
                "labels": {},
                "auth": {"type": "none"},
                "discovery": {
                    "source": "discovered",
                    "last_announce_at": "2024-01-01T00:00:00",
                    "approved": False,
                },
            }
            registry.upsert_webcam("node-race", create_value, patch_value)
        stop.set()

    def reader() -> None:
        while not stop.is_set():
            try:
                webcams = registry.list_webcams()
                assert isinstance(webcams, list)
            except Exception as exc:  # pragma: no cover - assertion records failures
                failures.append(exc)
                stop.set()

    writer_thread = threading.Thread(target=writer)
    reader_threads = [threading.Thread(target=reader) for _ in range(4)]

    for thread in reader_threads:
        thread.start()
    writer_thread.start()

    writer_thread.join()
    for thread in reader_threads:
        thread.join()

    assert failures == []


def test_update_from_current_preserves_discovery_announce_fields(tmp_path):
    registry = FileWebcamRegistry(str(tmp_path / "registry.json"))
    registry.create_webcam(
        {
            **_node("node-race", "Initial"),
            "discovery": {
                "source": "discovered",
                "first_seen": "2024-01-01T00:00:00+00:00",
                "last_announce_at": "2024-01-01T00:00:00+00:00",
                "approved": False,
            },
        }
    )

    stale_existing = registry.get_webcam("node-race")
    assert stale_existing is not None

    # Simulate a discovery announcement that lands between a stale read and write.
    upserted = registry.upsert_webcam_from_current(
        "node-race",
        _node("node-race", "Discovery"),
        lambda existing: {
            "name": "Discovery",
            "base_url": existing["base_url"],
            "transport": existing["transport"],
            "capabilities": existing["capabilities"],
            "last_seen": "2024-01-02T00:00:00+00:00",
            "labels": existing["labels"],
            "auth": existing["auth"],
            "discovery": {
                "source": "discovered",
                "first_seen": existing["discovery"]["first_seen"],
                "last_announce_at": "2024-01-02T00:00:00+00:00",
                "approved": existing["discovery"]["approved"],
            },
        },
    )
    assert upserted["upserted"] == "updated"

    # Manual update computes defaults from the in-lock current record, not stale_existing.
    updated = registry.update_webcam_from_current(
        "node-race",
        lambda existing: {
            "name": "Manual",
            "discovery": _manual_discovery_defaults(existing),
        },
    )

    assert stale_existing["discovery"]["last_announce_at"] == "2024-01-01T00:00:00+00:00"
    assert updated["discovery"]["source"] == "manual"
    assert updated["discovery"]["approved"] is True
    assert updated["discovery"]["last_announce_at"] == "2024-01-02T00:00:00+00:00"
