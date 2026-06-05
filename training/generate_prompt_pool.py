import argparse
import json
import random
from pathlib import Path


SEED_CONCEPTS = [
    "A world where dreams are currency.",
    "A civilization ruled by migratory birds.",
    "A city that pays rent in memories.",
    "A planet where gravity changes with music.",
    "A kingdom where shadows vote in elections.",
    "An empire that measures status by how much silence a person owns.",
    "A coastal nation where the dead return as weather.",
    "A moon where children inherit the seasons.",
    "A republic built inside the skeleton of a sleeping giant.",
    "A desert world where laws are written in glass before dawn.",
    "A city whose streets rearrange themselves to avoid grief.",
    "A civilization where names expire and must be earned again.",
    "A world where books grow like fruit.",
    "A nation where mirrors are state property.",
    "A society where time is taxed by the hour.",
    "A mountain culture that trades in borrowed luck.",
    "A world where the sea remembers every lie spoken above it.",
    "A city ruled by librarians who interpret earthquakes as law.",
    "A civilization where homes migrate every winter.",
    "A world where music can alter inheritance."
]

PREFIXES = [
    "A world where",
    "A civilization where",
    "A city where",
    "A nation where",
    "A kingdom where",
    "A moon where",
    "A planet where"
]

SUBJECTS = [
    "weather",
    "memory",
    "gravity",
    "silence",
    "shadows",
    "sleep",
    "language",
    "ritual",
    "music",
    "migration",
    "debt",
    "time",
    "law",
    "hunger",
    "salt",
    "fire",
    "mirrors",
    "mourning"
]

VERBS = [
    "is inherited",
    "can be taxed",
    "is used as currency",
    "must be voted on",
    "can be stored in glass",
    "is regulated by priests",
    "changes with the tide",
    "is auctioned at dawn",
    "is treated as a public utility",
    "must be shared by law"
]


def synthesize_concept(rng: random.Random) -> str:
    return f"{rng.choice(PREFIXES)} {rng.choice(SUBJECTS)} {rng.choice(VERBS)}."


def write_jsonl(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a prompt pool for museum fine-tuning.")
    parser.add_argument("--output", required=True, help="Path to the output JSONL file.")
    parser.add_argument("--count", type=int, default=200, help="Number of prompts to create.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    concepts = list(SEED_CONCEPTS)
    while len(concepts) < args.count:
        concepts.append(synthesize_concept(rng))

    rng.shuffle(concepts)
    rows = [{"concept": concept.strip()} for concept in concepts[: args.count]]
    write_jsonl(rows, Path(args.output))
    print(f"Wrote {len(rows)} prompts to {args.output}")


if __name__ == "__main__":
    main()
