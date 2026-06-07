import html

import gradio as gr

from generators.engine import (
    generate_artifacts,
    generate_newspaper,
    generate_timeline,
    generate_visitor_book,
    generate_world_bible,
)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=Cinzel:wght@400;500;600&display=swap');

:root {
    --bg: #16110f;
    --bg-deep: #0d0a08;
    --bg-wash: #241912;
    --panel: rgba(16, 12, 10, 0.92);
    --panel-light: rgba(240, 232, 212, 0.96);
    --line: rgba(200, 169, 110, 0.22);
    --gold: #c8a96e;
    --gold-soft: #8a7248;
    --paper: #eadfc9;
    --muted: #94846b;
    --ink: #241a12;
}

body, .gradio-container {
    background:
        radial-gradient(circle at 12% 18%, rgba(200, 169, 110, 0.11), transparent 22%),
        radial-gradient(circle at 80% 6%, rgba(107, 63, 31, 0.2), transparent 18%),
        radial-gradient(circle at top, rgba(80, 57, 27, 0.18), transparent 34%),
        linear-gradient(180deg, #090706 0%, var(--bg) 30%, #120d0a 100%) !important;
    color: var(--paper) !important;
    font-family: 'Cormorant Garamond', Georgia, serif !important;
}

.gradio-container {
    max-width: 1180px !important;
}

.museum-shell {
    border: 1px solid var(--line);
    margin: 20px;
    background: rgba(10, 8, 7, 0.72);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
    overflow: hidden;
}

.museum-header {
    padding: 18px 22px 0;
    border-bottom: 1px solid var(--line);
    background:
        radial-gradient(circle at 50% -20%, rgba(200, 169, 110, 0.24), transparent 35%),
        linear-gradient(180deg, rgba(200, 169, 110, 0.08), transparent 40%),
        linear-gradient(180deg, rgba(12, 9, 7, 0.98), rgba(19, 14, 11, 0.92));
}

.museum-marquee {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    border-bottom: 1px solid rgba(200, 169, 110, 0.14);
    padding: 0 0 12px;
    margin-bottom: 28px;
    color: var(--muted);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.hero-grid {
    display: grid;
    grid-template-columns: 1.6fr 1fr;
    gap: 22px;
    align-items: stretch;
    padding-bottom: 26px;
}

.hero-main {
    padding: 22px 10px 16px 8px;
}

.hero-side {
    border: 1px solid var(--line);
    border-radius: 16px;
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.08), transparent 18%),
        rgba(17, 12, 10, 0.8);
    padding: 18px 18px 16px;
}

.museum-kicker,
.section-heading,
.progress-label,
.lobby-label,
.artifact-kicker,
.paper-kicker,
.visitor-kicker,
.mode-chip {
    font-family: 'Cinzel', serif;
    letter-spacing: 0.36em;
    text-transform: uppercase;
}

.museum-kicker {
    font-size: 10px;
    color: var(--gold-soft);
    margin-bottom: 14px;
}

.museum-title {
    font-family: 'Cinzel', serif;
    font-size: 42px;
    line-height: 1.2;
    color: var(--gold);
    margin-bottom: 10px;
}

.museum-tagline {
    font-size: 18px;
    color: var(--paper);
    opacity: 0.88;
    font-style: italic;
    max-width: 720px;
    margin: 0 auto;
}

.museum-lead {
    margin-top: 18px;
    color: var(--muted);
    font-size: 18px;
    line-height: 1.8;
    max-width: 680px;
}

.hero-plaques {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-top: 22px;
}

.hero-plaque {
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(10, 8, 7, 0.55);
}

.hero-plaque-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.hero-plaque-value {
    color: var(--paper);
    font-size: 16px;
    line-height: 1.4;
}

.hero-side-heading {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 15px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.hero-side-copy {
    color: var(--paper);
    line-height: 1.75;
    font-size: 17px;
}

.hero-side-note {
    margin-top: 14px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.65;
}

.input-zone {
    padding: 24px 24px 2px;
}

.input-zone textarea,
.input-zone input {
    background: rgba(10, 8, 7, 0.92) !important;
    color: var(--paper) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    font-size: 17px !important;
    box-shadow: none !important;
}

.input-zone label {
    color: var(--gold-soft) !important;
    font-family: 'Cinzel', serif !important;
    font-size: 11px !important;
    letter-spacing: 0.2em !important;
}

.control-shell {
    padding: 0 24px 10px;
}

.control-card {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 18px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.08), transparent 24%),
        rgba(12, 9, 7, 0.78);
}

