import html
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import gradio as gr

from generators.engine import (
    build_world_complexity_report,
    detect_curator_notes,
    generate_artifacts,
    generate_featured_artifact_image,
    generate_newspaper,
    generate_timeline,
    generate_visitor_book,
    generate_world_ambassador_reply,
    generate_world_bible,
    tag_artifacts,
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

  let walkToken = 0;
  let audioContext = null;
  let ambientGain = null;
  let ambientOscillator = null;
  let guideUtterance = null;

  function ensureAudioContext() {
    if (audioContext) return audioContext;
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return null;
    audioContext = new Context();
    return audioContext;
  }

  function startAmbientSound() {
    const context = ensureAudioContext();
    if (!context || ambientOscillator) return;
    ambientGain = context.createGain();
    ambientGain.gain.value = 0.008;
    ambientOscillator = context.createOscillator();
    ambientOscillator.type = "sine";
    ambientOscillator.frequency.value = 58;

    const filter = context.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 220;

    ambientOscillator.connect(filter);
    filter.connect(ambientGain);
    ambientGain.connect(context.destination);
    ambientOscillator.start();
  }

  function playFootstep() {
    const context = ensureAudioContext();
    if (!context) return;
    startAmbientSound();
    if (context.state === "suspended") {
      context.resume().catch(() => {});
    }

    const now = context.currentTime;
    const osc = context.createOscillator();
    const gain = context.createGain();
    const filter = context.createBiquadFilter();

    osc.type = "triangle";
    osc.frequency.setValueAtTime(110, now);
    osc.frequency.exponentialRampToValueAtTime(65, now + 0.12);

    filter.type = "lowpass";
    filter.frequency.setValueAtTime(420, now);

    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.016, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.16);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(context.destination);
    osc.start(now);
    osc.stop(now + 0.18);
  }

  function typeElement(node) {
    if (!node || node.dataset.typeDone === "true") return;
    const fullText = node.dataset.typeText || node.textContent || "";
    if (!fullText.trim()) {
      node.dataset.typeDone = "true";
      return;
    }

    node.dataset.typeDone = "typing";
    node.textContent = "";
    let index = 0;
    const cadence = Number(node.dataset.typeSpeed || 16);

    const tick = () => {
      if (!node.isConnected) return;
      index += 1;
      node.textContent = fullText.slice(0, index);
      if (index < fullText.length) {
        window.setTimeout(tick, cadence);
      } else {
        node.dataset.typeDone = "true";
      }
    };

    tick();
  }

  function runTypewriters(scope = document) {
    scope.querySelectorAll("[data-type-text]").forEach((node) => {
      if (!node.dataset.typeDone || node.dataset.typeDone === "typing") {
        typeElement(node);
      }
    });
  }

  function slugifyName(text) {
    return String(text || "museum-world")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-") || "museum-world";
  }

  function drawWrappedText(ctx, text, x, y, maxWidth, lineHeight, color, font, maxLines = 3) {
    ctx.fillStyle = color;
    ctx.font = font;
    const words = String(text || "").split(/\\s+/).filter(Boolean);
    const lines = [];
    let current = "";

    words.forEach((word) => {
      const probe = current ? `${current} ${word}` : word;
      if (ctx.measureText(probe).width <= maxWidth || !current) {
        current = probe;
      } else {
        lines.push(current);
        current = word;
      }
    });
    if (current) lines.push(current);

    const trimmed = lines.slice(0, maxLines);
    if (lines.length > maxLines && trimmed.length) {
      trimmed[trimmed.length - 1] = `${trimmed[trimmed.length - 1].replace(/[. ]+$/, "")}...`;
    }

    trimmed.forEach((line, index) => {
      ctx.fillText(line, x, y + (index * lineHeight));
    });
  }

  function hashString(text) {
    const value = String(text || "");
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return Math.abs(hash >>> 0);
  }

  function paletteFromSeed(seed) {
    const palettes = [
      { accent: "#c8a96e", glow: "rgba(200,169,110,0.16)", panel: "#231913", line: "rgba(200,169,110,0.38)" },
      { accent: "#d38a5a", glow: "rgba(211,138,90,0.16)", panel: "#27150f", line: "rgba(211,138,90,0.34)" },
      { accent: "#8bb7c2", glow: "rgba(139,183,194,0.16)", panel: "#122028", line: "rgba(139,183,194,0.32)" },
      { accent: "#b5a0d6", glow: "rgba(181,160,214,0.15)", panel: "#1d1726", line: "rgba(181,160,214,0.30)" },
      { accent: "#8fb98b", glow: "rgba(143,185,139,0.15)", panel: "#162218", line: "rgba(143,185,139,0.30)" },
    ];
    return palettes[seed % palettes.length];
  }

  function drawNoise(ctx, width, height, seed) {
    ctx.save();
    ctx.globalAlpha = 0.06;
    for (let i = 0; i < 180; i += 1) {
      const x = (seed * (i + 17) * 13) % width;
      const y = (seed * (i + 29) * 7) % height;
      const w = 40 + ((seed + i * 19) % 120);
      const h = 1 + ((seed + i * 11) % 3);
      ctx.fillStyle = i % 2 === 0 ? "rgba(255,255,255,0.22)" : "rgba(0,0,0,0.22)";
      ctx.fillRect(x, y, w, h);
    }
    ctx.restore();
  }

  function drawArtifactPanel(ctx, layout, payload, palette, seed) {
    const { x, y, w, h } = layout;
    ctx.save();
    ctx.fillStyle = palette.panel;
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = palette.line;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.strokeRect(x + 10, y + 10, w - 20, h - 20);

    const innerGlow = ctx.createRadialGradient(x + (w * 0.5), y + (h * 0.38), 18, x + (w * 0.5), y + (h * 0.38), w * 0.58);
    innerGlow.addColorStop(0, palette.glow);
    innerGlow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = innerGlow;
    ctx.fillRect(x, y, w, h);

    const variant = seed % 4;
    ctx.strokeStyle = palette.accent;
    ctx.fillStyle = palette.accent;
    ctx.lineWidth = 3;

    if (variant === 0) {
      ctx.beginPath();
      ctx.arc(x + (w * 0.5), y + (h * 0.38), Math.min(w, h) * 0.17, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillRect(x + (w * 0.43), y + (h * 0.54), w * 0.14, h * 0.16);
    } else if (variant === 1) {
      ctx.beginPath();
      ctx.moveTo(x + (w * 0.28), y + (h * 0.62));
      ctx.lineTo(x + (w * 0.5), y + (h * 0.2));
      ctx.lineTo(x + (w * 0.72), y + (h * 0.62));
      ctx.closePath();
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x + (w * 0.5), y + (h * 0.69), Math.min(w, h) * 0.08, 0, Math.PI * 2);
      ctx.fill();
    } else if (variant === 2) {
      for (let i = 0; i < 5; i += 1) {
        const yy = y + (h * (0.22 + (i * 0.11)));
        ctx.beginPath();
        ctx.moveTo(x + (w * 0.24), yy);
        ctx.bezierCurveTo(x + (w * 0.4), yy - 12, x + (w * 0.6), yy + 12, x + (w * 0.76), yy);
        ctx.stroke();
      }
    } else {
      ctx.fillRect(x + (w * 0.34), y + (h * 0.24), w * 0.32, h * 0.28);
      ctx.clearRect(x + (w * 0.42), y + (h * 0.32), w * 0.16, h * 0.12);
      ctx.strokeRect(x + (w * 0.29), y + (h * 0.57), w * 0.42, h * 0.09);
    }

    ctx.fillStyle = palette.accent;
    ctx.font = '600 12px "Cinzel", Georgia, serif';
    ctx.textAlign = "left";
    ctx.fillText("FEATURED RELIC", x + 24, y + h - 58);
    drawWrappedText(ctx, payload.artifact_name || payload.museum_name, x + 24, y + h - 28, w - 48, 24, "#f5efe3", '400 21px "Cormorant Garamond", Georgia, serif', 2);
    ctx.restore();
  }

  function exportShareCardFromPayload(payload) {
    if (!payload) return;

    const canvas = document.createElement("canvas");
    canvas.width = 1200;
    canvas.height = 630;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const seed = hashString([payload.museum_name, payload.premise, payload.visual_motif, payload.turning_point].join("|"));
    const palette = paletteFromSeed(seed);
    const bg = "#16110f";
    const gold = palette.accent;
    const paper = "#eadfc9";
    const white = "#f5efe3";
    const isWideArt = seed % 2 === 0;

    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const glow = ctx.createRadialGradient(600, 110, 40, 600, 110, 420);
    glow.addColorStop(0, palette.glow);
    glow.addColorStop(1, "rgba(200,169,110,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawNoise(ctx, canvas.width, canvas.height, seed);

    ctx.strokeStyle = "rgba(200,169,110,0.14)";
    ctx.lineWidth = 1;
    ctx.strokeRect(28, 28, 1144, 574);
    ctx.strokeRect(40, 40, 1120, 550);

    ctx.fillStyle = gold;
    ctx.font = '600 18px "Cinzel", Georgia, serif';
    ctx.textAlign = "center";
    ctx.fillText("INFINITE MUSEUM OF IMPOSSIBLE WORLDS", 600, 78);

    ctx.font = '600 54px "Cinzel", Georgia, serif';
    ctx.fillStyle = gold;
    ctx.fillText(String(payload.museum_name || "Infinite Museum"), 600, 142);

    ctx.font = 'italic 20px "Cormorant Garamond", Georgia, serif';
    ctx.fillStyle = paper;
    drawWrappedText(ctx, payload.tagline || "", 225, 182, 750, 28, paper, 'italic 20px "Cormorant Garamond", Georgia, serif', 2);

    const fields = [
      ["Premise", payload.premise],
      ["Government", payload.government],
      ["Artifact to Remember", payload.artifact_name],
      ["Turning Point", payload.turning_point],
      ["Absolute Taboo", payload.taboo],
      ["Visual Motif", payload.visual_motif],
    ];

    const artLayout = isWideArt
      ? { x: 70, y: 238, w: 360, h: 265 }
      : { x: 80, y: 252, w: 300, h: 235 };
    drawArtifactPanel(ctx, artLayout, payload, palette, seed);

    const startX = isWideArt ? 480 : 430;
    const startY = 274;
    const colWidth = 285;
    const rowHeight = 92;
    const colGap = 60;

    fields.forEach(([label, value], index) => {
      const col = index % 2;
      const row = Math.floor(index / 2);
      const x = startX + (col * (colWidth + colGap));
      const y = startY + (row * rowHeight);

      ctx.fillStyle = gold;
      ctx.font = '600 14px "Cinzel", Georgia, serif';
      ctx.textAlign = "left";
      ctx.fillText(label, x, y);
      ctx.fillStyle = palette.line;
      ctx.fillRect(x, y + 12, 56, 2);

      drawWrappedText(
        ctx,
        value || "-",
        x,
        y + 34,
        colWidth,
        22,
        white,
        '400 20px "Cormorant Garamond", Georgia, serif',
        3,
      );
    });

    ctx.strokeStyle = palette.line;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(70, 526);
    ctx.lineTo(1130, 526);
    ctx.stroke();

    ctx.fillStyle = "rgba(8,6,5,0.92)";
    ctx.fillRect(0, 570, 1200, 60);
    ctx.fillStyle = paper;
    ctx.font = '500 16px "Cormorant Garamond", Georgia, serif';
    ctx.textAlign = "left";
    const visitorLine = payload.visitor_name
      ? `Issued to ${payload.visitor_name}${payload.visitor_year ? ` • Arrived from ${payload.visitor_year}` : ""}`
      : "Curated by M. Vishnu Vardhan Reddy - Museum Manager";
    ctx.fillText(visitorLine, 42, 607);
    ctx.textAlign = "right";
    ctx.fillText("Build Small Hackathon 2026", 1158, 607);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = `${slugifyName(payload.museum_name)}.png`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "image/png");
  }

  function drawQrGlyph(ctx, x, y, size, seed, palette) {
    const cells = 11;
    const cell = size / cells;
    ctx.save();
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.fillRect(x, y, size, size);
    for (let row = 0; row < cells; row += 1) {
      for (let col = 0; col < cells; col += 1) {
        const value = ((seed + (row * 13) + (col * 29)) ^ (row * col * 7)) % 5;
        if (value === 0 || value === 2) {
          ctx.fillStyle = palette.accent;
          ctx.fillRect(x + (col * cell), y + (row * cell), cell - 1, cell - 1);
        }
      }
    }
    ctx.strokeStyle = palette.line;
    ctx.strokeRect(x, y, size, size);
    ctx.restore();
  }

  function renderTicketCanvas(payload) {
    const canvas = document.createElement("canvas");
    canvas.width = 1080;
    canvas.height = 620;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const seed = hashString([payload.ticket_number, payload.visitor_name, payload.visitor_year, payload.museum_name].join("|"));
    const palette = paletteFromSeed(seed);
    ctx.fillStyle = "#120d0a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const shimmer = ctx.createLinearGradient(120, 40, 900, 560);
    shimmer.addColorStop(0, "rgba(255,255,255,0.02)");
    shimmer.addColorStop(0.5, palette.glow);
    shimmer.addColorStop(1, "rgba(255,255,255,0.01)");
    ctx.fillStyle = shimmer;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawNoise(ctx, canvas.width, canvas.height, seed);

    ctx.fillStyle = "rgba(16,12,10,0.92)";
    ctx.fillRect(42, 42, 996, 536);
    ctx.strokeStyle = palette.line;
    ctx.lineWidth = 2;
    ctx.strokeRect(42, 42, 996, 536);
    ctx.strokeRect(58, 58, 964, 504);

    ctx.fillStyle = palette.accent;
    ctx.font = '600 16px "Cinzel", Georgia, serif';
    ctx.textAlign = "left";
    ctx.fillText("INFINITE MUSEUM OF IMPOSSIBLE WORLDS", 86, 96);
    ctx.textAlign = "right";
    ctx.fillText(payload.ticket_number || "IM-0000", 990, 96);

    ctx.fillStyle = "#f5efe3";
    ctx.font = '600 56px "Cinzel", Georgia, serif';
    ctx.textAlign = "left";
    ctx.fillText(`ADMIT ONE: ${String(payload.visitor_name || "VISITOR").toUpperCase()}`, 86, 170);

    ctx.font = 'italic 28px "Cormorant Garamond", Georgia, serif';
    ctx.fillStyle = "#eadfc9";
    ctx.fillText(`Traveller from the Year ${payload.visitor_year || "Unknown"}`, 88, 214);

    ctx.font = '500 22px "Cormorant Garamond", Georgia, serif';
    ctx.fillStyle = palette.accent;
    ctx.fillText(payload.visitor_title || "Explorer of Impossible Worlds", 88, 258);

    ctx.strokeStyle = palette.line;
    ctx.beginPath();
    ctx.moveTo(86, 282);
    ctx.lineTo(990, 282);
    ctx.stroke();

    const labels = [
      ["Museum", payload.museum_name || "Infinite Museum"],
      ["Visit Date", payload.visit_date || ""],
      ["Access", "Granted to the World of Imagination"],
      ["Complexity", `${payload.complexity_score || "--"} ${payload.complexity_band || ""}`.trim() || "--"],
    ];

    labels.forEach(([label, value], index) => {
      const y = 334 + (index * 58);
      ctx.fillStyle = palette.accent;
      ctx.font = '600 14px "Cinzel", Georgia, serif';
      ctx.fillText(label, 88, y);
      ctx.fillStyle = "#f5efe3";
      ctx.font = '400 24px "Cormorant Garamond", Georgia, serif';
      ctx.fillText(value, 88, y + 28);
    });

    drawQrGlyph(ctx, 790, 330, 180, seed, palette);
    ctx.fillStyle = "#eadfc9";
    ctx.font = '500 16px "Cormorant Garamond", Georgia, serif';
    ctx.textAlign = "center";
    ctx.fillText("Museum Passage Seal", 880, 536);

    return canvas;
  }

  function downloadTicketFromPayload(payload) {
    const canvas = renderTicketCanvas(payload);
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (!blob) return;
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = `${slugifyName(payload.visitor_name || payload.museum_name || "museum-ticket")}-ticket.png`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, "image/png");
  }

  async function shareTicketFromPayload(payload) {
    const canvas = renderTicketCanvas(payload);
    if (!canvas) return;
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], `${slugifyName(payload.visitor_name || payload.museum_name || "museum-ticket")}-ticket.png`, { type: "image/png" });
      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({
            title: payload.museum_name || "Infinite Museum Ticket",
            text: `I just opened ${payload.museum_name || "an impossible museum world"} as ${payload.visitor_name || "a visitor"}.`,
            files: [file],
          });
          return;
        } catch (_error) {}
      }
      downloadTicketFromPayload(payload);
    }, "image/png");
  }

  function retriggerTypewriters(scope) {
    if (!scope) return;
    scope.querySelectorAll("[data-type-text]").forEach((node) => {
      node.dataset.typeDone = "";
      node.textContent = "";
    });
    runTypewriters(scope);
  }

  function marker() {
    return null;
  }

  function caption() {
    return document.getElementById("museum-visitor-caption");
  }

  function activeScene() {
    const stage = document.querySelector(".museum-room-stage");
    if (!stage) return null;
    const roomId = stage.getAttribute("data-active-room") || "lobby";
    return stage.querySelector(`.museum-room-scene--${roomId}`);
  }

  function setGuideStatus(text) {
    const node = document.getElementById("museum-audio-status");
    if (node) node.textContent = text;
  }

  function stopGuide() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    guideUtterance = null;
    document.body.classList.remove("is-guide-speaking");
    const panel = document.querySelector(".museum-audio-guide");
    if (panel) panel.classList.remove("is-speaking");
    setGuideStatus("Guide paused");
  }

  function syncAudioGuide() {
    const scene = activeScene();
    const title = scene?.getAttribute("data-guide-title") || "Curator audio guide";
    const copy = scene?.getAttribute("data-guide-copy") || "Move into a hall to hear the guide speak about the current world.";
    const hall = scene?.getAttribute("data-guide-room") || "Lobby";
    const titleNode = document.getElementById("museum-audio-title");
    const copyNode = document.getElementById("museum-audio-copy");
    const hallNode = document.getElementById("museum-audio-hall");
    if (titleNode) titleNode.textContent = title;
    if (copyNode) copyNode.textContent = copy;
    if (hallNode) hallNode.textContent = hall;
    if (!document.body.classList.contains("is-guide-speaking")) {
      setGuideStatus(`Ready for ${hall}`);
    }
  }

  function playGuide() {
    const scene = activeScene();
    if (!scene) return;
    const text = scene.getAttribute("data-guide-copy") || "";
    const title = scene.getAttribute("data-guide-title") || "Curator guide";
    const hall = scene.getAttribute("data-guide-room") || "Lobby";
    const panel = document.querySelector(".museum-audio-guide");

    if (!("speechSynthesis" in window)) {
      setGuideStatus("Speech not available in this browser");
      return;
    }

    stopGuide();
    playFootstep();

    guideUtterance = new SpeechSynthesisUtterance(`${title}. ${text}`);
    guideUtterance.rate = 0.95;
    guideUtterance.pitch = 0.95;
    guideUtterance.onstart = () => {
      document.body.classList.add("is-guide-speaking");
      if (panel) panel.classList.add("is-speaking");
      setGuideStatus(`Now guiding ${hall}`);
    };
    guideUtterance.onend = () => {
      document.body.classList.remove("is-guide-speaking");
      if (panel) panel.classList.remove("is-speaking");
      setGuideStatus(`Finished ${hall}`);
      guideUtterance = null;
    };
    guideUtterance.onerror = () => {
      document.body.classList.remove("is-guide-speaking");
      if (panel) panel.classList.remove("is-speaking");
      setGuideStatus("Guide unavailable");
      guideUtterance = null;
    };
    window.speechSynthesis.speak(guideUtterance);
  }

  function currentMap() {
    return document.querySelector(".museum-map");
  }

  function setVisitorPosition(point) {
    return;
  }

  function setVisitorCaption(text) {
    const node = caption();
    if (node) node.textContent = text;
  }

  function setDoorTarget(roomId) {
    return;
  }

  function pathForRoom(roomId) {
    return [];
  }

  function setActiveHall(roomId, scrollIntoView = true) {
    document.documentElement.style.setProperty("--active-room-shift", roomId);
    document.querySelectorAll(".museum-hall-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.id === `hall-panel-${roomId}`);
    });
    document.querySelectorAll(".museum-hall-nav-btn").forEach((button) => {
      button.classList.toggle("is-active", button.getAttribute("data-hall-target") === roomId);
    });
    const stage = document.querySelector(".museum-room-stage");
    if (stage) {
      stage.classList.remove("is-transitioning");
      void stage.offsetWidth;
      stage.classList.add("is-transitioning");
      stage.setAttribute("data-active-room", roomId);
      const activeScene = stage.querySelector(`.museum-room-scene--${roomId}`);
      retriggerTypewriters(activeScene);
      window.setTimeout(() => {
        if (stage.getAttribute("data-active-room") === roomId) {
          stage.classList.remove("is-transitioning");
        }
      }, 760);
    }
    const activePanel = document.getElementById(`hall-panel-${roomId}`);
    retriggerTypewriters(activePanel);
    syncAudioGuide();
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
    setVisitorCaption(`Currently in ${ROOM_LABELS[roomId] || "Lobby"}`);
  }

  function positionFromActiveRoom() {
    const map = currentMap();
    if (!map) return;
    const roomId = map.getAttribute("data-active-room") || "lobby";
    setVisitorCaption(`Currently in ${ROOM_LABELS[roomId] || "Lobby"}`);
  }

  window.museumNavigate = function museumNavigate(room) {
    if (!room) return false;
    const roomId = room.getAttribute("data-room-id");
    playFootstep();
    setVisitorCaption(`Currently in ${ROOM_LABELS[roomId] || "hall"}`);
    const map = currentMap();
    if (map) {
      map.setAttribute("data-active-room", roomId);
    }
    setActiveHall(roomId, true);
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

  function syncWorldAura() {
    const source = document.querySelector("[data-world-aura-source]");
    document.body.setAttribute("data-world-aura", source?.getAttribute("data-world-aura-source") || "default");
  }

  function resolveVoiceField(selector) {
    const root = document.querySelector(selector);
    if (!root) return null;
    if (root.matches("textarea, input")) return root;
    return root.querySelector("textarea, input");
  }

  function startVoiceIntake(selector, button) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const field = resolveVoiceField(selector);
    if (!SpeechRecognition || !field) return;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    button.classList.add("is-listening");
    button.textContent = "Listening...";
    recognition.onresult = (event) => {
      const transcript = event?.results?.[0]?.[0]?.transcript?.trim();
      if (!transcript) return;
      const spacer = field.value && !String(field.value).endsWith(" ") ? " " : "";
      field.value = `${field.value || ""}${spacer}${transcript}`.trim();
      field.dispatchEvent(new Event("input", { bubbles: true }));
      field.dispatchEvent(new Event("change", { bubbles: true }));
    };
    recognition.onend = () => {
      button.classList.remove("is-listening");
      button.textContent = button.getAttribute("data-voice-label") || "Speak";
    };
    recognition.onerror = () => {
      button.classList.remove("is-listening");
      button.textContent = "Voice unavailable";
      window.setTimeout(() => {
        button.textContent = button.getAttribute("data-voice-label") || "Speak";
      }, 1800);
    };
    recognition.start();
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

    const shareButton = event.target.closest("[data-share-world]");
    if (shareButton) {
      event.preventDefault();
      const raw = shareButton.getAttribute("data-share-payload");
      if (!raw) return;
      try {
        exportShareCardFromPayload(JSON.parse(raw));
      } catch (_error) {}
      return;
    }

    const shareTicketButton = event.target.closest("[data-share-ticket]");
    if (shareTicketButton) {
      event.preventDefault();
      const raw = shareTicketButton.getAttribute("data-ticket-payload");
      if (!raw) return;
      try {
        shareTicketFromPayload(JSON.parse(raw));
      } catch (_error) {}
      return;
    }

    const downloadTicketButton = event.target.closest("[data-download-ticket]");
    if (downloadTicketButton) {
      event.preventDefault();
      const raw = downloadTicketButton.getAttribute("data-ticket-payload");
      if (!raw) return;
      try {
        downloadTicketFromPayload(JSON.parse(raw));
      } catch (_error) {}
      return;
    }

    const beginJourneyButton = event.target.closest("#begin-journey-btn");
    if (beginJourneyButton) {
      document.body.classList.add("is-beginning-journey");
      window.setTimeout(() => document.body.classList.remove("is-beginning-journey"), 1400);
    }

    const voiceButton = event.target.closest("[data-voice-target]");
    if (voiceButton) {
      event.preventDefault();
      startVoiceIntake(voiceButton.getAttribute("data-voice-target"), voiceButton);
      return;
    }

    const audioPlay = event.target.closest("[data-audio-guide-toggle]");
    if (audioPlay) {
      event.preventDefault();
      playGuide();
      return;
    }

    const audioStop = event.target.closest("[data-audio-guide-stop]");
    if (audioStop) {
      event.preventDefault();
      stopGuide();
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
    const conceptVoice = document.getElementById("concept-voice-btn");
    if (conceptVoice) {
      conceptVoice.setAttribute("data-voice-target", "#concept-input");
      conceptVoice.setAttribute("data-voice-label", "Speak World Idea");
    }
    const ambassadorVoice = document.getElementById("ambassador-voice-btn");
    if (ambassadorVoice) {
      ambassadorVoice.setAttribute("data-voice-target", "#ambassador-input");
      ambassadorVoice.setAttribute("data-voice-label", "Speak Question");
    }
    syncWorldAura();
    positionFromActiveRoom();
    window.setTimeout(positionFromActiveRoom, 250);
    window.setTimeout(positionFromActiveRoom, 900);
    window.setTimeout(syncMapToSelectedTab, 500);
    window.setTimeout(syncAudioGuide, 520);
    runTypewriters(document);
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches?.("[data-type-text]")) {
          typeElement(node);
        } else {
          runTypewriters(node);
        }
        syncWorldAura();
        syncAudioGuide();
      });
    }
  });

  observer.observe(document.documentElement, { childList: true, subtree: true });

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
    --panel-strong: rgba(12, 9, 7, 0.86);
    --line: rgba(255, 255, 255, 0.05);
    --gold: #c8a96e;
    --gold-soft: #8a7248;
    --paper: #eadfc9;
    --muted: #94846b;
    --ink: #241a12;
    --shadow: rgba(0, 0, 0, 0.35);
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

