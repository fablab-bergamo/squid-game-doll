import cv2

last_render = 0


class ExclusionRect:
    UNDEFINED = (-1, -1)

    def __init__(self):
        self.top_left = ExclusionRect.UNDEFINED
        self.bottom_right = ExclusionRect.UNDEFINED


def add_exclusion_rectangles(frame: cv2.UMat, rectangles: list, color=(128, 64, 64)) -> cv2.UMat:
    for rect in rectangles:
        if rect.top_left != ExclusionRect.UNDEFINED and rect.bottom_right != ExclusionRect.UNDEFINED:
            cv2.rectangle(frame, rect.top_left, rect.bottom_right, color, -1)

    # Add 2 px around frame
    height, width, _ = frame.shape
    cv2.rectangle(frame, (1, 1), (width - 1, height - 1), (0, 0, 0), thickness=2)
    return frame


def add_camera_settings(cap: cv2.VideoCapture, frame: cv2.UMat) -> cv2.UMat:
    """
    Adds camera settings information to the given frame.

    Parameters:
    cap (cv2.VideoCapture): The video capture device.
    frame (cv2.UMat): The frame to which the settings information will be added.

    Returns:
    cv2.UMat: The frame with the added settings information.
    """
    global last_render
    if last_render == 0:
        last_render = cv2.getTickCount()

    # compute fps
    current_time = cv2.getTickCount()
    time_diff = (current_time - last_render) / cv2.getTickFrequency()
    last_render = current_time
    fps = int(1.0 / time_diff)
    height, width, _ = frame.shape

    cv2.putText(
        frame,
        text=f"Act. FPS={fps} (camera:{cap.get(cv2.CAP_PROP_FPS)})",
        org=(10, 40),
        fontFace=cv2.FONT_HERSHEY_COMPLEX,
        fontScale=0.5,
        color=(255, 255, 255),
    )

    cv2.putText(
        frame,
        text=f"Picture={height}x{width}",
        org=(10, 20),
        fontFace=cv2.FONT_HERSHEY_COMPLEX,
        fontScale=0.5,
        color=(255, 255, 255),
    )
    cv2.putText(
        frame,
        text=f"Exposure={cap.get(cv2.CAP_PROP_EXPOSURE)}",
        org=(10, 60),
        fontFace=cv2.FONT_HERSHEY_COMPLEX,
        fontScale=0.5,
        color=(255, 255, 255),
    )
    return frame


def draw_visor_at_coord(img: cv2.UMat, coord: tuple) -> cv2.UMat:
    """
    Draws a visor at the specified coordinates on the given image.

    Parameters:
    img (cv2.UMat): The image on which to draw the visor.
    coord (tuple): The (x, y) coordinates where the visor will be drawn.

    Returns:
    cv2.UMat: The image with the drawn visor.
    """
    cv2.line(img, (coord[0] - 10, coord[1]), (coord[0] - 5, coord[1]), (0, 255, 0), 2)
    cv2.line(img, (coord[0] + 5, coord[1]), (coord[0] + 10, coord[1]), (0, 255, 0), 2)
    cv2.line(img, (coord[0], coord[1] - 10), (coord[0], coord[1] - 5), (0, 255, 0), 2)
    cv2.line(img, (coord[0], coord[1] + 5), (coord[0], coord[1] + 10), (0, 255, 0), 2)
    cv2.rectangle(
        img,
        (coord[0] - 14, coord[1] - 14),
        (coord[0] + 14, coord[1] + 14),
        (0, 255, 0),
        2,
    )
    return img


def draw_target_at_coord(img: cv2.UMat, coord: tuple) -> cv2.UMat:
    """
    Draws a target at the specified coordinates on the given image.

    Parameters:
    img (cv2.UMat): The image on which to draw the target.
    coord (tuple): The (x, y) coordinates where the target will be drawn.

    Returns:
    cv2.UMat: The image with the drawn target.
    """
    if coord is None or len(coord) != 2:
        return img
    cv2.line(img, (coord[0] - 5, coord[1]), (coord[0] - 1, coord[1]), (0, 0, 255), 1)
    cv2.line(img, (coord[0] + 1, coord[1]), (coord[0] + 5, coord[1]), (0, 0, 255), 1)
    cv2.line(img, (coord[0], coord[1] - 5), (coord[0], coord[1] - 1), (0, 0, 255), 1)
    cv2.line(img, (coord[0], coord[1] + 1), (coord[0], coord[1] + 5), (0, 0, 255), 1)
    return img
