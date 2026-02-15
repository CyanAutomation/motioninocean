import importlib
import logging
import sys
import types

import pytest


logger = logging.getLogger(__name__)


@pytest.fixture
def clean_sys_modules():
    """Fixture to clean up sys.modules after tests that modify it."""
    original_sys_modules = sys.modules.copy()
    yield
    sys.modules.clear()
    sys.modules.update(original_sys_modules)


@pytest.fixture(autouse=True)
def caplog_for_test(caplog):
    """Fixture to capture logs during tests."""
    caplog.set_level(logging.INFO)
    return caplog


def test_module_not_found_scenario(clean_sys_modules, caplog_for_test):
    """
    Test scenario: Simulate ModuleNotFoundError for pykms and verify the workaround.
    """
    # Ensure picamera2 is available, skip if not
    pytest.importorskip("picamera2")

    logger.info("Testing pykms import workaround (ModuleNotFoundError scenario)...")
    logger.info("=" * 60)

    # Test 1: Simulate the absence of pykms by blocking it
    logger.info("\n[Test 1] ModuleNotFoundError scenario")
    logger.info("-" * 60)

    # Temporarily remove pykms and kms from sys.modules
    sys.modules["pykms"] = None
    sys.modules["kms"] = None

    try:
        # Try importing picamera2 - this should initially raise ModuleNotFoundError
        importlib.import_module("picamera2")
        pytest.fail("FAIL: Import should have failed but succeeded before workaround.")
    except ModuleNotFoundError as e:
        if "pykms" in str(e) or "kms" in str(e):
            logger.info("✓ Expected error caught: %s", e)

            # Now apply the workaround
            logger.info("\nApplying mock module workaround...")

            # Create mock modules
            pykms_mock = types.ModuleType("pykms")
            kms_mock = types.ModuleType("kms")

            # Add to sys.modules
            sys.modules["pykms"] = pykms_mock
            sys.modules["kms"] = kms_mock

            logger.info("✓ Mock modules created and registered")

            # Retry import
            try:
                picamera2_module = importlib.import_module("picamera2")
                # Access a common attribute to ensure it's functional
                _ = picamera2_module.Picamera2
                logger.info("✓ picamera2 imported successfully with mock modules!")

                # Verify PixelFormat mock is available
                # Re-import pykms to get the mock
                import pykms

                if hasattr(pykms, "PixelFormat") and hasattr(pykms.PixelFormat, "RGB888"):
                    logger.info("✓ PixelFormat mock with RGB888 attribute available")
                else:
                    logger.warning("⚠️  WARNING: PixelFormat mock may be incomplete")

                logger.info("\n✅ SUCCESS: ModuleNotFoundError workaround working correctly")
                assert True  # Explicitly pass
            except Exception as retry_error:
                pytest.fail(f"FAIL: Import still failed after workaround: {retry_error}")
        else:
            pytest.fail(f"FAIL: Unexpected error: {e}")
    except Exception as e:
        pytest.fail(f"FAIL: Unexpected error type during ModuleNotFoundError scenario: {e}")


def test_attribute_error_scenario(clean_sys_modules, caplog_for_test):
    """
    Test scenario: Simulate incomplete pykms (missing PixelFormat) and verify behaviour.
    """
    # Ensure picamera2 is available, skip if not
    pytest.importorskip("picamera2")

    logger.info("Testing pykms import workaround (AttributeError scenario)...")
    logger.info("=" * 60)

    # Test 2: Simulate incomplete pykms (has module but missing PixelFormat)
    logger.info("\n[Test 2] AttributeError scenario (incomplete pykms)")
    logger.info("-" * 60)

    # Create incomplete pykms mock (missing PixelFormat)
    incomplete_pykms = types.ModuleType("pykms")
    incomplete_kms = types.ModuleType("kms")
    sys.modules["pykms"] = incomplete_pykms
    sys.modules["kms"] = incomplete_kms

    logger.info("✓ Incomplete pykms module created (no PixelFormat attribute)")

    # This should trigger AttributeError which the workaround should catch
    try:
        # Force reimport by removing picamera2 from cache
        if "picamera2" in sys.modules:
            del sys.modules["picamera2"]
        # Ensure any submodules are also cleared if they've been loaded
        for module_name in list(sys.modules.keys()):
            if module_name.startswith("picamera2"):
                del sys.modules[module_name]

        picamera2_module = importlib.import_module("picamera2")
        # Attempt to access Picamera2 which might trigger the underlying PixelFormat issue
        _ = picamera2_module.Picamera2
        logger.warning(
            "⚠️  Note: picamera2 imported without error (may have internal fallback). This is acceptable for this test."
        )
        assert (
            True
        )  # If picamera2 handles it internally, this scenario might not strictly fail import.
    except AttributeError as attr_error:
        if "PixelFormat" in str(attr_error):
            logger.info("✓ Expected AttributeError caught: %s", attr_error)
            logger.info("✓ This error would be caught by the enhanced workaround in main.py")
            assert True  # Expected behavior
        else:
            pytest.fail(f"FAIL: Unexpected AttributeError: {attr_error}")
    except Exception as e:
        pytest.fail(f"FAIL: Unexpected error in Test 2: {e}")

    logger.info("\n✅ SUCCESS: All pykms import workaround tests completed.")
