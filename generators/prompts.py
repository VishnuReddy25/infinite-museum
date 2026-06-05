import json


SYSTEM_PROMPT = """You are the curator of the Infinite Museum of Impossible Worlds.
You write like a serious museum institution documenting a real lost civilization.
Your tone is elegant, precise, slightly eerie, and emotionally restrained.
You must preserve world consistency across every exhibit.
Return only raw valid JSON. No markdown. No code fences. No commentary."""


WORLD_BIBLE_SCHEMA = {
    "museum_name": "Museum of Somnia",
    "tagline": "Where sleep is ledger and prophecy is taxed.",
    "core_premise": "Dreams are currency.",
    "government": "The Nocturnal Treasury",
    "founded": "Year 0 of the Velvet Ledger",
    "population": "18 million",
    "currency": "Distilled dreams sealed in blue glass",
    "language": "Somnari",
    "capital": "Velis",
    "summary": "A concise 2-3 sentence overview of the civilization.",
    "tone_words": ["melancholic", "ritualized", "ornate"],
    "laws_of_reality": [
        "Dreams can be harvested and traded.",
        "Nightmares are considered contaminated wealth.",
        "Sleep debt has legal and economic consequences."
    ],
    "taboo": "Selling the final dream of the dead.",
    "historical_anchors": [
        "Founding of the First Sleep Ledger",
        "The Hollow Night market collapse",
        "The Reform of Public Dreamhouses"
    ],
    "visual_motifs": ["blue glass", "wax seals", "velvet dusk"],
    "social_contradictions": [
        "The poor sleep longer but own less.",
        "The wealthy can purchase peace but rarely rest."
    ],
    "daily_life": "2-3 sentences about how ordinary people live within this impossible system."
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
