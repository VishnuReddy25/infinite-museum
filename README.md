---
title: Infinite Museum of Impossible Worlds
emoji: 🏛️
colorFrom: gray
colorTo: yellow
sdk: gradio
sdk_version: 5.29.0
python_version: 3.11
app_file: app.py
pinned: true
license: mit
short_description: AI museum of impossible worlds
---

# Infinite Museum of Impossible Worlds

An atmospheric Gradio app that turns a single impossible-world prompt into a five-hall museum experience:

- Lobby
- Artifacts
- Timeline
- Newspaper
- Visitor's Book

Recent UI work adds a curated hall rail, world-specific atmospheric shifts, generated emblems, and collectible share-card exports.

## Architecture

The app generates a canonical `world_bible` first, then uses it to keep every hall consistent.

The text stack now supports role-based model routing:

- `world` model: structured world bible generation
- `hall` model: artifacts, timeline, newspaper
- `guide` model: lighter human-facing writing such as visitor-book style output

Runtime modes:

- `MUSEUM_RUNTIME=local` loads the model directly inside the Space or local environment.
- `MUSEUM_RUNTIME=hub` uses hosted inference, and the `world` route can attach your published LoRA through `MUSEUM_ADAPTER_ID`.
- `MUSEUM_RUNTIME=llamacpp` connects the app to a local `llama.cpp` OpenAI-compatible server.

## Recommended models

Default:

- `Qwen/Qwen2.5-7B-Instruct`

Recommended split:

- `MUSEUM_WORLD_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `MUSEUM_HALL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `MUSEUM_GUIDE_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`

Planned hackathon targets:

- `Qwen/Qwen3-8B`
- a GGUF build served through `llama.cpp` for the final badge-aligned deployment

## Environment variables

- `MUSEUM_RUNTIME=local`
- `MUSEUM_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `MUSEUM_WORLD_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `MUSEUM_HALL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `MUSEUM_GUIDE_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `MUSEUM_ADAPTER_ID=VishnuReddy25/infinite-museum-lora` applies to the `world` route in `hub` and `local` runtimes
- `HF_TOKEN=...` only required when `MUSEUM_RUNTIME=hub`
- `LLAMACPP_BASE_URL=http://127.0.0.1:8080`
- `LLAMACPP_MODEL=museum-gguf`
- `LLAMACPP_WORLD_MODEL=museum-world-gguf`
- `LLAMACPP_HALL_MODEL=museum-hall-gguf`
- `LLAMACPP_GUIDE_MODEL=museum-guide-gguf`
- `LLAMACPP_API_KEY=` optional unless your local server expects one
- `MUSEUM_IMAGE_RUNTIME=disabled`, `local`, or `backend`
- `MUSEUM_IMAGE_BASE_URL=http://127.0.0.1:7861` only for `backend`
- `MUSEUM_IMAGE_MODEL=black-forest-labs/FLUX.2-klein-4B`
- `MUSEUM_IMAGE_API_KEY=` optional unless your image backend expects one
- `MUSEUM_IMAGE_OUTPUT_DIR=generated_images`

## Local run

```bash
pip install -r requirements.txt
python app.py
```

## llama.cpp run

If you have already converted your tuned model to GGUF, start a local OpenAI-compatible server first:

```bash
llama-server -m /path/to/your-model.gguf --ctx-size 8192 --port 8080
```

Then set:

```bash
set MUSEUM_RUNTIME=llamacpp
set LLAMACPP_BASE_URL=http://127.0.0.1:8080
set LLAMACPP_MODEL=museum-gguf
set LLAMACPP_WORLD_MODEL=museum-world-gguf
set LLAMACPP_HALL_MODEL=museum-hall-gguf
set LLAMACPP_GUIDE_MODEL=museum-guide-gguf
python app.py
```

## Multi-model routing

If you want a single model for everything, set only:

```bash
set MUSEUM_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
```

If you want the hackathon-oriented split, set:

```bash
set MUSEUM_WORLD_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
set MUSEUM_HALL_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
set MUSEUM_GUIDE_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
set MUSEUM_ADAPTER_ID=VishnuReddy25/infinite-museum-lora
```

Current task routing:

- `generate_world_bible()` -> `world`
- `generate_artifacts()` -> `hall`
- `generate_timeline()` -> `hall`
- `generate_newspaper()` -> `hall`
- `generate_visitor_book()` -> `guide`

## Featured artifact images

The artifact hall now has a featured image slot. By default it shows the generated image prompt and a placeholder panel.

For the simplest Space-style setup, let the app generate images directly from `app.py`:

```bash
pip install -r requirements-image.txt
set MUSEUM_IMAGE_RUNTIME=local
set MUSEUM_IMAGE_MODEL=black-forest-labs/FLUX.2-klein-4B
python app.py
```

This uses the local helper in [generators/image_engine.py](/C:/Users/vishn/OneDrive/Desktop/infinite-museum/generators/image_engine.py) and saves images into `generated_images/`.

If you still want an external image service later, you can keep using the optional backend mode below.

To connect a local image backend later, expose a simple HTTP endpoint:

- `POST /generate`
- request body:

```json
{
  "model": "black-forest-labs/FLUX.2-klein-4B",
  "prompt": "museum artifact photograph ...",
  "width": 1024,
  "height": 1024,
  "num_inference_steps": 4,
  "guidance_scale": 3.5
}
```

- response body:

```json
{
  "image_url": "http://127.0.0.1:7861/generated/example.png"
}
```

Then set:

```bash
set MUSEUM_IMAGE_RUNTIME=backend
set MUSEUM_IMAGE_BASE_URL=http://127.0.0.1:7861
set MUSEUM_IMAGE_MODEL=black-forest-labs/FLUX.2-klein-4B
python app.py
```

## Local FLUX image server

This repo now includes a tiny local image server in [image_backend.py](/C:/Users/vishn/OneDrive/Desktop/infinite-museum/image_backend.py) that matches the museum app's `/generate` contract.

Install the image dependencies:

```bash
pip install -r requirements-image.txt
```

Run the server:

```bash
set MUSEUM_IMAGE_MODEL=black-forest-labs/FLUX.2-klein-4B
python image_backend.py
```

Optional environment variables:

- `MUSEUM_IMAGE_HOST=127.0.0.1`
- `MUSEUM_IMAGE_PORT=7861`
- `MUSEUM_IMAGE_OUTPUT_DIR=generated_images`

Then start the museum app with:

```bash
set MUSEUM_IMAGE_RUNTIME=backend
set MUSEUM_IMAGE_BASE_URL=http://127.0.0.1:7861
set MUSEUM_IMAGE_MODEL=black-forest-labs/FLUX.2-klein-4B
python app.py
```

Quick backend check:

```bash
curl http://127.0.0.1:7861/health
```
