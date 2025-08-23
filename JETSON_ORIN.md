# NVIDIA Jetson Orin Setup Guide

This guide covers optimal setup and performance optimization for **NVIDIA Jetson Orin** with JetPack 6.1+ for maximum performance.

## Quick Setup

### Prerequisites
* NVIDIA Jetson Orin with JetPack 6.1+ installed
* USB webcam (Logitech C920 recommended)
* Internet connection for package installation

### Installation Commands

```bash
# Install poetry and dependencies
pip install poetry
poetry install

# Install PyTorch with CUDA support for Jetson Orin
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl

# Install ONNX Runtime with GPU support
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl

# IMPORTANT: If ONNX Runtime gets reinstalled during setup, reinstall the GPU version:
# poetry run pip uninstall onnxruntime -y && poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl
```

### Model Optimization

```bash
# Run optimization script (exports to ONNX by default)
poetry run python optimize_for_jetson.py --int8  # Full optimization with INT8
poetry run python optimize_for_jetson.py         # Standard optimization with FP16

# For maximum performance: Export to TensorRT engine format
/usr/src/tensorrt/bin/trtexec --onnx=yolo11n.onnx --saveEngine=yolo11n.engine --memPoolSize=workspace:4096 --fp16 --verbose
/usr/src/tensorrt/bin/trtexec --onnx=yolo11l.onnx --saveEngine=yolo11l.engine --memPoolSize=workspace:4096 --fp16 --verbose
```

### Performance Mode
```bash
# Set Jetson to max performance mode
sudo nvpmodel -m 0 && sudo jetson_clocks
```

---

## Performance Analysis

### Jetson Orin Performance Optimization
The PlayerTrackerUL class includes specific optimizations for Jetson Orin:

**Automatic Model Format Detection**: 
- Automatically detects Jetson Orin hardware (aarch64 + /etc/nv_tegra_release)
- **Model Priority**: TensorRT (.engine) > PyTorch (.pt) for maximum performance
- Uses yolo11n.pt (nano model) by default for optimal speed vs accuracy balance

**Performance Optimizations**:
- TensorRT execution with system TensorRT libraries
- FP16 precision for improved speed
- Disabled augmentation during inference
- Optimized thread count for ARM processors
- Static input shapes for TensorRT optimization

### Measured Performance on Jetson Orin (Real-world Testing)

**Model Performance Comparison**:
- PyTorch model: ~80-100ms inference (10-12 FPS)
- ONNX GPU: Not compatible (API limitations in Jetson GPU build)

**TensorRT Engine Performance** ⚡ **MAXIMUM PERFORMANCE**:

**YOLO11n (Nano Model)**:
  - **Preprocessing**: ~2ms (image preparation)
  - **TensorRT Inference**: ~5-15ms (neural network computation)
  - **Postprocessing**: ~3ms (NMS, output formatting)
  - **Tracking Overhead**: ~15-20ms (ByteTrack algorithm)
  - **Total Frame Processing**: ~25-40ms (25-40 FPS)

**YOLO11l (Large Model)**:
  - **Preprocessing**: 2.7ms (image preparation)
  - **TensorRT Inference**: 47.1ms (neural network computation)
  - **Postprocessing**: 5.8ms (NMS, output formatting)
  - **Tracking Overhead**: ~15-20ms (ByteTrack algorithm)
  - **Total Frame Processing**: 68-72ms (14-16 FPS)

### Performance Breakdown Analysis
- ✅ **TensorRT inference**: Excellent performance vs PyTorch
- ⚠️ **Tracking bottleneck**: ByteTrack algorithm is main limitation
- ✅ **Post-processing**: Optimized GPU→CPU transfers
- 💡 **Model choice**: Nano model for speed, Large model for accuracy

### Performance Optimization Recommendations
- ✅ **Use TensorRT**: Provides significant inference speed improvement
- ✅ **Choose model size**: yolo11n for speed, yolo11l for accuracy
- ⚠️ **Tracking limitation**: ByteTrack algorithm limits overall FPS
- 💡 **For higher FPS**: Consider detection-only mode without tracking
- 🎯 **Balanced approach**: Current performance is suitable for Squid Game mechanics

---

## Troubleshooting Jetson Orin Issues

### CUDA Issues

If you see messages like "CUDA not available" or "Using CPU..." in the logs, follow these steps:

**Problem**: PyTorch shows "CUDA available: False"
```bash
# Solution: Install CUDA-enabled PyTorch and torchvision wheels
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl
```

**Problem**: ONNX Runtime shows "Failed to start ONNX Runtime with CUDA. Using CPU..."
```bash
# Solution: Ensure ONNX Runtime GPU version is installed (may need reinstallation)
poetry run pip uninstall onnxruntime -y && poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl
```

### Verification Commands

