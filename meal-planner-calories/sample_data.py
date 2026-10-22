"""Demo mode: sample recipes and prices so the app works with no API keys.
Gemma still runs for real; only the Tasty and Kroger data is canned.

Each course has a pool of 12 recipes. search() returns a random 6 per call
(planner.py considers at most 6 per course), so repeat runs give different menus.
Set DEMO_SEED=42 in .env for repeatable results when presenting.

Every sample recipe also has made-up per-serving calories so the calorie feature works offline."""
import os
import random

STORE_LABEL = "Demo store (sample prices, not real Kroger data)"

_rng = random.Random(int(os.getenv("DEMO_SEED"))) if os.getenv("DEMO_SEED") else random.Random()


def _r(rid, name, servings, diet, ingredients):
    """diet is 'meat', 'veg' (vegetarian), or 'vegan'."""
    return {
        "id": rid, "name": name, "servings": servings,
        "vegetarian": diet in ("veg", "vegan"), "vegan": diet == "vegan",
        "ingredients": ingredients, "image": None, "url": None,
    }


RECIPES = {
    "main": [
        _r("m1", "Herb-Roasted Turkey Breast", 8, "meat", [
            "1 bone-in turkey breast (5 lb)", "4 tbsp butter, softened",
            "2 tbsp fresh thyme", "1 tbsp salt", "1 tsp black pepper", "1 cup chicken broth"]),
        _r("m2", "Stuffed Acorn Squash", 4, "vegan", [
            "2 acorn squash", "1 cup cooked wild rice", "1/2 cup dried cranberries",
            "1/2 cup chopped pecans", "2 tbsp olive oil", "1 tsp salt"]),
        _r("m3", "Honey-Glazed Ham", 10, "meat", [
            "1 spiral-cut ham (8 lb)", "1/2 cup honey", "1/4 cup brown sugar",
            "2 tbsp Dijon mustard"]),
        _r("m4", "Cranberry-Orange Roast Chicken", 6, "meat", [
            "1 whole chicken (4 lb)", "1 orange", "1 cup fresh cranberries",
            "3 tbsp olive oil", "2 tbsp fresh rosemary", "1 tsp salt"]),
        _r("m5", "Mushroom Wellington", 6, "veg", [
            "2 sheets puff pastry", "1 lb cremini mushrooms", "1 yellow onion",
            "2 tbsp olive oil", "2 cloves garlic", "2 tbsp fresh thyme"]),
        _r("m6", "Maple-Glazed Salmon", 6, "meat", [
            "2 lb salmon fillet", "1/4 cup maple syrup", "2 tbsp Dijon mustard",
            "1 lemon", "1 tbsp olive oil", "1 tsp black pepper"]),
        _r("m7", "Braised Beef Brisket", 10, "meat", [
            "4 lb beef brisket", "2 yellow onions", "4 carrots", "3 cloves garlic",
            "2 cups beef broth", "1 can tomato paste", "2 tbsp fresh thyme"]),
        _r("m8", "Lentil Shepherd's Pie", 6, "vegan", [
            "1 1/2 cups green lentils", "2 carrots", "1 yellow onion", "1 cup frozen peas",
            "2 lb russet potatoes", "2 tbsp olive oil", "2 cups vegetable broth"]),
        _r("m9", "Roasted Cornish Game Hens", 4, "meat", [
            "4 Cornish game hens", "3 tbsp butter", "1 lemon", "4 cloves garlic",
            "2 tbsp fresh rosemary", "1 tsp salt"]),
        _r("m10", "Butternut Squash Risotto", 6, "veg", [
            "1 butternut squash", "1 1/2 cups arborio rice", "4 cups vegetable broth",
            "1/2 cup grated Parmesan", "1 yellow onion", "2 tbsp butter"]),
        _r("m11", "Spinach and Ricotta Stuffed Shells", 8, "veg", [
            "1 box jumbo pasta shells", "15 oz ricotta cheese", "10 oz frozen spinach",
            "2 cups shredded mozzarella", "1 jar marinara sauce", "1 egg"]),
        _r("m12", "Chickpea and Sweet Potato Curry", 6, "vegan", [
            "2 cans chickpeas", "2 sweet potatoes", "1 can coconut milk",
            "1 yellow onion", "2 tbsp curry powder", "1 can diced tomatoes", "2 cups cooked rice"]),
    ],
    "side": [
        _r("s1", "Garlic Mashed Potatoes", 6, "veg", [
            "3 lb russet potatoes", "4 tbsp butter", "1 cup whole milk",
            "4 cloves garlic", "1 tsp salt"]),
        _r("s2", "Green Bean Casserole", 6, "veg", [
            "1 lb green beans", "1 can cream of mushroom soup",
            "1 cup crispy fried onions", "1/2 cup whole milk"]),
        _r("s3", "Cornbread Stuffing", 8, "meat", [
            "1 box cornbread stuffing mix", "2 cups chicken broth", "1 yellow onion",
            "3 celery stalks", "4 tbsp butter"]),
        _r("s4", "Roasted Brussels Sprouts", 6, "vegan", [
            "2 lb Brussels sprouts", "2 tbsp olive oil", "1/4 cup balsamic vinegar",
            "1/3 cup dried cranberries", "1/3 cup chopped pecans"]),
        _r("s5", "Sweet Potato Casserole", 8, "veg", [
            "3 lb sweet potatoes", "1/4 cup brown sugar", "3 tbsp butter",
            "1/2 cup milk", "1 cup vegetarian mini marshmallows", "1 tsp cinnamon"]),
        _r("s6", "Cranberry-Apple Sauce", 8, "vegan", [
            "12 oz fresh cranberries", "2 apples", "3/4 cup sugar",
            "1 cup orange juice", "1 tsp orange zest"]),
        _r("s7", "Garlic Parmesan Roasted Broccoli", 6, "veg", [
            "2 lb broccoli", "3 tbsp olive oil", "4 cloves garlic",
            "1/2 cup grated Parmesan", "1 lemon"]),
        _r("s8", "Maple Roasted Carrots", 6, "vegan", [
            "2 lb carrots", "3 tbsp maple syrup", "2 tbsp olive oil",
            "1 tbsp fresh thyme", "1 tsp salt"]),
        _r("s9", "Baked Macaroni and Cheese", 8, "veg", [
            "1 lb elbow macaroni", "4 cups shredded cheddar", "3 cups whole milk",
            "4 tbsp butter", "1/4 cup flour", "1 cup breadcrumbs"]),
        _r("s10", "Wild Rice Pilaf", 6, "vegan", [
            "1 1/2 cups wild rice blend", "3 cups vegetable broth", "1 yellow onion",
            "3 celery stalks", "2 tbsp olive oil", "1/2 cup dried cranberries"]),
        _r("s11", "Buttermilk Biscuits", 8, "veg", [
            "2 1/2 cups flour", "1 cup buttermilk", "1/2 cup cold butter",
            "1 tbsp baking powder", "1 tsp sugar"]),
        _r("s12", "Collard Greens with Smoked Turkey", 8, "meat", [
            "2 lb collard greens", "1 smoked turkey leg", "1 yellow onion",
            "3 cups chicken broth", "3 cloves garlic", "2 tbsp apple cider vinegar"]),
    ],
    "dessert": [
        _r("d1", "Classic Pumpkin Pie", 8, "veg", [
            "1 can pumpkin puree (15 oz)", "1 can evaporated milk", "2 eggs",
            "1 frozen pie crust", "3/4 cup sugar", "1 tsp cinnamon"]),
        _r("d2", "Apple Crisp", 8, "veg", [
            "6 apples", "1 cup rolled oats", "1/2 cup brown sugar",
            "1/2 cup butter", "1 tsp cinnamon"]),
        _r("d3", "Sweet Potato Pie", 8, "veg", [
            "2 lb sweet potatoes", "1/2 cup butter", "1 cup sugar", "2 eggs",
            "1 frozen pie crust", "1 tsp vanilla extract"]),
        _r("d4", "Pecan Pie", 8, "veg", [
            "1 frozen pie crust", "1 1/2 cups pecans", "3 eggs",
            "1 cup corn syrup", "1/2 cup brown sugar", "2 tbsp butter"]),
        _r("d5", "Cranberry Orange Bars", 12, "veg", [
            "2 cups fresh cranberries", "2 oranges", "1 1/2 cups flour",
            "1 cup sugar", "1/2 cup butter", "2 eggs"]),
        _r("d6", "Gingerbread Cake", 10, "veg", [
            "2 cups flour", "1/2 cup molasses", "1/2 cup brown sugar",
            "1/2 cup butter", "1 egg", "1 tsp ground ginger", "1 tsp cinnamon"]),
        _r("d7", "Peppermint Brownies", 16, "veg", [
            "1 box brownie mix", "2 eggs", "1/2 cup vegetable oil",
            "1 cup crushed peppermint candies", "1 cup chocolate chips"]),
        _r("d8", "Cinnamon Baked Apples", 6, "vegan", [
            "6 baking apples", "1/2 cup rolled oats", "1/3 cup brown sugar",
            "3 tbsp coconut oil", "1 tsp cinnamon", "1/2 cup chopped walnuts"]),
        _r("d9", "Peach Cobbler", 10, "veg", [
            "6 cups sliced peaches", "1 cup flour", "1 cup sugar",
            "1 cup milk", "1/2 cup butter", "1 tsp cinnamon"]),
        _r("d10", "Banana Pudding", 10, "veg", [
            "1 box vanilla pudding mix", "3 cups whole milk", "1 box vanilla wafers",
            "5 bananas", "1 tub whipped topping"]),
        _r("d11", "Chocolate Avocado Mousse", 6, "vegan", [
            "3 ripe avocados", "1/2 cup cocoa powder", "1/2 cup maple syrup",
            "1/4 cup almond milk", "1 tsp vanilla extract", "1 cup raspberries"]),
        _r("d12", "Red Velvet Cake", 12, "veg", [
            "2 1/2 cups flour", "1 1/2 cups sugar", "1 cup buttermilk", "2 eggs",
            "2 tbsp red food coloring", "8 oz cream cheese", "1/2 cup butter"]),
    ],
}


