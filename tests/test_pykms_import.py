import builtins
import sys
import types

import pytest


def _install_fake_picamera2_modules(monkeypatch):
    picamera2_module = types.ModuleType("picamera2")
    encoders_module = types.ModuleType("picamera2.encoders")
    outputs_module = types.ModuleType("picamera2.outputs")

    class FakePicamera2:
        pass

    class FakeJpegEncoder:
        pass

    class FakeFileOutput:
        pass

    picamera2_module.Picamera2 = FakePicamera2
    encoders_module.JpegEncoder = FakeJpegEncoder
    outputs_module.FileOutput = FakeFileOutput

    monkeypatch.setitem(sys.modules, "picamera2", picamera2_module)
    monkeypatch.setitem(sys.modules, "picamera2.encoders", encoders_module)
    monkeypatch.setitem(sys.modules, "picamera2.outputs", outputs_module)

    return FakePicamera2, FakeJpegEncoder, FakeFileOutput


def test_import_components_mocks_pykms_when_allowed(monkeypatch):
    """When picamera2 initially fails on pykms import, helper should inject mocks and retry."""
    from pi_camera_in_docker.modes.webcam import import_camera_components

    expected_picamera2, expected_encoder, expected_output = _install_fake_picamera2_modules(
        monkeypatch
    )

    monkeypatch.delitem(sys.modules, "pykms", raising=False)
    monkeypatch.delitem(sys.modules, "kms", raising=False)

    real_import = builtins.__import__
    should_fail_once = {"value": True}

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "picamera2" and should_fail_once["value"]:
            should_fail_once["value"] = False
            raise ModuleNotFoundError("No module named 'pykms'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    picamera2_cls, jpeg_encoder_cls, file_output_cls = import_camera_components(
        allow_pykms_mock=True
    )

    assert picamera2_cls is expected_picamera2
    assert jpeg_encoder_cls is expected_encoder
    assert file_output_cls is expected_output
    assert hasattr(sys.modules["pykms"], "PixelFormat")
    assert hasattr(sys.modules["kms"], "PixelFormat")
    assert sys.modules["pykms"].PixelFormat.RGB888 == "RGB888"


def test_import_components_raises_when_mock_not_allowed(monkeypatch):
    """If pykms-related import fails and fallback is disabled, error should be surfaced."""
    from pi_camera_in_docker.modes.webcam import import_camera_components

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "picamera2":
            raise ModuleNotFoundError("No module named 'pykms'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ModuleNotFoundError, match="pykms"):
        import_camera_components(allow_pykms_mock=False)
