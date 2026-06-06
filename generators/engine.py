import json
import os
import re
from functools import lru_cache

from dotenv import load_dotenv

try:
    import spaces
    GPU = spaces.GPU
except Exception:
    def GPU(fn):
        return fn

from generators.prompts import (
    ARTIFACTS_PROMPT,
    HALL_RULES,
    NEWSPAPER_PROMPT,
    SYSTEM_PROMPT,
    TIMELINE_PROMPT,
    VISITOR_BOOK_PROMPT,
    WORLD_BIBLE_PROMPT,
    WORLD_BIBLE_SCHEMA_TEXT,
)

load_dotenv()

# Enable fast multi-threaded downloads on HuggingFace Spaces
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("HF_HUB_CACHE", "/data/huggingface")

MODEL_ID = os.environ.get("MUSEUM_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
RUNTIME = os.environ.get("MUSEUM_RUNTIME", "local").lower()
HF_TOKEN = os.environ.get("HF_TOKEN")


def extract_json(text: str) -> dict:
    """Extract a JSON object from a model response."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except Exception:
            pass

    return {"error": "Could not parse JSON", "raw": text[:500]}


@lru_cache(maxsize=1)
def _load_local_pipeline():
    from transformers import pipeline

    return pipeline(
        "text-generation",
        model=MODEL_ID,
        device_map="auto",
        torch_dtype="auto",
    )


@lru_cache(maxsize=1)
def _load_hf_client():
    from huggingface_hub import InferenceClient

    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is required when MUSEUM_RUNTIME=hub.")
    return InferenceClient(api_key=HF_TOKEN)


@GPU
def _generate_with_local(messages: list[dict], max_new_tokens: int) -> str:
    pipe = _load_local_pipeline()
    output = pipe(
        messages,
        max_new_tokens=max_new_tokens,
        max_length=None,
        temperature=0.8,
        do_sample=True,
        return_full_text=False,
    )
    if not output:
        return ""
    first = output[0]
    generated = first.get("generated_text", "")
    if isinstance(generated, list):
        return generated[-1].get("content", "").strip()
    return str(generated).strip()


def _generate_with_hub(messages: list[dict], max_new_tokens: int) -> str:
    client = _load_hf_client()
    completion = client.chat_completion(
        model=MODEL_ID,
        messages=messages,
        max_tokens=max_new_tokens,
        temperature=0.8,
    )
    return completion.choices[0].message.content.strip()


def call_llm(prompt: str, max_new_tokens: int = 900) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    text = ""
    try:
        if RUNTIME == "hub":
            text = _generate_with_hub(messages, max_new_tokens)
        else:
            text = _generate_with_local(messages, max_new_tokens)

        print(f"[LLM RAW] {text[:300]}")
        parsed = extract_json(text)
        if "error" in parsed:
            raise ValueError(parsed["error"])
        return parsed
    except Exception as exc:
        print(f"[LLM ERROR] {exc}")
        return {"error": str(exc), "raw": text[:300]}


def _world_bible_text(world_bible: dict) -> str:
    return json.dumps(world_bible, indent=2, ensure_ascii=True)


def _limit_list(payload: dict, key: str, size: int) -> dict:
    items = payload.get(key)
    if isinstance(items, list):
        payload[key] = items[:size]
    return payload


def generate_world_bible(concept: str) -> dict:
    return call_llm(
        WORLD_BIBLE_PROMPT.format(
            concept=concept,
            schema=WORLD_BIBLE_SCHEMA_TEXT,
        ),
        max_new_tokens=1100,
    )


def generate_artifacts(concept: str, world_bible: dict) -> dict:
    payload = call_llm(
        ARTIFACTS_PROMPT.format(
            concept=concept,
            world_bible=_world_bible_text(world_bible),
            hall_rules=HALL_RULES,
        ),
        max_new_tokens=900,
    )
    return _limit_list(payload, "artifacts", 3)


def generate_timeline(concept: str, world_bible: dict) -> dict:
    payload = call_llm(
        TIMELINE_PROMPT.format(
            concept=concept,
            world_bible=_world_bible_text(world_bible),
            hall_rules=HALL_RULES,
        ),
        max_new_tokens=850,
    )
    return _limit_list(payload, "events", 5)


def generate_newspaper(concept: str, world_bible: dict) -> dict:
    return call_llm(
        NEWSPAPER_PROMPT.format(
            concept=concept,
            world_bible=_world_bible_text(world_bible),
            hall_rules=HALL_RULES,
        ),
        max_new_tokens=850,
    )


def generate_visitor_book(concept: str, world_bible: dict) -> dict:
    return call_llm(
        VISITOR_BOOK_PROMPT.format(
            concept=concept,
            world_bible=_world_bible_text(world_bible),
            hall_rules=HALL_RULES,
        ),
        max_new_tokens=500,
    )
