import html

import gradio as gr

from generators.engine import (
    generate_artifacts,
    generate_newspaper,
    generate_timeline,
    generate_visitor_book,
    generate_world_bible,
)


APP_HEAD = """
<script>
(() => {
  if (window.__museumUiBooted) return;
  window.__museumUiBooted = true;

  const ROOM_POINTS = {
    lobby: { x: 23, y: 24 },
    artifacts: { x: 79, y: 24 },
    timeline: { x: 25, y: 70 },
    newspaper: { x: 77, y: 70 },
    visitor: { x: 50, y: 75 },
    foyer: { x: 50, y: 49 }
  };

  const ROOM_LABELS = {
    lobby: "Lobby",
    artifacts: "Artifacts",
    timeline: "Timeline",
    newspaper: "Newspaper",
    visitor: "Visitor's Book",
    foyer: "Central Foyer"
  };

  const TAB_INDEX_TO_ROOM = ["lobby", "artifacts", "timeline", "newspaper", "visitor"];

  let walkToken = 0;

  function marker() {
    return document.getElementById("museum-visitor");
  }

  function caption() {
    return document.getElementById("museum-visitor-caption");
  }

  function currentMap() {
    return document.querySelector(".museum-map");
  }

  function setVisitorPosition(point) {
    const node = marker();
    if (!node || !point) return;
    node.style.left = `${point.x}%`;
    node.style.top = `${point.y}%`;
  }

  function setVisitorCaption(text) {
    const node = caption();
    if (node) node.textContent = text;
  }

  function setDoorTarget(roomId) {
    document.querySelectorAll(".museum-door").forEach((door) => {
      door.classList.toggle("is-target", !!roomId && door.getAttribute("data-door-id") === roomId);
    });
  }

  function pathForRoom(roomId) {
    const target = ROOM_POINTS[roomId];
    if (!target) return [];
    if (roomId === "visitor") return [ROOM_POINTS.foyer, { x: 50, y: 67 }, target];
    if (roomId === "lobby" || roomId === "artifacts") return [ROOM_POINTS.foyer, { x: target.x, y: 24 }, target];
    return [ROOM_POINTS.foyer, { x: target.x, y: 70 }, target];
  }

  function setActiveHall(roomId, scrollIntoView = true) {
    document.querySelectorAll(".museum-hall-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.id === `hall-panel-${roomId}`);
    });
    document.querySelectorAll(".museum-hall-nav-btn").forEach((button) => {
      button.classList.toggle("is-active", button.getAttribute("data-hall-target") === roomId);
    });
    if (scrollIntoView) {
      const stack = document.querySelector(".museum-hall-stack");
      if (stack) {
        stack.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  function syncMapToSelectedTab() {
    const map = currentMap();
    const roomId = map?.getAttribute("data-active-room") || "lobby";
    if (!roomId) return;
    setActiveHall(roomId, false);
    setVisitorPosition(ROOM_POINTS[roomId] || ROOM_POINTS.lobby);
    setVisitorCaption(`Standing in ${ROOM_LABELS[roomId] || "Lobby"}`);
    setDoorTarget("");
    const node = marker();
    if (node) node.classList.remove("walking");
  }

  function positionFromActiveRoom() {
    const map = currentMap();
    if (!map) return;
    const roomId = map.getAttribute("data-active-room") || "lobby";
    setVisitorPosition(ROOM_POINTS[roomId] || ROOM_POINTS.lobby);
    setVisitorCaption(`Standing in ${ROOM_LABELS[roomId] || "Lobby"}`);
    setDoorTarget("");
    const node = marker();
    if (node) node.classList.remove("walking");
  }

  window.museumNavigate = function museumNavigate(room) {
    if (!room) return false;
    const roomId = room.getAttribute("data-room-id");
    const tabIndex = Number(room.getAttribute("data-tab-index"));
    const node = marker();
    const steps = pathForRoom(roomId);
    if (!node || !steps.length) {
      openMuseumTab(tabIndex);
      return false;
    }

    const token = ++walkToken;
    node.classList.add("walking");
    setDoorTarget(roomId);
    setVisitorCaption(`Walking to ${ROOM_LABELS[roomId] || "hall"}...`);

    let index = 0;
    const advance = () => {
      if (token !== walkToken) return;
      setVisitorPosition(steps[index]);
      index += 1;
      if (index < steps.length) {
        window.setTimeout(advance, 300);
        return;
      }

      window.setTimeout(() => {
        if (token !== walkToken) return;
        node.classList.remove("walking");
        setDoorTarget("");
        setVisitorCaption(`Standing in ${ROOM_LABELS[roomId] || "hall"}`);
        const map = currentMap();
        if (map) {
          map.setAttribute("data-active-room", roomId);
        }
        setActiveHall(roomId, true);
      }, 160);
    };

    advance();
    return false;
  };

  function applyTheme(theme) {
    const value = theme || "retro";
    document.body.setAttribute("data-museum-theme", value);
    window.localStorage.setItem("museum-theme", value);
    document.querySelectorAll("[data-theme-switch]").forEach((button) => {
      button.classList.toggle("is-active", button.getAttribute("data-theme-switch") === value);
    });
  }

  document.addEventListener("click", (event) => {
    const themeButton = event.target.closest("[data-theme-switch]");
    if (themeButton) {
      event.preventDefault();
      applyTheme(themeButton.getAttribute("data-theme-switch"));
      return;
    }

    const hallButton = event.target.closest(".museum-hall-nav-btn");
    if (hallButton) {
      event.preventDefault();
      const roomId = hallButton.getAttribute("data-hall-target");
      const pseudoRoom = document.querySelector(`.museum-room[data-room-id="${roomId}"]`);
      if (pseudoRoom) {
        window.museumNavigate(pseudoRoom);
      } else {
        setActiveHall(roomId, true);
      }
      return;
    }

    const room = event.target.closest(".museum-room[data-room-id]");
    if (!room) return;
    event.preventDefault();
    window.museumNavigate(room);
  });

  document.addEventListener("keydown", (event) => {
    const room = event.target.closest(".museum-room[data-room-id]");
    if (!room) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    window.museumNavigate(room);
  });

  function bootMuseumUi() {
    applyTheme(window.localStorage.getItem("museum-theme") || "retro");
    positionFromActiveRoom();
    window.setTimeout(positionFromActiveRoom, 250);
    window.setTimeout(positionFromActiveRoom, 900);
    window.setTimeout(syncMapToSelectedTab, 500);
  }

  if (document.readyState === "loading") {
    window.addEventListener("load", bootMuseumUi);
  } else {
    bootMuseumUi();
  }
})();
</script>
"""


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
    max-width: none !important;
    width: 100% !important;
    padding: 0 20px 36px !important;
}

