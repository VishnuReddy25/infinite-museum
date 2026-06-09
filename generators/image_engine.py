import os
from functools import lru_cache
from pathlib import Path

try:
    import spaces
    GPU = spaces.GPU
except Exception:
    def GPU(fn):
        return fn


IMAGE_MODEL = os.environ.get("MUSEUM_IMAGE_MODEL", "black-forest-labs/FLUX.2-klein-4B")
IMAGE_OUTPUT_DIR = Path(os.environ.get("MUSEUM_IMAGE_OUTPUT_DIR", "generated_images"))
IMAGE_WIDTH = int(os.environ.get("MUSEUM_IMAGE_WIDTH", "768"))
IMAGE_HEIGHT = int(os.environ.get("MUSEUM_IMAGE_HEIGHT", "768"))
IMAGE_STEPS = int(os.environ.get("MUSEUM_IMAGE_STEPS", "6"))
IMAGE_GUIDANCE = float(os.environ.get("MUSEUM_IMAGE_GUIDANCE", "3.0"))


@lru_cache(maxsize=1)
def _load_pipeline():
    import torch
    from diffusers import DiffusionPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    pipe = DiffusionPipeline.from_pretrained(
        IMAGE_MODEL,
        torch_dtype=dtype,
    )

    if device == "cuda":
        try:
            pipe.enable_model_cpu_offload()
        except Exception:
            pipe = pipe.to(device)
    else:
        pipe = pipe.to(device)

    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()
    return pipe, device


@GPU
def generate_image(
    prompt: str,
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
    num_inference_steps: int = IMAGE_STEPS,
    guidance_scale: float = IMAGE_GUIDANCE,
) -> dict:
    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        pipe, device = _load_pipeline()
        image = pipe(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        ).images[0]
    except Exception as exc:
        return {"error": f"Local image generation failed: {exc}"}

    file_name = f"artifact_{abs(hash(prompt))}.png"
    file_path = IMAGE_OUTPUT_DIR / file_name
    image.save(file_path)

    return {
        "image_path": str(file_path.resolve()),
        "model": IMAGE_MODEL,
        "device": device,
    }
