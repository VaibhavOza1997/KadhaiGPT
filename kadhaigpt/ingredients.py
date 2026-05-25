import json
from pathlib import Path

from kadhaigpt.profile import Profile

_DIET_FLAG = {
    "vegetarian": "is_vegetarian",
    "vegan": "is_vegan",
    "jain": "is_jain_safe",
    "pescetarian": "is_pescetarian_safe",
}


def load_ingredients(ingredients_file: Path) -> list[dict]:
    with open(ingredients_file) as f:
        data = json.load(f)
    return data["ingredients"]


def filter_by_diet(ingredients: list[dict], profile: Profile) -> list[dict]:
    flag = _DIET_FLAG[profile.dietary_mode]
    base = [i for i in ingredients if i.get(flag)]

    if profile.dietary_mode == "jain" or not profile.protein_addons:
        return base

    # Add any protein addons not already in the base list.
    # Jain is excluded above — its filter is absolute and cannot be overridden.
    base_names = {i["english_name"] for i in base}
    addon_map = {i["english_name"]: i for i in ingredients}

    for name in profile.protein_addons:
        if name not in base_names and name in addon_map:
            base.append(addon_map[name])

    return base


def search(ingredients: list[dict], query: str) -> list[dict]:
    q = query.lower().strip()
    results = []
    for item in ingredients:
        if q in item["english_name"].lower():
            results.append(item)
            continue
        regional = item.get("indian_regional_names", {})
        if any(q in name.lower() for name in regional.values()):
            results.append(item)
    return results
