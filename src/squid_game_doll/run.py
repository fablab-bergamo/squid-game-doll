import platform
import os
import argparse
import warnings
import sys

# Suppress NumPy subnormal value warnings that occur on some systems during initialization
warnings.filterwarnings("ignore", message="The value of the smallest subnormal.*is zero", category=UserWarning)

import pygame
from loguru import logger
from .game_camera import GameCamera
from .game_screen import GameScreen
from .game_settings import GameSettings
from .squid_game import SquidGame
from .config_phase import GameConfigPhase
from .utils.platform import (
    should_use_hailo,
    get_platform_info
)


def load_neural_network(model: str):
    """Load neural network using the same logic as SquidGame.load_model()"""
    import os
    from .utils.platform import get_optimal_model_for_platform
    
    # Use platform utilities for hardware detection
    platform_info = get_platform_info()
    tracker = None
    
    # Determine the actual model that will be used for better logging
    actual_model = model if model != "" else get_optimal_model_for_platform()
    model_name = os.path.splitext(os.path.basename(actual_model))[0]  # Extract model name (e.g., "yolo11n")
    
    # Only try Hailo on Raspberry Pi, use Ultralytics elsewhere
    if should_use_hailo():
        try:
            from .player_tracker_hailo import PlayerTrackerHailo
            logger.info(f"🤖 Loading HAILO model '{model_name}' ({platform_info})")
            if model != "":
                tracker = PlayerTrackerHailo(model)
            else:
                tracker = PlayerTrackerHailo()
            logger.info(f"✅ Successfully loaded HAILO tracker with model '{model_name}'")
        except (ImportError, ModuleNotFoundError) as import_error:
            logger.warning(f"⚠️  HAILO dependencies not available ({import_error}), falling back to Ultralytics")
            try:
                from .player_tracker_ul import PlayerTrackerUL
                logger.info(f"🤖 Loading Ultralytics model '{model_name}' ({platform_info})")
                if model != "":
                    tracker = PlayerTrackerUL(model)
                else:
                    tracker = PlayerTrackerUL()
                logger.info(f"✅ Successfully loaded Ultralytics tracker with model '{model_name}'")
            except Exception as ul_error:
                logger.error(f"❌ Failed to load Ultralytics tracker: {ul_error}")
                tracker = None
        except Exception as hailo_error:
            logger.error(f"❌ Failed to initialize HAILO tracker: {hailo_error}")
            try:
                from .player_tracker_ul import PlayerTrackerUL
                logger.info(f"🤖 Attempting Ultralytics fallback with model '{model_name}' ({platform_info})")
                if model != "":
                    tracker = PlayerTrackerUL(model)
                else:
                    tracker = PlayerTrackerUL()
                logger.info(f"✅ Successfully loaded Ultralytics tracker with model '{model_name}'")
            except Exception as ul_error:
                logger.error(f"❌ Failed to load Ultralytics tracker: {ul_error}")
                tracker = None
    else:
        # Use Ultralytics for Jetson, Windows, macOS, and other Linux systems
        try:
            from .player_tracker_ul import PlayerTrackerUL
            logger.info(f"🤖 Loading Ultralytics model '{model_name}' ({platform_info})")
            if model != "":
                tracker = PlayerTrackerUL(model)
            else:
                tracker = PlayerTrackerUL()
            logger.info(f"✅ Successfully loaded Ultralytics tracker with model '{model_name}'")
        except Exception as e:
            logger.error(f"❌ Failed to load Ultralytics tracker: {e}")
            tracker = None

    return tracker


