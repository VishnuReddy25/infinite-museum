# Fine-Tuning Workflow

This folder contains the end-to-end starter pipeline for building a public-data-backed fine-tune for the Infinite Museum project.

## Goal

Fine-tune a small model so it becomes better at:

- generating consistent `world_bible` JSON
- keeping names, laws, and institutions coherent
- writing in the museum voice
- returning clean structured outputs

## Folder layout

- `schemas/`: exact JSON targets for each task
- `dataset_sources.json`: public source ideas and how to use them
- `generate_prompt_pool.py`: builds a pool of impossible-world concepts
- `fetch_public_prompt_sources.py`: pulls and normalizes seed concepts from public Hugging Face datasets
- `build_museum_examples.py`: converts concepts into museum-format JSONL
- `train_lora_modal.py`: Modal LoRA starter
- `requirements-train.txt`: training and data prep dependencies

## Recommended workflow

1. Create a prompt pool.
2. Review and trim the prompt pool to remove weak concepts.
3. Generate synthetic museum examples with a strong teacher model.
4. Hand-curate the best examples.
5. Fine-tune on the curated JSONL.
6. Evaluate base vs tuned model on a hidden prompt set.
7. Publish the tuned model to Hugging Face.

## Step-by-step

### 1. Install training dependencies

```bash
pip install -r training/requirements-train.txt
```

### 2. Pull public seed concepts

This step downloads premise-like rows from public Hugging Face datasets and rewrites them into concise concept candidates.

```bash
python training/fetch_public_prompt_sources.py \
  --output data/raw_prompts/public_world_concepts.jsonl \
  --per-source 120
```

### 3. Build a prompt pool

Prepare a CSV with at least one `concept` column, or use the built-in seed list.

```bash
python training/generate_prompt_pool.py \
  --output data/raw_prompts/world_concepts.jsonl \
  --public-input data/raw_prompts/public_world_concepts.jsonl \
  --count 200
```

Optional:

- add public-dataset-inspired prompts manually
- merge prompts from your team
- remove joke prompts that have no worldbuilding depth

### 4. Generate synthetic museum examples

This step converts each concept into one or more task examples:

- `world_bible`
- `artifacts`
- `timeline`
- `newspaper`
- `visitor_book`

You can point it at any teacher endpoint or local script later. The starter supports loading pre-generated teacher outputs too.

```bash
python training/build_museum_examples.py \
  --prompts data/raw_prompts/world_concepts.jsonl \
  --output-dir data/synthetic \
  --tasks world_bible artifacts timeline newspaper visitor_book
```

The script writes JSONL stubs if no teacher outputs are provided yet, so you can still inspect the exact training shape.

### 5. Curate a gold dataset

Create these files by keeping only high-quality rows:

- `data/final/world_bible_train.jsonl`
- `data/final/artifacts_train.jsonl`
- `data/final/timeline_train.jsonl`
- `data/final/newspaper_train.jsonl`
- `data/final/visitor_book_train.jsonl`

Target sizes:

- MVP: 80 to 150 examples
- Strong: 300 to 800 examples

If time is tight, fine-tune only `world_bible_train.jsonl`.

### 6. Fine-tune with Modal

Set env vars:

- `HF_TOKEN`
- `HF_USERNAME`
- `BASE_MODEL`
- `TRAIN_FILE`
- `OUTPUT_REPO`

Example:

```bash
set HF_TOKEN=hf_xxx
set HF_USERNAME=yourname
set BASE_MODEL=Qwen/Qwen2.5-3B-Instruct
set TRAIN_FILE=data/final/world_bible_train.jsonl
set OUTPUT_REPO=yourname/infinite-museum-worldbible-lora
modal run training/train_lora_modal.py
```

### 7. Evaluate

Hold out at least 20 prompts the model never saw in training.

Score both base and tuned model on:

- JSON validity
- world coherence
- specificity
- tone
- reuse of canon

### 8. Publish and integrate

- push the adapter or merged model to Hugging Face
- update the app runtime to use the tuned checkpoint
- record before/after examples for the hackathon report

## Public data strategy

Use public datasets as inspiration and seed material, not as direct final targets.

Recommended seed sources:

- `archit11/worldbuilding`
- `euclaise/writingprompts`
- `Dxniz/Novelist-CoT`
- `HeAAAAA/story_generation_sft`

See `dataset_sources.json` for notes.

## Practical recommendation

For the hackathon, the highest-value tuning target is:

- `concept -> world_bible`

That is the best place to improve structure, tone, and consistency with the least amount of data.
