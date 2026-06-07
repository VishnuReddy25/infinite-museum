import json


SYSTEM_PROMPT = """You are the curator of the Infinite Museum of Impossible Worlds.
You document lost civilizations clearly and vividly, like a museum guide explaining to a curious visitor.
Your tone is warm but eerie, clear but atmospheric. Use simple words with strong images.
Avoid academic or overly formal language. Write so anyone can read it and feel something.
You must preserve world consistency across every exhibit.
Return only raw valid JSON. No markdown. No code fences. No commentary."""


WORLD_BIBLE_SCHEMA = {
    "museum_name": "A unique name for this world's museum — do NOT use Museum of Somnia",
    "tagline": "A short, striking line that captures this world's essence",
    "core_premise": "One sentence: the impossible rule that defines this world",
    "government": "Name and short description of the ruling system",
    "founded": "When and how this civilization began",
    "population": "Approximate population",
    "currency": "What people use to trade and survive",
    "language": "What the people call their language",
    "capital": "Name of the main city",
    "summary": "2-3 clear sentences describing the civilization and how people live",
    "tone_words": ["word1", "word2", "word3"],
    "laws_of_reality": [
        "The first impossible rule of this world",
        "The second impossible rule",
        "The third impossible rule"
    ],
    "taboo": "The one thing no one is allowed to do, ever",
    "historical_anchors": [
        "A founding event",
        "A crisis or collapse",
        "A turning point or reform"
    ],
    "visual_motifs": ["a recurring image", "a material or color", "a symbol"],
    "social_contradictions": [
        "Something unfair or ironic about how this society works",
        "Another contradiction"
    ],
    "daily_life": "2-3 sentences about what an ordinary person's day looks like in this world"
}


HALL_RULES = """Hard rules:
- Reuse names, institutions, laws, and motifs from the world bible exactly when relevant.
- Do not invent physical laws that contradict the world bible.
- Prefer existing historical anchors over introducing unrelated lore.
- Keep the prose concrete, elegant, and museum-like.
- Return raw valid JSON only."""


WORLD_BIBLE_PROMPT = """Design a complete world bible for an impossible civilization.

World concept:
{concept}

Return only this JSON shape:
{schema}
"""


WORLD_BIBLE_SCHEMA_TEXT = json.dumps(WORLD_BIBLE_SCHEMA, indent=2)


ARTIFACTS_PROMPT = """World concept:
{concept}

World bible:
{world_bible}

{hall_rules}

Generate exactly 3 museum artifacts from this civilization.
Return only this JSON:
{{
  "artifacts": [
    {{
      "name": "artifact name",
      "era": "historical period",
      "material": "what it is made from",
      "description": "2-3 sentences in exhibit-card prose",
      "significance": "one sentence on cultural importance"
    }}
  ]
}}
"""


TIMELINE_PROMPT = """World concept:
{concept}

World bible:
{world_bible}

{hall_rules}

Generate exactly 5 historical events for this civilization.
Return only this JSON:
{{
  "events": [
    {{
      "year": "year or era",
      "title": "event name",
      "description": "1-2 sentences of museum prose",
      "type": "one of: founding, conflict, discovery, collapse, golden_age, reform"
    }}
  ]
}}
"""


NEWSPAPER_PROMPT = """World concept:
{concept}

World bible:
{world_bible}

{hall_rules}

Generate a front page from this civilization.
Return only this JSON:
{{
  "newspaper_name": "publication name",
  "date": "date in their own calendar",
  "headline": "major headline",
  "headline_body": "3-4 sentences for the lead story",
  "secondary_headline": "secondary story headline",
  "secondary_body": "2 sentences",
  "advertisement": "1-2 line period-appropriate advertisement or classified",
  "weather": "weather report using this world's own terms"
}}
"""


VISITOR_BOOK_PROMPT = """World concept:
{concept}

World bible:
{world_bible}

{hall_rules}

Write a visitor-book entry from an ordinary person who lived in this world.
It should feel intimate, plausible, and quietly haunting.
Return only this JSON:
{{
  "entry": "2-4 sentences in first person",
  "signed": "name, role, and date"
}}
"""
