from typing import Optional, Tuple
import cv2
import numpy as np
import os
import warnings
from pathlib import Path
from loguru import logger
from .laser_coordinate_filter import LaserCoordinateFilter

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

# Default configuration constants
DEFAULT_CONFIDENCE_THRESHOLD = 0.05
DEFAULT_IOU_THRESHOLD = 0.01
DEFAULT_NN_SMOOTHING_FACTOR = 0.1
DEFAULT_NN_MAX_HISTORY_SIZE = 10
DEFAULT_NN_OUTLIER_THRESHOLD = 150.0
DEFAULT_NN_MIN_CONFIDENCE = 0.05
PERFORMANCE_LOG_INTERVAL_FRAMES = 30


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
        self.confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD
        self.iou_threshold = DEFAULT_IOU_THRESHOLD
        self.is_jetson = is_jetson_orin()
        self.frame_count = 0
        
        # Initialize coordinate smoothing filter
        self.coordinate_filter = LaserCoordinateFilter(
            smoothing_factor=DEFAULT_NN_SMOOTHING_FACTOR,
            max_history_size=DEFAULT_NN_MAX_HISTORY_SIZE,
            outlier_threshold=DEFAULT_NN_OUTLIER_THRESHOLD,
            min_confidence_for_update=DEFAULT_NN_MIN_CONFIDENCE
        )
        
        self._load_optimized_model()

    def _find_optimal_model_format(self) -> Tuple[str, str]:
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
            self.frame_count = 0
            return True
            
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            logger.error(f"Error loading YOLOv5 laser model: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading YOLOv5 laser model: {e}")
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
                    
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"Jetson laser detection optimization failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error during Jetson optimization: {e}")

    def laser_found(self) -> bool:
        """Check if laser was found in the last detection."""
        return self.laser_coord is not None

    def get_laser_coord(self) -> Optional[Tuple[int, int]]:
        """Get the smoothed laser coordinates (default behavior for compatibility)."""
        return self.get_smoothed_coord()

    def get_raw_coord(self) -> Optional[Tuple[int, int]]:
        """Get the raw (unsmoothed) laser coordinate."""
        return self.coordinate_filter.get_raw_coordinate()

    def get_smoothed_coord(self) -> Optional[Tuple[int, int]]:
        """Get the smoothed laser coordinate."""
        return self.coordinate_filter.get_smoothed_coordinate()

    def get_winning_strategy(self) -> str:
        """Get information about the detection strategy used.
        
        Returns:
            str: Description of detection method and parameters if laser found, empty string otherwise
        """
        if self.laser_found():
            return f"YOLOv5_NN(conf={self.confidence_threshold}, iou={self.iou_threshold})"
        return ""

    def find_laser(self, img: cv2.UMat, rects: list = None, nn_frame: cv2.UMat = None) -> Tuple[Optional[Tuple[int, int]], Optional[cv2.UMat]]:
        """
        Find laser in the given image using YOLOv5 neural network.
        
        Args:
            img: Input image as cv2.UMat (full webcam frame)
            rects: List of exclusion rectangles (not used in NN version)
            nn_frame: Optional preprocessed NN frame to use instead of full frame
            
        Returns:
            Tuple of (laser_coordinates_in_full_frame, output_image)
            Note: Coordinates are always returned in full frame space regardless of input
        """
        if self.model is None:
            if DEBUG_LASER_FIND_NN:
                logger.debug("Model not loaded, cannot detect laser")
            self.laser_coord = None
            return (None, None)
        
        try:
            start_time = cv2.getTickCount()

            # Choose which frame to use for inference (prefer NN frame if available)
            use_nn_frame = nn_frame is not None
            inference_img = nn_frame if use_nn_frame else img
            
            # Convert UMat to numpy array if needed
            if isinstance(inference_img, cv2.UMat):
                img_np = cv2.UMat.get(inference_img)
            else:
                img_np = inference_img
                
            # Store frame dimensions for coordinate scaling
            if use_nn_frame:
                # Get full frame dimensions for coordinate scaling
                full_frame_shape = img.get().shape if isinstance(img, cv2.UMat) else img.shape
                nn_frame_shape = img_np.shape
                scale_x = full_frame_shape[1] / nn_frame_shape[1]
                scale_y = full_frame_shape[0] / nn_frame_shape[0]
            else:
                scale_x = scale_y = 1.0
                
            if DEBUG_LASER_FIND_NN:
                frame_type = "NN frame" if use_nn_frame else "full frame"
                logger.debug(f"Running YOLOv5 inference on {frame_type} shape: {img_np.shape}")
                if use_nn_frame:
                    logger.debug(f"Scale factors for coordinate mapping: {scale_x:.3f}x{scale_y:.3f}")
            
            # Run inference
            results = self.model(img_np)
            self.frame_count += 1

            # Process results
            detections = []
            output_image = img_np.copy()
            
            if results.xyxy[0] is not None and len(results.xyxy[0]) > 0:
                predictions = results.xyxy[0].cpu().numpy()  # xyxy format
                
                if DEBUG_LASER_FIND_NN:
                    logger.debug(f"Found {len(predictions)} detections")
                
                for pred in predictions:
                    x1, y1, x2, y2, conf, class_id = pred
                    class_name = self.model.names[int(class_id)]
                    
                    # Calculate center in inference frame coordinates
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    # Scale coordinates to full frame if using NN frame
                    if use_nn_frame:
                        center_x = int(center_x * scale_x)
                        center_y = int(center_y * scale_y)
                        bbox = (int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y))
                    else:
                        bbox = (int(x1), int(y1), int(x2), int(y2))
                    
                    detection = {
                        'center': (center_x, center_y),
                        'bbox': bbox,
                        'confidence': float(conf),
                        'class_name': class_name
                    }
                    detections.append(detection)
                    
                    # Draw bounding box on inference image (not scaled)
                    cv2.rectangle(output_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    
                    # Draw center point on inference image (not scaled)
                    cv2.circle(output_image, (int((x1 + x2) / 2), int((y1 + y2) / 2)), 5, (0, 0, 255), -1)
                    
                    # Draw label on inference image
                    label = f"{class_name}: {conf:.2f}"
                    cv2.putText(output_image, label, (int(x1), int(y1) - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    if DEBUG_LASER_FIND_NN:
                        coord_info = f"(scaled to full frame)" if use_nn_frame else "(original coordinates)"
                        logger.debug(f"Detected laser: {class_name} (conf: {conf:.3f}) at center ({center_x}, {center_y}) {coord_info}")
            
            # Select best detection (highest confidence)
            if detections:
                best_detection = max(detections, key=lambda d: d['confidence'])
                raw_coord = best_detection['center']
                confidence = best_detection['confidence']
                
                # Update the coordinate filter with the best detection
                self.coordinate_filter.update(raw_coord, confidence)
                
                # Store raw coordinate for compatibility
                self.laser_coord = raw_coord
                self.prev_detections = detections
                
                # Add strategy info to output image
                frame_info = "NN frame" if use_nn_frame else "full frame"
                cv2.putText(output_image, f"YOLOv5 Neural Network ({frame_info})", (10, 30), 
                          cv2.FONT_HERSHEY_COMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(output_image, f"Best conf: {confidence:.3f}", (10, 60), 
                          cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 255, 0), 1)
                
                # Show both raw and smoothed coordinates
                smoothed_coord = self.coordinate_filter.get_smoothed_coordinate()
                cv2.putText(output_image, f"Raw: {raw_coord}", (10, 90), 
                          cv2.FONT_HERSHEY_COMPLEX, 0.4, (0, 255, 255), 1)  # Cyan for raw
                if smoothed_coord:
                    cv2.putText(output_image, f"Smooth: {smoothed_coord}", (10, 110), 
                              cv2.FONT_HERSHEY_COMPLEX, 0.4, (255, 255, 0), 1)  # Yellow for smoothed
                
                if DEBUG_LASER_FIND_NN:
                    logger.debug(f"Selected best detection at {self.laser_coord} with confidence {best_detection['confidence']:.3f}")
                
                end_time = cv2.getTickCount()
                time_taken = (end_time - start_time) / cv2.getTickFrequency()
                total_time_ms = time_taken * 1000
                self.fps = 1 / time_taken if time_taken > 0 else 0
                
                # Log total processing time (very reduced frequency)
                if self.frame_count % PERFORMANCE_LOG_INTERVAL_FRAMES == 0:  # Log every 30 frames (~2 seconds at 15 FPS)
                    logger.info(f"🎯 Laser detection performance: {total_time_ms:.1f}ms ({self.fps:.1f} FPS) | Detections: {len(detections)} | Frame: {self.frame_count}")
                
                return (self.laser_coord, output_image)
            else:
                # No laser found - update filter with None
                self.coordinate_filter.update(None, confidence=0.0)
                self.laser_coord = None
                self.prev_detections = []
                
                if DEBUG_LASER_FIND_NN:
                    logger.debug("No laser detections found")
                
                return (None, None)
                
        except (RuntimeError, ValueError, AttributeError) as e:
            if DEBUG_LASER_FIND_NN:
                logger.error(f"Error during YOLOv5 inference: {e}")
            # Update filter with None on error
            self.coordinate_filter.update(None, confidence=0.0)
            self.laser_coord = None
            return (None, None)
        except Exception as e:
            if DEBUG_LASER_FIND_NN:
                logger.error(f"Unexpected error during YOLOv5 inference: {e}")
            # Update filter with None on error
            self.coordinate_filter.update(None, confidence=0.0)
            self.laser_coord = None
            return (None, None)

    def set_confidence_threshold(self, threshold: float):
        """Set the confidence threshold for detections.
        
        Args:
            threshold: Minimum confidence (0.0-1.0) required for laser detection
        """
        self.confidence_threshold = threshold
        if self.model is not None:
            self.model.conf = threshold

    def set_iou_threshold(self, threshold: float):
        """Set the IoU threshold for non-maximum suppression.
        
        Args:
            threshold: IoU threshold (0.0-1.0) for filtering overlapping detections
        """
        self.iou_threshold = threshold
        if self.model is not None:
            self.model.iou = threshold

    def get_all_detections(self) -> list:
        """Get all detections from the last inference."""
        return self.prev_detections.copy()