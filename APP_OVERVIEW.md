# Infinite Museum of Impossible Worlds

## What This App Is

Infinite Museum of Impossible Worlds is a cinematic Gradio experience that turns one impossible idea into a full museum visit.

Instead of showing plain text output, the app presents the generated world as a guided museum journey with halls, room transitions, atmospheric visuals, artifact images, and downloadable visitor/share assets.

The app is designed to feel like:

- a museum
- a story experience
- a worldbuilding engine
- a polished hackathon demo

## Core Idea

The visitor gives the app a single impossible-world prompt, such as:

`A world where dreams are currency`

The system expands that into a coherent civilization with:

- a governing premise
- institutions and government
- artifacts
- history
- newspaper coverage
- a personal visitor voice

All of that is presented as a museum with five connected halls.

## Main Visitor Flow

### 1. Entrance Landing

The visitor first enters a premium landing experience with:

- a welcome chamber
- cinematic museum styling
- visitor identity capture
- a live museum admission ticket preview

The landing asks:

- `What should we call you?`
- `Which year are you visiting us from?`
- `What impossible world should the museum open for you?`

This creates a stronger feeling of entering the museum instead of filling out a normal form.

### 2. Ticket And Identity

The app generates a visitor identity layer using:

- visitor name
- visitor year
- museum admission pass
- ticket number
- visit date
- imaginative visitor title

This identity is reused later in:

- the museum header
- ticket export
- share experience

### 3. Museum Generation

After clicking `Begin My Journey`, the app builds the world in stages:

1. World bible
2. Artifact hall
3. Timeline hall
4. Newspaper hall
5. Visitor's book

During this process, the interface shows a museum-style journey path instead of a generic progress bar.

### 4. Museum Exploration

Once generated, the visitor moves through the museum:

- Lobby
- Artifacts
- Timeline
- Newspaper
- Visitor's Book

Each hall has:

- its own room styling
- a panel with generated content
- themed stage visuals
- hall-specific tone

### 5. Artifact Rendering

In the artifacts hall, the visitor can render artifact images on demand.

The app:

- builds an image prompt from the world data
- generates an image locally
- saves the output
- displays it in the featured artifact section

### 6. Export And Sharing

After the museum is complete, the visitor can:

- share the world
- share the museum ticket
- download the museum ticket

## Museum Halls

### Hall 01: Lobby

Purpose:

- introduce the civilization
- establish its rules
- summarize its social order

Typical content:

- government
- capital
- founded date
- currency
- laws of reality
- visual motifs
- daily life
- taboo

### Hall 02: Artifacts

Purpose:

- show physical evidence of the world
- communicate what the civilization values

Typical content:

- artifact name
- era
- material
- description
- significance

Special feature:

- on-demand artifact image generation

### Hall 03: Timeline

Purpose:

- explain how the world developed
- show the major turning points

Typical content:

- dates
- founding events
- social changes
- institutional milestones

### Hall 04: Newspaper

Purpose:

- show how the civilization speaks about itself in public
- create a more immediate and social tone

Typical content:

- newspaper name
- date
- main headline
- body copy
- secondary story
- advertisement

### Hall 05: Visitor's Book

Purpose:

- bring the world down to a personal scale
- end with one human voice

Typical content:

- first-person testimony
- signed voice

## Model And Generation Architecture

The text generation pipeline is role-based.

### Roles

- `world`: generates the core world bible
- `hall`: generates artifacts, timeline, and newspaper
- `guide`: generates the visitor-book style output

### Current Runtime Modes

The app supports:

- `local`
- `hub`
- `llamacpp`

### Current Best Working Setup

For the current Space flow, the strongest setup has been:

- local text generation
- LoRA adapter applied across all text roles
- local artifact image generation
- ZeroGPU-compatible tuning for image rendering

## LoRA Usage

The app supports a fine-tuned LoRA adapter for the museum text generation path.

