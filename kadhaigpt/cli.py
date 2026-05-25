#!/usr/bin/env python3
import sys
from pathlib import Path

import questionary
from questionary import Style

from kadhaigpt.config import load_config
from kadhaigpt.ingredients import filter_by_diet, load_ingredients
from kadhaigpt.profile import Profile, load_profile, save_profile
from kadhaigpt.suggester import Suggestion, get_suggestions

_INGREDIENTS_FILE = Path(__file__).resolve().parent.parent / "ingredients.json"

_STYLE = Style([
    ("qmark",       "fg:#f5a623 bold"),
    ("question",    "bold"),
    ("answer",      "fg:#f5a623 bold"),
    ("pointer",     "fg:#f5a623 bold"),
    ("highlighted", "fg:#f5a623 bold"),
    ("selected",    "fg:#68b723"),
    ("instruction", "fg:#858585"),
    ("disabled",    "fg:#858585 italic"),
])

_ALL_PROTEINS = ["paneer", "tofu", "fish", "prawns", "chicken", "mutton"]


def main() -> None:
    try:
        config = load_config()
    except ValueError as e:
        print(f"\nConfiguration error: {e}")
        sys.exit(1)

    profile_dir = config.profile_dir
    profile = load_profile(profile_dir)
    is_first_run = not (profile_dir / "profile.json").exists()

    if is_first_run:
        _print_banner()
        print("Welcome! Let's set up your dietary profile first.\n")
        profile = _setup_profile(profile)
        save_profile(profile, profile_dir)
        print(f"\nProfile saved to {profile_dir / 'profile.json'}\n")

    _main_menu(config, profile)


def _main_menu(config, profile: Profile) -> None:
    while True:
        print(
            f"\n  KadhaiGPT  |  mode: {profile.dietary_mode}"
            f"  |  backend: {config.backend}"
        )
        choice = questionary.select(
            "What would you like to do?",
            choices=["Get dish suggestions", "Change dietary profile", "Exit"],
            style=_STYLE,
        ).ask()

        if choice is None or choice == "Exit":
            print("\nGoodbye!\n")
            break
        elif choice == "Get dish suggestions":
            _suggestion_flow(config, profile)
        elif choice == "Change dietary profile":
            profile = _setup_profile(profile)
            save_profile(profile, config.profile_dir)
            print("\nProfile updated.")


# ── Profile setup wizard ───────────────────────────────────────────────────────

def _setup_profile(current: Profile) -> Profile:
    mode = questionary.select(
        "Select your dietary mode:",
        choices=["vegetarian", "vegan", "jain", "pescetarian"],
        default=current.dietary_mode,
        style=_STYLE,
    ).ask()

    addons = questionary.checkbox(
        "Select protein add-ons you want available (optional):",
        choices=_ALL_PROTEINS,
        default=current.protein_addons,
        style=_STYLE,
    ).ask() or []

    serves_str = questionary.text(
        "Default serving size (1–10):",
        default=str(current.default_serves),
        validate=lambda v: (v.isdigit() and 1 <= int(v) <= 10) or "Enter a number between 1 and 10",
        style=_STYLE,
    ).ask()

    return Profile(
        dietary_mode=mode,
        protein_addons=addons,
        default_serves=int(serves_str),
    )


# ── Suggestion flow ────────────────────────────────────────────────────────────

def _suggestion_flow(config, profile: Profile) -> None:
    all_ingredients = load_ingredients(_INGREDIENTS_FILE)
    available = filter_by_diet(all_ingredients, profile)

    categories = sorted({i["category"] for i in available})
    selected_cats = questionary.checkbox(
        "Which ingredient categories do you have in your kitchen?",
        choices=categories,
        style=_STYLE,
    ).ask()

    if not selected_cats:
        print("\nNo categories selected — returning to menu.")
        return

    selected: list[dict] = []
    for cat in selected_cats:
        cat_items = sorted(
            [i for i in available if i["category"] == cat],
            key=lambda x: x["english_name"],
        )
        choices = [
            questionary.Choice(
                title=f"{i['english_name']}  ({i['indian_regional_names'].get('hindi', '')})",
                value=i,
            )
            for i in cat_items
        ]
        picked = questionary.checkbox(
            f"Select your {cat}:",
            choices=choices,
            style=_STYLE,
        ).ask() or []
        selected.extend(picked)

    if not selected:
        print("\nNo ingredients selected — returning to menu.")
        return

    serves_str = questionary.text(
        "How many people are you cooking for?",
        default=str(profile.default_serves),
        validate=lambda v: (v.isdigit() and 1 <= int(v) <= 10) or "Enter a number between 1 and 10",
        style=_STYLE,
    ).ask()
    serves = int(serves_str)

    print(f"\n  Asking {config.backend} for suggestions", end="", flush=True)
    print(" ...\n")

    try:
        suggestions = get_suggestions(selected, profile, serves, config)
    except Exception as e:
        print(f"\n  Error: {e}")
        print("  Check that your AI backend is running and configured correctly.")
        return

    _display_suggestions(suggestions)


# ── Display ────────────────────────────────────────────────────────────────────

def _display_suggestions(suggestions: list[Suggestion]) -> None:
    if not suggestions:
        print("\n  No suggestions returned. Try selecting more ingredients.\n")
        return

    print(f"{'=' * 62}")
    print(f"  {len(suggestions)} DISH SUGGESTIONS")
    print(f"{'=' * 62}")

    for n, s in enumerate(suggestions, 1):
        print(f"\n{'─' * 62}")
        title = s.dish_name_english.upper()
        if s.dish_name_hindi and s.dish_name_hindi.lower() != s.dish_name_english.lower():
            title += f"  /  {s.dish_name_hindi}"
        print(f"  {n}. {title}")
        print(f"{'─' * 62}")
        print(
            f"  Region: {s.cuisine_region}"
            f"  |  Time: {s.cook_time}"
            f"  |  Difficulty: {s.difficulty}"
        )

        print("\n  INGREDIENTS:")
        for ing in s.ingredients:
            print(f"    •  {ing.get('name', '')}  —  {ing.get('amount', '')}")

        if s.missing_ingredients:
            print("\n  YOU ARE MISSING:")
            for m in s.missing_ingredients:
                print(f"    ✗  {m}")

        print("\n  STEPS:")
        for j, step in enumerate(s.instructions, 1):
            _print_wrapped(f"{j}. {step}", indent="     ", first_indent=f"  {j:2}. ")

    print(f"\n{'=' * 62}\n")


def _print_wrapped(text: str, indent: str, first_indent: str, width: int = 62) -> None:
    words = text.split()
    line = first_indent
    for word in words:
        if len(line) + len(word) + 1 > width:
            print(line.rstrip())
            line = indent + word + " "
        else:
            line += word + " "
    if line.strip():
        print(line.rstrip())


def _print_banner() -> None:
    print("""
  ╔═══════════════════════════════════╗
  ║         K a d h a i G P T        ║
  ║   Indian meal suggestions from   ║
  ║         your own pantry          ║
  ╚═══════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
