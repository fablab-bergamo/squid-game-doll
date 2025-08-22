import platform
import os
import argparse
import pygame
import sys
from loguru import logger
from .GameCamera import GameCamera
from .GameScreen import GameScreen
from .GameSettings import GameSettings
from .SquidGame import SquidGame
from .ConfigPhase import GameConfigPhase


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

    cam = GameCamera(args.webcam)

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
        screen = pygame.display.set_mode(size)
        
        # Detect hardware platform - only use Hailo on Raspberry Pi
        is_raspberry_pi = False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
                is_raspberry_pi = 'raspberry' in cpuinfo or 'bcm' in cpuinfo
        except:
            pass
        
        # Use the same robust tracker loading as in SquidGame
        nn = None
        if platform.system() == "Linux" and is_raspberry_pi:
            try:
                from .PlayerTrackerHailo import PlayerTrackerHailo
                logger.info(f"Loading HAILO model for Raspberry Pi ({args.model})...")
                if args.model != "":
                    nn = PlayerTrackerHailo(args.model)
                else:
                    nn = PlayerTrackerHailo()
                logger.info("Successfully loaded Hailo tracker for setup")
            except (ImportError, ModuleNotFoundError) as e:
                logger.warning(f"Hailo not available ({e}), falling back to Ultralytics for setup")
                try:
                    from .PlayerTrackerUL import PlayerTrackerUL
                    logger.info(f"Loading Ultralytics model ({args.model})...")
                    if args.model != "":
                        nn = PlayerTrackerUL(args.model)
                    else:
                        nn = PlayerTrackerUL()
                    logger.info("Successfully loaded Ultralytics tracker for setup")
                except Exception as e2:
                    logger.error(f"Failed to load any tracker for setup: {e2}")
                    return
        else:
            # Use Ultralytics for Jetson, Windows, macOS, and other Linux systems
            try:
                from .PlayerTrackerUL import PlayerTrackerUL
                logger.info(f"Loading Ultralytics model ({args.model})...")
                if args.model != "":
                    nn = PlayerTrackerUL(args.model)
                else:
                    nn = PlayerTrackerUL()
                logger.info("Successfully loaded Ultralytics tracker for setup")
            except Exception as e:
                logger.error(f"Failed to load Ultralytics tracker for setup: {e}")
                return
        
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