.landing-wrap {
    width: min(100%, 1540px);
    margin: 24px auto 0;
    min-height: calc(100vh - 56px);
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.landing-shell {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 30px;
    background:
        radial-gradient(circle at 12% 16%, rgba(200, 169, 110, 0.14), transparent 22%),
        radial-gradient(circle at 86% 12%, rgba(200, 169, 110, 0.08), transparent 20%),
        linear-gradient(135deg, color-mix(in srgb, var(--panel-strong) 92%, black), var(--panel));
    box-shadow: 0 24px 60px var(--shadow);
    min-height: 720px;
}

.admission-welcome {
    position: relative;
    overflow: hidden;
    margin-bottom: 22px;
    padding: 32px 32px 28px;
    border-radius: 26px;
    border: 1px solid rgba(200, 169, 110, 0.2);
    background:
        radial-gradient(circle at 18% 18%, rgba(200, 169, 110, 0.18), transparent 24%),
        linear-gradient(135deg, rgba(19, 13, 11, 0.96), rgba(12, 8, 7, 0.94));
    box-shadow: 0 20px 44px rgba(0, 0, 0, 0.22);
    backdrop-filter: blur(14px);
    animation: landingCardReveal 0.78s ease both;
}

.admission-welcome::after {
    content: "";
    position: absolute;
    inset: 14px;
    border: 1px solid rgba(255, 234, 198, 0.08);
    border-radius: 18px;
    pointer-events: none;
}

.admission-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.admission-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: clamp(28px, 4vw, 44px);
    line-height: 1.04;
    max-width: 12ch;
    margin-bottom: 12px;
}

.admission-copy {
    color: var(--muted);
    font-size: 18px;
    line-height: 1.72;
    max-width: 56ch;
}

.admission-rail {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 18px;
}

.admission-chip {
    padding: 9px 14px;
    border-radius: 999px;
    border: 1px solid rgba(200, 169, 110, 0.18);
    background: rgba(255, 255, 255, 0.03);
    color: var(--paper);
    font-size: 13px;
}

.landing-shell::before {
    content: "";
    position: absolute;
    inset: 18px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 22px;
    pointer-events: none;
}

.landing-shell::after {
    content: "";
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 20% 24%, rgba(255,255,255,0.08), transparent 12%),
        radial-gradient(circle at 74% 18%, rgba(197, 143, 255, 0.14), transparent 14%),
        radial-gradient(circle at 82% 54%, rgba(255, 220, 161, 0.14), transparent 15%);
    animation: museumMotes 12s linear infinite;
    pointer-events: none;
}

.landing-grid {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    gap: 26px;
    padding: 34px;
    align-items: stretch;
}

.landing-copy {
    padding: 10px 6px 10px 4px;
}

.landing-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 11px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    margin-bottom: 18px;
}

.landing-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 58px;
    line-height: 1.04;
    max-width: 11ch;
    text-wrap: balance;
}

.landing-subtitle {
    margin-top: 16px;
    color: var(--gold);
    font-size: 22px;
    line-height: 1.45;
    max-width: 28ch;
}

.landing-lead {
    margin-top: 20px;
    color: var(--muted);
    font-size: 19px;
    line-height: 1.8;
    max-width: 34em;
}

.landing-plaque-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 24px;
}

.landing-plaque {
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-radius: 16px;
    padding: 14px 14px 12px;
    background: rgba(255, 255, 255, 0.03);
}

.landing-plaque-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.landing-plaque-value {
    color: var(--paper);
    font-size: 16px;
    line-height: 1.45;
}

.landing-cta-copy {
    margin-top: 24px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
    max-width: 38em;
}

.landing-floating-fragments {
    position: absolute;
    inset: 0;
    pointer-events: none;
}

.landing-floating-fragments span {
    position: absolute;
    width: 76px;
    height: 96px;
    border-radius: 18px;
    border: 1px solid rgba(255, 232, 196, 0.12);
    background:
        linear-gradient(145deg, rgba(255,255,255,0.05), rgba(200,169,110,0.02)),
        rgba(22, 16, 13, 0.28);
    box-shadow: 0 16px 34px rgba(0, 0, 0, 0.16);
    backdrop-filter: blur(8px);
}

.landing-floating-fragments span:nth-child(1) {
    left: 7%;
    top: 14%;
    transform: rotate(-14deg);
    animation: fragmentFloat 9s ease-in-out infinite;
}

.landing-floating-fragments span:nth-child(2) {
    right: 10%;
    top: 12%;
    transform: rotate(11deg);
    animation: fragmentFloat 10s ease-in-out infinite -2s;
}

.landing-floating-fragments span:nth-child(3) {
    right: 14%;
    bottom: 14%;
    transform: rotate(-9deg);
    animation: fragmentFloat 8.6s ease-in-out infinite -3.2s;
}

.landing-art {
    position: relative;
    min-height: 680px;
    border-radius: 24px;
    overflow: hidden;
    border: 1px solid rgba(200, 169, 110, 0.14);
    background:
        radial-gradient(circle at 50% 24%, rgba(245, 228, 191, 0.32), transparent 16%),
        radial-gradient(circle at 50% 16%, rgba(200, 169, 110, 0.22), transparent 28%),
        linear-gradient(180deg, rgba(10, 8, 7, 0.22), rgba(10, 8, 7, 0.66)),
        linear-gradient(180deg, color-mix(in srgb, var(--panel-light) 10%, transparent), color-mix(in srgb, var(--panel-strong) 92%, black));
    animation: landingStageFloat 9s ease-in-out infinite;
}

.landing-art::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        linear-gradient(90deg, transparent 0, transparent 44%, rgba(255, 255, 255, 0.05) 50%, transparent 56%, transparent 100%);
    opacity: 0.4;
}

.landing-skyline {
    position: absolute;
    inset: auto 0 0;
    height: 64%;
    background:
        linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.08) 18%, rgba(0, 0, 0, 0.34) 100%);
    animation: skylineDrift 18s ease-in-out infinite;
}

.landing-dome {
    position: absolute;
    left: 50%;
    bottom: 17%;
    width: 56%;
    aspect-ratio: 1.18 / 1;
    transform: translateX(-50%);
    border-radius: 50% 50% 0 0;
    background:
        radial-gradient(circle at 50% 20%, rgba(249, 236, 203, 0.42), transparent 24%),
        linear-gradient(180deg, rgba(232, 211, 165, 0.24), rgba(61, 45, 27, 0.76));
    border: 1px solid rgba(223, 198, 150, 0.18);
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
    animation: domePulse 7s ease-in-out infinite;
}

.landing-dome::before {
    content: "";
    position: absolute;
    inset: 16% 14% auto;
    height: 54%;
    border-radius: 50% 50% 0 0;
    border: 1px solid rgba(255, 244, 218, 0.16);
}

.landing-steps {
    position: absolute;
    left: 50%;
    bottom: 8%;
    width: 82%;
    height: 26%;
    transform: translateX(-50%);
    background:
        linear-gradient(180deg, rgba(243, 230, 200, 0.1), rgba(36, 26, 18, 0.82));
    clip-path: polygon(12% 100%, 20% 74%, 31% 74%, 37% 50%, 63% 50%, 69% 74%, 80% 74%, 88% 100%);
    animation: stepsGlow 6s ease-in-out infinite;
}

.landing-pillars {
    position: absolute;
    inset: auto 19% 13%;
    height: 38%;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
}

.landing-pillars span {
    border-radius: 999px 999px 6px 6px;
    background: linear-gradient(180deg, rgba(245, 229, 194, 0.24), rgba(45, 32, 18, 0.88));
    border: 1px solid rgba(245, 229, 194, 0.12);
}

.landing-pillars span:nth-child(odd) {
    animation: pillarRise 8s ease-in-out infinite;
}

.landing-pillars span:nth-child(even) {
    animation: pillarRise 8s ease-in-out infinite -2.4s;
}

