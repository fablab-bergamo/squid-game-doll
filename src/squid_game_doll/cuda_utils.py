"""
CUDA OpenCV utilities for GPU-accelerated image processing.
Automatically falls back to CPU operations if CUDA is not available.
"""
import cv2
import numpy as np
from typing import Optional, Tuple


class CudaProcessor:
    """GPU-accelerated image processing using OpenCV CUDA"""
    
    def __init__(self):
        self.cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if self.cuda_available:
            print("✅ CUDA OpenCV available - enabling GPU acceleration")
        else:
            print("ℹ️ CUDA OpenCV not available - using CPU processing")
    
    def is_cuda_available(self) -> bool:
        """Check if CUDA is available"""
        return self.cuda_available
    
    def cvt_color(self, src: cv2.UMat, code: int) -> cv2.UMat:
        """GPU-accelerated color conversion with CPU fallback"""
        if self.cuda_available and isinstance(src, np.ndarray):
            try:
                gpu_src = cv2.cuda_GpuMat()
                gpu_src.upload(src)
                gpu_result = cv2.cuda.cvtColor(gpu_src, code)
                return gpu_result.download()
            except Exception:
                pass  # Fall back to CPU
        
        # CPU fallback
        return cv2.cvtColor(src, code)
    
    def resize(self, src: cv2.UMat, dsize: Tuple[int, int], interpolation: int = cv2.INTER_LINEAR) -> cv2.UMat:
        """GPU-accelerated resize with CPU fallback"""
        if self.cuda_available and isinstance(src, np.ndarray):
            try:
                gpu_src = cv2.cuda_GpuMat()
                gpu_src.upload(src)
                gpu_result = cv2.cuda.resize(gpu_src, dsize, interpolation=interpolation)
                return gpu_result.download()
            except Exception:
                pass  # Fall back to CPU
        
        # CPU fallback
        return cv2.resize(src, dsize, interpolation=interpolation)
    
    def gaussian_blur(self, src: cv2.UMat, ksize: Tuple[int, int], sigmaX: float, sigmaY: float = 0) -> cv2.UMat:
        """GPU-accelerated Gaussian blur with CPU fallback"""
        if self.cuda_available and isinstance(src, np.ndarray):
            try:
                gpu_src = cv2.cuda_GpuMat()
                gpu_src.upload(src)
                gpu_result = cv2.cuda.GaussianBlur(gpu_src, ksize, sigmaX, sigmaY)
                return gpu_result.download()
            except Exception:
                pass  # Fall back to CPU
        
        # CPU fallback
        return cv2.GaussianBlur(src, ksize, sigmaX, sigmaY)


# Global instance for easy access
cuda_processor = CudaProcessor()


# Convenience functions
def cuda_cvt_color(src: cv2.UMat, code: int) -> cv2.UMat:
    """GPU-accelerated color conversion"""
    return cuda_processor.cvt_color(src, code)


def cuda_resize(src: cv2.UMat, dsize: Tuple[int, int], interpolation: int = cv2.INTER_LINEAR) -> cv2.UMat:
    """GPU-accelerated resize"""
    return cuda_processor.resize(src, dsize, interpolation)


def cuda_gaussian_blur(src: cv2.UMat, ksize: Tuple[int, int], sigmaX: float, sigmaY: float = 0) -> cv2.UMat:
    """GPU-accelerated Gaussian blur"""
    return cuda_processor.gaussian_blur(src, ksize, sigmaX, sigmaY)


def is_cuda_opencv_available() -> bool:
    """Check if CUDA OpenCV is available"""
    return cuda_processor.is_cuda_available()