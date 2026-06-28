"""
FridgeForge Recipes — meal suggestion lookup tables + ranking.

Recipes are lookup rows: canonical ingredient keys, meal slots, tags, and a
kid_ok flag. Suggestion = set intersection against inventory, ranked by
coverage; missing ingredients feed the shopping list. Kid profiles apply
HARD constraints (dislikes exclude a recipe outright; likes boost rank);
tags adjust ranking for both kid and adult lanes.

Stdlib only. Import-time tables, pure-function ranking.
"""
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple

MEALS: Tuple[str, ...] = ("breakfast", "lunch", "dinner", "snack")

# (name, meal, ingredients, optional_ingredients, tags, kid_ok)
_R = [
    # breakfast
    ("Scrambled eggs & toast", "breakfast", ("eggs", "bread", "butter"), ("cheese",),
     ("quick", "hot", "classic"), True),
    ("Cereal & milk", "breakfast", ("cereal", "milk"), ("bananas", "berries"),
     ("quick", "no-cook"), True),
    ("Oatmeal with fruit", "breakfast", ("oats", "milk"), ("berries", "bananas", "honey"),
     ("hot", "healthy"), True),
    ("Pancakes", "breakfast", ("pancake_mix", "eggs", "milk"), ("syrup", "berries"),
     ("weekend", "hot", "fun"), True),
    ("Yogurt parfait", "breakfast", ("yogurt",), ("berries", "granola_bars", "honey"),
     ("quick", "no-cook", "healthy"), True),
    ("Bagel & cream cheese", "breakfast", ("bagels", "cream_cheese"), (),
     ("quick", "no-cook"), True),
    ("Breakfast burrito", "breakfast", ("tortillas", "eggs", "cheese"), ("salsa", "bacon"),
     ("hot", "hearty"), True),
    ("Toaster waffles", "breakfast", ("waffles",), ("syrup", "berries"),
     ("quick", "fun"), True),
    # lunch
    ("PB&J sandwich", "lunch", ("bread", "peanut_butter", "jelly"), (),
     ("quick", "no-cook", "classic"), True),
    ("Grilled cheese", "lunch", ("bread", "cheese", "butter"), ("tomatoes",),
     ("hot", "classic"), True),
    ("Turkey sandwich", "lunch", ("bread", "deli_meat"), ("cheese", "lettuce", "tomatoes", "mayo"),
     ("quick", "no-cook"), True),
    ("Quesadilla", "lunch", ("tortillas", "cheese"), ("chicken", "salsa", "peppers"),
     ("hot", "quick", "fun"), True),
    ("Garden salad + protein", "lunch", ("lettuce",), ("chicken", "tomatoes", "cucumbers", "ranch", "cheese"),
     ("healthy", "no-cook", "light"), False),
    ("Hummus veggie wrap", "lunch", ("tortillas", "hummus"), ("cucumbers", "carrots", "peppers", "lettuce"),
     ("healthy", "no-cook", "veggie"), False),
    ("Hot dogs", "lunch", ("hot_dogs", "bread"), ("ketchup", "mustard"),
     ("quick", "hot", "fun"), True),
    # dinner
    ("Spaghetti & sauce", "dinner", ("pasta", "pasta_sauce"), ("ground_beef", "cheese"),
     ("classic", "hot", "hearty"), True),
    ("Tacos", "dinner", ("tortillas", "ground_beef", "cheese"), ("lettuce", "tomatoes", "salsa"),
     ("fun", "hot", "family"), True),
    ("Chicken & rice", "dinner", ("chicken", "rice"), ("broccoli", "carrots", "soy_sauce"),
     ("hearty", "hot", "healthy"), True),
    ("Stir fry", "dinner", ("rice", "soy_sauce"), ("chicken", "tofu", "broccoli", "peppers", "carrots"),
     ("healthy", "hot", "veggie"), False),
    ("Baked fish & potatoes", "dinner", ("fish", "potatoes"), ("lemons", "olive_oil", "broccoli"),
     ("healthy", "hot"), False),
    ("Frozen pizza night", "dinner", ("frozen_pizza",), ("lettuce",),
     ("quick", "fun", "family"), True),
    ("Chicken nuggets & veg", "dinner", ("nuggets",), ("frozen_veg", "ketchup", "carrots"),
     ("quick", "fun"), True),
    ("Bean & cheese burritos", "dinner", ("tortillas", "beans", "cheese"), ("salsa", "rice"),
     ("veggie", "hot", "budget"), True),
    ("Breakfast for dinner", "dinner", ("eggs", "pancake_mix"), ("bacon", "syrup", "berries"),
     ("fun", "family", "weekend"), True),
    # snack
    ("Apple + peanut butter", "snack", ("apples", "peanut_butter"), (),
     ("healthy", "quick", "no-cook"), True),
    ("Cheese & crackers", "snack", ("cheese", "crackers"), (),
     ("quick", "no-cook"), True),
    ("Veggies & ranch", "snack", ("carrots", "ranch"), ("cucumbers", "peppers"),
     ("healthy", "no-cook"), True),
    ("Trail mix", "snack", ("trail_mix",), (),
     ("no-cook", "grab-and-go"), True),
    ("Fruit & yogurt", "snack", ("yogurt", "berries"), ("honey",),
     ("healthy", "no-cook"), True),
    ("Popcorn", "snack", ("popcorn",), (),
     ("quick", "movie"), True),
    ("Banana sushi", "snack", ("bananas", "peanut_butter", "tortillas"), (),
     ("fun", "no-cook", "kid-craft"), True),
]