.control-panel-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.control-panel-copy {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.65;
    margin-bottom: 18px;
}

.mode-radio {
    gap: 10px;
}

.mode-radio label {
    min-width: 0 !important;
    flex: 1 1 auto !important;
}

.mode-radio label span {
    width: 100%;
    display: block;
    padding: 12px 14px;
    border-radius: 999px;
    border: 1px solid rgba(200, 169, 110, 0.2);
    background: rgba(18, 13, 11, 0.72);
    color: var(--paper) !important;
    font-family: 'Cinzel', serif !important;
    font-size: 11px !important;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    text-align: center;
}

.mode-radio input:checked + span {
    background: linear-gradient(180deg, rgba(200, 169, 110, 0.18), rgba(38, 27, 18, 0.86));
    border-color: rgba(200, 169, 110, 0.5);
    color: var(--gold) !important;
}

.enter-btn {
    height: 100% !important;
    min-height: 84px;
    background: linear-gradient(180deg, #2c2117, #17100c) !important;
    color: var(--gold) !important;
    border: 1px solid rgba(200, 169, 110, 0.45) !important;
    border-radius: 10px !important;
    font-family: 'Cinzel', serif !important;
    font-size: 12px !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
}

.enter-btn:hover {
    border-color: rgba(200, 169, 110, 0.8) !important;
    background: linear-gradient(180deg, #35281a, #19120d) !important;
}

.status-wrap {
    padding: 2px 24px 18px;
}

.status-panel {
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 18px 20px;
    background:
        linear-gradient(90deg, rgba(200, 169, 110, 0.06), transparent 22%),
        rgba(13, 10, 8, 0.72);
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 18px;
}

.status-line {
    font-family: 'Cinzel', serif;
    color: var(--gold);
    font-size: 14px;
    letter-spacing: 0.12em;
}

.status-subline {
    margin-top: 8px;
    color: var(--muted);
    font-size: 16px;
}

.status-side {
    border-left: 1px solid rgba(200, 169, 110, 0.12);
    padding-left: 18px;
}

.mode-chip {
    font-size: 9px;
    color: var(--gold-soft);
    margin-bottom: 10px;
}

.mode-name {
    color: var(--paper);
    font-size: 18px;
    margin-bottom: 8px;
}

.mode-desc {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
}

.map-wrap {
    padding: 0 24px 14px;
}

.museum-map {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
}

.museum-room {
    min-height: 124px;
    border-radius: 14px;
    border: 1px solid rgba(200, 169, 110, 0.14);
    background:
        radial-gradient(circle at top, rgba(200, 169, 110, 0.06), transparent 45%),
        rgba(13, 10, 8, 0.74);
    padding: 14px 14px 12px;
    position: relative;
    overflow: hidden;
}

.museum-room::after {
    content: "";
    position: absolute;
    inset: auto -30% -55% auto;
    width: 110px;
    height: 110px;
    border-radius: 50%;
    background: rgba(200, 169, 110, 0.05);
}

.museum-room.state-active {
    border-color: rgba(200, 169, 110, 0.6);
    box-shadow: 0 0 0 1px rgba(200, 169, 110, 0.08), inset 0 0 0 1px rgba(200, 169, 110, 0.08);
}

.museum-room.state-complete {
    background:
        radial-gradient(circle at top, rgba(200, 169, 110, 0.12), transparent 45%),
        rgba(18, 14, 11, 0.82);
}

.museum-room.state-idle {
    opacity: 0.8;
}

.museum-room-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 14px;
}

.museum-room-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 16px;
    margin-bottom: 8px;
}

.museum-room-copy {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.55;
}

.hall-tabs .tab-nav {
    padding: 0 20px !important;
    background: rgba(10, 8, 7, 0.84) !important;
    border-top: 1px solid var(--line) !important;
    border-bottom: 1px solid var(--line) !important;
}

.hall-tabs .tab-nav button {
    font-family: 'Cinzel', serif !important;
    color: var(--muted) !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    font-size: 10px !important;
    padding: 16px 18px !important;
    border-bottom: 2px solid transparent !important;
}

.hall-tabs .tab-nav button.selected {
    color: var(--gold) !important;
    border-bottom: 2px solid var(--gold) !important;
}

