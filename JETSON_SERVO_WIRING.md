# Jetson Orin GPIO Servo Wiring Instructions

This document provides detailed wiring instructions for connecting SG90 servos and laser components directly to the Jetson Orin 40-pin GPIO header for the squid-game-doll project.

## ⚠️ Safety Warnings

- **POWER OFF** the Jetson Orin before making any connections
- **LASER SAFETY**: Never point laser at people, animals, or reflective surfaces
- **VOLTAGE CHECK**: Ensure servo voltage requirements match GPIO specifications
- **CURRENT LIMITS**: SG90 servos draw ~100-200mA each; total GPIO current should not exceed limits
- **STATIC PROTECTION**: Use anti-static precautions when handling components

## 🔍 Critical: Verify Your Jetson Model

**This pinout is for Jetson Orin Nano.** AGX Orin has a different pinout!

**Before wiring, confirm your model:**
```bash
# Check your Jetson model
cat /proc/device-tree/model

# Expected outputs:
# "NVIDIA Jetson Orin Nano Developer Kit"  ← Use this guide
# "NVIDIA Jetson AGX Orin Developer Kit"   ← Different pinout!
```

**If you have AGX Orin, the GPIO assignments will be different!**

## GPIO Pin Assignments (Board Numbering) 

| Component | Board Pin | GPIO Function | GPIO# | Validated | Notes |
|-----------|-----------|---------------|-------|-----------|-------|
| H-Servo (Pan) | Pin 29 | GPIO01 | 453 | ✅ | Horizontal laser targeting |
| V-Servo (Tilt) | Pin 31 | GPIO11 | 454 | ✅ | Vertical laser targeting |
| Head Servo | Pin 33 | GPIO13 (PWM) | 391 | ✅ | Doll head rotation |
| Laser Module | Pin 32 | GPIO07 (PWM) | 389 | ✅ | Laser on/off (active LOW) |
| Eyes PWM | Pin 15 | GPIO12 (PWM) | 433 | ✅ | Red LED brightness |
| **Alternative** | Pin 7 | GPIO09 | 492 | ✅ | Spare validated pin |
| **5V Power** | Pin 2, 4 | 5.0 VDC | - | - | Servo power rail |
| **Ground** | Pin 6, 9, 14, 20, 25, 30, 34, 39 | GND | - | - | Common ground |

**Key Changes:**
- All pins now use device-tree validated pins from jetson-orin-webgpio project
- Pins 7, 15, 29, 31, 32, 33 are confirmed working with proper GPIO setup
- GPIO numbers match official NVIDIA pinmux documentation

## Wiring Connections

### SG90 Servo Connections (3 Servos Total)

**Laser Pointer Pan/Tilt Platform (2 servos):**
- H-Servo: Horizontal movement of laser pointer
- V-Servo: Vertical movement of laser pointer

**Doll Head Servo (1 servo):**
- Head Servo: Rotates the doll's head for red/green light phases

Each SG90 servo has 3 wires:
- **Brown/Black**: Ground (GND)
- **Red**: Power (+5V)
- **Orange/Yellow**: PWM Signal

#### H-Axis Servo (Pan) - Horizontal Laser Pointer Movement
- **Signal Wire** → Pin 29 (GPIO01/453) ✅ VALIDATED
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 30, 34, 39 (GND)

#### V-Axis Servo (Tilt) - Vertical Laser Pointer Movement  
- **Signal Wire** → Pin 31 (GPIO11/454) ✅ VALIDATED
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 30, 34, 39 (GND)

#### Head Servo - Doll Head Rotation
- **Signal Wire** → Pin 33 (GPIO13/391) ✅ VALIDATED
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 30, 34, 39 (GND)

### Laser Pointer Module Connection
- **Control Signal** → Pin 32 (GPIO07/389) ✅ VALIDATED PWM-capable
- **Power (+)** → Pin 2 or 4 (5V)
- **Ground (-)** → Pin 6, 9, 14, 20, 25, 30, 34, 39 (GND)

*Note: Laser control is active LOW (GPIO LOW = laser ON). Pin initialized LOW for safety.*

### Eyes PWM Connection (Red LEDs in Doll Eyes)
- **PWM Signal** → Pin 15 (GPIO12/433) ✅ VALIDATED PWM-capable
- **Power (+)** → Pin 2 or 4 (5V) or 3.3V depending on LED requirements
- **Ground (-)** → Pin 6, 9, 14, 20, 25, 30, 34, 39 (GND)

*Note: Hardware PWM capable pin with software PWM implementation for brightness control.*

## Power Distribution

