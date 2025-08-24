pip install poetry
poetry install
poetry run pip install git+https://github.com/hailo-ai/hailo-apps-infra.git

# Download some compiled HAILO8L model from https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO8L/HAILO8L_object_detection.rst
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov7e6.hef
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11x.hef

# Download YOLOv5l6 Laser Spot Detection Model
# From: https://zenodo.org/records/10471835 - Neural Network Laser Spot Tracking
echo "Downloading YOLOv5l6 laser spot detection model..."
wget -O yolov5l6_e200_b8_tvt302010_laser_v5.pt "https://zenodo.org/records/10471835/files/yolov5l6_e200_b8_tvt302010_laser_v5.pt?download=1"
echo "Laser model download completed."
