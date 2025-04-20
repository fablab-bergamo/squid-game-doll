from ConfigPhase import GameConfigPhase
from GameCamera import GameCamera
from GameScreen import GameScreen
from PlayerTrackerUL import PlayerTrackerUL
from GameSettings import GameSettings
import pygame


# Example usage:
if __name__ == "__main__":
    import ctypes, os

    ctypes.windll.user32.SetProcessDPIAware()

    # Disable hardware acceleration for webcam on Windows
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

    # Initialize pygame and set up display
    pygame.init()

    config_file = "config.yaml"

    size, monitor = GameScreen.get_desktop(-1)
    print("Running on monitor:", monitor, "size:", size)
    screen = pygame.display.set_mode(size)
    cam = GameCamera()
    nn = PlayerTrackerUL()
    game_settings = GameSettings.load_settings(config_file)
    if game_settings is None:
        game_settings = GameSettings()

    config_phase = GameConfigPhase(
        camera=cam, screen=screen, neural_net=nn, game_settings=game_settings, config_file=config_file
    )
    game_settings = config_phase.run()
    # Now areas and settings are available for further processing.
    print("Configuration completed.", game_settings)
    pygame.quit()
