# Installation Guide - Raspberry Pi 5 + Hailo AI KIT

> **Note**: This installation guide is specifically for Raspberry Pi 5 with Hailo AI KIT hardware. For other platforms (PC/Windows, Jetson Nano), see the main [README.md](README.md) and [CLAUDE.md](CLAUDE.md) files.

## Prerequisites

* Raspberry Pi 5 with Hailo AI KIT properly installed and configured
* USB webcam (tested) or Raspberry Pi camera module
* SD card with Raspberry Pi OS (64-bit recommended)
* Internet connection for package installation

## Hardware Setup

### Camera Configuration
Ensure your webcam is properly connected and recognized:

```shell
# List available camera devices
v4l2-ctl --list-devices

# Test camera configuration (optional)
v4l2-ctl -v width=1920,height=1080,pixelformat=MJPG
v4l2-ctl --stream-mmap=3 --stream-to=/dev/null --stream-count=250
```

## Software Installation

### 1. Install Hailo Software Stack

Install the Hailo AI Kit software packages:

```shell
sudo apt update
sudo apt install hailo-all
sudo apt install python3-gi
sudo reboot
```

### 2. Verify Hailo Installation

Check that the Hailo chip is properly recognized:

```shell
hailortcli fw-control identify
```

Expected output should show:
```
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

### 3. Install Project Dependencies

Clone the repository and install the Squid Game Doll software:

```bash
# Install Poetry (Python dependency manager)
pip install poetry

# Install project dependencies and setup virtual environment
poetry install

# Install Hailo-specific dependencies
poetry run pip install git+https://github.com/hailo-ai/hailo-apps-infra.git

# Download pre-trained Hailo model
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
```

## Configuration and Testing

### 1. Find Your Camera Index

Test the application to identify the correct camera device:

```bash
poetry run python -m src.squid_game_doll.run
```

The application will list available cameras. Look for USB webcam devices (typically lower numbers) among the Raspberry Pi specific devices:

```
Hello from the pygame community. https://www.pygame.org/contribute.html
SquidGame(res=(1920, 1080) on #0, tracker disabled=True, ip=192.168.45.50)
Listing webcams with capabilities:
	 0: USB Camera: USB Camera          # <-- USB webcam (use this)
	 1820: pispbe-input                 # <-- Pi-specific devices
	 1821: pispbe-tdn_input
	 1822: pispbe-stitch_input
	 [... more Pi-specific devices ...]
	 1819: rpivid
```

### 2. Configure Vision Areas

Run the setup mode to configure detection areas:

```bash
# Use the webcam index you identified (e.g., 0 for USB camera)
poetry run python -m src.squid_game_doll.run --setup -w 0
```

Follow the on-screen instructions to define:
- **Start Zone**: Where players register their faces
- **Finish Zone**: Goal area players must reach
- **Vision Area**: Detection area for movement monitoring

### 3. Run the Game

Start the game with your configured camera:

```bash
# Replace 0 with your actual camera index
poetry run python -m src.squid_game_doll.run -w 0
```

## Optional: ESP32 Laser Integration

To enable the animated doll with laser targeting:

```bash
# Enable ESP32 tracker with specific IP
poetry run python -m src.squid_game_doll.run -w 0 -k -i 192.168.45.50
```

See the [ESP32 documentation](esp32/) for hardware setup details.

## Troubleshooting

### Camera Issues
- If no USB camera is detected, check `lsusb` output
- Try different USB ports or cables
- Verify camera permissions: `ls -la /dev/video*`

### Hailo Issues
- Ensure AI KIT is properly seated in M.2 slot
- Check `dmesg | grep hailo` for hardware messages
- Verify Hailo installation: `hailortcli scan`

For additional help, see [CLAUDE.md](CLAUDE.md) for detailed development information.