.hall-content {
    min-height: 420px;
    padding: 28px 26px !important;
    background: transparent !important;
}

.empty-state {
    min-height: 280px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--muted);
    font-size: 18px;
    font-style: italic;
    border: 1px dashed rgba(200, 169, 110, 0.18);
    border-radius: 12px;
    background: rgba(12, 9, 7, 0.45);
    padding: 24px;
}

.section-heading {
    font-size: 10px;
    color: var(--gold-soft);
    margin-bottom: 18px;
}

.lobby-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 18px;
}

.lobby-card,
.artifact-card,
.timeline-card,
.world-detail,
.visitor-book {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--panel);
}

.lobby-card {
    padding: 14px;
}

.lobby-label {
    font-size: 9px;
    color: var(--gold-soft);
    margin-bottom: 8px;
}

.lobby-value {
    font-size: 17px;
    color: var(--paper);
}

.lobby-summary {
    padding: 18px 20px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(14, 11, 9, 0.84);
    margin-bottom: 18px;
    line-height: 1.85;
    font-size: 18px;
}

.world-details {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
}

.world-detail {
    padding: 16px 18px;
}

.world-detail ul {
    margin: 8px 0 0 18px;
}

.world-detail li {
    margin-bottom: 6px;
}

.artifact-card {
    padding: 18px;
    margin-bottom: 14px;
}

.artifact-kicker {
    color: var(--gold-soft);
    font-size: 9px;
    margin-bottom: 8px;
}

.artifact-name {
    font-family: 'Cinzel', serif;
    color: var(--gold);
    font-size: 19px;
    margin-bottom: 6px;
}

.artifact-meta {
    color: var(--muted);
    font-style: italic;
    margin-bottom: 10px;
}

.artifact-desc {
    color: var(--paper);
    line-height: 1.8;
    font-size: 17px;
    margin-bottom: 12px;
}

.artifact-significance {
    color: var(--gold-soft);
    border-top: 1px solid var(--line);
    padding-top: 10px;
}

.timeline-card {
    padding: 16px 18px;
    margin-bottom: 12px;
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 16px;
}

.timeline-year {
    font-family: 'Cinzel', serif;
    color: var(--gold-soft);
    font-size: 12px;
    letter-spacing: 0.1em;
}

.timeline-title {
    font-family: 'Cinzel', serif;
    color: var(--paper);
    font-size: 16px;
    margin-bottom: 6px;
}

.timeline-desc {
    color: var(--muted);
    line-height: 1.7;
    font-size: 16px;
}

.timeline-type {
    color: var(--gold-soft);
    font-size: 12px;
    margin-top: 8px;
    font-style: italic;
}

.newspaper-shell {
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.16), transparent 25%),
        var(--panel-light);
    border-radius: 12px;
    color: var(--ink) !important;
    padding: 24px;
    border: 1px solid rgba(58, 42, 24, 0.18);
    box-shadow: inset 0 0 60px rgba(85, 58, 24, 0.08);
}

.newspaper-shell * {
    color: var(--ink) !important;
}

.paper-kicker {
    font-size: 10px;
    color: #7a5e3e;
    text-align: center;
    margin-bottom: 10px;
}

.newspaper-name {
    font-family: 'Cinzel', serif;
    font-size: 30px;
    text-align: center;
    border-top: 2px solid rgba(36, 26, 18, 0.82);
    border-bottom: 2px solid rgba(36, 26, 18, 0.82);
    padding: 8px 0;
    margin-bottom: 8px;
}

.newspaper-meta {
    text-align: center;
    color: #6d5740;
    font-size: 13px;
    font-style: italic;
    margin-bottom: 18px;
}

.newspaper-headline {
    font-family: 'Cinzel', serif;
    font-size: 22px;
    line-height: 1.35;
    margin-bottom: 12px;
}

.newspaper-body,
.newspaper-secondary-body {
    font-size: 17px;
    line-height: 1.8;
}

.newspaper-body {
    border-bottom: 1px solid rgba(70, 50, 30, 0.25);
    padding-bottom: 16px;
    margin-bottom: 16px;
}

.newspaper-secondary-headline {
    font-family: 'Cinzel', serif;
    font-size: 16px;
    margin-bottom: 8px;
}

