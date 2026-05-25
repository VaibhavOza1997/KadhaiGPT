import json
from dataclasses import dataclass, field
from pathlib import Path

VALID_DIETARY_MODES = {"vegetarian", "vegan", "jain", "pescetarian"}
_PROFILE_FILE = "profile.json"


@dataclass
class Profile:
    dietary_mode: str
    protein_addons: list[str]
    default_serves: int


def load_profile(profile_dir: Path) -> Profile:
    profile_file = profile_dir / _PROFILE_FILE

    if not profile_file.exists():
        return _default_profile()

    with open(profile_file) as f:
        data = json.load(f)

    mode = data.get("dietary_mode", "vegetarian")
    if mode not in VALID_DIETARY_MODES:
        mode = "vegetarian"

    return Profile(
        dietary_mode=mode,
        protein_addons=data.get("protein_addons", []),
        default_serves=max(1, min(10, int(data.get("default_serves", 2)))),
    )


def save_profile(profile: Profile, profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_file = profile_dir / _PROFILE_FILE
    with open(profile_file, "w") as f:
        json.dump(
            {
                "dietary_mode": profile.dietary_mode,
                "protein_addons": profile.protein_addons,
                "default_serves": profile.default_serves,
            },
            f,
            indent=2,
        )


def _default_profile() -> Profile:
    return Profile(dietary_mode="vegetarian", protein_addons=[], default_serves=2)
