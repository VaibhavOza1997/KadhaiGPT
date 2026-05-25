import json
from pathlib import Path

import pytest

from kadhaigpt.ingredients import filter_by_diet, load_ingredients, search
from kadhaigpt.profile import Profile, load_profile, save_profile
from kadhaigpt.suggester import _build_prompt, _parse_response

_INGREDIENTS_FILE = Path(__file__).resolve().parent.parent / "ingredients.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

def _all_ingredients():
    return load_ingredients(_INGREDIENTS_FILE)


def _filtered(mode, addons=None):
    profile = Profile(dietary_mode=mode, protein_addons=addons or [], default_serves=2)
    return filter_by_diet(_all_ingredients(), profile), profile


def _names(ingredient_list):
    return {i["english_name"] for i in ingredient_list}


# ── _parse_response ────────────────────────────────────────────────────────────

class TestParseResponse:
    def test_clean_json(self):
        raw = json.dumps({"suggestions": [{
            "dish_name_english": "Dal Tadka",
            "dish_name_hindi": "dal tadka",
            "cuisine_region": "North Indian",
            "cook_time": "30 minutes",
            "difficulty": "easy",
            "ingredients": [{"name": "toor dal", "amount": "200g"}],
            "instructions": ["Boil the dal.", "Add tadka."],
            "missing_ingredients": [],
        }]})
        result = _parse_response(raw)
        assert len(result) == 1
        assert result[0].dish_name_english == "Dal Tadka"
        assert result[0].cuisine_region == "North Indian"
        assert result[0].missing_ingredients == []

    def test_strips_json_markdown_fence(self):
        raw = '```json\n{"suggestions": []}\n```'
        assert _parse_response(raw) == []

    def test_strips_plain_markdown_fence(self):
        raw = '```\n{"suggestions": []}\n```'
        assert _parse_response(raw) == []

    def test_missing_ingredients_defaults_to_empty(self):
        raw = json.dumps({"suggestions": [{
            "dish_name_english": "Khichdi",
            "dish_name_hindi": "khichdi",
            "cuisine_region": "Pan-Indian",
            "cook_time": "20 minutes",
            "difficulty": "easy",
            "ingredients": [],
            "instructions": [],
        }]})
        result = _parse_response(raw)
        assert result[0].missing_ingredients == []

    def test_three_suggestions_parsed(self):
        suggestion = {
            "dish_name_english": "Dish",
            "dish_name_hindi": "dish",
            "cuisine_region": "North Indian",
            "cook_time": "20 minutes",
            "difficulty": "easy",
            "ingredients": [],
            "instructions": [],
            "missing_ingredients": [],
        }
        raw = json.dumps({"suggestions": [suggestion, suggestion, suggestion]})
        assert len(_parse_response(raw)) == 3

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response("this is not json at all")

    def test_empty_suggestions_list(self):
        raw = json.dumps({"suggestions": []})
        assert _parse_response(raw) == []


# ── _build_prompt ──────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def setup_method(self):
        filtered, self.profile = _filtered("vegetarian")
        self.prompt = _build_prompt(filtered, self.profile, serves=4)

    def test_dietary_mode_in_prompt(self):
        assert "vegetarian" in self.prompt

    def test_serves_in_prompt(self):
        assert "4" in self.prompt

    def test_categories_grouped(self):
        assert "Spices:" in self.prompt
        assert "Dairy:" in self.prompt
        assert "Grains:" in self.prompt

    def test_ingredient_names_in_prompt(self):
        assert "spinach" in self.prompt
        assert "turmeric" in self.prompt

    def test_jain_prompt_excludes_root_veg(self):
        filtered, profile = _filtered("jain")
        prompt = _build_prompt(filtered, profile, serves=2)
        assert "onion" not in prompt
        assert "garlic" not in prompt
        assert "potato" not in prompt
        assert "ginger" not in prompt


# ── Jain filter — the spec's hardest correctness requirement ───────────────────

_JAIN_PROHIBITED = [
    "onion", "garlic", "potato", "carrot", "beetroot",
    "radish", "turnip", "ginger", "lotus stem", "mushroom",
]

class TestJainFilter:
    def setup_method(self):
        self.filtered, _ = _filtered("jain")
        self.names = _names(self.filtered)

    def test_blocks_all_spec_root_vegetables(self):
        for item in _JAIN_PROHIBITED:
            assert item not in self.names, f"Jain filter failed: '{item}' must be blocked"

    def test_blocks_meat(self):
        for item in ("chicken", "mutton", "fish", "prawns", "eggs"):
            assert item not in self.names

    def test_allows_paneer(self):
        assert "paneer" in self.names

    def test_allows_lentils(self):
        assert "split pigeon peas" in self.names
        assert "red lentils" in self.names

    def test_allows_spices(self):
        assert "turmeric" in self.names
        assert "cumin seeds" in self.names

    def test_addon_cannot_override_hard_filter(self):
        """Jain hard filter must block chicken even when added as protein addon."""
        filtered, _ = _filtered("jain", addons=["chicken", "paneer"])
        names = _names(filtered)
        assert "chicken" not in names
        assert "paneer" in names

    def test_addon_cannot_add_root_veg(self):
        """No mechanism should allow onion into a Jain ingredient list."""
        filtered, _ = _filtered("jain", addons=["onion"])
        assert "onion" not in _names(filtered)


