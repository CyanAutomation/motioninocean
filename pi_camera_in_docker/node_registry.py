import json
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .transport_url_validation import validate_base_url_for_transport


try:
    import fcntl
except ImportError:  # pragma: no cover - unavailable on non-POSIX
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - unavailable on non-Windows
    msvcrt = None


logger = logging.getLogger(__name__)


# Node registry schema and validation constants
REQUIRED_WEBCAM_FIELDS = {
    "id",
    "name",
    "base_url",
    "auth",
    "labels",
    "last_seen",
    "capabilities",
    "transport",
}
DISCOVERY_FIELDS = {"source", "first_seen", "last_announce_at", "approved"}
ALLOWED_DISCOVERY_SOURCES = {"manual", "discovered"}
ALLOWED_TRANSPORTS = {"http", "docker"}


class NodeValidationError(ValueError):
    """Exception raised for webcam validation or registry operation errors.

    Used to wrap validation failures, permission issues, or file corruption errors.
    """


def _webcam_auth_error(webcam_id: str, reason: str) -> NodeValidationError:
    """Create NodeValidationError for deprecated auth field usage.

    Args:
        webcam_id: ID of webcam with deprecated auth.
        reason: Human-readable reason (e.g., "legacy keys present").

    Returns:
        NodeValidationError with detailed migration guidance.
    """
    return NodeValidationError(
        " ".join(
            [
                f"webcam '{webcam_id}' uses deprecated auth fields: {reason}.",
                "Replace auth with {'type': 'bearer', 'token': '<api_token>'} and remove",
                "legacy auth.username/auth.password/auth.encoded fields.",
            ]
        )
    )


def migrate_legacy_auth(auth: Any, webcam_id: str = "unknown") -> Dict[str, Any]:
    """Migrate legacy basic auth fields to modern bearer token format.

    Handles backward compatibility for nodes using deprecated auth fields:
    - auth.type="basic" with auth.token or auth.encoded → bearer token
    - Removes legacy keys (username, password, encoded) after migration.

    Args:
        auth: Auth dictionary potentially containing legacy fields.
        webcam_id: Node ID for error context (default: "unknown").

    Returns:
        Migrated auth dict with type="bearer" and token field.

    Raises:
        NodeValidationError: If auth structure invalid or cannot auto-migrate.
    """
    if not isinstance(auth, dict):
        message = "auth must be an object"
        raise NodeValidationError(message)

    migrated = dict(auth)
    auth_type = migrated.get("type", "none")

    if auth_type == "basic":
        token_candidate = migrated.get("token")
        encoded = migrated.get("encoded")

        if isinstance(token_candidate, str) and token_candidate.strip():
            migrated["type"] = "bearer"
            migrated["token"] = token_candidate.strip()
        elif isinstance(encoded, str) and encoded.lower().startswith("bearer "):
            bearer_token = encoded[7:].strip()
            if not bearer_token:
                raise _webcam_auth_error(webcam_id, "auth.encoded has an empty bearer token")
            migrated["type"] = "bearer"
            migrated["token"] = bearer_token
        else:
            raise _webcam_auth_error(
                webcam_id,
                "auth.type='basic' cannot be auto-migrated without an API token",
            )

    legacy_keys = [key for key in ("encoded", "username", "password") if key in migrated]
    if legacy_keys:
        if (
            isinstance(migrated.get("token"), str)
            and migrated["token"].strip()
            and migrated.get("type") in {"basic", "bearer", "none"}
        ):
            migrated["type"] = "bearer"
            migrated["token"] = migrated["token"].strip()
            for key in legacy_keys:
                migrated.pop(key, None)
        else:
            raise _webcam_auth_error(
                webcam_id,
                f"legacy keys present ({', '.join(f'auth.{key}' for key in legacy_keys)})",
            )

    return migrated


