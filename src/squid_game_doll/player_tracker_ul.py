import cv2
import torch
import os
from ultralytics import YOLO
from pygame import Rect
from loguru import logger

from .base_player_tracker import BasePlayerTracker
from .game_settings import GameSettings
from .player import Player
from .utils.platform import (
    is_jetson_orin,
    get_optimal_model_for_platform,
    get_optimal_input_size,
    get_optimal_thread_count,
    should_use_tensorrt,
    get_platform_info
)


class PlayerTrackerUL(BasePlayerTracker):
    def __init__(self, model_path: str = "") -> None:
        """
        Initialize the PlayerTracker with the given YOLO model.
        Optimized for Jetson Nano performance.

        Args:
            model_path (str): Path to the YOLO model. If empty, auto-selects optimal model.
            movement_threshold (int): Pixels of movement to be considered "moving".
        """
        super().__init__()
        
        # Full tracking every frame (as requested)
        self.frame_count = 0
        
        # Auto-select optimal model if not specified
        if not model_path:
            model_path = get_optimal_model_for_platform()
        
        self.base_model_path = model_path
        self.is_jetson = is_jetson_orin()
        
        # Initialize model with optimized loading
        self._load_optimized_model()
    
    
    def _get_tensorrt_model_path(self, base_path: str = None) -> str:
        """Get TensorRT model path"""
        path = base_path or self.base_model_path
        base_name = os.path.splitext(path)[0]
        return f"{base_name}.engine"
    
    def _setup_tensorrt_paths(self, engine_path: str) -> bool:
        """Setup TensorRT system paths and verify availability"""
        import sys
        
        self.original_sys_path = sys.path.copy()
        
        # Add multiple possible TensorRT locations
        tensorrt_paths = [
            '/usr/lib/python3/dist-packages',
            '/usr/local/lib/python3.10/dist-packages',
            '/usr/lib/python3.10/dist-packages',
            '/opt/nvidia/vpi2/lib64/python3.10/site-packages',
            '/usr/local/lib/python3/site-packages',
        ]
        
        for path in tensorrt_paths:
            if path not in sys.path:
                sys.path.insert(0, path)
        
        try:
            # Clear any existing tensorrt module from cache
            if 'tensorrt' in sys.modules:
                del sys.modules['tensorrt']
            
            # Try to import TensorRT
            import tensorrt
            logger.info(f"✅ System TensorRT {tensorrt.__version__} available for engine loading")
            
            # Verify Ultralytics can load the engine
            try:
                test_yolo = YOLO(engine_path, task="detect", verbose=False)
                logger.info(f"🎯 TensorRT engine successfully loaded by Ultralytics")
                del test_yolo  # Clean up test instance
                return True
            except Exception as e:
                logger.warning(f"⚠️  TensorRT engine load test failed: {e}")
                return False
                
        except ImportError as e:
            logger.warning(f"⚠️  System TensorRT not accessible: {e}")
            return False
        except Exception as e:
            logger.warning(f"⚠️  TensorRT verification failed: {e}")
            return False
    
    def _restore_sys_path(self):
        """Restore original sys.path"""
        import sys
        if hasattr(self, 'original_sys_path'):
            sys.path = self.original_sys_path
    
    def _find_optimal_model_format(self) -> tuple[str, str]:
        """Find the optimal model format and path"""
        # Check for optimized model formats in priority order: TensorRT > ONNX > PyTorch
        
        # Priority 1: TensorRT engine (maximum performance)
        tensorrt_path = self._get_tensorrt_model_path()
        if os.path.exists(tensorrt_path):
            logger.info(f"✅ Found TensorRT engine: {tensorrt_path}")
            return tensorrt_path, "TensorRT (.engine)"
        
        # Priority 2: ONNX model (good performance with GPU)
        onnx_path = f"{os.path.splitext(self.base_model_path)[0]}.onnx"
        if os.path.exists(onnx_path):
            logger.info(f"✅ Found ONNX model: {onnx_path}")
            return onnx_path, "ONNX (.onnx)"
        
        # Priority 3: PyTorch model (fallback)
        logger.info(f"ℹ️  Using PyTorch model: {self.base_model_path}")
        return self.base_model_path, "PyTorch (.pt)"
    
    def _load_optimized_model(self):
        """Load model with optimal format detection and TensorRT handling"""
        # Find optimal model format
        model_path, model_format = self._find_optimal_model_format()
        
        logger.info(f"🚀 Loading model format: {model_format}")
        logger.info(f"📁 Model path: {model_path}")
        
        # Handle TensorRT engine loading with system TensorRT
        if model_format == "TensorRT (.engine)":
            tensorrt_available = self._setup_tensorrt_paths(model_path)
            
            if not tensorrt_available:
                self._restore_sys_path()
                logger.warning("🔄 Falling back to ONNX model for compatibility")
                
                # Fall back to ONNX if available
                onnx_path = f"{os.path.splitext(model_path.replace('.engine', ''))[0]}.onnx"
                if os.path.exists(onnx_path):
                    model_path = onnx_path
                    model_format = "ONNX (.onnx)"
                    logger.info(f"✅ Using ONNX fallback: {onnx_path}")
                else:
                    # Fall back to PyTorch
                    pt_path = f"{os.path.splitext(model_path.replace('.engine', ''))[0]}.pt"
                    if os.path.exists(pt_path):
                        model_path = pt_path
                        model_format = "PyTorch (.pt)"
                        logger.info(f"✅ Using PyTorch fallback: {pt_path}")
        
        # Store final model path and format
        self.model_path = model_path
        self.model_format = model_format
        
        # Load the YOLO model
        self.yolo: YOLO = YOLO(self.model_path, task="detect", verbose=False)
        
        # Optimize for current platform
        if self.is_jetson:
            self._optimize_for_jetson()
        elif torch.cuda.is_available() and model_format == "PyTorch (.pt)":
            self.yolo.to("cuda")

        # Get device info after optimization
        device_info = self._get_device_info()
        logger.info(f"🎯 YOLO inference running on: {device_info} ({get_platform_info()})")
        logger.info(f"⚡ Model format in use: {model_format}")
    
    def _get_device_info(self) -> str:
        """Get device information for logging"""
        try:
            if hasattr(self.yolo, 'device') and self.yolo.device is not None:
                return str(self.yolo.device)
            elif torch.cuda.is_available():
                return "CUDA available"
            else:
                return "CPU"
        except:
            return "Unknown"
    
    def _optimize_for_jetson(self) -> None:
        """Apply Jetson-specific optimizations"""
        try:
            # Set optimal number of threads for current platform
            torch.set_num_threads(get_optimal_thread_count())
            
            # Handle device optimization based on model format
            if hasattr(self, 'model_format') and self.model_format in ["ONNX (.onnx)", "TensorRT (.engine)"]:
                # ONNX and TensorRT models handle device in predict() calls, not via .to()
                if torch.cuda.is_available():
                    logger.info(f"✅ Jetson GPU available for {self.model_format} inference")
                    self.preferred_device = 0  # Use GPU device 0
                else:
                    logger.warning("CUDA not available on Jetson, will use CPU")
                    self.preferred_device = "cpu"
            else:
                # PyTorch models can use .to()
                if torch.cuda.is_available():
                    self.yolo.to("cuda")
                    logger.info("✅ Using Jetson GPU acceleration for PyTorch model")
                else:
                    logger.warning("CUDA not available on Jetson, using CPU")
                    
        except Exception as e:
            logger.warning(f"Jetson optimization failed: {e}")
    
    def export_to_tensorrt(self, imgsz: int = 640, half: bool = True, int8: bool = False) -> str:
        """
        Export model to TensorRT for optimal Jetson performance
        
        Args:
            imgsz: Input image size (smaller = faster)
            half: Use FP16 precision
            int8: Use INT8 precision (fastest but may reduce accuracy)
        
        Returns:
            Path to exported TensorRT model
        """
        try:
            logger.info(f"Exporting to TensorRT (imgsz={imgsz}, half={half}, int8={int8})")
            
            # Export with optimized settings for Jetson Nano
            exported_path = self.yolo.export(
                format="engine",
                imgsz=imgsz,
                half=half,
                int8=int8,
                dynamic=False,  # Static shapes for better performance
                workspace=4,    # 4GB workspace limit for Jetson Nano
                verbose=True
            )
            
            logger.info(f"TensorRT export completed: {exported_path}")
            return exported_path
            
        except Exception as e:
            logger.error(f"TensorRT export failed: {e}")
            return None

    def reset(self) -> None:
        """
        Resets the player tracker to its initial state.
        """
        self.previous_result = []
        self.frame_count = 0
        
        # Reload model with optimized format detection
        logger.info("🔄 Resetting player tracker...")
        self._load_optimized_model()

    def process_nn_frame(self, nn_frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        """
        Processes a video frame, detects players using YOLO, and returns a list of Player objects.
        Optimized for Jetson Nano performance.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        start_time = cv2.getTickCount()
        try:
            self.frame_rect = Rect(0, 0, nn_frame.shape[1], nn_frame.shape[0])
            self.nn_rect = Rect(0, 0, nn_frame.shape[1], nn_frame.shape[0])
            
            # Correctly separated detection and tracking parameters per Ultralytics docs
            inference_kwargs = {
                # Core detection parameters
                "persist": True,
                "classes": [0],         # Only detect persons
                "verbose": False,
                "stream": False,        # Direct results
                
                # Detection optimization parameters
                "conf": 0.4,            # Higher confidence threshold for speed
                "iou": 0.7,             # NMS IoU threshold
                "max_det": 8,           # Limit detections for speed
                "agnostic_nms": True,   # Faster NMS processing
                "half": True,           # Enable FP16 precision
                "augment": False,       # Disable test-time augmentation
                
                # Tracking parameters (correctly formatted)
                "tracker": "bytetrack.yaml",  # ByteTrack: Fastest available
                
                # Disable unnecessary features
                "retina_masks": False,  # Disable mask processing
                "save": False,          # No file saving
                "show": False,          # No visualization
            }
            
            # Additional optimizations for Jetson
            if self.is_jetson:
                inference_kwargs.update({
                    "augment": False,     # Disable augmentation for speed
                    "half": True,         # Use FP16 if available
                })
                
                # For ONNX/TensorRT models, specify device in inference call
                if hasattr(self, 'preferred_device'):
                    inference_kwargs["device"] = self.preferred_device
            
            # Full tracking every frame with lightweight optimizations
            self.frame_count += 1
            
            # Full tracking with optimized parameters
            tracking_start = cv2.getTickCount()
            results = self.yolo.track(nn_frame, **inference_kwargs)
            tracking_end = cv2.getTickCount()
            tracking_ms = ((tracking_end - tracking_start) / cv2.getTickFrequency()) * 1000
            # Only log tracking time if it's unusually slow or occasionally
            if tracking_ms > 80.0 or self.frame_count % 60 == 0:
                logger.debug(f"🎯 Tracking: {tracking_ms:.1f}ms [{self.model_format}]")
            
        except Exception as e:
            logger.exception(f"process_nn_frame: error: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return self.previous_result

        # Apply confidence threshold from settings
        self.confidence = gamesettings.get_param("confidence", 40) / 100.0
        
        # Measure post-processing steps
        post_start = cv2.getTickCount()
        detections = self.yolo_to_supervision(results)
        yolo_conv_time = ((cv2.getTickCount() - post_start) / cv2.getTickFrequency()) * 1000
        
        supervision_start = cv2.getTickCount()
        players = self.supervision_to_players(detections)
        supervision_time = ((cv2.getTickCount() - supervision_start) / cv2.getTickFrequency()) * 1000
        
        # Only log post-processing if there are issues
        if yolo_conv_time > 5.0 or supervision_time > 5.0:
            logger.info(f"📊 Slow post-processing: YOLO→Supervision {yolo_conv_time:.1f}ms | Supervision→Players {supervision_time:.1f}ms")
        # Only log individual players occasionally
        if self.frame_count % 60 == 0 and players:
            logger.debug(f"Players: {[f'ID:{p.get_id()} pos:({p.get_bbox()[0]},{p.get_bbox()[1]}) {int(p.get_confidence()*100)} %' for p in players]}")
        self.previous_result = players
        end_time = cv2.getTickCount()
        time_taken = (end_time - start_time) / cv2.getTickFrequency()
        total_time_ms = time_taken * 1000
        self.fps = 1 / time_taken if time_taken > 0 else 0
        
        # Log total processing time (very reduced frequency)
        if self.frame_count % 30 == 0:  # Log every 30 frames (~2 seconds at 15 FPS)
            logger.info(f"🎯 Performance: {total_time_ms:.1f}ms ({self.fps:.1f} FPS) | Players: {len(players)} | Frame: {self.frame_count}")
        elif total_time_ms > 100.0:  # Only log individual frames if they're really slow
            logger.warning(f"🐌 Slow frame: {total_time_ms:.1f}ms ({self.fps:.1f} FPS) | Players: {len(players)}")
        return players

    def get_max_size(self) -> int:
        """Get optimal input size for current platform"""
        return get_optimal_input_size()
