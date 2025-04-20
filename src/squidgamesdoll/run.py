import platform
import os
import argparse
import pygame
from GameCamera import GameCamera
from GameScreen import GameScreen
from GameSettings import GameSettings
from SquidGame import SquidGame


def command_line_args() -> any:
    import argparse

    parser = argparse.ArgumentParser("SquidGame.py")
    parser.add_argument(
        "-m", "--monitor", help="0-based index of the monitor", dest="monitor", type=int, default=-1, required=False
    )
    parser.add_argument(
        "-w", "--webcam", help="0-based index of the webcam", dest="webcam", type=int, default=-1, required=False
    )
    parser.add_argument(
        "-t",
        "--tracker",
        help="enable or disable the esp32 laser",
        dest="tracker",
        type=bool,
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
        help="specify neural network model for player recognition",
        dest="model",
        type=str,
        default="",
        required=False,
    )

    parser.add_argument(
        "-c",
        "--config",
        help="specify cpnfig file",
        dest="config",
        type=str,
        default="config.yaml",
        required=False,
    )
    return parser.parse_args()


def run():
    if platform.system() != "Linux":
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
        # Disable hardware acceleration for webcam on Windows
        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

    pygame.init()

    args = command_line_args()
    size, monitor = GameScreen.get_desktop(args.monitor)
    joystick: pygame.joystick.Joystick = None
    if args.joystick != -1:
        joystick = pygame.joystick.Joystick(args.joystick)
        print(f"Using joystick: {joystick.get_name()}")
    else:
        print("Joysticks:")
        for idx in range(0, pygame.joystick.get_count()):
            print(f"\t{idx}:{pygame.joystick.Joystick(idx).get_name()}")
        print("-")

    cam = GameCamera(args.webcam)

    if not cam.valid:
        print("No compatible webcam found")
        exit(1)

    if args.model != "" and not os.path.exists(args.model):
        print("Invalid model file")
        exit(1)

    settings = GameSettings.load_settings(args.config)
    if settings is None:
        settings = GameSettings()
        frame_size = cam.get_frame_size()
        settings.settings = GameSettings.default_params()
        settings.areas = GameSettings.default_areas(frame_size[0], frame_size[1])
        settings.save(args.config)
        print("Default settings created")

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
            print("Exception", e)
            raise e


if __name__ == "__main__":
    run()
