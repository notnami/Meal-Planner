"""Calorie logic. Python does all the math; Gemma only estimates when a recipe has no nutrition data.

Conventions:
- Calories are per SERVING, as Tasty reports them.
- A guest is assumed to eat one serving of each dish (main + side + dessert).
- Every number carries a source label ("Tasty", "AI estimate", "Sample data") so the UI can be honest about it.
"""
import itertools

import llm

MIN_KCAL, MAX_KCAL = 20, 2500  # sanity range for one serving of one dish


def _valid(value):
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        return None
    return n if MIN_KCAL <= n <= MAX_KCAL else None


def fill_calories(candidates, model):
    """Set c['calories'] and c['calorie_source'] on every candidate (None if unknown).

    Uses Tasty's data when present. Everything else goes to Gemma in ONE batched call.
    """
    missing = []
    for c in candidates:
        nutrition = c.get("nutrition") or {}
        kcal = _valid(nutrition.get("calories"))
        c["calories"] = kcal
        c["calorie_source"] = nutrition.get("source", "Tasty") if kcal else None
        if kcal is None:
            missing.append(c)

    if not missing:
        return candidates

    blocks = []
    for c in missing:
        ingredients = "; ".join(c["ingredients"][:14])
        blocks.append(f"id={c['id']} | {c['name']} | serves {c['servings']} | {ingredients}")
    prompt = f"""Estimate the calories in ONE SERVING of each recipe below.
Use the ingredient list and the number of servings. Round to the nearest 10.
If you are unsure, give your best realistic estimate.

Recipes:
{chr(10).join(blocks)}

Return ONLY JSON: {{"estimates": [{{"id": "<id>", "calories": 0}}]}}"""
    try:
        data = llm.chat_json(prompt, model)
    except Exception:
        return candidates  # leave them unknown rather than fail the whole plan

    by_id = {str(e.get("id")): e.get("calories") for e in data.get("estimates", []) if isinstance(e, dict)}
    for c in missing:
        kcal = _valid(by_id.get(c["id"]))
        if kcal:
            c["calories"], c["calorie_source"] = kcal, "AI estimate"
    return candidates


def fit_to_goal(picks, candidates, goal):
    """Make sure the chosen plate is within the calorie goal, if one was given.

    picks: {course: recipe}. Returns (picks, changed).
    If Gemma's menu is already within the goal (or the goal is unknown), nothing changes.
    Otherwise search every main/side/dessert combination with known calories and keep
    the one that stays within the goal and keeps as many of Gemma's picks as possible.
    """
    if not goal:
        return picks, False

    def total(p):
        return sum(r["calories"] for r in p.values())

    if all(r.get("calories") for r in picks.values()) and total(picks) <= goal:
        return picks, False

    courses = [c for c in picks]
    pools = [[c for c in candidates if c["course"] == course and c.get("calories")] for course in courses]
    if not all(pools):
        return picks, False

    best, best_key = None, None
    for combo in itertools.product(*pools):
        plate = dict(zip(courses, combo))
        t = total(plate)
        if t > goal:
            continue
        matches = sum(1 for course in courses if plate[course]["id"] == picks[course]["id"])
        key = (matches, t)  # keep Gemma's picks first, then use the goal as fully as possible
        if best_key is None or key > best_key:
            best, best_key = plate, key
    if best is None:
        return picks, False  # nothing fits; the UI will say so
    changed = any(best[c]["id"] != picks[c]["id"] for c in courses)
    return best, changed


def plate_summary(menu, goal):
    """Per-dish calories and the per-person total for the whole meal."""
    rows, known_total, unknown = [], 0, []
    for dish in menu:
        r = dish["recipe"]
        kcal = r.get("calories")
        rows.append({
            "course": dish["course"],
            "name": r["name"],
            "calories": kcal,
            "source": r.get("calorie_source") or "Not available",
        })
        if kcal:
            known_total += kcal
        else:
            unknown.append(r["name"])

    if not goal:
        status, diff = "none", 0
    elif known_total > goal:
        status, diff = "over", known_total - goal
    elif unknown:
        status, diff = "unknown", goal - known_total
    else:
        status, diff = "under", goal - known_total

    return {
        "rows": rows,
        "per_person": known_total,
        "unknown": unknown,
        "goal": goal,
        "status": status,
        "difference": diff,
    }
