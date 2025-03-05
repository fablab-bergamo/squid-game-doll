import cv2
from ultralytics import YOLO
from Player import Player
import torch
import torch_directml


class PlayerTracker:
    def __init__(self, model_path: str = "yolov8s.pt") -> None:
        """
        Initialize the PlayerTracker with the given YOLO model.

        Args:
            model_path (str): Path to the YOLO model.
            movement_threshold (int): Pixels of movement to be considered "moving".
        """
        self.yolo: YOLO = YOLO(model_path, verbose=True)
        # Run the model on the Nvidia GPU
        if torch.cuda.is_available():
            self.yolo.to("cuda")

        print(f"YOLOv8 running on {self.yolo.device}")
        self.confidence: float = 0.5
        self.previous_result: list[Player] = []

    def __preprocess_frame(self, frame: cv2.UMat, target_size: tuple[int, int] = (640, 480)) -> cv2.UMat:
        """
        Preprocesses a frame to enhance YOLO object detection performance.

        Args:
            frame (cv2.UMat): Input image (BGR format from OpenCV).
            target_size (tuple[int, int]): Desired frame size for YOLO model.

        Returns:
            cv2.UMat: Preprocessed frame.
        """

        # Resize the frame to match YOLO's expected input size
        frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)

        # Apply Gaussian Blur to reduce noise
        frame = cv2.GaussianBlur(frame, (5, 5), 0)

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
        """
        Processes a video frame, detects players using YOLO, and returns a list of Player objects.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        try:
            # Preprocess the frame for improved YOLO detection
            h, w = frame.shape[:2]
            target_size = (640, int(640 / (w / h)))
            yolo_frame = self.__preprocess_frame(frame, target_size)
            results = self.yolo.track(yolo_frame, persist=True, stream=True, classes=[0])
        except Exception as e:
            print("Error:", e)
            return self.previous_result

        players: list[Player] = []

        # Get original frame size
        orig_h, orig_w, _ = frame.shape
        yolo_h, yolo_w, _ = yolo_frame.shape  # Since we resize the frame

        # Scaling factors to map detections back to original frame size
        scale_x: float = orig_w / yolo_w
        scale_y: float = orig_h / yolo_h

        # display frame with bounding box and player id
        debug_frame = frame.copy()
        # yolo_debug = yolo_frame.copy()  # Uncomment for additional debugging visualization

        for result in results:
            if result.boxes is None:
                continue  # Skip if no detections

            for box in result.boxes:
                conf: float = float(box.conf[0].cpu().numpy())  # Extract confidence
                class_id: int = int(box.cls[0].cpu().numpy())  # Get class ID
                if conf > self.confidence and class_id == 0:  # Check if it's a person
                    # Extract and convert bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

                    # cv2.rectangle(yolo_debug, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    # Scale bounding box back to original frame size
                    x1 = int(x1 * scale_x)
                    y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x)
                    y2 = int(y2 * scale_y)

                    track_id: int | None = int(box.id[0].cpu().numpy()) if box.id is not None else None

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

        # cv2.imshow("yolo_results_frame", debug_frame)
        # cv2.imshow("yolo_debug_frame", yolo_debug)

        self.previous_result = players
        return players
