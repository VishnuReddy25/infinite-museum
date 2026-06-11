import hashlib
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
    if role != "world":
        return None
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
        try:
            return client.text_generation(
                prompt,
                model=_resolve_model_id(role),
                adapter_id=adapter_id,
                max_new_tokens=max_new_tokens,
                temperature=0.8,
                do_sample=True,
                return_full_text=False,
            ).strip()
        except Exception as exc:
            detail = str(exc).lower()
            if "text-generation" not in detail and "supported task: conversational" not in detail:
                raise
            print("[LLM WARN] Falling back to chat completion because the hub provider rejected text-generation for this model.")

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


def generate_world_ambassador_reply(question: str, world_bible: dict, visitor_book: dict | None = None, conversation: list[dict] | None = None) -> str:
    visitor_book = visitor_book or {}
    conversation = conversation or []
    system_prompt = (
        "You are a citizen of the generated civilization inside the Infinite Museum of Impossible Worlds. "
        "Speak as someone who truly lives there. Be vivid, grounded, and in-world. "
        "Do not mention being an AI, prompt, JSON, or simulation. "
        "Keep replies under 140 words and answer directly. "
        "If asked something impossible to know, answer from rumor, belief, or daily experience inside the world."
    )
    user_prompt = (
        f"World bible:\n{_world_bible_text(world_bible)}\n\n"
        f"Visitor testimony:\n{json.dumps(visitor_book, ensure_ascii=True)}\n\n"
        f"Question from a museum visitor:\n{question.strip()}"
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation[-4:])
    messages.append({"role": "user", "content": user_prompt})

    if RUNTIME == "hub":
        return _generate_with_hub(messages, 220, "guide")
    if RUNTIME == "llamacpp":
        return _generate_with_llamacpp(messages, 220, "guide")
    return _generate_with_local(messages, 220, "guide")


def _compact_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_compact_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_compact_text(item) for item in value.values())
    return str(value)


def _keyword_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z]{4,}", text.lower()) if token not in {"that", "with", "this", "from", "have", "they", "their", "there", "about", "into", "which"}}


def build_world_complexity_report(world_bible: dict, artifacts_payload: dict | None = None, timeline_payload: dict | None = None) -> dict:
    world_bible = world_bible or {}
    artifacts = (artifacts_payload or {}).get("artifacts") or []
    timeline = (timeline_payload or {}).get("events") or []
    laws = world_bible.get("laws_of_reality") or []
    motifs = world_bible.get("visual_motifs") or []
    anchors = world_bible.get("historical_anchors") or []
    score = 28
    score += min(22, len(laws) * 6)
    score += min(18, len(motifs) * 4)
    score += min(18, len(anchors) * 4)
    score += min(14, len(artifacts) * 4)
    score += min(10, len(timeline) * 2)
    if world_bible.get("taboo"):
        score += 4
    if world_bible.get("daily_life"):
        score += 4
    score = max(0, min(100, score))

    if score >= 85:
        band = "Labyrinthine"
        note = "Dense institutions, layered symbols, and strong internal texture."
    elif score >= 70:
        band = "Ornate"
        note = "Rich enough to feel collectible, with several good lines of inquiry."
    elif score >= 55:
        band = "Layered"
        note = "Clear central rule with enough supporting detail to explore."
    else:
        band = "Emergent"
        note = "A promising world sketch that still leans on the central premise."

    return {"score": score, "band": band, "note": note}


