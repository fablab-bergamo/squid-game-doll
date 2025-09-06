"""
Test laser system class loading and basic functionality after code quality improvements.

This test ensures all laser system classes can be imported and instantiated properly
without requiring external dependencies like ESP32 connections or model files.
"""

import pytest
import os
import pygame
import numpy as np
from unittest.mock import patch, MagicMock

from squid_game_doll.laser_coordinate_filter import LaserCoordinateFilter
from squid_game_doll.laser_finder import LaserFinder  
from squid_game_doll.laser_finder_nn import LaserFinderNN
from squid_game_doll.laser_shooter import LaserShooter
from squid_game_doll.laser_tracker import LaserTracker


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize pygame for tests that need it."""
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    pygame.init()
    yield
    pygame.quit()


class TestLaserCoordinateFilter:
    """Test LaserCoordinateFilter class loading and functionality."""
    
    def test_import_and_instantiation(self):
        """Test that LaserCoordinateFilter can be imported and instantiated."""
        filter_obj = LaserCoordinateFilter()
        assert filter_obj is not None
        assert not filter_obj.has_detection()
    
    def test_constants_accessible(self):
        """Test that configuration constants are accessible."""
        from squid_game_doll.laser_coordinate_filter import (
            DEFAULT_SMOOTHING_FACTOR, DEFAULT_MAX_HISTORY_SIZE,
            DEFAULT_OUTLIER_THRESHOLD, DEFAULT_MIN_CONFIDENCE,
            DEFAULT_MAX_CONSECUTIVE_OUTLIERS, DEFAULT_MEMORY_TIMEOUT_SECONDS,
            DEFAULT_MAX_NO_DETECTION_FRAMES, RECOVERY_MODE_ALPHA
        )
        
        # Test that constants have reasonable values
        assert 0.0 <= DEFAULT_SMOOTHING_FACTOR <= 1.0
        assert DEFAULT_MAX_HISTORY_SIZE > 0
        assert DEFAULT_OUTLIER_THRESHOLD > 0
        assert 0.0 <= DEFAULT_MIN_CONFIDENCE <= 1.0
        assert DEFAULT_MAX_CONSECUTIVE_OUTLIERS > 0
        assert DEFAULT_MEMORY_TIMEOUT_SECONDS > 0
        assert DEFAULT_MAX_NO_DETECTION_FRAMES > 0
        assert 0.0 < RECOVERY_MODE_ALPHA <= 1.0
    
    def test_basic_functionality(self):
        """Test basic filter functionality."""
        filter_obj = LaserCoordinateFilter()
        
        # Test update with coordinate
        filter_obj.update((100, 200), confidence=0.8)
        assert filter_obj.has_detection()
        
        # Test get coordinates
        raw_coord = filter_obj.get_raw_coordinate()
        smoothed_coord = filter_obj.get_smoothed_coordinate()
        assert raw_coord == (100, 200)
        assert smoothed_coord is not None
        
        # Test configuration methods
        filter_obj.set_smoothing_factor(0.5)
        filter_obj.set_outlier_threshold(100.0)
        filter_obj.set_recovery_params(10)
        filter_obj.set_memory_params(5.0, 50)


class TestLaserFinder:
    """Test LaserFinder class loading and functionality."""
    
    def test_import_and_instantiation(self):
        """Test that LaserFinder can be imported and instantiated."""
        finder = LaserFinder()
        assert finder is not None
        assert not finder.laser_found()
    
    def test_basic_methods(self):
        """Test that basic methods are accessible."""
        finder = LaserFinder()
        
        # Create dummy image
        dummy_img = np.zeros((300, 400, 3), dtype=np.uint8)
        
        # Test find_laser method with required rects parameter (may not find anything in dummy image)
        result = finder.find_laser(dummy_img, rects=[])
        assert isinstance(result, tuple)
        assert len(result) == 2  # (coordinate, output_image)


class TestLaserFinderNN:
    """Test LaserFinderNN class loading and functionality."""
    
    def test_import_and_instantiation(self):
        """Test that LaserFinderNN can be imported and instantiated."""
        finder = LaserFinderNN("dummy_model.pt")
        assert finder is not None
        assert not finder.laser_found()
    
    def test_constants_accessible(self):
        """Test that configuration constants are accessible."""
        from squid_game_doll.laser_finder_nn import (
            DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_IOU_THRESHOLD,
            DEFAULT_NN_SMOOTHING_FACTOR, DEFAULT_NN_MAX_HISTORY_SIZE,
            DEFAULT_NN_OUTLIER_THRESHOLD, DEFAULT_NN_MIN_CONFIDENCE,
            PERFORMANCE_LOG_INTERVAL_FRAMES
        )
        
        # Test that constants have reasonable values
        assert 0.0 <= DEFAULT_CONFIDENCE_THRESHOLD <= 1.0
        assert 0.0 <= DEFAULT_IOU_THRESHOLD <= 1.0
        assert 0.0 <= DEFAULT_NN_SMOOTHING_FACTOR <= 1.0
        assert DEFAULT_NN_MAX_HISTORY_SIZE > 0
        assert DEFAULT_NN_OUTLIER_THRESHOLD > 0
        assert 0.0 <= DEFAULT_NN_MIN_CONFIDENCE <= 1.0
        assert PERFORMANCE_LOG_INTERVAL_FRAMES > 0
    
    def test_configuration_methods(self):
        """Test configuration methods."""
        finder = LaserFinderNN("dummy_model.pt")
        
        # Test threshold setting (should work even without model)
        finder.set_confidence_threshold(0.5)
        finder.set_iou_threshold(0.3)
        assert finder.confidence_threshold == 0.5
        assert finder.iou_threshold == 0.3
        
        # Test coordinate methods
        assert finder.get_raw_coord() is None
        assert finder.get_smoothed_coord() is None
        assert finder.get_winning_strategy() == ""


class TestLaserShooter:
    """Test LaserShooter class loading and functionality."""
    
    @patch('squid_game_doll.laser_shooter.LaserShooter.get_limits')
    @patch('squid_game_doll.laser_shooter.LaserShooter.init_PID')
    def test_import_and_instantiation(self, mock_init_pid, mock_get_limits):
        """Test that LaserShooter can be imported and instantiated without ESP32."""
        # Mock the methods that try to connect to ESP32
        mock_get_limits.return_value = None  # Return None for limits (no connection)
        mock_init_pid.return_value = False   # Return False for PID init failure
        
        shooter = LaserShooter("192.168.1.100", enable_laser=False)
        assert shooter is not None
        assert not shooter.is_laser_enabled()
        
        # Verify mocks were called
        mock_get_limits.assert_called_once()
        mock_init_pid.assert_called_once()
    
    def test_constants_accessible(self):
        """Test that configuration constants are accessible."""
        from squid_game_doll.laser_shooter import (
            DEFAULT_ESP32_PORT, DEFAULT_DEADBAND_PX, DEFAULT_MAX_FREQUENCY_HZ,
            DEFAULT_PX_PER_DEGREE_H, DEFAULT_PX_PER_DEGREE_V, DEFAULT_PID_KP,
            PID_KI_FACTOR, PID_KD_FACTOR, MIN_STEP_SIZE, MAX_STEP_SIZE,
            RATE_LIMIT_MAX_CHANGE, SOCKET_RECV_BUFFER_SIZE, MAX_CONNECTION_ATTEMPTS
        )
        
        # Test that constants have reasonable values
        assert DEFAULT_ESP32_PORT > 0
        assert DEFAULT_DEADBAND_PX >= 0
        assert DEFAULT_MAX_FREQUENCY_HZ > 0
        assert DEFAULT_PX_PER_DEGREE_H > 0
        assert DEFAULT_PX_PER_DEGREE_V > 0
        assert DEFAULT_PID_KP > 0
        assert PID_KI_FACTOR > 0
        assert PID_KD_FACTOR > 0
        assert MIN_STEP_SIZE > 0
        assert MAX_STEP_SIZE > MIN_STEP_SIZE
        assert RATE_LIMIT_MAX_CHANGE > 0
        assert SOCKET_RECV_BUFFER_SIZE > 0
        assert MAX_CONNECTION_ATTEMPTS > 0
    
    @patch('squid_game_doll.laser_shooter.LaserShooter.get_limits')
    @patch('squid_game_doll.laser_shooter.LaserShooter.init_PID')
    def test_configuration_methods(self, mock_init_pid, mock_get_limits):
        """Test configuration methods."""
        # Mock the methods that try to connect to ESP32
        mock_get_limits.return_value = None
        mock_init_pid.return_value = False
        
        shooter = LaserShooter("192.168.1.100", enable_laser=False)
        
        # Test coefficient setting
        shooter.set_coeffs((60.0, 20.0))
        assert shooter.coeffs == (60.0, 20.0)


class TestLaserTracker:
    """Test LaserTracker class loading and functionality."""
    
    @patch('squid_game_doll.laser_shooter.LaserShooter.get_limits')
    @patch('squid_game_doll.laser_shooter.LaserShooter.init_PID')
    def test_import_and_instantiation(self, mock_init_pid, mock_get_limits):
        """Test that LaserTracker can be imported and instantiated."""
        # Mock ESP32 connection methods
        mock_get_limits.return_value = None
        mock_init_pid.return_value = False
        
        shooter = LaserShooter("192.168.1.100", enable_laser=False)
        tracker = LaserTracker(shooter)
        
        assert tracker is not None
        assert tracker.target == (0, 0)
    
    @patch('squid_game_doll.laser_shooter.LaserShooter.get_limits')
    @patch('squid_game_doll.laser_shooter.LaserShooter.init_PID')
    def test_basic_methods(self, mock_init_pid, mock_get_limits):
        """Test basic tracker methods."""
        # Mock ESP32 connection methods
        mock_get_limits.return_value = None
        mock_init_pid.return_value = False
        
        shooter = LaserShooter("192.168.1.100", enable_laser=False)
        tracker = LaserTracker(shooter)
        
        # Test target setting
        tracker.set_target((100, 200))
        assert tracker.target == (100, 200)
        
        # Test shot completion check
        assert tracker.shot_complete() == False


class TestTypeCompatibility:
    """Test that type hints work with current Python version."""
    
    def test_tuple_typing_imports(self):
        """Test that Tuple imports work correctly."""
        # These should not raise import errors
        from squid_game_doll.laser_coordinate_filter import LaserCoordinateFilter
        from squid_game_doll.laser_shooter import LaserShooter
        from squid_game_doll.laser_tracker import LaserTracker
        from squid_game_doll.laser_finder import LaserFinder
        from squid_game_doll.laser_finder_nn import LaserFinderNN
        
        # If we get here without ImportError, typing is compatible
        assert True


class TestDocumentation:
    """Test that key methods have proper documentation."""
    
    def test_class_docstrings(self):
        """Test that classes have docstrings."""
        assert LaserCoordinateFilter.__doc__ is not None
        assert LaserFinder.__doc__ is not None
        assert LaserFinderNN.__doc__ is not None
        assert LaserShooter.__doc__ is not None
        assert LaserTracker.__doc__ is not None
    
    def test_method_docstrings(self):
        """Test that key methods have docstrings."""
        # LaserCoordinateFilter methods
        assert LaserCoordinateFilter.update.__doc__ is not None
        assert LaserCoordinateFilter.set_outlier_threshold.__doc__ is not None
        
        # LaserFinderNN methods
        assert LaserFinderNN.get_winning_strategy.__doc__ is not None
        assert LaserFinderNN.set_confidence_threshold.__doc__ is not None
        
        # LaserShooter methods  
        assert LaserShooter.is_laser_enabled.__doc__ is not None
        assert LaserShooter.set_coeffs.__doc__ is not None