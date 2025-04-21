# squid-game-doll

An attempt to create a "Red Light, Green Light" robot inspired by Squid Game TV series, using AI for player recognition and tracking.  A moving doll is used to signal the game phase.
First working version was demonstrated during Arduino Days 2025 in FabLab Bergamo (Italy). A future unit with a laser pan&tilt platform is foreseen in order to shoot moving players with a laser.

## Gameplay

Players are expected to line-up 8-10m from the screen, stand in line during registration where their faces are saved, then start moving towards the finish line during green light. If they move during red light, they are eliminated and a fixed sum is added to the prize pool.

| Game phase | Screen | Doll |
| -- | -- | -- |
| Loading screen | ![Loading screen](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/loading_screen.png?raw=true) | random to attract crowd |
| Registration (with 15s countdown) | ![registration](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/init.png?raw=true) | ![facing, no eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_init.png?raw=true) |
| Green light | ![registration](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/green_light.png?raw=true) | ![rotated, no eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_off.png?raw=true) |
| Red light | ![registration](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/red_light.png?raw=true) Note that player 1 has reached the finish line and is therefore green. | ![facing, red eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_on.png?raw=true) |
| Elimination | player play screenshot | ![facing, red eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_on.png?raw=true) |
| End game | prize distribution screenshot | ![facing, no eyes](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_init.png?raw=true) |

## Configuration screen

* Webcam typically have 16/10 aspect ratios, and the play area may be a limited zone of the webcam field of view. It is useful to define a *vision area* from the webcam feed in order to avoid non-players detections, mask unwanted areas and to provide more details for the neural network limited 640x640 resolution.
* To define *vision area*, one or more rectangles needs to be drawn on the screen (non-covered areas will be masked, i.e. to mask external lights).
* Example screenshot from config phase:
![config](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/config.png?raw=true)
* Bounding rectangle in yellow of the *vision area* will be fed to the NN after image processing + resizing.
* *Finish area*: player bounding box must intersect with finish area in order to be recognized as a winner. It can be drawn with rectangles like vision area.
* *Starting area*: player bounding box must intersect with starting area in order to be registered as a player initially. It can be drawn with rectangles like vision area.
* *Vision area* must intersect with finish and starting areas for the game to work properly.
* During config phase, some settings can be adjusted (confidence level, contrast adjustments) in the SETTINGS menu option.
* Live object detection & tracking performance can be checked, using the "Neural network preview" menu option.

## Open issues / Tasks

* ~~(DOLL) Build a 3D model for a doll with red LED eyes and moving head~~ 
* (VISION) How to combine laser red dot recognition requirements (low exposure) with players recognition requirements (normal exposure)
* (LASER SHOOTER) Maybe using a depth estimator model to calculate the angles rather than adjusting based on a video stream
* ~~(GAMEPLAY) How to terminate the game (finish line logic missing)~~ 
* ~~(GAMEPLAY) Have a player registration step or not ??~~
* (GAMEPLAY) Sensibility threshold to be shot is based on rectangle center movements, so large moves are authorized far from the camera, very little close to the camera. 
* (LASER SHOOTER) Speed of laser pointing - slow to converge, about 10-15 s
* (Various) Software quality: github actions for python packaging, some basic automated tests
 
## Hardware

