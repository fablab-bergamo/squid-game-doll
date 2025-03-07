# squid-game-doll
An attempt to create a "Red Light, Green Light" robot inspired by Squid Game TV series, using AI for player recognition and tracking.

# Geometry

* Expected play area 10 x 10 m indoor
* In order to hit a 50 cm wide target @ 10m the laser shall be precise 2.8° in horizontal axis. This should be doable with standard servos and 3D-printed pan&tilt platform for the laser (see hardware folder).

# Detecting the red laser dot

In order to reliably point the laser to the eliminated player, laser dot position must be acquired, positioning error calculated, and angles corrected accordingly.
In the example picture below, red laser dot is found on the webcam and a visor is added on top of predicted position.

![image](https://github.com/user-attachments/assets/b3f5dd56-1ecf-4783-9174-87988d44a1f1)


## Tools used

* Python 3.11, libraries Numpy, OpenCV-python. See laser-pict-gen.py

```shell
pip install opencv-python numpy
```
* Logitech webcam HD PRO Webcam C920 on Windows 11

* Green laser 5mW (11 EUR) : https://aliexpress.com/item/1005005346537253.html . This model has high luminiosity with respect to red laser, but has poor focus. This may be better for eye safety.

* Red laser 5mW (3 EUR) : https://aliexpress.com/item/1005008087745092.html . This model has good focus.

* ESP32C2 MINI Wemos board for servo control.

## Current approach

* Choose a channel from the webcam picture (R,G,B) or convert to grayscale. 

* Apply a threshold to the picture to find the brightest pixels

```python
diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
```

Resulting image:

![image](https://github.com/user-attachments/assets/5bef5984-6bc9-4310-a7bd-8a4e4634ca12)

* Increase remaining spots with dilate (a key ingredient!!)

```python
masked_channel = cv2.dilate(masked_channel, None, iterations=4)
```

Resulting image:

![image](https://github.com/user-attachments/assets/336c67bc-ccb0-4f91-9eda-7e0f3152b8e3)

* Look for circles using Hough Transform

```python
circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                                param1=50,param2=2,minRadius=3,maxRadius=10)
```

param2 is a very sensitive parameter. minRadius and maxRadius are dependent on webcam resolution and dilate step.

* If the circles found are more than one, increase threshold (dichotomy search) and retry.
* If no circles are found, decrease threshold (dichotomy search) and retry
* If threshold limits are reached, exit reporting no laser
* If exactly one circle is found, exit reporting the circle center coordinates

## What is tricky about laser recognition

* *Exposure of the webcam* is very important:

If picture is too bright (autosettings tend to produce very bright images), laser detection fails. For this reason, webcam is set to manual exposure and underexposed. Probably, an exposure calibration step is required until the picture has the right average brightness. With Logitech C920 results are OK in interior room with exposure around (-10, -5) @ 920x720 resolution. This will vary with different webcam.

| Overexposure (-4) | Under-exposure (-11) |
| -- | -- |
| ![image](https://github.com/user-attachments/assets/970ebd68-ed88-4cae-9aec-5cdea090d67a) | ![image](https://github.com/user-attachments/assets/c05399e9-55eb-413e-bc1f-bd2ac2f9e174) |
| ![image](https://github.com/user-attachments/assets/da60a5f8-7516-4530-99ba-a4e7c5e1b815) (threshold) | ![image](https://github.com/user-attachments/assets/f7b11868-5535-4285-9b7c-822c3c1f62e0) (after dilate) |

* Exposure is somehow dependent on resolution requested and FPS requested to the webcam. I fixed the parameters in the webcam initialization step to avoid variability.

* Some surfaces absorb more light than other resulting in brightest spot not being the laser. Additional search algorithms to be tested (e.g. checking maximum R to G / R to B color ratios)
  
* Green laser seem to work better than Red laser on many surfaces. But it may be my Aliexpress green laser is more powerful.
  
* Try-and-error loop is slow - another approach which helped me speed up testing is to generate pictures by adding fake laser spots (ellipsis with variable red/brightness) and compare actual position with predicted precisions.

## Dev notes regarding laser detection

* Very slow startup on x64 / Windows 11 fixed by

```python
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2
```

* Image processing techniques that did not work
  
| Attempt | Why it failed | What could be done |
| -- | -- | -- |
| Switching on the laser programmatically and substract images to find the spot | Even without buffer, webcam images have latency > 250 ms resulting in difference images having lots of pixels especially with persons in the scene | Solve webcam latency and retry with fast laser switch (>25Hz?). Check if the laser really turns off immediately. |
| Laplace transform to find rapid variations around the spot | It's more for contour detection and it finds a lot of rapid variations in normal interior scenes, or faces | ??? |
| HSV thresholds based on fixed value | Red laser is not fully red on the picture, white is present at the center | Implement adaptive adaptation on V value? |

## Game itself

Using pygame as rendering engine see game.py

![image](https://github.com/user-attachments/assets/4f3aed2e-ce2e-4f75-a8dc-2d508aff0b47)


### Player detection

* YOLO v8 medium with tracking see players_tracker.py. Performance w/ CUDA RTX2060 30fps, on AMD CPU 3fps.
* YOLO returns bounding rectangles with class person around players. The center of the rectangle is memorized and shouldnt move above a fixed pixel threshold around 10 px.

### Face detection

* mediapipe / FaceDetection see face_extractor.py
* Used to create the player tiles on the left part of the screen

## How to install

* Install requirements from list in src directory

```python
pip install -r ./src/requirements.txt
```

* Run game

```python
python ./src/squidgamedoll/game.py
```

## How to profile

* Use cProfile + snakeviz

```python
pip install snakeviz
python -m cProfile -o game.prof  .\src\squidgamesdoll\game.py
snakeviz .\game.prof
```

### Open issues

* Reliability of player detections ; players must be visible at all time (occlusions not tested)
* Have a player registration step or not
* Sensibility threshold is pixel based, so large moved are authorized far from the camera, very little close to the camera
* Speed of laser pointing
* Python packaging
* Speed of YOLOv8-m (around 300 ms per frame on PC)

### Hardware

* RaspberryPi 5 with AI KIT or Jetson Orin Nano 