def tag_artifacts(artifacts_payload: dict, world_bible: dict | None = None) -> dict:
    payload = dict(artifacts_payload or {})
    world_bible = world_bible or {}
    motifs = _keyword_set(_compact_text(world_bible.get("visual_motifs") or []))
    premise_terms = _keyword_set(_compact_text([world_bible.get("core_premise"), world_bible.get("government"), world_bible.get("taboo")]))
    tagged = []
    for artifact in payload.get("artifacts") or []:
        artifact = dict(artifact or {})
        text = _compact_text([artifact.get("name"), artifact.get("description"), artifact.get("significance"), artifact.get("material"), artifact.get("era")]).lower()
        tags: list[str] = []
        if any(word in text for word in ["crown", "seal", "decree", "scepter", "council", "ledger", "registry", "standard"]):
            tags.append("State Relic")
        if any(word in text for word in ["ritual", "temple", "sacred", "prayer", "omen", "oracle"]):
            tags.append("Ritual Object")
        if any(word in text for word in ["tool", "clock", "compass", "machine", "instrument", "device", "engine"]):
            tags.append("Civic Tool")
        if any(word in text for word in ["memory", "record", "archive", "book", "quill", "map"]):
            tags.append("Archive Piece")
        if any(word in text for word in ["mask", "dress", "garment", "uniform", "veil", "robe"]):
            tags.append("Social Costume")
        if premise_terms and len(_keyword_set(text) & premise_terms) >= 2:
            tags.append("Premise Anchor")
        if motifs and len(_keyword_set(text) & motifs) >= 1:
            tags.append("Motif Echo")
        if not tags:
            tags.append("Cultural Relic")
        artifact["curator_tags"] = tags[:3]
        tagged.append(artifact)
    payload["artifacts"] = tagged
    return payload


def detect_curator_notes(world_bible: dict, artifacts_payload: dict | None = None, timeline_payload: dict | None = None, newspaper_payload: dict | None = None, visitor_book: dict | None = None) -> dict:
    world_bible = world_bible or {}
    artifacts_payload = artifacts_payload or {}
    timeline_payload = timeline_payload or {}
    newspaper_payload = newspaper_payload or {}
    visitor_book = visitor_book or {}

    notes: list[dict] = []
    reference_terms = _keyword_set(
        _compact_text(
            [
                world_bible.get("core_premise"),
                world_bible.get("government"),
                world_bible.get("taboo"),
                world_bible.get("daily_life"),
                world_bible.get("historical_anchors"),
            ]
        )
    )
    artifact_text = _compact_text(artifacts_payload)
    timeline_text = _compact_text(timeline_payload)
    newspaper_text = _compact_text(newspaper_payload)
    visitor_text = _compact_text(visitor_book)

    artifact_items = artifacts_payload.get("artifacts") if isinstance(artifacts_payload, dict) else None
    timeline_events = timeline_payload.get("events") if isinstance(timeline_payload, dict) else None
    newspaper_ready = isinstance(newspaper_payload, dict) and bool(newspaper_payload.get("headline"))
    visitor_entry = visitor_book.get("entry") if isinstance(visitor_book, dict) else None

    if reference_terms and artifact_items and len(_keyword_set(artifact_text) & reference_terms) < 2:
        notes.append({"level": "warning", "title": "Artifact hall drift", "body": "The artifact descriptions feel a little detached from the core premise. A stronger material or symbolic link would make the collection feel more inevitable."})
    if reference_terms and newspaper_ready and len(_keyword_set(newspaper_text) & reference_terms) < 2:
        notes.append({"level": "warning", "title": "Public record drift", "body": "The newspaper does not strongly echo the main social rule yet. The press voice could lean more on the world’s core tension."})
    if world_bible.get("taboo") and visitor_entry:
        taboo_terms = _keyword_set(str(world_bible.get("taboo")))
        if taboo_terms and len(_keyword_set(visitor_text) & taboo_terms) == 0:
            notes.append({"level": "note", "title": "Taboo not felt personally", "body": "The private testimony does not yet brush against the stated taboo. A more intimate sign of fear or avoidance could deepen the final hall."})
    if timeline_events and len(timeline_events) < 3:
        notes.append({"level": "note", "title": "Thin chronology", "body": "The archive works, but a denser chain of turning points would make the civilization feel older and more inhabited."})
    if world_bible.get("visual_motifs") and (artifact_items or newspaper_ready or visitor_entry):
        motif_terms = _keyword_set(_compact_text(world_bible.get("visual_motifs")))
        combined_text = " ".join([artifact_text, newspaper_text, visitor_text]).lower()
        if motif_terms and len(_keyword_set(combined_text) & motif_terms) < 1:
            notes.append({"level": "note", "title": "Motif underused", "body": "The visual motif is recorded in the lobby but does not echo strongly enough across later halls."})

    severity_penalty = sum(10 if note["level"] == "warning" else 5 for note in notes)
    consistency_score = max(52, 100 - severity_penalty)
    headline = "Collection feels internally consistent." if not notes else "A few curatorial tensions were detected."
    return {"headline": headline, "consistency_score": consistency_score, "notes": notes[:4]}


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


