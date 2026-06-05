import argparse
import json
from pathlib import Path


TASK_FILES = {
    "world_bible": "world_bible_train.jsonl",
    "artifacts": "artifacts_train.jsonl",
    "timeline": "timeline_train.jsonl",
    "newspaper": "newspaper_train.jsonl",
    "visitor_book": "visitor_book_train.jsonl",
}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def stub_world_bible(concept: str) -> dict:
    return {
        "museum_name": "Museum of Placeholder Realms",
        "tagline": "A temporary exhibit awaiting curation.",
        "core_premise": concept,
        "government": "To be curated",
        "founded": "Unknown era",
        "population": "Unknown",
        "currency": "Unknown",
        "language": "Unknown",
        "capital": "Unknown",
        "summary": "Replace this stub with a teacher-generated world bible.",
        "tone_words": ["museum", "precise", "eerie"],
        "laws_of_reality": ["Replace with teacher output."],
        "taboo": "Replace with teacher output.",
        "historical_anchors": ["Replace with teacher output."],
        "visual_motifs": ["Replace with teacher output."],
        "social_contradictions": ["Replace with teacher output."],
        "daily_life": "Replace with teacher output."
    }


def stub_hall(task: str) -> dict:
    if task == "artifacts":
        return {"artifacts": [{"name": "Replace me", "era": "Unknown", "material": "Unknown", "description": "Teacher output goes here.", "significance": "Teacher output goes here."}]}
    if task == "timeline":
        return {"events": [{"year": "Unknown", "title": "Replace me", "description": "Teacher output goes here.", "type": "founding"}]}
    if task == "newspaper":
        return {
            "newspaper_name": "Replace me",
            "date": "Unknown",
            "headline": "Teacher output goes here.",
            "headline_body": "Teacher output goes here.",
            "secondary_headline": "Teacher output goes here.",
            "secondary_body": "Teacher output goes here.",
            "advertisement": "Teacher output goes here.",
            "weather": "Teacher output goes here."
        }
    return {"entry": "Teacher output goes here.", "signed": "Replace me"}


def build_messages(task: str, concept: str, world_bible: dict | None = None, assistant_payload: dict | None = None) -> dict:
    system = "You are the curator of the Infinite Museum of Impossible Worlds. Return only valid JSON."

    if task == "world_bible":
        user = f"Generate a world bible for this impossible world:\n{concept}"
        assistant = assistant_payload or stub_world_bible(concept)
    else:
        user = (
            f"World concept:\n{concept}\n\n"
            f"World bible:\n{json.dumps(world_bible or stub_world_bible(concept), ensure_ascii=True)}\n\n"
            f"Generate the {task} exhibit in valid JSON."
        )
        assistant = assistant_payload or stub_hall(task)

    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=True)}
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build museum-format JSONL training data.")
    parser.add_argument("--prompts", required=True, help="JSONL file with a concept field.")
    parser.add_argument("--output-dir", required=True, help="Directory for task JSONL files.")
    parser.add_argument("--tasks", nargs="+", default=list(TASK_FILES.keys()), choices=list(TASK_FILES.keys()))
    args = parser.parse_args()

    prompts = read_jsonl(Path(args.prompts))
    output_dir = Path(args.output_dir)

    world_bible_rows = []
    for prompt in prompts:
        concept = prompt["concept"].strip()
        world_bible_rows.append(build_messages("world_bible", concept))
    write_jsonl(output_dir / TASK_FILES["world_bible"], world_bible_rows)

    stubs_by_concept = {prompt["concept"].strip(): stub_world_bible(prompt["concept"].strip()) for prompt in prompts}

    for task in args.tasks:
        if task == "world_bible":
            continue
        rows = []
        for prompt in prompts:
            concept = prompt["concept"].strip()
            rows.append(build_messages(task, concept, world_bible=stubs_by_concept[concept]))
        write_jsonl(output_dir / TASK_FILES[task], rows)

    print(f"Wrote museum-format task files to {output_dir}")


if __name__ == "__main__":
    main()