### Recommended Power Setup
```
Jetson 5V Rail (Pin 2/4)
    ├── Laser H-Servo Power (Red wire)
    ├── Laser V-Servo Power (Red wire) 
    ├── Doll Head Servo Power (Red wire)
    ├── Laser Pointer Module Power
    └── Eyes Red LEDs Power (if 5V rated)

Jetson GND (Multiple pins)
    ├── Laser H-Servo Ground (Brown/Black wire)
    ├── Laser V-Servo Ground (Brown/Black wire)
    ├── Doll Head Servo Ground (Brown/Black wire)
    ├── Laser Pointer Module Ground
    └── Eyes Red LEDs Ground
```

### Power Considerations
- **Total Current**: 3x SG90 servos = ~300-600mA peak
- **Jetson 5V Rating**: Check Jetson Orin specifications for maximum current
- **External Power**: Consider external 5V supply for high current applications
- **Capacitor**: Add 1000µF electrolytic capacitor near servos for power smoothing

## Physical Mounting

### Servo Pan-Tilt Platform
Based on project files in `hardware/proto/`:
- Use provided STL files for 3D printing servo mounts
- Mount servos in pan-tilt configuration
- Ensure mechanical limits match software limits:
  - **H-axis**: 30° to 150° (120° range)
  - **V-axis**: 0° to 120° (120° range)
  - **Head**: 0° to 180° (180° range)

### Cable Management
- Use ribbon cable or individual jumper wires
- Secure connections with heat shrink tubing
- Route cables away from moving servo parts
- Label wires for easy identification

## Software Configuration

### Required Dependencies
```bash
# Install Jetson GPIO library
pip install Jetson.GPIO

# Verify GPIO permissions
sudo groupadd -f -r gpio
sudo usermod -a -G gpio $USER
# Logout and login again for group changes
```

### Test Setup
```bash
# Run the test script
python test_jetson_servo.py

# Test individual components
# 1 - H-axis servo
# 2 - V-axis servo  
# 3 - Head servo
# 4 - Complete targeting system
# 5 - Calibrate limits
```

### GPIO Permissions
Add udev rule for GPIO access:
```bash
# Create udev rule file
sudo nano /etc/udev/rules.d/99-gpio.rules

# Add this content:
SUBSYSTEM=="gpio*", KERNEL=="gpiochip[0-9]*", GROUP="gpio", MODE="0664"
SUBSYSTEM=="gpio", KERNEL=="gpio[0-9]*", ACTION=="add", GROUP="gpio", MODE="0664"

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Troubleshooting

### Common Issues

#### Servos Not Moving
- Check 5V power supply voltage and current capacity
- Verify PWM signal connections
- Confirm GPIO permissions
- Test with multimeter: PWM signal should be 0-3.3V

#### Erratic Servo Movement
- Add power supply capacitor (1000µF)
- Check for loose connections
- Reduce PWM frequency if needed
- Ensure adequate power supply current

#### Laser Not Working
- Verify laser module voltage requirements
- Check active LOW configuration (GPIO LOW = ON)
- Test laser module independently
- Ensure safety compliance

#### GPIO Permission Errors
```bash
# Check current user groups
groups

# Add user to gpio group if not present
sudo usermod -a -G gpio $USER

# Logout and login again
```

#### Import Errors
```bash
# Install missing dependencies
pip install Jetson.GPIO numpy simple-pid

# For development environment
poetry run pip install Jetson.GPIO
```

## Servo Specifications

### SG90 Servo Specifications
- **Operating Voltage**: 4.8V - 6V
- **Operating Current**: 100-200mA (no load), 500-900mA (stall)
- **Control Signal**: PWM, 50Hz frequency
- **Pulse Width**: 0.5ms (0°) to 2.5ms (180°)
- **Rotation**: 180° maximum
- **Torque**: 1.8kg⋅cm (4.8V)
- **Speed**: 0.1s/60° (4.8V)

### PWM Signal Timing
- **Frequency**: 50Hz (20ms period)
- **0° Position**: 0.5ms pulse width (2.5% duty cycle)
- **90° Position**: 1.5ms pulse width (7.5% duty cycle)  
- **180° Position**: 2.5ms pulse width (12.5% duty cycle)

## Integration with Main Project

### Automatic Detection
The system will automatically detect Jetson GPIO availability and switch between:
- **Network Mode**: ESP32 communication (default)
- **Direct Mode**: Jetson GPIO control (when available)

### Configuration Override
Add to `config.yaml`:
```yaml
laser_control:
  mode: "direct"  # or "network" 
  gpio_enabled: true
```

This setup provides direct hardware control while maintaining compatibility with the existing ESP32 network-based system.