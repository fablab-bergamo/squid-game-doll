# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A "Red Light, Green Light" robot inspired by Squid Game TV series, using AI for player recognition and tracking with an animated doll and optional laser targeting system. Players register via face detection, move during green light phases, and are eliminated if they move during red light phases. The system runs on either PC (with CUDA support recommended), Jetson Orin (with CUDA acceleration), or Raspberry Pi 5 with Hailo AI KIT.

## Development Commands

### Setup and Installation
```bash
# Install poetry
pip install poetry

# === PC Installation (Windows/Linux) ===
# Install base dependencies + PyTorch
poetry install --extras standard
# Install Ultralytics
poetry run pip install ultralytics --no-deps
poetry run pip install tqdm seaborn psutil py-cpuinfo thop requests PyYAML
# Optional: CUDA support for NVIDIA GPU
poetry run pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall

# === Jetson Orin Installation ===
# Install base dependencies (WITHOUT PyTorch)  
poetry install
# Install Jetson-optimized PyTorch
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl
# Install Ultralytics without dependencies
poetry run pip install ultralytics --no-deps
poetry run pip install tqdm seaborn psutil py-cpuinfo thop requests PyYAML
# Install ONNX Runtime GPU
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl

# === Raspberry Pi Installation ===
# Install base dependencies
poetry install
# Install Hailo AI infrastructure
poetry run pip install git+https://github.com/hailo-ai/hailo-apps-infra.git
# Download Hailo models
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
# Install PyTorch for Raspberry Pi
poetry install --extras standard

# For detailed Jetson Orin setup and performance optimization, see:
# 📖 JETSON_ORIN.md / JETSON_ORIN_IT.md - Complete Jetson Orin installation and performance guide
```

### ESP32 Development
```bash
# ESP32 files are located in esp32/ folder
# Use Thonny IDE (https://thonny.org/) for MicroPython development
# Flash MicroPython firmware to ESP32C2 MINI Wemos board

# Main files:
# - boot.py: WiFi connection and auto-start
# - tracker.py: Main control server for doll and laser systems  
# - Servo.py: Custom servo control class for SG90 motors
```

### Running the Application
```bash
# Configure vision areas (generates config.yaml)
poetry run python -m squid_game_doll --setup

# Run with default configuration
poetry run python -m squid_game_doll

# Run with specific hardware configuration
poetry run python -m squid_game_doll -m 0 -w 0 -k -i 192.168.45.50

# All CLI options:
# -m/--monitor: 0-based monitor index
# -w/--webcam: 0-based webcam index  
# -k/--killer: enable ESP32 laser shooter
# -i/--tracker-ip: ESP32 IP address (default: 192.168.45.50)
# -j/--joystick: joystick index
# -n/--neural_net: custom neural network model file
# -c/--config: config file (default: config.yaml)
# -s/--setup: setup mode for area configuration

### Game Controls
```bash
# During gameplay or setup:
# Q key: Exit the game/setup immediately
# ESC key: Exit setup mode (setup only)
# Mouse: Click buttons and interact with UI
# Close window: Standard window close button
```

### Testing and Quality
```bash
# Run tests
poetry run pytest

# Code formatting and linting (development dependencies)
poetry install --with dev
poetry run black .
poetry run flake8 .

