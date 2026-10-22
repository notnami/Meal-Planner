"""Tasty recipe search (via RapidAPI)."""
import os

import requests

HOST = "tasty.p.rapidapi.com"


def search(query, diet_tag=None, size=10):
    key = os.getenv("TASTY_RAPIDAPI_KEY")
    if not key:
        raise RuntimeError("TASTY_RAPIDAPI_KEY is not set. Add it to .env or use Demo mode.")
    params = {"from": 0, "size": size, "q": query}
    if diet_tag in ("vegetarian", "vegan"):
        params["tags"] = diet_tag
    resp = requests.get(
        f"https://{HOST}/recipes/list",
        headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    simplified = (_simplify(r) for r in resp.json().get("results", []))
    return [r for r in simplified if r]


def _simplify(raw):
    # Compilations ("15 easy dinners") have no sections; skip them.
    if not raw.get("sections"):
        return None
    lines = []
    for section in raw["sections"]:
        for comp in section.get("components", []):
            text = (comp.get("raw_text") or "").strip()
            if text:
                lines.append(text)
    if not lines:
        return None
    slug = raw.get("slug")
    return {
        "id": str(raw["id"]),
        "name": raw.get("name", "Untitled recipe"),
        "servings": raw.get("num_servings") or 4,
        "ingredients": lines,
        "nutrition": _nutrition(raw.get("nutrition")),
        "source_name": "Tasty",
        "image": raw.get("thumbnail_url"),
        "url": f"https://tasty.co/recipe/{slug}" if slug else None,
    }


def _nutrition(raw):
    """Tasty reports nutrition per serving, but many recipes have none. Return None when missing."""
    if not isinstance(raw, dict):
        return None
    out = {}
    for key in ("calories", "protein", "fat", "carbohydrates", "sugar", "fiber"):
        try:
            out[key] = round(float(raw[key]))
        except (KeyError, TypeError, ValueError):
            pass
    return out if out.get("calories") else None
