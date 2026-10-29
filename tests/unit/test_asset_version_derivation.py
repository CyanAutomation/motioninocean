"""Unit tests for deriving frontend asset versions."""

from flask import Flask

from pi_camera_in_docker.asset_versioning import derive_asset_version, register_asset_versioning
from scripts.generate_asset_version import derive_asset_version as derive_build_asset_version


def test_asset_version_changes_when_asset_contents_change(tmp_path):
    """The derived version changes whenever a frontend asset changes."""
    asset = tmp_path / "js" / "app.js"
    asset.parent.mkdir()
    asset.write_text("first", encoding="utf-8")
    first_version = derive_asset_version(tmp_path)

    asset.write_text("second", encoding="utf-8")

    assert derive_asset_version(tmp_path) != first_version


def test_build_and_runtime_asset_hash_algorithms_match(tmp_path):
    asset = tmp_path / "css" / "site.css"
    asset.parent.mkdir()
    asset.write_text("body { color: navy; }", encoding="utf-8")

    assert derive_build_asset_version(tmp_path) == derive_asset_version(tmp_path)


def test_asset_registration_uses_precomputed_version_file(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")
    expected = derive_asset_version(static_dir)
    (tmp_path / "ASSET_VERSION").write_text(expected + "\n", encoding="ascii")
    app = Flask(__name__, root_path=str(tmp_path), static_folder=str(static_dir))
    app.root_path = str(tmp_path / "app")

    def unexpected_runtime_hash(_directory):
        raise AssertionError("precomputed asset version should avoid startup hashing")

    monkeypatch.setattr(
        "pi_camera_in_docker.asset_versioning.derive_asset_version", unexpected_runtime_hash
    )

    assert register_asset_versioning(app) == expected
