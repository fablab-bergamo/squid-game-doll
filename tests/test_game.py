import pytest
from squid_game_doll.SquidGame import SquidGame
from squid_game_doll.Player import Player
from squid_game_doll.GameSettings import GameSettings
import pygame


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()


def test_settings():
    settings = GameSettings()
    settings.areas = GameSettings.default_areas(1920, 1080)
    settings.params = GameSettings.default_params()
    assert settings.save("config-test.yaml")
    settings = GameSettings.load_settings("config-test.yaml")
    assert settings is not None
