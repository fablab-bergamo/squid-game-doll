import cv2
from .imgprocessing import brightness

class LaserFinder:
    def __init__(self):
        """
        Initializes the LaserFinder object.
        """
        self.prev_strategy = None
        self.prev_threshold = None
        self.laser_coord = None
    
    def laser_found(self) -> bool:
        return self.laser_coord is not None
    
    def get_laser_coord(self) -> tuple:
        return self.laser_coord
    
    def get_winning_strategy(self) -> str:
        if self.laser_found():
            return f"{self.prev_strategy}(THR={self.prev_threshold})"
        return ""
    
    def find_laser(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using different strategies.

        Parameters:
        img (cv2.UMat): The input image.

        Returns:
        tuple: The coordinates of the laser, the output image, the strategy used, and the threshold value.
        """
        strategies = [self.find_laser_by_red_color, self.find_laser_by_grayscale, self.find_laser_by_green_color]
        
        if self.prev_strategy is not None:
            # sort strategies by hint
            strategies.sort(key=lambda x: x.__name__ == self.prev_strategy, reverse=True)

        #self.find_laser_by_threshold_2(img)
        for strategy in strategies:
            print(f"Trying strategy {strategy.__name__}")   
            (coord, output) = strategy(img.copy())
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
                self.prev_strategy = strategy.__name__
                self.laser_coord = coord
                return (coord, output)
        
        self.laser_coord = None
        
        return (None, None)

    def find_laser_by_threshold(self, channel: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given channel using a thresholding strategy.

        Parameters:
        channel (cv2.UMat): The input channel.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        MAX_TRIES = 7
        MIN_THRESHOLD = 100
        MAX_THRESHOLD = 255
        threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2
        
        if (self.prev_threshold is not None and self.prev_threshold > MIN_THRESHOLD and self.prev_threshold < MAX_THRESHOLD):
            threshold = self.prev_threshold

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
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue
                
            if circles_cpt > 1:
                step = (MAX_THRESHOLD - threshold) // 2
                if step == 0:
                    step = 1
                threshold += step
                print(f"Found {circles_cpt} circles, increasing threshold to {threshold}")
                if threshold > MAX_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
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
                self.prev_threshold = threshold
                self.laser_coord = center
                return (center, output)
        
        self.laser_coord = None
        return (None, None)

    def find_laser_by_threshold_2(self, channel: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given channel using a thresholding strategy.

        Parameters:
        channel (cv2.UMat): The input channel.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        MAX_TRIES = 100
        MIN_THRESHOLD = 50
        MAX_THRESHOLD = 255
        threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2
        step = (MIN_THRESHOLD + MAX_THRESHOLD) // 4

        if (self.prev_threshold is not None and self.prev_threshold > MIN_THRESHOLD and self.prev_threshold < MAX_THRESHOLD):
            threshold = self.prev_threshold

        tries = 0
        while tries < MAX_TRIES:
            _, diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
            #cv2.imshow("Threshold", cv2.cvtColor(diff_thr, cv2.COLOR_GRAY2BGR))
            img_conv = cv2.cvtColor(diff_thr, cv2.COLOR_BGR2GRAY)

            pixels = cv2.countNonZero(img_conv)
            
            if pixels == 0:
                step = 1
                if step == 0:
                    step = 1
                threshold -= step 
                print(f"Found no pixels, decreasing threshold to {threshold}")
                if threshold < MIN_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue
                
            if pixels > 100:
                step = 1
                if step == 0:
                    step = 1
                threshold += step
                print(f"Found {pixels} pixels, increasing threshold to {threshold}")
                if threshold > MAX_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue
            
            print(f"Found <100 highest pixels, threshold={threshold}")

            # find countours
            circles = cv2.HoughCircles(img_conv, cv2.HOUGH_GRADIENT, 1, minDist=50,
                                    param1=50,param2=2,minRadius=3,maxRadius=10)
            
            if circles is not None:
                for circle in circles[0,:]:
                    cv2.circle(img_conv, (int(circle[0]), int(circle[1])), int(circle[2]), (255, 0, 0), 1)
            
            cv2.imshow("Contours", img_conv)
            return ((1,1), img_conv)

        self.laser_coord = (1,1)
        return ((1,1),None)
    
    def find_laser_by_grayscale(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using a grayscale strategy.

        Parameters:
        img (cv2.UMat): The input image.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        return self.find_laser_by_threshold(normalized_gray_image)

    def find_laser_by_red_color(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using the red color channel.

        Parameters:
        img (cv2.UMat): The input image.
        hint (int): The threshold hint to use for the strategy.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        (_, _, R) = cv2.split(img)
        return self.find_laser_by_threshold(R)
    
    def find_laser_by_green_color(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using the green color channel.

        Parameters:
        img (cv2.UMat): The input image.
        hint (int): The threshold hint to use for the strategy.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        (_, G, _) = cv2.split(img)
        return self.find_laser_by_threshold(G)