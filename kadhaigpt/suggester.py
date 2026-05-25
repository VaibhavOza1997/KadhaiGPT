import json
from dataclasses import dataclass

import requests

from kadhaigpt.config import Config
from kadhaigpt.profile import Profile

# ── Prompt template ──────────────────────────────────────────────────────────
# Edit this string to change what KadhaiGPT asks the AI.
# Placeholders: {dietary_mode}, {serves}, {ingredient_list}

_PROMPT = """You are KadhaiGPT, an expert Indian cooking assistant.

USER PROFILE:
- Dietary mode: {dietary_mode}
- Serving size: {serves} people

AVAILABLE INGREDIENTS:
{ingredient_list}

TASK:
Suggest exactly 3 Indian dishes this user can realistically cook with the above ingredients.
For each dish, you may include up to 2 ingredients the user does NOT have — list them in missing_ingredients.
If a dish needs more than 2 missing ingredients, do not suggest it.
Scale all ingredient amounts for {serves} people. Use practical measurements (grams, cups, tablespoons, teaspoons).

Respond ONLY with valid JSON. No explanation, no markdown, no code fences. Use this exact structure:

{{
  "suggestions": [
    {{
      "dish_name_english": "Palak Paneer",
      "dish_name_hindi": "palak paneer",
      "cuisine_region": "North Indian",
      "cook_time": "30 minutes",
      "difficulty": "easy",
      "ingredients": [
        {{"name": "spinach", "amount": "500g"}},
        {{"name": "paneer", "amount": "200g"}}
      ],
      "instructions": [
        "Blanch the spinach in boiling water for 2 minutes, then drain and blend to a smooth puree.",
        "Heat 2 tbsp oil in a pan. Add cumin seeds and let them splutter."
      ],
      "missing_ingredients": []
    }}
  ]
}}"""

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Suggestion:
    dish_name_english: str
    dish_name_hindi: str
    cuisine_region: str
    cook_time: str
    difficulty: str
    ingredients: list[dict]
    instructions: list[str]
    missing_ingredients: list[str]


# ── Public API ─────────────────────────────────────────────────────────────────

def get_suggestions(
    ingredients: list[dict],
    profile: Profile,
    serves: int,
    config: Config,
) -> list[Suggestion]:
    prompt = _build_prompt(ingredients, profile, serves)

    if config.backend == "ollama":
        raw = _call_ollama(prompt, config)
    elif config.backend == "anthropic":
        raw = _call_anthropic(prompt, config)
    elif config.backend == "openai":
        raw = _call_openai(prompt, config)
    elif config.backend == "gemini":
        raw = _call_gemini(prompt, config)
    else:
        raise ValueError(f"Unknown backend: {config.backend}")

    return _parse_response(raw)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(ingredients: list[dict], profile: Profile, serves: int) -> str:
    by_category: dict[str, list[str]] = {}
    for item in ingredients:
        cat = item["category"].title()
        by_category.setdefault(cat, []).append(item["english_name"])

    ingredient_lines = []
    for cat in sorted(by_category):
        names = ", ".join(sorted(by_category[cat]))
        ingredient_lines.append(f"{cat}: {names}")

    return _PROMPT.format(
        dietary_mode=profile.dietary_mode,
        serves=serves,
        ingredient_list="\n".join(ingredient_lines),
    )


# ── Backend callers ────────────────────────────────────────────────────────────

def _call_ollama(prompt: str, config: Config) -> str:
    url = f"{config.ollama_base_url}/api/generate"
    response = requests.post(
        url,
        json={"model": config.ollama_model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]


def _call_anthropic(prompt: str, config: Config) -> str:
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]


def _call_openai(prompt: str, config: Config) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.openai_api_key}",
            "content-type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str, config: Config) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        f"/models/gemini-2.0-flash:generateContent?key={config.gemini_api_key}"
    )
    response = requests.post(
        url,
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


# ── Response parser ────────────────────────────────────────────────────────────

def _parse_response(text: str) -> list[Suggestion]:
    text = text.strip()

    # Strip markdown code fences many models add despite being asked not to
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    data = json.loads(text)
    suggestions = []
    for s in data.get("suggestions", []):
        suggestions.append(
            Suggestion(
                dish_name_english=s.get("dish_name_english", ""),
                dish_name_hindi=s.get("dish_name_hindi", ""),
                cuisine_region=s.get("cuisine_region", ""),
                cook_time=s.get("cook_time", ""),
                difficulty=s.get("difficulty", ""),
                ingredients=s.get("ingredients", []),
                instructions=s.get("instructions", []),
                missing_ingredients=s.get("missing_ingredients", []),
            )
        )
    return suggestions
