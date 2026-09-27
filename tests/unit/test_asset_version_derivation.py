"""Unit tests for deriving frontend asset versions."""

from pi_camera_in_docker.asset_versioning import derive_asset_version


def test_asset_version_changes_when_asset_contents_change(tmp_path):
    """The derived version changes whenever a frontend asset changes."""
    asset = tmp_path / "js" / "app.js"
    asset.parent.mkdir()
    asset.write_text("first", encoding="utf-8")
    first_version = derive_asset_version(tmp_path)

    asset.write_text("second", encoding="utf-8")

    assert derive_asset_version(tmp_path) != first_version
