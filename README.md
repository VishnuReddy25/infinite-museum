---
title: Infinite Museum of Impossible Worlds
emoji: "🏛️"
colorFrom: gray
colorTo: yellow
sdk: gradio
python_version: 3.11

app_file: app.py
pinned: true
license: mit
sdk: gradio
sdk_version: 5.0.0

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

## Local run

```bash
pip install -r requirements.txt
python app.py
```
