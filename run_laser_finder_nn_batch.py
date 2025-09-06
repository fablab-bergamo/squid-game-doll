#!/usr/bin/env python3
"""
Batch LaserFinderNN Processing Script

This script runs LaserFinderNN on all laser*.* files in the pictures subfolder
and saves the annotated output images with prefix "laser-finder-".

Usage:
    python run_laser_finder_nn_batch.py
"""

import cv2
import sys
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from squid_game_doll.laser_finder_nn import LaserFinderNN


def find_laser_images(pictures_dir: Path = Path("pictures")) -> List[Path]:
    """Find all laser*.* image files in the pictures directory."""
    if not pictures_dir.exists():
        print(f"Error: Pictures directory '{pictures_dir}' not found!")
        return []
    
    # Find all laser*.* files
    patterns = ["laser*.*"]
    image_files = []
    
    for pattern in patterns:
        image_files.extend(pictures_dir.glob(pattern))
    
    # Filter for common image extensions
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    image_files = [f for f in image_files if f.suffix.lower() in valid_extensions]
    
    return sorted(image_files)


def process_single_image(laser_finder: LaserFinderNN, image_path: Path) -> Dict[str, Any]:
    """Process a single image with LaserFinderNN."""
    start_time = time.time()
    
    print(f"Processing {image_path.name}...", end=" ")
    
    # Load image
    image = cv2.imread(str(image_path))
    if image is None:
        print("❌ Failed to load")
        return {
            'image_path': image_path,
            'success': False,
            'error': 'Failed to load image',
            'processing_time': time.time() - start_time
        }
    
    try:
        # Run laser detection
        laser_coord, output_image = laser_finder.find_laser(image)
        processing_time = time.time() - start_time
        
        # Generate output filename
        output_filename = f"laser-finder-{image_path.name}"
        output_path = image_path.parent / output_filename
        
        if laser_finder.laser_found():
            print(f"✅ Found at {laser_coord} ({processing_time:.3f}s)")
            
            # Save annotated output image
            if output_image is not None:
                cv2.imwrite(str(output_path), output_image)
            else:
                # If no output image, save original with detection info
                annotated_image = image.copy()
                if laser_coord:
                    cv2.circle(annotated_image, laser_coord, 10, (0, 255, 0), 3)
                    cv2.putText(annotated_image, f"Laser: {laser_coord}", 
                              (laser_coord[0] + 15, laser_coord[1] - 15),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imwrite(str(output_path), annotated_image)
            
            # Get detection details
            detections = laser_finder.get_all_detections()
            strategy = laser_finder.get_winning_strategy()
            
            return {
                'image_path': image_path,
                'output_path': output_path,
                'success': True,
                'laser_coord': laser_coord,
                'detections': detections,
                'strategy': strategy,
                'processing_time': processing_time
            }
        else:
            print(f"❌ No laser found ({processing_time:.3f}s)")
            
            # Still save the processed image (might have some annotations)
            if output_image is not None:
                cv2.imwrite(str(output_path), output_image)
            else:
                # Save original with "No laser found" annotation
                annotated_image = image.copy()
                cv2.putText(annotated_image, "No laser detected", (20, 40),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                cv2.imwrite(str(output_path), annotated_image)
            
            return {
                'image_path': image_path,
                'output_path': output_path,
                'success': True,
                'laser_coord': None,
                'detections': [],
                'strategy': "",
                'processing_time': processing_time
            }
    
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Error: {e} ({processing_time:.3f}s)")
        
        return {
            'image_path': image_path,
            'success': False,
            'error': str(e),
            'processing_time': processing_time
        }


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print processing summary and statistics."""
    print("\n" + "=" * 70)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    detections_found = [r for r in successful if r.get('laser_coord') is not None]
    no_detections = [r for r in successful if r.get('laser_coord') is None]
    
    print(f"Total images processed: {len(results)}")
    print(f"Successful processing: {len(successful)}")
    print(f"Failed processing: {len(failed)}")
    print(f"Laser detections found: {len(detections_found)}")
    print(f"No detections: {len(no_detections)}")
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
    
    if detections_found:
        print("SUCCESSFUL DETECTIONS:")
        for result in detections_found:
            coord = result['laser_coord']
            detections = result.get('detections', [])
            best_conf = max(detections, key=lambda d: d['confidence'])['confidence'] if detections else 0
            print(f"  {result['image_path'].name}: {coord} (conf: {best_conf:.3f})")
        print()
    
    if failed:
        print("FAILED IMAGES:")
        for result in failed:
            print(f"  {result['image_path'].name}: {result.get('error', 'Unknown error')}")
        print()
    
    print("Output images saved with prefix 'laser-finder-' in pictures/ folder")
    print("\nExample output files:")
    output_files = sorted(Path("pictures").glob("laser-finder-*"))[:5]
    for file in output_files:
        print(f"  - {file.name}")
    if len(output_files) >= 5:
        print(f"  ... and {len(output_files) - 5} more files")


def main():
    """Main function to run batch LaserFinderNN processing."""
    print("Batch LaserFinderNN Processing Script")
    print("=" * 50)
    
    # Find all laser images
    pictures_dir = Path("pictures")
    image_files = find_laser_images(pictures_dir)
    
    if not image_files:
        print(f"No laser*.* image files found in '{pictures_dir}' directory!")
        print("Make sure you have laser image files like:")
        print("  - laser-1.jpg")
        print("  - laser-2.png")
        print("  - laser-test.jpeg")
        return
    
    print(f"Found {len(image_files)} laser images to process:")
    for file in image_files:
        print(f"  - {file.name}")
    print()
    
    # Initialize LaserFinderNN
    print("Initializing LaserFinderNN...")
    try:
        laser_finder = LaserFinderNN()
        print("✅ LaserFinderNN initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LaserFinderNN: {e}")
        return
    
    print()
    
    # Process all images
    results = []
    start_time = time.time()
    
    for image_path in image_files:
        result = process_single_image(laser_finder, image_path)
        results.append(result)
    
    total_time = time.time() - start_time
    
    # Print summary
    print(f"\nBatch processing completed in {total_time:.3f} seconds")
    print_summary(results)


if __name__ == "__main__":
    main()