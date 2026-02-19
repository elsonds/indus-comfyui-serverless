#!/bin/bash
set -e

echo "[Start] Installing ComfyUI + dependencies..."

# Install ComfyUI if not already present (Flash Boot will cache this)
if [ ! -d "/comfyui/main.py" ]; then
    git clone https://github.com/comfyanonymous/ComfyUI.git /comfyui 2>/dev/null || true
    cd /comfyui && pip install -q -r requirements.txt
fi

pip install -q runpod requests

# Download handler from GitHub
wget -q -O /handler.py https://raw.githubusercontent.com/elsonds/indus-comfyui-serverless/master/handler.py

echo "[Start] Starting handler..."
python /handler.py