.landing-caption {
    position: absolute;
    left: 24px;
    right: 24px;
    bottom: 22px;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    color: rgba(248, 240, 223, 0.82);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.museum-topbar {
    width: min(100%, 1540px);
    margin: 18px auto 0;
    padding: 0 24px;
    display: flex;
    justify-content: flex-start;
}

.museum-topbar .museum-secondary-btn {
    min-width: 180px;
}

body[data-museum-theme="retro"], body[data-museum-theme="retro"] .gradio-container {
    background:
        radial-gradient(circle at 12% 18%, rgba(200, 169, 110, 0.11), transparent 22%),
        radial-gradient(circle at 80% 6%, rgba(107, 63, 31, 0.2), transparent 18%),
        radial-gradient(circle at top, rgba(80, 57, 27, 0.18), transparent 34%),
        linear-gradient(180deg, #090706 0%, var(--bg) 30%, #120d0a 100%) !important;
}

body[data-museum-theme="dark"], body[data-museum-theme="dark"] .gradio-container {
    background:
        radial-gradient(circle at 14% 12%, rgba(79, 183, 187, 0.16), transparent 20%),
        radial-gradient(circle at 84% 10%, rgba(14, 92, 116, 0.22), transparent 18%),
        linear-gradient(180deg, #03070c 0%, var(--bg) 42%, #08131a 100%) !important;
}

body[data-museum-theme="light"], body[data-museum-theme="light"] .gradio-container {
    background:
        radial-gradient(circle at 12% 10%, rgba(95, 141, 156, 0.11), transparent 18%),
        radial-gradient(circle at 88% 8%, rgba(190, 165, 132, 0.14), transparent 16%),
        linear-gradient(180deg, #fcfbf8 0%, var(--bg) 44%, #eef3f3 100%) !important;
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
    --panel-strong: rgba(12, 9, 7, 0.86);
    --line: rgba(200, 169, 110, 0.22);
    --gold: #c8a96e;
    --gold-soft: #8a7248;
    --paper: #eadfc9;
    --muted: #94846b;
    --ink: #241a12;
    --shadow: rgba(0, 0, 0, 0.35);
}

body[data-museum-theme="dark"] {
    --bg: #071119;
    --bg-deep: #03070c;
    --bg-wash: #103246;
    --panel: rgba(7, 18, 28, 0.94);
    --panel-light: rgba(227, 244, 248, 0.97);
    --panel-strong: rgba(8, 16, 24, 0.9);
    --line: rgba(255, 255, 255, 0.06);
    --gold: #8be6d8;
    --gold-soft: #4fb7bb;
    --paper: #ebfbff;
    --muted: #92b7c4;
    --ink: #102028;
    --shadow: rgba(0, 8, 14, 0.42);
}

body[data-museum-theme="light"] {
    --bg: #f7f4ee;
    --bg-deep: #efe9de;
    --bg-wash: #d9e3e6;
    --panel: rgba(255, 252, 247, 0.97);
    --panel-light: rgba(255, 255, 252, 0.99);
    --panel-strong: rgba(250, 245, 237, 0.98);
    --line: rgba(24, 36, 43, 0.08);
    --gold: #365c6b;
    --gold-soft: #6a4f39;
    --paper: #18242b;
    --muted: #51646d;
    --ink: #18242b;
    --shadow: rgba(65, 82, 90, 0.12);
}

body[data-world-aura="ember"] .gradio-container {
    background:
        radial-gradient(circle at 22% 18%, rgba(211, 138, 90, 0.18), transparent 24%),
        radial-gradient(circle at 86% 10%, rgba(113, 42, 26, 0.16), transparent 20%),
        linear-gradient(180deg, #100807 0%, var(--bg) 38%, #1a0e0a 100%) !important;
}

body[data-world-aura="tide"] .gradio-container {
    background:
        radial-gradient(circle at 18% 14%, rgba(94, 160, 182, 0.18), transparent 22%),
        radial-gradient(circle at 78% 10%, rgba(54, 108, 136, 0.14), transparent 20%),
        linear-gradient(180deg, #071218 0%, var(--bg) 38%, #0b1d28 100%) !important;
}

body[data-world-aura="verdant"] .gradio-container {
    background:
        radial-gradient(circle at 18% 16%, rgba(112, 156, 102, 0.18), transparent 24%),
        radial-gradient(circle at 82% 10%, rgba(54, 92, 60, 0.14), transparent 20%),
        linear-gradient(180deg, #07100b 0%, var(--bg) 38%, #101912 100%) !important;
}

body[data-world-aura="velvet"] .gradio-container {
    background:
        radial-gradient(circle at 18% 16%, rgba(126, 96, 155, 0.18), transparent 24%),
        radial-gradient(circle at 82% 10%, rgba(66, 42, 92, 0.14), transparent 20%),
        linear-gradient(180deg, #0b0811 0%, var(--bg) 38%, #171021 100%) !important;
}

.museum-shell {
    border: 1px solid var(--line);
    margin: 20px auto;
    background: var(--panel-strong);
    box-shadow: 0 10px 40px var(--shadow);
    overflow: hidden;
    width: min(100%, 1540px);
}

.museum-workspace {
    width: min(100%, 1540px);
    margin: 0 auto;
    padding: 0 24px 18px;
    display: grid;
    grid-template-columns: 250px minmax(0, 1fr);
    gap: 26px;
    align-items: start;
}

.museum-sidebar {
    position: sticky;
    top: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.museum-canvas {
    min-width: 0;
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
        var(--panel);
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
    color: var(--paper);
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

.museum-visitor-pass {
    margin-top: 10px;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.5;
}

.museum-lead {
    margin-top: 18px;
    color: var(--muted);
    font-size: 18px;
    line-height: 1.8;
    max-width: 680px;
}

.museum-header-band {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 6px 0 16px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 18px;
    animation: museumHeaderDrift 6.5s ease-in-out infinite;
}

.museum-header-identity {
    display: flex;
    align-items: center;
    gap: 16px;
}

.museum-world-emblem {
    width: 58px;
    height: 58px;
    border-radius: 16px;
    border: 1px solid rgba(200, 169, 110, 0.24);
    display: grid;
    place-items: center;
    background:
        radial-gradient(circle at 30% 30%, rgba(255,255,255,0.08), transparent 44%),
        rgba(255,255,255,0.02);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    animation: museumSealFloat 5.8s ease-in-out infinite;
}

.museum-world-emblem svg {
    width: 38px;
    height: 38px;
}

.museum-world-emblem path,
.museum-world-emblem circle,
.museum-world-emblem line,
.museum-world-emblem polygon {
    stroke: var(--gold);
    fill: none;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.museum-header-share[hidden] {
    display: none !important;
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
    padding: 12px 24px 6px;
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

.concept-chip-row {
    width: min(100%, 1540px);
    margin: -2px auto 14px;
    padding: 0 24px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.concept-chip-btn {
    min-height: 42px !important;
    padding: 0 16px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(200, 169, 110, 0.26) !important;
    background: rgba(18, 13, 11, 0.72) !important;
    color: var(--paper) !important;
    font-size: 13px !important;
    line-height: 1.2 !important;
    transition: transform 0.22s ease, border-color 0.22s ease, background 0.22s ease, box-shadow 0.22s ease !important;
}

.concept-chip-btn:hover {
    border-color: rgba(200, 169, 110, 0.58) !important;
    background: rgba(200, 169, 110, 0.12) !important;
    transform: translateY(-2px);
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.16);
}

.control-shell {
    padding: 0 24px 24px;
    margin-top: 18px;
    position: relative;
    z-index: 3;
}

.theme-wrap {
    padding: 0 0 14px;
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
        var(--panel);
}

.theme-bar-copy {
    display: none;
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
    transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.theme-chip:hover,
.theme-chip.is-active {
    transform: translateY(-1px);
    border-color: rgba(200, 169, 110, 0.55);
    background: rgba(200, 169, 110, 0.14);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
}

.control-card {
    position: relative;
    max-width: 1180px;
    margin: 0 auto;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 28px;
    padding: 28px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.12), transparent 24%),
        linear-gradient(135deg, rgba(17, 13, 11, 0.62), rgba(11, 9, 8, 0.78));
    backdrop-filter: blur(18px);
    box-shadow: 0 26px 66px rgba(0, 0, 0, 0.28);
    animation: landingCardReveal 0.82s ease both;
}

.admission-card-grid {
    align-items: start;
    gap: 20px;
}

.admission-card-copy {
    margin-bottom: 16px;
}

.admission-form-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.admission-input .wrap,
.admission-input textarea,
.admission-input input {
    border-radius: 18px !important;
}

.admission-input textarea,
.admission-input input {
    min-height: 64px !important;
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(200, 169, 110, 0.34) !important;
    color: var(--paper) !important;
    font-size: 18px !important;
    padding: 16px 18px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 12px 30px rgba(0, 0, 0, 0.12);
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
}

.admission-input textarea:focus,
.admission-input input:focus {
    border-color: rgba(200,169,110,0.58) !important;
    box-shadow: 0 0 0 1px rgba(200,169,110,0.18), 0 0 26px rgba(200,169,110,0.12) !important;
    transform: translateY(-1px);
}

.admission-input label span {
    color: var(--paper) !important;
    font-size: 18px !important;
    margin-bottom: 8px !important;
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
    background: linear-gradient(180deg, color-mix(in srgb, var(--gold) 28%, var(--panel-strong)), var(--panel-strong)) !important;
    color: var(--gold) !important;
    border: 1px solid rgba(200, 169, 110, 0.45) !important;
    border-radius: 18px !important;
    font-family: 'Cinzel', serif !important;
    font-size: 14px !important;
    letter-spacing: 0.12em !important;
    text-transform: none !important;
    box-shadow:
        inset 0 1px 0 rgba(200, 169, 110, 0.1),
        0 14px 30px rgba(0, 0, 0, 0.24);
    transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
}

.enter-btn:hover {
    border-color: rgba(200, 169, 110, 0.8) !important;
    background: linear-gradient(180deg, color-mix(in srgb, var(--gold) 38%, var(--panel-strong)), var(--panel-strong)) !important;
    transform: translateY(-1px);
    box-shadow:
        inset 0 1px 0 rgba(200, 169, 110, 0.12),
        0 18px 36px rgba(0, 0, 0, 0.28);
}

.museum-ticket-preview {
    position: relative;
    overflow: hidden;
    border-radius: 26px;
    border: 1px solid rgba(200,169,110,0.18);
    background:
        linear-gradient(135deg, rgba(21, 15, 12, 0.96), rgba(10, 8, 7, 0.94));
    min-height: 100%;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}

.museum-ticket-preview::before {
    content: "";
    position: absolute;
    inset: 14px;
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 18px;
    pointer-events: none;
}

.museum-ticket-body {
    padding: 28px 28px 22px;
}

.museum-ticket-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    margin-bottom: 14px;
}

.museum-ticket-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 34px;
    line-height: 1.06;
    margin-bottom: 10px;
}

.museum-ticket-subtitle {
    color: var(--paper);
    font-size: 19px;
    line-height: 1.55;
    font-style: italic;
    margin-bottom: 18px;
}

.museum-ticket-meta {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 18px;
}

.museum-ticket-stat {
    border-radius: 16px;
    border: 1px solid rgba(200,169,110,0.14);
    background: rgba(255,255,255,0.03);
    padding: 12px 14px;
}

.museum-ticket-stat-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.museum-ticket-stat-value {
    color: var(--paper);
    font-size: 18px;
    line-height: 1.45;
}

.museum-ticket-qr {
    width: 116px;
    height: 116px;
    border-radius: 18px;
    border: 1px solid rgba(200,169,110,0.16);
    background:
        linear-gradient(90deg, rgba(255,255,255,0.06) 8%, transparent 8% 16%, rgba(255,255,255,0.03) 16% 24%, transparent 24%),
        linear-gradient(rgba(255,255,255,0.06) 8%, transparent 8% 16%, rgba(255,255,255,0.03) 16% 24%, transparent 24%),
        rgba(13, 10, 8, 0.8);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}

.museum-ticket-footer {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
}

.museum-ticket-copy {
    color: var(--muted);
    font-size: 17px;
    line-height: 1.6;
    max-width: 20ch;
}

.museum-ticket-ribbon {
    margin-top: 12px;
    padding: 12px 18px;
    background: linear-gradient(90deg, rgba(200,169,110,0.18), rgba(111,83,154,0.14));
    border-top: 1px solid rgba(255,255,255,0.06);
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.journey-rail {
    margin-top: 22px;
    border-radius: 22px;
    border: 1px solid rgba(200,169,110,0.14);
    background: rgba(255,255,255,0.03);
    padding: 18px;
}

.journey-rail-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 14px;
}

.journey-rail-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
}

.journey-stop {
    position: relative;
    border-radius: 18px;
    border: 1px solid rgba(200,169,110,0.12);
    background: rgba(12,9,7,0.58);
    padding: 16px 14px 14px;
    min-height: 128px;
}

.journey-stop::before {
    content: "";
    position: absolute;
    top: 18px;
    right: 16px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: rgba(255,255,255,0.08);
    box-shadow: 0 0 0 5px rgba(255,255,255,0.02);
}

.journey-stop.is-active,
.journey-stop.is-complete {
    border-color: rgba(200,169,110,0.42);
    box-shadow: inset 0 1px 0 rgba(200,169,110,0.08), 0 0 28px rgba(200,169,110,0.08);
}

.journey-stop.is-active::before,
.journey-stop.is-complete::before {
    background: var(--gold);
}

.journey-stop-index {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 9px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.journey-stop-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 17px;
    line-height: 1.3;
    margin-bottom: 8px;
}

.journey-stop-copy {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.5;
}

.museum-header-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
    width: 100%;
}

.museum-ticket-btn {
    min-width: 180px;
}

body.is-beginning-journey .control-card {
    transform: scale(0.985) rotate(-0.6deg);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

body.is-beginning-journey .control-card::after {
    content: "ADMISSION STAMPED";
    position: absolute;
    inset: 28px auto auto 28px;
    color: rgba(255, 208, 150, 0.88);
    border: 1px solid rgba(255, 208, 150, 0.34);
    border-radius: 999px;
    padding: 10px 14px;
    font-family: 'Cinzel', serif;
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    background: rgba(52, 22, 18, 0.34);
    transform: rotate(-11deg) scale(0.86);
    animation: stampFlash 0.9s ease;
}

.museum-action-btn,
.museum-secondary-btn {
    background: linear-gradient(180deg, color-mix(in srgb, var(--gold) 16%, var(--panel-strong)), color-mix(in srgb, var(--panel-strong) 88%, black)) !important;
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
    background: linear-gradient(180deg, color-mix(in srgb, var(--gold) 24%, var(--panel-strong)), color-mix(in srgb, var(--panel-strong) 84%, black)) !important;
    transform: translateY(-1px);
}

.status-wrap {
    padding: 0;
}

.share-wrap {
    width: 100%;
    margin: 0;
    padding: 0 0 14px;
}

.audio-guide-wrap,
.installation-wrap {
    width: 100%;
    margin: 0;
    padding: 0 0 14px;
}

.museum-audio-guide,
.museum-installation-shell {
    border: 1px solid var(--line);
    border-radius: 20px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.12), transparent 24%),
        var(--panel);
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.18);
}

.museum-audio-guide {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.9fr);
    gap: 18px;
    padding: 18px 20px;
    align-items: center;
}

.museum-audio-copyblock {
    min-width: 0;
}

.museum-audio-kicker,
.museum-installation-kicker,
.museum-installation-plaque-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.museum-audio-title,
.museum-installation-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 28px;
    line-height: 1.15;
}

.museum-audio-copy,
.museum-installation-text,
.museum-installation-note {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.6;
    margin-top: 8px;
}

.museum-audio-controls {
    border-left: 1px solid rgba(200, 169, 110, 0.12);
    padding-left: 18px;
    display: grid;
    gap: 12px;
    align-content: center;
}

.museum-audio-hall,
.museum-audio-status {
    color: var(--paper);
    font-size: 14px;
}

.museum-audio-button-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.museum-audio-meter {
    display: inline-flex;
    gap: 6px;
    align-items: end;
    min-height: 18px;
}

.museum-audio-meter span {
    width: 6px;
    height: 10px;
    border-radius: 999px;
    background: rgba(200, 169, 110, 0.25);
    transform-origin: bottom center;
}

body.is-guide-speaking .museum-audio-meter span,
.museum-audio-guide.is-speaking .museum-audio-meter span {
    animation: museumEqualizer 0.9s ease-in-out infinite;
}

.museum-audio-meter span:nth-child(2) {
    animation-delay: 0.08s;
}

.museum-audio-meter span:nth-child(3) {
    animation-delay: 0.16s;
}

.museum-audio-meter span:nth-child(4) {
    animation-delay: 0.24s;
}

.museum-installation-shell {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.95fr);
    gap: 18px;
    padding: 22px;
    align-items: center;
}

.museum-installation-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
}

.museum-installation-tags span {
    border-radius: 999px;
    border: 1px solid rgba(200, 169, 110, 0.18);
    padding: 6px 10px 5px;
    color: var(--paper);
    font-size: 11px;
    background: rgba(255,255,255,0.02);
}

.museum-installation-stage {
    position: relative;
    min-height: 280px;
    border-radius: 18px;
    overflow: hidden;
    background:
        radial-gradient(circle at 50% 18%, rgba(255, 243, 214, 0.18), transparent 18%),
        linear-gradient(180deg, rgba(44, 29, 18, 0.32), rgba(11, 8, 7, 0.92));
    border: 1px solid rgba(200, 169, 110, 0.12);
}

.museum-installation-aura {
    position: absolute;
    inset: 18px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.04);
    background: radial-gradient(circle at 50% 26%, rgba(255, 243, 214, 0.08), transparent 22%);
    animation: roomGlowShift 7.5s ease-in-out infinite;
}

.museum-installation-frame {
    position: absolute;
    left: 50%;
    top: 34px;
    width: 220px;
    height: 220px;
    transform: translateX(-50%);
    border-radius: 50%;
    background:
        radial-gradient(circle at 35% 30%, rgba(255,255,255,0.24), transparent 20%),
        radial-gradient(circle at 50% 50%, rgba(200,169,110,0.18), rgba(34,22,13,0.92) 74%);
    border: 1px solid rgba(200, 169, 110, 0.2);
    box-shadow: 0 28px 48px rgba(0,0,0,0.22);
}

.museum-installation-orb {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 96px;
    height: 96px;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    background:
        radial-gradient(circle at 35% 32%, rgba(255, 242, 214, 0.88), rgba(181, 136, 74, 0.72) 44%, rgba(74, 45, 22, 0.98) 100%);
    box-shadow: 0 0 38px rgba(217, 176, 106, 0.18);
    animation: artifactFloat 5.4s ease-in-out infinite;
}

.museum-installation-plaque {
    position: absolute;
    left: 22px;
    right: 22px;
    bottom: 18px;
    border: 1px solid rgba(255, 235, 203, 0.1);
    background: rgba(14, 10, 8, 0.72);
    padding: 12px 14px;
    border-radius: 14px;
}

.museum-installation-plaque-value {
    color: var(--paper);
    font-size: 15px;
    line-height: 1.45;
}

.share-card {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 20px 22px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.12), transparent 24%),
        var(--panel);
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.18);
}

.share-card-kicker,
.share-card-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    text-transform: uppercase;
    letter-spacing: 0.16em;
}

.share-card-kicker {
    font-size: 10px;
    margin-bottom: 8px;
}

.share-card-title {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 28px;
    margin-bottom: 8px;
}

.share-card-summary {
    color: var(--paper);
    font-size: 18px;
    line-height: 1.65;
    margin-bottom: 16px;
}

.share-card-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.share-card-stat {
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-radius: 14px;
    padding: 12px 14px;
    background: rgba(255, 255, 255, 0.03);
}

.share-card-label {
    font-size: 9px;
    margin-bottom: 8px;
}

.share-card-value {
    color: var(--paper);
    font-size: 15px;
    line-height: 1.55;
}

.status-panel {
    border: 1px solid rgba(200, 169, 110, 0.18);
    border-radius: 18px;
    padding: 16px;
    background:
        radial-gradient(circle at top left, rgba(200, 169, 110, 0.08), transparent 34%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 22%),
        var(--panel);
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.status-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 9px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    opacity: 0.9;
    margin-bottom: 8px;
}

.status-line {
    font-family: 'Cinzel', serif;
    color: var(--paper);
    font-size: 16px;
    line-height: 1.25;
    letter-spacing: 0.06em;
    text-wrap: balance;
}

.status-subline {
    margin-top: 6px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
}

.status-side {
    border-top: 1px solid rgba(200, 169, 110, 0.12);
    padding-top: 12px;
}

.mode-chip {
    font-size: 9px;
    color: var(--gold-soft);
    margin-bottom: 8px;
}

.mode-name {
    color: var(--paper);
    font-size: 17px;
    margin-bottom: 4px;
}

.mode-desc {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.55;
}

.status-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.status-tag {
    border-radius: 999px;
    border: 1px solid rgba(200, 169, 110, 0.18);
    padding: 6px 10px 5px;
    color: var(--paper);
    font-size: 10px;
    letter-spacing: 0.04em;
    background: rgba(255, 255, 255, 0.02);
}

.map-wrap {
    padding: 0;
}

.museum-map {
    position: relative;
    min-height: 280px;
    border: 1px solid var(--line);
    border-radius: 24px;
    background:
        radial-gradient(circle at top left, rgba(200, 169, 110, 0.08), transparent 20%),
        linear-gradient(180deg, color-mix(in srgb, var(--panel) 92%, transparent), color-mix(in srgb, var(--panel-strong) 96%, black));
    overflow: hidden;
    box-shadow:
        inset 0 1px 0 rgba(200, 169, 110, 0.04),
        0 18px 44px rgba(0, 0, 0, 0.22);
}

