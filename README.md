# Squid Game Doll 🔴🟢

*English | [**Italiano**](README-it.md)*

An AI-powered "Red Light, Green Light" robot inspired by the Squid Game TV series. This project uses computer vision and machine learning for real-time player recognition and tracking, featuring an animated doll that signals game phases and an optional laser targeting system for eliminated players.

**🎯 Features:**
- Real-time player detection and tracking using YOLO neural networks
- Face recognition for player registration
- Interactive animated doll with LED eyes and servo-controlled head
- Optional laser targeting system for eliminated players *(work in progress)*
- Support for PC (with CUDA), NVIDIA Jetson Nano (with CUDA), and Raspberry Pi 5 (with Hailo AI Kit)
- Configurable play areas and game parameters

**🏆 Status:** First working version demonstrated at Arduino Days 2025 in FabLab Bergamo, Italy.

## 🎮 Quick Start

### Prerequisites
- Python 3.9+ with Poetry
- Webcam (Logitech C920 recommended)
- Optional: ESP32 for doll control, laser targeting hardware

### Installation

#### **Method 1: PC (Windows/Linux)**
```bash
# 1. Install Poetry
pip install poetry

# 2. Install base dependencies + PyTorch for PC
poetry install --extras standard

# 3. Optional: CUDA support for NVIDIA GPU (better performance)
poetry run pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall

# 4. Install Ultralytics (required for AI detection)
poetry run pip install ultralytics --no-deps
poetry run pip install tqdm seaborn psutil py-cpuinfo thop requests PyYAML
```

#### **Method 2: NVIDIA Jetson Orin**
```bash
# 1. Install Poetry
pip install poetry

# 2. Install base dependencies (WITHOUT PyTorch)
poetry install

# 3. Install Jetson-optimized PyTorch manually
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl

# 4. Install Ultralytics without dependencies (prevents PyTorch overwrite)
poetry run pip install ultralytics --no-deps
poetry run pip install tqdm seaborn psutil py-cpuinfo thop requests PyYAML

# 5. Install ONNX Runtime GPU for Jetson
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl

# 6. Optional: CUDA OpenCV for maximum performance (see JETSON_ORIN.md)
# After building CUDA OpenCV system-wide:
VENV_PATH=$(poetry env info --path)
cp -r /usr/lib/python3/dist-packages/cv2* "$VENV_PATH/lib/python3.10/site-packages/"
```

#### **Method 3: Raspberry Pi 5 with Hailo AI Kit**
```bash
# 1. Install Poetry
pip install poetry

# 2. Install base dependencies
poetry install

# 3. Install Hailo AI infrastructure
poetry run pip install git+https://github.com/hailo-ai/hailo-apps-infra.git

# 4. Download pre-compiled Hailo models
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef

# 5. Install PyTorch for Raspberry Pi (if not automatically installed)
poetry install --extras standard
```

#### **Platform Detection**
The application automatically detects your platform and uses the appropriate AI backend:
- **PC**: Uses Ultralytics YOLO with PyTorch
- **Jetson Orin**: Uses TensorRT-optimized YOLO with CUDA acceleration  
- **Raspberry Pi**: Uses Hailo AI accelerated models (.hef files)

### Setup and Run

1. **Configure play areas** (first-time setup):
```bash
# Using Python module
poetry run python -m squid_game_doll --setup

# Or using console script (after installation)
squid-game-doll --setup
```

2. **Run the game**:
```bash
# Using Python module
poetry run python -m squid_game_doll

# Or using console script (after installation)
squid-game-doll
```

3. **Run with laser targeting** (requires ESP32 setup):
```bash
# Using Python module
poetry run python -m squid_game_doll -k -i 192.168.45.50

# Or using console script
squid-game-doll -k -i 192.168.45.50
```

## 🎯 How It Works

### Game Flow
Players line up 8-10m from the screen and follow this sequence:

1. **📝 Registration (15s)**: Stand in the starting area while the system captures your face
2. **🟢 Green Light**: Move toward the finish line (doll turns away, eyes off)
3. **🔴 Red Light**: Freeze! Any movement triggers elimination (doll faces forward, red eyes)
4. **🏆 Victory/💀 Elimination**: Win by reaching the finish line or get eliminated for moving during red light

### Game Phases Visual Guide

| Phase | Screen | Doll State | Action |
|-------|--------|------------|---------|
| **Loading** | ![Loading screen](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/loading_screen.png?raw=true) | Random movement | Attracts crowd |
| **Registration** | ![registration](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/init.png?raw=true) | ![Facing, no eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_init.png?raw=true) | Face capture |
| **Green Light** | ![Green light](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/green_light.png?raw=true) | ![Rotated, no eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_off.png?raw=true) | Players move |
| **Red Light** | ![Red light](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/red_light.png?raw=true) | ![Facing, red eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_on.png?raw=true) | Motion detection |

## ⚙️ Configuration

The setup mode allows you to configure play areas and camera settings for optimal performance.

### Area Configuration
You need to define three critical areas:

