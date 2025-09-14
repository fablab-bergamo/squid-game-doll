# ESP32 Development with mpremote

Simple guide for ESP32 development using standard `mpremote` commands with minimal scripting.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Standard Commands](#standard-commands)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

```bash
# Install mpremote
pip install mpremote
```

### Verify Installation

```bash
# Check mpremote version
mpremote version

# Auto-detect ESP32 device
mpremote connect auto

# List files on ESP32
mpremote fs ls
```

## Quick Start

**Important**: All ESP32 development must be done from within the `esp32/` directory.

```bash
# Navigate to ESP32 directory
cd esp32/

# Sync all files to ESP32
./sync.sh

# Or manually sync individual files
mpremote fs cp *.py :
mpremote reset
```

## Standard Commands

### File Operations

```bash
# Copy single file
mpremote fs cp tracker.py :

# Copy all Python files
mpremote fs cp *.py :

# Remove file from ESP32
mpremote fs rm :tracker.py

# List ESP32 files
mpremote fs ls

# Show file contents
mpremote fs cat :tracker.py
```

### Device Control

```bash
# Hard reset (hardware reset)
mpremote reset

# Soft reset (restart Python)
mpremote eval "import machine; machine.soft_reset()"

# Execute Python command
mpremote eval "print('Hello from ESP32!')"

# Interactive REPL
mpremote repl
```

### Advanced Operations

```bash
# Mount local directory (for temporary testing)
mpremote mount esp32/ exec "import tracker"

# Capture output to file
mpremote repl --capture-output > esp32_logs.txt

# Check ESP32 memory
mpremote eval "import gc; print('Free memory:', gc.mem_free())"
```

## Development Workflow

### 1. Initial Setup

```bash
# Navigate to ESP32 directory
cd esp32/

# Sync all files
./sync.sh

# Verify files were copied
mpremote fs ls

# Check ESP32 response
mpremote eval "print('ESP32 ready!')"
```

### 2. Development Cycle

```bash
# 1. Edit files in your IDE
# 2. Sync changes
./sync.sh

# 3. Test via REPL
mpremote repl
>>> import tracker
>>> # Test your code
```

### 3. Debugging

```bash
# View real-time output
mpremote repl --capture-output

# Check for errors
mpremote eval "
try:
    import tracker
    print('✅ Import successful')
except Exception as e:
    print('❌ Import failed:', e)
"

# Check memory usage
mpremote eval "
import gc
print('Free memory:', gc.mem_free())
print('Allocated:', gc.mem_alloc())
"
```

## File Structure

The ESP32 tracker consists of these files:

```
esp32/
├── constants.py          # Hardware pins and timing
├── Servo.py             # Servo control class
├── head_controller.py   # Head movement
├── eyes_controller.py   # Eye brightness control
├── laser_controller.py  # Laser targeting
├── test_mode_manager.py # Test mode coordination
├── status_led.py        # WiFi status LED
├── tracker_server.py    # TCP server
├── tracker.py          # Main application
├── boot.py             # ESP32 boot script
└── sync.sh             # Simple sync script
```

## Troubleshooting

### Common Issues

#### ESP32 Not Detected
```bash
# List available devices
ls /dev/tty* | grep -E "(USB|ACM)"

# Connect to specific port
mpremote connect /dev/ttyUSB0
```

#### Permission Errors (Linux)
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Then logout and login again

# Or use sudo for one-time access
sudo mpremote fs ls
```

#### File Transfer Errors
```bash
# Check ESP32 filesystem space
mpremote eval "import os; print('Free space:', os.statvfs('/')[3] * os.statvfs('/')[1])"

# Remove files if needed
mpremote fs rm :old_file.py
```

#### Syntax Errors
```bash
# Validate files locally (if micropython is installed)
micropython -c "compile(open('tracker.py').read(), 'tracker.py', 'exec')"

# Or test import on ESP32
mpremote eval "
try:
    compile(open('tracker.py').read(), 'tracker.py', 'exec')
    print('✅ Syntax OK')
except SyntaxError as e:
    print('❌ Syntax error:', e)
"
```

### Debug Commands

```bash
# List imported modules
mpremote eval "import sys; print('Modules:', list(sys.modules.keys()))"

# Free memory
mpremote eval "import gc; gc.collect(); print('Free memory:', gc.mem_free())"

# ESP32 info
mpremote eval "
import sys
print('Platform:', sys.platform)
print('Implementation:', sys.implementation)
"
```

## Best Practices

1. **Always work from esp32/ directory**
2. **Test changes incrementally** - sync and test small changes
3. **Use REPL for debugging** - interactive testing is faster
4. **Check syntax locally** before syncing when possible
5. **Keep backups** of working configurations
6. **Monitor memory usage** to prevent out-of-memory issues

---

## Quick Reference

| Task | Command |
|------|---------|
| Sync all files | `./sync.sh` |
| Copy single file | `mpremote fs cp file.py :` |
| Open REPL | `mpremote repl` |
| Hard reset | `mpremote reset` |
| Soft reset | `mpremote eval "import machine; machine.soft_reset()"` |
| List files | `mpremote fs ls` |
| Show logs | `mpremote repl --capture-output` |

**Happy ESP32 Development! 🚀**