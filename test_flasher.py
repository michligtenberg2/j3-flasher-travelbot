"""
Unit tests for J3 Flasher Travelbot

This module contains tests for the core functionality of the flasher application,
focusing on non-GUI functions that can be tested without hardware.
"""

import unittest
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Try to import the functions to test, skip GUI-related tests if PyQt6 not available
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Mock PyQt6 modules to avoid import errors in test environment
    sys.modules['PyQt6'] = MagicMock()
    sys.modules['PyQt6.QtWidgets'] = MagicMock()
    sys.modules['PyQt6.QtGui'] = MagicMock()
    sys.modules['PyQt6.QtCore'] = MagicMock()
    
    import flash
    FLASH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import flash module: {e}")
    FLASH_AVAILABLE = False


@unittest.skipUnless(FLASH_AVAILABLE, "Flash module not available")
class TestFlasherCore(unittest.TestCase):
    """Test core flasher functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "SM-J320FN": {
                "device": "j3lte",
                "recovery_url": "https://example.com/twrp.img",
                "rom_url": "https://example.com/lineage.zip",
                "magisk_url": "https://example.com/magisk.zip"
            }
        }

    def test_version_info(self):
        """Test that version information is properly defined."""
        self.assertTrue(hasattr(flash, '__version__'))
        self.assertTrue(hasattr(flash, '__author__'))
        self.assertTrue(hasattr(flash, '__description__'))
        self.assertIsInstance(flash.__version__, str)
        self.assertIsInstance(flash.__author__, str)
        self.assertIsInstance(flash.__description__, str)

    @patch('builtins.open', new_callable=mock_open, read_data='{}')
    @patch('pathlib.Path.exists')
    def test_load_profile_empty_config(self, mock_exists, mock_file):
        """Test loading profile from empty config file."""
        mock_exists.return_value = True
        result = flash.load_profile()
        self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('json.load')
    def test_load_profile_valid_config(self, mock_json_load, mock_exists, mock_file):
        """Test loading profile from valid config file."""
        mock_exists.return_value = True
        mock_json_load.return_value = self.test_config
        
        result = flash.load_profile()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['device'], 'j3lte')
        self.assertEqual(result['recovery_url'], 'https://example.com/twrp.img')

    @patch('pathlib.Path.exists')
    def test_load_profile_missing_config(self, mock_exists):
        """Test loading profile when config file doesn't exist."""
        mock_exists.return_value = False
        result = flash.load_profile()
        self.assertIsNone(result)

    def test_check_tool_existing(self):
        """Test check_tool with existing tool."""
        with patch('shutil.which', return_value='/usr/bin/adb'):
            result = flash.check_tool('adb')
            self.assertEqual(result, '/usr/bin/adb')

    def test_check_tool_missing(self):
        """Test check_tool with missing tool."""
        with patch('shutil.which', return_value=None):
            result = flash.check_tool('nonexistent')
            self.assertIsNone(result)

    @patch('subprocess.run')
    def test_adb_command(self, mock_subprocess):
        """Test ADB command execution."""
        mock_result = MagicMock()
        mock_result.stdout = 'List of devices attached\n'
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        with patch('flash.check_tool', return_value='/usr/bin/adb'):
            result = flash.adb_command(['devices'])
            self.assertEqual(result.stdout, 'List of devices attached\n')
            self.assertEqual(result.returncode, 0)

    @patch('flash.adb_command')
    def test_device_connected_true(self, mock_adb_command):
        """Test device_connected when device is connected."""
        mock_result = MagicMock()
        mock_result.stdout = 'List of devices attached\ndevice123\tdevice\n'
        mock_adb_command.return_value = mock_result
        
        result = flash.device_connected()
        self.assertTrue(result)

    @patch('flash.adb_command')
    def test_device_connected_false(self, mock_adb_command):
        """Test device_connected when no device is connected."""
        mock_result = MagicMock()
        mock_result.stdout = 'List of devices attached\n'
        mock_adb_command.return_value = mock_result
        
        result = flash.device_connected()
        self.assertFalse(result)

    def test_constants_defined(self):
        """Test that required constants are defined."""
        self.assertTrue(hasattr(flash, 'CONFIG_FILE'))
        self.assertTrue(hasattr(flash, 'LOG_FILE'))
        self.assertTrue(hasattr(flash, 'ROOT_LOG_FILE'))
        self.assertTrue(hasattr(flash, 'TWRP_URL'))
        self.assertTrue(hasattr(flash, 'IS_WINDOWS'))
        self.assertTrue(hasattr(flash, 'ADB_NAME'))
        self.assertTrue(hasattr(flash, 'HEIMDALL_NAME'))

    def test_log_levels_usage(self):
        """Test that logging levels are used appropriately."""
        # This test ensures the logging setup is called
        with patch('flash.logging.handlers.RotatingFileHandler') as mock_handler:
            with patch('flash.logging.getLogger') as mock_logger:
                flash.setup_logging()
                mock_handler.assert_called_once()
                mock_logger.assert_called_once()


@unittest.skipUnless(FLASH_AVAILABLE, "Flash module not available")
class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_log_function_exists(self):
        """Test that log function is defined and callable."""
        self.assertTrue(callable(flash.log))
        self.assertTrue(callable(flash.root_log))

    def test_setup_logging_function(self):
        """Test that setup_logging function is defined."""
        self.assertTrue(callable(flash.setup_logging))


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality that doesn't require the flash module."""

    def test_basic_python_functionality(self):
        """Test that basic Python functionality works."""
        # Test basic imports
        import json
        import os
        import sys
        from pathlib import Path
        
        # Test basic operations
        self.assertTrue(True)
        self.assertEqual(1 + 1, 2)
        
        # Test Path operations
        test_path = Path('/tmp/test')
        self.assertIsInstance(test_path, Path)


if __name__ == '__main__':
    # Run the tests
    if not FLASH_AVAILABLE:
        print("Warning: Flash module not available, running limited tests")
    unittest.main(verbosity=2)