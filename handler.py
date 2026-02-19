"""
RunPod Serverless Handler for ComfyUI - Indus Image Generator

Uses models from the Indus network volume mounted at /runpod-volume.
Symlinks ComfyUI model dirs to the volume so ComfyUI finds them.
"""

import runpod
import time
import base64
import requests
import subprocess
import os
import sys
import threading

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_PATH = "/comfyui"
VOLUME_MODELS = "/runpod-volume/ComfyUI/models"


def log(msg):
    print(f"[Handler] {msg}", flush=True)


def link_models():
    """Symlink model directories from network volume into ComfyUI."""
    local_models = f"{COMFYUI_PATH}/models"
    dirs_to_link = [
        "diffusion_models",
        "text_encoders",
        "vae",
        "loras",
        "clip",
        "unet",
        "controlnet",
        "checkpoints",
    ]
    for d in dirs_to_link:
        src = os.path.join(VOLUME_MODELS, d)
        dst = os.path.join(local_models, d)
        if os.path.exists(src):
            if os.path.exists(dst) and not os.path.islink(dst):
                os.rename(dst, dst + ".bak")
            elif os.path.islink(dst):
                os.remove(dst)
            os.symlink(src, dst)
            log(f"Linked {d} -> {src}")
        else:
            log(f"Volume dir not found: {src}")


def start_comfyui():
    """Start ComfyUI and block until ready."""
    try:
        r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
        if r.status_code == 200:
            log("ComfyUI already running")
            return True
    except Exception:
        pass

    log(f"Starting ComfyUI from {COMFYUI_PATH}...")
    process = subprocess.Popen(
        [
            sys.executable, "main.py",
            "--listen", "0.0.0.0",
            "--port", "8188",
            "--disable-auto-launch",
        ],
        cwd=COMFYUI_PATH,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    def _stream():
        for line in iter(process.stdout.readline, b""):
            text = line.decode("utf-8", errors="ignore").strip()
            if text:
                log(f"ComfyUI: {text[:300]}")

    threading.Thread(target=_stream, daemon=True).start()

    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
            if r.status_code == 200:
                log("ComfyUI is ready!")
                return True
        except Exception:
            pass
        time.sleep(2)

    log("ComfyUI failed to start within 300s")
    return False


def queue_prompt(workflow):
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=30)
    return r.json()


def get_history(prompt_id):
    r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
    return r.json()


def get_image(filename, subfolder="", folder_type="output"):
    r = requests.get(
        f"{COMFYUI_URL}/view",
        params={"filename": filename, "subfolder": subfolder, "type": folder_type},
        timeout=30,
    )
    return r.content


def wait_for_result(prompt_id, timeout=300):
    """Poll ComfyUI history until the prompt finishes."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            history = get_history(prompt_id)
            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {}).get("status_str", "")
                if status == "error":
                    msg = entry.get("status", {}).get("exception_message", "unknown")
                    raise RuntimeError(f"ComfyUI execution error: {msg}")
                outputs = entry.get("outputs", {})
                for node_output in outputs.values():
                    if "images" in node_output:
                        return node_output["images"]
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"Generation timed out after {timeout}s")


def handler(event):
    """
    Input:  {"input": {"workflow": { ...ComfyUI API workflow... }}}
    Output: {"image": "base64...", "filename": "...", "prompt_id": "..."}
    """
    try:
        job_input = event.get("input", {})
        workflow = job_input.get("workflow")
        if not workflow:
            return {"error": "No workflow provided"}

        log(f"Received workflow with {len(workflow)} nodes")

        log("Queuing workflow...")
        resp = queue_prompt(workflow)
        if "error" in resp:
            return {"error": f"Queue error: {resp['error']}"}

        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            return {"error": f"No prompt_id returned: {resp}"}
        log(f"Prompt ID: {prompt_id}")

        images = wait_for_result(prompt_id, timeout=300)
        if not images:
            return {"error": "No images generated"}

        img = images[0]
        log(f"Downloading {img['filename']}...")
        data = get_image(img["filename"], img.get("subfolder", ""), img.get("type", "output"))
        b64 = base64.b64encode(data).decode("utf-8")
        log(f"Done. Image {len(data)} bytes")

        return {"image": b64, "filename": img["filename"], "prompt_id": prompt_id}

    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# === Startup sequence ===
log("=== Indus ComfyUI Serverless Handler ===")

log("Step 1: Link models from network volume...")
if os.path.exists(VOLUME_MODELS):
    link_models()
else:
    log(f"WARNING: Volume not mounted at {VOLUME_MODELS}")
    log("Models must be in the container image or downloads will fail.")

log("Step 2: Start ComfyUI...")
if not start_comfyui():
    log("FATAL: ComfyUI failed to start. Exiting.")
    sys.exit(1)

log("Step 3: Ready! Starting RunPod serverless listener...")
runpod.serverless.start({"handler": handler})
