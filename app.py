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
}

.museum-header {
    padding: 44px 28px 34px;
    text-align: center;
    border-bottom: 1px solid var(--line);
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.08), transparent 40%),
        linear-gradient(180deg, rgba(12, 9, 7, 0.98), rgba(19, 14, 11, 0.92));
}

.museum-kicker,
.section-heading,
.progress-label,
.lobby-label,
.artifact-kicker,
.paper-kicker,
.visitor-kicker {
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
    font-size: 34px;
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

.input-zone {
    padding: 24px 24px 8px;
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
    padding: 6px 24px 18px;
}

.status-panel {
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 18px 20px;
    background: rgba(13, 10, 8, 0.72);
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
    color: var(--ink);
    padding: 24px;
    border: 1px solid rgba(58, 42, 24, 0.18);
    box-shadow: inset 0 0 60px rgba(85, 58, 24, 0.08);
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
    .timeline-card {
        grid-template-columns: 1fr;
    }

    .museum-title {
        font-size: 28px;
    }
}
"""


def esc(value: str) -> str:
    return html.escape(str(value or ""))


def format_list(items) -> str:
    if not items:
        return "<p>None recorded.</p>"
    rows = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"<ul>{rows}</ul>"


def build_status_html(title: str, subtitle: str) -> str:
    return f"""
<div class="status-panel">
    <div class="status-line">{esc(title)}</div>
    <div class="status-subline">{esc(subtitle)}</div>
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


def generate_museum(concept: str):
    concept = (concept or "").strip()
    if not concept:
        yield (
            build_status_html("Awaiting a world concept", "Describe an impossible civilization to open the museum."),
            gr.update(value="<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Every idea creates a civilization. Every civilization leaves artifacts.</div>"),
            empty_gallery("The museum awaits its first impossible world."),
            empty_gallery("The artifact hall is sealed."),
            empty_gallery("History has not yet been arranged."),
            empty_gallery("No front page has gone to print."),
            empty_gallery("No one has yet signed the visitor's book."),
        )
        return

    waiting = "The curatorial staff is preparing this hall."
    yield (
        build_status_html("Opening the museum", "We are drafting the world bible and preparing the first gallery."),
        gr.update(value="<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Preparing a new impossible civilization.</div>"),
        empty_gallery("Drafting the foundational world bible."),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
    )

    world_bible = generate_world_bible(concept)
    header = museum_heading(world_bible)

    yield (
        build_status_html("Lobby opened", "The civilization has taken shape. The first records are now on display."),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        empty_gallery("Excavating artifacts from the collection vault."),
        empty_gallery("Assembling the official historical record."),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
    )

    artifacts = generate_artifacts(concept, world_bible)
    yield (
        build_status_html("Artifacts catalogued", "The collection vault has opened. The chronology is being assembled."),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        empty_gallery("Assembling the official historical record."),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
    )

    timeline = generate_timeline(concept, world_bible)
    yield (
        build_status_html("Timeline restored", "The museum now knows how this world rose, changed, and endured."),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        gr.update(value=build_timeline_html(timeline)),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
    )

    newspaper = generate_newspaper(concept, world_bible)
    yield (
        build_status_html("Presses running", "A surviving newspaper is now on display beside the official archive."),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        empty_gallery("Opening the final testimony cabinet."),
    )

    visitor_book = generate_visitor_book(concept, world_bible)
    yield (
        build_status_html("Museum complete", "All five halls are open. The world is ready to be explored."),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html(artifacts)),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        gr.update(value=build_visitor_book_html(visitor_book)),
    )


with gr.Blocks(css=CSS, title="Infinite Museum of Impossible Worlds") as demo:
    gr.HTML(
        """
<div class="museum-shell">
    <div class="museum-header">
        <div class="museum-kicker">Department of impossible civilizations</div>
        <div class="museum-title">Infinite Museum of Impossible Worlds</div>
        <div class="museum-tagline">Every idea creates a civilization. Every civilization leaves artifacts.</div>
    </div>
</div>
"""
    )

    with gr.Row(elem_classes=["input-zone"]):
        with gr.Column(scale=5):
            concept_input = gr.Textbox(
                label="Describe an impossible world",
                placeholder="A world where dreams are currency. A city ruled by tides that remember. A moon where gravity is negotiated each morning.",
                lines=2,
            )
        with gr.Column(scale=1, min_width=190):
            generate_btn = gr.Button("Open Museum", elem_classes=["enter-btn"])

    with gr.Row(elem_classes=["status-wrap"]):
        status_html = gr.HTML(
            build_status_html(
                "Awaiting a world concept",
                "Describe an impossible civilization to open the museum.",
            )
        )

    museum_header = gr.HTML(
        "<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Every idea creates a civilization. Every civilization leaves artifacts.</div>"
    )

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
        museum_header,
        lobby_html,
        artifacts_html,
        timeline_html,
        newspaper_html,
        visitor_html,
    ]

    generate_btn.click(generate_museum, inputs=[concept_input], outputs=outputs)
    concept_input.submit(generate_museum, inputs=[concept_input], outputs=outputs)


if __name__ == "__main__":
    demo.launch()
