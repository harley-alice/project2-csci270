"""Source-class -> merged-class mapping. Edit this file to change the merge.

Keys are the folder names under data/raw/. A value of None drops that label
(the box is removed; images left with no boxes are dropped too).
Every source class must appear here, or clean_and_merge.py will refuse to run.
"""

CLASS_MAP = {
    "Fridge objects.v2i.yolov8": {
        "avocado": "avocado",
        "bacon": "bacon",
        "butter": "butter",
        "cheese": "cheese",
        "eggs": "egg",
        "lemon": "lemon",
        "milk": "milk",
        "pepper": "bell_pepper",
        "tomatoes": "tomato",
        "yogurt": "yogurt",
    },
    "Hien_Fridge.v12i.yolov8": {
        "apple": "apple",
        "egg": "egg",
        "milk_carton": "milk",
        "others": None,          # catch-all, no usable meaning
        "soda_can": None,        # not a FoodKeeper perishable
        "yogurt_container": "yogurt",
    },
    "aicook.v1i.yolov8": {
        "apple": "apple",
        "banana": "banana",
        "beef": "beef",
        "blueberries": "blueberries",
        "bread": "bread",
        "butter": "butter",
        "carrot": "carrot",
        "cheese": "cheese",
        "chicken": "chicken",
        "chicken_breast": "chicken",
        "chocolate": "chocolate",
        "corn": "corn",
        "eggs": "egg",
        "flour": "flour",
        "goat_cheese": "goat_cheese",
        "green_beans": "green_beans",
        "ground_beef": "beef",
        "ham": "ham",
        "heavy_cream": "cream",
        "lime": "lime",
        "milk": "milk",
        "mushrooms": "mushrooms",
        "onion": "onion",
        "potato": "potato",
        "shrimp": "shrimp",
        "spinach": "spinach",
        "strawberries": "strawberries",
        "sugar": "sugar",
        "sweet_potato": "sweet_potato",
        "tomato": "tomato",
    },
}

# Final class order (index = class id in the cleaned dataset).
# Hien 'others' boxes relabelled one by one (see others_relabel.py / others_boxmap.json,
# keyed "<split>/<label stem>/<line index>"). Boxes not in the file stay dropped.
OTHERS_DATASET = "Hien_Fridge.v12i.yolov8"
OTHERS_CLASS = "others"
OTHERS_BOXMAP_FILE = "others_boxmap.json"
EXTRA_CLASSES = ["jar", "mango", "orange", "persimmon", "pomegranate"]

FINAL_CLASSES = sorted({v for m in CLASS_MAP.values() for v in m.values() if v} | set(EXTRA_CLASSES))
