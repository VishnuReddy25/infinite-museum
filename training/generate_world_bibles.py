"""
training/generate_world_bibles.py

Generates world_bible JSON training data using Groq's free tier (llama-3.3-70b).
Reads cleaned concepts from data/raw_prompts/public_world_concepts.jsonl
Writes training rows to data/synthetic/world_bible_train.jsonl

Free tier limits (as of 2026):
  - 30 RPM  (requests per minute)
  - 6,000 TPM (tokens per minute)
  - 1,000 RPD (requests per day)

We pace at ~1 request every 11 seconds to stay safely under TPM.

Usage:
    pip install groq
    Add GROQ_API_KEY=your_key to your .env file
    python training/generate_world_bibles.py
    python training/generate_world_bibles.py --dry-run        # preview only, no API calls
    python training/generate_world_bibles.py --limit 20       # process first 20 concepts
    python training/generate_world_bibles.py --resume         # skip already-generated concepts
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
INPUT_FILE  = ROOT / "data" / "raw_prompts" / "public_world_concepts.jsonl"
OUTPUT_FILE = ROOT / "data" / "synthetic" / "world_bible_train.jsonl"
SKIPPED_FILE = ROOT / "data" / "synthetic" / "skipped_concepts.jsonl"

# ── groq config ───────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1100

# ── prompts (mirrors generators/prompts.py) ───────────────────────────────────
SYSTEM_PROMPT = """You are the curator of the Infinite Museum of Impossible Worlds.
You write like a serious museum institution documenting a real lost civilization.
Your tone is elegant, precise, slightly eerie, and emotionally restrained.
You must preserve world consistency across every exhibit.
Return only raw valid JSON. No markdown. No code fences. No commentary."""

WORLD_BIBLE_SCHEMA = {
    "museum_name": "string",
    "tagline": "string",
    "core_premise": "string",
    "government": "string",
    "founded": "string",
    "population": "string",
    "currency": "string",
    "language": "string",
    "capital": "string",
    "summary": "2-3 sentence overview of the civilization",
    "tone_words": ["word1", "word2", "word3"],
    "laws_of_reality": ["law 1", "law 2", "law 3"],
    "taboo": "string",
    "historical_anchors": ["event 1", "event 2", "event 3"],
    "visual_motifs": ["motif 1", "motif 2", "motif 3"],
    "social_contradictions": ["contradiction 1", "contradiction 2"],
    "daily_life": "2-3 sentences about how ordinary people live within this impossible system"
}

REQUIRED_FIELDS = list(WORLD_BIBLE_SCHEMA.keys())

WORLD_BIBLE_PROMPT = """Design a complete world bible for an impossible civilization.

World concept:
{concept}

