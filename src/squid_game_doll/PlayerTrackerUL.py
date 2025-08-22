import cv2
import torch
import os
import platform
from ultralytics import YOLO
from pygame import Rect
from loguru import logger

from .BasePlayerTracker import BasePlayerTracker
from .GameSettings import GameSettings
from .Player import Player


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
        
        # Auto-select optimal model for Jetson Nano if not specified
        if not model_path:
            model_path = self._get_optimal_model()
        
        self.model_path = model_path
        self.is_jetson = self._is_jetson_nano()
        
        # Try to load TensorRT optimized model first
        tensorrt_path = self._get_tensorrt_model_path()
        if os.path.exists(tensorrt_path) and self.is_jetson:
            logger.info(f"Loading TensorRT optimized model: {tensorrt_path}")
            self.model_path = tensorrt_path
        
        self.yolo: YOLO = YOLO(self.model_path, verbose=False)
        
        # Optimize for Jetson Nano
        if self.is_jetson:
            self._optimize_for_jetson()
        elif torch.cuda.is_available():
            self.yolo.to("cuda")

        logger.info(f"YOLO running on {self.yolo.device} (Jetson: {self.is_jetson})")
    
    def _is_jetson_nano(self) -> bool:
        """Check if running on Jetson Nano"""
        try:
            return (platform.machine() == "aarch64" and 
                   os.path.exists("/etc/nv_tegra_release"))
        except:
            return False
    
    def _get_optimal_model(self) -> str:
        """Get optimal model for current platform"""
        if self._is_jetson_nano():
            return "yolo11n.pt"  # Nano model for Jetson Nano
        else:
            return "yolo11s.pt"  # Small model for other platforms
    
    def _get_tensorrt_model_path(self) -> str:
        """Get TensorRT model path"""
        base_name = os.path.splitext(self.model_path)[0]
        return f"{base_name}.engine"
    
    def _optimize_for_jetson(self) -> None:
        """Apply Jetson-specific optimizations"""
        try:
            # Set optimal number of threads for ARM processors
            torch.set_num_threads(4)
            
            # Use GPU if available on Jetson
            if torch.cuda.is_available():
                self.yolo.to("cuda")
                logger.info("Using Jetson GPU acceleration")
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
        
        # Try to load TensorRT optimized model first
        tensorrt_path = self._get_tensorrt_model_path()
        if os.path.exists(tensorrt_path) and self.is_jetson:
            logger.info(f"Loading TensorRT optimized model: {tensorrt_path}")
            model_path = tensorrt_path
        else:
            model_path = self.model_path
            
        self.yolo: YOLO = YOLO(model_path, verbose=False)
        
        # Optimize for Jetson Nano
        if self.is_jetson:
            self._optimize_for_jetson()
        elif torch.cuda.is_available():
            self.yolo.to("cuda")

        logger.info(f"YOLO running on {self.yolo.device} (Jetson: {self.is_jetson})")

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
            
            # Optimized inference settings for Jetson Nano
            inference_kwargs = {
                "persist": True,
                "classes": [0],  # Only detect persons
                "verbose": False,
                "stream": True,
            }
            
            # Additional optimizations for Jetson
            if self.is_jetson:
                inference_kwargs.update({
                    "augment": False,     # Disable augmentation for speed
                    "half": True,         # Use FP16 if available
                })
            
            results = self.yolo.track(nn_frame, **inference_kwargs)
            
        except Exception as e:
            logger.exception("process_nn_frame: error:")
            return self.previous_result

        # Apply confidence threshold from settings
        self.confidence = gamesettings.get_param("confidence", 40) / 100.0
        detections = self.yolo_to_supervision(results)
        players = self.supervision_to_players(detections)
        for p in players:
            logger.debug(p)
        self.previous_result = players
        end_time = cv2.getTickCount()
        time_taken = (end_time - start_time) / cv2.getTickFrequency()
        self.fps = 1 / time_taken if time_taken > 0 else 0
        return players

    def get_max_size(self) -> int:
        """Get optimal input size for current platform"""
        return 640  # Standard size for all platforms