def infer_visitor_world_role(world_bible: dict, curator_mode: str = "Anthropology") -> str:
    world_bible = world_bible or {}
    text = " ".join(
        _compact_text(value)
        for value in [
            world_bible.get("museum_name"),
            world_bible.get("core_premise"),
            world_bible.get("government"),
            world_bible.get("visual_motifs"),
            world_bible.get("taboo"),
        ]
    ).lower()

    keyword_roles = [
        (("memory", "scribe", "archive", "record", "ledger"), "memory clerk"),
        (("dream", "sleep", "night"), "dream registrar"),
        (("tide", "water", "canal", "sea"), "tide keeper"),
        (("gravity", "rank", "orbit", "moon"), "gravity surveyor"),
        (("food", "feast", "hunger", "grain"), "ration keeper"),
        (("mirror", "reflection", "glass"), "mirror guide"),
        (("clock", "time", "hour", "season"), "time keeper"),
        (("law", "seal", "decree", "council"), "seal bearer"),
        (("tax", "coin", "currency", "market"), "market registrar"),
    ]
    for keywords, role in keyword_roles:
        if any(keyword in text for keyword in keywords):
            return role

    mode_roles = {
        "Anthropology": ["street archivist", "market guide", "civic recorder", "district keeper"],
        "Mythic": ["ritual guide", "shrine keeper", "omen reader", "ceremonial singer"],
        "Imperial Archive": ["records clerk", "seal bearer", "registry officer", "state recorder"],
        "Melancholy": ["lamp keeper", "memorial guide", "night watcher", "letter carrier"],
    }
    candidates = mode_roles.get(curator_mode, mode_roles["Anthropology"])
    seed = hashlib.sha1(
        f"{world_bible.get('museum_name', '')}|{curator_mode}|{world_bible.get('government', '')}".encode("utf-8")
    ).hexdigest()
    return candidates[int(seed[:2], 16) % len(candidates)]


def build_visitor_portrait_prompt(
    world_bible: dict,
    visitor_name: str = "",
    curator_mode: str = "Anthropology",
    portrait_style: str = "Citizen Portrait",
    assigned_role: str | None = None,
) -> tuple[str, str]:
    world_bible = world_bible or {}
    role = assigned_role or infer_visitor_world_role(world_bible, curator_mode)
    museum_name = world_bible.get("museum_name", "Infinite Museum")
    premise = world_bible.get("core_premise") or world_bible.get("summary") or "one impossible rule shapes daily life"
    government = world_bible.get("government") or "an unknown civic order"
    motifs = _compact_text(world_bible.get("visual_motifs") or []) or "ornate civic symbols"
    laws = _compact_text(world_bible.get("laws_of_reality") or []) or "one impossible law"
    taboo = world_bible.get("taboo") or "an unnamed taboo"
    mood = {
        "Citizen Portrait": "cinematic museum portrait, clear face, half-body framing, real clothing, one person",
        "Official Archive ID": "formal archive portrait, direct pose, crisp lighting, identity-card framing, one person",
        "Ceremonial Portrait": "ornate ceremonial portrait, rich costume details, symbolic objects, dramatic light, one person",
    }.get(portrait_style, "cinematic museum portrait, one person")
    subject_name = visitor_name.strip() or "the visitor"
    prompt = (
        f"Museum portrait of {subject_name} as a {role} from {museum_name}. "
        f"World premise: {premise}. Government: {government}. "
        f"Visual motifs: {motifs}. Laws of reality: {laws}. "
        f"Taboo: {taboo}. Style: {portrait_style}. "
        f"Show one person only, centered composition, believable clothing from this world, "
        f"museum-quality portrait, detailed face, no text, no watermark, no extra people. "
        f"Overall mood: {mood}."
    ).strip()
    return prompt, role


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


