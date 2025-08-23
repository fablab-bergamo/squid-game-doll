#!/usr/bin/env python3
"""
Jetson Orin Optimization Script for Squid Game Doll

This script optimizes YOLO models for Jetson Orin by:
1. Converting models to TensorRT format
2. Setting optimal system performance settings
3. Validating the optimized setup

Usage:
    python optimize_for_jetson.py [--model MODEL_PATH] [--int8] [--imgsz SIZE]
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from loguru import logger

def is_jetson_orin():
    """Check if running on Jetson Orin"""
    try:
        return (platform.machine() == "aarch64" and 
               os.path.exists("/etc/nv_tegra_release"))
    except:
        return False

def set_jetson_max_performance():
    """Set Jetson to maximum performance mode"""
    if not is_jetson_orin():
        logger.warning("Not running on Jetson Orin, skipping performance settings")
        return
    
    try:
        # Set max power mode
        logger.info("Setting Jetson to max power mode...")
        subprocess.run(["sudo", "nvpmodel", "-m", "0"], check=True)
        
        # Enable jetson clocks
        logger.info("Enabling jetson clocks...")
        subprocess.run(["sudo", "jetson_clocks"], check=True)
        
        logger.info("Jetson performance optimizations applied successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set Jetson performance settings: {e}")
    except FileNotFoundError:
        logger.error("Jetson utilities not found. Make sure you're running on a Jetson device.")

def convert_to_tensorrt(model_path: str, imgsz: int = 640, half: bool = True, int8: bool = False):
    """Convert YOLO model to TensorRT format"""
    try:
        # Add system paths to access TensorRT on Jetson
        if is_jetson_orin():
            import sys
            sys.path.append('/usr/lib/python3/dist-packages')
            sys.path.append('/usr/local/lib/python3.10/dist-packages')
        
        from ultralytics import YOLO
        
        logger.info(f"Loading model: {model_path}")
        model = YOLO(model_path)
        
        # Check if TensorRT is available before attempting export
        try:
            import tensorrt
            logger.info(f"TensorRT version: {tensorrt.__version__}")
        except ImportError:
            logger.warning("TensorRT not available - falling back to ONNX export")
            # Export to ONNX instead as fallback
            exported_path = model.export(
                format="onnx",
                imgsz=imgsz,
                half=half,
                dynamic=False,
                verbose=True
            )
            logger.info(f"ONNX export completed: {exported_path}")
            return exported_path
        
        # Export to TensorRT
        logger.info(f"Converting to TensorRT (imgsz={imgsz}, half={half}, int8={int8})")
        exported_path = model.export(
            format="engine",
            imgsz=imgsz,
            half=half,
            int8=int8,
            dynamic=False,  # Static shapes for better performance
            workspace=4,    # 4GB workspace limit for Jetson Nano
            verbose=True
        )
        
        logger.info(f"TensorRT conversion completed: {exported_path}")
        return exported_path
        
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Model conversion failed: {e}")
        return None

def download_optimal_model():
    """Download optimal YOLO model for Jetson Nano"""
    try:
        from ultralytics import YOLO
        
        model_name = "yolo11n.pt"  # Nano model for best performance
        logger.info(f"Downloading optimal model: {model_name}")
        
        model:YOLO = YOLO(model_name, verbose=True)
        model_path = Path(model_name).resolve()
        
        logger.info(f"Model downloaded to: {model_path}")
        return str(model_path)
        
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        return None

def validate_setup():
    """Validate the optimized setup"""
    logger.info("Validating setup...")
    
    # Check if TensorRT is available
    try:
        # Add system paths for Jetson
        if is_jetson_orin():
            import sys
            sys.path.append('/usr/lib/python3/dist-packages')
            sys.path.append('/usr/local/lib/python3.10/dist-packages')
        
        import tensorrt
        logger.info(f"TensorRT version: {tensorrt.__version__}")
    except ImportError:
        if is_jetson_orin():
            logger.warning("TensorRT not accessible in virtual environment - will fall back to ONNX")
        else:
            logger.warning("TensorRT not available - models will run on PyTorch")
    
    # Check if CUDA is available
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            logger.warning("CUDA not available - using CPU")
    except ImportError:
        logger.error("PyTorch not installed")
    
    # Check if running on Jetson
    if is_jetson_orin():
        logger.info("Running on Jetson Orin - optimizations will be applied")
        
        # Check Jetson stats if available
        try:
            result = subprocess.run(["jtop", "--json"], capture_output=True, text=True, timeout=5)
            logger.info("Jetson stats available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.info("Install jetson-stats for monitoring: sudo pip install jetson-stats")
    else:
        logger.info("Not running on Jetson Orin")

def main():
    parser = argparse.ArgumentParser(description="Optimize YOLO models for Jetson Orin")
    parser.add_argument("--model", type=str, default="", 
                       help="Path to YOLO model (default: download yolo11n.pt)")
    parser.add_argument("--imgsz", type=int, default=640,
                       help="Input image size (default: 640)")
    parser.add_argument("--int8", action="store_true",
                       help="Use INT8 quantization (fastest but may reduce accuracy)")
    parser.add_argument("--no-performance", action="store_true",
                       help="Skip Jetson performance optimizations")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate setup, don't perform optimizations")
    
    args = parser.parse_args()
    
    logger.add("jetson_optimization.log", rotation="1 MB")
    logger.info("Starting Jetson Orin optimization for Squid Game Doll")
    
    if args.validate_only:
        validate_setup()
        return
    
    # Set Jetson performance if requested and available
    if not args.no_performance and is_jetson_orin():
        set_jetson_max_performance()
    
    # Download model if not specified
    model_path = args.model
    if not model_path:
        model_path = download_optimal_model()
        if not model_path:
            logger.error("Failed to get model")
            sys.exit(1)
    
    # Validate model path
    if not os.path.exists(model_path):
        logger.error(f"Model not found: {model_path}")
        sys.exit(1)
    
    # Convert to TensorRT
    tensorrt_path = convert_to_tensorrt(
        model_path, 
        imgsz=args.imgsz, 
        half=True, 
        int8=args.int8
    )
    
    if tensorrt_path:
        logger.info("Optimization completed successfully!")
        logger.info(f"Optimized model: {tensorrt_path}")
        logger.info("The game will automatically use the TensorRT model when running on Jetson Orin")
    else:
        logger.error("Optimization failed")
        sys.exit(1)
    
    # Validate the final setup
    validate_setup()

if __name__ == "__main__":
    main()