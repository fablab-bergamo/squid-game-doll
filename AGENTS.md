# Repository guidance

This file applies to all coding agents working in this repository.

## Working agreements

- Do not commit, push, or publish unless the user requests it.
- Preserve unrelated user changes and keep changes focused on the task.
- Update matching English and Italian documentation together when a translated
  counterpart exists. This shared contributor guide is maintained in English.
- Keep machine-specific configuration, credentials, downloaded model weights,
  generated TensorRT/ONNX models, and profiling output out of Git.
- Treat `pyproject.toml` and the tracked `poetry.lock` as the dependency sources of
  truth. Update them together and retain security version floors.

## Setup

Python 3.11 or newer is required. CI uses Python 3.11 and Poetry 2.5.1.

```bash
python -m pip install poetry==2.5.1
poetry env use python3.11
poetry check --lock
poetry sync --extras standard
```

The `standard` extra installs PyTorch, torchvision, and Ultralytics. Development
dependencies are installed by default. Avoid additional unpinned `pip install`
commands that bypass the lockfile. For a custom CUDA or embedded deployment,
match binary builds to the Python version, GPU architecture and vendor runtime.
The old `cp310` Jetson wheel examples and `setup_jetson.sh` are legacy instructions
and are incompatible with the current Python minimum. Do not delete the lockfile
or blindly run that setup script.

On Windows, WSL can reuse a Linux virtual environment. A Linux `.venv` cannot run
under native Windows Python; create or select an environment for the active OS.
Keep the selected interpreter consistent across installation and validation.

## Run and inspect

```bash
poetry run python -m squid_game_doll --help
poetry run python -m squid_game_doll --setup
poetry run python -m squid_game_doll
poetry run python -m squid_game_doll -f pictures/laser-1.jpg
```

The console command `poetry run squid-game-doll` uses the same entry point.
`--help` is the source of truth for CLI options. Setup creates `config.yaml` with
camera and gameplay areas. Running the game normally needs a display and camera;
ESP32 and laser control are optional (`-k` and `--tracker-ip`).

## Validation

```bash
poetry check --lock
poetry run python -m pip check
poetry run python -m compileall -q src tests esp32 optimize_for_jetson.py run_laser_finder_nn_batch.py
poetry build
poetry run pytest
```

For headless Linux or WSL testing, set `SDL_VIDEODRIVER=dummy` and
`SDL_AUDIODRIVER=dummy` before running pytest. Set `CUDA_VISIBLE_DEVICES=` to
exercise the CPU fallback. Pytest collects `tests/`; root-level and `drafts/`
scripts are manual experiments, not the automated suite.

Tests cover settings, player state and motion, laser components, Pillow image
loading, and the real MediaPipe Tasks face detector using its bundled model.
The real laser test needs `yolov5l6_e200_b8_tvt302010_laser_v5.pt` and
`pictures/laser-1.jpg`. CUDA player tracking additionally needs a GPU,
`yolov8s.pt`, and `pictures/screenshot_init.png`. Those integration tests skip
when prerequisites are absent; model loading or assertion failures must fail.
Do not turn failures into skips or let unit tests download models implicitly.

For dependency changes, audit the resolved environment with `pip-audit`, including
development dependencies. Install audit tooling outside the application
environment and export it with `poetry run python -m pip freeze --exclude-editable`.
Also test the built wheel (`pip install --no-deps --force-reinstall dist/*.whl`
inside the validation environment), including bundled media and model assets.
Report test skips and distinguish inference checks from physical camera, ESP32,
Jetson, or Hailo testing. Python compilation does not validate MicroPython hardware.

Use Black and Flake8 on the files being changed when relevant; avoid unrelated
repository-wide formatting. Profile with
`poetry run python -m cProfile -o game.prof -m squid_game_doll` and inspect with
`poetry run snakeviz game.prof`.

## Code map

- `src/squid_game_doll/run.py` and `__main__.py`: CLI and application startup.
- `squid_game.py`: game state transitions and orchestration.
- `game_screen.py`, `display.py`, `victory_animation.py`: Pygame UI and animation.
- `game_camera.py`, `game_settings.py`, `config_phase.py`: camera, saved settings,
  and interactive area configuration.
- `player.py`, `base_player_tracker.py`, `player_tracker_ul.py`,
  `player_tracker_hailo.py`: player state and detection/tracking backends.
- `face_extractor.py`: MediaPipe Tasks `FaceDetector`, using the bundled
  `media/blaze_face_short_range.tflite`; it does not use Haar cascades or
  the removed `mp.solutions` API.
- `laser_finder.py`, `laser_finder_nn.py`, `laser_coordinate_filter.py`,
  `laser_tracker.py`, `laser_shooter.py`: image-based and neural laser detection,
  smoothing, feedback, and ESP32 communication.
- `utils/platform.py`, `cuda_utils.py`: platform selection and CUDA helpers.
- `esp32/boot.py`, `tracker.py`, `Servo.py`: MicroPython firmware and TCP control.
- `hardware/`: CAD and fabrication assets; `drafts/`: experimental code.

Platform selection is capability-based: Hailo is attempted on supported Raspberry
Pi systems, with an Ultralytics fallback; desktop Linux and Windows use
Ultralytics, as does Jetson. Optimized model selection can prefer TensorRT and
ONNX over PyTorch; preserve CPU fallbacks. See `README.md` / `README-it.md` and
`JETSON_ORIN.md` / `JETSON_ORIN_IT.md` for deployment background, checking legacy
examples against current Python and dependency requirements before use.

## CI and releases

`.github/workflows/ci.yaml` validates the lockfile, synchronizes dependencies,
checks compilation, builds, audits dependencies, and tests the installed wheel.
`publish.yml` calls that same workflow before publishing to PyPI or TestPyPI.
Claude workflows are service-specific integrations; project instructions live
here. Keep action revisions pinned and compatible with their declared inputs.
Dependabot checks GitHub Actions updates weekly. Validate workflow edits with
`actionlint` and inspect upstream action metadata for changed inputs.
