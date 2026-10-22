"""The pipeline. Gemma handles language; Python handles APIs, math, and validation."""
import re

import llm
import nutrition

COURSES = ["main", "side", "dessert"]

_MEAT = ("chicken", "beef", "pork", "turkey", "ham", "bacon", "sausage", "lamb", "fish", "salmon",
         "tuna", "shrimp", "crab", "catfish", "tilapia", "cod", "anchovy", "gelatin")
_ANIMAL = ("egg", "milk", "cheese", "butter", "yogurt", "honey", "cream", "mayonnaise", "whey")


def _scale(guests, servings):
    return round(guests / max(servings, 1), 1) if servings else None


def _to_num(value):
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_request(text, model):
    prompt = f"""Convert this holiday meal request into JSON.
Return ONLY a JSON object with these keys:
- "guests": integer number of people (use 4 if not stated)
- "budget": number in US dollars, or null if not stated
- "calorie_goal": integer calories PER PERSON for the whole meal, or null if not stated
- "meal": short name of the occasion, for example "Thanksgiving dinner"
- "diet_tag": "vegetarian" or "vegan" ONLY if every dish must be that, otherwise null
- "dietary_notes": short text about other dietary needs, allergies, or a partly vegetarian group, or ""
- "search_terms": list of exactly 3 short recipe search phrases: a main dish, a side dish, a dessert, all fitting the occasion

Request: {text}"""
    data = llm.chat_json(prompt, model)

    guests = int(min(max(_to_num(data.get("guests")) or 4, 1), 50))
    budget = _to_num(data.get("budget"))
    if budget is not None and budget <= 0:
        budget = None
    calorie_goal = _to_num(data.get("calorie_goal"))
    calorie_goal = round(calorie_goal) if calorie_goal and 300 <= calorie_goal <= 5000 else None
    meal = str(data.get("meal") or "holiday dinner").strip()
    tag = str(data.get("diet_tag") or "").lower()
    terms = [str(t).strip() for t in (data.get("search_terms") or []) if str(t).strip()][:3]
    defaults = [f"{meal} main dish", f"{meal} side dish", f"{meal} dessert"]
    terms += defaults[len(terms):]
    return {
        "guests": guests,
        "budget": budget,
        "calorie_goal": calorie_goal,
        "meal": meal,
        "diet_tag": tag if tag in ("vegetarian", "vegan") else None,
        "dietary_notes": str(data.get("dietary_notes") or "").strip(),
        "search_terms": terms,
    }


#  Recipe candidates (Tasty) -------------------------------------------------
def gather_candidates(constraints, search_fn):
    seen, candidates = set(), []
    for course, term in zip(COURSES, constraints["search_terms"]):
        found = search_fn(term, constraints["diet_tag"], course)
        if not found:  # retry with a simpler query
            found = search_fn(f"{constraints['meal']} {course}", constraints["diet_tag"], course)
        for recipe in found[:6]:
            if recipe["id"] not in seen:
                seen.add(recipe["id"])
                candidates.append({**recipe, "course": course})
    if not candidates:
        raise RuntimeError("No recipes found. Try rewording your request or use Demo mode.")
    return candidates