- **🎯 Vision Area** (Yellow): The area fed to the neural network for player detection
- **🏁 Finish Area**: Players must reach this area to win
- **🚀 Starting Area**: Players must register in this area initially

![Configuration Interface](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/config.png?raw=true)

### Configuration Steps
1. Run setup mode: `poetry run python -m squid_game_doll --setup`
2. Draw rectangles to define play areas (vision area must intersect with start/finish areas)
3. Adjust settings in the SETTINGS menu (confidence levels, contrast)
4. Test performance using "Neural network preview"
5. Save configuration to `config.yaml`

### Important Notes
- Vision area should exclude external lights and non-play zones
- Webcam resolution affects neural network input (typically resized to 640x640)
- Proper area configuration is essential for game mechanics to work correctly

## 🔧 Hardware Requirements

### Supported Platforms
| Platform | AI Acceleration | Performance | Best For |
|----------|----------------|-------------|----------|
| **PC with NVIDIA GPU** | CUDA | 30+ FPS | Development, High Performance |
| **NVIDIA Jetson Nano** | CUDA | 15-25 FPS | Mobile Deployment, Edge Computing |
| **Raspberry Pi 5 + Hailo AI Kit** | Hailo 8L | 10-15 FPS | Production Deployment |
| **PC (CPU only)** | None | 3-5 FPS | Basic Testing |

### Required Components

#### Core System
- **Computer**: PC (Windows/Linux), NVIDIA Jetson Nano, or Raspberry Pi 5
- **Webcam**: Logitech C920 HD Pro (recommended) or compatible USB webcam
- **Display**: Monitor or projector for game interface

#### Doll Hardware
- **Controller**: ESP32C2 MINI Wemos board
- **Servo**: 1x SG90 servo motor (head movement)
- **LEDs**: 2x Red LEDs (eyes)
- **3D Parts**: Printable doll components (see `hardware/doll-model/`)

#### Optional Laser Targeting System *(Work in Progress)*
⚠️ **Safety Warning**: Use appropriate laser safety measures and follow local regulations.

**Status**: Basic targeting implemented but requires refinement for production use.

