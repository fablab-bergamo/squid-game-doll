from typing import Optional, Tuple
import cv2
import numpy as np
import os
import warnings
from pathlib import Path
from loguru import logger

# Suppress the specific FutureWarning about torch.cuda.amp.autocast deprecation
# This warning comes from YOLOv5 library usage of deprecated torch.cuda.amp API
warnings.filterwarnings("ignore", message=".*torch.cuda.amp.autocast.*is deprecated.*", category=FutureWarning)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from .utils.platform import (
    is_jetson_orin,
    get_platform_info,
    get_optimal_thread_count,
)

DEBUG_LASER_FIND_NN = False


class LaserFinderNN:
    """
    Neural network-based laser finder using YOLOv5 model.
    Provides similar interface to the original LaserFinder class.
    """
    
    def __init__(self, model_path: str = "yolov5l6_e200_b8_tvt302010_laser_v5.pt"):
        """
        Initializes the LaserFinderNN object.
        
        Args:
            model_path: Path to the YOLOv5 model file
        """
        self.base_model_path = model_path
        self.model = None
        self.laser_coord = None
        self.prev_detections = []
        self.confidence_threshold = 0.10
        self.iou_threshold = 0.01
        self.is_jetson = is_jetson_orin()
        
        self._load_optimized_model()

    def _find_optimal_model_format(self) -> tuple[str, str]:
        """Find the optimal model format and path"""
        # Check for optimized model formats in priority order: TensorRT > ONNX > PyTorch
        
        # Priority 1: TensorRT engine (maximum performance)
        tensorrt_path = f"{os.path.splitext(self.base_model_path)[0]}.engine"
        if os.path.exists(tensorrt_path):
            logger.info(f"✅ Found TensorRT laser model: {tensorrt_path}")
            return tensorrt_path, "TensorRT (.engine)"
        
        # Priority 2: ONNX model (good performance with GPU)
        onnx_path = f"{os.path.splitext(self.base_model_path)[0]}.onnx"
        if os.path.exists(onnx_path):
            logger.info(f"✅ Found ONNX laser model: {onnx_path}")
            return onnx_path, "ONNX (.onnx)"
        
        # Priority 3: PyTorch model (fallback)
        logger.info(f"ℹ️  Using PyTorch laser model: {self.base_model_path}")
        return self.base_model_path, "PyTorch (.pt)"
    
    def _load_optimized_model(self) -> bool:
        """Load the YOLOv5 model with optimal format detection."""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available. LaserFinderNN will not work.")
            return False
            
        try:
            # Find optimal model format
            model_path, model_format = self._find_optimal_model_format()
            
            model_file = Path(model_path)
            if not model_file.exists():
                logger.error(f"Model file '{model_path}' not found!")
                return False
            
            logger.info(f"🔍 Loading laser detection model format: {model_format}")
            logger.info(f"📁 Model path: {model_path}")
            
            # Store final model path and format
            self.model_path = model_path
            self.model_format = model_format
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            if device == 'cuda':
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                         path=self.model_path, force_reload=True)
                self.model.to("cuda")
            else:
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                         path=self.model_path, force_reload=True,
                                         map_location=torch.device('cpu'))
            
            self.model.eval()
            
            # Optimize for current platform
            if self.is_jetson:
                self._optimize_for_jetson()
            
            # Set detection thresholds
            self.model.conf = self.confidence_threshold
            self.model.iou = self.iou_threshold
            
            device_info = device
            logger.info(f"🎯 Laser detection running on: {device_info} ({get_platform_info()})")
            logger.info(f"⚡ Model format in use: {model_format}")
            logger.info(f"🔧 Model classes: {list(self.model.names.values())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading YOLOv5 laser model: {e}")
            return False

    def _optimize_for_jetson(self) -> None:
        """Apply Jetson-specific optimizations"""
        try:
            # Set optimal number of threads for current platform
            torch.set_num_threads(get_optimal_thread_count())
            
            if torch.cuda.is_available():
                self.model.to("cuda")
                logger.info("✅ Using Jetson GPU acceleration for laser detection")
            else:
                logger.warning("CUDA not available on Jetson, using CPU for laser detection")
                    
        except Exception as e:
            logger.warning(f"Jetson laser detection optimization failed: {e}")

    def laser_found(self) -> bool:
        """Check if laser was found in the last detection."""
        return self.laser_coord is not None

    def get_laser_coord(self) -> Optional[Tuple[int, int]]:
        """Get the laser coordinates from the last detection."""
        return self.laser_coord

    def get_winning_strategy(self) -> str:
        """Get information about the detection strategy used."""
        if self.laser_found():
            return f"YOLOv5_NN(conf={self.confidence_threshold}, iou={self.iou_threshold})"
        return ""

    def find_laser(self, img: cv2.UMat, rects: list = None) -> Tuple[Optional[Tuple[int, int]], Optional[cv2.UMat]]:
        """
        Find laser in the given image using YOLOv5 neural network.
        
        Args:
            img: Input image as cv2.UMat
            rects: List of exclusion rectangles (not used in NN version)
            
        Returns:
            Tuple of (laser_coordinates, output_image)
        """
        if self.model is None:
            if DEBUG_LASER_FIND_NN:
                print("Model not loaded, cannot detect laser")
            self.laser_coord = None
            return (None, None)
        
        try:
            # Convert UMat to numpy array if needed
            if isinstance(img, cv2.UMat):
                img_np = cv2.UMat.get(img)
            else:
                img_np = img
                
            if DEBUG_LASER_FIND_NN:
                print(f"Running YOLOv5 inference on image shape: {img_np.shape}")
            
            # Run inference
            results = self.model(img_np)
            
            # Process results
            detections = []
            output_image = img_np.copy()
            
            if results.xyxy[0] is not None and len(results.xyxy[0]) > 0:
                predictions = results.xyxy[0].cpu().numpy()  # xyxy format
                
                if DEBUG_LASER_FIND_NN:
                    print(f"Found {len(predictions)} detections")
                
                for pred in predictions:
                    x1, y1, x2, y2, conf, class_id = pred
                    class_name = self.model.names[int(class_id)]
                    
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    detection = {
                        'center': (center_x, center_y),
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': float(conf),
                        'class_name': class_name
                    }
                    detections.append(detection)
                    
                    # Draw bounding box
                    cv2.rectangle(output_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    
                    # Draw center point
                    cv2.circle(output_image, (center_x, center_y), 5, (0, 0, 255), -1)
                    
                    # Draw label
                    label = f"{class_name}: {conf:.2f}"
                    cv2.putText(output_image, label, (int(x1), int(y1) - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    if DEBUG_LASER_FIND_NN:
                        print(f"Detected laser: {class_name} (conf: {conf:.3f}) at center ({center_x}, {center_y})")
            
            # Select best detection (highest confidence)
            if detections:
                best_detection = max(detections, key=lambda d: d['confidence'])
                self.laser_coord = best_detection['center']
                self.prev_detections = detections
                
                # Add strategy info to output image
                cv2.putText(output_image, "YOLOv5 Neural Network", (10, 30), 
                          cv2.FONT_HERSHEY_COMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(output_image, f"Best conf: {best_detection['confidence']:.3f}", (10, 60), 
                          cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 255, 0), 1)
                
                if DEBUG_LASER_FIND_NN:
                    print(f"Selected best detection at {self.laser_coord} with confidence {best_detection['confidence']:.3f}")
                
                return (self.laser_coord, output_image)
            else:
                self.laser_coord = None
                self.prev_detections = []
                
                if DEBUG_LASER_FIND_NN:
                    print("No laser detections found")
                
                return (None, None)
                
        except Exception as e:
            if DEBUG_LASER_FIND_NN:
                print(f"Error during YOLOv5 inference: {e}")
            self.laser_coord = None
            return (None, None)

    def set_confidence_threshold(self, threshold: float):
        """Set the confidence threshold for detections."""
        self.confidence_threshold = threshold
        if self.model is not None:
            self.model.conf = threshold

    def set_iou_threshold(self, threshold: float):
        """Set the IoU threshold for non-maximum suppression."""
        self.iou_threshold = threshold
        if self.model is not None:
            self.model.iou = threshold

    def get_all_detections(self) -> list:
        """Get all detections from the last inference."""
        return self.prev_detections.copy()