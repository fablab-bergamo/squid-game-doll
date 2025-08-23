# OpenCV CUDA Installation Guide for Jetson Nano

This guide provides step-by-step instructions for installing OpenCV with CUDA support on Jetson Nano.

## Prerequisites

- Jetson Nano with JetPack installed
- At least 8.5 GB total memory (RAM + swap)
- CUDA toolkit installed (verify with `nvcc --version`)
- **Ubuntu multiverse repository enabled** (required for multimedia codecs)

## Current System Check

First, verify your current OpenCV installation:

```bash
# Check OpenCV version and CUDA support
python3 -c "import cv2; print('OpenCV version:', cv2.__version__); print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"

# Check CUDA toolkit
nvcc --version

# Check available memory
free -h && df -h /
```

## Installation Methods

### Method 1: Automated Script (Recommended)

The easiest approach using Q-Engineering's automated installation script:

```bash
# Download the installation script
wget https://github.com/Qengineering/Install-OpenCV-Jetson-Nano/raw/main/OpenCV-4-13-0.sh

# Make it executable
sudo chmod 755 ./OpenCV-4-13-0.sh

# Run the installation (takes 2-3 hours)
./OpenCV-4-13-0.sh
```
## Common Issues and Solutions

### Enable Multiverse Repository

**IMPORTANT**: Before installing multimedia packages, enable the multiverse repository:

**GUI Method (Recommended):**
1. Open "Software & Updates" utility
2. Go to "Ubuntu Software" tab
3. Check the box for "Software restricted by copyright or legal issues (multiverse)"
4. Click "Close" and reload package lists when prompted

**Command Line Method:**
```bash
# Enable multiverse repository
sudo add-apt-repository multiverse
sudo apt update
```

### libfaac-dev Package Missing Error

If you encounter `E: Unable to locate package libfaac-dev`:

```bash
# Install alternative AAC codec
sudo apt update
sudo apt install libfdk-aac-dev

# Install additional multimedia codecs (requires multiverse enabled)
sudo apt install ubuntu-restricted-extras
sudo apt install libfdk-aac-dev libmp3lame-dev libx264-dev libx265-dev
```

### Memory Requirements

- **Minimum**: 8.5 GB total memory (RAM + swap)
- **Build time**: 2-3 hours
- **Recommendation**: Set swap to 8GB to reduce build time from 2.5 hours to 1.5 hours

## Verification

After installation, verify CUDA support:

```bash
# Test OpenCV CUDA installation
python3 -c "
import cv2
print('OpenCV version:', cv2.__version__)
print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    print('✅ OpenCV CUDA support enabled')
else:
    print('❌ OpenCV CUDA support not found')
"
```

## Integration with Poetry Projects

### Method 1: Copy CUDA OpenCV to Poetry Environment (Recommended)

After building CUDA OpenCV system-wide, integrate it with your Poetry project:

```bash
# Get Poetry virtual environment path
VENV_PATH=$(poetry env info --path)

# Copy system CUDA OpenCV to Poetry environment
cp -r /usr/lib/python3/dist-packages/cv2* "$VENV_PATH/lib/python3.10/site-packages/"

# Verify CUDA support
poetry run python -c "import cv2; print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"
```

## Integration with Squid Game Project

The project includes automatic CUDA detection and GPU acceleration:

```python
from .cuda_utils import cuda_cvt_color, cuda_resize, is_cuda_opencv_available

# Automatic GPU acceleration with CPU fallback
gray = cuda_cvt_color(frame, cv2.COLOR_BGR2GRAY)  # Uses GPU if available
resized = cuda_resize(frame, (320, 240))  # Uses GPU if available

# Check CUDA status
if is_cuda_opencv_available():
    print("🚀 CUDA OpenCV enabled - GPU acceleration active")
else:
    print("ℹ️ Using CPU-only OpenCV processing")
```

**GPU-Accelerated Operations:**
- Color conversions (BGR↔RGB, BGR↔Gray)
- Image resizing and scaling
- Gaussian blur filtering
- Automatic fallback to CPU if GPU operations fail

## Performance Benefits

- **Larger models**: More pronounced CUDA acceleration effects
- **Tensor processing**: Better performance with more simultaneous tensor operations
- **Image processing**: Significant speedup for resize, color conversion, and filtering operations
- **Combined with TensorRT**: Optimal performance for YOLO inference + OpenCV preprocessing

## Troubleshooting

### Troubleshooting Poetry Integration

**Issue: "CUDA not detected in Poetry environment"**
```bash
# Solution: Verify copy was successful
poetry run python -c "import cv2; print('Location:', cv2.__file__); print('CUDA:', cv2.cuda.getCudaEnabledDeviceCount())"
```
