import json
import os
import re
from functools import lru_cache
from urllib import error, request

from dotenv import load_dotenv
from generators.image_engine import generate_image

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

# Enable fast multi-threaded downloads on Hugging Face Spaces
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("HF_HOME", "/tmp/huggingface")
os.environ.setdefault("HF_HUB_CACHE", "/tmp/huggingface/hub")

MODEL_ID = os.environ.get("MUSEUM_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
WORLD_MODEL_ID = os.environ.get("MUSEUM_WORLD_MODEL_ID", MODEL_ID)
HALL_MODEL_ID = os.environ.get("MUSEUM_HALL_MODEL_ID", MODEL_ID)
GUIDE_MODEL_ID = os.environ.get("MUSEUM_GUIDE_MODEL_ID", HALL_MODEL_ID)
ADAPTER_ID = os.environ.get("MUSEUM_ADAPTER_ID", "VishnuReddy25/infinite-museum-lora")
RUNTIME = os.environ.get("MUSEUM_RUNTIME", "local").lower()
HF_TOKEN = os.environ.get("HF_TOKEN")
LLAMACPP_BASE_URL = os.environ.get("LLAMACPP_BASE_URL", "http://127.0.0.1:8080")
LLAMACPP_MODEL = os.environ.get("LLAMACPP_MODEL", "museum-gguf")
LLAMACPP_WORLD_MODEL = os.environ.get("LLAMACPP_WORLD_MODEL", LLAMACPP_MODEL)
LLAMACPP_HALL_MODEL = os.environ.get("LLAMACPP_HALL_MODEL", LLAMACPP_MODEL)
LLAMACPP_GUIDE_MODEL = os.environ.get("LLAMACPP_GUIDE_MODEL", LLAMACPP_HALL_MODEL)
LLAMACPP_API_KEY = os.environ.get("LLAMACPP_API_KEY", "")
IMAGE_RUNTIME = os.environ.get("MUSEUM_IMAGE_RUNTIME", "disabled").lower()
IMAGE_MODEL = os.environ.get("MUSEUM_IMAGE_MODEL", "black-forest-labs/FLUX.2-klein-4B")
IMAGE_API_KEY = os.environ.get("MUSEUM_IMAGE_API_KEY", "")


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


def _resolve_model_id(role: str) -> str:
    return {
        "world": WORLD_MODEL_ID,
        "hall": HALL_MODEL_ID,
        "guide": GUIDE_MODEL_ID,
    }.get(role, MODEL_ID)


def _resolve_llamacpp_model(role: str) -> str:
    return {
        "world": LLAMACPP_WORLD_MODEL,
        "hall": LLAMACPP_HALL_MODEL,
        "guide": LLAMACPP_GUIDE_MODEL,
    }.get(role, LLAMACPP_MODEL)


def _adapter_for_role(role: str) -> str | None:
    return ADAPTER_ID or None


def _messages_to_prompt(messages: list[dict]) -> str:
    parts: list[str] = []
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if role == "system":
            parts.append(f"System:\n{content}")
        elif role == "user":
            parts.append(f"User:\n{content}")
        else:
            parts.append(content)
    parts.append("Assistant:\n")
    return "\n\n".join(parts)


@lru_cache(maxsize=None)
def _load_local_pipeline(role: str = "world"):
    from transformers import pipeline
    from peft import PeftModel

    model_id = _resolve_model_id(role)
    adapter_id = _adapter_for_role(role)
    print(f"Loading {role} model: {model_id}")
    if adapter_id:
        print(f"Loading adapter for {role}: {adapter_id}")

    pipe = pipeline(
        "text-generation",
        model=model_id,
        device_map="auto",
        torch_dtype="auto",
        token=HF_TOKEN,
    )

    if adapter_id:
        pipe.model = PeftModel.from_pretrained(
            pipe.model,
            adapter_id,
            token=HF_TOKEN,
        )
        pipe.model = pipe.model.merge_and_unload()
        print(f"Adapter merged successfully for {role}.")
    return pipe


@lru_cache(maxsize=1)
def _load_hf_client():
    from huggingface_hub import InferenceClient

    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is required when MUSEUM_RUNTIME=hub.")
    return InferenceClient(api_key=HF_TOKEN)


@GPU
def _generate_with_local(messages: list[dict], max_new_tokens: int, role: str = "world") -> str:
    pipe = _load_local_pipeline(role)
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


def _generate_with_hub(messages: list[dict], max_new_tokens: int, role: str = "world") -> str:
    client = _load_hf_client()
    adapter_id = _adapter_for_role(role)
    if adapter_id:
        prompt = _messages_to_prompt(messages)
        return client.text_generation(
            prompt,
            model=_resolve_model_id(role),
            adapter_id=adapter_id,
            max_new_tokens=max_new_tokens,
            temperature=0.8,
            do_sample=True,
            return_full_text=False,
        ).strip()

    completion = client.chat_completion(
        model=_resolve_model_id(role),
        messages=messages,
        max_tokens=max_new_tokens,
        temperature=0.8,
    )
    return completion.choices[0].message.content.strip()


def _generate_with_llamacpp(messages: list[dict], max_new_tokens: int, role: str = "world") -> str:
    payload = json.dumps(
        {
            "model": _resolve_llamacpp_model(role),
            "messages": messages,
            "max_tokens": max_new_tokens,
            "temperature": 0.8,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if LLAMACPP_API_KEY:
        headers["Authorization"] = f"Bearer {LLAMACPP_API_KEY}"

    endpoint = f"{LLAMACPP_BASE_URL.rstrip('/')}/v1/chat/completions"
    req = request.Request(endpoint, data=payload, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"llama.cpp HTTP {exc.code}: {detail[:300]}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Could not reach llama.cpp server at {endpoint}. "
            "Make sure your local server is running."
        ) from exc

    try:
        return body["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Unexpected llama.cpp response: {body}") from exc


def call_llm(prompt: str, max_new_tokens: int = 900, role: str = "world") -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    text = ""
    try:
        if RUNTIME == "hub":
            text = _generate_with_hub(messages, max_new_tokens, role)
        elif RUNTIME == "llamacpp":
            text = _generate_with_llamacpp(messages, max_new_tokens, role)
        else:
            text = _generate_with_local(messages, max_new_tokens, role)

        print(f"[LLM RAW:{role}] {text[:300]}")
        parsed = extract_json(text)
        if "error" in parsed:
            raise ValueError(parsed["error"])
        return parsed
    except Exception as exc:
        print(f"[LLM ERROR] {exc}")
        return {"error": str(exc), "raw": text[:300]}


def _world_bible_text(world_bible: dict) -> str:
    return json.dumps(world_bible, indent=2, ensure_ascii=True)


def _limit_list(payload, key: str, size: int) -> dict:
    if isinstance(payload, list):
        return {key: payload[:size]}

    if not isinstance(payload, dict):
        return {key: []}

    items = payload.get(key)
    if isinstance(items, list):
        payload[key] = items[:size]
    elif items is None:
        payload[key] = []
    return payload


def generate_world_bible(concept: str) -> dict:
    return call_llm(
        WORLD_BIBLE_PROMPT.format(
            concept=concept,
            schema=WORLD_BIBLE_SCHEMA_TEXT,
        ),
        max_new_tokens=1100,
        role="world",
    )


def generate_artifacts(concept: str, world_bible: dict) -> dict:
    payload = call_llm(
        ARTIFACTS_PROMPT.format(
            concept=concept,
            world_bible=_world_bible_text(world_bible),
            hall_rules=HALL_RULES,
        ),
        max_new_tokens=900,
        role="hall",
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
        role="hall",
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
        role="hall",
    )


def generate_visitor_book(concept: str, world_bible: dict) -> dict:
    return call_llm(
        VISITOR_BOOK_PROMPT.format(
            concept=concept,
            world_bible=_world_bible_text(world_bible),
            hall_rules=HALL_RULES,
        ),
        max_new_tokens=500,
        role="guide",
    )


def build_featured_artifact_prompt(world_bible: dict, artifact: dict) -> str:
    motifs = ", ".join(world_bible.get("visual_motifs", [])[:3])
    laws = ", ".join(world_bible.get("laws_of_reality", [])[:2])
    return (
        f"Museum artifact photograph, centered display object, dramatic exhibit lighting. "
        f"Show {artifact.get('name', 'an impossible artifact')} from the civilization of {world_bible.get('capital', 'an unknown capital')}. "
        f"Material: {artifact.get('material', 'unknown material')}. "
        f"Era: {artifact.get('era', 'unknown era')}. "
        f"Use details from this description: {artifact.get('description', '')} "
        f"Visual motifs: {motifs}. "
        f"World rules: {laws}. "
        f"Dark museum background, realistic texture, no text, no people, one hero object."
    ).strip()


def _generate_image_via_backend(prompt: str) -> dict:
    IMAGE_BASE_URL = os.environ.get("MUSEUM_IMAGE_BASE_URL", "http://127.0.0.1:7861")
    payload = json.dumps(
        {
            "model": IMAGE_MODEL,
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 4,
            "guidance_scale": 3.5,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if IMAGE_API_KEY:
        headers["Authorization"] = f"Bearer {IMAGE_API_KEY}"

    endpoint = f"{IMAGE_BASE_URL.rstrip('/')}/generate"
    req = request.Request(endpoint, data=payload, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=240) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return {"error": f"image backend HTTP {exc.code}: {detail[:300]}"}
    except error.URLError as exc:
        return {"error": f"Could not reach image backend at {endpoint}: {exc}"}

    image_url = body.get("image_url") or body.get("url") or body.get("image")
    if not image_url:
        return {"error": f"Unexpected image backend response: {body}"}
    return {"image_url": image_url, "prompt": prompt}


def generate_featured_artifact_image(world_bible: dict, artifacts_payload: dict) -> dict:
    artifacts = artifacts_payload.get("artifacts") if isinstance(artifacts_payload, dict) else None
    if not artifacts:
        return {}

    artifact = artifacts[0]
    prompt = build_featured_artifact_prompt(world_bible, artifact)

    if IMAGE_RUNTIME == "disabled":
        return {"prompt": prompt, "artifact_name": artifact.get("name", ""), "status": "disabled"}
    if IMAGE_RUNTIME == "local":
        result = generate_image(prompt)
        result["prompt"] = prompt
        result["artifact_name"] = artifact.get("name", "")
        return result
    if IMAGE_RUNTIME == "backend":
        result = _generate_image_via_backend(prompt)
        result["artifact_name"] = artifact.get("name", "")
        return result

    return {"prompt": prompt, "artifact_name": artifact.get("name", ""), "status": "unknown_runtime"}