.museum-map-help,
.museum-legend {
    display: none;
}

.museum-nav-rail {
    padding: 14px 12px 12px;
}

.museum-nav-header {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 4px 4px 14px;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--line);
}

.museum-nav-stack {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.museum-room {
    position: relative;
    border-radius: 16px;
    border: 1.5px solid rgba(200, 169, 110, 0.26);
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.01)),
        color-mix(in srgb, var(--panel-strong) 76%, transparent);
    padding: 12px 12px 11px;
    cursor: pointer;
    transition: transform 0.22s ease, border-color 0.22s ease, opacity 0.22s ease, box-shadow 0.22s ease;
    z-index: 2;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    backdrop-filter: blur(1px);
}

.museum-room::before {
    content: "";
    position: absolute;
    inset: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 14px;
    pointer-events: none;
}

.museum-room::after {
    display: none;
}

.museum-room:hover {
    transform: translateY(-3px) scale(1.01);
    border-color: rgba(200, 169, 110, 0.44);
    box-shadow: 0 18px 28px rgba(0, 0, 0, 0.16);
}

.museum-room.state-active {
    animation: hallActivePulse 1.1s ease;
}

@keyframes hallActivePulse {
    0% {
        transform: translateY(0);
        box-shadow: 0 0 0 rgba(200, 169, 110, 0);
    }
    38% {
        transform: translateY(-3px) scale(1.01);
        box-shadow: 0 0 0 10px rgba(200, 169, 110, 0.12), 0 22px 34px rgba(0, 0, 0, 0.16);
    }
    100% {
        transform: translateY(0);
        box-shadow: 0 0 0 rgba(200, 169, 110, 0);
    }
}

.museum-room.state-active {
    border-color: rgba(200, 169, 110, 0.6);
    box-shadow: 0 0 0 1px rgba(200, 169, 110, 0.08), inset 0 0 0 1px rgba(200, 169, 110, 0.08), 0 0 24px rgba(200, 169, 110, 0.1);
    background:
        linear-gradient(180deg, rgba(200, 169, 110, 0.18), rgba(200, 169, 110, 0.08)),
        rgba(28, 22, 17, 0.92);
}

.museum-room.state-active .museum-room-sigil {
    animation: sigilOrbitPulse 1.6s ease-in-out infinite;
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

.museum-room--rail {
    min-height: 82px;
    padding-right: 42px;
}

.museum-room-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 8px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 6px;
    opacity: 0.72;
}

.museum-room-sigil {
    position: absolute;
    right: 12px;
    top: 12px;
    width: 22px;
    height: 22px;
    border-radius: 999px;
    border: 1px solid rgba(200, 169, 110, 0.18);
    display: grid;
    place-items: center;
    color: var(--gold-soft);
    font-size: 12px;
    opacity: 0.88;
    background: rgba(255,255,255,0.02);
}

.museum-room-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 17px;
    letter-spacing: 0.01em;
    margin-bottom: 4px;
    line-height: 1.1;
    text-wrap: balance;
}

.museum-room-copy {
    color: var(--muted);
    display: block;
    font-size: 12px;
    line-height: 1.38;
    max-width: 18ch;
}

.museum-visitor-label {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 8px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    opacity: 0.85;
}

.museum-visitor-caption {
    color: var(--paper);
    background: none;
    border: 0;
    border-radius: 0;
    padding: 0;
    font-size: 13px;
    line-height: 1.2;
    box-shadow: none;
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
body[data-museum-theme="light"] .museum-audio-guide,
body[data-museum-theme="light"] .museum-installation-shell,
body[data-museum-theme="light"] .status-panel,
body[data-museum-theme="light"] .loading-card,
body[data-museum-theme="light"] .museum-room {
    background-color: rgba(255, 251, 244, 0.86) !important;
}

body[data-museum-theme="light"] .input-zone textarea,
body[data-museum-theme="light"] .input-zone input,
body[data-museum-theme="light"] .theme-chip {
    background: rgba(255, 255, 253, 0.96) !important;
    color: var(--paper) !important;
}

body[data-museum-theme="light"] .museum-room-copy,
body[data-museum-theme="light"] .hero-side-note,
body[data-museum-theme="light"] .control-panel-copy,
body[data-museum-theme="light"] .museum-map-help,
body[data-museum-theme="light"] .museum-legend-copy,
body[data-museum-theme="light"] .museum-audio-copy,
body[data-museum-theme="light"] .museum-installation-text,
body[data-museum-theme="light"] .museum-installation-note {
    color: #556971 !important;
}

body[data-museum-theme="dark"] .museum-map,
body[data-museum-theme="dark"] .control-card,
body[data-museum-theme="dark"] .theme-bar,
body[data-museum-theme="dark"] .museum-shell,
body[data-museum-theme="dark"] .museum-room,
body[data-museum-theme="dark"] .hall-tabs .tab-nav {
    background-color: rgba(10, 14, 22, 0.88) !important;
}

body[data-museum-theme="light"] .museum-header {
    background:
        radial-gradient(circle at 50% -20%, rgba(95, 141, 156, 0.18), transparent 35%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(245, 240, 233, 0.96)) !important;
}

body[data-museum-theme="light"] .museum-marquee,
body[data-museum-theme="light"] .museum-tagline,
body[data-museum-theme="light"] .hero-side-copy,
body[data-museum-theme="light"] .featured-text,
body[data-museum-theme="light"] .lobby-summary,
body[data-museum-theme="light"] .timeline-desc,
body[data-museum-theme="light"] .visitor-entry,
body[data-museum-theme="light"] .hall-panel-copy,
body[data-museum-theme="light"] .status-subline {
    color: #24333b !important;
}

body[data-museum-theme="light"] .museum-hall-nav-copy,
body[data-museum-theme="light"] .mode-desc,
body[data-museum-theme="light"] .artifact-meta,
body[data-museum-theme="light"] .featured-prompt {
    color: #556971 !important;
}

body[data-museum-theme="light"] .museum-room {
    background:
        linear-gradient(180deg, rgba(95, 141, 156, 0.12), rgba(95, 141, 156, 0.04)),
        rgba(255, 252, 247, 0.95) !important;
    border-color: rgba(88, 111, 122, 0.3) !important;
}

body[data-museum-theme="light"] .museum-room-title,
body[data-museum-theme="light"] .museum-legend-title,
body[data-museum-theme="light"] .museum-hall-nav-title,
body[data-museum-theme="light"] .timeline-title,
body[data-museum-theme="light"] .artifact-name {
    color: #1f3138 !important;
}

body[data-museum-theme="light"] .museum-foyer-label,
body[data-museum-theme="light"] .museum-visitor-label {
    color: #4e6570 !important;
}

body[data-museum-theme="light"] .museum-visitor-caption {
    color: #f8fcfd !important;
    background: rgba(38, 57, 66, 0.92) !important;
    border-color: rgba(88, 111, 122, 0.36) !important;
}

body[data-museum-theme="light"] .theme-chip:hover,
body[data-museum-theme="light"] .theme-chip.is-active,
body[data-museum-theme="light"] .museum-hall-nav-btn:hover,
body[data-museum-theme="light"] .museum-hall-nav-btn.is-active,
body[data-museum-theme="light"] .mode-radio input:checked + span {
    background: rgba(213, 229, 235, 0.86) !important;
    color: #18323b !important;
}

body[data-museum-theme="dark"] .museum-header {
    background:
        radial-gradient(circle at 50% -20%, rgba(79, 183, 187, 0.22), transparent 35%),
        linear-gradient(180deg, rgba(12, 24, 31, 0.96), rgba(7, 18, 28, 0.92)) !important;
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

.museum-room-stage {
    position: relative;
    width: min(100%, 1540px);
    min-height: 470px;
    margin: 0 auto 18px;
    border: 1px solid rgba(200, 169, 110, 0.16);
    border-radius: 24px;
    overflow: hidden;
    background:
        radial-gradient(circle at top, rgba(200, 169, 110, 0.08), transparent 26%),
        linear-gradient(180deg, rgba(17, 12, 10, 0.82), rgba(10, 8, 7, 0.9));
    box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.03),
        0 20px 50px rgba(0, 0, 0, 0.24);
}

.museum-room-stage::before {
    content: "";
    position: absolute;
    inset: -20% -10%;
    background:
        radial-gradient(circle at 18% 18%, rgba(255,255,255,0.05), transparent 16%),
        radial-gradient(circle at 78% 20%, rgba(200,169,110,0.07), transparent 18%),
        radial-gradient(circle at 46% 12%, rgba(255,255,255,0.04), transparent 14%);
    opacity: 0.7;
    pointer-events: none;
    animation: museumDustDrift 22s linear infinite;
}

.museum-room-stage.is-transitioning::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(110deg, transparent 0%, rgba(255, 242, 214, 0.04) 42%, rgba(255, 242, 214, 0.14) 50%, transparent 58%);
    pointer-events: none;
    animation: roomSweep 0.74s ease;
    z-index: 5;
}

.museum-room-scene {
    position: absolute;
    inset: 0;
    opacity: 0;
    transform: scale(1.03) translateY(12px);
    transition: opacity 0.6s ease, transform 0.6s ease;
    pointer-events: none;
}

.museum-room-stage[data-active-room="lobby"] .museum-room-scene--lobby,
.museum-room-stage[data-active-room="artifacts"] .museum-room-scene--artifacts,
.museum-room-stage[data-active-room="timeline"] .museum-room-scene--timeline,
.museum-room-stage[data-active-room="newspaper"] .museum-room-scene--newspaper,
.museum-room-stage[data-active-room="visitor"] .museum-room-scene--visitor {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.museum-room-scene::before {
    content: "";
    position: absolute;
    inset: 0;
    opacity: 0.95;
}

.museum-room-scene::after {
    content: "";
    position: absolute;
    inset: auto 0 0;
    height: 30%;
    background:
        linear-gradient(180deg, transparent 0%, rgba(26, 18, 13, 0.18) 22%, rgba(14, 11, 9, 0.94) 100%);
    border-top: 1px solid rgba(200, 169, 110, 0.08);
}

.museum-room-scene--lobby::before {
    background:
        radial-gradient(circle at 50% 26%, rgba(244, 222, 176, 0.34), transparent 12%),
        linear-gradient(180deg, rgba(56, 37, 24, 0.16), rgba(10, 8, 7, 0.08)),
        linear-gradient(90deg, rgba(24, 16, 12, 0.78) 0 18%, transparent 18% 82%, rgba(24, 16, 12, 0.78) 82% 100%),
        linear-gradient(180deg, rgba(124, 86, 48, 0.18), rgba(18, 12, 10, 0.92));
}

.museum-room-scene--artifacts::before {
    background:
        repeating-linear-gradient(90deg, rgba(34, 24, 18, 0.72) 0 10%, rgba(18, 13, 11, 0.82) 10% 20%),
        radial-gradient(circle at 28% 42%, rgba(214, 191, 141, 0.12), transparent 10%),
        radial-gradient(circle at 70% 38%, rgba(214, 191, 141, 0.12), transparent 11%),
        linear-gradient(180deg, rgba(92, 58, 30, 0.16), rgba(14, 11, 9, 0.94));
}

.museum-room-scene--timeline::before {
    background:
        linear-gradient(90deg, rgba(17, 12, 10, 0.78) 0 12%, transparent 12% 88%, rgba(17, 12, 10, 0.78) 88% 100%),
        repeating-linear-gradient(90deg, transparent 0 14%, rgba(214, 191, 141, 0.08) 14% 14.6%, transparent 14.6% 28%),
        linear-gradient(180deg, rgba(179, 140, 81, 0.14), rgba(10, 8, 7, 0.9));
}

.museum-room-scene--newspaper::before {
    background:
        linear-gradient(180deg, rgba(255, 251, 239, 0.08), transparent 28%),
        radial-gradient(circle at 78% 24%, rgba(236, 215, 170, 0.18), transparent 16%),
        linear-gradient(90deg, rgba(22, 16, 12, 0.78) 0 16%, transparent 16% 84%, rgba(22, 16, 12, 0.78) 84% 100%),
        linear-gradient(180deg, rgba(108, 76, 38, 0.16), rgba(12, 9, 7, 0.92));
}

.museum-room-scene--visitor::before {
    background:
        radial-gradient(circle at 50% 36%, rgba(232, 220, 192, 0.18), transparent 18%),
        linear-gradient(90deg, rgba(18, 13, 11, 0.82) 0 26%, transparent 26% 74%, rgba(18, 13, 11, 0.82) 74% 100%),
        linear-gradient(180deg, rgba(84, 64, 42, 0.14), rgba(10, 8, 7, 0.92));
}

.museum-room-glow {
    position: absolute;
    inset: 16px;
    border-radius: 18px;
    border: 1px solid rgba(255, 255, 255, 0.04);
    background: radial-gradient(circle at 50% 18%, rgba(255, 244, 218, 0.06), transparent 18%);
    animation: roomGlowShift 7.5s ease-in-out infinite;
}

.museum-room-spotlight {
    position: absolute;
    top: 20px;
    width: 190px;
    height: 190px;
    border-radius: 50%;
    filter: blur(8px);
    background: radial-gradient(circle, rgba(255, 240, 205, 0.4) 0%, rgba(255, 240, 205, 0.16) 32%, transparent 72%);
    opacity: 0.92;
    animation: spotlightFloat 6.8s ease-in-out infinite;
}

.museum-room-spotlight--left {
    left: 15%;
    animation-delay: -1.4s;
}

.museum-room-spotlight--center {
    left: 50%;
    transform: translateX(-50%);
}

.museum-room-spotlight--right {
    right: 15%;
    animation-delay: -3.1s;
}

.museum-room-gallery {
    position: absolute;
    left: clamp(320px, 34%, 520px);
    right: 5%;
    top: 76px;
    bottom: 34px;
    display: grid;
    grid-template-columns: 1.35fr 0.9fr;
    gap: 22px;
    align-items: end;
}

.museum-room-artwall {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    align-items: start;
}

.museum-room-frame {
    position: relative;
    min-height: 190px;
    border-radius: 6px;
    background:
        linear-gradient(135deg, rgba(109, 80, 43, 0.9), rgba(48, 32, 18, 0.96));
    padding: 10px;
    box-shadow:
        0 16px 30px rgba(0, 0, 0, 0.24),
        inset 0 1px 0 rgba(255, 234, 198, 0.1);
    transform-origin: center bottom;
    animation: frameSway 8.5s ease-in-out infinite;
}

.museum-room-frame::before {
    content: "";
    position: absolute;
    inset: 10px;
    border: 1px solid rgba(255, 233, 197, 0.14);
    pointer-events: none;
}

.museum-room-canvas {
    position: relative;
    min-height: 170px;
    height: 100%;
    border: 1px solid rgba(25, 16, 10, 0.4);
    background:
        radial-gradient(circle at 32% 28%, rgba(255, 240, 219, 0.18), transparent 16%),
        linear-gradient(135deg, rgba(83, 56, 29, 0.92), rgba(28, 19, 12, 0.92));
    overflow: hidden;
}

.museum-room-canvas--tall {
    min-height: 250px;
}

.museum-room-canvas::after {
    content: "";
    position: absolute;
    inset: 0;
    background:
        linear-gradient(90deg, transparent 0 48%, rgba(255, 255, 255, 0.03) 50%, transparent 52%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 40%);
    mix-blend-mode: screen;
    animation: varnishShimmer 5.6s ease-in-out infinite;
}

.museum-room-plinth-zone {
    position: relative;
    min-height: 280px;
}

.museum-room-plinth {
    position: absolute;
    left: 12%;
    right: 12%;
    bottom: 0;
    height: 92px;
    border-radius: 10px 10px 0 0;
    background:
        linear-gradient(180deg, rgba(215, 188, 139, 0.12), rgba(40, 27, 16, 0.96));
    border: 1px solid rgba(230, 205, 160, 0.12);
    box-shadow: 0 18px 34px rgba(0, 0, 0, 0.24);
    animation: plinthBreath 6.5s ease-in-out infinite;
}

.museum-room-object {
    position: absolute;
    left: 50%;
    bottom: 72px;
    transform: translateX(-50%);
    animation: artifactFloat 5.6s ease-in-out infinite;
}

.museum-room-object--orb {
    width: 92px;
    height: 92px;
    border-radius: 50%;
    background:
        radial-gradient(circle at 35% 32%, rgba(255, 242, 214, 0.82), rgba(181, 136, 74, 0.72) 44%, rgba(74, 45, 22, 0.98) 100%);
    box-shadow: 0 0 38px rgba(217, 176, 106, 0.16);
}

.museum-room-object--column {
    width: 86px;
    height: 138px;
    border-radius: 44px 44px 10px 10px;
    background:
        linear-gradient(180deg, rgba(228, 214, 183, 0.24), rgba(81, 56, 31, 0.96));
    clip-path: polygon(28% 0%, 72% 0%, 86% 16%, 86% 84%, 72% 100%, 28% 100%, 14% 84%, 14% 16%);
    animation-duration: 6.3s;
}

.museum-room-object--desk {
    width: 150px;
    height: 86px;
    border-radius: 14px 14px 8px 8px;
    background:
        linear-gradient(180deg, rgba(208, 177, 123, 0.2), rgba(58, 39, 22, 0.96));
    box-shadow: inset 0 -20px 30px rgba(0, 0, 0, 0.22);
    animation-duration: 7s;
}

.museum-room-object--book {
    width: 120px;
    height: 28px;
    border-radius: 4px 4px 10px 10px;
    background:
        linear-gradient(180deg, rgba(240, 233, 211, 0.8), rgba(103, 76, 44, 0.94));
    transform: translateX(-50%) rotate(-8deg);
    animation-duration: 5.2s;
}

.museum-room-wall-label {
    position: absolute;
    left: 6%;
    bottom: 24px;
    padding: 10px 12px 9px;
    border: 1px solid rgba(255, 235, 203, 0.1);
    background: rgba(14, 10, 8, 0.66);
    color: var(--muted);
    font-size: 12px;
    line-height: 1.45;
    max-width: 22ch;
}

.museum-room-label-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 4px;
}

.museum-room-scene-copy {
    position: absolute;
    left: 32px;
    top: 34px;
    width: clamp(220px, 27vw, 360px);
    max-width: calc(100% - 140px);
    z-index: 2;
    padding: 0 10px 14px 0;
    animation: copyRevealFloat 1s ease both;
}

.museum-room-scene-kicker {
    color: var(--gold-soft);
    font-family: 'Cinzel', serif;
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.museum-room-scene-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 34px;
    line-height: 1.15;
    margin-bottom: 10px;
}

