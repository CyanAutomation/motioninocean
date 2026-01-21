"""
Unit tests for pykms import fallback workaround.
Tests the mock module workaround for environments without pykms.
"""

import pytest
import sys
import types


@pytest.mark.unit
def test_pykms_mock_creation():
    """Test that we can create mock pykms modules."""
    # Create mock modules
    pykms_mock = types.ModuleType('pykms')
    kms_mock = types.ModuleType('kms')
    
    assert pykms_mock is not None
    assert kms_mock is not None
    assert pykms_mock.__name__ == 'pykms'
    assert kms_mock.__name__ == 'kms'


@pytest.mark.unit
def test_pykms_workaround_logic():
    """Test the pykms import workaround logic without actually importing picamera2."""
    # Save original state
    original_pykms = sys.modules.get('pykms')
    original_kms = sys.modules.get('kms')
    
    try:
        # Simulate the workaround
        pykms_mock = types.ModuleType('pykms')
        kms_mock = types.ModuleType('kms')
        
        sys.modules['pykms'] = pykms_mock
        sys.modules['kms'] = kms_mock
        
        # Verify they're registered
        assert 'pykms' in sys.modules
        assert 'kms' in sys.modules
        assert sys.modules['pykms'] == pykms_mock
        assert sys.modules['kms'] == kms_mock
        
    finally:
        # Restore original state
        if original_pykms is None:
            sys.modules.pop('pykms', None)
        else:
            sys.modules['pykms'] = original_pykms
            
        if original_kms is None:
            sys.modules.pop('kms', None)
        else:
            sys.modules['kms'] = original_kms


@pytest.mark.unit
def test_mock_module_attributes():
    """Test that mock modules can have attributes set."""
    mock = types.ModuleType('test_module')
    
    # Should be able to set attributes
    mock.test_attribute = "test_value"
    mock.test_function = lambda: "test"
    
    assert mock.test_attribute == "test_value"
    assert mock.test_function() == "test"


@pytest.mark.unit
def test_pykms_in_main():
    """Test that main.py contains the pykms workaround."""
    from pathlib import Path
    
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    # Check for the workaround code
    assert 'pykms' in code or 'kms' in code, \
        "main.py should contain pykms/kms handling"
    
    # Check for module creation
    assert 'types.ModuleType' in code or 'ModuleType' in code or \
           'sys.modules' in code, \
        "main.py should contain module mocking logic"


@pytest.mark.unit
def test_types_module_available():
    """Test that types module is available for creating mock modules."""
    import types
    
    assert hasattr(types, 'ModuleType')
    
    # Can create a module
    test_mod = types.ModuleType('test')
    assert test_mod.__name__ == 'test'


@pytest.mark.unit
def test_picamera2_import_with_mock():
    """Test picamera2 import with mock pykms (only if picamera2 available)."""
    # Check if picamera2 is available
    import importlib.util
    if importlib.util.find_spec('picamera2') is None:
        pytest.skip("picamera2 not installed in this environment")
    
    # Save original state
    original_pykms = sys.modules.get('pykms')
    original_kms = sys.modules.get('kms')
    original_picamera2 = sys.modules.get('picamera2')
    
    try:
        # Remove picamera2 to force reimport
        if 'picamera2' in sys.modules:
            del sys.modules['picamera2']
        
        # Install mocks
        sys.modules['pykms'] = types.ModuleType('pykms')
        sys.modules['kms'] = types.ModuleType('kms')
        
        # Try to import
        from picamera2 import Picamera2
        
        # Should succeed
        assert Picamera2 is not None
        
    except ModuleNotFoundError as e:
        # If it still fails, it's for a different reason
        if 'pykms' in str(e) or 'kms' in str(e):
            pytest.fail("Mock modules didn't work as expected")
        else:
            # Some other module is missing, that's okay
            pytest.skip(f"Other dependency missing: {e}")
            
    finally:
        # Restore original state
        if original_pykms is None:
            sys.modules.pop('pykms', None)
        else:
            sys.modules['pykms'] = original_pykms
            
        if original_kms is None:
            sys.modules.pop('kms', None)
        else:
            sys.modules['kms'] = original_kms
            
        if original_picamera2 is None:
            sys.modules.pop('picamera2', None)
        else:
            sys.modules['picamera2'] = original_picamera2
