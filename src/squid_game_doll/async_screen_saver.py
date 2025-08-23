import threading
import queue
import pygame
from typing import Tuple
from loguru import logger


class AsyncScreenSaver:
    """Asynchronous screen saver to prevent game slowdowns during screenshot saving."""
    
    def __init__(self):
        self._save_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread."""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.debug("AsyncScreenSaver worker thread started")
    
    def _worker_loop(self):
        """Background thread loop that processes save requests."""
        while not self._stop_event.is_set():
            try:
                # Wait for save request with timeout to check stop event
                surface, filepath = self._save_queue.get(timeout=1.0)
                self._save_surface_to_disk(surface, filepath)
                self._save_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.exception(f"Error in AsyncScreenSaver worker: {e}")
    
    def _save_surface_to_disk(self, surface: pygame.Surface, filepath: str):
        """Save pygame surface to disk as JPEG."""
        try:
            # Save as JPEG for much faster compression than PNG
            pygame.image.save(surface, filepath, "JPEG")
            logger.info(f"Screenshot saved as {filepath}")
        except pygame.error as e:
            logger.exception(f"Error saving screenshot to {filepath}: {e}")
    
    def save_async(self, surface: pygame.Surface, filename: str):
        """Queue a surface to be saved asynchronously.
        
        Args:
            surface: pygame.Surface to save
            filename: filename (will be prefixed with pictures/screenshot_)
        """
        filepath = f"pictures/screenshot_{filename.replace('.png', '.jpg')}"
        
        # Make a copy of the surface to avoid threading issues
        surface_copy = surface.copy()
        
        try:
            self._save_queue.put_nowait((surface_copy, filepath))
        except queue.Full:
            logger.warning("Screenshot save queue is full, skipping save")
    
    def shutdown(self):
        """Shutdown the async saver and wait for pending saves."""
        logger.debug("Shutting down AsyncScreenSaver...")
        
        # Stop accepting new requests
        self._stop_event.set()
        
        # Wait for current queue to finish
        try:
            self._save_queue.join()  # Wait for all tasks to complete
        except Exception as e:
            logger.warning(f"Error waiting for save queue to finish: {e}")
        
        # Join the worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                logger.warning("Worker thread did not shut down cleanly")
        
        logger.debug("AsyncScreenSaver shutdown complete")
    
    def get_queue_size(self) -> int:
        """Get the current number of pending saves."""
        return self._save_queue.qsize()