"""
Platform detection utilities for the Squid Game Doll project.

This module provides cross-platform detection functions to optimize
performance and select appropriate models for different hardware.
"""

import os
import platform
from loguru import logger


def is_jetson_orin() -> bool:
    """
    Check if running on NVIDIA Jetson Nano.
    
    Returns:
        bool: True if running on Jetson Nano, False otherwise
    """
    try:
        return (platform.machine() == "aarch64" and 
               os.path.exists("/etc/nv_tegra_release"))
    except Exception as e:
        logger.debug(f"Jetson Nano detection failed: {e}")
        return False


def is_raspberry_pi() -> bool:
    """
    Check if running on Raspberry Pi.
    
    Returns:
        bool: True if running on Raspberry Pi, False otherwise
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read().lower()
            return 'raspberry' in cpuinfo or 'bcm' in cpuinfo
    except Exception as e:
        logger.debug(f"Raspberry Pi detection failed: {e}")
        return False


def get_platform_info() -> str:
    """
    Get human-readable platform information.
    
    Returns:
        str: Platform description string
    """
    if is_jetson_orin():
        return "NVIDIA Jetson Orin"
    elif is_raspberry_pi():
        return "Raspberry Pi"
    elif platform.system() == "Linux":
        return f"Linux ({platform.machine()})"
    elif platform.system() == "Windows":
        return f"Windows ({platform.machine()})"
    elif platform.system() == "Darwin":
        return f"macOS ({platform.machine()})"
    else:
        return f"{platform.system()} ({platform.machine()})"


def get_optimal_model_for_platform() -> str:
    """
    Get the optimal YOLO model for the current platform.
    
    Returns:
        str: Model filename optimized for current hardware
    """
    if is_jetson_orin():
        # Use nano model for Jetson Nano for best speed/accuracy balance
        return "yolo11n.pt"
    elif is_raspberry_pi():
        # Raspberry Pi will use Hailo models, but fallback to nano for Ultralytics
        return "yolo11n.pt"
    else:
        # Use small model for PC/other platforms (good balance)
        return "yolo11s.pt"


def should_use_hailo() -> bool:
    """
    Determine if Hailo AI acceleration should be used.
    
    Returns:
        bool: True if Hailo should be used, False otherwise
    """
    return platform.system() == "Linux" and is_raspberry_pi()


def should_use_tensorrt() -> bool:
    """
    Determine if TensorRT optimization should be used.
    
    Returns:
        bool: True if TensorRT should be used, False otherwise
    """
    return is_jetson_orin()


def get_optimal_input_size() -> int:
    """
    Get optimal neural network input size for current platform.
    
    Returns:
        int: Optimal input size in pixels
    """
    # All platforms now use standard 640px resolution
    return 640


def get_optimal_thread_count() -> int:
    """
    Get optimal thread count for current platform.
    
    Returns:
        int: Number of threads to use
    """
    if is_jetson_orin():
        # ARM processors typically work well with 4 threads
        return 4
    elif is_raspberry_pi():
        # Raspberry Pi usually has 4 cores
        return 4
    else:
        # Let the system decide for other platforms
        return os.cpu_count() or 4