.newspaper-ad {
    margin-top: 16px;
    padding: 12px 14px;
    border: 1px solid rgba(70, 50, 30, 0.22);
    font-size: 14px;
    color: #6f573e;
    font-style: italic;
}

.visitor-book {
    padding: 34px 28px;
    max-width: 760px;
    margin: 0 auto;
    text-align: center;
}

.visitor-kicker {
    color: var(--gold-soft);
    font-size: 10px;
    margin-bottom: 16px;
}

.visitor-entry {
    font-size: 24px;
    line-height: 1.8;
    color: var(--paper);
    font-style: italic;
    margin-bottom: 18px;
}

.visitor-signed {
    font-family: 'Cinzel', serif;
    color: var(--gold);
    font-size: 12px;
    letter-spacing: 0.12em;
}

.museum-footer {
    padding: 20px;
    text-align: center;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.16em;
}

@media (max-width: 900px) {
    .lobby-grid,
    .world-details,
    .timeline-card,
    .hero-grid,
    .museum-map,
    .status-panel {
        grid-template-columns: 1fr;
    }

    .hero-plaques {
        grid-template-columns: 1fr;
    }

    .status-side {
        border-left: none;
        border-top: 1px solid rgba(200, 169, 110, 0.12);
        padding-left: 0;
        padding-top: 14px;
    }

    .museum-title {
        font-size: 28px;
    }
}
"""

CURATOR_MODES = {
    "Anthropology": {
        "tagline": "Everyday life, social rules, and how people actually live.",
        "lead": "This mode focuses on work, ritual, family life, and the small systems that make an impossible world feel ordinary to the people inside it.",
        "plaque": "Daily life and social rules",
    },
    "Mythic": {
        "tagline": "Omens, sacred stories, and meaning shaped by belief.",
        "lead": "This mode leans toward prophecy, symbols, and ritual meaning, while still grounding the world in real social life.",
        "plaque": "Belief and ritual",
    },
    "Imperial Archive": {
        "tagline": "Official records, institutions, and the language of the state.",
        "lead": "This mode emphasizes chronicles, law, bureaucracy, and how powerful institutions describe the world in their own terms.",
        "plaque": "State records",
    },
    "Melancholy": {
        "tagline": "Loss, memory, and the human cost inside history.",
        "lead": "This mode softens the museum into something more intimate, with fading customs, private grief, and the emotional residue of public events.",
        "plaque": "Memory and loss",
    },
}

ROOMS = [
    ("lobby", "Lobby", "World overview", "The main rule, social structure, and tension at the center of the world."),
    ("artifacts", "Artifacts", "Object gallery", "Tools, relics, and impossible objects from everyday and public life."),
    ("timeline", "Timeline", "History wall", "The events that shaped the civilization over time."),
    ("newspaper", "Newspaper", "Press room", "A surviving front page from how this world saw itself."),
    ("visitor", "Visitor's Book", "Personal voice", "A single human voice to close the museum at ground level."),
]


def esc(value: str) -> str:
    return html.escape(str(value or ""))


def format_list(items) -> str:
    if not items:
        return "<p>None recorded.</p>"
    rows = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"<ul>{rows}</ul>"


def build_status_html(title: str, subtitle: str) -> str:
    return build_status_panel(title, subtitle, "Anthropology")


def build_status_panel(title: str, subtitle: str, curator_mode: str) -> str:
    mode = CURATOR_MODES.get(curator_mode, CURATOR_MODES["Anthropology"])
    return f"""
<div class="status-panel">
    <div>
        <div class="status-line">{esc(title)}</div>
        <div class="status-subline">{esc(subtitle)}</div>
    </div>
    <div class="status-side">
        <div class="mode-chip">Active curatorial lens</div>
        <div class="mode-name">{esc(curator_mode)}</div>
        <div class="mode-desc">{esc(mode["tagline"])}</div>
    </div>
</div>
"""


def build_lobby_html(world_bible: dict) -> str:
    if not world_bible or "museum_name" not in world_bible:
        return "<div class='empty-state'>Describe an impossible world to open the museum.</div>"

    stats = [
        ("Government", world_bible.get("government", "-")),
        ("Capital", world_bible.get("capital", "-")),
        ("Founded", world_bible.get("founded", "-")),
        ("Currency", world_bible.get("currency", "-")),
    ]
    stat_html = "".join(
        f"<div class='lobby-card'><div class='lobby-label'>{esc(label)}</div><div class='lobby-value'>{esc(value)}</div></div>"
        for label, value in stats
    )

    return f"""