**Components:**
- **Servos**: 2x SG90 servo motors for pan-tilt mechanism
- **Platform**: [Pan-and-tilt platform (~11 EUR)](https://it.aliexpress.com/item/1005005666356097.html)
- **Laser**: Choose one option:
  - **Green 5mW**: Higher visibility, safer for eyes, less precise focus
  - **Red 5mW**: Better focus, lower cost
- **3D Parts**: Laser holder (see `hardware/proto/Laser Holder v6.stl`)

### Play Space Requirements
- **Area**: 10m x 10m indoor space recommended
- **Distance**: Players start 8-10m from screen
- **Lighting**: Controlled lighting for optimal computer vision performance

### Detailed Installation
- **PC Setup**: See installation instructions above
- **Raspberry Pi 5**: See [INSTALL.md](INSTALL.md) ([Italiano](INSTALL_IT.md)) for complete Hailo AI Kit setup
- **ESP32 Programming**: Use [Thonny IDE](https://thonny.org/) with MicroPython (see `esp32/` folder)

## 🎲 Command Line Options

```bash
poetry run python -m squid_game_doll [OPTIONS]
# or
squid-game-doll [OPTIONS]
```

### Available Options
| Option | Description | Example |
|--------|-------------|---------|
| `-m, --monitor` | Monitor index (0-based) | `-m 0` |
| `-w, --webcam` | Webcam index (0-based) | `-w 0` |
| `-f, --fixed-image` | Fixed image for testing (instead of webcam) | `-f test_image.jpg` |
| `-k, --killer` | Enable ESP32 laser shooter | `-k` |
| `-i, --tracker-ip` | ESP32 IP address | `-i 192.168.45.50` |
| `-j, --joystick` | Joystick index | `-j 0` |
| `-n, --neural_net` | Custom neural network model | `-n yolov11m.hef` |
| `-c, --config` | Config file path | `-c my_config.yaml` |
| `-s, --setup` | Setup mode for area configuration | `-s` |

### Example Commands

**Basic setup:**
```bash
# First-time configuration
poetry run python -m squid_game_doll --setup -w 0

# Run game with default settings
poetry run python -m squid_game_doll
```

**Advanced configuration:**
```bash
# Full setup with laser targeting
poetry run python -m squid_game_doll -m 0 -w 0 -k -i 192.168.45.50

# Custom model and config
poetry run python -m squid_game_doll -n custom_model.hef -c custom_config.yaml

# Testing with fixed image instead of webcam
poetry run python -m squid_game_doll -f pictures/test_image.jpg
```

## 🤖 AI & Computer Vision

### Neural Network Models
- **PC (Ultralytics)**: YOLOv8/v11 models for object detection and tracking
- **NVIDIA Jetson Nano**: CUDA-optimized YOLOv11 models with automatic platform detection
- **Raspberry Pi (Hailo)**: Pre-compiled Hailo models optimized for edge AI
- **Face Detection**: OpenCV Haar cascades for player registration and identification

### Performance Optimization

#### Platform-Specific Optimizations
**NVIDIA Jetson Nano:**
- **Automatic CUDA acceleration** with optimized PyTorch wheels
- **CUDA OpenCV support** for GPU-accelerated image processing (optional)
- **Reduced input size** (416px vs 640px) for faster inference  
- **FP16 precision** for 2x speed improvement
- **Optimized thread count** for ARM processors
- **Jetson-specific model selection** (yolo11n.pt for optimal speed/accuracy balance)
- **TensorRT optimization** available via `optimize_for_jetson.py` script

**Raspberry Pi 5 + Hailo:**
- **Hardware-accelerated inference** using Hailo 8L AI processor
- **Optimized .hef models** compiled specifically for Hailo architecture
- **Parallel processing** between ARM CPU and Hailo AI accelerator

**PC with NVIDIA GPU:**
- **Full CUDA acceleration** with maximum input resolution
- **High-precision models** for best accuracy
- **Multi-threaded processing** for real-time performance

#### General Performance
- **Object Detection**: 3-30+ FPS depending on hardware and optimization
- **Face Extraction**: CPU-bound with OpenCV Haar cascades (GPU-accelerated with CUDA OpenCV)
- **Image Processing**: 2-5x speedup with CUDA OpenCV for color conversions and resizing
- **Laser Detection**: Computer vision pipeline using threshold + dilate + Hough circles

### Model Resources
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO8L/HAILO8L_object_detection.rst)
- [Neural Network Implementation Details](https://www.fablabbergamo.it/2025/03/30/primi-passi-con-lai-raspberry-pi-5-hailo/)

## 🛠️ Development & Testing

### Code Quality Tools
```bash
# Install development dependencies
poetry install --with dev

# Code formatting
poetry run black .

# Linting
poetry run flake8 .

# Run tests
poetry run pytest
```

### Performance Profiling
```bash
# Profile the application
poetry run python -m cProfile -o game.prof -m squid_game_doll

# Visualize profiling results
poetry run snakeviz ./game.prof
```

### Game Interface

![Game Interface](https://github.com/user-attachments/assets/4f3aed2e-ce2e-4f75-a8dc-2d508aff0b47)

The game uses PyGame as the rendering engine with real-time player tracking overlay.

## 🎯 Laser Targeting System (Advanced)

### Computer Vision Pipeline
The laser targeting system uses a sophisticated computer vision approach to detect and track laser dots:

![Laser Detection Example](https://github.com/user-attachments/assets/b3f5dd56-1ecf-4783-9174-87988d44a1f1)

### Detection Algorithm
1. **Channel Selection**: Extract R, G, B channels or convert to grayscale
2. **Thresholding**: Find brightest pixels using `cv2.threshold()`
3. **Morphological Operations**: Apply dilation to enhance spots
4. **Circle Detection**: Use Hough Transform to locate circular laser dots
5. **Validation**: Adaptive threshold adjustment for single-dot detection

```python
# Key processing steps
diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
masked_channel = cv2.dilate(masked_channel, None, iterations=4)
circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                          param1=50, param2=2, minRadius=3, maxRadius=10)
```

### Critical Considerations
- **Webcam Exposure**: Manual exposure control required (typically -10 to -5 for C920)
- **Surface Reflectivity**: Different surfaces affect laser visibility
- **Color Choice**: Green lasers often perform better than red
- **Timing**: 10-15 second convergence time for accurate targeting

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Windows slow startup | Set `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0` |
| Poor laser detection | Adjust exposure settings, check surface types |
| Multiple false positives | Increase threshold, mask external light sources |

## 🚧 Known Issues & Future Improvements

### Current Limitations
- **Vision System**: Combining low-exposure laser detection with normal-exposure player tracking
- **Laser Performance**: 10-15 second targeting convergence time
- **Hardware Dependency**: Manual webcam exposure calibration required

### Roadmap
- [ ] Retrain YOLO model for combined laser/player detection
- [ ] Implement depth estimation for faster laser positioning
- [ ] Automatic exposure calibration system
- [ ] Enhanced surface reflection compensation

### Completed Features
- ✅ 3D printable doll with animated head and LED eyes
- ✅ Player registration and finish line detection
- ✅ Configurable motion sensitivity thresholds
- ✅ GitHub Actions CI/CD and automated testing

## 📚 Additional Resources

- **Installation Guide**: [INSTALL.md](INSTALL.md) ([Italiano](INSTALL_IT.md)) for Raspberry Pi setup
- **CUDA OpenCV Setup**: [OPENCV_JETSON.md](OPENCV_JETSON.md) for Jetson Nano GPU acceleration
- **ESP32 Development**: Use [Thonny IDE](https://thonny.org/) for MicroPython
- **Neural Networks**: [Hailo AI implementation details](https://www.fablabbergamo.it/2025/03/30/primi-passi-con-lai-raspberry-pi-5-hailo/)
- **Camera Optimization**: [OpenCV camera performance tips](https://forum.opencv.org/t/opencv-camera-low-fps/567/4)

## 📄 License

This project is open source. See the LICENSE file for details.