# Performance profiling
poetry run python -m cProfile -o game.prof -m src.squid_game_doll.run
poetry run snakeviz ./game.prof
```

## Architecture Overview

### Core Game Components
- **SquidGame**: Main game controller managing state transitions (LOADING → INIT → GREEN_LIGHT → RED_LIGHT → VICTORY/GAMEOVER)
- **GameScreen**: Pygame-based rendering engine for UI and game display
- **GameCamera**: Webcam interface with frame processing and coordinate transformations
- **GameSettings**: Configuration management for vision areas, game parameters, and hardware settings

### Player Detection and Tracking
- **BasePlayerTracker**: Abstract base for player detection systems
- **PlayerTrackerUL**: Ultralytics YOLO implementation for PC (supports CUDA)
- **PlayerTrackerHailo**: Hailo AI accelerated tracking for Raspberry Pi 5
- **Player**: Player state management (position, face, elimination status, movement detection)
- **FaceExtractor**: OpenCV Haar cascade face detection for player registration (improved Jetson compatibility)

### Laser Targeting System (Work in Progress)
- **LaserShooter**: ESP32 communication for servo control and laser activation
- **LaserTracker**: Computer vision laser dot detection and positioning feedback  
- **LaserFinder**: Image processing pipeline for laser dot recognition using threshold + dilate + Hough circles
- **Status**: Currently under development, basic targeting implemented but requires refinement

### Configuration and Setup
- **ConfigPhase**: Interactive setup for defining vision areas (start zone, finish zone, play area)
- **Calibrator**: Camera calibration utilities

## Platform-Specific Behavior

### Neural Network Model Selection
- **Linux (Raspberry Pi)**: Automatically uses Hailo models (.hef files) via PlayerTrackerHailo
- **Linux (Jetson Orin)**: Uses TensorRT-optimized YOLO models via PlayerTrackerUL for maximum performance with CUDA acceleration
- **Windows/PC**: Uses Ultralytics YOLO models via PlayerTrackerUL
- Models are loaded dynamically based on platform detection

### Jetson Orin Performance Optimization

For detailed performance analysis, optimization guides, and troubleshooting:
**📖 See [JETSON_ORIN.md](JETSON_ORIN.md) / [JETSON_ORIN_IT.md](JETSON_ORIN_IT.md) - Complete performance guide and optimization instructions**

**Quick Summary**:
- **TensorRT Engine**: Maximum performance with hardware acceleration
- **Model Priority**: TensorRT (.engine) > PyTorch (.pt) for best speed
- **Real Performance**: 14-40 FPS depending on model choice (nano vs large)
- **Automatic Detection**: System automatically selects optimal model format

### Troubleshooting

For CUDA issues, installation problems, and performance troubleshooting:
**📖 See [JETSON_ORIN.md](JETSON_ORIN.md#troubleshooting-jetson-orin-issues) / [JETSON_ORIN_IT.md](JETSON_ORIN_IT.md#risoluzione-problemi-jetson-orin) - Complete troubleshooting guide**

### Hardware Integration
- **ESP32 Controller**: MicroPython-based servo and LED control (see esp32/ folder)
- **Jetson GPIO**: Direct GPIO control using validated pins from jetson-orin-webgpio project (pins 7, 15, 29, 31, 32, 33)
- **Webcam**: Logitech C920 recommended, manual exposure control for laser detection
- **Laser System**: Optional pan-tilt platform with red/green laser (improved with validated GPIO pins)

## Key Configuration Files

- **config.yaml**: Generated by setup mode, contains vision areas and game parameters
- **pyproject.toml**: Poetry dependencies and project metadata

## Game Flow and States

1. **LOADING**: Intro screen while neural network models load
2. **INIT**: 15-second player registration phase (face capture in start area)
3. **GREEN_LIGHT**: Players can move toward finish line
4. **RED_LIGHT**: Motion detection active, violators eliminated
5. **VICTORY/GAMEOVER**: End state based on player outcomes

## Testing Strategy

Tests focus on core game logic components:
- GameSettings serialization/deserialization
- Player state management and movement detection
- Configuration file handling
- Basic component initialization

The test suite uses pytest with pygame initialization fixtures and does not test hardware-dependent components (camera, ESP32, neural networks).

## ESP32 Hardware Controller

### Architecture
The ESP32 controller manages physical doll components via a TCP server (port 15555) that receives commands from the main Python application.

### Hardware Connections

#### ESP32C2 MINI Wemos (Network Mode)
```
GPIO Pin | Component        | Function
---------|------------------|------------------
Pin 3    | SG90 Servo       | Head rotation (0-180°)
Pin 1    | PWM LEDs         | Eyes brightness control
Pin 5    | SG90 Servo       | Laser H-axis (pan) - WIP
Pin 4    | SG90 Servo       | Laser V-axis (tilt) - WIP  
Pin 2    | Laser Module     | Laser on/off - WIP
Pin 7    | RGB LED          | Status indicator (built-in)
```

#### Jetson Orin GPIO (Direct Mode) - VALIDATED PINS
```
Board Pin | GPIO# | Component        | Function
----------|-------|------------------|------------------
Pin 29    | 453   | H-Servo (Pan)    | Horizontal laser targeting
Pin 31    | 454   | V-Servo (Tilt)   | Vertical laser targeting
Pin 33    | 391   | Head Servo       | Doll head rotation (0-180°)
Pin 32    | 389   | Laser Module     | Laser on/off (active LOW, PWM capable)
Pin 15    | 433   | Eyes PWM         | LED brightness control (PWM capable)
Pin 7     | 492   | [SPARE]          | Reserved validated pin
```

**Jetson GPIO Improvements:**
- All pins validated through jetson-orin-webgpio testing
- Proper device tree overlay configuration  
- Enhanced error handling with emoji logging
- Safety: pins initialized LOW to prevent unexpected activation
- JETSON_MODEL_NAME environment variable set automatically

### Key ESP32 Files
- **boot.py**: Auto-connects to WiFi, sets hostname, imports tracker module
- **tracker.py**: Main async server handling doll control and laser targeting
- **Servo.py**: Custom servo control class optimized for SG90 motors

### Communication Protocol
The ESP32 exposes these commands via TCP:
```python
# Doll control
"h0"           # Head position 0 (facing forward)
"h1"           # Head position 180 (turned away) 
"e0"           # Eyes off
"e1"           # Eyes on (pulsing effect)