That means the generated worlds are not just base-model outputs. They carry the style and behavior of the fine-tuned museum model.

The adapter is currently applied for:

- world
- hall
- guide

when running in the appropriate local runtime path.

## Image Generation

Artifact image generation is integrated into the museum rather than generated automatically for every world.

This keeps the experience faster and gives the visitor more control.

### Current Image Flow

1. Visitor clicks `Render Artifact 1`, `2`, or `3`
2. App builds a prompt from:
   - artifact details
   - museum world details
   - motifs
   - world rules
3. Local image model generates the image
4. Image is saved
5. Gradio serves the generated file back into the hall

### Image Model Direction

The app is configured to use:

- `black-forest-labs/FLUX.2-klein-4B`

with settings tuned for ZeroGPU-style operation.

## Ticket System

The visitor ticket system is one of the most distinctive parts of the app.

It includes:

- visitor name
- visitor year
- imaginative title
- ticket number
- visit date
- museum name
- visual ticket layout
- QR-style seal block

This turns the visitor into part of the story and makes the project feel more like a real experience.

## Sharing System

There are two main share/export surfaces.

### 1. World Share Card

This exports a premium world summary card with:

- museum name
- premise
- government
- lead artifact
- turning point
- taboo
- visual motif

### 2. Museum Ticket Export

This exports a visitor-focused museum ticket with:

- visitor identity
- museum pass styling
- ticket number
- visit date
- imaginative title

## UI Direction

The app is intentionally far beyond stock Gradio styling.

Design goals:

- cinematic
- atmospheric
- museum-like
- premium
- interactive
- hackathon-demo friendly

Visual language includes:

- custom typography
- room-stage architecture
- warm gold gallery tones
- dark museum surfaces
- glassmorphism-inspired panels
- animated hall transitions
- ticket visuals
- exportable artifacts

## Interactive Features

Current notable interactions include:

- hall-to-hall navigation
- animated room stage
- typewriter text reveal
- audio guide controls
- theme switching
- visitor ticket preview
- world share export
- ticket export
- on-demand artifact image rendering

## Technical Notes

### Main Files

- `app.py`
  - main UI
  - museum flow
  - landing experience
  - share/ticket rendering logic
- `generators/engine.py`
  - text generation orchestration
  - role-based runtime routing
  - artifact image dispatch logic
- `generators/image_engine.py`
  - local image generation
  - ZeroGPU-friendly image pipeline setup

### State

The app keeps a shared museum state containing things like:

- concept
- curator mode
- visitor name
- visitor year
- world bible
- artifacts
- featured image
- timeline
- newspaper
- visitor book

## Why This App Is Strong

What makes the app stand out is not only that it generates text, but that it turns generation into an experience.

Its strengths are:

- custom UI beyond stock Gradio
- strong thematic coherence
- ticketed museum framing
- fine-tuned text generation
- interactive hall exploration
- image generation inside the artifact flow
- exportable and shareable outputs

## Good Demo Narrative

If you are presenting this app, the simplest strong explanation is:

`This is not a prompt box. It is a museum that builds and displays impossible civilizations as if they were real cultural histories.`

Then show:

1. visitor entrance and ticket
2. world generation
3. hall progression
4. artifact image rendering
5. downloadable ticket/share asset

## Suggested Next Improvements

If continuing development, the most valuable next upgrades would be:

- true full-screen entrance overlay
- even richer ticket animation
- stronger responsive polish for the landing area
- visitor-aware narration in more places
- more artifact render styles
- hall-specific ambient soundscapes
- multi-world comparison exhibition mode

## Summary

Infinite Museum of Impossible Worlds is a worldbuilding app presented as a cinematic museum visit.

It combines:

- fine-tuned text generation
- artifact image generation
- museum-style interface design
- visitor identity and ticketing
- shareable outputs

The result is an experience that feels much more like entering a fictional institution than using a normal AI demo.