def search(term, diet_tag, course):
    pool = RECIPES.get(course, [])
    if diet_tag == "vegan":
        pool = [r for r in pool if r["vegan"]]
    elif diet_tag == "vegetarian":
        pool = [r for r in pool if r["vegetarian"]]
    return _rng.sample(pool, min(len(pool), 6))


def price(term):
    """Deterministic fake price so demos are repeatable."""
    h = sum(ord(c) for c in term.lower())
    return {
        "product": f"{term.title()} (sample)",
        "price": round(1.49 + (h % 70) / 10, 2),
        "size": "sample",
        "on_sale": False,
    }


# Illustrative per-serving calories for demo mode only (not real nutrition data).
_SAMPLE_CALORIES = {
    "m1": 320, "m2": 380, "m3": 290, "m4": 410, "m5": 450, "m6": 380,
    "m7": 480, "m8": 360, "m9": 520, "m10": 430, "m11": 420, "m12": 440,
    "s1": 210, "s2": 160, "s3": 250, "s4": 150, "s5": 330, "s6": 140,
    "s7": 170, "s8": 130, "s9": 450, "s10": 220, "s11": 260, "s12": 180,
    "d1": 320, "d2": 340, "d3": 380, "d4": 500, "d5": 240, "d6": 310,
    "d7": 280, "d8": 210, "d9": 360, "d10": 390, "d11": 260, "d12": 480,
}
for _pool in RECIPES.values():
    for _recipe in _pool:
        _recipe["nutrition"] = {"calories": _SAMPLE_CALORIES[_recipe["id"]], "source": "Sample data"}