**Check PyTorch CUDA support**:
```bash
poetry run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

**Check ONNX Runtime GPU providers**:
```bash
poetry run python -c "import onnxruntime as ort; print('Available providers:', ort.get_available_providers())"
```

**Expected output should show**:
- PyTorch: `CUDA available: True`
- ONNX Runtime: `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']`

### TensorRT Engine Issues

**Problem**: TensorRT engine fails to load
- **Solution**: Ensure system TensorRT is accessible and compatible
- **Fallback**: System automatically falls back to PyTorch model
- **Check**: Look for "System TensorRT X.X.X available" in logs

**Problem**: "AttributeError: module 'onnxruntime' has no attribute 'get_available_providers'"
- **Cause**: Jetson ONNX Runtime GPU version has limited API
- **Solution**: System automatically uses PyTorch model instead
- **Note**: This is expected behavior, not an error

---

## Hardware Integration

### ESP32 Controller
For physical doll control, see the ESP32 setup in the main documentation.

### Webcam Setup
- **Recommended**: Logitech C920 for best compatibility
- **Requirements**: Manual exposure control for laser detection
- **Performance**: Typically 10-30 FPS depending on model choice

### Laser System (Optional)
- **Status**: Work in progress, basic targeting implemented
- **Hardware**: Pan-tilt platform with red/green laser modules
- **Safety**: Proper safety considerations required

---

## OpenCV CUDA Installation

For optimal performance, install OpenCV with CUDA support to accelerate image processing operations.

### Prerequisites for OpenCV CUDA
- Jetson Orin with JetPack 6.1+ installed
- At least 8.5 GB total memory (RAM + swap)
- CUDA toolkit installed (verify with `nvcc --version`)
- **Ubuntu multiverse repository enabled** (required for multimedia codecs)

### Current System Check

First, verify your current OpenCV installation:

```bash
# Check OpenCV version and CUDA support
python3 -c "import cv2; print('OpenCV version:', cv2.__version__); print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"

# Check CUDA toolkit
nvcc --version

# Check available memory
free -h && df -h /
```

### OpenCV CUDA Installation Methods

#### Method 1: Automated Script (Recommended)

The easiest approach using Q-Engineering's automated installation script:

```bash
# Download the installation script
wget https://github.com/Qengineering/Install-OpenCV-Jetson-Nano/raw/main/OpenCV-4-13-0.sh

# Make it executable
sudo chmod 755 ./OpenCV-4-13-0.sh

# Run the installation (takes 2-3 hours)
./OpenCV-4-13-0.sh
```

#### Enable Multiverse Repository

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

#### Common OpenCV Installation Issues

**libfaac-dev Package Missing Error**

If you encounter `E: Unable to locate package libfaac-dev`:

```bash
# Install alternative AAC codec
sudo apt update
sudo apt install libfdk-aac-dev

# Install additional multimedia codecs (requires multiverse enabled)
sudo apt install ubuntu-restricted-extras
sudo apt install libfdk-aac-dev libmp3lame-dev libx264-dev libx265-dev
```

#### Memory Requirements
- **Minimum**: 8.5 GB total memory (RAM + swap)
- **Build time**: 2-3 hours
- **Recommendation**: Set swap to 8GB to reduce build time from 2.5 hours to 1.5 hours

### OpenCV CUDA Verification

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

### Integration with Poetry Projects

#### Copy CUDA OpenCV to Poetry Environment (Recommended)

After building CUDA OpenCV system-wide, integrate it with your Poetry project:

```bash
# Get Poetry virtual environment path
VENV_PATH=$(poetry env info --path)

# Copy system CUDA OpenCV to Poetry environment
cp -r /usr/lib/python3/dist-packages/cv2* "$VENV_PATH/lib/python3.10/site-packages/"

# Verify CUDA support
poetry run python -c "import cv2; print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"
```

### Squid Game OpenCV CUDA Integration

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

### OpenCV CUDA Performance Benefits

- **Larger models**: More pronounced CUDA acceleration effects
- **Tensor processing**: Better performance with more simultaneous tensor operations
- **Image processing**: Significant speedup for resize, color conversion, and filtering operations
- **Combined with TensorRT**: Optimal performance for YOLO inference + OpenCV preprocessing

### OpenCV CUDA Troubleshooting

**Issue: "CUDA not detected in Poetry environment"**
```bash
# Solution: Verify copy was successful
poetry run python -c "import cv2; print('Location:', cv2.__file__); print('CUDA:', cv2.cuda.getCudaEnabledDeviceCount())"
```

---

## Development Notes

- Webcam exposure must be manually controlled for reliable laser detection
- Vision areas must be properly configured for game mechanics to work
- Face detection uses OpenCV Haar cascades for better cross-platform compatibility
- Enhanced face processing includes background removal and contour enhancement
- Laser targeting requires careful calibration of threshold parameters (Work in Progress)
- OpenCV CUDA acceleration provides significant performance improvements for image processing
- Combined TensorRT + CUDA OpenCV gives optimal performance for real-time applications