.input-zone,
.control-shell,
.status-wrap,
.theme-wrap,
.map-wrap,
.hall-tabs,
.museum-hall-stack,
.museum-footer {
    width: min(100%, 1540px);
    margin-left: auto;
    margin-right: auto;
}

body[data-museum-theme="retro"] {
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

body[data-museum-theme="dark"] {
    --bg: #0b1018;
    --bg-deep: #06080c;
    --bg-wash: #132238;
    --panel: rgba(11, 16, 24, 0.94);
    --panel-light: rgba(220, 233, 252, 0.96);
    --line: rgba(101, 163, 255, 0.22);
    --gold: #8fb6ff;
    --gold-soft: #5f7fad;
    --paper: #e8f0ff;
    --muted: #98a8c7;
    --ink: #0d1522;
}

body[data-museum-theme="light"] {
    --bg: #f4efe5;
    --bg-deep: #ece4d6;
    --bg-wash: #d5c4a7;
    --panel: rgba(251, 248, 241, 0.94);
    --panel-light: rgba(255, 252, 246, 0.98);
    --line: rgba(126, 92, 43, 0.22);
    --gold: #7f5b2b;
    --gold-soft: #9e7a46;
    --paper: #2b2013;
    --muted: #6a5843;
    --ink: #241a12;
}

.museum-shell {
    border: 1px solid var(--line);
    margin: 20px auto;
    background: rgba(10, 8, 7, 0.72);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
    overflow: hidden;
    width: min(100%, 1540px);
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
    padding: 24px 24px 6px;
}

.input-zone textarea,
.input-zone input {
    background: rgba(10, 8, 7, 0.92) !important;
    color: var(--paper) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    font-size: 17px !important;
    box-shadow: none !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
}

.input-zone textarea:focus,
.input-zone input:focus {
    border-color: rgba(200, 169, 110, 0.55) !important;
    box-shadow: 0 0 0 4px rgba(200, 169, 110, 0.08) !important;
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

.theme-wrap {
    padding: 0 24px 12px;
}

.theme-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 14px 18px;
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.08), transparent 18%),
        rgba(17, 12, 10, 0.7);
}

.theme-bar-copy {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.5;
}

.theme-chip-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.theme-chip {
    appearance: none;
    border: 1px solid rgba(200, 169, 110, 0.24);
    border-radius: 999px;
    background: rgba(18, 13, 11, 0.72);
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 11px 16px;
    cursor: pointer;
    transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.theme-chip:hover,
.theme-chip.is-active {
    transform: translateY(-1px);
    border-color: rgba(200, 169, 110, 0.55);
    background: rgba(200, 169, 110, 0.14);
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
    min-height: 96px;
    background: linear-gradient(180deg, #2c2117, #17100c) !important;
    color: var(--gold) !important;
    border: 1px solid rgba(200, 169, 110, 0.45) !important;
    border-radius: 16px !important;
    font-family: 'Cinzel', serif !important;
    font-size: 12px !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    box-shadow:
        inset 0 1px 0 rgba(200, 169, 110, 0.1),
        0 14px 30px rgba(0, 0, 0, 0.24);
    transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
}

.enter-btn:hover {
    border-color: rgba(200, 169, 110, 0.8) !important;
    background: linear-gradient(180deg, #35281a, #19120d) !important;
    transform: translateY(-1px);
    box-shadow:
        inset 0 1px 0 rgba(200, 169, 110, 0.12),
        0 18px 36px rgba(0, 0, 0, 0.28);
}

.museum-action-btn,
.museum-secondary-btn {
    background: linear-gradient(180deg, rgba(44, 33, 23, 0.96), rgba(23, 16, 12, 0.96)) !important;
    color: var(--gold) !important;
    border: 1px solid rgba(200, 169, 110, 0.4) !important;
    border-radius: 999px !important;
    font-family: 'Cinzel', serif !important;
    text-transform: uppercase !important;
    box-shadow: inset 0 1px 0 rgba(200, 169, 110, 0.08);
    transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease !important;
}

.museum-action-btn {
    min-height: 42px !important;
    padding: 0 18px !important;
    font-size: 11px !important;
    letter-spacing: 0.16em !important;
}

.museum-secondary-btn {
    min-height: 38px !important;
    padding: 0 14px !important;
    font-size: 10px !important;
    letter-spacing: 0.14em !important;
}

.museum-action-btn:hover,
.museum-secondary-btn:hover {
    border-color: rgba(200, 169, 110, 0.78) !important;
    background: linear-gradient(180deg, rgba(53, 40, 26, 0.98), rgba(25, 18, 13, 0.98)) !important;
    transform: translateY(-1px);
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
    position: relative;
    min-height: 560px;
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-radius: 24px;
    background:
        radial-gradient(circle at top left, rgba(200, 169, 110, 0.08), transparent 20%),
        linear-gradient(180deg, rgba(18, 13, 11, 0.92), rgba(11, 8, 7, 0.96));
    overflow: hidden;
    box-shadow:
        inset 0 1px 0 rgba(200, 169, 110, 0.04),
        0 18px 44px rgba(0, 0, 0, 0.22);
}

.museum-map::before {
    content: "";
    position: absolute;
    inset: 18px;
    border: 1px dashed rgba(200, 169, 110, 0.08);
    border-radius: 14px;
    pointer-events: none;
}

.museum-blueprint-line {
    position: relative;
    background: rgba(200, 169, 110, 0.28);
    border-radius: 999px;
    box-shadow: 0 0 0 1px rgba(200, 169, 110, 0.04);
}

.museum-blueprint-line.h {
    height: 2px;
}

.museum-blueprint-line.v {
    width: 2px;
}

.museum-room {
    position: absolute;
    border-radius: 20px;
    border: 1.5px solid rgba(200, 169, 110, 0.26);
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.06), rgba(200, 169, 110, 0.02)),
        rgba(15, 11, 9, 0.58);
    padding: 18px 18px 14px;
    cursor: pointer;
    transition: transform 0.18s ease, border-color 0.18s ease, opacity 0.18s ease;
    z-index: 2;
    display: flex;
    flex-direction: column;
    justify-content: center;
    backdrop-filter: blur(1px);
}

.museum-room::before {
    content: "";
    position: absolute;
    inset: 10px;
    border: 1px solid rgba(200, 169, 110, 0.1);
    border-radius: 14px;
    pointer-events: none;
}

.museum-room::after {
    content: "";
    position: absolute;
    inset: auto 14px 12px auto;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 1px solid rgba(200, 169, 110, 0.12);
    background: rgba(200, 169, 110, 0.03);
}

.museum-room:hover {
    transform: translateY(-2px);
    border-color: rgba(200, 169, 110, 0.35);
}

.museum-room.state-active {
    border-color: rgba(200, 169, 110, 0.6);
    box-shadow: 0 0 0 1px rgba(200, 169, 110, 0.08), inset 0 0 0 1px rgba(200, 169, 110, 0.08), 0 0 28px rgba(200, 169, 110, 0.08);
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.12), rgba(200, 169, 110, 0.04)),
        rgba(20, 15, 11, 0.8);
}

