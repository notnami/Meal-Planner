"""MyPlate.food API: USDA MyPlate Kitchen recipes with real USDA nutrition data. No API key.

Free-tier limits: 20 requests/minute per IP, 100 full-recipe fetches/day per IP.
Live per-request use only. Do not mirror or bulk-download the recipe catalog
(see https://myplate.food/terms). Check https://myplate.food/api for current limits.
"""
import re
from urllib.parse import quote

import requests

BASE = "https://myplate.food/api/v1"
SOURCE_NAME = "MyPlate Kitchen"
NUTRITION_SOURCE = "USDA MyPlate Kitchen"

_STOP = {"dish", "main", "side", "dessert", "dinner", "lunch", "recipe", "recipes", "easy",
         "and", "the", "with", "for", "holiday", "party"}
# If a text search finds nothing, fall back to a food group that loosely fits the course.
_FALLBACK_GROUP = {"main": "protein-foods", "side": "vegetables", "dessert": "fruits"}


def _get(path, params=None):
    resp = requests.get(
        f"{BASE}{path}", params=params, timeout=15,
        headers={"Accept": "application/json", "User-Agent": "holiday-meal-planner-demo"},
    )
    if resp.status_code == 429:
        wait = resp.headers.get("Retry-After")
        when = f"in {wait} seconds" if wait else "in a minute"
        raise RuntimeError(
            "MyPlate.food rate limit reached (free tier: 20 requests/minute, 100 full recipes/day). "
            f"Try again {when}."
        )
    if resp.status_code == 404:
        raise RuntimeError("That recipe wasn't found on MyPlate.food.")
    resp.raise_for_status()
    return resp.json()


def _attempts(query, course):
    """Try the full phrase, then its last meaningful word, then a loose food-group match."""
    yield {"q": query}
    words = [w for w in re.findall(r"[a-z]+", query.lower()) if w not in _STOP and len(w) > 2]
    if words:
        yield {"q": words[-1]}
    group = _FALLBACK_GROUP.get(course)
    if group:
        yield {"food_group": group}


def search(query, diet_tag=None, course=None, size=8):
    """Return recipe cards. Calories per serving come back with the search, so no extra fetch is needed.

    The API has no vegetarian/vegan filter, so diet_tag is not applied here;
    planner.check_diet() flags suspicious ingredients after the full recipes are fetched.
    """
    for extra in _attempts(query, course):
        data = _get("/recipes", {**extra, "limit": 24, "min_rating": 3})
        found = [c for c in (_card(r) for r in data.get("results", [])) if c]
        if found:
            # The API lists alphabetically; prefer well-rated recipes instead.
            found.sort(key=lambda c: (c["rating"], c["rating_count"]), reverse=True)
            return found[:size]
    return []


def _card(raw):
    if not raw.get("slug") or not raw.get("calories"):
        return None
    rating = raw.get("rating") or {}
    return {
        "id": raw["slug"],
        "name": raw.get("name", "Untitled recipe"),
        "servings": None,  # filled in by get_recipe() for the 3 dishes that get chosen
        "ingredients": [],
        "ingredient_count": raw.get("ingredient_count") or 0,
        "nutrition": {"calories": raw["calories"], "source": NUTRITION_SOURCE},
        "rating": rating.get("value") or 0,
        "rating_count": rating.get("count") or 0,
        "image": raw.get("image_url"),
        "url": raw.get("recipe_url"),
        "source_name": SOURCE_NAME,
    }


def get_recipe(slug):
    """Full recipe (counts toward the 100/day fetch limit). Returns fields to merge into a card."""
    data = _get(f"/recipes/{quote(slug, safe='')}")
    lines = []
    for ing in data.get("ingredients", []):
        text = (ing.get("text") or "").strip()
        if text:
            lines.append(f"{text} ({ing['note']})" if ing.get("note") else text)

    match = re.search(r"\d+", data.get("yield") or "")
    servings = int(match.group()) if match else 4

    values = {n["key"]: n["amount"] for n in data.get("nutrition", [])
              if isinstance(n, dict) and n.get("key") and n.get("amount") is not None}
    nutrition = {"source": NUTRITION_SOURCE}
    for ours, theirs in (("calories", "total_calories"), ("protein", "protein"),
                         ("fat", "total_fat"), ("carbohydrates", "carbohydrates"),
                         ("fiber", "dietary_fiber"), ("sodium", "sodium")):
        if theirs in values:
            nutrition[ours] = round(values[theirs])

    return {
        "ingredients": lines,
        "servings": servings,
        "nutrition": nutrition,
        "image": data.get("image_url"),
        "url": data.get("recipe_url"),
        "directions": data.get("directions"),
    }
