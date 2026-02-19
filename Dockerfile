FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV COMFYUI_PATH=/comfyui

RUN apt-get update && apt-get install -y git wget && rm -rf /var/lib/apt/lists/*

# Install ComfyUI + RunPod SDK (lightweight image, models download at first boot)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFYUI_PATH} && \
    cd ${COMFYUI_PATH} && \
    pip install -r requirements.txt && \
    pip install runpod requests

COPY handler.py /handler.py

CMD ["python", "/handler.py"]
