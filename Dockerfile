FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV COMFYUI_PATH=/comfyui

# Install system dependencies
RUN apt-get update && apt-get install -y git wget && rm -rf /var/lib/apt/lists/*

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFYUI_PATH} && \
    cd ${COMFYUI_PATH} && \
    pip install -r requirements.txt && \
    pip install runpod requests

# Download models (baked into image = fast cold starts)
# Diffusion model (~10GB bf16)
RUN wget -q --show-progress -O ${COMFYUI_PATH}/models/diffusion_models/qwen_image_2512_bf16.safetensors \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_2512_bf16.safetensors"

# Text encoder
RUN wget -q --show-progress -O ${COMFYUI_PATH}/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"

# VAE
RUN wget -q --show-progress -O ${COMFYUI_PATH}/models/vae/qwen_image_vae.safetensors \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"

# LoRA - Indus style
RUN wget -q --show-progress -O ${COMFYUI_PATH}/models/loras/indus-style.safetensors \
    "https://huggingface.co/ArceusInception/iis/resolve/main/indus-style.safetensors"

# Copy handler
COPY handler.py /handler.py

CMD ["python", "/handler.py"]
