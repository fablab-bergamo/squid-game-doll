#!/usr/bin/env python3
"""
Direct TensorRT Export Script for Jetson Orin

This script exports YOLO models to TensorRT engine format using system-installed TensorRT
without requiring pip installation of tensorrt package.
"""

import os
import sys
import torch
from pathlib import Path

def export_to_tensorrt(model_path: str, engine_path: str = None, imgsz: int = 640, half: bool = True, workspace: int = 4):
    """Export YOLO model to TensorRT engine format"""
    
    # Add system paths for TensorRT
    sys.path.append('/usr/lib/python3/dist-packages')
    sys.path.append('/usr/local/lib/python3.10/dist-packages')
    
    try:
        import tensorrt as trt
        print(f"✅ TensorRT {trt.__version__} available")
        
        from ultralytics import YOLO
        print(f"🚀 Loading model: {model_path}")
        
        # Load model
        model = YOLO(model_path)
        
        # Generate engine path if not provided
        if engine_path is None:
            base_name = os.path.splitext(model_path)[0]
            engine_path = f"{base_name}.engine"
        
        print(f"📦 Exporting to TensorRT engine (half={half}, workspace={workspace}GB)")
        
        # Custom export with system TensorRT
        success = False
        try:
            # First try the export method with device specification
            exported_path = model.export(
                format="engine",
                imgsz=imgsz,
                half=half,
                int8=False,
                dynamic=False,
                workspace=workspace,
                device=0,  # Use GPU device 0
                verbose=True,
                batch=1,   # Static batch size
            )
            success = True
            engine_path = exported_path
            
        except Exception as export_error:
            print(f"⚠️  Standard export failed: {export_error}")
            print("🔄 Trying alternative export method...")
            
            # Alternative: Export to ONNX first, then use trtexec
            try:
                onnx_path = f"{os.path.splitext(model_path)[0]}.onnx"
                print(f"📄 Exporting to ONNX: {onnx_path}")
                
                model.export(format="onnx", imgsz=imgsz, dynamic=False, verbose=True)
                
                # Use trtexec command line tool
                workspace_mb = workspace * 1024  # Convert GB to MB
                precision_flag = "--fp16" if half else ""
                
                cmd = f"/usr/src/tensorrt/bin/trtexec --onnx={onnx_path} --saveEngine={engine_path} --memPoolSize=workspace:{workspace_mb} {precision_flag} --verbose"
                print(f"🛠️  Running: {cmd}")
                
                result = os.system(cmd)
                if result == 0:
                    success = True
                    print(f"✅ TensorRT engine created via trtexec: {engine_path}")
                else:
                    print(f"❌ trtexec failed with exit code: {result}")
                    
            except Exception as alt_error:
                print(f"❌ Alternative export failed: {alt_error}")
        
        if success and os.path.exists(engine_path):
            engine_size = os.path.getsize(engine_path) / (1024 * 1024)  # MB
            print(f"🎉 TensorRT export successful!")
            print(f"📁 Engine file: {engine_path}")
            print(f"📏 Engine size: {engine_size:.1f} MB")
            return engine_path
        else:
            print("❌ TensorRT export failed - engine file not created")
            return None
            
    except ImportError as e:
        print(f"❌ TensorRT import failed: {e}")
        print("💡 Make sure TensorRT is installed on your system")
        return None
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Export YOLO model to TensorRT engine")
    parser.add_argument("model", help="Path to YOLO model (.pt)")
    parser.add_argument("--output", help="Output engine path (optional)")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--fp32", action="store_true", help="Use FP32 instead of FP16")
    parser.add_argument("--workspace", type=int, default=4, help="Workspace size in GB")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.model):
        print(f"❌ Model file not found: {args.model}")
        sys.exit(1)
    
    half = not args.fp32
    engine_path = export_to_tensorrt(
        args.model, 
        args.output, 
        args.imgsz, 
        half, 
        args.workspace
    )
    
    if engine_path:
        print(f"✅ Success! TensorRT engine: {engine_path}")
        sys.exit(0)
    else:
        print("❌ Export failed")
        sys.exit(1)

if __name__ == "__main__":
    main()