.museum-room.state-complete {
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.08), rgba(200, 169, 110, 0.02)),
        rgba(18, 14, 11, 0.68);
    border-color: rgba(200, 169, 110, 0.28);
}

.museum-room.state-idle {
    opacity: 0.8;
}

.museum-room.state-active .museum-room-title {
    color: #f4dfb0;
}

.museum-room.state-complete .museum-room-kicker {
    color: #b8965f;
}

.museum-room--lobby {
    clip-path: polygon(0 14%, 14% 0, 88% 0, 100% 16%, 100% 86%, 86% 100%, 0 100%);
}

.museum-room--artifacts {
    clip-path: polygon(0 0, 74% 0, 74% 14%, 100% 14%, 100% 100%, 0 100%);
}

.museum-room--timeline {
    clip-path: polygon(0 0, 100% 0, 100% 78%, 84% 78%, 84% 100%, 0 100%);
}

.museum-room--newspaper {
    clip-path: polygon(0 14%, 26% 14%, 26% 0, 100% 0, 100% 100%, 0 100%);
}

.museum-room--visitor {
    clip-path: ellipse(50% 50% at 50% 50%);
    padding-top: 12px;
    text-align: center;
}

.museum-room--visitor::before {
    border-radius: 999px;
}

.museum-room--visitor .museum-room-copy {
    margin: 0 auto;
    max-width: 20ch;
}

.museum-door {
    position: absolute;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1px solid rgba(200, 169, 110, 0.18);
    background: rgba(200, 169, 110, 0.08);
    box-shadow: 0 0 0 rgba(200, 169, 110, 0);
    transition: background 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.museum-door.is-target {
    background: rgba(200, 169, 110, 0.26);
    border-color: rgba(200, 169, 110, 0.55);
    box-shadow: 0 0 18px rgba(200, 169, 110, 0.38);
    animation: museumDoorPulse 1.2s infinite ease-in-out;
}

@keyframes museumDoorPulse {
    0%, 100% {
        transform: scale(1);
        opacity: 0.85;
    }
    50% {
        transform: scale(1.18);
        opacity: 1;
    }
}

.museum-room-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 8px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 8px;
    opacity: 0.82;
}

.museum-room-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 19px;
    letter-spacing: 0.03em;
    margin-bottom: 4px;
    text-wrap: balance;
}

.museum-room-copy {
    color: var(--muted);
    display: none;
}

.museum-foyer {
    position: absolute;
    left: 42.5%;
    top: 38%;
    width: 15%;
    height: 22%;
    border: 1.5px solid rgba(200, 169, 110, 0.22);
    border-radius: 999px;
    background:
        radial-gradient(circle at center, rgba(200, 169, 110, 0.08), transparent 58%),
        rgba(20, 15, 12, 0.34);
}

.museum-foyer-label {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    color: rgba(232, 223, 200, 0.52);
    font-family: 'Cinzel', serif;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    white-space: nowrap;
}

.museum-visitor {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    background: radial-gradient(circle at 35% 35%, #f7dfaa, #d9b26e 58%, #8f6f3a 100%);
    box-shadow: 0 0 22px rgba(200, 169, 110, 0.32);
    border: 1px solid rgba(18, 12, 9, 0.72);
    transform: translate(-50%, -50%);
    transition:
        left 0.24s ease,
        top 0.24s ease,
        transform 0.18s ease;
    pointer-events: none;
    z-index: 4;
}

.museum-visitor::after {
    content: "";
    position: absolute;
    left: 50%;
    top: calc(100% + 2px);
    width: 10px;
    height: 12px;
    border-radius: 999px;
    transform: translate(-50%, -50%);
    background: linear-gradient(180deg, rgba(217, 178, 110, 0.95), rgba(143, 111, 58, 0.9));
    clip-path: polygon(30% 0%, 70% 0%, 100% 100%, 0% 100%);
}

.museum-visitor.walking {
    animation: museumWalker 0.6s infinite ease-in-out;
}

@keyframes museumWalker {
    0%, 100% {
        transform: translate(-50%, -50%) scale(1) translateY(0);
    }
    50% {
        transform: translate(-50%, -50%) scale(1.05) translateY(-3px);
    }
}

.museum-visitor-label {
    position: absolute;
    left: 50%;
    top: calc(100% + 18px);
    transform: translateX(-50%);
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 8px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
    opacity: 0.85;
}

.museum-visitor-caption {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 12px);
    transform: translateX(-50%);
    color: var(--paper);
    background: rgba(12, 9, 7, 0.88);
    border: 1px solid rgba(200, 169, 110, 0.18);
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 11px;
    line-height: 1;
    white-space: nowrap;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.museum-map-help {
    margin-top: 14px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.5;
    text-align: center;
}

.museum-legend {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    margin-top: 18px;
}

.museum-legend-item {
    border: 1px solid rgba(200, 169, 110, 0.12);
    border-radius: 14px;
    padding: 12px 12px 10px;
    text-align: center;
    background: rgba(12, 9, 7, 0.42);
}

.museum-legend-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 4px;
}

