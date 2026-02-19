FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget libgl1-mesa-glx libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

RUN git clone https://github.com/comfyanonymous/ComfyUI.git /comfyui && \
    cd /comfyui && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir runpod requests

COPY handler.py /handler.py

CMD ["python", "/handler.py"]
