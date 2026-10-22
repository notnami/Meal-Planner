# Holiday Meal Planner with Calories (Gemma + Tasty + Kroger)

A local-AI demo. Gemma (via Ollama) turns a plain-English request into a menu,
shopping list, and estimated cost. Python calls the APIs; Gemma does the language work.

```
"Thanksgiving dinner for 6, one vegetarian, budget $100, under 900 calories per person"
  1. Gemma parses the request into JSON         (language -> structure)
  2. Tasty returns candidate recipes             (API)
  3. Calories per serving: Tasty data, or one batched Gemma estimate when missing
  4. Gemma picks a main, side, and dessert       (reasoning over constraints)
     Python then checks the calorie math and swaps dishes if the plate is over the goal
  5. Gemma merges ingredients into one list      (cleanup)
  6. Kroger prices each item at a nearby store   (API)
  7. Gemma writes the plan; Python did the math  (summarizing)
```

## Run it

```bash
ollama pull gemma3          # or gemma3:12b if your machine can handle it
pip install -r requirements.txt
cp .env.example .env        # optional: add API keys, or use Demo mode
streamlit run app.py
```

**Demo mode** (on by default when keys are missing) uses sample recipes and prices,
so you can present reliably without Wi-Fi or rate limits. Gemma still runs live.

## Recipe sources (pick in the sidebar)
- **MyPlate.food** (default): free, no key. About 1,000 USDA MyPlate Kitchen recipes with real USDA nutrition.
  Search results already include calories per serving; the 3 chosen dishes get one full-recipe fetch each.
  Free-tier limits: 20 requests/minute and 100 full recipes/day per IP. Live use only: do not copy or mirror the catalog.
  The collection is healthy, everyday USDA recipes, so expect fewer classic holiday dishes than Tasty.
  There is no vegetarian filter, so the app checks ingredients and warns if a dish looks wrong.
- **Tasty**: needs a RapidAPI key; nutrition data is missing on some recipes (Gemma estimates those).
- **Demo**: sample recipes and calories, works offline.

## How calories work
- MyPlate.food and Tasty report per-serving calories (Tasty not for every recipe). Missing ones are estimated by Gemma
  from the ingredient list and labeled "AI estimate" in the table.
- One plate = one serving of the main + side + dessert. Python adds it up; Gemma never does the arithmetic.
- Set a goal in your request ("under 800 calories per person") or in the sidebar (the sidebar wins).
- Demo mode uses made-up sample calories. Figures are approximate and not medical or dietary advice.

## API keys
- **Tasty**: subscribe on RapidAPI, then put the key in `TASTY_RAPIDAPI_KEY`.
- **Kroger**: create an app at developer.kroger.com, then set `KROGER_CLIENT_ID` and `KROGER_CLIENT_SECRET`.
  The app looks up the nearest store from the ZIP in the sidebar (default 30144).
- Check current docs and rate limits; they change.

## Accessibility notes
- Palette: KSU black `#000000` and gold `#FDBB30`, plus white and light gray `#D0D3D4`.
- Contrast (WCAG 2.1 formula): gold on black 12.3:1, white on black 21:1, light gray on black 14.0:1,
  black text on gold buttons 12.3:1. All exceed AAA (7:1) for text. Gold is never used as text on a light background.
- Status messages use words and icons, not color alone.
- Visible white focus ring on every control, 44px button targets, 2px input borders, `prefers-reduced-motion` respected.
- Images get descriptive alt text; the shopping list is a real table with header cells.
- Known gaps: Streamlit controls the page `lang` attribute and some internal markup. Before an official
  presentation, check with a screen reader (NVDA or VoiceOver), keyboard-only navigation, and the WebAIM contrast checker.

## Ideas to extend
- "Swap this ingredient" follow-up (multi-turn chat)
- Compare gemma3 4B vs 12B outputs side by side
- Show protein, carbs, and fat (Tasty already returns them; tasty.py keeps them)
- Per-guest portions (e.g. smaller dessert servings) instead of one serving each
- Add a light, high-contrast theme toggle
