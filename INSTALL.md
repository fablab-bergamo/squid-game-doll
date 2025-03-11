# Setup on Raspberry Pi 5 + AI KIT

## Hardware

* Make sure Raspberry Pi 5 and AI KIT are configured properly
* Webcam (USB) is configured and visible

## Software

* Install HAILO software on Raspberry Pi

```shell
sudo apt install hailo-all
sudo apt install python3-gi
sudo reboot
```

* Run install script to create venv and install requirements

```shell
./install.sh
```

* Run SquidGame.py and check webcam index

```shell
python ./src/squidgamesdolls/SquidGame.py
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

* Run SquidGame.py with forced webcam index (example: 200)

```shell
python ./src/squidgamesdolls/SquidGame.py -w 200
```
