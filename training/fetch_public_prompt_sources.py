import argparse
import json
import re
from pathlib import Path

from datasets import load_dataset


DATASET_SPECS = [
    {
        "id": "euclaise/writingprompts",
        "split": "train",
        "fields": ["prompt"],
        "prefix": "Writing prompt",
    },
    {
        "id": "archit11/worldbuilding",
        "split": "train",
        "fields": ["question", "answer"],
        "prefix": "Worldbuilding",
    },
    {
        "id": "Dxniz/Novelist-CoT",
        "split": "train",
        "fields": ["instruction", "input"],
        "prefix": "Narrative",
    },
    {
        "id": "HeAAAAA/story_generation_sft",
        "split": "train",
        "fields": ["prompt", "instruction"],
        "prefix": "Story",
    },
]

MAX_CONCEPT_LEN = 160


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_nonempty(row: dict, fields: list[str]) -> str:
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return normalize_space(value)
    return ""


def premise_from_text(text: str) -> str:
    text = normalize_space(text)
    text = re.sub(r"^\[[^\]]+\]\s*", "", text)
    text = text.strip("\"' ")
    text = re.sub(r"^Write (?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^Imagine\s+", "", text, flags=re.IGNORECASE)

    if len(text) > MAX_CONCEPT_LEN:
        cut = text[:MAX_CONCEPT_LEN].rsplit(" ", 1)[0].strip()
        text = cut if cut else text[:MAX_CONCEPT_LEN].strip()

    if not text.endswith((".", "!", "?")):
        text += "."

    lowered = text.lower()
    if not any(token in lowered for token in ["world", "civilization", "city", "kingdom", "planet", "moon", "society", "nation"]):
        text = f"A world where {text[0].lower() + text[1:]}" if text else text

    return text


def is_viable_concept(text: str) -> bool:
    lowered = text.lower()
    if len(text) < 24:
        return False
    if len(text) > MAX_CONCEPT_LEN + 20:
        return False
    banned = ["write a story", "respond to", "chapter", "dialogue", "essay"]
    if any(term in lowered for term in banned):
        return False
    return True


def fetch_rows(spec: dict, per_source: int) -> list[dict]:
    dataset = load_dataset(spec["id"], split=spec["split"])
    rows = []
    seen = set()

    for row in dataset:
        source_text = first_nonempty(row, spec["fields"])
        if not source_text:
            continue
        concept = premise_from_text(source_text)
        key = concept.lower()
        if key in seen or not is_viable_concept(concept):
            continue
        seen.add(key)
        rows.append(
            {
                "concept": concept,
                "source_dataset": spec["id"],
                "source_prefix": spec["prefix"],
                "raw_text": source_text,
            }
        )
        if len(rows) >= per_source:
            break

    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public prompt seeds from Hugging Face datasets.")
    parser.add_argument("--output", required=True, help="Output JSONL path.")
    parser.add_argument("--per-source", type=int, default=120, help="Number of candidate prompts per dataset source.")
    args = parser.parse_args()

    rows = []
    for spec in DATASET_SPECS:
        try:
            rows.extend(fetch_rows(spec, args.per_source))
            print(f"Loaded prompt seeds from {spec['id']}")
        except Exception as exc:
            print(f"Skipping {spec['id']} due to error: {exc}")

    deduped = []
    seen = set()
    for row in rows:
        key = row["concept"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    write_jsonl(Path(args.output), deduped)
    print(f"Wrote {len(deduped)} public prompt seeds to {args.output}")


if __name__ == "__main__":
    main()