.museum-room-scene-text {
    color: var(--paper);
    font-size: 17px;
    line-height: 1.7;
    max-width: 32ch;
    max-height: 12em;
    overflow: hidden;
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
    opacity: 0.76;
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
    border: 1px solid var(--line);
    border-top: none;
    border-radius: 0 0 22px 22px;
    background:
        radial-gradient(circle at top right, rgba(255, 255, 255, 0.03), transparent 18%),
        rgba(10, 8, 7, 0.84);
    padding: 18px 18px 20px;
    transform-origin: top center;
}

.museum-hall-panel.is-active {
    display: block;
    animation: hallPanelReveal 0.56s cubic-bezier(.2,.8,.2,1) both;
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
    border-bottom: 1px solid var(--line);
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
    color: var(--paper);
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

.museum-hall-panel.hall-panel--lobby {
    background: linear-gradient(160deg, #2a1f14, #1a1208);
}

.museum-hall-panel.hall-panel--artifacts {
    background:
        linear-gradient(180deg, rgba(255,255,255,0.02), transparent 16%),
        #0f0d0b;
}

.museum-hall-panel.hall-panel--timeline {
    background:
        repeating-linear-gradient(
            90deg,
            rgba(200,169,110,0.03) 0,
            rgba(200,169,110,0.03) 1px,
            transparent 1px,
            transparent 80px
        ),
        #0c0a09;
}

.museum-hall-panel.hall-panel--newspaper {
    background:
        linear-gradient(180deg, rgba(255,255,255,0.48), rgba(255,255,255,0.18)),
        #f7f1e6;
    border-color: rgba(36,26,18,0.16);
}

.museum-hall-panel.hall-panel--newspaper,
.museum-hall-panel.hall-panel--newspaper .hall-panel-title,
.museum-hall-panel.hall-panel--newspaper .hall-panel-copy,
.museum-hall-panel.hall-panel--newspaper .hall-panel-kicker,
.museum-hall-panel.hall-panel--newspaper .museum-action-btn,
.museum-hall-panel.hall-panel--newspaper .museum-secondary-btn {
    color: #241a12 !important;
}

.museum-hall-panel.hall-panel--newspaper .hall-panel-copy {
    color: #4d3d2d !important;
}

.museum-hall-panel.hall-panel--visitor {
    background: #080605;
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
    border: 1px dashed var(--line);
    border-radius: 12px;
    background:
        radial-gradient(circle at top, rgba(255, 255, 255, 0.03), transparent 28%),
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

@keyframes museumHeaderDrift {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-2px); }
}

@keyframes museumSealFloat {
    0%, 100% { transform: translateY(0) scale(1); box-shadow: inset 0 1px 0 rgba(255,255,255,0.05); }
    50% { transform: translateY(-4px) scale(1.02); box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 12px 24px rgba(0,0,0,0.14); }
}

@keyframes museumDustDrift {
    0% { transform: translate3d(-2%, 0, 0) rotate(0deg); }
    50% { transform: translate3d(2%, 1.5%, 0) rotate(5deg); }
    100% { transform: translate3d(-2%, 0, 0) rotate(0deg); }
}

@keyframes roomSweep {
    0% { transform: translateX(-100%) skewX(-12deg); opacity: 0; }
    20% { opacity: 1; }
    100% { transform: translateX(120%) skewX(-12deg); opacity: 0; }
}

@keyframes roomGlowShift {
    0%, 100% { opacity: 0.85; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.01); }
}

@keyframes spotlightFloat {
    0%, 100% { transform: translateY(0) scale(1); opacity: 0.86; }
    50% { transform: translateY(8px) scale(1.06); opacity: 1; }
}

@keyframes frameSway {
    0%, 100% { transform: rotate(-0.4deg) translateY(0); }
    50% { transform: rotate(0.55deg) translateY(-3px); }
}

@keyframes varnishShimmer {
    0%, 100% { opacity: 0.35; transform: translateX(-2%); }
    50% { opacity: 0.7; transform: translateX(2%); }
}

@keyframes plinthBreath {
    0%, 100% { transform: translateY(0); box-shadow: 0 18px 34px rgba(0, 0, 0, 0.24); }
    50% { transform: translateY(-3px); box-shadow: 0 24px 40px rgba(0, 0, 0, 0.28); }
}

@keyframes artifactFloat {
    0%, 100% { transform: translateX(-50%) translateY(0); filter: drop-shadow(0 10px 20px rgba(0,0,0,0.16)); }
    50% { transform: translateX(-50%) translateY(-8px); filter: drop-shadow(0 16px 28px rgba(0,0,0,0.22)); }
}

@keyframes copyRevealFloat {
    0% { opacity: 0; transform: translateY(18px); }
    100% { opacity: 1; transform: translateY(0); }
}

@keyframes landingCardReveal {
    0% { opacity: 0; transform: translateY(28px) scale(0.98); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes hallPanelReveal {
    0% { opacity: 0; transform: translateY(16px) scale(0.985); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes sigilOrbitPulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 rgba(200,169,110,0); }
    50% { transform: scale(1.14); box-shadow: 0 0 0 8px rgba(200,169,110,0.08); }
}

@keyframes landingStageFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}

@keyframes skylineDrift {
    0%, 100% { transform: translateX(0); opacity: 0.92; }
    50% { transform: translateX(8px); opacity: 1; }
}

@keyframes domePulse {
    0%, 100% { transform: translateX(-50%) scale(1); filter: brightness(1); }
    50% { transform: translateX(-50%) scale(1.03); filter: brightness(1.08); }
}

@keyframes stepsGlow {
    0%, 100% { opacity: 0.88; }
    50% { opacity: 1; }
}

@keyframes pillarRise {
    0%, 100% { transform: translateY(0); opacity: 0.86; }
    50% { transform: translateY(-6px); opacity: 1; }
}

@keyframes fragmentFloat {
    0%, 100% { opacity: 0.72; }
    50% { opacity: 1; }
}

@keyframes museumMotes {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(10px); }
}

@keyframes stampFlash {
    0% { opacity: 0; transform: rotate(-16deg) scale(1.12); }
    45% { opacity: 1; transform: rotate(-11deg) scale(1); }
    100% { opacity: 0.92; transform: rotate(-11deg) scale(0.94); }
}

@keyframes museumEqualizer {
    0%, 100% { transform: scaleY(0.7); opacity: 0.45; }
    50% { transform: scaleY(1.55); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
    .museum-header-band,
    .museum-world-emblem,
    .museum-room.state-active,
    .museum-room.state-active .museum-room-sigil,
    .museum-room-stage::before,
    .museum-room-stage.is-transitioning::after,
    .museum-room-glow,
    .museum-room-spotlight,
    .museum-room-frame,
    .museum-room-canvas::after,
    .museum-room-plinth,
    .museum-room-object,
    .museum-room-scene-copy,
    .museum-hall-panel.is-active,
    .museum-installation-aura,
    .museum-installation-orb,
    .museum-audio-meter span,
    .landing-shell::after,
    .landing-floating-fragments span,
    .landing-art,
    .landing-skyline,
    .landing-dome,
    .landing-steps,
    .landing-pillars span {
        animation: none !important;
        transition: none !important;
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

.artifact-tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}

.artifact-tag {
    border: 1px solid rgba(200, 169, 110, 0.18);
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--gold-soft);
    background: rgba(200, 169, 110, 0.08);
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
        linear-gradient(180deg, rgba(255,255,255,0.55), rgba(255,255,255,0.24)),
        rgba(250, 245, 236, 0.96);
    border-radius: 18px;
    color: var(--ink) !important;
    padding: 24px 28px 18px;
    border: 1px solid rgba(54, 40, 24, 0.14);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.55),
        0 14px 30px rgba(40, 26, 15, 0.08);
}

.newspaper-shell * {
    color: var(--ink) !important;
}

.paper-kicker {
    font-size: 10px;
    color: #6b5135;
    text-align: center;
    margin-bottom: 12px;
}

.newspaper-name {
    font-family: 'Cinzel', serif;
    font-size: 32px;
    text-align: center;
    border-top: 2.5px solid rgba(36, 26, 18, 0.82);
    border-bottom: 2.5px solid rgba(36, 26, 18, 0.82);
    padding: 10px 0;
    margin-bottom: 8px;
    letter-spacing: 0.06em;
}

.newspaper-meta {
    text-align: center;
    color: #5c4937;
    font-size: 13px;
    font-style: italic;
    margin-bottom: 18px;
    border-bottom: 1px solid rgba(36,26,18,0.22);
    padding-bottom: 16px;
}

.newspaper-headline {
    font-family: 'Cinzel', serif;
    font-size: 26px;
    line-height: 1.3;
    margin-bottom: 16px;
    border-bottom: 1px solid rgba(36,26,18,0.22);
    padding-bottom: 12px;
    color: #1f1710 !important;
}

.newspaper-columns {
    column-count: 2;
    column-gap: 28px;
    column-rule: 1px solid rgba(70, 50, 30, 0.18);
}

.newspaper-column-block {
    break-inside: avoid;
    margin-bottom: 14px;
}

.newspaper-body,
.newspaper-secondary-body {
    font-size: 18px;
    line-height: 1.9;
    color: #241a12 !important;
}

.newspaper-body {
    border-bottom: 0;
    padding-bottom: 0;
    margin-bottom: 0;
}

.newspaper-body::first-letter {
    float: left;
    font-family: 'Cinzel', serif;
    font-size: 64px;
    line-height: 0.82;
    margin: 4px 8px 0 0;
    color: #241a12;
}

.newspaper-secondary-headline {
    font-family: 'Cinzel', serif;
    font-size: 18px;
    margin-bottom: 8px;
    color: #2b2016 !important;
}

.newspaper-ad {
    margin-top: 16px;
    padding: 12px 14px;
    border: 1px solid rgba(70, 50, 30, 0.28);
    font-size: 14px;
    color: #5d4732;
    font-style: italic;
    background: rgba(255,255,255,0.28);
    border-radius: 12px;
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

.curator-notes-shell {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 18px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.08), transparent 24%),
        rgba(16, 11, 9, 0.84);
}

.curator-notes-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    margin-bottom: 14px;
}

.curator-notes-kicker {
    color: #d7a4a4;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
}

.curator-notes-headline {
    color: var(--paper);
    font-size: 18px;
    line-height: 1.6;
}

.curator-notes-score {
    min-width: 112px;
    text-align: center;
    border: 1px solid rgba(215, 164, 164, 0.2);
    border-radius: 14px;
    padding: 10px 12px;
    color: #f1c9c9;
    font-family: 'Cinzel', serif;
}

.curator-notes-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.curator-note-card {
    border: 1px solid rgba(215, 164, 164, 0.16);
    border-radius: 14px;
    padding: 14px;
    background: rgba(37, 21, 19, 0.34);
}