.museum-legend-copy {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.45;
}

body[data-museum-theme="light"] .museum-shell,
body[data-museum-theme="light"] .control-card,
body[data-museum-theme="light"] .theme-bar,
body[data-museum-theme="light"] .museum-map,
body[data-museum-theme="light"] .hall-tabs .tab-nav,
body[data-museum-theme="light"] .hero-side,
body[data-museum-theme="light"] .hero-plaque,
body[data-museum-theme="light"] .status-panel,
body[data-museum-theme="light"] .loading-card,
body[data-museum-theme="light"] .museum-room {
    background-color: rgba(255, 251, 244, 0.86) !important;
}

body[data-museum-theme="light"] .input-zone textarea,
body[data-museum-theme="light"] .input-zone input,
body[data-museum-theme="light"] .theme-chip {
    background: rgba(255, 251, 244, 0.92) !important;
    color: var(--paper) !important;
}

body[data-museum-theme="light"] .museum-room-copy,
body[data-museum-theme="light"] .hero-side-note,
body[data-museum-theme="light"] .control-panel-copy,
body[data-museum-theme="light"] .museum-map-help,
body[data-museum-theme="light"] .museum-legend-copy {
    color: #6e604d !important;
}

body[data-museum-theme="dark"] .museum-map,
body[data-museum-theme="dark"] .control-card,
body[data-museum-theme="dark"] .theme-bar,
body[data-museum-theme="dark"] .museum-shell,
body[data-museum-theme="dark"] .museum-room,
body[data-museum-theme="dark"] .hall-tabs .tab-nav {
    background-color: rgba(10, 14, 22, 0.88) !important;
}

.museum-hall-stack {
    padding: 0 24px 30px;
}

.museum-section-intro {
    width: min(100%, 1540px);
    margin: 6px auto 10px;
    text-align: center;
}

.museum-section-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.museum-section-title {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 38px;
    line-height: 1.15;
    margin-bottom: 8px;
}

.museum-section-copy {
    color: var(--muted);
    font-size: 18px;
    line-height: 1.65;
    max-width: 840px;
    margin: 0 auto;
}

.museum-hall-shell {
    margin-top: 14px;
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-radius: 22px 22px 0 0;
    background:
        radial-gradient(circle at top, rgba(200, 169, 110, 0.08), transparent 26%),
        linear-gradient(180deg, rgba(17, 12, 10, 0.82), rgba(10, 8, 7, 0.86));
    padding: 20px 24px 22px;
    box-shadow: inset 0 1px 0 rgba(200, 169, 110, 0.05);
}

.museum-hall-shell::before {
    content: "Current Hall";
    display: block;
    margin-bottom: 14px;
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    text-align: center;
}

.museum-hall-nav {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    padding: 0 0 18px;
    margin-top: 0;
    border-bottom: 1px solid var(--line);
}

.museum-hall-nav-btn {
    appearance: none;
    border: 1px solid rgba(200, 169, 110, 0.18);
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 40%),
        rgba(16, 12, 10, 0.42);
    color: var(--muted);
    border-radius: 18px;
    padding: 14px;
    cursor: pointer;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-height: 102px;
}

.museum-hall-nav-btn:hover,
.museum-hall-nav-btn.is-active {
    color: var(--gold);
    border-color: rgba(200, 169, 110, 0.5);
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.16), rgba(18, 13, 11, 0.82)),
        rgba(200, 169, 110, 0.08);
    transform: translateY(-1px);
    box-shadow: inset 0 1px 0 rgba(200, 169, 110, 0.09);
}

.museum-hall-nav-index {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.museum-hall-nav-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 15px;
    line-height: 1.25;
}

.museum-hall-nav-copy {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.45;
}

.museum-hall-panel {
    display: none;
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-top: none;
    border-radius: 0 0 22px 22px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.06), transparent 18%),
        rgba(10, 8, 7, 0.84);
    padding: 18px 18px 20px;
}

.museum-hall-panel.is-active {
    display: block;
}

.museum-hall-panel,
.museum-hall-panel > .gradio-container,
.museum-hall-panel .gr-group,
.museum-hall-panel .gr-box,
.museum-hall-panel .gr-panel {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

.museum-hall-panel .gr-form,
.museum-hall-panel .gr-block,
.museum-hall-panel .gr-column,
.museum-hall-panel .gr-row {
    background: transparent !important;
}

.hall-panel-header {
    padding-bottom: 14px;
    margin-bottom: 16px;
    border-bottom: 1px solid rgba(200, 169, 110, 0.12);
}

.hall-panel-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.hall-panel-title {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 28px;
    line-height: 1.2;
}

.hall-panel-copy {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.65;
    max-width: 820px;
    margin-top: 8px;
}

.hall-action-row {
    gap: 10px;
    margin-bottom: 12px;
}

.hall-content {
    min-height: 220px;
    padding: 20px 4px 4px !important;
    background: transparent !important;
    max-width: 1240px;
    margin: 0 auto;
}

.empty-state {
    min-height: 170px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--muted);
    font-size: 19px;
    font-style: italic;
    border: 1px dashed rgba(200, 169, 110, 0.18);
    border-radius: 12px;
    background:
        radial-gradient(circle at top, rgba(200, 169, 110, 0.05), transparent 28%),
        rgba(12, 9, 7, 0.28);
    padding: 26px;
}

.loading-card {
    min-height: 280px;
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-radius: 16px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.08), transparent 28%),
        rgba(12, 9, 7, 0.72);
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 18px;
}

.loading-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}

.loading-title {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 24px;
    line-height: 1.35;
    margin: 6px 0 10px;
}

.loading-copy {
    color: var(--paper);
    font-size: 17px;
    line-height: 1.75;
    max-width: 720px;
}

.loading-track {
    width: 100%;
    height: 7px;
    border-radius: 999px;
    background: rgba(200, 169, 110, 0.12);
    overflow: hidden;
}

