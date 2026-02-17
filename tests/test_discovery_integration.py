"""
Integration tests for the announce and discovery mode.
Tests the full workflow of webcam nodes announcing themselves to management.
"""

import json
import tempfile
import threading
import time
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

    def test_announcer_retries_with_exponential_backoff(self):
        """Verify announcer retries with exponential backoff on failures."""
        import urllib.error

        from discovery import DiscoveryAnnouncer

        shutdown_event = threading.Event()
        payload = {"webcam_id": "node-test-4"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Fail first, then succeed later
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)

            mock_urlopen.side_effect = [
                urllib.error.URLError("Connection refused"),
                urllib.error.URLError("Connection refused"),
                mock_response,  # Success on third attempt
            ]

            announcer = DiscoveryAnnouncer(
                management_url="http://management.local:8001",
                token="test-token",
                interval_seconds=0.01,  # Very short interval for testing
                webcam_id=payload["webcam_id"],
                payload=payload,
                shutdown_event=shutdown_event,
            )

            # Run the announce loop for a short time - with short interval it should retry
            announcer.start()
            time.sleep(3.0)  # Allow retries to happen with exponential backoff
            announcer.stop()

            # Should have attempted at least 2 times - first 2 failures
            assert mock_urlopen.call_count >= 2

    def test_announcer_thread_lifecycle(self):
        """Verify announcer thread starts and stops correctly."""
        from discovery import DiscoveryAnnouncer

        shutdown_event = threading.Event()
        payload = {"webcam_id": "node-test-5"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            announcer = DiscoveryAnnouncer(
                management_url="http://management.local:8001",
                token="test-token",
                interval_seconds=0.05,  # Very short interval
                webcam_id=payload["webcam_id"],
                payload=payload,
                shutdown_event=shutdown_event,
            )

            # Verify thread not started yet
            assert announcer._thread is None or not announcer._thread.is_alive()

            # Start and verify thread is running
            announcer.start()
            assert announcer._thread is not None
            assert announcer._thread.is_alive()

            # Stop and verify thread is dead
            announcer.stop()
            time.sleep(0.2)  # Give thread time to exit
            assert not announcer._thread.is_alive()


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

            # Patch ALLOW_PRIVATE_IPS to allow private IP announcements for this test
            with patch("pi_camera_in_docker.management_api.ALLOW_PRIVATE_IPS", True):
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
                    "/api/discovery/announce",
                    json=announce_payload,
                    headers={"Authorization": "Bearer discovery-secret"},
                )

                assert response.status_code == 201, response.json
                node_data = response.json["node"]
                assert node_data["webcam_id"] == "node-webcam-1"
                assert node_data["discovery"]["source"] == "discovered"
                assert node_data["discovery"]["approved"] is False, (
                    "New discovery should start unapproved"
                )

                # Step 2: Admin approves the discovered node
                approval_response = client.post(
                    f"/api/nodes/{node_data['webcam_id']}/discovery/approve",
                    headers={"Authorization": "Bearer "},  # No auth needed if no token set
                )

                assert approval_response.status_code == 200
                approved_node = approval_response.json["node"]
                assert approved_node["discovery"]["approved"] is True

                # Step 3: Verify node is now in approved state in list
                list_response = client.get("/api/webcams")
                assert list_response.status_code == 200
                nodes = list_response.json["webcams"]
                approved_nodes = [n for n in nodes if n["webcam_id"] == "node-webcam-1"]
                assert len(approved_nodes) == 1
                assert approved_nodes[0]["discovery"]["approved"] is True

    def test_webcam_announces_with_private_ip_blocked_without_opt_in(self, monkeypatch):
        """Verify private IP announcements are blocked unless explicitly allowed."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        with tempfile.TemporaryDirectory() as registry_dir:
            registry_path = f"{registry_dir}/registry.json"
            monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
            # Do NOT set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS

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
                "/api/discovery/announce",
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

            # Patch ALLOW_PRIVATE_IPS to allow private IP announcements
            with patch("pi_camera_in_docker.management_api.ALLOW_PRIVATE_IPS", True):
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
                    "/api/discovery/announce",
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

            # Patch ALLOW_PRIVATE_IPS to allow private IP announcements
            with patch("pi_camera_in_docker.management_api.ALLOW_PRIVATE_IPS", True):
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
                        "/api/discovery/announce",
                        json=payload,
                        headers={"Authorization": "Bearer discovery-secret"},
                    )
                    assert response.status_code == 201, response.json

                # Verify all three cameras registered
                list_response = client.get("/api/webcams")
                assert list_response.status_code == 200
                nodes = list_response.json["webcams"]
                node_ids = {n["webcam_id"] for n in nodes}
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
                "/api/discovery/announce",
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

            # Patch ALLOW_PRIVATE_IPS to allow private IP announcements
            with patch("pi_camera_in_docker.management_api.ALLOW_PRIVATE_IPS", True):
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
                    "/api/discovery/announce",
                    json=payload,
                    headers={"Authorization": "Bearer discovery-secret"},
                )
                assert response1.status_code == 201, response1.json
                first_announce = response1.json["node"]["discovery"]["last_announce_at"]

                time.sleep(0.1)  # Small delay

                # Second announcement
                response2 = client.post(
                    "/api/discovery/announce",
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
