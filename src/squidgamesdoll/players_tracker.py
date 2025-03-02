import cv2
from ultralytics import YOLO
from Player import Player
from face_extractor import FaceExtractor


class PlayerTracker:
    def __init__(self, model_path="yolov8m.pt", movement_threshold=20):
        self.yolo = YOLO(model_path)
        self.confidence = 0.5
        self.movement_threshold = (
            movement_threshold  # Pixels of movement to be considered "moving"
        )
        self.previous_result = []

    def preprocess_frame(self, frame: cv2.UMat, target_size=(640, 640)):
        """
        Preprocesses a frame to enhance YOLO object detection performance.

        Args:
            frame (numpy.ndarray): Input image (BGR format from OpenCV).
            target_size (tuple): Desired frame size for YOLO model.

        Returns:
            numpy.ndarray: Preprocessed frame.
        """

        # Resize the frame to match YOLO's expected input size
        frame = cv2.resize(frame, target_size)

        # Convert to grayscale (optional, for debugging contrast)
        # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian Blur to reduce noise
        frame = cv2.GaussianBlur(frame, (5, 5), 0)

        # Convert back to color (if grayscale was used)
        # frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        # Normalize brightness and contrast using histogram equalization
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)  # Convert to LAB color space
        l, a, b = cv2.split(lab)
        l = cv2.equalizeHist(l)  # Apply histogram equalization to the L channel
        lab = cv2.merge((l, a, b))
        frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)  # Convert back to BGR

        # Adjust brightness & contrast (fine-tuning)
        alpha = 1.2  # Contrast control (1.0-3.0)
        beta = 20  # Brightness control (0-100)
        frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

        return frame

    def process_frame(self, frame: cv2.UMat) -> list[Player]:

        try:
            yolo_frame = self.preprocess_frame(frame)
            self.yolo.allowed_classes = ["person"]
            results = self.yolo.track(yolo_frame, persist=True, stream=False)
        except Exception as e:
            print("Error:", e)
            return self.previous_result

        players = []

        # Get original frame size
        orig_h, orig_w, _ = frame.shape
        yolo_h, yolo_w = 640, 640  # Since we resize the frame to 640x640

        # Scaling factors
        scale_x = orig_w / yolo_w
        scale_y = orig_h / yolo_h

        # display frame with bounding box and player id
        debug_frame = frame.copy()

        for result in results:
            if result.boxes is None:
                continue  # Skip if no detections

            for box in result.boxes:
                conf = float(box.conf[0].cpu().numpy())  # Extract confidence
                class_id = int(box.cls[0].cpu().numpy())  # Get class ID
                if conf > self.confidence and class_id == 0:  # Check if it's a person
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

                    # Scale bounding box back to original frame size
                    x1 = int(x1 * scale_x)
                    y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x)
                    y2 = int(y2 * scale_y)

                    track_id = (
                        int(box.id[0].cpu().numpy()) if box.id is not None else None
                    )

                    # Store new position and movement status
                    player = Player(track_id, (x1, y1, x2, y2))

                    cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        debug_frame,
                        f"Player {track_id}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (36, 255, 12),
                        2,
                    )

                    players.append(player)

        cv2.imshow("yolo_results_frame", debug_frame)

        self.previous_result = players
        return players
