#!/usr/bin/env python3
"""
Jetson Orin Optimization Script for Squid Game Doll

This script optimizes YOLO models for Jetson Orin by:
1. Converting models to TensorRT format (with fallback methods)
2. Setting optimal system performance settings
3. Validating the optimized setup

Usage:
    python optimize_for_jetson.py [--model MODEL_PATH] [--int8] [--imgsz SIZE]
    python optimize_for_jetson.py --export-only model.pt [--output model.engine]
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

def export_to_tensorrt(model_path: str, engine_path: str = None, imgsz: int = 640, half: bool = True, 
                      int8: bool = False, workspace: int = 4):
    """Export YOLO model to TensorRT engine format with multiple fallback methods"""
    
    # Add system paths for TensorRT
    sys.path.append('/usr/lib/python3/dist-packages')
    sys.path.append('/usr/local/lib/python3.10/dist-packages')
    
    try:
        from ultralytics import YOLO
        logger.info(f"🚀 Loading model: {model_path}")
        
        # Load model
        model = YOLO(model_path)
        
        # Generate engine path if not provided
        if engine_path is None:
            base_name = os.path.splitext(model_path)[0]
            engine_path = f"{base_name}.engine"
        
        # Check if TensorRT is available
        try:
            import tensorrt as trt
            logger.info(f"✅ TensorRT {trt.__version__} available")
            tensorrt_available = True
        except ImportError:
            logger.warning("TensorRT not available in Python environment")
            tensorrt_available = False
        
        logger.info(f"📦 Exporting to TensorRT engine (half={half}, int8={int8}, workspace={workspace}GB)")
        
        # Method 1: Direct Ultralytics export (if TensorRT available)
        if tensorrt_available:
            try:
                logger.info("🔄 Trying direct TensorRT export...")
                exported_path = model.export(
                    format="engine",
                    imgsz=imgsz,
                    half=half,
                    int8=int8,
                    dynamic=False,
                    workspace=workspace,
                    device=0,  # Use GPU device 0
                    verbose=True,
                    batch=1,   # Static batch size
                )
                
                if os.path.exists(exported_path):
                    engine_size = os.path.getsize(exported_path) / (1024 * 1024)  # MB
                    logger.info(f"🎉 Direct TensorRT export successful!")
                    logger.info(f"📁 Engine file: {exported_path}")
                    logger.info(f"📏 Engine size: {engine_size:.1f} MB")
                    return exported_path
                    
            except Exception as export_error:
                logger.warning(f"Direct TensorRT export failed: {export_error}")
        
        # Method 2: Fallback to ONNX + trtexec
        logger.info("🔄 Trying ONNX + trtexec fallback method...")
        try:
            onnx_path = f"{os.path.splitext(model_path)[0]}.onnx"
            logger.info(f"📄 Exporting to ONNX: {onnx_path}")
            
            # Export to ONNX first
            model.export(format="onnx", imgsz=imgsz, dynamic=False, verbose=True)
            
            if not os.path.exists(onnx_path):
                raise FileNotFoundError(f"ONNX export failed - file not found: {onnx_path}")
            
            # Use trtexec command line tool
            workspace_mb = workspace * 1024  # Convert GB to MB
            precision_flag = "--fp16" if half else ""
            int8_flag = "--int8" if int8 else ""
            
            cmd = f"/usr/src/tensorrt/bin/trtexec --onnx={onnx_path} --saveEngine={engine_path} --memPoolSize=workspace:{workspace_mb} {precision_flag} {int8_flag} --verbose"
            logger.info(f"🛠️  Running: {cmd}")
            
            result = os.system(cmd)
            if result == 0 and os.path.exists(engine_path):
                engine_size = os.path.getsize(engine_path) / (1024 * 1024)  # MB
                logger.info(f"✅ TensorRT engine created via trtexec: {engine_path}")
                logger.info(f"📏 Engine size: {engine_size:.1f} MB")
                return engine_path
            else:
                logger.error(f"❌ trtexec failed with exit code: {result}")
                
        except Exception as alt_error:
            logger.error(f"❌ ONNX + trtexec method failed: {alt_error}")
        
        # Method 3: Final fallback to ONNX only
        logger.info("🔄 Falling back to ONNX export only...")
        try:
            onnx_path = f"{os.path.splitext(model_path)[0]}.onnx"
            exported_path = model.export(
                format="onnx",
                imgsz=imgsz,
                half=half,
                dynamic=False,
                verbose=True
            )
            
            if os.path.exists(exported_path):
                onnx_size = os.path.getsize(exported_path) / (1024 * 1024)  # MB
                logger.info(f"✅ ONNX export successful (fallback)")
                logger.info(f"📁 ONNX file: {exported_path}")
                logger.info(f"📏 ONNX size: {onnx_size:.1f} MB")
                return exported_path
                
        except Exception as onnx_error:
            logger.error(f"❌ ONNX fallback failed: {onnx_error}")
        
        logger.error("❌ All export methods failed")
        return None
            
    except ImportError as e:
        logger.error(f"❌ Required packages not available: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        return None

def download_model(model_name):
    """Download YOLO model"""
    try:
        from ultralytics import YOLO
        
        logger.info(f"Downloading model: {model_name}")
        
        model = YOLO(model_name, verbose=True)
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
        logger.info(f"✅ TensorRT version: {tensorrt.__version__}")
    except ImportError:
        if is_jetson_orin():
            logger.warning("⚠️  TensorRT not accessible in virtual environment - will fall back to ONNX")
        else:
            logger.warning("⚠️  TensorRT not available - models will run on PyTorch")
    
    # Check if CUDA is available
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
            logger.info(f"   CUDA devices: {torch.cuda.device_count()}")
        else:
            logger.warning("⚠️  CUDA not available - using CPU")
    except ImportError:
        logger.error("❌ PyTorch not installed")
    
    # Check if running on Jetson
    if is_jetson_orin():
        logger.info("✅ Running on Jetson Orin - optimizations will be applied")
        
        # Check Jetson stats if available
        try:
            result = subprocess.run(["jtop", "--json"], capture_output=True, text=True, timeout=5)
            logger.info("✅ Jetson stats available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.info("💡 Install jetson-stats for monitoring: sudo pip install jetson-stats")
    else:
        logger.info("ℹ️  Not running on Jetson Orin")

def main():
    parser = argparse.ArgumentParser(description="Optimize YOLO models for Jetson Orin")
    parser.add_argument("model", nargs="?", type=str, default="", 
                       help="Path to YOLO model (default: download yolo11l.pt)")
    parser.add_argument("--output", type=str, help="Output engine path (for export-only mode)")
    parser.add_argument("--imgsz", type=int, default=640,
                       help="Input image size (default: 640)")
    parser.add_argument("--int8", action="store_true",
                       help="Use INT8 quantization (fastest but may reduce accuracy)")
    parser.add_argument("--fp32", action="store_true",
                       help="Use FP32 instead of FP16")
    parser.add_argument("--workspace", type=int, default=4,
                       help="Workspace size in GB (default: 4)")
    parser.add_argument("--no-performance", action="store_true",
                       help="Skip Jetson performance optimizations")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate setup, don't perform optimizations")
    parser.add_argument("--export-only", action="store_true",
                       help="Only export model, skip performance settings and validation")
    
    args = parser.parse_args()
    
    logger.add("jetson_optimization.log", rotation="1 MB")
    logger.info("Starting Jetson Orin optimization for Squid Game Doll")
    
    if args.validate_only:
        validate_setup()
        return
    
    # Export-only mode
    if args.export_only:
        if not args.model:
            logger.error("❌ Model path required for export-only mode")
            sys.exit(1)
        
        if not os.path.exists(args.model):
            logger.error(f"❌ Model file not found: {args.model}")
            sys.exit(1)
        
        half = not args.fp32
        exported_path = export_to_tensorrt(
            args.model,
            args.output,
            args.imgsz,
            half,
            args.int8,
            args.workspace
        )
        
        if exported_path:
            logger.info(f"✅ Export successful: {exported_path}")
            sys.exit(0)
        else:
            logger.error("❌ Export failed")
            sys.exit(1)
    
    # Full optimization mode
    # Set Jetson performance if requested and available
    if not args.no_performance and is_jetson_orin():
        set_jetson_max_performance()
    
    # Download model if not specified
    model_path = args.model
    if not model_path:
        try:
            model_path = input("Enter model path or name (e.g., yolo11l.pt): ").strip()
            if not model_path:
                logger.error("No model path provided")
                sys.exit(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            sys.exit(1)
        except EOFError:
            logger.error("No input available. Please specify a model path as argument.")
            sys.exit(1)
        
        # If it's just a model name, download it
        if not os.path.exists(model_path) and model_path.endswith('.pt'):
            logger.info(f"Downloading model: {model_path}")
            model_path = download_model(model_path)
            if not model_path:
                logger.error("Failed to download model")
                sys.exit(1)
    
    # Validate model path
    if not os.path.exists(model_path):
        logger.error(f"Model not found: {model_path}")
        sys.exit(1)
    
    # Convert to TensorRT
    half = not args.fp32
    tensorrt_path = export_to_tensorrt(
        model_path, 
        imgsz=args.imgsz, 
        half=half, 
        int8=args.int8,
        workspace=args.workspace
    )
    
    if tensorrt_path:
        logger.info("🎉 Optimization completed successfully!")
        logger.info(f"📁 Optimized model: {tensorrt_path}")
        logger.info("🚀 The game will automatically use the optimized model when running on Jetson Orin")
    else:
        logger.error("❌ Optimization failed")
        sys.exit(1)
    
    # Validate the final setup
    validate_setup()

if __name__ == "__main__":
    main()