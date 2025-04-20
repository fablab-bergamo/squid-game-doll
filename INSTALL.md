# Setup on Raspberry Pi 5 + AI KIT

## Hardware

* Make sure Raspberry Pi 5 and AI KIT are configured properly
* Webcam is configured and visible. This has been tested with USB Camera but native Raspberry cam should be usable.

```shell
v4l2-ctl --list-devices
v4l2-ctl -v width=1920,height=1080,pixelformat=MJPG
v4l2-ctl --stream-mmap=3 --stream-to=/dev/null --stream-count=250
```

## Software

* Install HAILO software stack on Raspberry Pi:

```shell
sudo apt install hailo-all
sudo apt install python3-gi
sudo reboot
```

* Check Hailo chip is recognized with hailortcli command:

```shell
(.venv) $ hailortcli fw-control identify
Executing on device: 0000:01:00.0
Identifying board
Control Protocol Version: 2
Firmware Version: 4.20.0 (release,app,extended context switch buffer)
Logger Version: 0
Board Name: Hailo-8
Device Architecture: HAILO8L
Serial Number: xxxxxxxxxxxxxxx
Part Number: HM21LB1C2LAE
Product Name: HAILO-8L AI ACC M.2 B+M KEY MODULE EXT TMP
```

* Run install script to create venv and install Python requirements and HEF model

```shell
./install.sh
```

* Run run.py and check webcam index:

```shell
python ./src/squidgamesdolls/run.py
```

Sample output

```
Hello from the pygame community. https://www.pygame.org/contribute.html
SquidGame(res=(1920, 1080) on #0, tracker disabled=True, ip=192.168.45.50)
Listing webcams:
	 1820: pispbe-input
	 1821: pispbe-tdn_input
	 1822: pispbe-stitch_input
	 1823: pispbe-output0
	 1824: pispbe-output1
	 1825: pispbe-tdn_output
	 1826: pispbe-stitch_output
	 1827: pispbe-config
	 1828: pispbe-input
	 1829: pispbe-tdn_input
	 1830: pispbe-stitch_input
	 1831: pispbe-output0
	 1832: pispbe-output1
	 1833: pispbe-tdn_output
	 1834: pispbe-stitch_output
	 1835: pispbe-config
	 1819: rpivid
	 220: pispbe-input
	 221: pispbe-tdn_input
	 222: pispbe-stitch_input
	 223: pispbe-output0
	 224: pispbe-output1
	 225: pispbe-tdn_output
	 226: pispbe-stitch_output
	 227: pispbe-config
	 228: pispbe-input
	 229: pispbe-tdn_input
	 230: pispbe-stitch_input
	 231: pispbe-output0
	 232: pispbe-output1
	 233: pispbe-tdn_output
	 234: pispbe-stitch_output
	 235: pispbe-config
	 219: rpivid
```

* Start the game with forced webcam index (example: 200)

```shell
python ./src/squidgamesdolls/run.py -w 200
```
