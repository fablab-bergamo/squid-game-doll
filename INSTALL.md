# Installation Guide

This guide covers installation for both supported hardware platforms:
- **Raspberry Pi 5 + Hailo AI KIT** (hardware-accelerated AI)
- **NVIDIA Jetson Nano** (CUDA-accelerated AI)

---

## NVIDIA Jetson Nano Installation

### Prerequisites
* NVIDIA Jetson Nano with JetPack 6.0+ installed
* USB webcam (Logitech C920 recommended)
* Internet connection for package installation
* At least 8GB microSD card (16GB+ recommended)

### 1. Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git wget curl
```

### 2. Install Project Dependencies

Clone the repository and install the Squid Game Doll software:

```bash
# Install Poetry (Python dependency manager)
pip install poetry

# Install project dependencies
poetry install

# IMPORTANT: Install CUDA-enabled PyTorch for Jetson Nano
poetry run pip uninstall torch torchvision torchaudio -y
poetry run pip install torch==2.8.0 torchvision==0.23.0 --index-url=https://pypi.jetson-ai-lab.io/jp6/cu126
```

### 3. Verify CUDA Installation

Check that PyTorch recognizes the Jetson GPU:

```bash
poetry run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

Expected output:
```
CUDA available: True
Device: Orin
```

### 4. Optimize Performance (Optional)

For maximum performance, enable high-performance mode:

```bash
# Set Jetson to maximum performance mode
sudo nvpmodel -m 0 && sudo jetson_clocks
```

### 5. Configuration and Testing

```bash
# Configure vision areas
poetry run python -m src.squid_game_doll.run --setup -w 0

# Run the game
poetry run python -m src.squid_game_doll.run -w 0
```

---

# Setup on Raspberry Pi 5 + AI KIT

## Hardware

* Make sure Raspberry Pi 5 and AI KIT are configured properly
* Webcam is configured and visible. This has been tested with USB Camera but native Raspberry cam should be usable.

```shell
v4l2-ctl --list-devices
v4l2-ctl -v width=1920,height=1080,pixelformat=MJPG
v4l2-ctl --stream-mmap=3 --stream-to=/dev/null --stream-count=250
```

## Software

* Install HAILO software stack on Raspberry Pi:

```shell
sudo apt install hailo-all
sudo apt install python3-gi
sudo reboot
```

* Check Hailo chip is recognized with hailortcli command:

```shell
(.venv) $ hailortcli fw-control identify
Executing on device: 0000:01:00.0
Identifying board
Control Protocol Version: 2
Firmware Version: 4.20.0 (release,app,extended context switch buffer)
Logger Version: 0
Board Name: Hailo-8
Device Architecture: HAILO8L
Serial Number: xxxxxxxxxxxxxxx
Part Number: HM21LB1C2LAE
Product Name: HAILO-8L AI ACC M.2 B+M KEY MODULE EXT TMP
```

* Run install script to create venv and install Python requirements and HEF model

```bash
./setup.sh
```

* Run run.py and check webcam index:

```bash
poetry run python -m src.squid_game_doll.run
```

Sample output

```
Hello from the pygame community. https://www.pygame.org/contribute.html
SquidGame(res=(1920, 1080) on #0, tracker disabled=True, ip=192.168.45.50)
Listing webcams:
	 1820: pispbe-input
	 1821: pispbe-tdn_input
	 1822: pispbe-stitch_input
	 1823: pispbe-output0
	 1824: pispbe-output1
	 1825: pispbe-tdn_output
	 1826: pispbe-stitch_output
	 1827: pispbe-config
	 1828: pispbe-input
	 1829: pispbe-tdn_input
	 1830: pispbe-stitch_input
	 1831: pispbe-output0
	 1832: pispbe-output1
	 1833: pispbe-tdn_output
	 1834: pispbe-stitch_output
	 1835: pispbe-config
	 1819: rpivid
	 220: pispbe-input
	 221: pispbe-tdn_input
	 222: pispbe-stitch_input
	 223: pispbe-output0
	 224: pispbe-output1
	 225: pispbe-tdn_output
	 226: pispbe-stitch_output
	 227: pispbe-config
	 228: pispbe-input
	 229: pispbe-tdn_input
	 230: pispbe-stitch_input
	 231: pispbe-output0
	 232: pispbe-output1
	 233: pispbe-tdn_output
	 234: pispbe-stitch_output
	 235: pispbe-config
	 219: rpivid
```

* Start the game with forced webcam index (example: 200)

```shell
poetry run python -m src.squid_game_doll.run -w 200
```
