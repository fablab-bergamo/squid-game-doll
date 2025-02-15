import cv2
import numpy as np
import configparser

# Callback function for trackbars (does nothing but required for OpenCV trackbars)


def nothing(x):
    pass

# Function to process frame and track laser pointer


def track_laser(frame, threshold_value, max_value, background_subtractor):
    fg_mask = background_subtractor.apply(frame)
    red_channel = frame[:, :, 2]  # We use Numpy to slice the image (blue=0, green=1, red=2)
    red_fg = cv2.bitwise_and(red_channel, red_channel, mask=fg_mask)
    _, mask = cv2.threshold(red_fg, threshold_value,
                            max_value, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        moments = cv2.moments(largest_contour)
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
            cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
            cv2.putText(frame, f"Laser at ({cx}, {cy})", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame, red_channel, mask

def create_settings_window(threshold_value, max_value):
    cv2.namedWindow("Settings", flags=cv2.WINDOW_GUI_NORMAL)
    cv2.createTrackbar("Threshold", "Settings", threshold_value, 255, nothing)
    cv2.createTrackbar("Max Value", "Settings", max_value, 255, nothing)

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    width = config.getint('Camera', 'width')
    height = config.getint('Camera', 'height')
    codec = config.get('Camera', 'codec', fallback='').strip()
    threshold_value = config.getint('Threshold', 'min_value')
    max_value = config.getint('Threshold', 'max_value')

    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if codec:
        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
        except:
            print("Warning: Could not set codec. Using default codec.")

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    background_subtractor = cv2.createBackgroundSubtractorMOG2(
        detectShadows=False)

    show_settings = True
    show_red_channels = True
    tracking_enabled = True

    # Create the initial "Settings" window
    create_settings_window(threshold_value, max_value)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        if show_settings:
            try:
                threshold_value = cv2.getTrackbarPos("Threshold", "Settings")
                max_value = cv2.getTrackbarPos("Max Value", "Settings")
            except cv2.error:
                # If the window is destroyed for some reason, recreate it
                create_settings_window(threshold_value, max_value)

        if not tracking_enabled:
            unprocessed_frame = frame.copy() 
        processed_frame, red_channel, mask = track_laser(
            frame, threshold_value, max_value, background_subtractor)
        if not tracking_enabled:
            processed_frame = unprocessed_frame  
            
        cv2.imshow("Laser Tracker", processed_frame)

        if show_red_channels:
            cv2.imshow("Red Channel", red_channel)
            cv2.imshow("Red Channel Mask", mask)
        else:
            cv2.destroyWindow("Red Channel")
            cv2.destroyWindow("Red Channel Mask")

        if not show_settings:
            try:
                cv2.destroyWindow("Settings")
            except cv2.error:
                pass  # Ignore if the window is already destroyed

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            show_settings = not show_settings
            if show_settings:
                create_settings_window(threshold_value, max_value)
        elif key == ord('d'):
            show_red_channels = not show_red_channels
        elif key == ord('t'):
            tracking_enabled = not tracking_enabled  # Toggle tracking on/off

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()