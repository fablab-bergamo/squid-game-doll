import cv2
import numpy as np
import supervision as sv
import threading
import queue
from Player import Player
from utils import HailoAsyncInference  # Make sure this is available in your project
from BasePlayerTracker import BasePlayerTracker


class PlayerTrackerHailo(BasePlayerTracker):
    def __init__(self, hef_path: str = "yolov11m.hef", score_thresh: float = 0.5) -> None:
        """
        Initialize the Hailo-based player tracker.

        Args:
            hef_path (str): Path to the HEF model.
            score_thresh (float): Minimum detection confidence.
        """
        super().__init__()
        self.score_thresh = score_thresh

        # Set up queues for asynchronous inference
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        # Initialize the Hailo inference engine
        self.hailo_inference = HailoAsyncInference(hef_path, self.input_queue, self.output_queue)
        self.model_h, self.model_w, _ = self.hailo_inference.get_input_shape()
        self.tracker = sv.ByteTrack(frame_rate=10, lost_track_buffer=80, minimum_matching_threshold=0.9)

        # Start the asynchronous inference in a separate thread
        self.inference_thread = threading.Thread(target=self.hailo_inference.run, daemon=True)
        self.inference_thread.start()

    def process_frame(self, frame: cv2.UMat) -> list[Player]:
        """
        Processes a video frame using Hailo asynchronous inference and returns a list of Player objects.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        try:
            # Get original frame dimensions
            video_h, video_w = frame.shape[:2]

            # Preprocess: Resize frame to model input size if necessary
            if (video_h, video_w) != (self.model_h, self.model_w):
                preprocessed_frame = cv2.resize(frame, (self.model_w, self.model_h))
            else:
                preprocessed_frame = frame

            ratios = (video_w, video_h)

            # Put the preprocessed frame into the Hailo inference queue
            self.input_queue.put([preprocessed_frame])

            # Retrieve the inference results (blocking call)
            _, results = self.output_queue.get()
            # In some Hailo versions the output is wrapped in an extra list
            if isinstance(results, list) and len(results) == 1:
                results = results[0]

            # Convert Hailo inference output into Supervision detections
            detections_sv = self.__extract_detections(results, ratios, self.score_thresh)
            detections_sv = self.tracker.update_with_detections(detections_sv)

            # Convert detections into Player objects using the base class helper
            players = self.supervision_to_players(detections_sv)

            self.previous_result = players
            return players

        except Exception as e:
            print("Error in process_frame:", e)
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
