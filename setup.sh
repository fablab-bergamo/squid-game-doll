python -m venv .venv --system-site-packages
source .venv/bin/activate
pip install git+https://github.com/hailo-ai/hailo-apps-infra.git
pip install -r ./src/requirements
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