<div class="section-heading">Orientation gallery</div>
<div class="lobby-grid">{stat_html}</div>
<div class="lobby-summary">{esc(world_bible.get("summary", ""))}</div>
<div class="world-details">
    <div class="world-detail">
        <div class="lobby-label">Laws of reality</div>
        {format_list(world_bible.get("laws_of_reality", []))}
    </div>
    <div class="world-detail">
        <div class="lobby-label">Historical anchors</div>
        {format_list(world_bible.get("historical_anchors", []))}
    </div>
    <div class="world-detail">
        <div class="lobby-label">Visual motifs</div>
        {format_list(world_bible.get("visual_motifs", []))}
    </div>
    <div class="world-detail">
        <div class="lobby-label">Daily life</div>
        <p>{esc(world_bible.get("daily_life", ""))}</p>
        <div class="lobby-label" style="margin-top:16px">One absolute taboo</div>
        <p>{esc(world_bible.get("taboo", ""))}</p>
    </div>
</div>
"""


def build_artifacts_html(data: dict) -> str:
    if not data or "artifacts" not in data:
        return "<div class='empty-state'>The artifact hall is still being catalogued.</div>"

    cards = []
    for artifact in data.get("artifacts", []):
        cards.append(
            f"""
<div class="artifact-card">
    <div class="artifact-kicker">Catalogued relic</div>
    <div class="artifact-name">{esc(artifact.get("name", ""))}</div>
    <div class="artifact-meta">{esc(artifact.get("era", ""))} | {esc(artifact.get("material", ""))}</div>
    <div class="artifact-desc">{esc(artifact.get("description", ""))}</div>
    <div class="artifact-significance">{esc(artifact.get("significance", ""))}</div>
</div>
"""
        )
    return "<div class='section-heading'>Artifacts hall</div>" + "".join(cards)


def build_timeline_html(data: dict) -> str:
    if not data or "events" not in data:
        return "<div class='empty-state'>The archivists are still arranging the chronology.</div>"

    cards = []
    for event in data.get("events", []):
        cards.append(
            f"""
<div class="timeline-card">
    <div class="timeline-year">{esc(event.get("year", ""))}</div>
    <div>
        <div class="timeline-title">{esc(event.get("title", ""))}</div>
        <div class="timeline-desc">{esc(event.get("description", ""))}</div>
        <div class="timeline-type">{esc(event.get("type", ""))}</div>
    </div>
</div>
"""
        )
    return "<div class='section-heading'>Timeline hall</div>" + "".join(cards)


def build_newspaper_html(data: dict) -> str:
    if not data or "headline" not in data:
        return "<div class='empty-state'>The presses have not finished tonight's edition.</div>"

    return f"""
<div class="newspaper-shell">
    <div class="paper-kicker">Printed for the morning crowd</div>
    <div class="newspaper-name">{esc(data.get("newspaper_name", "The Chronicle"))}</div>
    <div class="newspaper-meta">{esc(data.get("date", ""))} | {esc(data.get("weather", ""))}</div>
    <div class="newspaper-headline">{esc(data.get("headline", ""))}</div>
    <div class="newspaper-body">{esc(data.get("headline_body", ""))}</div>
    <div class="newspaper-secondary-headline">{esc(data.get("secondary_headline", ""))}</div>
    <div class="newspaper-secondary-body">{esc(data.get("secondary_body", ""))}</div>
    <div class="newspaper-ad">{esc(data.get("advertisement", ""))}</div>
</div>
"""


def build_visitor_book_html(data: dict) -> str:
    if not data or "entry" not in data:
        return "<div class='empty-state'>The visitor's book remains unopened.</div>"

    return f"""
<div class="visitor-book">
    <div class="visitor-kicker">Final testimony</div>
    <div class="visitor-entry">"{esc(data.get("entry", ""))}"</div>
    <div class="visitor-signed">{esc(data.get("signed", ""))}</div>
</div>
"""


def empty_gallery(message: str):
    return gr.update(value=f"<div class='empty-state'>{esc(message)}</div>")


def museum_heading(world_bible: dict) -> str:
    return f"""