# Gemma picks a menu (Python then checks the calorie math) ---------------------------
def choose_menu(constraints, candidates, model):
    goal = constraints["calorie_goal"]

    def kcal(c):
        return f"~{c['calories']} kcal/serving" if c.get("calories") else "calories unknown"

    listing = "\n".join(
        f"- id={c['id']} | {c['course']} | {c['name']} | "
        f"{c.get('ingredient_count') or len(c['ingredients'])} ingredients | {kcal(c)}"
        for c in candidates
    )
    prompt = f"""Pick a 3-dish menu for a {constraints['meal']}: one main, one side, one dessert.
Guests: {constraints['guests']}
Budget: {constraints['budget'] or 'not specified'}
Calorie goal per person for the whole meal: {goal or 'not specified'}
Dietary needs: {constraints['dietary_notes'] or 'none'}
If the budget is tight, prefer recipes with fewer ingredients.
If some guests are vegetarian, make sure they can eat a full plate (vegetarian sides count).
Each guest eats one serving of each dish, so the three calorie numbers add up to one plate.
If there is a calorie goal, pick dishes whose calories add up to about the goal or less.

Candidates:
{listing}

Return ONLY JSON: {{"main": "<id>", "side": "<id>", "dessert": "<id>", "reasoning": "one sentence"}}"""
    data = llm.chat_json(prompt, model)

    picks = {}
    for course in COURSES:
        in_course = [c for c in candidates if c["course"] == course]
        if in_course:
            picks[course] = next((c for c in in_course if c["id"] == str(data.get(course))), in_course[0])

    picks, adjusted = nutrition.fit_to_goal(picks, candidates, goal)

    menu = [
        {"course": course, "recipe": picks[course],
         "scale": _scale(constraints["guests"], picks[course].get("servings"))}
        for course in COURSES if course in picks
    ]
    reasoning = str(data.get("reasoning") or "").strip()
    if adjusted:
        reasoning = (reasoning + " " if reasoning else "") + (
            "Some dishes were swapped so one plate fits your calorie goal.")
    return menu, reasoning


#  Full recipes for the chosen dishes (only needed when search returns summary cards) ----
def hydrate_menu(menu, detail_fn, guests):
    out = []
    for dish in menu:
        full = detail_fn(dish["recipe"])
        recipe = {**dish["recipe"], **{k: v for k, v in full.items() if v}}
        out.append({**dish, "recipe": recipe, "scale": _scale(guests, recipe.get("servings"))})
    return out


def check_diet(menu, tag):
    """Plain keyword check. Sources without a diet filter can return the wrong kind of dish."""
    if tag not in ("vegetarian", "vegan"):
        return []
    words = _MEAT + (_ANIMAL if tag == "vegan" else ())
    pattern = re.compile(r"\b(?:" + "|".join(words) + r")s?\b", re.I)
    warnings = []
    for dish in menu:
        hits = sorted({m.lower() for line in dish["recipe"]["ingredients"] for m in pattern.findall(line)})
        if hits:
            warnings.append(f"{dish['recipe']['name']} may not be {tag}: its ingredients mention {', '.join(hits)}.")
    return warnings


#  Gemma merges ingredients into one grocery list --------------------------------
def build_shopping_list(menu, model):
    lines = []
    for dish in menu:
        lines.append(f"{dish['recipe']['name']}:")
        lines += [f"  {i}" for i in dish["recipe"]["ingredients"]]
    prompt = f"""Combine these recipe ingredient lines into ONE grocery list. Merge duplicates.
For each item return:
- "item": plain shopping-list name, no quantities
- "search": a 1-3 word grocery store search term
- "pantry": true only for basics like salt, pepper, water, ice, cooking oil, cooking spray; otherwise false

Ingredients:
{chr(10).join(lines)}

Return ONLY JSON: {{"items": [{{"item": "...", "search": "...", "pantry": false}}]}}"""
    data = llm.chat_json(prompt, model)
    items = []
    for raw in data.get("items", [])[:40]:
        if isinstance(raw, dict) and raw.get("item"):
            items.append({
                "item": str(raw["item"]).strip(),
                "search": str(raw.get("search") or raw["item"]).strip(),
                "pantry": bool(raw.get("pantry")),
            })
    if not items:
        raise RuntimeError("Gemma couldn't build a shopping list. Try again.")
    return items


#  Prices (Kroger) -----------------------------------------------------------------
def price_items(items, price_fn, skip_pantry):
    rows, pantry, cache = [], [], {}
    for it in items:
        if it["pantry"] and skip_pantry:
            pantry.append(it["item"])
            continue
        key = it["search"].lower()
        if key not in cache:
            try:
                cache[key] = price_fn(it["search"])
            except Exception:
                cache[key] = None
        hit = cache[key]
        rows.append({
            "item": it["item"],
            "product": hit["product"] if hit else "",
            "size": hit["size"] if hit else "",
            "price": hit["price"] if hit else None,
            "on_sale": bool(hit and hit["on_sale"]),
        })
    return rows, pantry


