import cv2
import numpy as np
import supervision as sv
import threading
import queue
from pygame import Rect
from loguru import logger
from .player import Player
from .utils import HailoAsyncInference  # Make sure this is available in your project
from .base_player_tracker import BasePlayerTracker
from .game_settings import GameSettings


class PlayerTrackerHailo(BasePlayerTracker):
    def __init__(self, hef_path: str = "yolov11m.hef", score_thresh: float = 0.4) -> None:
        """
        Initialize the Hailo-based player tracker.

        Args:
            hef_path (str): Path to the HEF model.
            score_thresh (float): Minimum detection confidence.
        """
        super().__init__()
        self.confidence = score_thresh

        # Set up queues for asynchronous inference
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        # Initialize the Hailo inference engine
        self.hailo_inference = HailoAsyncInference(hef_path, self.input_queue, self.output_queue, 1)
        self.model_h, self.model_w, _ = self.hailo_inference.get_input_shape()
        self.tracker = sv.ByteTrack(frame_rate=5)

        # Start the asynchronous inference in a separate thread
        self.inference_thread = threading.Thread(target=self.hailo_inference.run, daemon=True)
        self.inference_thread.start()

    def process_nn_frame(self, nn_frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        """
        Processes a video frame using Hailo asynchronous inference and returns a list of Player objects.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        try:
            self.frame_rect = Rect(0, 0, nn_frame.shape[1], nn_frame.shape[0])
            self.nn_rect = Rect(0, 0, nn_frame.shape[1], nn_frame.shape[0])

            start_time = cv2.getTickCount()
            # Put the preprocessed frame into the Hailo inference queue
            # Ridimensiona nn_frame a 640 640
            nn_frame = cv2.resize(nn_frame, (self.model_w, self.model_h))
            self.input_queue.put([nn_frame])

            # Retrieve the inference results (blocking call)
            _, results = self.output_queue.get()
            # In some Hailo versions the output is wrapped in an extra list
            if isinstance(results, list) and len(results) == 1:
                results = results[0]

            # Convert Hailo inference output into Supervision detections
            self.confidence = gamesettings.get_param("confidence", 40) / 100.0
            detections_sv = self.__extract_detections(results, (self.nn_rect.w, self.nn_rect.h), self.confidence)
            detections_sv = self.tracker.update_with_detections(detections_sv)

            # Convert detections into Player objects using the base class helper
            players = self.supervision_to_players(detections_sv)

            self.previous_result = players

            end_time = cv2.getTickCount()
            time_taken = (end_time - start_time) / cv2.getTickFrequency()
            self.fps = 1 / time_taken if time_taken > 0 else 0

            return players

        except Exception as e:
            logger.exception("Error in process_frame")
            return self.previous_result

    def __extract_detections(
        self, hailo_output: list[np.ndarray], ratios: tuple[float, float], threshold: float
    ) -> sv.Detections:
        """
        Converts Hailo asynchronous inference output into a supervision Detections object.

        Assumes the Hailo output is a list of numpy arrays where index 0 corresponds to person detections.
        The bounding boxes are expected in the normalized [ymin, xmin, ymax, xmax] format.

        Args:
            hailo_output (list[np.ndarray]): Raw output from Hailo inference.
            (video_h (int): Height of the original video frame.
            video_w (int): Width of the original video frame.)
            threshold (float): Confidence threshold.

        Returns:
            sv.Detections: Detections object with absolute pixel coordinates.
        """
        xyxy = []
        confidences = []

        # Iterate over all classes, but only process the 'person' class (COCO index 0)
        for class_id, detections in enumerate(hailo_output):
            if class_id != 0:
                continue  # Skip non-person detections
            for detection in detections:
                bbox, score = detection[:4], detection[4]
                if score < threshold:
                    continue
                # Convert bbox from normalized [ymin, xmin, ymax, xmax] to absolute [x1, y1, x2, y2]
                x1 = bbox[1] * ratios[0]
                y1 = bbox[0] * ratios[1]
                x2 = bbox[3] * ratios[0]
                y2 = bbox[2] * ratios[1]
                xyxy.append([x1, y1, x2, y2])
                confidences.append(score)

        if not xyxy:
            return sv.Detections.empty()

        xyxy_np = np.array(xyxy)
        conf_np = np.array(confidences)
        # Hailo output does not provide tracker IDs; we assign a default value (-1)
        tracker_id_np = -1 * np.ones_like(conf_np)
        return sv.Detections(xyxy=xyxy_np, confidence=conf_np, tracker_id=tracker_id_np)

    def stop(self) -> None:
        """
        Stops the Hailo asynchronous inference thread gracefully.
        """
        self.input_queue.put(None)
        self.inference_thread.join()

    def reset(self) -> None:
        """
        Resets the player tracker state.
        """
        self.stop()
        self.tracker.reset()
        self.previous_result = []
        self.inference_thread = threading.Thread(target=self.hailo_inference.run, daemon=True)
        self.inference_thread.start()

    def get_max_size(self) -> int:
        return 640
