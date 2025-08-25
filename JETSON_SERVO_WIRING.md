# Jetson Orin GPIO Servo Wiring Instructions

This document provides detailed wiring instructions for connecting SG90 servos and laser components directly to the Jetson Orin 40-pin GPIO header for the squid-game-doll project.

## ⚠️ Safety Warnings

- **POWER OFF** the Jetson Orin before making any connections
- **LASER SAFETY**: Never point laser at people, animals, or reflective surfaces
- **VOLTAGE CHECK**: Ensure servo voltage requirements match GPIO specifications
- **CURRENT LIMITS**: SG90 servos draw ~100-200mA each; total GPIO current should not exceed limits
- **STATIC PROTECTION**: Use anti-static precautions when handling components

## GPIO Pin Assignments (Board Numbering)

| Component | GPIO Pin | Board Pin | Function | Notes |
|-----------|----------|-----------|----------|-------|
| H-Servo (Pan) | GPIO 13 | Pin 33 | Software PWM | Horizontal laser targeting |
| V-Servo (Tilt) | GPIO 22 | Pin 15 | Software PWM | Vertical laser targeting |
| Head Servo | GPIO 12 | Pin 32 | Software PWM | Doll head rotation |
| Laser Module | GPIO 5 | Pin 29 | Digital Out | Laser on/off control |
| Eyes Control | GPIO 23 | Pin 16 | Digital Out | Doll eyes on/off |
| **5V Power** | 5V | Pin 2, 4 | Power Supply | Servo power rail |
| **Ground** | GND | Pin 6, 9, 14, 20, 25, 30, 34, 39 | Ground | Common ground |

## 40-Pin Header Layout Reference

```
    3.3V  [ 1] [ 2]  5V      ← Power for servos
   GPIO2  [ 3] [ 4]  5V      ← Power for servos  
   GPIO3  [ 5] [ 6]  GND     ← Ground
   GPIO4  [ 7] [ 8]  GPIO14
     GND  [ 9] [10]  GPIO15  ← Ground
  GPIO17  [11] [12]  GPIO18
  GPIO27  [13] [14]  GND     ← Ground
  GPIO22  [15] [16]  GPIO23  ← V-servo, Eyes control
    3.3V  [17] [18]  GPIO24
  GPIO10  [19] [20]  GND     ← Ground
   GPIO9  [21] [22]  GPIO25
  GPIO11  [23] [24]  GPIO8
     GND  [25] [26]  GPIO7   ← Ground
   GPIO0  [27] [28]  GPIO1
   GPIO5  [29] [30]  GND     ← Laser control, Ground
   GPIO6  [31] [32]  GPIO12  ← Head servo
  GPIO13  [33] [34]  GND     ← H-servo, Ground
  GPIO19  [35] [36]  GPIO16
  GPIO26  [37] [38]  GPIO20
     GND  [39] [40]  GPIO21  ← Ground
```

## Wiring Connections

### SG90 Servo Connections (All 3 Servos)
Each SG90 servo has 3 wires:
- **Brown/Black**: Ground (GND)
- **Red**: Power (+5V)
- **Orange/Yellow**: PWM Signal

#### H-Axis Servo (Pan) - Horizontal Laser Movement
- **Signal Wire** → Pin 33 (GPIO 13)
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 30, 34, or 39 (GND)

#### V-Axis Servo (Tilt) - Vertical Laser Movement
- **Signal Wire** → Pin 15 (GPIO 22)
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 30, 34, or 39 (GND)

#### Head Servo - Doll Head Rotation
- **Signal Wire** → Pin 32 (GPIO 12)
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 30, 34, or 39 (GND)

### Laser Module Connection
- **Control Signal** → Pin 29 (GPIO 5)
- **Power (+)** → Pin 2 or 4 (5V)
- **Ground (-)** → Pin 6, 9, 14, 20, 25, 30, 34, or 39 (GND)

*Note: Laser control is active LOW (GPIO LOW = laser ON)*

### Eyes Control Connection
- **Control Signal** → Pin 16 (GPIO 23)
- **Power (+)** → Pin 2 or 4 (5V) or 3.3V depending on LED requirements
- **Ground (-)** → Pin 6, 9, 14, 20, 25, 30, 34, or 39 (GND)

*Note: Simplified to digital on/off control. For PWM brightness control, use a PWM-capable pin or external PWM controller.*

## Power Distribution

### Recommended Power Setup
```
Jetson 5V Rail (Pin 2/4)
    ├── H-Servo Power (Red wire)
    ├── V-Servo Power (Red wire) 
    ├── Head Servo Power (Red wire)
    ├── Laser Module Power
    └── Eyes LEDs Power (if 5V rated)

Jetson GND (Multiple pins)
    ├── H-Servo Ground (Brown/Black wire)
    ├── V-Servo Ground (Brown/Black wire)
    ├── Head Servo Ground (Brown/Black wire)
    ├── Laser Module Ground
    └── Eyes LEDs Ground
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