.loading-bar {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(200, 169, 110, 0.3), rgba(200, 169, 110, 0.9));
    box-shadow: 0 0 18px rgba(200, 169, 110, 0.22);
}

.loading-meta {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: center;
    color: var(--muted);
    font-size: 15px;
}

.loading-dots {
    display: inline-flex;
    gap: 8px;
    align-items: center;
}

.loading-dots span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(200, 169, 110, 0.25);
    animation: museumPulse 1.2s infinite ease-in-out;
}

.loading-dots span:nth-child(2) {
    animation-delay: 0.15s;
}

.loading-dots span:nth-child(3) {
    animation-delay: 0.3s;
}

@keyframes museumPulse {
    0%, 80%, 100% {
        transform: scale(0.8);
        opacity: 0.4;
    }
    40% {
        transform: scale(1.15);
        opacity: 1;
    }
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
    padding: 22px 24px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.06), transparent 24%),
        rgba(14, 11, 9, 0.84);
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
    padding: 20px 20px 18px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
}

.artifact-card::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: linear-gradient(180deg, rgba(200, 169, 110, 0.85), rgba(200, 169, 110, 0.15));
}

.featured-artifact {
    border: 1px solid var(--line);
    border-radius: 16px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.08), transparent 28%),
        rgba(15, 11, 9, 0.88);
    padding: 18px;
    margin-bottom: 16px;
}

.featured-grid {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 18px;
    align-items: stretch;
}

.featured-image-shell {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(200, 169, 110, 0.15);
    background: rgba(10, 8, 7, 0.5);
    min-height: 320px;
}

.featured-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

.featured-placeholder {
    min-height: 320px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--muted);
    font-size: 17px;
    line-height: 1.7;
    padding: 18px;
}

