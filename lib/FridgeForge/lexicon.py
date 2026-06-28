"""
FridgeForge Lexicon — the product lookup tables.

All matching is lookup, not compute: a canonical product key, its category,
its aliases (what people/photos/filenames call it), and the staples template
that seeds the shopping list. Import-time, read-only.
"""
from typing import Dict, FrozenSet, List, Optional, Tuple

# key: (category, aliases)
PRODUCTS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    # dairy
    "milk":        ("dairy",     ("whole milk", "2%", "skim", "oat milk", "almond milk")),
    "butter":      ("dairy",     ("margarine",)),
    "cheese":      ("dairy",     ("cheddar", "mozzarella", "american", "swiss", "shredded cheese")),
    "yogurt":      ("dairy",     ("greek yogurt", "gogurt")),
    "eggs":        ("dairy",     ("egg", "dozen eggs")),
    "cream_cheese": ("dairy",    ("philadelphia",)),
    # produce
    "apples":      ("produce",   ("apple", "gala", "fuji")),
    "bananas":     ("produce",   ("banana",)),
    "berries":     ("produce",   ("strawberries", "blueberries", "raspberries")),
    "grapes":      ("produce",   ("grape",)),
    "lettuce":     ("produce",   ("salad", "greens", "romaine", "spinach")),
    "tomatoes":    ("produce",   ("tomato", "cherry tomatoes")),
    "carrots":     ("produce",   ("carrot", "baby carrots")),
    "potatoes":    ("produce",   ("potato", "russet")),
    "onions":      ("produce",   ("onion",)),
    "peppers":     ("produce",   ("bell pepper", "pepper")),
    "broccoli":    ("produce",   ()),
    "cucumbers":   ("produce",   ("cucumber",)),
    "avocado":     ("produce",   ("avocados",)),
    "lemons":      ("produce",   ("lemon", "lime", "limes")),
    # protein
    "chicken":     ("protein",   ("chicken breast", "chicken thighs", "rotisserie")),
    "ground_beef": ("protein",   ("beef", "hamburger meat")),
    "turkey":      ("protein",   ("deli turkey", "turkey slices")),
    "ham":         ("protein",   ("deli ham",)),
    "bacon":       ("protein",   ()),
    "hot_dogs":    ("protein",   ("hotdogs", "franks")),
    "fish":        ("protein",   ("salmon", "tilapia", "fish sticks")),
    "tofu":        ("protein",   ()),
    "beans":       ("protein",   ("black beans", "chickpeas", "kidney beans")),
    "deli_meat":   ("protein",   ("lunch meat", "cold cuts")),
    # grains
    "bread":       ("grain",     ("loaf", "sandwich bread", "whole wheat")),
    "tortillas":   ("grain",     ("tortilla", "wraps")),
    "pasta":       ("grain",     ("spaghetti", "penne", "noodles", "mac")),
    "rice":        ("grain",     ("white rice", "brown rice")),
    "cereal":      ("grain",     ("cheerios", "cornflakes")),
    "oats":        ("grain",     ("oatmeal", "rolled oats")),
    "bagels":      ("grain",     ("bagel",)),
    "pancake_mix": ("grain",     ("waffle mix", "bisquick")),
    "crackers":    ("grain",     ("saltines", "ritz", "goldfish")),
    # condiments / pantry
    "peanut_butter": ("condiment", ("pb", "almond butter", "nut butter")),
    "jelly":       ("condiment", ("jam", "preserves")),
    "ketchup":     ("condiment", ()),
    "mustard":     ("condiment", ()),
    "mayo":        ("condiment", ("mayonnaise",)),
    "salsa":       ("condiment", ()),
    "pasta_sauce": ("condiment", ("marinara", "tomato sauce", "red sauce")),
    "soy_sauce":   ("condiment", ()),
    "olive_oil":   ("condiment", ("oil", "vegetable oil", "cooking oil")),
    "honey":       ("condiment", ()),
    "syrup":       ("condiment", ("maple syrup",)),
    "hummus":      ("condiment", ()),
    "ranch":       ("condiment", ("ranch dressing", "dressing")),
    # snacks
    "chips":       ("snack",     ("tortilla chips", "potato chips")),
    "pretzels":    ("snack",     ()),
    "popcorn":     ("snack",     ()),
    "granola_bars": ("snack",    ("granola bar", "cereal bar")),
    "cookies":     ("snack",     ("oreos",)),
    "fruit_snacks": ("snack",    ("gummies",)),
    "trail_mix":   ("snack",     ("nuts", "almonds", "mixed nuts")),
    # beverage
    "juice":       ("beverage",  ("orange juice", "oj", "apple juice")),
    "soda":        ("beverage",  ("pop", "cola")),
    "coffee":      ("beverage",  ("coffee grounds", "k-cups")),
    "tea":         ("beverage",  ()),
    # frozen
    "frozen_pizza": ("frozen",   ("pizza",)),
    "frozen_veg":  ("frozen",    ("frozen vegetables", "frozen peas", "frozen corn")),
    "ice_cream":   ("frozen",    ()),
    "frozen_fruit": ("frozen",   ("frozen berries",)),
    "nuggets":     ("frozen",    ("chicken nuggets", "tenders")),
    "waffles":     ("frozen",    ("eggo", "frozen waffles")),
}

