#!/bin/bash
# Jetson Orin Setup Script - Prevents Poetry from overwriting torch

echo "🧹 Cleaning Poetry environment..."
poetry env remove python 2>/dev/null || true
rm poetry.lock 2>/dev/null || true

echo "📦 Installing base dependencies..."
poetry install

echo "🚀 Installing Jetson-optimized PyTorch..."
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl

echo "🤖 Installing Ultralytics without dependencies..."
poetry run pip install ultralytics --no-deps

echo "⚡ Installing ONNX Runtime GPU..."
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl

echo "🔍 Installing missing ultralytics dependencies..."
poetry run pip install tqdm seaborn psutil py-cpuinfo thop requests PyYAML

echo "✅ Verifying CUDA support..."
poetry run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"

echo "🎮 Ready to run: poetry run python -m squid_game_doll --setup"