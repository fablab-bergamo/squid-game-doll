"""
Laser Controller Factory - Automatic detection and initialization
Chooses between ESP32 network control and Jetson GPIO direct control
"""
import platform
from .laser_shooter import LaserShooter

# Try to import Jetson components
try:
    from .jetson_laser_controller import JetsonLaserController
    JETSON_AVAILABLE = True
except ImportError:
    JETSON_AVAILABLE = False


def create_laser_controller(ipaddress: str = "192.168.45.50", 
                          deadband_px: int = 10, 
                          max_frequency_hz: int = 10, 
                          enable_laser: bool = True,
                          force_mode: str = None) -> object:
    """
    Factory function to create appropriate laser controller.
    
    Args:
        ipaddress (str): ESP32 IP address for network mode
        deadband_px (int): Targeting deadband in pixels
        max_frequency_hz (int): Maximum update frequency
        enable_laser (bool): Enable laser control
        force_mode (str): Force specific mode ("network", "direct", None for auto)
        
    Returns:
        LaserShooter or JetsonLaserController instance
    """
    
    # Check for forced mode
    if force_mode == "network":
        print("Laser Controller: Forced network mode (ESP32)")
        return LaserShooter(ipaddress, deadband_px, max_frequency_hz, enable_laser)
    
    if force_mode == "direct":
        if not JETSON_AVAILABLE:
            raise RuntimeError("Direct GPIO mode forced but Jetson components not available")
        print("Laser Controller: Forced direct GPIO mode (Jetson)")
        return JetsonLaserController(deadband_px, max_frequency_hz, enable_laser)
    
    # Auto-detection logic
    system_info = platform.uname()
    
    # Check if running on Jetson platform
    is_jetson = (
        "tegra" in system_info.release.lower() or
        "jetson" in system_info.node.lower() or
        "nvidia" in system_info.machine.lower()
    )
    
    # Prefer direct GPIO control on Jetson if available
    if is_jetson and JETSON_AVAILABLE:
        try:
            print("Laser Controller: Auto-detected Jetson platform with GPIO support")
            print("                  Using direct GPIO control mode")
            return JetsonLaserController(deadband_px, max_frequency_hz, enable_laser)
        except Exception as e:
            print(f"Laser Controller: Direct GPIO initialization failed: {e}")
            print("                  Falling back to network mode")
    
    # Default to network mode (ESP32)
    print("Laser Controller: Using network mode (ESP32)")
    return LaserShooter(ipaddress, deadband_px, max_frequency_hz, enable_laser)


def detect_available_modes():
    """
    Detect which laser control modes are available.
    
    Returns:
        dict: Available modes with status
    """
    modes = {
        "network": True,  # Always available (LaserShooter)
        "direct": JETSON_AVAILABLE
    }
    
    system_info = platform.uname()
    is_jetson = (
        "tegra" in system_info.release.lower() or
        "jetson" in system_info.node.lower() or
        "nvidia" in system_info.machine.lower()
    )
    
    return {
        "available_modes": modes,
        "recommended": "direct" if (is_jetson and JETSON_AVAILABLE) else "network",
        "platform": {
            "system": system_info.system,
            "node": system_info.node,
            "release": system_info.release,
            "machine": system_info.machine,
            "is_jetson": is_jetson
        }
    }


class LaserControllerConfig:
    """Configuration class for laser controller settings."""
    
    def __init__(self, config_dict=None):
        """Initialize with config dictionary."""
        config = config_dict or {}
        
        self.mode = config.get("mode", "auto")  # "auto", "network", "direct"
        self.ipaddress = config.get("ipaddress", "192.168.45.50")
        self.deadband_px = config.get("deadband_px", 10)
        self.max_frequency_hz = config.get("max_frequency_hz", 10)
        self.enable_laser = config.get("enable_laser", True)
    
    def create_controller(self):
        """Create controller based on configuration."""
        force_mode = None if self.mode == "auto" else self.mode
        
        return create_laser_controller(
            self.ipaddress,
            self.deadband_px,
            self.max_frequency_hz,
            self.enable_laser,
            force_mode
        )