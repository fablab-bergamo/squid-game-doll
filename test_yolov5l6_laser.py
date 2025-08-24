#!/usr/bin/env python3
"""
YOLOv5l6 Laser Detection Test Script

This script loads the YOLOv5l6 PyTorch model and runs detection
on images in a specified directory, generating annotated output images.

Usage:
    python test_yolov5l6_laser.py --dir pictures --pattern "laser*.png"
    python test_yolov5l6_laser.py -d "C:\Temp\LAser\Data\TestSet\TestData" -p "*.jpg"

Author: Generated for Squid Game Doll Project
"""

import argparse
import glob
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PyTorch not available: {e}")
    TORCH_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Ultralytics not available: {e}")
    YOLO_AVAILABLE = False

# Try to import original YOLOv5 for legacy model support
YOLOV5_AVAILABLE = False
try:
    import yolov5
    YOLOV5_AVAILABLE = True
except ImportError:
    try:
        import torch.hub
        YOLOV5_AVAILABLE = True
    except ImportError:
        pass


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="YOLOv5l6 Custom Laser Model Detection Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_yolov5l6_laser.py --dir pictures --pattern "laser*.png"
  python test_yolov5l6_laser.py -d "C:\\Temp\\LAser\\Data\\TestSet\\TestData" -p "*.jpg"
  python test_yolov5l6_laser.py -d pictures -p "*.png"
        """
    )
    
    parser.add_argument(
        '-d', '--dir', '--directory',
        type=str,
        default='pictures',
        help='Directory containing images to process (default: pictures)'
    )
    
    parser.add_argument(
        '-p', '--pattern',
        type=str,
        default='laser*.*',
        help='File pattern to match (default: laser*.*)'
    )
    
    return parser.parse_args()


def main():
    """Main function to run YOLOv5l6 detection test."""
    args = parse_arguments()
    
    print("YOLOv5l6 Custom Laser Model Detection Test (IoU=0.01)")
    print("=" * 55)
    print(f"Directory: {args.dir}")
    print(f"Pattern: {args.pattern}")
    print()
    
    # Initialize paths and settings
    images_dir = Path(args.dir)
    if not images_dir.exists():
        print(f"Error: Directory '{images_dir}' not found!")
        return
        
    # Find all image files matching the pattern
    image_files = find_images_by_pattern(images_dir, args.pattern)
    if not image_files:
        print(f"No files matching '{args.pattern}' found in directory '{images_dir}'!")
        return
        
    print(f"Found {len(image_files)} images to process:")
    for file in image_files:
        print(f"  - {file.name}")
    print()
    
    # Initialize model
    print("Initializing YOLOv5l6 model...")
    model = initialize_yolov5l6_model()
    if model is None:
        print("Failed to initialize YOLOv5l6 model. Exiting.")
        return
    
    # Process each image
    results = []
    for image_path in image_files:
        print(f"Processing {image_path.name}...")
        result = process_image(image_path, model)
        results.append(result)
        if result.get('success', False):
            print(f"  -> Saved: {result['output_path']}")
            print(f"  -> Found {len(result['detections'])} detections")
        else:
            print(f"  -> Failed: {result.get('error', 'Unknown error')}")
        
    # Print summary
    print_summary(results)


def initialize_yolov5l6_model():
    """Initialize YOLOv5l6 custom trained model using torch.hub."""
    if not TORCH_AVAILABLE:
        print("Error: PyTorch not available. Please install with:")
        print("  poetry run pip install torch torchvision")
        return None
        
    try:
        # Load custom trained YOLOv5l6 model for laser detection
        model_path = "yolov5l6_e200_b8_tvt302010_laser_v5.pt"
        print(f"Loading custom YOLOv5l6 model: {model_path}")
        
        if not Path(model_path).exists():
            print(f"Error: Model file '{model_path}' not found!")
            print("Please ensure the model file is in the current directory.")
            return None
        
        # Use torch.hub to load YOLOv5 model (compatible with original YOLOv5 format)
        print("Loading model via torch.hub...")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        
        # Load YOLOv5 model using torch.hub for proper compatibility
        if device == 'cuda':
            model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                 path=model_path, force_reload=True)
            model.to("cuda")
        else:
            model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                 path=model_path, force_reload=True,
                                 map_location=torch.device('cpu'))
        
        model.eval()
        print(f"Model loaded successfully!")
        
        # Print model info
        print(f"Model device: {device}")
        print(f"Model classes: {len(model.names)} classes")
        print(f"Model class names: {list(model.names.values())}")
        print("Custom trained model for laser detection")
        return model
        
    except Exception as e:
        print(f"Error loading custom YOLOv5l6 model: {e}")
        return None


def find_images_by_pattern(images_dir: Path, pattern: str) -> List[Path]:
    """Find all image files matching the given pattern in the directory."""
    image_files = list(images_dir.glob(pattern))
    return sorted(image_files)


def process_image(image_path: Path, model) -> Dict[str, Any]:
    """Process a single image with YOLOv5l6 model."""
    start_time = time.time()
    
    # Load image
    image = cv2.imread(str(image_path))
    if image is None:
        return {
            'image_path': image_path,
            'success': False,
            'error': 'Failed to load image',
            'processing_time': time.time() - start_time
        }
    
    original_shape = image.shape[:2]  # (height, width)
    
    try:
        # Run YOLOv5l6 inference using torch.hub model
        print(f"    Running YOLOv5l6 inference on {original_shape[1]}x{original_shape[0]} image...")
        
        # Run inference with the torch.hub model using IoU=0.01 as per research paper
        # Set model parameters for laser detection optimization
        model.conf = 0.10  # confidence threshold
        model.iou = 0.01   # IoU threshold as per https://www.sciencedirect.com/science/article/pii/S092188902500140X
        
        results = model(image)
        
        detections = []
        output_image = image.copy()
        
        # Process results from torch.hub YOLOv5 model
        if results.xyxy[0] is not None and len(results.xyxy[0]) > 0:
            predictions = results.xyxy[0].cpu().numpy()  # xyxy format
            print(f"      Found {len(predictions)} detections")
            
            for pred in predictions:
                x1, y1, x2, y2, conf, class_id = pred
                class_name = model.names[int(class_id)]
                
                detection = {
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'confidence': float(conf),
                    'class_id': int(class_id),
                    'class_name': class_name,
                    'center': [float((x1 + x2) / 2), float((y1 + y2) / 2)]
                }
                detections.append(detection)
                
                # Draw bounding box
                cv2.rectangle(output_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                # Draw label
                label = f"{class_name}: {conf:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(output_image, (int(x1), int(y1) - label_size[1] - 10), 
                            (int(x1) + label_size[0], int(y1)), (0, 255, 0), -1)
                cv2.putText(output_image, label, (int(x1), int(y1) - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                print(f"      Detected: {class_name} (conf: {conf:.3f}) at ({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})")
        else:
            print("      No detections found")
                
        # Generate output filename in the same directory
        output_path = image_path.parent / f"yolov5l6-laser-output-{image_path.stem}.jpg"
        
        # Save output image
        cv2.imwrite(str(output_path), output_image)
        
        processing_time = time.time() - start_time
        
        return {
            'image_path': image_path,
            'output_path': output_path,
            'original_shape': original_shape,
            'detections': detections,
            'processing_time': processing_time,
            'success': True
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        return {
            'image_path': image_path,
            'success': False,
            'error': f'YOLOv5l6 inference failed: {str(e)}',
            'processing_time': processing_time
        }


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print processing summary and statistics."""
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    print(f"Total images processed: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print()
    
    if successful:
        # Processing time statistics
        times = [r['processing_time'] for r in successful]
        avg_time = np.mean(times)
        min_time = np.min(times)
        max_time = np.max(times)
        total_time = np.sum(times)
        
        print("PERFORMANCE METRICS:")
        print(f"  Total processing time: {total_time:.3f}s")
        print(f"  Average processing time: {avg_time:.3f}s")
        print(f"  Fastest image: {min_time:.3f}s")
        print(f"  Slowest image: {max_time:.3f}s")
        print()
        
        # Detection statistics
        all_detections = []
        images_with_detections = 0
        detection_counts = []
        
        for result in successful:
            detections = result['detections']
            detection_counts.append(len(detections))
            if len(detections) > 0:
                images_with_detections += 1
                all_detections.extend(detections)
        
        print("DETECTION STATISTICS:")
        print(f"  Images with detections: {images_with_detections}/{len(successful)}")
        print(f"  Total detections found: {len(all_detections)}")
        if all_detections:
            print(f"  Average detections per image: {len(all_detections)/len(successful):.2f}")
            print(f"  Max detections in single image: {max(detection_counts)}")
            
            # Class distribution
            class_counts = {}
            confidence_scores = []
            for detection in all_detections:
                class_name = detection['class_name']
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
                confidence_scores.append(detection['confidence'])
            
            print(f"  Average confidence: {np.mean(confidence_scores):.3f}")
            print(f"  Confidence range: {np.min(confidence_scores):.3f} - {np.max(confidence_scores):.3f}")
            print()
            
            print("DETECTED CLASSES:")
            for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {class_name}: {count} detections")
        print()

if __name__ == "__main__":
    main()