# ── Other dietary modes ────────────────────────────────────────────────────────

class TestVegetarianFilter:
    def test_blocks_meat(self):
        filtered, _ = _filtered("vegetarian")
        names = _names(filtered)
        for item in ("chicken", "mutton", "fish", "prawns", "eggs"):
            assert item not in names

    def test_allows_dairy(self):
        filtered, _ = _filtered("vegetarian")
        assert "paneer" in _names(filtered)

    def test_protein_addon_adds_chicken(self):
        """A vegetarian user can explicitly add chicken as an addon."""
        filtered, _ = _filtered("vegetarian", addons=["chicken"])
        assert "chicken" in _names(filtered)


class TestVeganFilter:
    def test_blocks_dairy(self):
        filtered, _ = _filtered("vegan")
        names = _names(filtered)
        for item in ("paneer", "ghee", "butter", "cream", "milk", "yogurt"):
            assert item not in names

    def test_allows_tofu(self):
        filtered, _ = _filtered("vegan")
        assert "tofu" in _names(filtered)


class TestPescetarianFilter:
    def test_includes_fish_and_prawns(self):
        filtered, _ = _filtered("pescetarian")
        names = _names(filtered)
        assert "fish" in names
        assert "prawns" in names

    def test_blocks_chicken_and_mutton(self):
        filtered, _ = _filtered("pescetarian")
        names = _names(filtered)
        assert "chicken" not in names
        assert "mutton" not in names

    def test_includes_dairy(self):
        filtered, _ = _filtered("pescetarian")
        assert "paneer" in _names(filtered)


# ── Search ─────────────────────────────────────────────────────────────────────

class TestSearch:
    def setup_method(self):
        self.ingredients = _all_ingredients()

    def test_by_english_name(self):
        results = search(self.ingredients, "spinach")
        assert any(i["english_name"] == "spinach" for i in results)

    def test_by_hindi_name(self):
        results = search(self.ingredients, "palak")
        assert any(i["english_name"] == "spinach" for i in results)

    def test_by_tamil_name(self):
        results = search(self.ingredients, "thengai")
        assert any(i["english_name"] == "fresh coconut" for i in results)

    def test_by_telugu_name(self):
        results = search(self.ingredients, "jeelakarra")
        assert any(i["english_name"] == "cumin seeds" for i in results)

    def test_case_insensitive(self):
        results = search(self.ingredients, "PALAK")
        assert any(i["english_name"] == "spinach" for i in results)

    def test_partial_match(self):
        # "gobhi" is the correct romanized Hindi — "gobi" is an anglicized shortening not in the data
        results = search(self.ingredients, "gobhi")
        names = {i["english_name"] for i in results}
        assert "cauliflower" in names or "cabbage" in names

    def test_no_results(self):
        assert search(self.ingredients, "xyznonexistentingredient") == []


# ── Profile persistence ────────────────────────────────────────────────────────

class TestProfilePersistence:
    def test_round_trip(self, tmp_path):
        profile = Profile(dietary_mode="jain", protein_addons=["paneer", "tofu"], default_serves=4)
        save_profile(profile, tmp_path)
        loaded = load_profile(tmp_path)
        assert loaded.dietary_mode == "jain"
        assert loaded.protein_addons == ["paneer", "tofu"]
        assert loaded.default_serves == 4

    def test_first_run_defaults(self, tmp_path):
        profile = load_profile(tmp_path)
        assert profile.dietary_mode == "vegetarian"
        assert profile.protein_addons == []
        assert profile.default_serves == 2

    def test_invalid_mode_falls_back_to_vegetarian(self, tmp_path):
        (tmp_path / "profile.json").write_text(
            json.dumps({"dietary_mode": "carnivore", "protein_addons": [], "default_serves": 2})
        )
        profile = load_profile(tmp_path)
        assert profile.dietary_mode == "vegetarian"

    def test_serves_out_of_range_is_clamped(self, tmp_path):
        (tmp_path / "profile.json").write_text(
            json.dumps({"dietary_mode": "vegan", "protein_addons": [], "default_serves": 99})
        )
        profile = load_profile(tmp_path)
        assert profile.default_serves == 10

    def test_creates_directory_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        profile = Profile(dietary_mode="vegan", protein_addons=[], default_serves=2)
        save_profile(profile, nested)
        assert (nested / "profile.json").exists()