# Laser targeting (Work in Progress)
"(h_angle, v_angle)"  # Set laser target coordinates
"on"/"off"     # Laser enable/disable
"angles"       # Get current servo positions
"limits"       # Get servo angle limits

# Utility
"test"         # Start servo test movement
"stop"         # Stop test movement
"quit"         # Close connection
```

### ESP32 Development Workflow
1. Install MicroPython firmware on ESP32C2 MINI
2. Use Thonny IDE for code development and upload
3. Configure WiFi credentials in boot.py (replace "SSID"/"Password")
4. Upload all three files to ESP32 root directory
5. ESP32 will auto-start server on boot at IP shown in serial output

### Important ESP32 Notes
- WiFi hostname set to "esp32tracker" for easy network identification
- Server automatically restarts if client disconnections occur
- Servo movements are smoothed to prevent jerky motion
- Built-in RGB LED indicates WiFi connection status (green=connected, red=disconnected)
- Head positioning uses gradual movement for realistic doll animation
- Eyes use PWM for smooth pulsing effect during red light phases

## Development Notes

- Webcam exposure must be manually controlled for reliable laser detection
- Frame rate typically 10 FPS for game loop, 30 FPS possible with CUDA acceleration
- Vision areas must be properly configured for game mechanics to work
- Face detection uses OpenCV Haar cascades for better cross-platform compatibility
- Enhanced face processing includes background removal and contour enhancement for dramatic visual effects
- Laser targeting improved with validated GPIO pins and better error handling
- ESP32 communication uses simple TCP protocol for reliability (alternative to direct GPIO)
- Jetson GPIO control uses proven approach from jetson-orin-webgpio project
- Servo angle limits configurable, pins validated for safety
- GPIO operations include comprehensive logging with emoji indicators
- All GPIO pins initialized LOW for safety (laser, servos, LEDs start in safe state)
- update the italian versions when you update any MD file in English
- dont commit without being asked to