.curator-note-level {
    color: #f1b6b6;
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.curator-note-title {
    color: var(--paper);
    font-family: 'Cinzel', serif;
    font-size: 15px;
    margin-bottom: 6px;
}

.curator-note-body {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.65;
}

.museum-complexity-badge {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 12px 16px;
    min-width: 128px;
    text-align: center;
    background: rgba(200, 169, 110, 0.08);
}

.museum-complexity-kicker {
    color: var(--gold-soft);
    font-size: 9px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.museum-complexity-score {
    color: var(--gold);
    font-family: 'Cinzel', serif;
    font-size: 30px;
    line-height: 1.1;
    margin-top: 4px;
}

.museum-complexity-band {
    color: var(--paper);
    font-size: 14px;
    margin-top: 4px;
}

.ambassador-shell {
    margin-top: 18px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background:
        radial-gradient(circle at top right, rgba(200, 169, 110, 0.06), transparent 26%),
        rgba(13, 10, 8, 0.84);
    padding: 18px;
}

.ambassador-intro {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.65;
    margin-bottom: 12px;
}

.ambassador-chat {
    min-height: 220px;
}

.ambassador-chat .message,
.ambassador-chat .message-wrap {
    border-radius: 16px !important;
}

.ambassador-chat textarea,
.ambassador-chat input {
    color: var(--paper) !important;
}

.is-listening {
    box-shadow: 0 0 0 1px rgba(200, 169, 110, 0.3), 0 0 24px rgba(200, 169, 110, 0.2);
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
    .museum-workspace {
        grid-template-columns: 1fr;
    }

    .museum-sidebar {
        position: static;
        min-height: auto;
    }

    .landing-grid,
    .lobby-grid,
    .world-details,
    .curator-notes-grid,
    .timeline-card,
    .hero-grid,
    .museum-audio-guide,
    .museum-installation-shell,
    .status-panel,
    .featured-grid,
    .admission-card-grid {
        grid-template-columns: 1fr;
    }

    .museum-map {
        min-height: 520px;
    }

    .hero-plaques {
        grid-template-columns: 1fr;
    }

    .journey-rail-grid,
    .museum-ticket-meta {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .museum-hall-nav {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .museum-hall-nav-btn {
        min-height: 92px;
    }

    .museum-header-band {
        align-items: flex-start;
        flex-direction: column;
    }

    .status-side {
        border-left: none;
        border-top: 1px solid rgba(200, 169, 110, 0.12);
        padding-left: 0;
        padding-top: 14px;
    }

    .museum-audio-controls {
        border-left: none;
        border-top: 1px solid rgba(200, 169, 110, 0.12);
        padding-left: 0;
        padding-top: 14px;
    }

    .museum-title {
        font-size: 28px;
    }

    .landing-title {
        font-size: 40px;
        max-width: 14ch;
    }

    .landing-art {
        min-height: 480px;
    }

    .landing-plaque-row {
        grid-template-columns: 1fr;
    }

}

@media (max-width: 640px) {
    .gradio-container {
        padding: 0 12px 24px !important;
    }

    .control-shell,
    .theme-wrap,
    .status-wrap,
    .input-zone,
    .map-wrap,
    .museum-hall-stack,
    .museum-topbar,
    .museum-workspace {
        padding-left: 0;
        padding-right: 0;
    }

    .landing-wrap {
        margin-top: 12px;
        min-height: auto;
    }

    .landing-grid {
        padding: 18px;
        gap: 18px;
    }

    .landing-shell {
        border-radius: 22px;
        min-height: auto;
    }

    .landing-title {
        font-size: 32px;
    }

    .landing-subtitle {
        font-size: 18px;
    }

    .landing-lead {
        font-size: 17px;
    }

    .landing-art {
        min-height: 360px;
    }

    .landing-caption {
        flex-direction: column;
        align-items: flex-start;
    }

    .control-shell {
        margin-top: 14px;
    }

    .control-card {
        padding: 18px;
        border-radius: 22px;
    }

    .journey-rail-grid,
    .museum-ticket-meta {
        grid-template-columns: 1fr;
    }

    .museum-header-actions {
        flex-direction: column;
        align-items: stretch;
    }

    .museum-ticket-title {
        font-size: 28px;
    }

    .museum-map {
        min-height: 460px;
        border-radius: 18px;
    }

    .share-card-grid,
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

    .newspaper-columns {
        column-count: 1;
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
    ("lobby", "Lobby", "World overview", "Rule, order, and the pressure point holding the world together."),
    ("artifacts", "Artifacts", "Object gallery", "Relics and impossible tools from public and private life."),
    ("timeline", "Timeline", "History wall", "The turns that made this civilization what it is."),
    ("newspaper", "Newspaper", "Press room", "One surviving front page from the world speaking for itself."),
    ("visitor", "Visitor's Book", "Personal voice", "A final human note after the institution falls quiet."),
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


def esc_attr(value: str) -> str:
    return html.escape(str(value or ""), quote=True)


def type_text(text: str, class_name: str, speed: int = 16, tag: str = "div") -> str:
    safe_text = str(text or "")
    return f"<{tag} class='{esc_attr(class_name)}' data-type-text='{esc_attr(safe_text)}' data-type-speed='{speed}'>{esc(safe_text)}</{tag}>"


def first_item(items, fallback: str) -> str:
    if isinstance(items, list) and items:
        return str(items[0] or fallback)
    return fallback


def simple_seed(text: str) -> int:
    value = str(text or "")
    return sum((index + 1) * ord(char) for index, char in enumerate(value))


def world_aura(world_bible: dict) -> str:
    source = " ".join(
        str(world_bible.get(key, ""))
        for key in ("museum_name", "tagline", "summary", "taboo")
    ).lower()
    if any(word in source for word in ("tide", "sea", "river", "flood", "mist")):
        return "tide"
    if any(word in source for word in ("flame", "ember", "ash", "forge", "fire")):
        return "ember"
    if any(word in source for word in ("garden", "forest", "vine", "moss", "seed")):
        return "verdant"
    if any(word in source for word in ("dream", "memory", "echo", "veil", "moon")):
        return "velvet"
    return ("ember", "tide", "verdant", "velvet")[simple_seed(source) % 4]


def hall_sigil(room_id: str) -> str:
    return {
        "lobby": "◈",
        "artifacts": "⬢",
        "timeline": "⟡",
        "newspaper": "✶",
        "visitor": "☽",
    }.get(room_id, "◌")


def emblem_svg(world_bible: dict) -> str:
    source = " ".join(
        str(world_bible.get(key, ""))
        for key in ("museum_name", "tagline", "government", "taboo")
    )
    variant = simple_seed(source) % 4
    if variant == 0:
        return """
<svg viewBox="0 0 48 48" aria-hidden="true">
  <circle cx="24" cy="24" r="16"></circle>
  <line x1="24" y1="8" x2="24" y2="40"></line>
  <line x1="8" y1="24" x2="40" y2="24"></line>
</svg>
"""
    if variant == 1:
        return """
<svg viewBox="0 0 48 48" aria-hidden="true">
  <polygon points="24,7 38,24 24,41 10,24"></polygon>
  <circle cx="24" cy="24" r="6"></circle>
</svg>
"""
    if variant == 2:
        return """
<svg viewBox="0 0 48 48" aria-hidden="true">
  <path d="M12 34 L24 10 L36 34"></path>
  <line x1="16" y1="28" x2="32" y2="28"></line>
</svg>
"""
    return """
<svg viewBox="0 0 48 48" aria-hidden="true">
  <circle cx="24" cy="15" r="7"></circle>
  <path d="M12 36 C16 28, 32 28, 36 36"></path>
  <line x1="24" y1="22" x2="24" y2="31"></line>
</svg>
"""


def normalize_timeline_event(event) -> dict:
    if isinstance(event, dict):
        return {
            "year": event.get("year", ""),
            "title": event.get("title", event.get("headline", "")),
            "description": event.get("description", event.get("summary", "")),
            "type": event.get("type", ""),
        }

    text = str(event or "").strip()
    if not text:
        return {"year": "", "title": "Unrecorded event", "description": "", "type": ""}

    head, sep, tail = text.partition(", ")
    if sep:
        return {"year": "", "title": head, "description": tail, "type": ""}
    return {"year": "", "title": text, "description": "", "type": ""}


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
        <div class="status-kicker">Curator companion</div>
        <div class="status-line">{esc(title)}</div>
        <div class="status-subline">{esc(subtitle)}</div>
    </div>
    <div class="status-side">
        <div class="mode-chip">Active curatorial lens</div>
        <div class="mode-name">{esc(curator_mode)}</div>
        <div class="mode-desc">{esc(mode["tagline"])}</div>
        <div class="status-tags">
            <div class="status-tag">5 halls</div>
            <div class="status-tag">One impossible premise</div>
            <div class="status-tag">Move room to room</div>
        </div>
    </div>
</div>
"""


def visitor_title_from_payload(visitor_name: str, visitor_year: str, curator_mode: str) -> str:
    mode_titles = {
        "Anthropology": "Explorer of impossible worlds",
        "Mythic": "Bearer of impossible myths",
        "Imperial Archive": "Archivist of impossible empires",
        "Melancholy": "Keeper of impossible rooms",
    }
    if visitor_year and str(visitor_year).isdigit():
        year_value = int(visitor_year)
        if year_value >= 2400:
            return "Witness from the far future"
        if year_value <= 1900:
            return "Time-displaced museum guest"
    return mode_titles.get(curator_mode, "Explorer of impossible worlds")


def issue_ticket_number(visitor_name: str, visitor_year: str, museum_name: str) -> str:
    seed = f"{visitor_name}|{visitor_year}|{museum_name}".encode("utf-8")
    digest = hashlib.sha1(seed).hexdigest().upper()
    return f"IM-{digest[:4]}-{digest[4:8]}"


def visit_date_label() -> str:
    return datetime.now().strftime("%d %b %Y")


def build_entry_ticket_preview(visitor_name: str = "", visitor_year: str = "", curator_mode: str = "Anthropology") -> str:
    safe_name = (visitor_name or "").strip() or "Future Guest"
    safe_year = (visitor_year or "").strip() or "2026"
    museum_name = "Infinite Museum of Impossible Worlds"
    ticket_title = visitor_title_from_payload(safe_name, safe_year, curator_mode)
    ticket_number = issue_ticket_number(safe_name, safe_year, museum_name)
    return f"""
<div class="museum-ticket-preview">
    <div class="museum-ticket-body">
        <div class="museum-ticket-kicker">Museum Admission Pass</div>
        <div class="museum-ticket-title">Admit One: <span id="landing-visitor-name">{esc(safe_name)}</span></div>
        <div class="museum-ticket-subtitle">Traveller from the Year <span id="landing-visitor-year">{esc(safe_year)}</span></div>
        <div class="museum-ticket-meta">
            <div class="museum-ticket-stat">
                <div class="museum-ticket-stat-label">Ticket number</div>
                <div class="museum-ticket-stat-value" id="landing-ticket-number">{esc(ticket_number)}</div>
            </div>
            <div class="museum-ticket-stat">
                <div class="museum-ticket-stat-label">Date of visit</div>
                <div class="museum-ticket-stat-value" id="landing-visit-date">{esc(visit_date_label())}</div>
            </div>
            <div class="museum-ticket-stat">
                <div class="museum-ticket-stat-label">Museum name</div>
                <div class="museum-ticket-stat-value">{esc(museum_name)}</div>
            </div>
            <div class="museum-ticket-stat">
                <div class="museum-ticket-stat-label">Imaginative title</div>
                <div class="museum-ticket-stat-value" id="landing-ticket-title">{esc(ticket_title)}</div>
            </div>
            <div class="museum-ticket-stat">
                <div class="museum-ticket-stat-label">Complexity seal</div>
                <div class="museum-ticket-stat-value">Pending world generation</div>
            </div>
        </div>
        <div class="museum-ticket-footer">
            <div class="museum-ticket-copy">Access granted to the World of Imagination.</div>
            <div class="museum-ticket-qr" aria-hidden="true"></div>
        </div>
    </div>
    <div class="museum-ticket-ribbon">Stamped for a journey through impossible halls</div>
</div>
"""


def build_journey_path_html(active_step: int = 0) -> str:
    steps = [
        ("Identity Discovered", "The museum learns who is entering today."),
        ("Ticket Created", "Your pass is printed and the seal is prepared."),
        ("Portal Opened", "The first impossible room begins to answer back."),
        ("Museum Journey Begins", "The halls unlock and the exhibition takes form."),
    ]
    cards = []
    for index, (title, copy) in enumerate(steps, start=1):
        state = "is-idle"
        if active_step >= index:
            state = "is-complete"
        elif active_step + 1 == index:
            state = "is-active"
        if active_step == 0 and index == 1:
            state = "is-active"
        cards.append(
            f"""
<div class="journey-stop {state}">
    <div class="journey-stop-index">Stage {index:02d}</div>
    <div class="journey-stop-title">{esc(title)}</div>
    <div class="journey-stop-copy">{esc(copy)}</div>
</div>
"""
        )
    return f"""
<div class="journey-rail">
    <div class="journey-rail-kicker">Visitor Path</div>
    <div class="journey-rail-grid">{''.join(cards)}</div>
</div>
"""


def build_share_card(state: dict) -> str:
    state = state or {}
    world_bible = state.get("world_bible") or {}
    if not world_bible:
        return "<div class='empty-state'>Generate a museum first to compose a share plaque.</div>"

    artifacts = (state.get("artifacts") or {}).get("artifacts") or []
    timeline = (state.get("timeline") or {}).get("events") or []
    lead_event_data = normalize_timeline_event(timeline[0]) if timeline else {"title": "No recorded turning point yet."}
    museum_name = world_bible.get("museum_name", "Infinite Museum")
    summary = world_bible.get("summary") or world_bible.get("tagline") or "An impossible civilization preserved in one continuous museum."
    lead_artifact = artifacts[0].get("name", "No artifact catalogued yet.") if artifacts else "No artifact catalogued yet."
    lead_event = lead_event_data.get("title") or lead_event_data.get("description") or "No recorded turning point yet."
    taboo = world_bible.get("taboo", "No absolute taboo recorded yet.")

    return f"""
<div class="share-card">
    <div class="share-card-kicker">Share Plaque</div>
    <div class="share-card-title">{esc(museum_name)}</div>
    <div class="share-card-summary">{esc(summary)}</div>
    <div class="share-card-grid">
        <div class="share-card-stat">
            <div class="share-card-label">Premise</div>
            <div class="share-card-value">{esc(state.get("concept", ""))}</div>
        </div>
        <div class="share-card-stat">
            <div class="share-card-label">Government</div>
            <div class="share-card-value">{esc(world_bible.get("government", "-"))}</div>
        </div>
        <div class="share-card-stat">
            <div class="share-card-label">Artifact to remember</div>
            <div class="share-card-value">{esc(lead_artifact)}</div>
        </div>
        <div class="share-card-stat">
            <div class="share-card-label">Turning point</div>
            <div class="share-card-value">{esc(lead_event)}</div>
        </div>
        <div class="share-card-stat">
            <div class="share-card-label">Absolute taboo</div>
            <div class="share-card-value">{esc(taboo)}</div>
        </div>
        <div class="share-card-stat">
            <div class="share-card-label">Visual motif</div>
            <div class="share-card-value">{esc(first_item(world_bible.get("visual_motifs"), "No motif recorded yet."))}</div>
        </div>
    </div>
</div>
"""


def build_share_payload(state: dict) -> dict:
    state = state or {}
    world_bible = state.get("world_bible") or {}
    artifacts = (state.get("artifacts") or {}).get("artifacts") or []
    premise = state.get("concept") or world_bible.get("core_premise") or ""
    visitor_name = state.get("visitor_name", "")
    visitor_year = state.get("visitor_year", "")
    museum_name = world_bible.get("museum_name", "Infinite Museum")
    complexity = state.get("complexity") or {}
    return {
        "museum_name": museum_name,
        "tagline": world_bible.get("tagline", ""),
        "premise": premise,
        "visitor_name": visitor_name,
        "visitor_year": visitor_year,
        "visitor_title": visitor_title_from_payload(visitor_name, visitor_year, state.get("curator_mode", "Anthropology")),
        "ticket_number": issue_ticket_number(visitor_name, visitor_year, museum_name),
        "visit_date": visit_date_label(),
        "government": world_bible.get("government", "-"),
        "artifact_name": artifacts[0].get("name", "No artifact catalogued yet.") if artifacts else "No artifact catalogued yet.",
        "turning_point": first_item(world_bible.get("historical_anchors"), "No turning point recorded yet."),
        "taboo": world_bible.get("taboo", "No absolute taboo recorded yet."),
        "visual_motif": first_item(world_bible.get("visual_motifs"), "No visual motif recorded yet."),
        "complexity_score": complexity.get("score", ""),
        "complexity_band": complexity.get("band", ""),
        "aura": world_aura(world_bible),
    }


def build_audio_guide(state: dict | None = None) -> str:
    state = state or {}
    world_bible = state.get("world_bible") or {}
    museum_name = world_bible.get("museum_name", "Infinite Museum of Impossible Worlds")
    title = f"Audio Guide: {museum_name}" if world_bible else "Curator audio guide"
    copy = (
        "Press play to hear a short guide for the hall you are viewing. The text changes as you move through the museum."
        if world_bible
        else "Generate a world first. Then the guide will speak for the active hall."
    )
    hall = "Lobby"
    return f"""
<div class="museum-audio-guide">
    <div class="museum-audio-copyblock">
        <div class="museum-audio-kicker">Curator audio guide</div>
        <div class="museum-audio-title" id="museum-audio-title">{esc(title)}</div>
        <div class="museum-audio-copy" id="museum-audio-copy">{esc(copy)}</div>
    </div>
    <div class="museum-audio-controls">
        <div class="museum-audio-hall">Active hall: <span id="museum-audio-hall">{esc(hall)}</span></div>
        <div class="museum-audio-button-row">
            <button class="museum-action-btn" type="button" data-audio-guide-toggle="true">Play Guide</button>
            <button class="museum-secondary-btn" type="button" data-audio-guide-stop="true">Stop</button>
        </div>
        <div class="museum-audio-meter" aria-hidden="true">
            <span></span><span></span><span></span><span></span>
        </div>
        <div class="museum-audio-status" id="museum-audio-status">Ready</div>
    </div>
</div>
"""


def build_museum_header(state: dict | None = None, share_ready: bool = False) -> str:
    state = state or {}
    world_bible = state.get("world_bible") or {}
    title = world_bible.get("museum_name", "Infinite Museum of Impossible Worlds")
    tagline = world_bible.get("tagline", "Every idea creates a civilization. Every civilization leaves artifacts.")
    visitor_name = (state.get("visitor_name") or "").strip()
    visitor_year = (state.get("visitor_year") or "").strip()
    aura = world_aura(world_bible) if world_bible else "default"
    complexity_html = build_complexity_badge(state.get("complexity"))
    button_html = ""
    if world_bible:
        payload = json.dumps(build_share_payload(state))
        hidden_attr = "" if share_ready else " hidden"
        button_html = (
            f"<div class='museum-header-actions'>"
            f"<button class='museum-secondary-btn museum-ticket-btn' type='button' data-share-ticket='true' data-ticket-payload='{esc_attr(payload)}'{hidden_attr}>Share My Ticket</button>"
            f"<button class='museum-action-btn museum-ticket-btn' type='button' data-download-ticket='true' data-ticket-payload='{esc_attr(payload)}'{hidden_attr}>Download Ticket</button>"
            f"<button class='museum-action-btn museum-header-share' type='button' data-share-world='true' "
            f"data-share-payload='{esc_attr(payload)}'{hidden_attr}>Share This World</button>"
            f"</div>"
        )

    visitor_html = ""
    if visitor_name or visitor_year:
        visitor_line = visitor_name or "Unnamed visitor"
        if visitor_year:
            visitor_line += f" • Arrived from {visitor_year}"
        visitor_html = f"<div class='museum-visitor-pass'>Admission issued to {esc(visitor_line)}</div>"

    return f"""
<div class="museum-header-band" data-world-aura-source="{esc_attr(aura)}">
    <div class="museum-header-identity">
        <div class="museum-world-emblem">{emblem_svg(world_bible) if world_bible else emblem_svg({})}</div>
        <div>
        <div class="museum-title">{esc(title)}</div>
        <div class="museum-tagline">{esc(tagline)}</div>
        {visitor_html}
        </div>
    </div>
    {complexity_html}
    {button_html}
</div>
"""


def build_lobby_html(world_bible: dict, complexity: dict | None = None, curator_notes: dict | None = None) -> str:
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
{type_text("Orientation gallery", "section-heading", 14)}
<div class="lobby-grid">{stat_html}</div>
{build_curator_notes_html(curator_notes)}
{type_text(world_bible.get("summary", ""), "lobby-summary", 10)}
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
        <div class="lobby-label" style="margin-top:16px">Complexity seal</div>
        <p>{esc(str((complexity or {}).get("score", "Pending")))} {esc((complexity or {}).get("band", ""))}</p>
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
            image_src = featured.get("image_url") or _artifact_image_src(featured.get("image_path")) or ""
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

    hall_intro = type_text("Artifacts hall", "section-heading", 14)
    for artifact in data.get("artifacts", []):
        tags = "".join(f"<span class='artifact-tag'>{esc(tag)}</span>" for tag in artifact.get("curator_tags", []))
        cards.append(
            f"""
<div class="artifact-card">
    <div class="artifact-kicker">Catalogued relic</div>
    {type_text(artifact.get("name", ""), "artifact-name", 12)}
    <div class="artifact-meta">{esc(artifact.get("era", ""))} | {esc(artifact.get("material", ""))}</div>
    <div class="artifact-tag-row">{tags}</div>
    <div class="artifact-desc">{esc(artifact.get("description", ""))}</div>
    <div class="artifact-significance">{esc(artifact.get("significance", ""))}</div>
</div>
"""
        )
    return hall_intro + featured_html + "".join(cards)


def _artifact_image_src(image_path: str | None) -> str:
    if not image_path:
        return ""

    path = str(image_path).strip()
    if not path:
        return ""

    if path.startswith(("http://", "https://", "/gradio_api/file=", "/file=")):
        return path

    resolved = Path(path).resolve()
    resolved_text = str(resolved).replace("\\", "/")
    return f"/gradio_api/file={quote(resolved_text, safe='/:')}"


def build_timeline_html(data: dict) -> str:
    if not data or "events" not in data:
        return "<div class='empty-state'>The archivists are still arranging the chronology.</div>"

    cards = []
    intro = type_text("Timeline hall", "section-heading", 14)
    for raw_event in data.get("events", []):
        event = normalize_timeline_event(raw_event)
        cards.append(
            f"""
<div class="timeline-card">
    <div class="timeline-year">{esc(event.get("year", ""))}</div>
    <div>
        {type_text(event.get("title", ""), "timeline-title", 12)}
        <div class="timeline-desc">{esc(event.get("description", ""))}</div>
        <div class="timeline-type">{esc(event.get("type", ""))}</div>
    </div>
</div>
"""
        )
    return intro + "".join(cards)


def build_newspaper_html(data: dict) -> str:
    if not data or "headline" not in data:
        return "<div class='empty-state'>The presses have not finished tonight's edition.</div>"

    return f"""
<div class="newspaper-shell">
    <div class="paper-kicker">Printed for the morning crowd</div>
    {type_text(data.get("newspaper_name", "The Chronicle"), "newspaper-name", 12)}
    <div class="newspaper-meta">{esc(data.get("date", ""))} | {esc(data.get("weather", ""))}</div>
    {type_text(data.get("headline", ""), "newspaper-headline", 12)}
    <div class="newspaper-columns">
        <div class="newspaper-column-block">
            <div class="newspaper-body">{esc(data.get("headline_body", ""))}</div>
        </div>
        <div class="newspaper-column-block">
            <div class="newspaper-secondary-headline">{esc(data.get("secondary_headline", ""))}</div>
            <div class="newspaper-secondary-body">{esc(data.get("secondary_body", ""))}</div>
        </div>
    </div>
    <div class="newspaper-ad">{esc(data.get("advertisement", ""))}</div>
</div>
"""


def build_visitor_book_html(data: dict) -> str:
    if not data or "entry" not in data:
        return "<div class='empty-state'>The visitor's book remains unopened.</div>"

    return f"""
<div class="visitor-book">
    <div class="visitor-kicker">Final testimony</div>
    {type_text(f'"{data.get("entry", "")}"', "visitor-entry", 11)}
    <div class="visitor-signed">{esc(data.get("signed", ""))}</div>
</div>
"""


def build_curator_notes_html(curator_notes: dict | None) -> str:
    curator_notes = curator_notes or {}
    notes = curator_notes.get("notes") or []
    if not notes:
        return """
<div class="curator-notes-shell">
    <div class="curator-notes-head">
        <div class="curator-notes-kicker">Curator Notes</div>
        <div class="curator-notes-score">100 / 100</div>
    </div>
    <div class="curator-notes-headline">The museum is internally coherent so far.</div>
</div>
"""

    cards = []
    for note in notes:
        level = note.get("level", "note")
        cards.append(
            f"""
<div class="curator-note-card curator-note-card--{esc(level)}">
    <div class="curator-note-level">{esc(level.title())}</div>
    <div class="curator-note-title">{esc(note.get("title", "Curator note"))}</div>
    <div class="curator-note-body">{esc(note.get("body", ""))}</div>
</div>
"""
        )

    return f"""
<div class="curator-notes-shell">
    <div class="curator-notes-head">
        <div>
            <div class="curator-notes-kicker">Curator Notes</div>
            <div class="curator-notes-headline">{esc(curator_notes.get("headline", "A few tensions were detected."))}</div>
        </div>
        <div class="curator-notes-score">{esc(str(curator_notes.get("consistency_score", 100)))} / 100</div>
    </div>
    <div class="curator-notes-grid">
        {''.join(cards)}
    </div>
</div>
"""


def build_complexity_badge(complexity: dict | None) -> str:
    complexity = complexity or {}
    score = complexity.get("score")
    band = complexity.get("band", "Emergent")
    if score is None:
        return ""
    return f"""
<div class="museum-complexity-badge">
    <div class="museum-complexity-kicker">World complexity</div>
    <div class="museum-complexity-score">{esc(str(score))}</div>
    <div class="museum-complexity-band">{esc(band)}</div>
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


def build_landing_html(curator_mode: str) -> str:
    mode = CURATOR_MODES.get(curator_mode, CURATOR_MODES["Anthropology"])
    return f"""
<div class="admission-welcome">
    <div class="admission-kicker">Welcome Chamber</div>
    <div class="admission-title">Welcome To The World Of Imagination</div>
    <div class="admission-copy">Before you enter, the museum asks for one small record. Tell us your name and the year you come from. We will stamp your visit into the world you create.</div>
    <div class="admission-rail">
        <div class="admission-chip">One visitor identity</div>
        <div class="admission-chip">One impossible world</div>
        <div class="admission-chip">One museum ticket to carry out</div>
    </div>
</div>
<div class="landing-shell">
    <div class="landing-floating-fragments" aria-hidden="true"><span></span><span></span><span></span></div>
    <div class="landing-grid">
            <div class="landing-copy">
                <div class="landing-kicker">Infinite Museum</div>
                <div class="landing-title">Build An Impossible World</div>
            <div class="landing-subtitle">Type one idea. We will turn it into a museum world.</div>
                <div class="landing-lead">{esc(mode["tagline"])}</div>
            <div class="landing-plaque-row">
                <div class="landing-plaque">
                    <div class="landing-plaque-label">Mode</div>
                    <div class="landing-plaque-value">{esc(curator_mode)}</div>
                </div>
                <div class="landing-plaque">
                    <div class="landing-plaque-label">Inside</div>
                    <div class="landing-plaque-value">Lobby, artifacts, timeline, newspaper, and visitor book.</div>
                </div>
                <div class="landing-plaque">
                    <div class="landing-plaque-label">Focus</div>
                    <div class="landing-plaque-value">{esc(mode["plaque"])}</div>
                </div>
            </div>
            <div class="landing-cta-copy">Keep the idea simple. After your ticket is stamped, the museum opens from the lobby and begins calling you by name.</div>
        </div>
        <div class="landing-art" aria-hidden="true">
            <div class="landing-skyline"></div>
            <div class="landing-dome"></div>
            <div class="landing-steps"></div>
            <div class="landing-pillars"><span></span><span></span><span></span><span></span><span></span></div>
            <div class="landing-caption">
                <span>Atmospheric entrance rendering</span>
                <span>Impossible Civilizations Archive</span>
            </div>
        </div>
    </div>
</div>
"""


def build_map_html(active_room: str, completed_rooms: list[str]) -> str:
    completed = set(completed_rooms)
    active = active_room if active_room in ROOM_LAYOUT else "lobby"
    cards = []
    for index, (room_id, title, kicker, copy) in enumerate(ROOMS, start=1):
        state = "state-idle"
        if room_id in completed:
            state = "state-complete"
        if room_id == active:
            state = "state-active"
        cards.append(
            f"""
<div class="museum-room museum-room--rail {state}" data-hall="{esc(title)}" data-room-id="{esc(room_id)}" role="button" tabindex="0" aria-label="Open {esc(title)} hall" onclick="window.museumNavigate && window.museumNavigate(this)" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault(); window.museumNavigate && window.museumNavigate(this);}}">
    <div class="museum-room-kicker">Hall {index:02d}</div>
    <div class="museum-room-sigil">{hall_sigil(room_id)}</div>
    <div class="museum-room-title">{esc(title)}</div>
    <div class="museum-room-copy">{esc(copy)}</div>
</div>
"""
        )

    active_title = next(room[1] for room in ROOMS if room[0] == active)
    return f"""
<div class='museum-map museum-nav-rail' data-active-room='{esc(active)}'>
    <div class='museum-nav-header'>
        <div class='museum-visitor-caption' id='museum-visitor-caption'>Currently in {esc(active_title)}</div>
        <div class='museum-visitor-label'>Curator rail</div>
    </div>
    <div class='museum-nav-stack'>
        {''.join(cards)}
    </div>
</div>
"""


def build_loading_html(title: str, body: str, step: int, total: int, next_hall: str) -> str:
    journey_stage = min(4, max(1, step))
    return f"""
<div class="loading-card">
    <div>
        <div class="loading-kicker">Museum in progress</div>
        <div class="loading-title">{esc(title)}</div>
        <div class="loading-copy">{esc(body)}</div>
    </div>
    <div>
        {build_journey_path_html(journey_stage)}
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


def build_room_stage(state: dict | None = None) -> str:
    state = state or {}
    world_bible = state.get("world_bible") or {}
    artifacts = (state.get("artifacts") or {}).get("artifacts") or []
    timeline = (state.get("timeline") or {}).get("events") or []
    lead_timeline_event = normalize_timeline_event(timeline[0]) if timeline else {"title": "The historical sequence is still dark.", "description": "Chronology will unfurl across the walls when the archive opens."}
    newspaper = state.get("newspaper") or {}
    visitor_book = state.get("visitor_book") or {}

    museum_name = world_bible.get("museum_name", "Infinite Museum")
    tagline = world_bible.get("tagline", "An impossible civilization waiting to take architectural form.")
    artifact_name = artifacts[0].get("name", "Uncatalogued ceremonial object") if artifacts else "Uncatalogued ceremonial object"
    artifact_significance = artifacts[0].get("significance", "Its significance will be revealed once the vault opens.") if artifacts else "Its significance will be revealed once the vault opens."
    timeline_title = lead_timeline_event.get("title") or "The historical sequence is still dark."
    timeline_desc = lead_timeline_event.get("description") or "Chronology will unfurl across the walls when the archive opens."
    paper_name = newspaper.get("newspaper_name", "Morning Edition Pending")
    paper_headline = newspaper.get("headline", "No headline has survived the pressroom yet.")
    visitor_line = visitor_book.get("entry", "No visitor has left a testimony yet.")
    visual_motif = first_item(world_bible.get("visual_motifs"), "No visual motif recorded yet.")
    taboo = world_bible.get("taboo", "No taboo recorded yet.")
    concept = state.get("concept") or world_bible.get("summary") or "An impossible civilization is taking shape."

    lobby_guide = f"Welcome to {museum_name}. This world starts with one core idea: {concept}. In the lobby you can see the rule, social order, and everyday life of the world."
    artifact_guide = f"This hall shows {artifact_name}. {artifact_significance} It helps explain what this world values and how people live inside it."
    timeline_guide = f"This hall is built around {timeline_title}. {timeline_desc} It shows the key turns that shaped the world."
    newspaper_guide = f"In this hall, {paper_name} leads with: {paper_headline} It shows how the world spoke about itself in public."
    visitor_guide = f"This last hall gives one personal voice. {visitor_line} It helps bring the world down to a human level."

    return f"""
<div class="museum-room-stage" data-active-room="lobby">
    <div class="museum-room-scene museum-room-scene--lobby" data-guide-room="Lobby" data-guide-title="{esc_attr(museum_name)}" data-guide-copy="{esc_attr(lobby_guide)}">
        <div class="museum-room-spotlight museum-room-spotlight--center"></div>
        <div class="museum-room-glow"></div>
        <div class="museum-room-scene-copy">
            <div class="museum-room-scene-kicker">Hall 01</div>
            {type_text(museum_name, "museum-room-scene-title", 12)}
            {type_text(tagline, "museum-room-scene-text", 10)}
        </div>
        <div class="museum-room-gallery">
            <div class="museum-room-artwall">
                <div class="museum-room-frame"><div class="museum-room-canvas museum-room-canvas--tall"></div></div>
                <div class="museum-room-frame"><div class="museum-room-canvas"></div></div>
            </div>
            <div class="museum-room-plinth-zone">
                <div class="museum-room-plinth"></div>
                <div class="museum-room-object museum-room-object--orb"></div>
            </div>
        </div>
        <div class="museum-room-wall-label">
            <div class="museum-room-label-title">Orientation Plaque</div>
            {esc(visual_motif)}
        </div>
    </div>
    <div class="museum-room-scene museum-room-scene--artifacts" data-guide-room="Artifacts" data-guide-title="{esc_attr(artifact_name)}" data-guide-copy="{esc_attr(artifact_guide)}">
        <div class="museum-room-spotlight museum-room-spotlight--left"></div>
        <div class="museum-room-spotlight museum-room-spotlight--right"></div>
        <div class="museum-room-glow"></div>
        <div class="museum-room-scene-copy">
            <div class="museum-room-scene-kicker">Hall 02</div>
            {type_text(artifact_name, "museum-room-scene-title", 12)}
            {type_text(artifact_significance, "museum-room-scene-text", 10)}
        </div>
        <div class="museum-room-gallery">
            <div class="museum-room-artwall">
                <div class="museum-room-frame"><div class="museum-room-canvas"></div></div>
                <div class="museum-room-frame"><div class="museum-room-canvas museum-room-canvas--tall"></div></div>
            </div>
            <div class="museum-room-plinth-zone">
                <div class="museum-room-plinth"></div>
                <div class="museum-room-object museum-room-object--column"></div>
            </div>
        </div>
        <div class="museum-room-wall-label">
            <div class="museum-room-label-title">Collection Note</div>
            {esc(world_bible.get("government", "Government still being deciphered."))}
        </div>
    </div>
    <div class="museum-room-scene museum-room-scene--timeline" data-guide-room="Timeline" data-guide-title="{esc_attr(timeline_title)}" data-guide-copy="{esc_attr(timeline_guide)}">
        <div class="museum-room-spotlight museum-room-spotlight--center"></div>
        <div class="museum-room-glow"></div>
        <div class="museum-room-scene-copy">
            <div class="museum-room-scene-kicker">Hall 03</div>
            {type_text(timeline_title, "museum-room-scene-title", 12)}
            {type_text(timeline_desc, "museum-room-scene-text", 10)}
        </div>
        <div class="museum-room-gallery">
            <div class="museum-room-artwall">
                <div class="museum-room-frame"><div class="museum-room-canvas museum-room-canvas--tall"></div></div>
                <div class="museum-room-frame"><div class="museum-room-canvas museum-room-canvas--tall"></div></div>
            </div>
            <div class="museum-room-plinth-zone">
                <div class="museum-room-plinth"></div>
                <div class="museum-room-object museum-room-object--book"></div>
            </div>
        </div>
        <div class="museum-room-wall-label">
            <div class="museum-room-label-title">Archive Strip</div>
            {esc(first_item(world_bible.get("historical_anchors"), "Historical anchors are still being pinned to the wall."))}
        </div>
    </div>
    <div class="museum-room-scene museum-room-scene--newspaper" data-guide-room="Newspaper" data-guide-title="{esc_attr(paper_name)}" data-guide-copy="{esc_attr(newspaper_guide)}">
        <div class="museum-room-spotlight museum-room-spotlight--right"></div>
        <div class="museum-room-glow"></div>
        <div class="museum-room-scene-copy">
            <div class="museum-room-scene-kicker">Hall 04</div>
            {type_text(paper_name, "museum-room-scene-title", 12)}
            {type_text(paper_headline, "museum-room-scene-text", 10)}
        </div>
        <div class="museum-room-gallery">
            <div class="museum-room-artwall">
                <div class="museum-room-frame"><div class="museum-room-canvas"></div></div>
                <div class="museum-room-frame"><div class="museum-room-canvas"></div></div>
            </div>
            <div class="museum-room-plinth-zone">
                <div class="museum-room-plinth"></div>
                <div class="museum-room-object museum-room-object--desk"></div>
            </div>
        </div>
        <div class="museum-room-wall-label">
            <div class="museum-room-label-title">Press Cabinet</div>
            {esc(taboo)}
        </div>
    </div>
    <div class="museum-room-scene museum-room-scene--visitor" data-guide-room="Visitor's Book" data-guide-title="Visitor's Book" data-guide-copy="{esc_attr(visitor_guide)}">
        <div class="museum-room-spotlight museum-room-spotlight--center"></div>
        <div class="museum-room-glow"></div>
        <div class="museum-room-scene-copy">
            <div class="museum-room-scene-kicker">Hall 05</div>
            {type_text("Visitor's Book", "museum-room-scene-title", 12)}
            {type_text(visitor_line, "museum-room-scene-text", 10)}
        </div>
        <div class="museum-room-gallery">
            <div class="museum-room-artwall">
                <div class="museum-room-frame"><div class="museum-room-canvas museum-room-canvas--tall"></div></div>
                <div class="museum-room-frame"><div class="museum-room-canvas"></div></div>
            </div>
            <div class="museum-room-plinth-zone">
                <div class="museum-room-plinth"></div>
                <div class="museum-room-object museum-room-object--book"></div>
            </div>
        </div>
        <div class="museum-room-wall-label">
            <div class="museum-room-label-title">Closing Note</div>
            {esc(world_bible.get("daily_life", "A final personal voice will settle the room once the exhibition opens."))}
        </div>
    </div>
</div>
"""


def build_shell_intro() -> str:
    return """
<div class="museum-section-intro">
    <div class="museum-section-kicker">Hall Navigation</div>
    <div class="museum-section-title">Move Through The Museum</div>
    <div class="museum-section-copy">Start in the lobby, then move hall by hall. Use the audio guide if you want, and download the share card only when you need it.</div>
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


def build_museum_state(
    concept: str,
    curator_mode: str,
    world_bible: dict,
    visitor_name: str = "",
    visitor_year: str = "",
    artifacts=None,
    timeline=None,
    newspaper=None,
    visitor_book=None,
    complexity=None,
    curator_notes=None,
) -> dict:
    return {
        "concept": concept,
        "curator_mode": curator_mode,
        "visitor_name": visitor_name,
        "visitor_year": visitor_year,
        "guided_concept": format_concept(concept, curator_mode),
        "world_bible": world_bible or {},
        "artifacts": artifacts or {},
        "featured_image": None,
        "timeline": timeline or {},
        "newspaper": newspaper or {},
        "visitor_book": visitor_book or {},
        "complexity": complexity or {},
        "curator_notes": curator_notes or {},
        "ambassador_history": [],
        "ambassador_turns": 0,
    }


def default_state() -> dict:
    return build_museum_state("", "Anthropology", {})


def show_museum_shell():
    return gr.update(visible=False), gr.update(visible=True)


def show_landing_page():
    return gr.update(visible=True), gr.update(visible=False)


def build_ambassador_seed_message(state: dict) -> str:
    state = state or {}
    world_bible = state.get("world_bible") or {}
    visitor_book = state.get("visitor_book") or {}
    museum_name = world_bible.get("museum_name") or "this impossible world"
    premise = world_bible.get("core_premise") or "life here follows one impossible rule"
    witness = visitor_book.get("entry") or "A private testimony is still being gathered."
    witness = " ".join(str(witness).split())[:180]
    return (
        f"I am speaking from inside {museum_name}. {premise}. "
        f"Ask me about daily life, fear, power, ritual, or survival here. "
        f"One local voice says: {witness}"
    )


def reset_ambassador_state(state: dict) -> dict:
    state = state or default_state()
    state["ambassador_history"] = [{"role": "assistant", "content": build_ambassador_seed_message(state)}]
    state["ambassador_turns"] = 0
    return state


def build_ambassador_chat_state(state: dict):
    state = state or default_state()
    history = state.get("ambassador_history") or []
    return history or [{"role": "assistant", "content": "Open a world first, then a local voice will answer from inside it."}]


def refresh_world_analysis(state: dict) -> dict:
    state = state or default_state()
    world_bible = state.get("world_bible") or {}
    artifacts = state.get("artifacts") or {}
    timeline = state.get("timeline") or {}
    newspaper = state.get("newspaper") or {}
    visitor_book = state.get("visitor_book") or {}

    if artifacts:
        state["artifacts"] = tag_artifacts(artifacts, world_bible)
    state["complexity"] = build_world_complexity_report(world_bible, state.get("artifacts") or {}, timeline)
    state["curator_notes"] = detect_curator_notes(world_bible, state.get("artifacts") or {}, timeline, newspaper, visitor_book)
    return state


def ask_ambassador(state: dict, question: str):
    state = state or default_state()
    curator_mode = state.get("curator_mode") or "Anthropology"
    question = (question or "").strip()

    if not (state.get("world_bible") or {}):
        return (
            build_status_panel("Open a museum first", "Generate a civilization before asking someone who lives inside it.", curator_mode),
            build_ambassador_chat_state(state),
            state,
            gr.update(value=""),
        )

    if not question:
        return (
            build_status_panel("Ask the ambassador something", "Try a question about daily life, taboo, government, ritual, or fear.", curator_mode),
            build_ambassador_chat_state(state),
            state,
            gr.update(value=""),
        )

    history = list(state.get("ambassador_history") or [])
    if not history:
        state = reset_ambassador_state(state)
        history = list(state.get("ambassador_history") or [])

    turns = int(state.get("ambassador_turns") or 0)
    if turns >= 3:
        return (
            build_status_panel("Ambassador conversation complete", "This local voice has answered three questions. Regenerate the Visitor's Book for a new witness.", curator_mode),
            history,
            state,
            gr.update(value=""),
        )

    history.append({"role": "user", "content": question})
    reply = generate_world_ambassador_reply(
        question,
        state.get("world_bible") or {},
        state.get("visitor_book") or {},
        history[:-1],
    ).strip()
    history.append({"role": "assistant", "content": reply or "The ambassador pauses, then lets the silence stand in place of an answer."})
    state["ambassador_history"] = history
    state["ambassador_turns"] = turns + 1

    return (
        build_status_panel("Ambassador responded", f"Question {state['ambassador_turns']} of 3 has been recorded in this hall.", curator_mode),
        history,
        state,
        gr.update(value=""),
    )


def generate_artifact_image_action(state: dict, artifact_index: int):
    curator_mode = (state or {}).get("curator_mode") or "Anthropology"
    state = state or default_state()
    artifacts_payload = state.get("artifacts") or {}
    world_bible = state.get("world_bible") or {}
    artifacts = artifacts_payload.get("artifacts") if isinstance(artifacts_payload, dict) else None
    print(
        f"[IMAGE UI] Artifact button clicked | index={artifact_index} "
        f"| has_world={bool(world_bible)} | artifact_count={len(artifacts) if artifacts else 0}"
    )

    if not world_bible or not artifacts:
        print("[IMAGE UI] Aborting because museum state is incomplete")
        return (
            build_status_panel("Open the artifact hall first", "Generate a world and its artifact collection before rendering an exhibit image.", curator_mode),
            gr.update(value=build_artifacts_html({**(artifacts_payload or {}), "featured_image": state.get("featured_image")})),
            state,
        )

    featured_image = generate_featured_artifact_image(world_bible, artifacts_payload, artifact_index)
    state["featured_image"] = featured_image
    print(f"[IMAGE UI] Featured image result keys={sorted(featured_image.keys()) if isinstance(featured_image, dict) else []}")

    if featured_image.get("error"):
        title = "Artifact render failed"
        subtitle = featured_image["error"]
    elif featured_image.get("status") == "disabled":
        title = "Image generation disabled"
        subtitle = "Set MUSEUM_IMAGE_RUNTIME=local or backend to render artifact images."
    elif featured_image.get("status") == "unknown_runtime":
        title = "Unknown image runtime"
        subtitle = "The image engine runtime is not recognized by the museum."
    else:
        title = "Artifact rendered"
        subtitle = f"Created a featured exhibit image for {featured_image.get('artifact_name', 'the selected artifact')}."

    return (
        build_status_panel(title, subtitle, curator_mode),
        gr.update(value=build_artifacts_html({**artifacts_payload, "featured_image": state.get("featured_image")})),
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
            gr.update(value=build_room_stage(state)),
            gr.update(value=build_audio_guide(state)),
            gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
            gr.update(value=build_artifacts_html({**(state.get("artifacts") or {}), "featured_image": state.get("featured_image")})),
            gr.update(value=build_timeline_html(state.get("timeline") or {})),
            gr.update(value=build_newspaper_html(state.get("newspaper") or {})),
            gr.update(value=build_visitor_book_html(state.get("visitor_book") or {})),
            gr.update(value=build_ambassador_chat_state(state)),
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
        state = reset_ambassador_state(state)
        title = "Visitor's Book rerolled"
        subtitle = "A different personal voice has been added to the same world, and the ambassador has changed with it."
    else:
        title = "Unknown hall"
        subtitle = "No changes were made."

    state = refresh_world_analysis(state)

    return (
        build_status_panel(title, subtitle, curator_mode),
        gr.update(value=build_map_html(hall if hall in {"artifacts", "timeline", "newspaper", "visitor"} else "lobby", ["lobby", "artifacts", "timeline", "newspaper", "visitor"])),
        gr.update(value=build_room_stage(state)),
        gr.update(value=build_audio_guide(state)),
        gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
        gr.update(value=build_artifacts_html({**(state.get("artifacts") or {}), "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(state.get("timeline") or {})),
        gr.update(value=build_newspaper_html(state.get("newspaper") or {})),
        gr.update(value=build_visitor_book_html(state.get("visitor_book") or {})),
        gr.update(value=build_ambassador_chat_state(state)),
        state,
    )


def generate_museum(concept: str, curator_mode: str, visitor_name: str, visitor_year: str):
    concept = (concept or "").strip()
    curator_mode = curator_mode or "Anthropology"
    visitor_name = (visitor_name or "").strip()
    visitor_year = (visitor_year or "").strip()

    if not concept:
        yield (
            gr.update(visible=True),
            gr.update(visible=False),
            build_status_panel("Awaiting a world concept", "Write a prompt to open the museum.", curator_mode),
            gr.update(value=build_map_html("lobby", [])),
            gr.update(value=build_museum_header()),
            gr.update(value=build_room_stage()),
            gr.update(value=build_audio_guide()),
            empty_gallery("The museum awaits its first impossible world."),
            empty_gallery("The artifact hall is sealed."),
            empty_gallery("History has not yet been arranged."),
            empty_gallery("No front page has gone to print."),
            empty_gallery("No one has yet signed the visitor's book."),
            [],
            default_state(),
        )
        return

    waiting = "The curatorial staff is preparing this hall."
    guided_concept = format_concept(concept, curator_mode)
    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        build_status_panel("Opening the museum", "We are drafting the world bible and preparing the first gallery.", curator_mode),
        gr.update(value=build_map_html("lobby", [])),
        gr.update(value=build_museum_header({"world_bible": {"museum_name": "Infinite Museum of Impossible Worlds", "tagline": "Preparing a new impossible civilization."}}, share_ready=False)),
        gr.update(value=build_room_stage()),
        gr.update(value=build_audio_guide()),
        gr.update(value=build_loading_html("Drafting the world", "The museum is defining the main rule, social order, and daily life of this civilization.", 1, 5, "Artifacts")),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
        empty_gallery(waiting),
        [],
        default_state(),
    )

    world_bible = generate_world_bible(guided_concept)
    state = build_museum_state(concept, curator_mode, world_bible, visitor_name, visitor_year)
    state = refresh_world_analysis(state)

    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        build_status_panel("Lobby opened", "The civilization has taken shape. The first records are now on display.", curator_mode),
        gr.update(value=build_map_html("artifacts", ["lobby"])),
        gr.update(value=build_museum_header(state, share_ready=False)),
        gr.update(value=build_room_stage(state)),
        gr.update(value=build_audio_guide(state)),
        gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
        gr.update(value=build_loading_html("Excavating the collection", "The museum is cataloguing objects from this civilization and selecting the first exhibit pieces.", 2, 5, "Timeline")),
        empty_gallery("Assembling the official historical record."),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
        [],
        state,
    )

    artifacts = generate_artifacts(guided_concept, world_bible)
    state["artifacts"] = artifacts
    state["featured_image"] = None
    state = refresh_world_analysis(state)
    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        build_status_panel("Artifacts catalogued", "The collection vault has opened. The chronology is being assembled.", curator_mode),
        gr.update(value=build_map_html("timeline", ["lobby", "artifacts"])),
        gr.update(value=build_museum_header(state, share_ready=False)),
        gr.update(value=build_room_stage(state)),
        gr.update(value=build_audio_guide(state)),
        gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": None})),
        gr.update(value=build_loading_html("Restoring the timeline", "The archive is assembling the sequence of events that shaped this world.", 3, 5, "Newspaper")),
        empty_gallery("Preparing the day's newspaper edition."),
        empty_gallery("Opening the final testimony cabinet."),
        [],
        state,
    )

    timeline = generate_timeline(guided_concept, world_bible)
    state["timeline"] = timeline
    state = refresh_world_analysis(state)
    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        build_status_panel("Timeline restored", "The museum now knows how this world rose, changed, and endured.", curator_mode),
        gr.update(value=build_map_html("newspaper", ["lobby", "artifacts", "timeline"])),
        gr.update(value=build_museum_header(state, share_ready=False)),
        gr.update(value=build_room_stage(state)),
        gr.update(value=build_audio_guide(state)),
        gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_loading_html("Printing the newspaper", "The press room is composing a front page from inside the civilization's own point of view.", 4, 5, "Visitor's Book")),
        empty_gallery("Opening the final testimony cabinet."),
        [],
        state,
    )

    newspaper = generate_newspaper(guided_concept, world_bible)
    state["newspaper"] = newspaper
    state = refresh_world_analysis(state)
    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        build_status_panel("Presses running", "A surviving newspaper is now on display beside the official archive.", curator_mode),
        gr.update(value=build_map_html("visitor", ["lobby", "artifacts", "timeline", "newspaper"])),
        gr.update(value=build_museum_header(state, share_ready=False)),
        gr.update(value=build_room_stage(state)),
        gr.update(value=build_audio_guide(state)),
        gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        gr.update(value=build_loading_html("Opening the last page", "The museum is finding one private voice that lived inside this world.", 5, 5, "Final display")),
        [],
        state,
    )

    visitor_book = generate_visitor_book(guided_concept, world_bible)
    state["visitor_book"] = visitor_book
    state = refresh_world_analysis(state)
    state = reset_ambassador_state(state)
    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        build_status_panel("Museum complete", "All five halls are open. The world is ready to be explored.", curator_mode),
        gr.update(value=build_map_html("visitor", ["lobby", "artifacts", "timeline", "newspaper", "visitor"])),
        gr.update(value=build_museum_header(state, share_ready=True)),
        gr.update(value=build_room_stage(state)),
        gr.update(value=build_audio_guide(state)),
        gr.update(value=build_lobby_html(world_bible, state.get("complexity"), state.get("curator_notes"))),
        gr.update(value=build_artifacts_html({**state["artifacts"], "featured_image": state.get("featured_image")})),
        gr.update(value=build_timeline_html(timeline)),
        gr.update(value=build_newspaper_html(newspaper)),
        gr.update(value=build_visitor_book_html(visitor_book)),
        gr.update(value=build_ambassador_chat_state(state)),
        state,
    )


with gr.Blocks(css=CSS, head=APP_HEAD, title="Infinite Museum of Impossible Worlds") as demo:
    museum_state = gr.State(default_state())
    with gr.Column(visible=True) as landing_view:
        with gr.Row(elem_classes=["landing-wrap"]):
            landing_html = gr.HTML(build_landing_html("Anthropology"))
        with gr.Row(elem_classes=["control-shell"]):
            with gr.Column(elem_classes=["control-card"]):
                gr.HTML(
                    """
<div class="control-panel-label">Curator mode</div>
<div class="control-panel-copy">This should feel like stepping up to a museum desk, not filling out a form. Tell us who is arriving, what impossible world you want to open, and let the pass stamp itself into the archive.</div>
"""
                )
                with gr.Row(elem_classes=["admission-card-grid"]):
                    with gr.Column(scale=6):
                        gr.HTML("<div class='admission-form-label'>Choose the curatorial mood for your arrival</div>", elem_classes=["admission-card-copy"])
                        curator_mode = gr.Radio(
                            choices=list(CURATOR_MODES.keys()),
                            value="Anthropology",
                            show_label=False,
                            elem_classes=["mode-radio"],
                        )
                        visitor_name_input = gr.Textbox(
                            label="What should we call you?",
                            placeholder="Enter your name",
                            lines=1,
                            elem_id="visitor-name-input",
                            elem_classes=["admission-input"],
                        )
                        visitor_year_input = gr.Textbox(
                            label="Which year are you visiting us from?",
                            placeholder="For example, 2026",
                            lines=1,
                            elem_id="visitor-year-input",
                            elem_classes=["admission-input"],
                        )
                        concept_input = gr.Textbox(
                            label="What impossible world should the museum open for you?",
                            placeholder="A world where dreams are currency.",
                            lines=3,
                            elem_id="concept-input",
                            elem_classes=["admission-input"],
                        )
                        with gr.Row(elem_classes=["hall-action-row"]):
                            concept_voice_btn = gr.Button("Speak World Idea", elem_classes=["museum-secondary-btn"], elem_id="concept-voice-btn")
                            generate_btn = gr.Button("Begin My Journey →", elem_classes=["enter-btn"], elem_id="begin-journey-btn")
                        journey_preview_html = gr.HTML(build_journey_path_html(0))
                    with gr.Column(scale=5):
                        admission_ticket_html = gr.HTML(build_entry_ticket_preview())

    with gr.Column(visible=False, elem_classes=["museum-shell"]) as museum_view:
        with gr.Row(elem_classes=["museum-topbar"]):
            exit_btn = gr.Button("Back To Entrance", size="sm", elem_classes=["museum-secondary-btn"])

        with gr.Row(elem_classes=["concept-chip-row"]):
            concept_chip_1 = gr.Button("Dreams are taxed and stored in public vaults", elem_classes=["concept-chip-btn"])
            concept_chip_2 = gr.Button("A floating city ruled by tides that remember every oath", elem_classes=["concept-chip-btn"])
            concept_chip_3 = gr.Button("A moon colony where gravity changes by social rank", elem_classes=["concept-chip-btn"])

        with gr.Row(elem_classes=["museum-workspace"]):
            with gr.Column(elem_classes=["museum-sidebar"]):
                map_html = gr.HTML(build_map_html("lobby", []), elem_classes=["map-wrap"])
                status_html = gr.HTML(
                    build_status_panel(
                        "Awaiting a world concept",
                        "Describe an impossible civilization to open the museum.",
                        "Anthropology",
                    ),
                    elem_classes=["status-wrap"],
                )
            with gr.Column(elem_classes=["museum-canvas"]):
                museum_header = gr.HTML(build_museum_header())
                gr.HTML(build_theme_bar(), elem_classes=["theme-wrap"])
                audio_guide_html = gr.HTML(build_audio_guide(), elem_classes=["audio-guide-wrap"])
                shell_intro_html = gr.HTML(build_shell_intro())
                room_stage_html = gr.HTML(build_room_stage())

                with gr.Column(elem_classes=["museum-hall-stack"]):
                    with gr.Group(elem_classes=["museum-hall-panel", "hall-panel--lobby", "is-active"], elem_id="hall-panel-lobby"):
                        gr.HTML(build_panel_header("Hall 01", "Lobby", "Read the governing rule of the civilization, then move sideways through the museum as each room changes the tone around you."))
                        lobby_html = gr.HTML(
                            value="<div class='empty-state'>The museum awaits its first impossible world.</div>",
                            elem_classes=["hall-content"],
                        )
                    with gr.Group(elem_classes=["museum-hall-panel", "hall-panel--artifacts"], elem_id="hall-panel-artifacts"):
                        gr.HTML(build_panel_header("Hall 02", "Artifacts", "This room should feel denser and more tactile, as if the collection is pressing closer around you."))
                        with gr.Row(elem_classes=["hall-action-row"]):
                            artifact_image_btn_1 = gr.Button("Render Artifact 1", size="sm", elem_classes=["museum-secondary-btn"])
                            artifact_image_btn_2 = gr.Button("Render Artifact 2", size="sm", elem_classes=["museum-secondary-btn"])
                            artifact_image_btn_3 = gr.Button("Render Artifact 3", size="sm", elem_classes=["museum-secondary-btn"])
                        regen_artifacts_btn = gr.Button("Regenerate Artifacts", size="sm", elem_classes=["museum-action-btn"])
                        artifacts_html = gr.HTML(
                            value="<div class='empty-state'>The artifact hall is sealed.</div>",
                            elem_classes=["hall-content"],
                        )
                    with gr.Group(elem_classes=["museum-hall-panel", "hall-panel--timeline"], elem_id="hall-panel-timeline"):
                        gr.HTML(build_panel_header("Hall 03", "Timeline", "The room lengthens into chronology here, with the sense that history is wrapping around the walls rather than sitting on a page."))
                        regen_timeline_btn = gr.Button("Regenerate Timeline", size="sm", elem_classes=["museum-action-btn"])
                        timeline_html = gr.HTML(
                            value="<div class='empty-state'>History has not yet been arranged.</div>",
                            elem_classes=["hall-content"],
                        )
                    with gr.Group(elem_classes=["museum-hall-panel", "hall-panel--newspaper"], elem_id="hall-panel-newspaper"):
                        gr.HTML(build_panel_header("Hall 04", "Newspaper", "This room becomes more public and immediate, like stepping under reading lamps into a preserved press chamber."))
                        regen_newspaper_btn = gr.Button("Regenerate Newspaper", size="sm", elem_classes=["museum-action-btn"])
                        newspaper_html = gr.HTML(
                            value="<div class='empty-state'>No front page has gone to print.</div>",
                            elem_classes=["hall-content"],
                        )
                    with gr.Group(elem_classes=["museum-hall-panel", "hall-panel--visitor"], elem_id="hall-panel-visitor"):
                        gr.HTML(build_panel_header("Hall 05", "Visitor's Book", "The final room quiets everything down, letting one voice sit in the space after the institution has finished speaking."))
                        regen_visitor_btn = gr.Button("Regenerate Visitor's Book", size="sm", elem_classes=["museum-action-btn"])
                        visitor_html = gr.HTML(
                            value="<div class='empty-state'>No one has yet signed the visitor's book.</div>",
                            elem_classes=["hall-content"],
                        )
                        gr.HTML(
                            """
<div class="control-panel-label">Tiny World Ambassador</div>
<div class="control-panel-copy">Ask one local resident what this world feels like from the inside. Three questions per visitor, so each answer stays special.</div>
"""
                        )
                        ambassador_chatbot = gr.Chatbot(
                            value=[],
                            type="messages",
                            show_label=False,
                            elem_classes=["ambassador-chat", "museum-ambassador-chat"],
                        )
                        with gr.Row(elem_classes=["hall-action-row"]):
                            ambassador_input = gr.Textbox(
                                placeholder="Ask about daily life, taboo, fear, ritual, or power...",
                                lines=2,
                                show_label=False,
                                elem_id="ambassador-input",
                                elem_classes=["admission-input", "ambassador-input"],
                            )
                            ambassador_voice_btn = gr.Button("Speak Question", elem_classes=["museum-secondary-btn"], elem_id="ambassador-voice-btn")
                            ambassador_send_btn = gr.Button("Ask Ambassador", elem_classes=["museum-action-btn"])
                    gr.HTML("</div>")

        gr.HTML(
            """
<div class="museum-footer">
    Infinite Museum of Impossible Worlds | Small-model worldbuilding | Built for Build Small Hackathon 2026
</div>
"""
        )

    outputs = [
        landing_view,
        museum_view,
        status_html,
        map_html,
        museum_header,
        room_stage_html,
        audio_guide_html,
        lobby_html,
        artifacts_html,
        timeline_html,
        newspaper_html,
        visitor_html,
        ambassador_chatbot,
        museum_state,
    ]

    curator_mode.change(
        fn=lambda mode: build_landing_html(mode),
        inputs=[curator_mode],
        outputs=[landing_html],
    )
    preview_inputs = [visitor_name_input, visitor_year_input, curator_mode]
    preview_updater = lambda name, year, mode: build_entry_ticket_preview(name, year, mode)
    visitor_name_input.input(fn=preview_updater, inputs=preview_inputs, outputs=[admission_ticket_html])
    visitor_year_input.input(fn=preview_updater, inputs=preview_inputs, outputs=[admission_ticket_html])
    curator_mode.change(fn=preview_updater, inputs=preview_inputs, outputs=[admission_ticket_html])

    exit_btn.click(show_landing_page, outputs=[landing_view, museum_view])

    concept_chip_1.click(lambda: gr.update(value="A civilization where dreams are taxed and stored in public vaults."), outputs=[concept_input])
    concept_chip_2.click(lambda: gr.update(value="A floating city ruled by tides that remember every oath."), outputs=[concept_input])
    concept_chip_3.click(lambda: gr.update(value="A moon colony where gravity changes according to social rank."), outputs=[concept_input])

    generate_btn.click(generate_museum, inputs=[concept_input, curator_mode, visitor_name_input, visitor_year_input], outputs=outputs)
    concept_input.submit(generate_museum, inputs=[concept_input, curator_mode, visitor_name_input, visitor_year_input], outputs=outputs)

    hall_outputs = [
        status_html,
        map_html,
        room_stage_html,
        audio_guide_html,
        lobby_html,
        artifacts_html,
        timeline_html,
        newspaper_html,
        visitor_html,
        ambassador_chatbot,
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
    ambassador_outputs = [status_html, ambassador_chatbot, museum_state, ambassador_input]
    ambassador_send_btn.click(ask_ambassador, inputs=[museum_state, ambassador_input], outputs=ambassador_outputs)
    ambassador_input.submit(ask_ambassador, inputs=[museum_state, ambassador_input], outputs=ambassador_outputs)


if __name__ == "__main__":
    demo.launch(allowed_paths=[str(Path("generated_images").resolve())])
