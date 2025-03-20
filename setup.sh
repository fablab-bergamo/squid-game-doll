python -m venv .venv --system-site-packages
source .venv/bin/activate
pip install git+https://github.com/hailo-ai/hailo-apps-infra.git
pip install -r ./src/requirements
# Download some compiled HAILO8L model from https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO8L/HAILO8L_object_detection.rst
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov7e6.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11x.hef
# Fix FPS for logitech webcam
v4l2-ctl -v width=1920,height=1080