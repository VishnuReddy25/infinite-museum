import os
import uuid
from pathlib import Path

import torch
from diffusers import DiffusionPipeline
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn


MODEL_ID = os.environ.get("MUSEUM_IMAGE_MODEL", "black-forest-labs/FLUX.2-klein-4B")
HOST = os.environ.get("MUSEUM_IMAGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("MUSEUM_IMAGE_PORT", "7861"))
OUTPUT_DIR = Path(os.environ.get("MUSEUM_IMAGE_OUTPUT_DIR", "generated_images"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if DEVICE == "cuda" else torch.float32

app = FastAPI(title="Infinite Museum Image Backend")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=str(OUTPUT_DIR)), name="generated")


class GenerateRequest(BaseModel):
    model: str = Field(default=MODEL_ID)
    prompt: str
    width: int = 1024
    height: int = 1024
    num_inference_steps: int = 4
    guidance_scale: float = 3.5


def load_pipeline() -> DiffusionPipeline:
    pipe = DiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=DTYPE,
    )
    pipe = pipe.to(DEVICE)
    if DEVICE == "cuda":
        try:
            pipe.enable_model_cpu_offload()
        except Exception:
            pass
    return pipe


PIPE = load_pipeline()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_ID, "device": DEVICE}


@app.post("/generate")
def generate(request: GenerateRequest) -> dict:
    image = PIPE(
        prompt=request.prompt,
        width=request.width,
        height=request.height,
        num_inference_steps=request.num_inference_steps,
        guidance_scale=request.guidance_scale,
    ).images[0]

    file_name = f"{uuid.uuid4().hex}.png"
    file_path = OUTPUT_DIR / file_name
    image.save(file_path)

    return {
        "image_url": f"http://{HOST}:{PORT}/generated/{file_name}",
        "model": MODEL_ID,
        "device": DEVICE,
    }


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
