import pytest
import cv2
import numpy as np
import os
import pygame
from unittest.mock import patch, MagicMock

from squid_game_doll.laser_finder_nn import LaserFinderNN


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def sample_image():
    """Create a sample image for testing"""
    return np.zeros((300, 400, 3), dtype=np.uint8)


@pytest.fixture
def without_model_loading(monkeypatch):
    monkeypatch.setattr(LaserFinderNN, "_load_optimized_model", lambda self: False)


def test_initialization(without_model_loading):
    """Test LaserFinderNN initialization"""
    finder = LaserFinderNN()
    assert finder.base_model_path == "yolov5l6_e200_b8_tvt302010_laser_v5.pt"
    assert not finder.laser_found()
    assert finder.get_laser_coord() is None


def test_custom_model_path(without_model_loading):
    """Test initialization with custom model path"""
    finder = LaserFinderNN("custom.pt")
    assert finder.base_model_path == "custom.pt"


def test_thresholds(without_model_loading):
    """Test setting confidence and IoU thresholds"""
    finder = LaserFinderNN()
    finder.set_confidence_threshold(0.25)
    finder.set_iou_threshold(0.5)
    assert finder.confidence_threshold == 0.25
    assert finder.iou_threshold == 0.5


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_model_loading_device_and_trust(tmp_path, monkeypatch, device):
    import torch
    from squid_game_doll.laser_finder_nn import YOLOV5_HUB_REPO

    model_path = tmp_path / "laser.pt"
    model_path.touch()
    model = MagicMock()
    model.names = {0: "laser"}
    monkeypatch.setattr(torch.cuda, "is_available", lambda: device == "cuda")
    monkeypatch.setattr("squid_game_doll.laser_finder_nn.is_jetson_orin", lambda: False)
    with patch.object(torch.hub, "load", return_value=model) as load:
        finder = LaserFinderNN(str(model_path))

    load.assert_called_once_with(
        YOLOV5_HUB_REPO, "custom", path=str(model_path),
        device="0" if device == "cuda" else "cpu", trust_repo=True
    )
    assert finder.model is model
    model.eval.assert_called_once()
    assert model.conf == finder.confidence_threshold
    assert model.iou == finder.iou_threshold


def test_real_model_detection():
    """Test laser detection with real model and image"""
    from pathlib import Path
    
    # Check if model and test image exist
    model_path = "yolov5l6_e200_b8_tvt302010_laser_v5.pt"
    test_image_path = Path("pictures/laser-1.jpg")
    
    if not Path(model_path).exists():
        pytest.skip(f"Model file {model_path} not found - run setup.sh first")
    
    if not test_image_path.exists():
        pytest.skip(f"Test image {test_image_path} not found")
    
    finder = LaserFinderNN(model_path)
    assert finder.model is not None, "Failed to load laser model"

    test_image = cv2.imread(str(test_image_path))
    assert test_image is not None, "Failed to load test image"

    coord, output = finder.find_laser(test_image)

    assert finder.laser_found(), "Should detect laser in test image"
    assert coord is not None, "Should return laser coordinates"
    assert isinstance(coord, tuple) and len(coord) == 2, "Coordinates should be (x, y) tuple"
    assert len(finder.get_all_detections()) >= 1, "Should have at least one detection"
