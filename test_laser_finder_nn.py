#!/usr/bin/env python3
"""
LaserFinderNN Test Script

This script tests the LaserFinderNN class with a fixed image to verify it works correctly.

Usage:
    python test_laser_finder_nn.py
"""

import cv2
import sys
from pathlib import Path
import time

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from squid_game_doll.laser_finder_nn import LaserFinderNN


def main():
    """Test LaserFinderNN with a fixed image"""
    print("LaserFinderNN Test Script")
    print("=" * 40)
    
    # Choose a test image
    test_image_path = Path("pictures/laser-1.jpg")
    
    if not test_image_path.exists():
        print(f"Error: Test image '{test_image_path}' not found!")
        print("Available laser images in pictures/:")
        laser_images = list(Path("pictures").glob("laser-*.jpg"))
        laser_images.extend(Path("pictures").glob("laser-*.png"))
        for img in sorted(laser_images)[:5]:  # Show first 5
            print(f"  - {img.name}")
        if laser_images:
            test_image_path = laser_images[0]
            print(f"Using: {test_image_path}")
        else:
            print("No laser images found!")
            return
    
    print(f"Test image: {test_image_path}")
    print()
    
    # Initialize LaserFinderNN
    print("Initializing LaserFinderNN...")
    laser_finder = LaserFinderNN()
    
    # Load test image
    print(f"Loading image: {test_image_path}")
    image = cv2.imread(str(test_image_path))
    
    if image is None:
        print("Error: Failed to load image!")
        return
    
    print(f"Image shape: {image.shape}")
    print()
    
    # Test laser detection
    print("Running laser detection...")
    start_time = time.time()
    
    laser_coord, output_image = laser_finder.find_laser(image)
    
    detection_time = time.time() - start_time
    print(f"Detection time: {detection_time:.3f} seconds")
    print()
    
    # Show results
    if laser_finder.laser_found():
        print("✅ Laser found!")
        print(f"Coordinates: {laser_coord}")
        print(f"Strategy: {laser_finder.get_winning_strategy()}")
        print()
        
        # Get additional information
        all_detections = laser_finder.get_all_detections()
        print(f"Total detections: {len(all_detections)}")
        
        for i, detection in enumerate(all_detections):
            print(f"  Detection {i+1}: {detection['class_name']} "
                  f"(conf: {detection['confidence']:.3f}) "
                  f"at {detection['center']}")
        
        # Save output image if available
        if output_image is not None:
            output_path = test_image_path.parent / f"test_nn_output_{test_image_path.name}"
            cv2.imwrite(str(output_path), output_image)
            print(f"Output image saved: {output_path}")
    else:
        print("❌ No laser found in the image")
    
    print("\nTest completed!")


if __name__ == "__main__":
    main()