def generate_featured_artifact_image(world_bible: dict, artifacts_payload: dict, artifact_index: int = 0) -> dict:
    artifacts = artifacts_payload.get("artifacts") if isinstance(artifacts_payload, dict) else None
    if not artifacts:
        print("[IMAGE ACTION] No artifacts available for image generation")
        return {}

    if artifact_index < 0 or artifact_index >= len(artifacts):
        artifact_index = 0

    artifact = artifacts[artifact_index]
    prompt = build_featured_artifact_prompt(world_bible, artifact)
    print(
        f"[IMAGE ACTION] runtime={IMAGE_RUNTIME} | artifact_index={artifact_index} "
        f"| artifact_name={artifact.get('name', 'Unknown artifact')}"
    )

    if IMAGE_RUNTIME == "disabled":
        print("[IMAGE ACTION] Image runtime is disabled")
        return {
            "prompt": prompt,
            "artifact_name": artifact.get("name", ""),
            "artifact": artifact,
            "status": "disabled",
        }
    if IMAGE_RUNTIME == "local":
        print("[IMAGE ACTION] Dispatching to local image generator")
        result = generate_image(prompt)
        result["prompt"] = prompt
        result["artifact_name"] = artifact.get("name", "")
        result["artifact"] = artifact
        print(f"[IMAGE ACTION] Local image result keys={sorted(result.keys())}")
        return result
    if IMAGE_RUNTIME == "backend":
        print("[IMAGE ACTION] Dispatching to backend image generator")
        result = _generate_image_via_backend(prompt)
        result["artifact_name"] = artifact.get("name", "")
        result["artifact"] = artifact
        print(f"[IMAGE ACTION] Backend image result keys={sorted(result.keys())}")
        return result

    print(f"[IMAGE ACTION] Unknown image runtime encountered: {IMAGE_RUNTIME}")
    return {
        "prompt": prompt,
        "artifact_name": artifact.get("name", ""),
        "artifact": artifact,
        "status": "unknown_runtime",
    }


def generate_visitor_world_portrait(
    world_bible: dict,
    visitor_name: str = "",
    curator_mode: str = "Anthropology",
    portrait_style: str = "Citizen Portrait",
) -> dict:
    prompt, role = build_visitor_portrait_prompt(
        world_bible=world_bible,
        visitor_name=visitor_name,
        curator_mode=curator_mode,
        portrait_style=portrait_style,
    )
    print(
        f"[PORTRAIT ACTION] runtime={IMAGE_RUNTIME} | style={portrait_style} "
        f"| role={role} | visitor_name={visitor_name or 'Unknown visitor'}"
    )

    if IMAGE_RUNTIME == "disabled":
        return {
            "prompt": prompt,
            "style": portrait_style,
            "assigned_role": role,
            "status": "disabled",
        }
    if IMAGE_RUNTIME == "local":
        result = generate_image(prompt)
        result["prompt"] = prompt
        result["style"] = portrait_style
        result["assigned_role"] = role
        return result
    if IMAGE_RUNTIME == "backend":
        result = _generate_image_via_backend(prompt)
        result["prompt"] = prompt
        result["style"] = portrait_style
        result["assigned_role"] = role
        return result

    return {
        "prompt": prompt,
        "style": portrait_style,
        "assigned_role": role,
        "status": "unknown_runtime",
    }