<div class="museum-title">{esc(world_bible.get("museum_name", "Infinite Museum"))}</div>
<div class="museum-tagline">{esc(world_bible.get("tagline", ""))}</div>
"""


def build_hero_html(curator_mode: str) -> str:
    mode = CURATOR_MODES.get(curator_mode, CURATOR_MODES["Anthropology"])
    return f"""
<div class="museum-shell">
    <div class="museum-header">
        <div class="museum-marquee">
            <span>Impossible Civilizations Archive</span>
            <span>Museum open</span>
            <span>Mode: {esc(curator_mode)}</span>
        </div>
        <div class="hero-grid">
            <div class="hero-main">
                <div class="museum-kicker">Infinite Museum of Impossible Worlds</div>
                <div class="museum-title">Step Into A Civilization That Should Not Exist</div>
                <div class="museum-tagline">Every idea creates a civilization. Every civilization leaves artifacts.</div>
                <div class="museum-lead">{esc(mode["lead"])}</div>
                <div class="hero-plaques">
                    <div class="hero-plaque">
                        <div class="hero-plaque-label">Current mode</div>
                        <div class="hero-plaque-value">{esc(curator_mode)}</div>
                    </div>
                    <div class="hero-plaque">
                        <div class="hero-plaque-label">What this does</div>
                        <div class="hero-plaque-value">One idea becomes a full civilization.</div>
                    </div>
                    <div class="hero-plaque">
                        <div class="hero-plaque-label">Focus</div>
                        <div class="hero-plaque-value">{esc(mode["plaque"])}</div>
                    </div>
                </div>
            </div>
            <div class="hero-side">
                <div class="hero-side-heading">Curator note</div>
                <div class="hero-side-copy">{esc(mode["tagline"])}</div>
                <div class="hero-side-note">Describe one impossible condition. The museum will turn it into government, objects, history, news, and personal memory.</div>
            </div>
        </div>
    </div>
</div>
"""


def build_map_html(active_room: str, completed_rooms: list[str]) -> str:
    cards = []
    completed = set(completed_rooms)
    for room_id, title, kicker, copy in ROOMS:
        state = "state-idle"
        if room_id in completed:
            state = "state-complete"
        if room_id == active_room:
            state = "state-active"
        cards.append(
            f"""
<div class="museum-room {state}">
    <div class="museum-room-kicker">{esc(kicker)}</div>
    <div class="museum-room-title">{esc(title)}</div>
    <div class="museum-room-copy">{esc(copy)}</div>
</div>
"""
        )
    return "<div class='museum-map'>" + "".join(cards) + "</div>"


def format_concept(concept: str, curator_mode: str) -> str:
    mode = CURATOR_MODES.get(curator_mode, CURATOR_MODES["Anthropology"])
    return (
        f"{concept}\n\n"
        f"Curatorial lens: {curator_mode}. "
        f"Prioritize this sensibility: {mode['tagline']}"
    )


def generate_museum(concept: str, curator_mode: str):
    concept = (concept or "").strip()
    curator_mode = curator_mode or "Anthropology"
    if not concept:
        yield (
            build_status_panel("Awaiting a world concept", "Describe an impossible civilization to open the museum.", curator_mode),
            gr.update(value=build_hero_html(curator_mode)),
            gr.update(value=build_map_html("lobby", [])),
            gr.update(value="<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Every idea creates a civilization. Every civilization leaves artifacts.</div>"),
            empty_gallery("The museum awaits its first impossible world."),
            empty_gallery("The artifact hall is sealed."),
            empty_gallery("History has not yet been arranged."),
            empty_gallery("No front page has gone to print."),
            empty_gallery("No one has yet signed the visitor's book."),
        )
        return

    waiting = "The curatorial staff is preparing this hall."
    guided_concept = format_concept(concept, curator_mode)
    yield (
        build_status_panel("Opening the museum", "We are drafting the world bible and preparing the first gallery.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("lobby", [])),
        gr.update(value="<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Preparing a new impossible civilization.</div>"),
        empty_gallery("Drafting the foundational world bible."),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
    )

    world_bible = generate_world_bible(guided_concept)
    header = museum_heading(world_bible)

    yield (
        build_status_panel("Lobby opened", "The civilization has taken shape. The first records are now on display.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("artifacts", ["lobby"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        empty_gallery("Excavating artifacts from the collection vault."),
        empty_gallery("Assembling the official historical record."),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
    )

    artifacts = generate_artifacts(guided_concept, world_bible)
    yield (
        build_status_panel("Artifacts catalogued", "The collection vault has opened. The chronology is being assembled.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("timeline", ["lobby", "artifacts"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        empty_gallery("Assembling the official historical record."),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
    )

    timeline = generate_timeline(guided_concept, world_bible)
    yield (
        build_status_panel("Timeline restored", "The museum now knows how this world rose, changed, and endured.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("newspaper", ["lobby", "artifacts", "timeline"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        gr.update(value=build_timeline_html(timeline)),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
    )

    newspaper = generate_newspaper(guided_concept, world_bible)
    yield (
        build_status_panel("Presses running", "A surviving newspaper is now on display beside the official archive.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("visitor", ["lobby", "artifacts", "timeline", "newspaper"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        empty_gallery("Opening the final testimony cabinet."),
    )

    visitor_book = generate_visitor_book(guided_concept, world_bible)
    yield (
        build_status_panel("Museum complete", "All five halls are open. The world is ready to be explored.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("visitor", ["lobby", "artifacts", "timeline", "newspaper", "visitor"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        gr.update(value=build_visitor_book_html(visitor_book)),
    )


with gr.Blocks(css=CSS, title="Infinite Museum of Impossible Worlds") as demo:
    hero_html = gr.HTML(build_hero_html("Anthropology"))

    with gr.Row(elem_classes=["input-zone"]):
        with gr.Column(scale=5):
            concept_input = gr.Textbox(
                label="Describe an impossible world",
                placeholder="A world where dreams are currency. A city ruled by tides that remember. A moon where gravity is negotiated each morning.",
                lines=2,
            )
        with gr.Column(scale=1, min_width=190):
            generate_btn = gr.Button("Open Museum", elem_classes=["enter-btn"])

    with gr.Row(elem_classes=["control-shell"]):
        with gr.Column(elem_classes=["control-card"]):
            gr.HTML(
                """
