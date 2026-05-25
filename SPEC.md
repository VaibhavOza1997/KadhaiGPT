# KadhaiGPT — Project Specification v0.1

## Overview

KadhaiGPT is an open source, privacy-first meal suggestion tool built for Indian and Indian-American households. It runs entirely on the user's machine, stores no data, and works with any MCP-compatible AI agent or local model via Ollama. Users tell it what is in their fridge, set their dietary profile once, and get three actionable dish suggestions with full instructions.

---

## Problem statement

Most meal suggestion tools are Western-centric, ignore nuanced Indian dietary rules (especially Jain), and require cloud accounts that store personal data. Indian and Indian-American households are underserved.

---

## Goals

- Free to run forever (local Ollama or user's own API key)
- Zero data stored anywhere, ever
- Works with any MCP-compatible AI (Claude, Cursor, Windsurf, etc.)
- Bilingual ingredient list (English + Hindi)
- Respects Indian dietary rules strictly, not as suggestions

---

## Non-goals (out of scope for MVP)

- Hosted web app or server
- User accounts or authentication
- Non-Indian cuisines (future expansion)
- Mobile app
- Grocery ordering integration

---

## Users

Primary: Indian and Indian-American households, bilingual (Hindi + English)
Secondary: Developers who want to run or extend an MCP-based AI tool

---

## Dietary modes

| Mode | Rules enforced |
|---|---|
| Vegetarian | No meat, no seafood. Eggs optional (configurable) |
| Vegan | No meat, no seafood, no dairy, no eggs, no honey |
| Jain | Vegetarian + strictly no root vegetables (onion, garlic, potato, carrot, beetroot, radish, turnip) |
| Pescetarian | Vegetarian + seafood allowed |

Dietary mode is set once in a user profile. Jain filtering happens before the prompt reaches the AI — root vegetables are removed from the ingredient list entirely, not left to the model to figure out.

---

## Core features — MVP

### F1: Ingredient selection
- Browseable by category: vegetables, dairy, spices, lentils and legumes, grains, proteins, condiments
- Searchable by English or Hindi name
- Ingredient data lives in a community-editable JSON file (not hardcoded)
- Each ingredient entry contains: English name, Hindi name, category, dietary flags (is_jain_safe, is_vegan, is_vegetarian)

### F2: Dietary profile
- Set once on first run, stored in a local config file on the user's machine
- Configurable anytime via a settings menu
- Options: vegetarian / vegan / jain / pescetarian
- Protein add-on toggle: allows user to add a protein (paneer, tofu, chicken, fish) on top of their base diet mode

### F3: Dish suggestion
- Sends ingredient list + dietary profile + serving size to the AI
- AI returns exactly 3 dish suggestions
- Each suggestion includes:
  - Dish name (English + Hindi where possible)
  - Cuisine region (North Indian, South Indian, Gujarati, etc.)
  - Cook time
  - Difficulty (easy / medium / hard)
  - Ingredients with measurements scaled to serving size
  - Step by step instructions
  - What ingredients the user is missing (if any), max 2 missing allowed

### F4: Serving size
- Default: 2 people
- Adjustable: 1 to 10
- All measurements in steps update automatically based on serving size

### F5: Missing ingredients
- If a dish needs up to 2 extra ingredients the user does not have, it is still suggested
- Clearly shown as: "You are missing: jeera (cumin seeds), rai (mustard seeds)"
- If more than 2 ingredients are missing, that dish is not suggested

### F6: AI backend (user's choice)
- Option A: Local Ollama model (free, fully private, recommended)
- Option B: Anthropic API key (user provides their own)
- Option C: OpenAI API key (user provides their own)
- Option D: Gemini API key (user provides their own)
- Config stored in a local .env file, never committed to git

---

## Technical architecture

### Phase 1 — Python CLI (learning phase)
- Interactive menu-driven terminal app
- Pure Python, minimal dependencies
- Talks to Ollama locally or any LLM API
- This is the learning vehicle: prompting, API calls, structured output

### Phase 2 — MCP server (final product)
- Wraps the Phase 1 logic as an MCP server
- Exposes KadhaiGPT as a tool any MCP-compatible AI can call
- User installs it once, any AI agent on their machine can use it
- Same zero-data, zero-server principle

### Data files (community editable)
- ingredients.json — master ingredient list with Hindi names and dietary flags
- No database, no cloud, no server

### GitHub Actions
- Lint and test on every pull request
- Validate ingredients.json schema on every PR (so community contributions don't break the app)
- Package and release on version tag

---

## Repo structure (planned)

```
KadhaiGPT/
├── README.md
├── .env.example
├── ingredients.json
├── kadhaigpt/
│   ├── __init__.py
│   ├── cli.py          # Phase 1: interactive CLI
│   ├── mcp_server.py   # Phase 2: MCP server
│   ├── suggester.py    # core logic: build prompt, call AI, parse response
│   ├── ingredients.py  # load and filter ingredient list
│   ├── profile.py      # user dietary profile management
│   └── config.py       # AI backend config (.env loader)
├── tests/
│   └── test_suggester.py
└── .github/
    └── workflows/
        ├── lint.yml
        └── validate_ingredients.yml
```

---

## Development phases

### Phase 1 — CLI (you learn: Python project structure, LLM prompting, API calls, structured output parsing)
- [ ] Set up repo and Python project structure
- [ ] Build ingredients.json with 50 common Indian pantry items
- [ ] Build ingredient browser and search (CLI)
- [ ] Build dietary profile system
- [ ] Build prompt constructor (this is where LLM learning happens)
- [ ] Call Ollama / API and parse response
- [ ] Display suggestions with missing ingredients
- [ ] Serving size scaling

### Phase 2 — GitHub Actions (you learn: CI/CD, automation, open source workflow)
- [ ] Lint workflow on PR
- [ ] JSON schema validation workflow
- [ ] Release workflow on version tag

### Phase 3 — MCP server (you learn: MCP protocol, tool definitions, open source AI ecosystem)
- [ ] Wrap CLI logic as MCP tools
- [ ] Test with Claude desktop
- [ ] Write contributor guide so community can add ingredients

---

## Success criteria for MVP

- A user with Ollama installed can clone the repo, run one setup command, and get 3 meal suggestions in under 2 minutes
- Jain mode never suggests a dish with root vegetables
- All measurements scale correctly when serving size changes
- Zero network calls when using Ollama (fully offline)

---

## Open questions (to revisit)

- Should Hindi dish names use Devanagari script or romanized Hindi?
- Minimum Ollama model recommendation (llama3.2 likely)
- Should we support regional Indian English spellings? (e.g. "brinjal" vs "eggplant")

---

*Spec version: 0.1 | Status: Draft | Owner: KadhaiGPT contributors*
