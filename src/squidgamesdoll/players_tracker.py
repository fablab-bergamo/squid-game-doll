import cv2
from cv2 import UMat
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
import pygame


class Player:
    def __init__(self, id: int, coords: tuple, moved: bool = False):
        self.id = id
        self.coords = coords
        self.moved = moved
        self.face = None

    def set_face(self, face: cv2.UMat):
        """Saves the face image of the player"""
        self.face = face

    def get_face(self) -> cv2.UMat:
        """Returns the face image of the player"""
        return self.face

    def get_image(self) -> pygame.image:
        if self.face is None:
            return None
        return pygame.image.frombuffer(
            self.face.tostring(), self.face.shape[1::-1], "BGR"
        )

    def set_rect(self, rect: tuple):
        """Sets the bounding box rectangle in (x, y, w, h) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        self.coords = (rect[0], rect[1], rect[2] + rect[0], rect[3] + rect[1])

    def get_rect(self):
        """Returns the bounding box rectangle in (x, y, w, h) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        return (
            self.coords[0],
            self.coords[1],
            self.coords[2] - self.coords[0],
            self.coords[3] - self.coords[1],
        )

    def get_coords(self):
        """Returns the bounding box coordinates in (x1, y1, x2, y2) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        return self.coords

    def set_coords(self, coords: tuple):
        """Sets the bounding box coordinates in (x1, y1, x2, y2) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        self.coords = coords

    def set_moved(self, moved: bool):
        """Sets the movement status of the player"""
        self.moved = moved

    def has_moved(self):
        """Returns the movement status of the player"""
        return self.moved

    def __str__(self):
        return f"Player {self.id} at {self.coords} (moved: {self.moved})"


class PlayerTracker:
    def __init__(self, model_path="yolov8m.pt", movement_threshold=20):
        self.yolo = YOLO(model_path)
        self.confidence = 0.5
        self.movement_threshold = (
            movement_threshold  # Pixels of movement to be considered "moving"
        )
        self.previous_positions = {}  # Stores past positions of players
        self.previous_result = []
        self.face_detector = mp.solutions.face_detection.FaceDetection(
            min_detection_confidence=0.5
        )  # Mediapipe Face Detector

    def extract_face(self, frame: cv2.UMat, bbox: tuple) -> UMat:
        """
        Extracts a face from a given person's bounding box.
        Args:
            frame (numpy.ndarray): The input frame.
            bbox (tuple): Bounding box (x1, y1, x2, y2) of the detected player.
        Returns:
            face_crop (numpy.ndarray or None): Cropped face if detected, otherwise None.
        """
        x1, y1, x2, y2 = bbox

        # Crop the person from the frame
        person_crop = frame[y1:y2, x1:x2]

        if person_crop.size == 0:
            return None

        # Convert to RGB for Mediapipe
        rgb_face = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)

        # Detect faces
        results = self.face_detector.process(rgb_face)

        if results.detections:
            for detection in results.detections:
                # Get face bounding box relative to the cropped person
                bboxC = detection.location_data.relative_bounding_box
                fx, fy, fw, fh = bboxC.xmin, bboxC.ymin, bboxC.width, bboxC.height

                # Convert relative coordinates to absolute
                h, w, _ = person_crop.shape
                fx, fy, fw, fh = int(fx * w), int(fy * h), int(fw * w), int(fh * h)

                # **Increase space around the face**
                margin = 0.2  # 20% margin
                extra_w = int(fw * margin)
                extra_h = int(fh * margin)

                # New bounding box with margin, ensuring it stays within image bounds
                x_start = max(fx - extra_w, 0)
                y_start = max(fy - extra_h, 0)
                x_end = min(fx + fw + extra_w, w)
                y_end = min(fy + fh + extra_h, h)

                # Extract expanded face region
                face_crop = person_crop[y_start:y_end, x_start:x_end]

                face_crop = cv2.resize(
                    face_crop, (250, 250), interpolation=cv2.INTER_AREA
                )  # Resize

                # **Enhance contrast**
                alpha = 1.5  # Contrast factor (adjustable)
                beta = 20  # Brightness factor (adjustable)
                face_crop = cv2.convertScaleAbs(face_crop, alpha=alpha, beta=beta)

                return face_crop

        print("No face detected")
        return None

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

                    # Movement detection
                    moved = False
                    if track_id in self.previous_positions:
                        prev_x1, prev_y1, prev_x2, prev_y2 = self.previous_positions[
                            track_id
                        ]
                        distance = np.linalg.norm(
                            [
                                (x1 + x2) / 2 - (prev_x1 + prev_x2) / 2,
                                (y1 + y2) / 2 - (prev_y1 + prev_y2) / 2,
                            ]
                        )
                        if distance > self.movement_threshold:
                            moved = True

                    # Store new position and movement status
                    player = Player(track_id, (x1, y1, x2, y2), moved=moved)

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

                    face = self.extract_face(frame, player.get_coords())
                    if face is not None:
                        player.set_face(face)
                    players.append(player)
                    self.previous_positions[track_id] = (x1, y1, x2, y2)

        cv2.imshow("process_frame", debug_frame)
        print("PlayerTracker returns", players)
        self.previous_result = players
        return players