.featured-copy {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.featured-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.featured-title {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 24px;
    margin-bottom: 10px;
}

.featured-text {
    color: var(--paper);
    font-size: 17px;
    line-height: 1.75;
    margin-bottom: 12px;
}

.featured-prompt {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.65;
    border-top: 1px solid rgba(200, 169, 110, 0.14);
    padding-top: 12px;
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
    padding: 18px 20px;
    margin-bottom: 12px;
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 16px;
    position: relative;
    overflow: hidden;
}

.timeline-card::before {
    content: "";
    position: absolute;
    left: 110px;
    top: 18px;
    bottom: 18px;
    width: 1px;
    background: rgba(200, 169, 110, 0.16);
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
    border-radius: 18px;
    color: var(--ink) !important;
    padding: 28px;
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
    padding: 42px 32px;
    max-width: 760px;
    margin: 0 auto;
    text-align: center;
    border-radius: 18px;
    background:
        radial-gradient(circle at top, rgba(200, 169, 110, 0.08), transparent 24%),
        rgba(12, 9, 7, 0.72);
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
    .status-panel,
    .featured-grid {
        grid-template-columns: 1fr;
    }

    .museum-map {
        min-height: 520px;
    }

    .hero-plaques {
        grid-template-columns: 1fr;
    }

    .museum-hall-nav {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .museum-hall-nav-btn {
        min-height: 92px;
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

@media (max-width: 640px) {
    .gradio-container {
        padding: 0 12px 24px !important;
    }

    .museum-header,
    .control-shell,
    .theme-wrap,
    .status-wrap,
    .input-zone,
    .map-wrap,
    .museum-hall-stack {
        padding-left: 0;
        padding-right: 0;
    }

    .museum-map {
        min-height: 460px;
        border-radius: 18px;
    }

    .museum-legend,
    .museum-hall-nav {
        grid-template-columns: 1fr;
    }

    .hall-panel-title {
        font-size: 24px;
    }

    .timeline-card::before {
        display: none;
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

ROOM_LAYOUT = {
    "lobby": {"left": "7.5%", "top": "11%", "width": "26%", "height": "24%", "visitor_left": "23%", "visitor_top": "24%"},
    "artifacts": {"left": "65.5%", "top": "11%", "width": "27%", "height": "24%", "visitor_left": "79%", "visitor_top": "24%"},
    "timeline": {"left": "8.5%", "top": "60%", "width": "28%", "height": "20%", "visitor_left": "25%", "visitor_top": "70%"},
    "newspaper": {"left": "64.5%", "top": "60%", "width": "28%", "height": "20%", "visitor_left": "77%", "visitor_top": "70%"},
    "visitor": {"left": "35.5%", "top": "68%", "width": "29%", "height": "14%", "visitor_left": "50%", "visitor_top": "75%"},
}


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
    featured = data.get("featured_image") if isinstance(data, dict) else None
    featured_html = ""
    if featured:
        lead = featured.get("artifact", {})
        prompt_text = featured.get("prompt", "") if isinstance(featured, dict) else ""
        image_src = ""
        if isinstance(featured, dict):
            image_src = featured.get("image_url") or featured.get("image_path") or ""
        if image_src:
            media = f"<img class='featured-image' src='{esc(image_src)}' alt='{esc(lead.get('name', 'Featured artifact'))}'>"
        else:
            media = "<div class='featured-placeholder'>No artifact image generated yet. Use one of the image buttons below to render an object on demand.</div>"

        featured_html = f"""
<div class="featured-artifact">
    <div class="featured-grid">
        <div class="featured-image-shell">{media}</div>
        <div class="featured-copy">
            <div>
                <div class="featured-label">Featured artifact</div>
                <div class="featured-title">{esc(lead.get('name', 'Featured artifact'))}</div>
                <div class="featured-text">{esc(lead.get('description', ''))}</div>
                <div class="featured-text"><strong>Material:</strong> {esc(lead.get('material', ''))} | <strong>Era:</strong> {esc(lead.get('era', ''))}</div>
            </div>
            <div class="featured-prompt">Image prompt: {esc(prompt_text or 'This prompt will appear here once the backend hook is active.')}</div>
        </div>
    </div>
</div>
"""
    else:
        featured_html = """
<div class="featured-artifact">
    <div class="featured-grid">
        <div class="featured-image-shell">
            <div class="featured-placeholder">No artifact image generated yet. Pick an artifact below and render it only when you want it.</div>
        </div>
        <div class="featured-copy">
            <div>
                <div class="featured-label">Artifact image</div>
                <div class="featured-title">On-demand generation</div>
                <div class="featured-text">The museum no longer slows down by generating images automatically. Click an artifact image button when you want to render one object.</div>
            </div>
            <div class="featured-prompt">The chosen artifact prompt will appear here after generation.</div>
        </div>
    </div>
</div>
"""

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
    return "<div class='section-heading'>Artifacts hall</div>" + featured_html + "".join(cards)


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
<div class="museum-section-intro">
    <div class="museum-section-kicker">Current exhibition</div>
    <div class="museum-section-title">{esc(world_bible.get("museum_name", "Infinite Museum"))}</div>
    <div class="museum-section-copy">{esc(world_bible.get("tagline", ""))}</div>
</div>
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
    visitor_room = active_room if active_room in ROOM_LAYOUT else "lobby"
    for room_id, title, kicker, copy in ROOMS:
        tab_index = next(index for index, room in enumerate(ROOMS) if room[0] == room_id)
        state = "state-idle"
        if room_id in completed:
            state = "state-complete"
        if room_id == active_room:
            state = "state-active"
        layout = ROOM_LAYOUT[room_id]
        cards.append(
            f"""
<div class="museum-room museum-room--{esc(room_id)} {state}" data-hall="{esc(title)}" data-room-id="{esc(room_id)}" data-tab-index="{tab_index}" role="button" tabindex="0" aria-label="Open {esc(title)} hall" onclick="window.museumNavigate && window.museumNavigate(this)" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault(); window.museumNavigate && window.museumNavigate(this);}}" style="left:{layout['left']};top:{layout['top']};width:{layout['width']};height:{layout['height']};">
    <div class="museum-room-kicker">{esc(kicker)}</div>
    <div class="museum-room-title">{esc(title)}</div>
    <div class="museum-room-copy">{esc(copy)}</div>
</div>
"""
        )
    visitor_layout = ROOM_LAYOUT[visitor_room]
    legend = "".join(
        f"""
<div class="museum-legend-item museum-legend-item--{esc(room_id)}">
    <div class="museum-legend-title">{esc(title)}</div>
    <div class="museum-legend-copy">{esc(copy)}</div>
</div>
"""
        for room_id, title, _kicker, copy in ROOMS
    )
    blueprint = f"""
<div class='museum-map' data-active-room='{esc(visitor_room)}'>
    <div class='museum-blueprint-line h' style='position:absolute;left:32%;top:24%;width:36%;'></div>
    <div class='museum-blueprint-line h' style='position:absolute;left:34%;top:70%;width:32%;'></div>
    <div class='museum-blueprint-line v' style='position:absolute;left:50%;top:24%;height:46%;'></div>
    <div class='museum-blueprint-line v' style='position:absolute;left:23%;top:35%;height:25%;'></div>
    <div class='museum-blueprint-line v' style='position:absolute;left:79%;top:35%;height:25%;'></div>
    <div class='museum-door' data-door-id='lobby' style='left:31.3%;top:23.2%;'></div>
    <div class='museum-door' data-door-id='artifacts' style='left:67.3%;top:23.2%;'></div>
    <div class='museum-door' data-door-id='timeline' style='left:33.2%;top:69.3%;'></div>
    <div class='museum-door' data-door-id='newspaper' style='left:65.7%;top:69.3%;'></div>
    <div class='museum-door' data-door-id='visitor' style='left:49.2%;top:66.2%;'></div>
    <div class='museum-foyer'><div class='museum-foyer-label'>Central Foyer</div></div>
    <div class='museum-visitor' id='museum-visitor' style='left:{visitor_layout["visitor_left"]};top:{visitor_layout["visitor_top"]};'>
        <div class='museum-visitor-caption' id='museum-visitor-caption'>Standing in {esc(next(room[1] for room in ROOMS if room[0] == visitor_room))}</div>
        <div class='museum-visitor-label'>You are here</div>
    </div>
    {''.join(cards)}
</div>
<div class='museum-map-help'>Move through the floor plan by clicking a hall. The marker walks through the foyer and opens that gallery.</div>
<div class='museum-legend'>{legend}</div>
"""
    return blueprint


def build_loading_html(title: str, body: str, step: int, total: int, next_hall: str) -> str:
    progress = max(8, min(100, int((step / total) * 100)))
    return f"""
<div class="loading-card">
    <div>
        <div class="loading-kicker">Museum in progress</div>
        <div class="loading-title">{esc(title)}</div>
        <div class="loading-copy">{esc(body)}</div>
    </div>
    <div>
        <div class="loading-track"><div class="loading-bar" style="width:{progress}%"></div></div>
        <div class="loading-meta">
            <span>Hall {step} of {total}</span>
            <span>Next stop: {esc(next_hall)}</span>
            <span class="loading-dots"><span></span><span></span><span></span></span>
        </div>
    </div>
</div>
"""


def build_theme_bar() -> str:
    return """
<div class="theme-bar">
    <div class="theme-bar-copy">
        Switch the museum atmosphere while you explore. Choose a warm retro gallery, a cooler night mode, or a bright archival reading room.
    </div>
    <div class="theme-chip-row">
        <button class="theme-chip is-active" type="button" data-theme-switch="retro">Retro</button>
        <button class="theme-chip" type="button" data-theme-switch="dark">Dark</button>
        <button class="theme-chip" type="button" data-theme-switch="light">White</button>
    </div>
</div>
"""


def build_panel_header(kicker: str, title: str, copy: str) -> str:
    return f"""
<div class="hall-panel-header">
    <div class="hall-panel-kicker">{esc(kicker)}</div>
    <div class="hall-panel-title">{esc(title)}</div>
    <div class="hall-panel-copy">{esc(copy)}</div>
</div>
"""


def build_hall_nav() -> str:
    buttons = "".join(
        f"""
<button class='museum-hall-nav-btn{' is-active' if room_id == 'lobby' else ''}' type='button' data-hall-target='{esc(room_id)}'>
    <div class='museum-hall-nav-index'>Hall {index:02d}</div>
    <div class='museum-hall-nav-title'>{esc(title)}</div>
    <div class='museum-hall-nav-copy'>{esc(kicker)}</div>
</button>
"""
        for index, (room_id, title, kicker, _copy) in enumerate(ROOMS, start=1)
    )
    return f"<div class='museum-hall-shell'><div class='museum-hall-nav'>{buttons}</div>"


def format_concept(concept: str, curator_mode: str) -> str:
    mode = CURATOR_MODES.get(curator_mode, CURATOR_MODES["Anthropology"])
    return (
        f"{concept}\n\n"
        f"Curatorial lens: {curator_mode}. "
        f"Prioritize this sensibility: {mode['tagline']}"
    )


def build_museum_state(concept: str, curator_mode: str, world_bible: dict, artifacts=None, timeline=None, newspaper=None, visitor_book=None) -> dict:
    return {
        "concept": concept,
        "curator_mode": curator_mode,
        "guided_concept": format_concept(concept, curator_mode),
        "world_bible": world_bible or {},
        "artifacts": artifacts or {},
        "featured_image": None,
        "timeline": timeline or {},
        "newspaper": newspaper or {},
        "visitor_book": visitor_book or {},
    }


def default_state() -> dict:
    return build_museum_state("", "Anthropology", {})


def generate_artifact_image_action(state: dict, artifact_index: int):
    curator_mode = (state or {}).get("curator_mode") or "Anthropology"
    return (
        build_status_panel("Image generation coming soon", "Artifact image generation is not enabled yet.", curator_mode),
        gr.update(value=build_artifacts_html({**((state or {}).get("artifacts") or {}), "featured_image": None})),
        state,
    )


def regenerate_hall(state: dict, hall: str):
    state = state or default_state()
    concept = (state.get("concept") or "").strip()
    curator_mode = state.get("curator_mode") or "Anthropology"
    world_bible = state.get("world_bible") or {}

    if not concept or not world_bible:
        return (
            build_status_panel("Open a museum first", "Generate a civilization before rerolling an individual hall.", curator_mode),
            gr.update(value=build_map_html("lobby", [])),
            gr.update(value=build_lobby_html(world_bible)),
            gr.update(value=build_artifacts_html({**(state.get("artifacts") or {}), "featured_image": state.get("featured_image")})),
            gr.update(value=build_timeline_html(state.get("timeline") or {})),
            gr.update(value=build_newspaper_html(state.get("newspaper") or {})),
            gr.update(value=build_visitor_book_html(state.get("visitor_book") or {})),
            state,
        )

    guided_concept = state.get("guided_concept") or format_concept(concept, curator_mode)

    if hall == "artifacts":
        artifacts = generate_artifacts(guided_concept, world_bible)
        state["artifacts"] = artifacts
        state["featured_image"] = None
        title = "Artifacts rerolled"
        subtitle = "The object gallery has been refreshed without changing the rest of the museum."
    elif hall == "timeline":
        timeline = generate_timeline(guided_concept, world_bible)
        state["timeline"] = timeline
        title = "Timeline rerolled"
        subtitle = "The history wall has been rebuilt while the civilization stays intact."
    elif hall == "newspaper":
        newspaper = generate_newspaper(guided_concept, world_bible)
        state["newspaper"] = newspaper
        title = "Newspaper rerolled"
        subtitle = "A new front page has been printed for the same civilization."
    elif hall == "visitor":
        visitor_book = generate_visitor_book(guided_concept, world_bible)
        state["visitor_book"] = visitor_book
        title = "Visitor's Book rerolled"
        subtitle = "A different personal voice has been added to the same world."
    else:
        title = "Unknown hall"
        subtitle = "No changes were made."

    return (
        build_status_panel(title, subtitle, curator_mode),
        gr.update(value=build_map_html(hall if hall in {"artifacts", "timeline", "newspaper", "visitor"} else "lobby", ["lobby", "artifacts", "timeline", "newspaper", "visitor"])),
            gr.update(value=build_lobby_html(world_bible)),
            gr.update(value=build_artifacts_html({**(state.get("artifacts") or {}), "featured_image": state.get("featured_image")})),
            gr.update(value=build_timeline_html(state.get("timeline") or {})),
            gr.update(value=build_newspaper_html(state.get("newspaper") or {})),
            gr.update(value=build_visitor_book_html(state.get("visitor_book") or {})),
        state,
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
            default_state(),
        )
        return

    waiting = "The curatorial staff is preparing this hall."
    guided_concept = format_concept(concept, curator_mode)
    yield (
        build_status_panel("Opening the museum", "We are drafting the world bible and preparing the first gallery.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("lobby", [])),
        gr.update(value="<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Preparing a new impossible civilization.</div>"),
        gr.update(value=build_loading_html("Drafting the world", "The museum is defining the main rule, social order, and daily life of this civilization.", 1, 5, "Artifacts")),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
        default_state(),
    )

    world_bible = generate_world_bible(guided_concept)
    header = museum_heading(world_bible)
    state = build_museum_state(concept, curator_mode, world_bible)

    yield (
        build_status_panel("Lobby opened", "The civilization has taken shape. The first records are now on display.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("artifacts", ["lobby"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_loading_html("Excavating the collection", "The museum is cataloguing objects from this civilization and selecting the first exhibit pieces.", 2, 5, "Timeline")),
        empty_gallery("Assembling the official historical record."),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
        state,
    )

    artifacts = generate_artifacts(guided_concept, world_bible)
    state["artifacts"] = artifacts
    state["featured_image"] = None
    yield (
        build_status_panel("Artifacts catalogued", "The collection vault has opened. The chronology is being assembled.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("timeline", ["lobby", "artifacts"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": None})),
        gr.update(value=build_loading_html("Restoring the timeline", "The archive is assembling the sequence of events that shaped this world.", 3, 5, "Newspaper")),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
        state,
    )

    timeline = generate_timeline(guided_concept, world_bible)
    state["timeline"] = timeline
    yield (
        build_status_panel("Timeline restored", "The museum now knows how this world rose, changed, and endured.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("newspaper", ["lobby", "artifacts", "timeline"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_loading_html("Printing the newspaper", "The press room is composing a front page from inside the civilization's own point of view.", 4, 5, "Visitor's Book")),
        empty_gallery("Opening the final testimony cabinet."),
        state,
    )

    newspaper = generate_newspaper(guided_concept, world_bible)
    state["newspaper"] = newspaper
    yield (
        build_status_panel("Presses running", "A surviving newspaper is now on display beside the official archive.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("visitor", ["lobby", "artifacts", "timeline", "newspaper"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        gr.update(value=build_loading_html("Opening the last page", "The museum is finding one private voice that lived inside this world.", 5, 5, "Final display")),
        state,
    )

    visitor_book = generate_visitor_book(guided_concept, world_bible)
    state["visitor_book"] = visitor_book
    yield (
        build_status_panel("Museum complete", "All five halls are open. The world is ready to be explored.", curator_mode),
        gr.update(value=build_hero_html(curator_mode)),
        gr.update(value=build_map_html("visitor", ["lobby", "artifacts", "timeline", "newspaper", "visitor"])),
        gr.update(value=header),
        gr.update(value=build_lobby_html(world_bible)),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        gr.update(value=build_visitor_book_html(visitor_book)),
        state,
    )


with gr.Blocks(css=CSS, head=APP_HEAD, title="Infinite Museum of Impossible Worlds") as demo:
    museum_state = gr.State(default_state())
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

    with gr.Row(elem_classes=["theme-wrap"]):
        gr.HTML(build_theme_bar())

    museum_header = gr.HTML(
        "<div class='museum-title'>Infinite Museum of Impossible Worlds</div><div class='museum-tagline'>Every idea creates a civilization. Every civilization leaves artifacts.</div>"
    )
    map_html = gr.HTML(build_map_html("lobby", []), elem_classes=["map-wrap"])

    with gr.Column(elem_classes=["museum-hall-stack"]):
        gr.HTML(build_hall_nav())
        with gr.Group(elem_classes=["museum-hall-panel", "is-active"], elem_id="hall-panel-lobby"):
            gr.HTML(build_panel_header("Hall 01", "Lobby", "Read the governing rule of the civilization, then use the floor plan to move deeper into the museum."))
            lobby_html = gr.HTML(
                value="<div class='empty-state'>The museum awaits its first impossible world.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Group(elem_classes=["museum-hall-panel"], elem_id="hall-panel-artifacts"):
            gr.HTML(build_panel_header("Hall 02", "Artifacts", "Move between the catalog view and on-demand renders without losing the rest of the exhibition."))
            with gr.Row(elem_classes=["hall-action-row"]):
                artifact_image_btn_1 = gr.Button("Render Artifact 1", size="sm", elem_classes=["museum-secondary-btn"])
                artifact_image_btn_2 = gr.Button("Render Artifact 2", size="sm", elem_classes=["museum-secondary-btn"])
                artifact_image_btn_3 = gr.Button("Render Artifact 3", size="sm", elem_classes=["museum-secondary-btn"])
            regen_artifacts_btn = gr.Button("Regenerate Artifacts", size="sm", elem_classes=["museum-action-btn"])
            artifacts_html = gr.HTML(
                value="<div class='empty-state'>The artifact hall is sealed.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Group(elem_classes=["museum-hall-panel"], elem_id="hall-panel-timeline"):
            gr.HTML(build_panel_header("Hall 03", "Timeline", "Follow the civilization in sequence, from founding logic to the events that distorted everyday life."))
            regen_timeline_btn = gr.Button("Regenerate Timeline", size="sm", elem_classes=["museum-action-btn"])
            timeline_html = gr.HTML(
                value="<div class='empty-state'>History has not yet been arranged.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Group(elem_classes=["museum-hall-panel"], elem_id="hall-panel-newspaper"):
            gr.HTML(build_panel_header("Hall 04", "Newspaper", "Read the world in its own public voice through a single surviving front page."))
            regen_newspaper_btn = gr.Button("Regenerate Newspaper", size="sm", elem_classes=["museum-action-btn"])
            newspaper_html = gr.HTML(
                value="<div class='empty-state'>No front page has gone to print.</div>",
                elem_classes=["hall-content"],
            )
        with gr.Group(elem_classes=["museum-hall-panel"], elem_id="hall-panel-visitor"):
            gr.HTML(build_panel_header("Hall 05", "Visitor's Book", "End with one human-scale testimony so the impossible world lands emotionally, not just structurally."))
            regen_visitor_btn = gr.Button("Regenerate Visitor's Book", size="sm", elem_classes=["museum-action-btn"])
            visitor_html = gr.HTML(
                value="<div class='empty-state'>No one has yet signed the visitor's book.</div>",
                elem_classes=["hall-content"],
            )
        gr.HTML("</div>")

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
        museum_state,
    ]

    curator_mode.change(
        fn=lambda mode: build_hero_html(mode),
        inputs=[curator_mode],
        outputs=[hero_html],
    )

    generate_btn.click(generate_museum, inputs=[concept_input, curator_mode], outputs=outputs)
    concept_input.submit(generate_museum, inputs=[concept_input, curator_mode], outputs=outputs)

    hall_outputs = [
        status_html,
        map_html,
        lobby_html,
        artifacts_html,
        timeline_html,
        newspaper_html,
        visitor_html,
        museum_state,
    ]

    regen_artifacts_btn.click(lambda state: regenerate_hall(state, "artifacts"), inputs=[museum_state], outputs=hall_outputs)
    regen_timeline_btn.click(lambda state: regenerate_hall(state, "timeline"), inputs=[museum_state], outputs=hall_outputs)
    regen_newspaper_btn.click(lambda state: regenerate_hall(state, "newspaper"), inputs=[museum_state], outputs=hall_outputs)
    regen_visitor_btn.click(lambda state: regenerate_hall(state, "visitor"), inputs=[museum_state], outputs=hall_outputs)

    artifact_image_outputs = [status_html, artifacts_html, museum_state]
    artifact_image_btn_1.click(lambda state: generate_artifact_image_action(state, 0), inputs=[museum_state], outputs=artifact_image_outputs)
    artifact_image_btn_2.click(lambda state: generate_artifact_image_action(state, 1), inputs=[museum_state], outputs=artifact_image_outputs)
    artifact_image_btn_3.click(lambda state: generate_artifact_image_action(state, 2), inputs=[museum_state], outputs=artifact_image_outputs)


if __name__ == "__main__":
    demo.launch()
