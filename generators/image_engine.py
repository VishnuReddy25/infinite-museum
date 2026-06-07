import os
from functools import lru_cache
from pathlib import Path


IMAGE_MODEL = os.environ.get("MUSEUM_IMAGE_MODEL", "black-forest-labs/FLUX.2-klein-4B")
IMAGE_OUTPUT_DIR = Path(os.environ.get("MUSEUM_IMAGE_OUTPUT_DIR", "generated_images"))


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
    pipe = pipe.to(device)
    return pipe, device


def generate_image(prompt: str, width: int = 1024, height: int = 1024, num_inference_steps: int = 4, guidance_scale: float = 3.5) -> dict:
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