<div class="control-panel-label">Curator modes</div>
<div class="control-panel-copy">Choose how the museum should frame the next world. The same premise can feel social, mythic, official, or intimate depending on the mode.</div>
"""
            )
            curator_mode = gr.Radio(
                choices=list(CURATOR_MODES.keys()),
                value="Anthropology",
                show_label=False,
                elem_classes=["mode-radio"],
            )

    with gr.Row(elem_classes=["status-wrap"]):
        status_html = gr.HTML(
            build_status_panel(
                "Awaiting a world concept",
                "Describe an impossible civilization to open the museum.",
                "Anthropology",
            )
        )

    museum_header = gr.HTML(
        "<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Every idea creates a civilization. Every civilization leaves artifacts.</div>"
    )
    map_html = gr.HTML(build_map_html("lobby", []), elem_classes=["map-wrap"])

    with gr.Tabs(elem_classes=["hall-tabs"]):
        with gr.Tab("Lobby"):
            lobby_html = gr.HTML(
                value="<div class='empty-state'>The museum awaits its first impossible world.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Tab("Artifacts"):
            artifacts_html = gr.HTML(
                value="<div class='empty-state'>The artifact hall is sealed.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Tab("Timeline"):
            timeline_html = gr.HTML(
                value="<div class='empty-state'>History has not yet been arranged.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Tab("Newspaper"):
            newspaper_html = gr.HTML(
                value="<div class='empty-state'>No front page has gone to print.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Tab("Visitor's Book"):
            visitor_html = gr.HTML(
                value="<div class='empty-state'>No one has yet signed the visitor's book.</div>",
                elem_classes=["hall-content"],
            )

    gr.HTML(
        """
<div class="museum-footer">
    Infinite Museum of Impossible Worlds | Small-model worldbuilding | Built for Build Small Hackathon 2026
</div>
"""
    )

    outputs = [
        status_html,
        hero_html,
        map_html,
        museum_header,
        lobby_html,
        artifacts_html,
        timeline_html,
        newspaper_html,
        visitor_html,
    ]

    curator_mode.change(
        fn=lambda mode: build_hero_html(mode),
        inputs=[curator_mode],
        outputs=[hero_html],
    )

    generate_btn.click(generate_museum, inputs=[concept_input, curator_mode], outputs=outputs)
    concept_input.submit(generate_museum, inputs=[concept_input, curator_mode], outputs=outputs)


if __name__ == "__main__":
    demo.launch()
