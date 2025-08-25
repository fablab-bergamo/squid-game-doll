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

| Component | Board Pin | Actual Function | Notes |
|-----------|-----------|------------------|-------|
| H-Servo (Pan) | Pin 32 | GPIO13 | Horizontal laser pointer targeting |
| V-Servo (Tilt) | Pin 15 | GPIO12 | Vertical laser pointer targeting |
| Head Servo | Pin 7 | GPIO09 | Doll head rotation |
| Laser Module | Pin 30 | GPIO11 | Laser pointer on/off control |
| Eyes PWM | Pin 36 | SPI1_MOSI | Red LED brightness (repurpose SPI pin) |
| **5V Power** | 5V | Pin 2, 4 | Power Supply | Servo power rail |
| **Ground** | GND | Pin 6, 9, 14, 20, 25, 30, 34, 39 | Ground | Common ground |

## 40-Pin Header Layout Reference

⚠️ **IMPORTANT**: This pinout is for **Jetson Orin Nano**. Verify your specific model before wiring.

```
           Jetson Orin 40-Pin GPIO Header
    
    Left Side (Odd)              Right Side (Even)
    ===============              =================
     3.3V  [ 1] [ 2]  5V      ← Power Rails
  I2C1_SDA [ 3] [ 4]  5V      ← Power Rails  
  I2C1_SCL [ 5] [ 6]  GND     ← Ground
    GPIO09 [ 7] [ 8]  UART1_TX   ← Head Servo
       GND [ 9] [10]  UART1_RX
  UART1_RTS[11] [12]  I2S0_SCLK
   SPI1_SCK[13] [14]  GND     ← Ground
    GPIO12 [15] [16]  SPI1_CS1 ← V-Servo (Laser Tilt)
      3.3V [17] [18]  SPI1_CS0
  SPI0_MOSI[19] [20]  GND     ← Ground
  SPI0_MISO[21] [22]  SPI1_MISO
   SPI0_SCK[23] [24]  SPI0_CS0
       GND [25] [26]  SPI0_CS1
  I2C0_SDA [27] [28]  I2C0_SCL
       GND [29] [30]  GPIO11   ← Laser Control
    GPIO07 [31] [32]  GPIO13   ← H-Servo (Laser Pan)
       GND [33] [34]  I2S0_FS
  UART1_CTS[35] [36]  SPI1_MOSI ← Eyes PWM
  I2S0_SDIN[37] [38]  GND
       GND [39] [40]  I2S0_SDOUT
```

**WARNING**: Pin assignments in code may need adjustment based on your specific Jetson model!

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
- **Signal Wire** → Pin 32 (GPIO13)
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 29, 33, 38, 39 (GND)

#### V-Axis Servo (Tilt) - Vertical Laser Pointer Movement  
- **Signal Wire** → Pin 15 (GPIO12)
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 29, 33, 38, 39 (GND)

#### Head Servo - Doll Head Rotation
- **Signal Wire** → Pin 7 (GPIO09)
- **Power Wire** → Pin 2 or 4 (5V)
- **Ground Wire** → Pin 6, 9, 14, 20, 25, 29, 33, 38, 39 (GND)

### Laser Pointer Module Connection
- **Control Signal** → Pin 30 (GPIO11)
- **Power (+)** → Pin 2 or 4 (5V)
- **Ground (-)** → Pin 6, 9, 14, 20, 25, 29, 33, 38, 39 (GND)

*Note: Laser control is active LOW (GPIO LOW = laser ON)*

### Eyes PWM Connection (Red LEDs in Doll Eyes)
- **PWM Signal** → Pin 36 (SPI1_MOSI repurposed as GPIO)
- **Power (+)** → Pin 2 or 4 (5V) or 3.3V depending on LED requirements
- **Ground (-)** → Pin 6, 9, 14, 20, 25, 29, 33, 38, 39 (GND)

*Note: Software PWM using repurposed SPI pin for brightness control.*

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