Return only this JSON shape — no markdown, no explanation, raw JSON only:
{schema}
"""

# ── filtering helpers ─────────────────────────────────────────────────────────

BAD_ENDINGS = (
    'she.', 'you.', 'he.', 'hum.', 'soon.', 'Soon.',
    'the.', 'a.', 'and.', 'him.', 'her.', 'they.', 'it.',
)

BAD_STARTS = (
    'you ', "you've", "you're", 'your ',
    'write a', 'from the perspective',
)

STORY_SIGNALS = [
    r'\byou\b.{0,15}(wake|woke|open your eyes|jolt)',
    r'\byou\b.{0,15}(are at|are an|are the)',
    r'from the perspective',
    r'make them as sympathetic',
]

GARBAGE_PATTERNS = [
    r'^a world where through \w+ and \w+\.$',   # "Through Iron And Flame"
    r'season \d+ of ',                           # "season 30 of Game of Thrones"
    r'the worst .{0,20} anyone has ever had',
    r'write a .{0,30} story',
    r'horror story from the perspective',
]


def is_bad_prompt(concept: str) -> tuple[bool, str]:
    """Return (should_skip, reason)."""
    cl = concept.lower().strip()

    if concept.endswith(BAD_ENDINGS):
        return True, "truncated"

    if cl.startswith(BAD_STARTS):
        return True, "story_pov"

    for pat in STORY_SIGNALS:
        if re.search(pat, cl):
            return True, "story_signal"

    for pat in GARBAGE_PATTERNS:
        if re.search(pat, cl):
            return True, "garbage"

    if len(concept.strip()) < 25:
        return True, "too_short"

    return False, ""


def clean_concept(concept: str) -> str:
    """
    Lightly rewrite concepts into 'A world where...' civilization form.
    Only applied to keepable prompts that need minor cleanup.
    """
    c = concept.strip()

    # already starts with "A world where" — just clean spacing
    if c.lower().startswith("a world where"):
        # normalize internal whitespace
        c = re.sub(r'\s+', ' ', c)
        return c

    # "The moon is actually..." → "A world where the moon is..."
    if c[0].isupper() and not c.lower().startswith("a world"):
        c = "A world where " + c[0].lower() + c[1:]

    c = re.sub(r'\s+', ' ', c).strip()
    return c


# ── json helpers ──────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass

    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        try:
            return json.loads(brace.group(0))
        except Exception:
            pass

    return {"error": "Could not parse JSON", "raw": text[:300]}


def validate_world_bible(data: dict) -> list[str]:
    """Return list of missing required fields."""
    return [f for f in REQUIRED_FIELDS if f not in data]


# ── groq call ─────────────────────────────────────────────────────────────────

def call_groq(client, concept: str) -> dict:
    prompt = WORLD_BIBLE_PROMPT.format(
        concept=concept,
        schema=json.dumps(WORLD_BIBLE_SCHEMA, indent=2)
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.8,
    )

    raw_text = response.choices[0].message.content.strip()
    return extract_json(raw_text)


# ── training row builder ──────────────────────────────────────────────────────

def build_training_row(concept: str, world_bible: dict) -> dict:
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are the curator of the Infinite Museum of Impossible Worlds. Return only valid JSON."
            },
            {
                "role": "user",
                "content": f"Generate a world bible for this impossible world:\n{concept}"
            },
            {
                "role": "assistant",
                "content": json.dumps(world_bible, ensure_ascii=True)
            }
        ]
    }


# ── I/O helpers ───────────────────────────────────────────────────────────────

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate world_bible training data via Groq.")
    parser.add_argument("--dry-run", action="store_true", help="Preview filtering without API calls.")
    parser.add_argument("--limit", type=int, default=None, help="Max concepts to process (default: all).")
    parser.add_argument("--resume", action="store_true", help="Skip concepts already in output file.")
    parser.add_argument("--delay", type=int, default=20, help="Seconds between API calls (default: 20).")
    args = parser.parse_args()

    DELAY_BETWEEN_CALLS = args.delay

    # ── load concepts ──
    raw_rows = read_jsonl(INPUT_FILE)
    print(f"Loaded {len(raw_rows)} raw concepts from {INPUT_FILE}")

    # ── load already-done concepts for resume ──
    done_concepts: set[str] = set()
    if args.resume:
        existing = read_jsonl(OUTPUT_FILE)
        for row in existing:
            try:
                user_msg = row["messages"][1]["content"]
                # extract concept from "Generate a world bible for this impossible world:\n<concept>"
                concept_part = user_msg.split(":\n", 1)[-1].strip()
                done_concepts.add(concept_part)
            except Exception:
                pass
        print(f"Resuming — {len(done_concepts)} concepts already done, will skip them.")

    # ── filter + clean ──
    to_process = []
    skipped = []

    for row in raw_rows:
        concept = row.get("concept", "").strip()
        bad, reason = is_bad_prompt(concept)
        if bad:
            skipped.append({"concept": concept, "reason": reason})
            continue
        cleaned = clean_concept(concept)
        if cleaned in done_concepts:
            continue
        to_process.append({"original": concept, "cleaned": cleaned})

    print(f"\nAfter filtering:")
    print(f"  Skipped (bad quality): {len(skipped)}")
    print(f"  To process:            {len(to_process)}")

    if args.limit:
        to_process = to_process[:args.limit]
        print(f"  Limited to:            {args.limit}")

    if args.dry_run:
        print("\n── DRY RUN — no API calls ──")
        print("\nSample cleaned concepts:")
        for item in to_process[:10]:
            print(f"  original: {item['original'][:70]}")
            print(f"  cleaned:  {item['cleaned'][:70]}")
            print()
        print(f"\nWould save {len(skipped)} skipped rows to {SKIPPED_FILE}")
        print(f"Would generate {len(to_process)} world bibles → {OUTPUT_FILE}")
        return

    # ── save skipped for reference ──
    SKIPPED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SKIPPED_FILE.open("w", encoding="utf-8") as f:
        for row in skipped:
            f.write(json.dumps(row) + "\n")
    print(f"Saved {len(skipped)} skipped concepts to {SKIPPED_FILE}")

    # ── setup groq ──
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found in environment. Add it to your .env file.")

    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Run: pip install groq")

    client = Groq(api_key=api_key)

    # ── generate ──
    total = len(to_process)
    success = 0
    failed = 0

    print(f"\nStarting generation — {total} concepts")
    print(f"Model: {GROQ_MODEL} | Delay: {DELAY_BETWEEN_CALLS}s between calls")
    print(f"Estimated time: ~{total * DELAY_BETWEEN_CALLS // 60} minutes\n")

    for i, item in enumerate(to_process, 1):
        concept = item["cleaned"]
        print(f"[{i}/{total}] {concept[:70]}...")

        try:
            world_bible = call_groq(client, concept)

            if "error" in world_bible:
                print(f"  ✗ Parse error: {world_bible['error'][:80]}")
                failed += 1
            else:
                missing = validate_world_bible(world_bible)
                if missing:
                    print(f"  ⚠ Missing fields: {missing} — saving anyway")

                row = build_training_row(concept, world_bible)
                append_jsonl(OUTPUT_FILE, row)
                success += 1
                print(f"  ✓ Saved — museum: {world_bible.get('museum_name', '?')}")

        except Exception as exc:
            err = str(exc)
            print(f"  ✗ API error: {err[:100]}")

            # handle rate limit — back off and retry once
            if "429" in err or "rate_limit" in err.lower():
                print("  Rate limited — waiting 60 seconds then retrying...")
                time.sleep(60)
                try:
                    world_bible = call_groq(client, concept)
                    row = build_training_row(concept, world_bible)
                    append_jsonl(OUTPUT_FILE, row)
                    success += 1
                    print(f"  ✓ Retry succeeded")
                except Exception as exc2:
                    print(f"  ✗ Retry also failed: {str(exc2)[:80]}")
                    failed += 1
            else:
                failed += 1

        # pace between calls
        if i < total:
            time.sleep(DELAY_BETWEEN_CALLS)

    print("\n── Done ──")
    print(f"  Success: {success}")
    print(f"  Failed:  {failed}")
    print(f"  Output:  {OUTPUT_FILE}")


if __name__ == "__main__":
    main()