def command_line_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("run.py")
    parser.add_argument(
        "-m", "--monitor", help="0-based index of the monitor", dest="monitor", type=int, default=-1, required=False
    )
    parser.add_argument(
        "-w", "--webcam", help="0-based index of the webcam", dest="webcam", type=int, default=-1, required=False
    )
    parser.add_argument(
        "-k",
        "--killer",
        help="enable or disable the esp32 laser shooter",
        dest="tracker",
        action="store_true",
        default=False,
        required=False,
    )
    parser.add_argument(
        "-i",
        "--tracker-ip",
        help="sets the esp32 tracker IP address",
        dest="ip",
        type=str,
        default="192.168.45.50",
        required=False,
    )
    parser.add_argument(
        "-j",
        "--joystick",
        help="sets the joystick index",
        dest="joystick",
        type=int,
        default=-1,
        required=False,
    )
    parser.add_argument(
        "-n",
        "--neural_net",
        help="specify neural network model file for player recognition",
        dest="model",
        type=str,
        default="",
        required=False,
    )

    parser.add_argument(
        "-c",
        "--config",
        help="specify config file (defaults to config.yaml)",
        dest="config",
        type=str,
        default="config.yaml",
        required=False,
    )

    parser.add_argument(
        "-s",
        "--setup",
        help="go to setup mode",
        dest="setup",
        action="store_true",
        default=False,
        required=False,
    )
    parser.add_argument(
        "-f",
        "--fixed-image",
        help="fixed image for testing",
        dest="fixed_image",
        type=str,
        default="",
        required=False,
    )
    return parser.parse_args()


def run():
    logger.add("squidgame.log", rotation="1 MB", retention="7 days", level="DEBUG")
    if platform.system() == "Windows":
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
        # Disable hardware acceleration for webcam on Windows
        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
        os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    elif platform.system() != "Linux":
        # For non-Linux, non-Windows systems (like macOS), only set OpenCV environment variables
        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
        os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

    args = command_line_args()

    pygame.init()
    size, monitor = GameScreen.get_desktop(args.monitor)
    logger.info(f"Running on monitor {monitor}, size {size}")
    joystick: pygame.joystick.Joystick = None
    if args.joystick != -1:
        joystick = pygame.joystick.Joystick(args.joystick)
        logger.info(f"Using joystick: {joystick.get_name()}")
    else:
        logger.debug("Available Joysticks:")
        for idx in range(0, pygame.joystick.get_count()):
            logger.debug(f"\t{idx}:{pygame.joystick.Joystick(idx).get_name()}")

    cam = GameCamera(args.webcam, args.fixed_image)

    if not cam.valid:
        logger.error("No compatible webcam found")
        exit(1)

    if args.model != "" and not os.path.exists(args.model):
        logger.error("Invalid model file")
        exit(1)

    settings = GameSettings.load_settings(args.config)
    if settings is None:
        settings = GameSettings()
        frame_size = cam.get_native_resolution(cam.index)
        settings.params = GameSettings.default_params()
        settings.areas = GameSettings.default_areas(frame_size[0], frame_size[1])
        settings.save(args.config)
        logger.info("Default settings created")

    if args.setup:
        # Set SDL hint to center window and raise it
        os.environ["SDL_VIDEO_WINDOW_POS"] = "centered"
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        
        # Create window 
        screen = pygame.display.set_mode(size)
        
        # Use the EXACT same neural network loading logic as game mode
        nn = load_neural_network(args.model)
        
        if nn is None:
            logger.error("No tracker could be loaded for setup mode")
            return

        config_phase = GameConfigPhase(
            camera=cam, screen=screen, neural_net=nn, game_settings=settings, config_file=args.config
        )

        config_phase.run()

        logger.info("Configuration completed! Re-run the game to apply the new settings.")
        pygame.quit()
        sys.exit()

    else:
        game = SquidGame(
            disable_tracker=not args.tracker,
            desktop_size=size,
            display_idx=monitor,
            ip=args.ip,
            joystick=joystick,
            cam=cam,
            model=args.model,
            settings=settings,
        )

        while True:
            try:
                game.start_game()
            except Exception as e:
                logger.exception("run")
                pygame.quit()
                raise e


if __name__ == "__main__":
    run()
