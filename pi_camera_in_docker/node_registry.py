import json
import os
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


REQUIRED_NODE_FIELDS = {
    "id",
    "name",
    "base_url",
    "auth",
    "labels",
    "last_seen",
    "capabilities",
    "transport",
}
ALLOWED_TRANSPORTS = {"http", "docker"}


class NodeValidationError(ValueError):
    pass


class NodeRegistry(ABC):
    @abstractmethod
    def list_nodes(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_node(self, node_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete_node(self, node_id: str) -> bool:
        raise NotImplementedError


def _validate_auth(auth: Any) -> None:
    if not isinstance(auth, dict):
        raise NodeValidationError("auth must be an object")
    auth_type = auth.get("type", "none")
    if auth_type not in {"none", "bearer", "basic"}:
        raise NodeValidationError("auth.type must be one of: none, bearer, basic")

    if auth_type == "bearer" and "token" in auth:
        if not isinstance(auth.get("token"), str) or not auth.get("token").strip():
            raise NodeValidationError("auth.token must be a non-empty string")

    if auth_type != "basic":
        return

    has_encoded = "encoded" in auth
    has_username_or_password = "username" in auth or "password" in auth

    if has_encoded:
        encoded = auth.get("encoded")
        if not isinstance(encoded, str) or not encoded.strip():
            raise NodeValidationError("auth.encoded must be a non-empty string")

    if has_username_or_password:
        username = auth.get("username")
        password = auth.get("password")
        if not isinstance(username, str) or not username.strip():
            raise NodeValidationError("auth.username must be a non-empty string")
        if not isinstance(username, str) or not username.strip():
            raise NodeValidationError("auth.username must be a non-empty string")
        if ":" in username:
            raise NodeValidationError("auth.username cannot contain colon character")
        if not isinstance(password, str) or len(password) == 0:
            raise NodeValidationError("auth.password must be a non-empty string")

    if not has_encoded and not has_username_or_password:
        raise NodeValidationError(
            "basic auth requires either auth.encoded or auth.username/auth.password"
        )


def validate_node(node: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
    if not isinstance(node, dict):
        raise NodeValidationError("node payload must be an object")

    if not partial:
        missing = REQUIRED_NODE_FIELDS.difference(node.keys())
        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise NodeValidationError(f"missing required fields: {missing_fields}")

    validated: Dict[str, Any] = {}
    fields = REQUIRED_NODE_FIELDS.intersection(node.keys())

    for field in fields:
        value = node[field]
        if field in {"id", "name", "base_url", "last_seen", "transport"}:
            if not isinstance(value, str) or not value.strip():
                raise NodeValidationError(f"{field} must be a non-empty string")
            validated[field] = value.strip()
        elif field == "labels":
            if not isinstance(value, dict):
                raise NodeValidationError("labels must be an object")
            validated[field] = value
        elif field == "capabilities":
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                raise NodeValidationError("capabilities must be an array of strings")
            validated[field] = value
        elif field == "auth":
            _validate_auth(value)
            validated[field] = value

    if "transport" in validated and validated["transport"] not in ALLOWED_TRANSPORTS:
        raise NodeValidationError("transport must be one of: http, docker")

    if "base_url" in validated and not validated["base_url"].startswith(("http://", "https://")):
        raise NodeValidationError("base_url must start with http:// or https://")

    if not partial and "last_seen" not in validated:
        validated["last_seen"] = datetime.utcnow().isoformat()

    return validated


class FileNodeRegistry(NodeRegistry):
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"nodes": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Handle corrupted registry file - return empty to allow recovery
            return {"nodes": []}
        if not isinstance(raw, dict):
            return {"nodes": []}
        nodes = raw.get("nodes", [])
        if not isinstance(nodes, list):
            nodes = []
        return {"nodes": nodes}

    def _save(self, data: Dict[str, Any]) -> None:
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
        lock_path = self.path.parent / f"{self.path.name}.lock"
        with open(lock_path, "w", encoding="utf-8") as lock_file:
            has_fcntl = False
            try:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                has_fcntl = True
            except ImportError:
                pass

            try:
                yield
            finally:
                if not has_fcntl:
                    return
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass

    def list_nodes(self) -> List[Dict[str, Any]]:
        return self._load()["nodes"]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        for node in self.list_nodes():
            if node.get("id") == node_id:
                return node
        return None

    def create_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        candidate = validate_node(node)

        with self._exclusive_lock():
            data = self._load()
            if any(existing.get("id") == candidate["id"] for existing in data["nodes"]):
                raise NodeValidationError(f"node {candidate['id']} already exists")
            data["nodes"].append(candidate)
            self._save(data)
            return candidate

    def update_node(self, node_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        validated_patch = validate_node(patch, partial=True)

        with self._exclusive_lock():
            data = self._load()
            for index, existing in enumerate(data["nodes"]):
                if existing.get("id") != node_id:
                    continue
                merged = {**existing, **validated_patch}
                merged = validate_node(merged)
                if any(
                    other_index != index and other.get("id") == merged["id"]
                    for other_index, other in enumerate(data["nodes"])
                ):
                    raise NodeValidationError(f"node {merged['id']} already exists")
                data["nodes"][index] = merged
                self._save(data)
                return merged
            raise KeyError(node_id)

    def delete_node(self, node_id: str) -> bool:
        with self._exclusive_lock():
            data = self._load()
            previous_count = len(data["nodes"])
            data["nodes"] = [node for node in data["nodes"] if node.get("id") != node_id]
            if previous_count == len(data["nodes"]):
                return False
            self._save(data)
            return True
