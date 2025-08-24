#!/usr/bin/env python3
"""
YOLOE-11L-PF Laser Dot Detection Test Script

This script tests the YOLOE-11L-PF model for detecting red laser dots
in images from the pictures folder. It processes all laser*.* files
and saves annotated outputs with detection results.

Author: Generated for Squid Game Doll Project
"""

import os
import glob
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Ultralytics not available: {e}")
    YOLO_AVAILABLE = False


def main():
    """Main function to run YOLOE laser dot detection test."""
    print("YOLOE-11L Text-Prompted Red Dot Detection Test")
    print("=" * 55)
    
    # Initialize paths and settings
    pictures_dir = Path("pictures")
    if not pictures_dir.exists():
        print(f"Error: Pictures directory '{pictures_dir}' not found!")
        return
        
    # Find all laser image files
    laser_files = find_laser_images(pictures_dir)
    if not laser_files:
        print("No laser*.* files found in pictures directory!")
        return
        
    print(f"Found {len(laser_files)} laser images to process:")
    for file in laser_files:
        print(f"  - {file.name}")
    print()
    
    # Initialize model
    print("Initializing YOLOE-11L-PF model...")
    model = initialize_yoloe_model()
    if model is None:
        print("Failed to initialize YOLOE model. Exiting.")
        return
    
    # Process each image
    results = []
    for image_path in laser_files:
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


def initialize_yoloe_model():
    """Initialize YOLOE-11L model with text prompting capability."""
    if not YOLO_AVAILABLE:
        print("Error: Ultralytics not available. Please install with:")
        print("  poetry run pip install ultralytics")
        return None
        
    try:
        # Try to load YOLOE-11L model (supports text prompts)
        # The model will be automatically downloaded if not present
        print("Loading YOLOE-11L model with text prompting capability...")
        model = YOLO("yoloe-v8l-seg.pt")  # Text-promptable model (not prompt-free)
        print(f"Model loaded successfully!")
        print("This model supports text prompts for specific object detection")
        return model
        
    except Exception as e:
        print(f"Error loading YOLOE model: {e}")
        return None


def find_laser_images(pictures_dir: Path) -> List[Path]:
    """Find all laser*.* image files in the pictures directory."""
    patterns = ["laser*.jpg", "laser*.jpeg", "laser*.png"]
    laser_files = []
    
    for pattern in patterns:
        files = list(pictures_dir.glob(pattern))
        laser_files.extend(files)
        
    return sorted(laser_files)


def process_image(image_path: Path, model) -> Dict[str, Any]:
    """Process a single image with YOLOE model."""
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
        # Run YOLOE inference with text prompts for red dots
        print(f"    Running YOLOE inference on {original_shape[1]}x{original_shape[0]} image...")
        
        # Try different text prompts for red dots/laser detection
        text_prompts = [
            "red dot",
            "human",
            "red cross"
        ]
        model.set_classes(text_prompts, model.get_text_pe(text_prompts))
        all_detections = []
        
        # Try each prompt and collect results
        for prompt in text_prompts:
            try:
                results = model.predict(
                    source=str(image_path),
                    conf=0.03,    # Very low confidence to catch small/dim objects
                    iou=0.4,      # Lower IoU for overlapping detections
                    verbose=True
                )
                
                if results and len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes.cpu().numpy()
                    if len(boxes.data) > 0:
                        print(f"      Found {len(boxes.data)} detections with prompt: '{prompt}'")
                        for box in boxes.data:
                            x1, y1, x2, y2, conf, class_id = box
                            # Get actual class name from model
                            actual_class_name = results[0].names[int(class_id)]
                            detection = {
                                'bbox': [float(x1), float(y1), float(x2), float(y2)],
                                'confidence': float(conf),
                                'class_id': int(class_id),
                                'class_name': actual_class_name,  # Use actual class name from model
                                'center': [float((x1 + x2) / 2), float((y1 + y2) / 2)],
                                'prompt': prompt
                            }
                            all_detections.append(detection)
                            
            except Exception as prompt_error:
                print(f"      Prompt '{prompt}' failed: {prompt_error}")
                continue
        
        # Process detection results
        detections = all_detections.copy() if all_detections else []
        output_image = image.copy()
        
        # If we used text prompts and got results, use those
        if all_detections:
            print(f"      Total detections from text prompts: {len(all_detections)}")
            sorted_detections = sorted(all_detections, key=lambda d: d['confidence'])
            for detection in sorted_detections:
                x1, y1, x2, y2 = detection['bbox']
                conf = detection['confidence']
                class_name = detection['class_name']
                
                # Draw bounding box (use red color for laser dot detections)
                cv2.rectangle(output_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                # Draw label
                label = f"{class_name}: {conf:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(output_image, (int(x1), int(y1) - label_size[1] - 10), 
                            (int(x1) + label_size[0], int(y1)), (0, 255, 0), -1)
                cv2.putText(output_image, label, (int(x1), int(y1) - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                print(f"      Detected: {class_name} (conf: {conf:.3f}) at ({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})")
                
        # Generate output filename (use different suffix for prompted version)
        output_path = image_path.parent / f"prompted-output-{image_path.stem}.jpg"
        
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
            'error': f'YOLOE inference failed: {str(e)}',
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
        
        # Per-image details
        print("DETAILED RESULTS:")
        for result in successful:
            detections = result['detections']
            img_name = result['image_path'].name
            output_name = result['output_path'].name
            time_taken = result['processing_time']
            shape = result['original_shape']
            
            print(f"  {img_name} ({shape[1]}x{shape[0]}) -> {output_name}")
            print(f"    Processing time: {time_taken:.3f}s")
            print(f"    Detections: {len(detections)}")
            
            for i, detection in enumerate(detections):
                bbox = detection['bbox']
                center = detection['center']
                print(f"      #{i+1}: {detection['class_name']} (conf: {detection['confidence']:.3f})")
                print(f"           BBox: ({bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f})")
                print(f"           Center: ({center[0]:.0f}, {center[1]:.0f})")
        
    if failed:
        print("\nFAILED IMAGES:")
        for result in failed:
            print(f"  - {result['image_path'].name}: {result.get('error', 'Unknown error')}")
            
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()