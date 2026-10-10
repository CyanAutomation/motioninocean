"""
Integration tests for the announce and discovery mode.
Tests the full workflow of webcam nodes announcing themselves to management.
"""

import json
import tempfile
import threading
from unittest.mock import MagicMock, patch


class TestDiscoveryAnnounceIntegration:
    """Integration tests for webcam discovery announcer in context of management node."""

    def test_announcer_makes_successful_announcement(self):
        """Verify announcer successfully posts discovery announcement to management endpoint."""
        from unittest.mock import MagicMock, patch
        from urllib.request import Request

        from discovery import DiscoveryAnnouncer

        shutdown_event = threading.Event()
        payload = {
            "webcam_id": "node-test-1",
            "name": "test-camera",
            "base_url": "http://192.168.1.100:8000",
            "transport": "http",
            "capabilities": ["stream", "snapshot"],
        }

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            announcer = DiscoveryAnnouncer(
                management_url="http://management.local:8001",
                token="test-token",
                interval_seconds=30,
                webcam_id=payload["webcam_id"],
                payload=payload,
                shutdown_event=shutdown_event,
            )

            result = announcer._announce_once()

            assert result is True
            mock_urlopen.assert_called_once()
            call_args = mock_urlopen.call_args[0]
            request = call_args[0]
            assert isinstance(request, Request)
            assert "Bearer test-token" in request.headers.get("Authorization", "")
            assert request.data == json.dumps(payload).encode("utf-8")

    def test_announcer_handles_http_error(self):
        """Verify announcer handles HTTP errors gracefully."""
        import urllib.error

        from discovery import DiscoveryAnnouncer

        shutdown_event = threading.Event()
        payload = {"webcam_id": "node-test-2"}

        mock_response = MagicMock()
        mock_response.code = 401

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "http://test.local", 401, "Unauthorized", {}, None
            )

            announcer = DiscoveryAnnouncer(
                management_url="http://management.local:8001",
                token="invalid-token",
                interval_seconds=30,
                webcam_id=payload["webcam_id"],
                payload=payload,
                shutdown_event=shutdown_event,
            )

            result = announcer._announce_once()

            assert result is False

    def test_announcer_handles_network_timeout(self):
        """Verify announcer handles network timeouts."""

        from discovery import DiscoveryAnnouncer

        shutdown_event = threading.Event()
        payload = {"webcam_id": "node-test-3"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timeout")

            announcer = DiscoveryAnnouncer(
                management_url="http://management.local:8001",
                token="test-token",
                interval_seconds=30,
                webcam_id=payload["webcam_id"],
                payload=payload,
                shutdown_event=shutdown_event,
            )

            result = announcer._announce_once()

            assert result is False

    def test_announcer_retries_with_exponential_backoff_and_resets_after_success(self, monkeypatch):
        """Retries follow bounded exponential backoff and reset after success.

        Traceability: docs/product/PRD-backend.md#discovery-sequence-flow.
        """
        from pi_camera_in_docker import discovery as discovery_module

        announcer = discovery_module.DiscoveryAnnouncer(
            management_url="http://management.local:8001",
            token="test-token",
            interval_seconds=4,
            webcam_id="node-test-4",
            payload={"webcam_id": "node-test-4"},
            shutdown_event=threading.Event(),
        )
        retry_waits: list[float] = []
        jitter_bounds: list[tuple[float, float]] = []
        jitter_values = iter([0.5, 1.0])
        attempt_results = iter([False, False, True])
        observed_attempts: list[bool] = []

        def fake_wait(wait_seconds: float) -> bool:
            retry_waits.append(wait_seconds)
            return len(retry_waits) == 4

        def fake_jitter(low: float, high: float) -> float:
            jitter_bounds.append((low, high))
            return next(jitter_values)

        def fake_announce() -> bool:
            result = next(attempt_results)
            observed_attempts.append(result)
            return result

        monkeypatch.setattr(announcer, "_wait_for_next_attempt", fake_wait)
        monkeypatch.setattr(announcer, "_announce_once", fake_announce)
        monkeypatch.setattr(discovery_module.random, "uniform", fake_jitter)

        announcer._run_loop()

        assert retry_waits == [0.0, 4.5, 9.0, 4.0]
        assert jitter_bounds == [(0.0, 1.0), (0.0, 2.0)]
        assert observed_attempts == [False, False, True]

    def test_announce_once_serializes_a_deep_payload_snapshot(self, monkeypatch):
        """Changes to the live payload after snapshotting do not alter the request body."""
        from pi_camera_in_docker import discovery as discovery_module

        payload = {
            "webcam_id": "node-test-snapshot",
            "labels": {"location": "kitchen"},
        }
        announcer = discovery_module.DiscoveryAnnouncer(
            management_url="http://management.local:8001",
            token="test-token",
            interval_seconds=30,
            webcam_id=payload["webcam_id"],
            payload=payload,
            shutdown_event=threading.Event(),
        )
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        original_dumps = discovery_module.json.dumps

        def mutate_live_payload(snapshot):
            announcer.payload["labels"]["location"] = "garage"
            return original_dumps(snapshot)

        monkeypatch.setattr(discovery_module.json, "dumps", mutate_live_payload)
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            assert announcer._announce_once() is True

        request = mock_urlopen.call_args.args[0]
        posted_payload = json.loads(request.data)
        assert posted_payload["labels"]["location"] == "kitchen"
        assert announcer.payload["labels"]["location"] == "garage"

    def test_announcer_thread_stops_after_active_announcement_finishes(self, monkeypatch):
        """Verify announcer thread starts and stops correctly."""
        from pi_camera_in_docker.discovery import DiscoveryAnnouncer

        shutdown_event = threading.Event()
        announcer = DiscoveryAnnouncer(
            management_url="http://management.local:8001",
            token="test-token",
            interval_seconds=30,
            webcam_id="node-test-5",
            payload={"webcam_id": "node-test-5"},
            shutdown_event=shutdown_event,
        )
        attempt_started = threading.Event()
        release_attempt = threading.Event()
        loop_stopped = threading.Event()
        original_run_loop = announcer._run_loop

        def blocked_announcement() -> bool:
            attempt_started.set()
            assert release_attempt.wait(timeout=2)
            return True

        def observe_run_loop() -> None:
            try:
                original_run_loop()
            finally:
                loop_stopped.set()

        monkeypatch.setattr(announcer, "_announce_once", blocked_announcement)
        monkeypatch.setattr(announcer, "_run_loop", observe_run_loop)
        announcer.start()

        try:
            assert attempt_started.wait(timeout=2)
            release_attempt.set()
            announcer.stop(timeout_seconds=2)
            assert loop_stopped.is_set()
        finally:
            release_attempt.set()
            announcer.stop(timeout_seconds=2)


class TestDiscoveryEndToEnd:
    """End-to-end tests simulating full announce/management discovery workflow."""

    def test_webcam_announces_to_management_and_gets_approved(self, monkeypatch):
        """Full flow: webcam announces -> management receives -> admin approves node."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"

            # Create management app
            app = Flask(__name__)

            monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
            register_management_routes(
                app,
                registry_path,
                node_discovery_shared_secret="discovery-secret",
            )
            client = app.test_client()

            # Step 1: Webcam announces itself
            announce_payload = {
                "webcam_id": "node-webcam-1",
                "name": "kitchen-camera",
                "base_url": "http://192.168.1.100:8000",
                "transport": "http",
                "capabilities": ["stream", "snapshot"],
                "labels": {"location": "kitchen", "device_class": "webcam"},
            }

            response = client.post(
                "/api/v1/discovery/announce",
                json=announce_payload,
                headers={"Authorization": "Bearer discovery-secret"},
            )

            assert response.status_code == 201, response.json
            node_data = response.json["node"]
            assert node_data["id"] == "node-webcam-1"
            assert node_data["discovery"]["source"] == "discovered"
            assert node_data["discovery"]["approved"] is False, (
                "New discovery should start unapproved"
            )

            # Step 2: Admin approves the discovered node
            approval_response = client.post(
                f"/api/v1/webcams/{node_data['id']}/discovery/approve",
                headers={"Authorization": "Bearer "},  # No auth needed if no token set
            )

            assert approval_response.status_code == 200
            approved_node = approval_response.json["node"]
            assert approved_node["discovery"]["approved"] is True

            # Step 3: Verify node is now in approved state in list
            list_response = client.get("/api/v1/webcams")
            assert list_response.status_code == 200
            nodes = list_response.json["webcams"]
            approved_nodes = [n for n in nodes if n["id"] == "node-webcam-1"]
            assert len(approved_nodes) == 1
            assert approved_nodes[0]["discovery"]["approved"] is True

    def test_webcam_announces_with_private_ip_blocked_without_opt_in(self, monkeypatch):
        """Verify private IP announcements are blocked unless explicitly allowed."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"
            monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
            # Do NOT set MIO_ALLOW_PRIVATE_IPS

            app = Flask(__name__)
            register_management_routes(
                app,
                registry_path,
                node_discovery_shared_secret="discovery-secret",
            )
            client = app.test_client()

            # Try to announce with private IP
            payload = {
                "webcam_id": "node-private-1",
                "name": "private-camera",
                "base_url": "http://192.168.1.100:8000",  # Private IP
                "transport": "http",
                "capabilities": ["stream"],
            }

            response = client.post(
                "/api/v1/discovery/announce",
                json=payload,
                headers={"Authorization": "Bearer discovery-secret"},
            )

            assert response.status_code == 403, "Private IP should be blocked"
            assert "private" in response.json.get("error", {}).get("code", "").lower()

    def test_webcam_announces_with_private_ip_allowed_with_opt_in(self, monkeypatch):
        """Verify private IP announcements are allowed when explicitly configured."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"

            app = Flask(__name__)

            monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
            register_management_routes(
                app,
                registry_path,
                node_discovery_shared_secret="discovery-secret",
            )
            client = app.test_client()

            # Announce with private IP - should succeed
            payload = {
                "webcam_id": "node-private-allowed",
                "name": "private-camera",
                "base_url": "http://192.168.1.100:8000",  # Private IP
                "transport": "http",
                "capabilities": ["stream"],
            }

            response = client.post(
                "/api/v1/discovery/announce",
                json=payload,
                headers={"Authorization": "Bearer discovery-secret"},
            )

            assert response.status_code == 201, response.json
            assert response.json["node"]["base_url"] == "http://192.168.1.100:8000"

    def test_webcam_discovery_payload_structure(self):
        """Verify discovery payload has all required fields for proper management integration."""
        from discovery import build_discovery_payload

        payload = build_discovery_payload(
            {
                "discovery_webcam_id": "node-kitchen",
                "discovery_base_url": "http://192.168.1.50:8000",
            }
        )

        # Verify all required fields
        required_fields = ["webcam_id", "name", "base_url", "transport", "capabilities", "labels"]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

        # Verify label contents identify the node type
        assert payload["labels"]["device_class"] == "webcam"
        assert payload["labels"]["app_mode"] == "webcam"
        assert "hostname" in payload["labels"]

        # Verify capabilities
        assert "stream" in payload["capabilities"]
        assert "snapshot" in payload["capabilities"]

    def test_multiple_webcams_announce_independently(self, monkeypatch):
        """Verify multiple webcams can announce independently without conflicts."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"

            app = Flask(__name__)

            monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
            register_management_routes(
                app,
                registry_path,
                node_discovery_shared_secret="discovery-secret",
            )
            client = app.test_client()

            # Announce three different webcams
            cameras = [
                {
                    "webcam_id": "node-kitchen",
                    "name": "kitchen-cam",
                    "base_url": "http://192.168.1.50:8000",
                },
                {
                    "webcam_id": "node-bedroom",
                    "name": "bedroom-cam",
                    "base_url": "http://192.168.1.51:8000",
                },
                {
                    "webcam_id": "node-porch",
                    "name": "porch-cam",
                    "base_url": "http://192.168.1.52:8000",
                },
            ]

            for camera in cameras:
                payload = {
                    **camera,
                    "transport": "http",
                    "capabilities": ["stream", "snapshot"],
                }
                response = client.post(
                    "/api/v1/discovery/announce",
                    json=payload,
                    headers={"Authorization": "Bearer discovery-secret"},
                )
                assert response.status_code == 201, response.json

            # Verify all three cameras registered
            list_response = client.get("/api/v1/webcams")
            assert list_response.status_code == 200
            nodes = list_response.json["webcams"]
            node_ids = {n["id"] for n in nodes}
            assert "node-kitchen" in node_ids
            assert "node-bedroom" in node_ids
            assert "node-porch" in node_ids
            assert len(node_ids) == 3

    def test_discovery_announce_without_shared_secret_fails(self, monkeypatch):
        """Verify announcement fails if NODE_DISCOVERY_SHARED_SECRET not configured."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"
            # Do NOT set NODE_DISCOVERY_SHARED_SECRET

            app = Flask(__name__)
            register_management_routes(
                app,
                registry_path,
                node_discovery_shared_secret="",  # Empty secret
            )
            client = app.test_client()

            payload = {
                "webcam_id": "node-test",
                "name": "test-cam",
                "base_url": "http://192.168.1.100:8000",
                "transport": "http",
                "capabilities": ["stream"],
            }

            response = client.post(
                "/api/v1/discovery/announce",
                json=payload,
                headers={"Authorization": "Bearer anything"},
            )

            assert response.status_code == 401, "Should fail without valid secret"

    def test_discovery_node_updates_last_announce_timestamp(self, monkeypatch):
        """Verify repeated announcements update last_announce_at timestamp."""
        import time

        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"

            app = Flask(__name__)

            monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
            register_management_routes(
                app,
                registry_path,
                node_discovery_shared_secret="discovery-secret",
            )
            client = app.test_client()

            payload = {
                "webcam_id": "node-update-test",
                "name": "update-cam",
                "base_url": "http://192.168.1.100:8000",
                "transport": "http",
                "capabilities": ["stream"],
            }

            # First announcement
            response1 = client.post(
                "/api/v1/discovery/announce",
                json=payload,
                headers={"Authorization": "Bearer discovery-secret"},
            )
            assert response1.status_code == 201, response1.json
            first_announce = response1.json["node"]["discovery"]["last_announce_at"]

            time.sleep(0.1)  # Small delay

            # Second announcement
            response2 = client.post(
                "/api/v1/discovery/announce",
                json=payload,
                headers={"Authorization": "Bearer discovery-secret"},
            )
            assert response2.status_code == 200, response2.json
            second_announce = response2.json["node"]["discovery"]["last_announce_at"]

            # Timestamps should be different
            assert second_announce != first_announce
            # First seen should remain unchanged
            assert (
                response2.json["node"]["discovery"]["first_seen"]
                == response1.json["node"]["discovery"]["first_seen"]
            )
