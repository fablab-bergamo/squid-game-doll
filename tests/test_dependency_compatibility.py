"""Exercise the image and face-detection APIs used by the game with real libraries."""

from types import SimpleNamespace
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from squid_game_doll.constants import PLAYER_SIZE
from squid_game_doll.face_extractor import FaceExtractor
from squid_game_doll.game_screen import GameScreen


@pytest.mark.parametrize("extension", ["png", "jpg"])
def test_player_image_loading(tmp_path, extension):
    path = tmp_path / f"player.{extension}"
    Image.new("RGB", (40, 60), (200, 50, 20)).save(path)

    # This method needs no display, fonts, or initialized GameScreen.
    surface = GameScreen.load_player_image(None, str(path))

    assert surface.get_size() == (PLAYER_SIZE, PLAYER_SIZE)
    pixel = surface.get_at((PLAYER_SIZE // 2, PLAYER_SIZE // 2))
    assert tuple(pixel[:3]) == pytest.approx((200, 50, 20), abs=2)
    assert pixel.a == 255


@pytest.fixture
def face_extractor():
    extractor = FaceExtractor()
    yield extractor
    extractor.face_detector.close()


def test_mediapipe_bundled_model(face_extractor):
    """Load the bundled TFLite model and run the actual Tasks API offline."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    assert face_extractor.extract_face(frame, (0, 0, 100, 100), 1, True) == (None, None)


def test_mediapipe_face_coordinates_and_cache(face_extractor, monkeypatch):
    frame = np.full((100, 120, 3), (10, 20, 30), dtype=np.uint8)
    detection = SimpleNamespace(
        bounding_box=SimpleNamespace(origin_x=10, origin_y=15, width=20, height=25)
    )
    monkeypatch.setattr(
        face_extractor.face_detector, "detect",
        lambda image: SimpleNamespace(detections=[detection]),
    )
    face, bbox = face_extractor.extract_face(frame, (20, 10, 100, 90), 1, True)
    assert bbox == (30, 25, 20, 25)
    assert face.shape == (PLAYER_SIZE, PLAYER_SIZE, 3)
    np.testing.assert_array_equal(face[0, 0], (10, 20, 30))

    monkeypatch.setattr(
        face_extractor.face_detector, "detect",
        lambda image: SimpleNamespace(detections=[]),
    )
    cached, bbox = face_extractor.extract_face(frame, (20, 10, 100, 90), 1, True)
    np.testing.assert_array_equal(cached, face)
    assert bbox is None
    face_extractor.reset_memory()
    assert face_extractor.extract_face(frame, (20, 10, 100, 90), 1, True) == (None, None)


def test_cuda_player_tracking():
    """Exercise the real game pipeline when local weights and a CUDA GPU exist."""
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA GPU unavailable")
    model_path = Path("yolov8s.pt")
    image_path = Path("pictures/screenshot_init.png")
    if not model_path.is_file() or not image_path.is_file():
        pytest.skip("Local player model or screenshot unavailable")

    import cv2
    from squid_game_doll.game_settings import GameSettings
    from squid_game_doll.player_tracker_ul import PlayerTrackerUL

    settings = GameSettings()
    settings.params = GameSettings.default_params()
    tracker = PlayerTrackerUL(str(model_path))
    assert next(tracker.yolo.model.parameters()).device.type == "cuda"
    frame = cv2.imread(str(image_path))
    assert frame is not None
    players = tracker.process_nn_frame(frame, settings)
    assert tracker.fps > 0, "Inference returned cached results after an error"
    assert players, "Expected a player in the registration screenshot"
    assert all(player.get_id() is not None for player in players)
