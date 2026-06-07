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

## Architecture

The app generates a canonical `world_bible` first, then uses it to keep every hall consistent.

Runtime modes:

- `MUSEUM_RUNTIME=local` loads the model directly inside the Space or local environment.
- `MUSEUM_RUNTIME=hub` uses hosted inference as a fallback during development.
- `MUSEUM_RUNTIME=llamacpp` connects the app to a local `llama.cpp` OpenAI-compatible server.

## Recommended model

Default:

- `Qwen/Qwen2.5-7B-Instruct`

Planned hackathon targets:

- `Qwen/Qwen3-8B`
- a GGUF build served through `llama.cpp` for the final badge-aligned deployment

## Environment variables

- `MUSEUM_RUNTIME=local`
- `MUSEUM_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `HF_TOKEN=...` only required when `MUSEUM_RUNTIME=hub`
- `LLAMACPP_BASE_URL=http://127.0.0.1:8080`
- `LLAMACPP_MODEL=museum-gguf`
- `LLAMACPP_API_KEY=` optional unless your local server expects one

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
python app.py
```
