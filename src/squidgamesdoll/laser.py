import cv2
from .imgprocessing import brightness

def find_laser(img: cv2.UMat, strategy_hint: str, threshold_hint: int) -> (tuple, cv2.UMat, str, int):
    """
    Finds the laser in the given image using different strategies.

    Parameters:
    img (cv2.UMat): The input image.
    strategy_hint (str): The strategy hint to prioritize a specific strategy.
    threshold_hint (int): The threshold hint to use for the strategies.

    Returns:
    tuple: The coordinates of the laser, the output image, the strategy used, and the threshold value.
    """
    strategies = [find_laser_by_red_color, find_laser_by_grayscale, find_laser_by_green_color]
    
    if strategy_hint is not None:
        # sort strategies by hint
        strategies.sort(key=lambda x: x.__name__ == strategy_hint, reverse=True)

    for strategy in strategies:
        print(f"Trying strategy {strategy.__name__}")   
        (coord, output, threshold) = strategy(img.copy(), threshold_hint)
        if coord is not None:
            print(f"Found laser at {coord}")
            cv2.putText(output, 
                text = strategy.__name__, 
                org=(10, 40),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=.5,
                color=(0, 255, 0))
            cv2.putText(output, 
                text = f"Brightness={int(brightness(img))}", 
                org=(10, 60),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=.5,
                color=(0, 255, 0))
            return (coord, output, strategy.__name__, threshold)
    return (None, None, None, None)

def find_laser_by_threshold(channel: cv2.UMat, threshold_hint:int) -> (tuple, cv2.UMat, int):
    """
    Finds the laser in the given channel using a thresholding strategy.

    Parameters:
    channel (cv2.UMat): The input channel.
    threshold_hint (int): The threshold hint to use for the strategy.

    Returns:
    tuple: The coordinates of the laser, the output image, and the threshold value.
    """
    MAX_TRIES = 7
    MIN_THRESHOLD = 100
    MAX_THRESHOLD = 255
    threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2
    
    if (threshold_hint is not None and threshold_hint > MIN_THRESHOLD and threshold_hint < MAX_THRESHOLD):
        threshold = threshold_hint

    tries = 0
    while tries < MAX_TRIES:
        _, diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
        #cv2.imshow("Threshold", cv2.cvtColor(diff_thr, cv2.COLOR_GRAY2BGR))
        
        masked_channel = cv2.dilate(diff_thr, None, iterations=4)
        #cv2.imshow("Dilate", cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR))

        circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                                param1=50,param2=2,minRadius=3,maxRadius=10)
        
        if circles is None:
            circles_cpt = 0
        else:
            circles_cpt = len(circles[0,:])
        
        if circles_cpt == 0:
            step = (threshold - MIN_THRESHOLD) // 2
            if step == 0:
                step = 1
            threshold -= step 
            print(f"Found no circles, decreasing threshold to {threshold}")
            if threshold < MIN_THRESHOLD:
                return (None, None, None)
            tries += 1
            continue
            
        if circles_cpt > 1:
            step = (MAX_THRESHOLD - threshold) // 2
            if step == 0:
                step = 1
            threshold += step
            print(f"Found {circles_cpt} circles, increasing threshold to {threshold}")
            if threshold > MAX_THRESHOLD:
                return (None, None, None)
            tries += 1
            continue
        
        print(f"Found 1 circle, threshold={threshold}")

        # draw circles found
        output = cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR)
        background = cv2.cvtColor(channel, cv2.COLOR_GRAY2BGR)

        for circle in circles[0,:]:
            center = (int(circle[0]), int(circle[1]))
            output = cv2.addWeighted(background, 0.2, output, 0.5, 0)
            cv2.putText(output, 
                        text = "THR="+ str(threshold), 
                        org=(10, 20),
                        fontFace=cv2.FONT_HERSHEY_COMPLEX,
                        fontScale=0.5,
                        color=(0, 255, 0))
            return (center, output, threshold)
        
    return (None, None, None)

def find_laser_by_grayscale(img: cv2.UMat, hint:int) -> (tuple, cv2.UMat, int):
    """
    Finds the laser in the given image using a grayscale strategy.

    Parameters:
    img (cv2.UMat): The input image.
    hint (int): The threshold hint to use for the strategy.

    Returns:
    tuple: The coordinates of the laser, the output image, and the threshold value.
    """
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    return find_laser_by_threshold(normalized_gray_image, hint)

def find_laser_by_red_color(img: cv2.UMat, hint:int) -> (tuple, cv2.UMat, int):
    """
    Finds the laser in the given image using the red color channel.

    Parameters:
    img (cv2.UMat): The input image.
    hint (int): The threshold hint to use for the strategy.

    Returns:
    tuple: The coordinates of the laser, the output image, and the threshold value.
    """
    (_, _, R) = cv2.split(img)
    return find_laser_by_threshold(R, hint)
   
def find_laser_by_green_color(img: cv2.UMat, hint:int) -> (tuple, cv2.UMat, int):
    """
    Finds the laser in the given image using the green color channel.

    Parameters:
    img (cv2.UMat): The input image.
    hint (int): The threshold hint to use for the strategy.

    Returns:
    tuple: The coordinates of the laser, the output image, and the threshold value.
    """
    (_, G, _) = cv2.split(img)
    return find_laser_by_threshold(G, hint)