import pytest
from squid_game_doll.SquidGame import SquidGame
from squid_game_doll.Player import Player
from squid_game_doll.GameSettings import GameSettings
import pygame
import os
import time
import numpy as np


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    pygame.init()
    yield
    pygame.quit()


def test_settings():
    settings = GameSettings()
    settings.areas = GameSettings.default_areas(1920, 1080)
    settings.params = GameSettings.default_params()
    settings.reference_frame = [1920, 1080]
    assert settings.save("config-test.yaml")
    settings = GameSettings.load_settings("config-test.yaml")
    assert settings is not None
    assert settings.areas is not None
    assert settings.params is not None
    assert settings.reference_frame is not None
    assert settings.get_reference_frame() == pygame.Rect(0, 0, 1920, 1080)
    assert type(settings.areas) == dict
    assert settings.areas.get("vision") is not None
    assert settings.areas.get("finish") is not None
    assert settings.areas.get("start") is not None
    assert settings.get_param("pixel_tolerance") is not None


def test_player_initialization():
    player = Player(1, (0, 0, 100, 100))
    assert player.get_id() == 1
    assert player.get_coords() == (0, 0, 100, 100)
    assert not player.is_eliminated()
    assert not player.is_visible()
    assert not player.is_winner()


def test_set_and_get_last_seen():
    player = Player(1, (0, 0, 100, 100))
    current_time = time.time()
    player.set_last_seen(current_time)
    assert player.get_last_seen() == current_time


def test_has_expired():
    player = Player(1, (0, 0, 100, 100))
    player.set_last_seen(time.time() - Player.MAX_AGE_SECONDS - 1)
    assert player.has_expired()

    player.set_last_seen(time.time())
    assert not player.has_expired()


def test_set_and_get_winner():
    player = Player(1, (0, 0, 100, 100))
    assert not player.is_winner()
    player.set_winner()
    assert player.is_winner()


def test_set_and_get_visibility():
    player = Player(1, (0, 0, 100, 100))
    assert not player.is_visible()
    player.set_visible(True)
    assert player.is_visible()


def test_set_and_get_eliminated():
    player = Player(1, (0, 0, 100, 100))
    assert not player.is_eliminated()
    player.set_eliminated(True)
    assert player.is_eliminated()


def test_set_and_get_last_position():
    player = Player(1, (0, 0, 100, 100))
    player.set_last_position((10, 10, 110, 110))
    assert player.get_last_position() == (10, 10, 110, 110)


def test_set_and_get_face():
    player = Player(1, (0, 0, 100, 100))
    face = np.zeros((100, 100, 3), dtype=np.uint8)
    player.set_face(face)
    assert np.array_equal(player.get_face(), face)


def test_set_and_get_coords():
    player = Player(1, (0, 0, 100, 100))
    player.set_coords((10, 10, 110, 110))
    assert player.get_coords() == (10, 10, 110, 110)


def test_has_moved():
    settings = GameSettings()
    settings.areas = GameSettings.default_areas(1920, 1080)
    settings.params = GameSettings.default_params()

    player = Player(1, (0, 0, 100, 100))
    player.set_last_position((0, 0, 100, 100))
    player.set_coords((20, 20, 120, 120))
    assert player.has_moved(settings)

    # Move by less than the threshold
    player.set_coords((0, 0, 101, 101))
    assert not player.has_moved(settings)


def test_get_rect():
    player = Player(1, (0, 0, 100, 100))
    assert player.get_rect() == (0, 0, 100, 100)


def test_get_last_rect():
    player = Player(1, (0, 0, 100, 100))
    player.set_last_position((10, 10, 110, 110))
    assert player.get_last_rect() == (10, 10, 100, 100)


def test_get_target():
    player = Player(1, (0, 0, 100, 100))
    assert player.get_target() == (50.0, 33.333333333333336)