#  Gemma writes it up (Python already did the math) --------------------------------
def write_summary(constraints, menu, total, unpriced, calories, model):
    budget = constraints["budget"]
    if budget is None:
        status = "No budget was given."
    elif total <= budget:
        status = f"Estimated total ${total:.2f} is UNDER the ${budget:.2f} budget."
    else:
        status = f"Estimated total ${total:.2f} is OVER the ${budget:.2f} budget by ${total - budget:.2f}."

    goal = calories["goal"]
    if goal is None:
        cal_status = f"No calorie goal was given. One plate is about {calories['per_person']} calories."
    elif calories["status"] == "over":
        cal_status = (f"One plate is about {calories['per_person']} calories, which is OVER the "
                      f"{goal} calorie goal by {calories['difference']}.")
    elif calories["status"] == "unknown":
        cal_status = (f"Known dishes add up to {calories['per_person']} calories, but some dishes have "
                      f"no calorie data, so the goal of {goal} can't be confirmed.")
    else:
        cal_status = (f"One plate is about {calories['per_person']} calories, which is UNDER the "
                      f"{goal} calorie goal by {calories['difference']}.")

    dishes = ", ".join(f"{d['recipe']['name']} ({d['course']})" for d in menu)
    over_budget = budget is not None and total > budget
    over_cal = calories["status"] == "over"
    extra = "2-3 specific cheaper swaps" if over_budget else "one idea for a small extra if there's budget left"
    if over_cal:
        extra += ", and 1-2 lighter swaps or smaller portions to bring calories down"
    prompt = f"""You are a friendly holiday meal planner. Write a short plan in plain Markdown, under 200 words.
Occasion: {constraints['meal']} for {constraints['guests']} guests.
Dietary needs: {constraints['dietary_notes'] or 'none'}
Menu: {dishes}
{status}
{cal_status}
Items with no price found: {', '.join(unpriced) or 'none'}

Include: a one-sentence menu overview, one or two practical prep tips, and {extra}.
Do not invent prices or calorie numbers, and do not change the numbers above.
Say the prices and calories are estimates. Do not give medical or weight-loss advice."""
    return llm.chat(prompt, model, temperature=0.6)


# Orchestration -------------------------------------------------------------------------
def run(text, *, model, search_fn, price_fn, store_label, skip_pantry=True,
        calorie_goal=None, detail_fn=None, on_step=lambda m: None):
    on_step("Reading your request…")
    constraints = parse_request(text, model)
    if calorie_goal:  # a goal typed in the sidebar wins over one parsed from the text
        constraints["calorie_goal"] = int(calorie_goal)

    on_step("Searching for recipes…")
    candidates = gather_candidates(constraints, search_fn)

    on_step("Looking up calories…")
    nutrition.fill_calories(candidates, model)

    on_step("Choosing a menu…")
    menu, reasoning = choose_menu(constraints, candidates, model)
    if detail_fn:
        on_step("Fetching the full recipes…")
        menu = hydrate_menu(menu, detail_fn, constraints["guests"])
    diet_warnings = check_diet(menu, constraints["diet_tag"])
    calories = nutrition.plate_summary(menu, constraints["calorie_goal"])

    on_step("Building your shopping list…")
    items = build_shopping_list(menu, model)

    on_step(f"Checking prices at {store_label}…")
    rows, pantry = price_items(items, price_fn, skip_pantry)
    total = round(sum(r["price"] for r in rows if r["price"] is not None), 2)
    unpriced = [r["item"] for r in rows if r["price"] is None]

    on_step("Writing your plan…")
    summary = write_summary(constraints, menu, total, unpriced, calories, model)

    return {
        "constraints": constraints, "menu": menu, "reasoning": reasoning,
        "calories": calories, "diet_warnings": diet_warnings,
        "rows": rows, "pantry": pantry, "total": total, "unpriced": unpriced,
        "summary": summary, "store": store_label,
    }