CATEGORIES: Tuple[str, ...] = ("dairy", "produce", "protein", "grain",
                               "condiment", "snack", "beverage", "frozen")

# alias -> canonical key (flattened lookup, import-time)
ALIAS_INDEX: Dict[str, str] = {}
for _key, (_cat, _aliases) in PRODUCTS.items():
    ALIAS_INDEX[_key.replace("_", " ")] = _key
    ALIAS_INDEX[_key] = _key
    for _a in _aliases:
        ALIAS_INDEX[_a.lower()] = _key

# The staples template: what a stocked kitchen keeps on hand.
# The shopping list seeds from (staples - inventory).
STAPLES_TEMPLATE: Tuple[str, ...] = (
    "milk", "eggs", "butter", "bread", "cheese",
    "apples", "bananas", "carrots", "lettuce", "tomatoes", "onions",
    "chicken", "deli_meat", "beans",
    "pasta", "rice", "cereal", "tortillas",
    "peanut_butter", "jelly", "pasta_sauce", "olive_oil", "ketchup",
    "juice", "granola_bars", "frozen_veg",
)


def match_token(token: str) -> Optional[str]:
    """Resolve one free-text token to a canonical product key (lookup)."""
    t = token.strip().lower().replace("_", " ").replace("-", " ")
    if not t:
        return None
    if t in ALIAS_INDEX:
        return ALIAS_INDEX[t]
    # singular/plural fallback
    if t.endswith("s") and t[:-1] in ALIAS_INDEX:
        return ALIAS_INDEX[t[:-1]]
    if t + "s" in ALIAS_INDEX:
        return ALIAS_INDEX[t + "s"]
    # substring pass (longest alias first, so "greek yogurt" beats "yogurt")
    for alias in sorted(ALIAS_INDEX, key=len, reverse=True):
        if alias in t or t in alias:
            return ALIAS_INDEX[alias]
    return None


def match_text(text: str) -> List[str]:
    """Resolve free text / a filename / a caption into product keys."""
    seps = ",;/+&\n\t._()[]0123456789"
    clean = "".join(" " if c in seps else c for c in text.lower())
    found: List[str] = []
    # try multi-word aliases against the whole string first
    for alias in sorted(ALIAS_INDEX, key=len, reverse=True):
        if " " in alias and alias in clean:
            k = ALIAS_INDEX[alias]
            if k not in found:
                found.append(k)
    for tok in clean.split():
        k = match_token(tok)
        if k and k not in found:
            found.append(k)
    return found


def category_of(key: str) -> str:
    return PRODUCTS.get(key, ("other", ()))[0]