* Installation on Raspberry PI 5 with AI KIT, see dedicated file [INSTALL.md](https://github.com/fablab-bergamo/squid-game-doll/blob/main/INSTALL.md). A PC can be used instead (best experience with CUDA GPU support)
* ESP32C2 MINI Wemos board for servo control and doll control with Micropython (see esp32 folder)
* Logitech webcam HD PRO Webcam C920 on Windows 11 / Raspberry PI 5
* 1 x SG90 servomotor for head animation
* 2 red LED for eyes animation
* 3D printable parts available in <code>hardware/doll-model</code>

For laser shooter (not yet working)
* 2 x SG90 servomotors
* Pan-and-tilt platform (11 EUR): https://it.aliexpress.com/item/1005005666356097.html?spm=a2g0o.order_list.order_list_main.41.47a73696V4aDQn&gatewayAdapt=glo2ita
* Laser holder 3D printable part : see <code>hardware/proto/Laser Holder v6.stl</code>
* Either green laser 5mW (11 EUR) : https://aliexpress.com/item/1005005346537253.html . This model has high luminiosity with respect to red laser, but has poor focus. This may be better for eye safety.
* or Red laser 5mW (3 EUR) : https://aliexpress.com/item/1005008087745092.html . This model has good focus.

## Dev tools used in this project 

* VS Code with Python extension
* Thonny for ESP32 development (download here : [https://thonny.org/](https://thonny.org/))
* Python 3.11/3.12 with main libraries opencv, ultralytics, hailo, numpy, pygame. 

## Geometry of play space

* Expected play area 10 x 10 m indoor
* In order to hit a 50 cm wide target @ 10m the laser shall be precise 2.8° in horizontal axis. This should be doable with standard servos and 3D-printed pan&tilt platform for the laser (see hardware folder).

## AI 

* For more details about the neural network model used for player recognition & tracking, see this [article](https://www.fablabbergamo.it/2025/03/30/primi-passi-con-lai-raspberry-pi-5-hailo/).

## (VISION) Detecting the red laser dot

In order to reliably point the laser to the eliminated player, laser dot position must be acquired, positioning error calculated, and angles corrected accordingly.
In the example picture below, red laser dot is found on the webcam and a visor is added on top of predicted position.

![image](https://github.com/user-attachments/assets/b3f5dd56-1ecf-4783-9174-87988d44a1f1)

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

## The game itself

Using pygame as rendering engine see game.py

![image](https://github.com/user-attachments/assets/4f3aed2e-ce2e-4f75-a8dc-2d508aff0b47)

### Player detection (YOLO model)

* On PC, YOLO v8 medium with tracking see players_tracker.py. Performance w/ CUDA RTX2060 30fps, on AMD CPU 3fps.
* On Raspberry, evaluating YOLOV11m (approx 10 fps)
* YOLO model returns bounding rectangles with class person around players. The center of the rectangle is memorized and shouldnt move above a fixed pixel threshold around 15 px.
* Pre-compiled models available for Hailo 8L (AI KIT on Raspberry) : https://github.com/hailo-ai/hailo_model_wzoo/blob/master/docs/public_models/HAILO8L/HAILO8L_object_detection.rst

### Face detection for player board

* mediapipe / FaceDetection see FaceExtractor.py
* Used to create the player tiles on the left part of the screen
* Quite slow, running on CPU

### How to install/run on PC (see INSTALL.MD for Raspberry)

* Install poetry and let him do the installation of packages into a venv.

```bash
pip install poetry
poetry install
```

* Install CUDA support for NVIDIA GPU (facultative)

```bash
poetry run pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
```

* Command-line settings

```shell
usage: run.py [-h] [-m MONITOR] [-w WEBCAM] [-k] [-i IP] [-j JOYSTICK] [-n MODEL] [-c CONFIG] [-s]

options:
  -h, --help            show this help message and exit
  -m MONITOR, --monitor MONITOR
                        0-based index of the monitor
  -w WEBCAM, --webcam WEBCAM
                        0-based index of the webcam
  -k, --killer          enable or disable the esp32 laser shooter
  -i IP, --tracker-ip IP
                        sets the esp32 tracker IP address
  -j JOYSTICK, --joystick JOYSTICK
                        sets the joystick index
  -n MODEL, --neural_net MODEL
                        specify neural network model file for player recognition
  -c CONFIG, --config CONFIG
                        specify config file (defaults to config.yaml)
  -s, --setup           go to setup mode
```

* Example: configure the vision area for webcam, finish and starting areas (will generate a config.yaml file)

```bash
poetry run python -m src.squid_game_doll.run --setup
```

* Example: run game with default configuration file

```bash
poetry run python -m src.squid_game_doll.run
```

* Example: run game on forced monitor 0, webcam 0, enable esp32 laser kills, esp32 on IP=192.168.45.50

```bash
poetry run python -m src.squid_game_doll.run -m 0 -w 0 -k -i 192.168.45.50
```

* Example: setup the areas using webcam at index 0

```bash
poetry run python -m src.squid_game_doll.run --setup -w 0
```

## How to profile Python and check what is slow

* Use cProfile + snakeviz

```bash
poetry install --with dev
poetry run python -m cProfile -o game.prof -m src.squid_game_doll.run
poetry run snakeviz .\game.prof
```

## Webcam info

* https://forum.opencv.org/t/opencv-camera-low-fps/567/4
* Camera indexes are dependent on capabilities (CAP_DSHOW and CAP_V4L2)