class WebcamRegistry(ABC):
    """Abstract base class for webcam registry implementations.

    Defines interface for persistent webcam storage operations: CRUD, listing, upsert.
    Implementations must handle validation, file locking, and error recovery.
    """

    @abstractmethod
    def list_webcams(self) -> List[Dict[str, Any]]:
        """List all registered nodes.

        Returns:
            List of webcam dictionaries.
        """
        raise NotImplementedError

    @abstractmethod
    def get_webcam(self, webcam_id: str) -> Optional[Dict[str, Any]]:
        """Get webcam by ID.

        Args:
            webcam_id: Unique webcam identifier.

        Returns:
            Node dictionary or None if not found.
        """
        raise NotImplementedError

    @abstractmethod
    def create_webcam(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new node.

        Args:
            node: Node data with required fields (id, name, base_url, auth, etc.).

        Returns:
            Created webcam dictionary.

        Raises:
            NodeValidationError: If validation fails or webcam ID already exists.
        """
        raise NotImplementedError

    @abstractmethod
    def update_webcam(self, webcam_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing webcam with partial data.

        Args:
            webcam_id: ID of webcam to update.
            patch: Partial webcam data to merge (any fields).

        Returns:
            Updated webcam dictionary.

        Raises:
            KeyError: If webcam not found.
            NodeValidationError: If validation fails.
        """
        raise NotImplementedError

    @abstractmethod
    def upsert_webcam(
        self,
        webcam_id: str,
        create_value: Dict[str, Any],
        patch_value: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create webcam if not exists, else update with patch.

        Args:
            webcam_id: Webcam ID to upsert.
            create_value: Data for webcam creation (if new).
            patch_value: Data for webcam update (if exists).

        Returns:
            Dict with 'node' and 'upserted' keys ("created" or "updated").

        Raises:
            NodeValidationError: If validation fails.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_webcam(self, webcam_id: str) -> bool:
        """Delete webcam by ID.

        Args:
            webcam_id: ID of webcam to delete.

        Returns:
            True if deleted, False if not found.
        """
        raise NotImplementedError


def _validate_auth(auth: Any, webcam_id: str = "unknown") -> Dict[str, Any]:
    """Validate and normalize auth configuration.

    Runs migrate_legacy_auth(), ensures no legacy keys remain, validates type/token.
    Supports: auth.type="none" (no token) or "bearer" (requires token).

    Args:
        auth: Auth dictionary to validate.
        webcam_id: Node ID for error context (default: "unknown").

    Returns:
        Validated auth dictionary.

    Raises:
        NodeValidationError: If auth.type invalid, legacy keys present, or token missing.
    """
    auth = migrate_legacy_auth(auth, webcam_id=webcam_id)

    auth_type = auth.get("type", "none")
    if auth_type not in {"none", "bearer"}:
        message = "auth.type must be one of: none, bearer"
        raise NodeValidationError(message)

    for legacy_key in ("encoded", "username", "password"):
        if legacy_key in auth:
            message = f"auth.{legacy_key} is not supported; use auth.type='bearer' with auth.token"
            raise NodeValidationError(message)

    if auth_type == "bearer":
        token = auth.get("token")
        if not isinstance(token, str) or not token.strip():
            message = "auth.token is required for auth.type='bearer'"
            raise NodeValidationError(message)

    return auth


def _validate_required_fields_present(node: Dict[str, Any], partial: bool) -> None:
    """Validate that all required webcam fields are present.

    Checks that all fields in REQUIRED_WEBCAM_FIELDS are present in node.
    Only enforced if partial=False (full validation).

    Args:
        node: Node data dictionary.
        partial: If True, required field check is skipped.

    Raises:
        NodeValidationError: If required fields are missing and partial=False.
    """
    if not partial:
        missing = REQUIRED_WEBCAM_FIELDS.difference(node.keys())
        if missing:
            missing_fields = ", ".join(sorted(missing))
            message = f"missing required fields: {missing_fields}"
            raise NodeValidationError(message)


def _validate_and_normalize_string_fields(node: Dict[str, Any], fields: set) -> Dict[str, str]:
    """Validate and normalize string fields.

    Validates that string fields (id, name, base_url, last_seen, transport) are
    non-empty strings and returns normalized (stripped) versions.

    Args:
        node: Node data dictionary.
        fields: Set of field names to validate (intersection with REQUIRED_WEBCAM_FIELDS).

    Returns:
        Dictionary of validated string fields with whitespace stripped.

    Raises:
        NodeValidationError: If any field is not a non-empty string.
    """
    validated: Dict[str, str] = {}
    string_fields = {"id", "name", "base_url", "last_seen", "transport"}

    for field in string_fields:
        if field not in fields:
            continue
        value = node[field]
        if not isinstance(value, str) or not value.strip():
            message = f"{field} must be a non-empty string"
            raise NodeValidationError(message)
        validated[field] = value.strip()

    return validated


def _validate_labels(value: Any) -> Dict[str, Any]:
    """Validate labels field.

    Ensures labels is a dictionary.

    Args:
        value: Labels value to validate.

    Returns:
        Validated labels dictionary.

    Raises:
        NodeValidationError: If labels is not a dictionary.
    """
    if not isinstance(value, dict):
        message = "labels must be an object"
        raise NodeValidationError(message)
    return value


def _validate_capabilities(value: Any) -> List[str]:
    """Validate capabilities field.

    Ensures capabilities is a list of strings.

    Args:
        value: Capabilities value to validate.

    Returns:
        Validated capabilities list.

    Raises:
        NodeValidationError: If capabilities is not a list or contains non-strings.
    """
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        message = "capabilities must be an array of strings"
        raise NodeValidationError(message)
    return value


def _validate_discovery_object(discovery: Any) -> Dict[str, Any]:
    """Validate discovery configuration object.

    Validates all discovery fields (source, first_seen, last_announce_at, approved)
    and rejects any unknown fields. Returns a validated discovery dictionary.

    Args:
        discovery: Discovery object to validate.

    Returns:
        Validated discovery dictionary.

    Raises:
        NodeValidationError: If discovery is not a dict, contains unsupported fields,
            or any field fails validation.
    """
    if not isinstance(discovery, dict):
        message = "discovery must be an object"
        raise NodeValidationError(message)

    unknown = set(discovery.keys()).difference(DISCOVERY_FIELDS)
    if unknown:
        message = f"discovery contains unsupported fields: {', '.join(sorted(unknown))}"
        raise NodeValidationError(message)

    validated_discovery: Dict[str, Any] = {}

    if "source" in discovery:
        source = discovery["source"]
        if not isinstance(source, str) or source not in ALLOWED_DISCOVERY_SOURCES:
            message = "discovery.source must be one of: manual, discovered"
            raise NodeValidationError(message)
        validated_discovery["source"] = source

    for timestamp_field in ("first_seen", "last_announce_at"):
        if timestamp_field in discovery:
            value = discovery[timestamp_field]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                message = f"discovery.{timestamp_field} must be a non-empty string or null"
                raise NodeValidationError(message)
            validated_discovery[timestamp_field] = value.strip() if isinstance(value, str) else None

    if "approved" in discovery:
        approved = discovery["approved"]
        if not isinstance(approved, bool):
            message = "discovery.approved must be a boolean"
            raise NodeValidationError(message)
        validated_discovery["approved"] = approved

    return validated_discovery


def validate_webcam(node: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
    """Validate and normalize webcam data.

    Validates required fields (unless partial=True), type-checks all fields,
    validates auth, discovery, transport, base_url format.
    Sets last_seen timestamp if missing (and not partial).

    Args:
        node: Node data dictionary.
        partial: If True, only provided fields required (for PATCH operations).

    Returns:
        Validated and normalized webcam dictionary.

    Raises:
        NodeValidationError: If validation fails for any field.
    """
    if not isinstance(node, dict):
        message = "webcam payload must be an object"
        raise NodeValidationError(message)

    _validate_required_fields_present(node, partial)

    validated: Dict[str, Any] = {}
    fields = REQUIRED_WEBCAM_FIELDS.intersection(node.keys())

    string_fields = _validate_and_normalize_string_fields(node, fields)
    validated.update(string_fields)

    if "labels" in fields:
        validated["labels"] = _validate_labels(node["labels"])

    if "capabilities" in fields:
        validated["capabilities"] = _validate_capabilities(node["capabilities"])

    if "auth" in fields:
        validated["auth"] = _validate_auth(node["auth"], webcam_id=str(node.get("id", "unknown")))

    if "transport" in validated and validated["transport"] not in ALLOWED_TRANSPORTS:
        message = "transport must be one of: http, docker"
        raise NodeValidationError(message)

    if "base_url" in validated:
        transport = validated.get("transport")
        if partial and transport is None:
            transport = node.get("transport")
        if transport in ALLOWED_TRANSPORTS:
            try:
                validate_base_url_for_transport(validated["base_url"], transport)
            except ValueError as exc:
                raise NodeValidationError(str(exc)) from exc

    if not partial and "last_seen" not in validated:
        validated["last_seen"] = datetime.now(timezone.utc).isoformat()

    if "discovery" in node:
        validated["discovery"] = _validate_discovery_object(node["discovery"])

    return validated


class FileWebcamRegistry(WebcamRegistry):
    """File-based webcam registry with POSIX/Windows file locking.

    Stores nodes in JSON file with exclusive locking to prevent concurrent mutations.
    Auto-creates parent directory and handles legacy auth migration on load.
    Supports both fcntl (Unix) and msvcrt (Windows) locking mechanisms.

    Attributes:
        path: Path to JSON registry file.

    Raises:
        NodeValidationError: If registry directory not writable or file corrupted.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            message = (
                f"Permission denied accessing registry path: {self.path.parent}. "
                f"Set NODE_REGISTRY_PATH to a writable directory (e.g., ./data/node-registry.json) "
                f"and ensure the container has write access. See DEPLOYMENT.md for details."
            )
            logger.error(message)
            raise NodeValidationError(message) from e

    def _load(self) -> Dict[str, Any]:
        """Load and validate registry from JSON file.

        Auto-creates empty registry if file doesn't exist.
        Validates all nodes during load, applies migration to legacy auth fields.

        Returns:
            Dict with "nodes" key containing list of validated webcam dicts.

        Raises:
            NodeValidationError: If file corrupted or webcam validation fails.
        """
        if not self.path.exists():
            return {"nodes": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            message = f"webcam registry file is corrupted and cannot be parsed: {self.path}"
            raise NodeValidationError(message) from exc
        if not isinstance(raw, dict):
            return {"nodes": []}
        nodes = raw.get("nodes", [])
        if not isinstance(nodes, list):
            nodes = []

        migrated_nodes: List[Dict[str, Any]] = []
        for index, webcam in enumerate(nodes):
            if not isinstance(webcam, dict):
                message = f"webcam at index {index} must be an object"
                raise NodeValidationError(message)

            migrated = dict(webcam)
            migrated_nodes.append(validate_webcam(migrated))

        return {"nodes": migrated_nodes}

    def _save(self, data: Dict[str, Any]) -> None:
        """Save registry to JSON file with atomic write.

        Uses temp file + atomic rename to prevent corruption on crash.
        Fsyncs data to disk before rename.

        Args:
            data: Registry dict with "nodes" key.
        """
        with tempfile.NamedTemporaryFile(
            "w", delete=False, dir=self.path.parent, encoding="utf-8"
        ) as temp:
            json.dump(data, temp, indent=2)
            temp.flush()
            os.fsync(temp.fileno())
            temp_path = temp.name
        Path(temp_path).replace(self.path)

    @contextmanager
    def _exclusive_lock(self):
        """Context manager for exclusive file locking.

        Uses fcntl.flock (Unix) or msvcrt.locking (Windows) for cross-platform support.
        Lock file created in same directory as registry file.

        Yields:
            None (lock held for context duration).

        Raises:
            RuntimeError: If no supported locking backend available.
        """
        lock_path = self.path.parent / f"{self.path.name}.lock"
        with lock_path.open("a+b") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                return

            if msvcrt is not None:
                file_size = lock_file.seek(0, 2)  # Seek to end to get size
                if file_size == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                return

            message = "No supported file-lock backend available for this platform"
            raise RuntimeError(message)

    def list_webcams(self) -> List[Dict[str, Any]]:
        """List all registered nodes.

        Returns:
            List of webcam dictionaries.
        """
        with self._exclusive_lock():
            return self._load()["nodes"]

    def get_webcam(self, webcam_id: str) -> Optional[Dict[str, Any]]:
        """Get webcam by ID.

        Args:
            webcam_id: Unique webcam identifier.

        Returns:
            Node dictionary or None if not found.
        """
        for webcam in self.list_webcams():
            if webcam.get("id") == webcam_id:
                return webcam
        return None

    def create_webcam(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Create new webcam with exclusive lock.

        Validates node, checks ID uniqueness, appends to registry.

        Args:
            node: Node data with required fields.

        Returns:
            Created webcam dictionary.

        Raises:
            NodeValidationError: If validation fails or ID already exists.
        """
        candidate = validate_webcam(node)

        with self._exclusive_lock():
            data = self._load()
            if any(existing.get("id") == candidate["id"] for existing in data["nodes"]):
                message = f"webcam {candidate['id']} already exists"
                raise NodeValidationError(message)
            data["nodes"].append(candidate)
            self._save(data)
            return candidate

    def update_webcam(self, webcam_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing webcam by merging patch data.

        Validates patch, merges with existing webcam (deep-merges discovery), re-validates merged.
        Checks ID uniqueness after merge.

        Args:
            webcam_id: ID of webcam to update.
            patch: Partial webcam data to merge.

        Returns:
            Updated webcam dictionary.

        Raises:
            KeyError: If webcam_id not found.
            NodeValidationError: If validation or ID uniqueness check fails.
        """
        validated_patch = validate_webcam(patch, partial=True)

        with self._exclusive_lock():
            data = self._load()
            for index, existing in enumerate(data["nodes"]):
                if existing.get("id") != webcam_id:
                    continue
                merged = {**existing, **validated_patch}
                if isinstance(existing.get("discovery"), dict) and isinstance(
                    validated_patch.get("discovery"), dict
                ):
                    merged["discovery"] = {**existing["discovery"], **validated_patch["discovery"]}
                merged = validate_webcam(merged)
                if any(
                    other_index != index and other.get("id") == merged["id"]
                    for other_index, other in enumerate(data["nodes"])
                ):
                    message = f"webcam {merged['id']} already exists"
                    raise NodeValidationError(message)
                data["nodes"][index] = merged
                self._save(data)
                return merged
            raise KeyError(webcam_id)

    def upsert_webcam(
        self,
        webcam_id: str,
        create_value: Dict[str, Any],
        patch_value: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create or update webcam with exclusive lock.

        If webcam exists: merges patch_value and validates merged result.
        If webcam not exists: creates with create_value.
        Returns dict with 'node' and 'upserted' ("created"/"updated") keys.

        Args:
            webcam_id: Webcam ID to upsert.
            create_value: Data for webcam creation (if new).
            patch_value: Data for webcam update (if exists).

        Returns:
            Dict with keys: 'node' (the node), 'upserted' (\"created\" or \"updated\").

        Raises:
            NodeValidationError: If validation or ID uniqueness check fails.
        """
        candidate = validate_webcam(create_value)
        validated_patch = validate_webcam(patch_value, partial=True)

        with self._exclusive_lock():
            data = self._load()
            for index, existing in enumerate(data["nodes"]):
                if existing.get("id") != webcam_id:
                    continue

                merged = {**existing, **validated_patch}
                if isinstance(existing.get("discovery"), dict) and isinstance(
                    validated_patch.get("discovery"), dict
                ):
                    merged["discovery"] = {**existing["discovery"], **validated_patch["discovery"]}
                merged = validate_webcam(merged)
                if any(
                    other_index != index and other.get("id") == merged["id"]
                    for other_index, other in enumerate(data["nodes"])
                ):
                    message = f"webcam {merged['id']} already exists"
                    raise NodeValidationError(message)
                data["nodes"][index] = merged
                self._save(data)
                return {"node": merged, "upserted": "updated"}

            if any(existing.get("id") == candidate["id"] for existing in data["nodes"]):
                message = f"webcam {candidate['id']} already exists"
                raise NodeValidationError(message)
            data["nodes"].append(candidate)
            self._save(data)
            return {"node": candidate, "upserted": "created"}

    def upsert_webcam_from_current(
        self,
        webcam_id: str,
        create_value: Dict[str, Any],
        patch_builder: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create or update webcam using an in-lock patch builder.

        Computes the update patch from the currently persisted webcam record while
        holding the exclusive registry lock. This avoids stale caller-side snapshots
        when concurrent writers modify the same node between reads and writes.

        Args:
            webcam_id: Webcam ID to upsert.
            create_value: Data for webcam creation (if new).
            patch_builder: Callback that receives the in-lock existing webcam record
                and returns a partial patch to apply.

        Returns:
            Dict with keys: 'node' (the node), 'upserted' ("created" or "updated").

        Raises:
            NodeValidationError: If validation or ID uniqueness check fails.
        """
        candidate = validate_webcam(create_value)

        with self._exclusive_lock():
            data = self._load()
            for index, existing in enumerate(data["nodes"]):
                if existing.get("id") != webcam_id:
                    continue

                patch_value = patch_builder(existing)
                validated_patch = validate_webcam(patch_value, partial=True)
                merged = {**existing, **validated_patch}
                if isinstance(existing.get("discovery"), dict) and isinstance(
                    validated_patch.get("discovery"), dict
                ):
                    merged["discovery"] = {**existing["discovery"], **validated_patch["discovery"]}
                merged = validate_webcam(merged)
                if any(
                    other_index != index and other.get("id") == merged["id"]
                    for other_index, other in enumerate(data["nodes"])
                ):
                    message = f"webcam {merged['id']} already exists"
                    raise NodeValidationError(message)
                data["nodes"][index] = merged
                self._save(data)
                return {"node": merged, "upserted": "updated"}

            if any(existing.get("id") == candidate["id"] for existing in data["nodes"]):
                message = f"webcam {candidate['id']} already exists"
                raise NodeValidationError(message)
            data["nodes"].append(candidate)
            self._save(data)
            return {"node": candidate, "upserted": "created"}

    def delete_webcam(self, webcam_id: str) -> bool:
        """Delete webcam by ID with exclusive lock.

        Args:
            webcam_id: ID of webcam to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._exclusive_lock():
            data = self._load()
            previous_count = len(data["nodes"])
            data["nodes"] = [webcam for webcam in data["nodes"] if webcam.get("id") != webcam_id]
            if previous_count == len(data["nodes"]):
                return False
            self._save(data)
            return True