RECIPES: Tuple[Dict[str, Any], ...] = tuple(
    {"name": n, "meal": m, "ingredients": frozenset(i),
     "optional": frozenset(o), "tags": frozenset(t), "kid_ok": k}
    for n, m, i, o, t, k in _R
)

ALL_TAGS: Tuple[str, ...] = tuple(sorted({t for r in RECIPES for t in r["tags"]}))


def suggest(inventory: Sequence[str], meal: str,
            lane: str = "adult",
            likes: Sequence[str] = (), dislikes: Sequence[str] = (),
            tags: Sequence[str] = (), limit: int = 6) -> List[Dict[str, Any]]:
    """Rank recipes for a meal against the inventory.

    lane='kid': kid_ok recipes only; DISLIKES ARE HARD — any disliked
    ingredient (required or optional-used) excludes the recipe; liked
    ingredients boost rank. Tags boost rank in both lanes.
    """
    inv = set(inventory)
    like_set = {x for x in likes}
    dis_set = {x for x in dislikes}
    tag_set = {x for x in tags}
    out: List[Dict[str, Any]] = []

    for r in RECIPES:
        if r["meal"] != meal:
            continue
        if lane == "kid":
            if not r["kid_ok"]:
                continue
            # HARD constraint: disliked ingredient anywhere in the recipe
            if (r["ingredients"] | r["optional"]) & dis_set:
                continue
        req = r["ingredients"]
        have = req & inv
        coverage = len(have) / len(req) if req else 1.0
        opt_have = r["optional"] & inv
        score = coverage * 100 + len(opt_have) * 4
        if tag_set:
            score += 12 * len(r["tags"] & tag_set)
        if lane == "kid" and like_set:
            score += 10 * len((req | r["optional"]) & like_set)
        missing = sorted(req - inv)
        out.append({
            "name": r["name"], "meal": meal, "lane": lane,
            "score": round(score, 1),
            "coverage": round(coverage, 3),
            "have": sorted(have), "optional_have": sorted(opt_have),
            "missing": missing,
            "makeable_now": not missing,
            "tags": sorted(r["tags"]),
        })

    out.sort(key=lambda x: (-x["makeable_now"], -x["score"]))
    return out[:limit]


def missing_for_meal_plan(inventory: Sequence[str],
                          picks: Sequence[str]) -> List[str]:
    """Union of missing required ingredients across chosen recipe names."""
    inv = set(inventory)
    by_name = {r["name"]: r for r in RECIPES}
    need: set = set()
    for name in picks:
        r = by_name.get(name)
        if r:
            need |= (r["ingredients"] - inv)
    return sorted(need)
