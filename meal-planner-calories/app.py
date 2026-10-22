import html
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import kroger  # noqa: E402
import llm  # noqa: E402
import myplate  # noqa: E402
import planner  # noqa: E402
import sample_data  # noqa: E402
import tasty  # noqa: E402

st.set_page_config(page_title="Holiday Meal Planner", page_icon="🦉", layout="centered")

# KSU black and gold. Contrast ratios (WCAG 2.1 formula):
#   gold #FDBB30 on black #000000 ........ 12.3:1   (AA needs 4.5, AAA needs 7)
#   gold on surface #1A1A1A ............... 10.2:1
#   white on black ........................ 21:1
#   light gray #D0D3D4 on black ........... 14.0:1
#   black text on gold buttons ............ 12.3:1

CSS = """
<style>
:root { --gold:#FDBB30; --black:#000000; --surface:#1A1A1A; --text:#FFFFFF; --muted:#D0D3D4;
        --field:#FFFFFF; --placeholder:#4A4A4A; }
.stApp { background: var(--black); color: var(--text); }
h1, h2, h3 { color: var(--gold) !important; }
h1 { border-bottom: 4px solid var(--gold); padding-bottom: .4rem; }
h2 { border-left: 6px solid var(--gold); padding-left: .6rem; }
a, a:visited { color: var(--gold) !important; text-decoration: underline; }
a:hover { color: var(--text) !important; }
p, li, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: var(--text); }
[data-testid="stCaptionContainer"] { color: var(--muted); }

/* Buttons: black on gold, 44px minimum target. The label sits in an inner <p>, so style it too. */
.stButton > button, [data-testid^="stBaseButton"] {
  background: var(--gold) !important; color: var(--black) !important;
  border: 2px solid var(--gold) !important; font-weight: 700; min-height: 44px;
}
.stButton > button *, [data-testid^="stBaseButton"] * { color: var(--black) !important; }
.stButton > button:hover:not(:disabled) { background: var(--text) !important; border-color: var(--text) !important; }
.stButton > button:disabled { background: var(--surface) !important; border-color: var(--muted) !important; }
.stButton > button:disabled * { color: var(--muted) !important; }

/* Inputs: white field, BLACK text (21:1), 2px borders. Plain tag selectors so any Streamlit version matches. */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="base-input"], [data-baseweb="select"] > div {
  border: 2px solid var(--muted) !important; background: var(--field) !important;
}
input, textarea {
  color: var(--black) !important; -webkit-text-fill-color: var(--black) !important;
  caret-color: var(--black) !important;
}
input[type="text"], input[type="number"], textarea { background-color: var(--field) !important; }
input[type="checkbox"] { -webkit-text-fill-color: initial !important; }
[data-baseweb="select"] div, [data-baseweb="select"] span { color: var(--black) !important; }
input::placeholder, textarea::placeholder {
  color: var(--placeholder) !important; -webkit-text-fill-color: var(--placeholder) !important; opacity: 1 !important;
}
/* Number box +/- buttons and dropdown options: black on white, gold when hovered or selected */
.stNumberInput button, .stNumberInput button * { background: var(--field) !important; color: var(--black) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: var(--field) !important; }
[data-baseweb="popover"] li, [data-baseweb="menu"] li { background: var(--field) !important; color: var(--black) !important; }
[data-baseweb="menu"] li:hover, [data-baseweb="menu"] li[aria-selected="true"] {
  background: var(--gold) !important; color: var(--black) !important;
}

/* Visible keyboard focus everywhere */
:focus-visible { outline: 3px solid var(--text) !important; outline-offset: 3px !important; }
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within { border-color: var(--gold) !important; }

/* Status boxes: same look for every state; meaning is carried by the text and icon, not color */
[data-testid="stAlert"] { background: var(--surface) !important; border: 2px solid var(--gold); color: var(--text) !important; }
[data-testid="stAlert"] p { color: var(--text) !important; }
[data-testid="stSidebar"] { background: var(--surface); border-right: 2px solid var(--gold); }
[data-testid="stExpander"] { border: 2px solid var(--muted); }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color: var(--text) !important; }

/* Tables: set both text and background so the page theme can't turn cells white-on-white */
table { border-collapse: collapse; width: 100%; }
th { background: var(--gold) !important; color: var(--black) !important; text-align: left; }
td { background: var(--black) !important; color: var(--text) !important; }
td, th { border: 1px solid var(--muted) !important; padding: .5rem !important; }

img.dish { max-width: 100%; border: 3px solid var(--gold); border-radius: 4px; }

@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


SOURCE_MYPLATE = "MyPlate.food (no key, USDA nutrition)"
SOURCE_TASTY = "Tasty (needs API key)"
SOURCE_DEMO = "Demo (sample recipes)"


def build_backends(source, sample_prices, zip_code):
    """Return (search_fn, detail_fn, price_fn, store_label)."""
    detail_fn = None
    if source == SOURCE_DEMO:
        search_fn = sample_data.search
    elif source == SOURCE_MYPLATE:
        search_fn = lambda term, tag, course: myplate.search(term, tag, course)  # noqa: E731
        detail_fn = lambda recipe: myplate.get_recipe(recipe["id"])  # noqa: E731
    else:
        search_fn = lambda term, tag, course: tasty.search(term, tag)  # noqa: E731

    if sample_prices:
        return search_fn, detail_fn, sample_data.price, sample_data.STORE_LABEL
    client = kroger.KrogerClient()
    store = client.find_store(zip_code)
    return (
        search_fn,
        detail_fn,
        lambda term: client.price(term, store["id"]),
        f"{store['name']}, {store['address']}",
    )


def money(value):
    return f"${value:,.2f}"


def render_calories(cal, guests):
    st.header("Calories")
    st.caption("Calories are per serving. Each guest is assumed to eat one serving of each dish.")
    st.table([
        {
            "Course": row["course"].title(),
            "Dish": row["name"],
            "Calories per serving": row["calories"] if row["calories"] else "Not available",
            "Source": row["source"],
        }
        for row in cal["rows"]
    ])
    st.subheader(f"One plate: about {cal['per_person']:,} calories")
    if cal["unknown"]:
        st.write("**No calorie data for:** " + ", ".join(cal["unknown"]) + " (not counted in the plate total).")
    goal, diff = cal["goal"], cal["difference"]
    if cal["status"] == "none":
        st.info("ℹ️ No calorie goal given. Add one in your request or in the sidebar to check against it.")
    elif cal["status"] == "under":
        st.success(f"✅ Within goal: {cal['per_person']:,} of {goal:,} calories ({diff:,} to spare).")
    elif cal["status"] == "unknown":
        st.warning(f"⚠️ Can't confirm the goal: known dishes are {cal['per_person']:,} of {goal:,} calories, but some data is missing.")
    else:
        st.warning(f"⚠️ Over goal: {cal['per_person']:,} against {goal:,} calories, over by {diff:,}.")
    if any(r["source"] == "AI estimate" for r in cal["rows"]):
        st.write("Rows marked AI estimate were estimated by the local model from the ingredient list.")
    st.caption("Calorie figures are approximate and for general information only. They are not medical or dietary advice.")


def render(result):
    c = result["constraints"]
    st.header("Your plan")
    with st.expander("What Gemma understood from your request"):
        st.markdown(
            f"- **Occasion:** {c['meal']}\n"
            f"- **Guests:** {c['guests']}\n"
            f"- **Budget:** {money(c['budget']) if c['budget'] else 'not specified'}\n"
            f"- **Calorie goal:** {str(c['calorie_goal']) + ' per person (whole meal)' if c['calorie_goal'] else 'not specified'}\n"
            f"- **Dietary needs:** {c['dietary_notes'] or (c['diet_tag'] or 'none')}"
        )
        if result["reasoning"]:
            st.markdown(f"**Why this menu:** {result['reasoning']}")

    st.header("Menu")
    for dish in result["menu"]:
        r = dish["recipe"]
        st.subheader(f"{dish['course'].title()}: {r['name']}")
        if r.get("image"):
            st.markdown(
                f'<img class="dish" src="{html.escape(r["image"])}" '
                f'alt="Photo of {html.escape(r["name"])}">',
                unsafe_allow_html=True,
            )
        if r.get("servings") and dish["scale"]:
            st.write(
                f"Recipe serves {r['servings']}. For {c['guests']} guests, "
                f"scale the recipe by about {dish['scale']}×."
            )
        if r.get("url"):
            st.markdown(f"[View the full recipe on {r.get('source_name', 'the source site')} (opens in a new tab)]({r['url']})")

    for warning in result.get("diet_warnings", []):
        st.warning(f"⚠️ Check this dish: {warning}")
    if any(d["recipe"].get("source_name") == myplate.SOURCE_NAME for d in result["menu"]):
        st.caption("Recipes and nutrition: USDA MyPlate Kitchen (public domain), via myplate.food. Not affiliated with the USDA.")
    render_calories(result["calories"], c["guests"])

    st.header("Shopping list and estimated cost")
    st.caption(f"Prices from: {result['store']}. One package per item; prices are estimates.")
    st.table([
        {
            "Item": row["item"],
            "Product": row["product"] or "Not found",
            "Size": row["size"],
            "Est. price": (money(row["price"]) + (" (sale)" if row["on_sale"] else ""))
            if row["price"] is not None else "No price found",
        }
        for row in result["rows"]
    ])
    if result["pantry"]:
        st.write("**Assumed on hand:** " + ", ".join(result["pantry"]))

    total, budget = result["total"], c["budget"]
    st.subheader(f"Estimated total: {money(total)}")
    if budget is None:
        st.info(f"ℹ️ No budget given. Estimated total is {money(total)}.")
    elif total <= budget:
        st.success(f"✅ Under budget: {money(total)} of {money(budget)} ({money(budget - total)} to spare).")
    else:
        st.warning(f"⚠️ Over budget: {money(total)} against {money(budget)}, over by {money(total - budget)}.")
    if result["unpriced"]:
        st.write("**No price found for:** " + ", ".join(result["unpriced"]) + " (not counted in the total).")

    st.header("Planning notes")
    st.markdown(result["summary"])
    st.caption("Generated by a local AI model. Check recipes and allergens yourself before cooking.")


# ---------- Page ----------
st.title("🦉 Holiday Meal Planner")
st.write(
    "Describe your holiday meal. A local Gemma model reads your request, "
    "picks recipes from Tasty, counts calories, and estimates the grocery bill with Kroger prices."
)

with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", value=llm.DEFAULT_MODEL, help="For example gemma3 or gemma3:12b")
    zip_code = st.text_input("ZIP code for Kroger prices", value="30144")
    source = st.selectbox(
        "Recipe source", [SOURCE_MYPLATE, SOURCE_TASTY, SOURCE_DEMO],
        help="MyPlate.food is free with no key and has USDA nutrition data. Tasty needs a RapidAPI key.",
    )
    kroger_ready = all(os.getenv(k) for k in ("KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET"))
    sample_prices = st.checkbox("Use sample prices (no Kroger keys needed)", value=not kroger_ready)
    skip_pantry = st.checkbox("Assume pantry staples are on hand", value=True)
    calorie_goal = st.number_input(
        "Calorie goal per person (whole meal)", min_value=0, max_value=5000, value=0, step=50,
        help="0 means no goal. If you set one here it overrides a goal written in your request.",
    )

ready, problem = llm.ollama_ready(model)
if not ready:
    st.error(f"Error: {problem}")

request = st.text_area(
    "Describe your meal",
    placeholder="Thanksgiving dinner for 6, one vegetarian, budget $100, under 900 calories per person",
    height=110,
)

if st.button("Plan my meal", type="primary", disabled=not ready or not request.strip()):
    with st.status("Planning your meal…", expanded=True) as status:
        try:
            search_fn, detail_fn, price_fn, store_label = build_backends(source, sample_prices, zip_code.strip())
            st.session_state["result"] = planner.run(
                request, model=model, search_fn=search_fn, price_fn=price_fn,
                store_label=store_label, skip_pantry=skip_pantry,
                calorie_goal=calorie_goal or None, detail_fn=detail_fn, on_step=st.write,
            )
            status.update(label="Done. Your plan is ready below.", state="complete")
        except Exception as e:
            st.session_state.pop("result", None)
            status.update(label="Something went wrong", state="error")
            st.error(f"Error: {e}")

if "result" in st.session_state:
    render(st.session_state["result"])
