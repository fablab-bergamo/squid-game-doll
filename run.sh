#!/bin/bash
source .venv/bin/activate
# python ./src/squidgamesdoll/run.py --setup
python ./src/squidgamesdoll/run.py -m 0 -j 0 -w 0 -k -i 192.168.45.90 -md yolov11m.hef 
