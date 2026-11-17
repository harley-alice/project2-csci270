"""
USDA FoodKeeper and Food Safety Hierarchy Seed Data.

Populates categories and deterministic storage rules covering all model classes
with dynamic shelf life durations partitioned by package state (sealed vs. opened)
and storage conditions (refrigerator vs. pantry vs. freezer).
"""

from __future__ import annotations

import sqlite3

CATEGORIES = [
    {
        "name": "Meat & Poultry",
        "tier": "tier_1",
        "priority": 1,
        "description": "High acute safety priority: Raw and cooked poultry, beef, and ground meats susceptible to Salmonella, E. coli, and Listeria."
    },
    {
        "name": "Seafood",
        "tier": "tier_1",
        "priority": 1,
        "description": "High acute safety priority: Highly perishable raw or cooked seafood requiring rapid use or freezing."
    },
    {
        "name": "Dairy & Refrigerated Perishables",
        "tier": "tier_2",
        "priority": 2,
        "description": "Refrigeration-sensitive items: Quality and pathogen risk change significantly upon opening and temperature abuse."
    },
    {
        "name": "Produce & Fresh Fruits/Vegetables",
        "tier": "tier_3",
        "priority": 3,
        "description": "Lower acute bacterial pathogen risk under refrigeration; susceptible to mold, moisture breakdown, and quality loss."
    },
    {
        "name": "Bakery & Shelf-Stable Goods",
        "tier": "tier_3",
        "priority": 3,
        "description": "Dry goods, shelf-stable bakery items, and pantry staples."
    },
    {
        "name": "Unidentified Containers",
        "tier": "special",
        "priority": 1,
        "description": "Ambiguous vessels (e.g. jars) requiring user clarification before determining shelf life."
    }
]

# Mapping each food class to its primary category name and USDA parameters
# Each entry defines:
#   sealed_fridge: (min, max, rec)
#   opened_fridge: (min, max, rec)
#   freezer_days: rec
#   pantry_days: rec (or None if requires fridge)
#   requires_user_detail: bool
#   detail_prompt: str
#   usda_guidance: str
RULES_CATALOG = [
    # Tier 1: High safety priority meats & seafood
    {
        "food_class": "ground_beef",
        "category": "Meat & Poultry",
        "requires_user_detail": True,
        "detail_prompt": "Is this raw or cooked ground beef?",
        "guidance": "USDA: Store at 40°F or below. Use or freeze raw ground beef within 1 to 2 days after purchase. Cooked ground beef lasts 3 to 4 days refrigerated.",
        "sealed": (1, 2, 2),
        "opened": (1, 2, 1),
        "cooked_sealed": (3, 4, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 120,
        "pantry": None
    },
    {
        "food_class": "beef",
        "category": "Meat & Poultry",
        "requires_user_detail": True,
        "detail_prompt": "Is this whole-muscle beef (steaks/roasts) or ground beef?",
        "guidance": "USDA: Raw steaks and roasts keep 3 to 5 days refrigerated; ground beef keeps 1 to 2 days. Cooked beef keeps 3 to 4 days.",
        "sealed": (3, 5, 4),
        "opened": (1, 2, 2),
        "cooked_sealed": (3, 4, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": None
    },
    {
        "food_class": "chicken",
        "category": "Meat & Poultry",
        "requires_user_detail": True,
        "detail_prompt": "Is this raw chicken or cooked chicken?",
        "guidance": "USDA: Raw poultry should be used or frozen within 1 to 2 days. Cooked chicken can be safely stored in refrigerator 3 to 4 days.",
        "sealed": (1, 2, 2),
        "opened": (1, 2, 1),
        "cooked_sealed": (3, 4, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 270,
        "pantry": None
    },
    {
        "food_class": "shrimp",
        "category": "Seafood",
        "requires_user_detail": True,
        "detail_prompt": "Is this raw, cooked, or thawed shrimp?",
        "guidance": "USDA: Raw seafood should be refrigerated at 40°F and used within 1 to 2 days. Cooked seafood keeps 3 to 4 days in the refrigerator.",
        "sealed": (1, 2, 2),
        "opened": (1, 2, 1),
        "cooked_sealed": (3, 4, 3),
        "cooked_opened": (3, 4, 3),
        "freezer": 180,
        "pantry": None
    },

    # Tier 2: Refrigeration-sensitive dairy and cured meats
    {
        "food_class": "milk",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this milk opened or sealed?",
        "guidance": "USDA FoodKeeper: Unopened commercial milk typically keeps 7 days refrigerated past purchase or sell-by date. Once opened, consume within 5 to 7 days.",
        "sealed": (7, 10, 7),
        "opened": (4, 7, 5),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 4),
        "freezer": 90,
        "pantry": None
    },
    {
        "food_class": "yogurt",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this yogurt opened or sealed?",
        "guidance": "USDA FoodKeeper: Unopened yogurt keeps 1 to 2 weeks refrigerated. Once opened, consume within 7 days.",
        "sealed": (10, 14, 14),
        "opened": (5, 7, 7),
        "cooked_sealed": (7, 10, 7),
        "cooked_opened": (5, 7, 5),
        "freezer": 60,
        "pantry": None
    },
    {
        "food_class": "cheese",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this hard cheese (cheddar/parmesan) or soft cheese?",
        "guidance": "USDA FoodKeeper: Hard cheese keeps up to 6 months unopened; 3 to 4 weeks after opening. Soft cheeses keep 1 to 2 weeks unopened; 1 week opened.",
        "sealed": (21, 60, 30),
        "opened": (7, 21, 14),
        "cooked_sealed": (7, 14, 10),
        "cooked_opened": (5, 7, 5),
        "freezer": 180,
        "pantry": None
    },
    {
        "food_class": "goat_cheese",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this fresh goat cheese (chevre) opened or sealed?",
        "guidance": "USDA FoodKeeper: Fresh soft goat cheese keeps 2 to 3 weeks sealed refrigerated; 7 to 10 days once opened.",
        "sealed": (14, 21, 14),
        "opened": (5, 7, 7),
        "cooked_sealed": (7, 10, 7),
        "cooked_opened": (5, 7, 5),
        "freezer": 90,
        "pantry": None
    },
    {
        "food_class": "butter",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Refrigerated butter keeps 1 to 2 months unopened, or 1 month after opening. Freezes safely for up to 9 months.",
        "sealed": (30, 60, 60),
        "opened": (21, 30, 30),
        "cooked_sealed": (14, 21, 14),
        "cooked_opened": (7, 14, 10),
        "freezer": 270,
        "pantry": 2
    },
    {
        "food_class": "cream",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this heavy cream, light cream, or half-and-half?",
        "guidance": "USDA FoodKeeper: Heavy cream keeps 10 to 14 days sealed refrigerated; once opened, use within 7 to 10 days.",
        "sealed": (10, 14, 10),
        "opened": (5, 7, 7),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 3),
        "freezer": 60,
        "pantry": None
    },
    {
        "food_class": "bacon",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this bacon sealed or opened?",
        "guidance": "USDA FoodKeeper: Vacuum-sealed unopened bacon keeps 2 weeks in refrigerator; once opened, use within 7 days.",
        "sealed": (14, 14, 14),
        "opened": (5, 7, 7),
        "cooked_sealed": (4, 5, 5),
        "cooked_opened": (4, 5, 4),
        "freezer": 30,
        "pantry": None
    },
    {
        "food_class": "ham",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Is this sliced deli ham or whole cured ham?",
        "guidance": "USDA FoodKeeper: Sliced deli ham keeps 3 to 5 days opened in the refrigerator; unopened pre-packaged deli meat keeps 2 weeks.",
        "sealed": (10, 14, 14),
        "opened": (3, 5, 4),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 5, 3),
        "freezer": 60,
        "pantry": None
    },
    {
        "food_class": "egg",
        "category": "Dairy & Refrigerated Perishables",
        "requires_user_detail": True,
        "detail_prompt": "Are these fresh shell eggs or hard-boiled eggs?",
        "guidance": "USDA FoodKeeper: Fresh raw shell eggs keep 3 to 5 weeks in the refrigerator. Hard-boiled eggs keep 7 days.",
        "sealed": (21, 35, 28),
        "opened": (21, 35, 28),
        "cooked_sealed": (7, 7, 7),
        "cooked_opened": (7, 7, 7),
        "freezer": 0,
        "pantry": None
    },

    # Tier 3: Produce and Lower Risk Foods
    {
        "food_class": "apple",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Apples keep 3 to 4 weeks in the refrigerator crisper, or 1 to 2 weeks at room temperature.",
        "sealed": (21, 30, 21),
        "opened": (3, 5, 4),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 3),
        "freezer": 240,
        "pantry": 10
    },
    {
        "food_class": "avocado",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Whole ripe avocados keep 3 to 4 days refrigerated; cut avocados keep 1 to 2 days covered with citrus juice.",
        "sealed": (3, 5, 4),
        "opened": (1, 2, 2),
        "cooked_sealed": (2, 3, 2),
        "cooked_opened": (1, 2, 1),
        "freezer": 90,
        "pantry": 4
    },
    {
        "food_class": "banana",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Bananas keep 2 to 7 days on the counter; refrigerating darkens peel but extends fruit firmness 3 to 5 days.",
        "sealed": (4, 7, 5),
        "opened": (1, 2, 1),
        "cooked_sealed": (2, 3, 2),
        "cooked_opened": (1, 2, 1),
        "freezer": 90,
        "pantry": 5
    },
    {
        "food_class": "bell_pepper",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Is the bell pepper whole or sliced?",
        "guidance": "USDA FoodKeeper: Whole bell peppers keep 1 to 2 weeks in refrigerator; cut peppers keep 2 to 3 days.",
        "sealed": (7, 14, 10),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": 3
    },
    {
        "food_class": "blueberries",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Fresh blueberries keep 1 to 2 weeks refrigerated; wash just before eating.",
        "sealed": (7, 14, 10),
        "opened": (5, 7, 5),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 3),
        "freezer": 300,
        "pantry": 2
    },
    {
        "food_class": "carrot",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Are the carrots whole or cut?",
        "guidance": "USDA FoodKeeper: Whole carrots keep 2 to 3 weeks in the refrigerator; cut carrots keep 2 to 3 weeks submerged in clean water.",
        "sealed": (14, 28, 21),
        "opened": (7, 14, 10),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 5, 3),
        "freezer": 300,
        "pantry": 5
    },
    {
        "food_class": "corn",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Is the corn fresh in husk, shucked, or cooked?",
        "guidance": "USDA FoodKeeper: Fresh sweet corn in husk keeps 1 to 2 days refrigerated; cooked corn keeps 3 to 4 days.",
        "sealed": (1, 3, 2),
        "opened": (1, 2, 2),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": 1
    },
    {
        "food_class": "green_beans",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Fresh green beans keep 3 to 5 days refrigerated in a crisper drawer.",
        "sealed": (4, 7, 5),
        "opened": (3, 5, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": 1
    },
    {
        "food_class": "lemon",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Whole lemons keep 2 to 3 weeks refrigerated, or 1 week at room temperature. Halved lemons keep 3 to 5 days wrapped.",
        "sealed": (14, 21, 21),
        "opened": (3, 5, 4),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 3),
        "freezer": 120,
        "pantry": 7
    },
    {
        "food_class": "lime",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Whole limes keep 2 to 3 weeks refrigerated, or 1 week at room temperature.",
        "sealed": (14, 21, 21),
        "opened": (3, 5, 4),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 3),
        "freezer": 120,
        "pantry": 7
    },
    {
        "food_class": "mango",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Ripe mangos keep 5 to 7 days refrigerated; sliced mangos keep 3 to 4 days.",
        "sealed": (5, 8, 7),
        "opened": (3, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": 4
    },
    {
        "food_class": "mushrooms",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Fresh whole mushrooms keep 4 to 7 days refrigerated in original paper or breathable packaging.",
        "sealed": (4, 7, 5),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": None
    },
    {
        "food_class": "onion",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Is the onion whole or chopped?",
        "guidance": "USDA FoodKeeper: Whole onions keep 1 to 2 months in cool dry pantry; chopped raw onions keep 7 to 10 days refrigerated sealed.",
        "sealed": (30, 60, 45),
        "opened": (7, 10, 7),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 5, 3),
        "freezer": 240,
        "pantry": 30
    },
    {
        "food_class": "orange",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Fresh oranges keep 2 to 3 weeks refrigerated, or 1 to 2 weeks at room temperature.",
        "sealed": (14, 21, 21),
        "opened": (3, 5, 4),
        "cooked_sealed": (4, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 120,
        "pantry": 10
    },
    {
        "food_class": "persimmon",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Ripe persimmons keep 5 to 7 days refrigerated.",
        "sealed": (5, 8, 7),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 180,
        "pantry": 4
    },
    {
        "food_class": "pomegranate",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Whole pomegranates keep 1 to 2 months refrigerated; extracted arils keep 5 to 7 days.",
        "sealed": (30, 60, 45),
        "opened": (5, 7, 5),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 3),
        "freezer": 240,
        "pantry": 14
    },
    {
        "food_class": "potato",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Are the potatoes whole raw or cooked?",
        "guidance": "USDA: Store raw whole potatoes in a cool, dark, well-ventilated pantry (1 to 2 months). Do not refrigerate raw potatoes. Cooked potatoes keep 3 to 5 days refrigerated.",
        "sealed": (30, 60, 45),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 300,
        "pantry": 45
    },
    {
        "food_class": "sweet_potato",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA: Store whole sweet potatoes in a cool dry pantry 2 to 3 weeks. Cooked sweet potatoes keep 3 to 5 days refrigerated.",
        "sealed": (21, 35, 28),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 300,
        "pantry": 28
    },
    {
        "food_class": "spinach",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Is the spinach fresh bagged, loose, or cooked?",
        "guidance": "USDA FoodKeeper: Fresh bagged spinach keeps 5 to 7 days sealed refrigerated; once opened, use within 3 to 5 days.",
        "sealed": (5, 7, 7),
        "opened": (3, 5, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 240,
        "pantry": None
    },
    {
        "food_class": "strawberries",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Fresh strawberries keep 3 to 7 days refrigerated in original ventilated container.",
        "sealed": (4, 7, 5),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 270,
        "pantry": 1
    },
    {
        "food_class": "tomato",
        "category": "Produce & Fresh Fruits/Vegetables",
        "requires_user_detail": True,
        "detail_prompt": "Are the tomatoes whole or sliced?",
        "guidance": "USDA FoodKeeper: Whole ripe tomatoes keep 5 to 7 days in the pantry or 1 to 2 weeks refrigerated; sliced tomatoes keep 2 to 3 days refrigerated.",
        "sealed": (7, 14, 10),
        "opened": (2, 4, 3),
        "cooked_sealed": (3, 5, 4),
        "cooked_opened": (3, 4, 3),
        "freezer": 180,
        "pantry": 7
    },

    # Tier 3: Bakery & Pantry Staples
    {
        "food_class": "bread",
        "category": "Bakery & Shelf-Stable Goods",
        "requires_user_detail": True,
        "detail_prompt": "Is this commercial bread or bakery/homemade bread?",
        "guidance": "USDA FoodKeeper: Commercial sliced bread keeps 14 to 21 days refrigerated, or 5 to 7 days in pantry. Freezes up to 3 months.",
        "sealed": (14, 21, 14),
        "opened": (7, 14, 10),
        "cooked_sealed": (7, 14, 10),
        "cooked_opened": (5, 10, 7),
        "freezer": 90,
        "pantry": 7
    },
    {
        "food_class": "chocolate",
        "category": "Bakery & Shelf-Stable Goods",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Chocolate keeps 12 months at room temperature away from heat. Can be refrigerated or frozen if hot.",
        "sealed": (180, 365, 365),
        "opened": (90, 180, 120),
        "cooked_sealed": (30, 60, 45),
        "cooked_opened": (14, 30, 21),
        "freezer": 540,
        "pantry": 365
    },
    {
        "food_class": "flour",
        "category": "Bakery & Shelf-Stable Goods",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: White flour keeps 6 to 12 months in a cool, dry pantry or up to 2 years refrigerated/frozen.",
        "sealed": (180, 365, 365),
        "opened": (90, 180, 180),
        "cooked_sealed": (7, 14, 10),
        "cooked_opened": (5, 7, 5),
        "freezer": 720,
        "pantry": 365
    },
    {
        "food_class": "sugar",
        "category": "Bakery & Shelf-Stable Goods",
        "requires_user_detail": False,
        "detail_prompt": None,
        "guidance": "USDA FoodKeeper: Granulated sugar has an indefinite shelf life when kept dry in an airtight container.",
        "sealed": (365, 730, 730),
        "opened": (365, 730, 730),
        "cooked_sealed": (14, 30, 21),
        "cooked_opened": (7, 14, 10),
        "freezer": 730,
        "pantry": 730
    },

    # Special / Unidentified Container
    {
        "food_class": "jar",
        "category": "Unidentified Containers",
        "requires_user_detail": True,
        "detail_prompt": "A jar is a container. Please specify contents (e.g. jam, pickles, pasta sauce, salsa, mayonnaise) to determine shelf life.",
        "guidance": "Unidentified container: Requires user verification of contents before calculating FoodKeeper storage windows.",
        "sealed": (14, 30, 14),
        "opened": (7, 14, 7),
        "cooked_sealed": (5, 7, 5),
        "cooked_opened": (3, 5, 4),
        "freezer": 90,
        "pantry": 30
    }
]


def seed_database(conn: sqlite3.Connection) -> None:
    """Populate categories and storage rules if not already present."""
    with conn:
        # 1. Insert categories
        cat_map = {}
        for cat in CATEGORIES:
            cursor = conn.execute(
                """
                INSERT INTO food_categories (name, tier, priority, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    tier=excluded.tier,
                    priority=excluded.priority,
                    description=excluded.description
                RETURNING id;
                """,
                (cat["name"], cat["tier"], cat["priority"], cat["description"]),
            )
            cat_map[cat["name"]] = cursor.fetchone()[0]

        # 2. Insert storage rules for each item
        for item in RULES_CATALOG:
            cat_id = cat_map[item["category"]]
            food_class = item["food_class"]
            detail = 1 if item["requires_user_detail"] else 0
            prompt = item["detail_prompt"]
            guidance = item["guidance"]

            # Rules for Refrigerator:
            # - Raw Sealed
            s_min, s_max, s_rec = item["sealed"]
            conn.execute(
                """
                INSERT INTO storage_rules (
                    food_class, category_id, package_state, storage_location, is_cooked,
                    shelf_life_days_min, shelf_life_days_max, recommended_shelf_life_days,
                    requires_user_detail, detail_prompt, usda_guidance
                ) VALUES (?, ?, 'sealed', 'refrigerator', 0, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(food_class, package_state, storage_location, is_cooked) DO UPDATE SET
                    shelf_life_days_min=excluded.shelf_life_days_min,
                    shelf_life_days_max=excluded.shelf_life_days_max,
                    recommended_shelf_life_days=excluded.recommended_shelf_life_days,
                    requires_user_detail=excluded.requires_user_detail,
                    detail_prompt=excluded.detail_prompt,
                    usda_guidance=excluded.usda_guidance;
                """,
                (food_class, cat_id, s_min, s_max, s_rec, detail, prompt, guidance)
            )

            # - Raw Opened
            o_min, o_max, o_rec = item["opened"]
            conn.execute(
                """
                INSERT INTO storage_rules (
                    food_class, category_id, package_state, storage_location, is_cooked,
                    shelf_life_days_min, shelf_life_days_max, recommended_shelf_life_days,
                    requires_user_detail, detail_prompt, usda_guidance
                ) VALUES (?, ?, 'opened', 'refrigerator', 0, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(food_class, package_state, storage_location, is_cooked) DO UPDATE SET
                    shelf_life_days_min=excluded.shelf_life_days_min,
                    shelf_life_days_max=excluded.shelf_life_days_max,
                    recommended_shelf_life_days=excluded.recommended_shelf_life_days,
                    requires_user_detail=excluded.requires_user_detail,
                    detail_prompt=excluded.detail_prompt,
                    usda_guidance=excluded.usda_guidance;
                """,
                (food_class, cat_id, o_min, o_max, o_rec, detail, prompt, guidance)
            )

            # - Cooked Sealed
            cs_min, cs_max, cs_rec = item["cooked_sealed"]
            conn.execute(
                """
                INSERT INTO storage_rules (
                    food_class, category_id, package_state, storage_location, is_cooked,
                    shelf_life_days_min, shelf_life_days_max, recommended_shelf_life_days,
                    requires_user_detail, detail_prompt, usda_guidance
                ) VALUES (?, ?, 'sealed', 'refrigerator', 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(food_class, package_state, storage_location, is_cooked) DO UPDATE SET
                    shelf_life_days_min=excluded.shelf_life_days_min,
                    shelf_life_days_max=excluded.shelf_life_days_max,
                    recommended_shelf_life_days=excluded.recommended_shelf_life_days,
                    requires_user_detail=excluded.requires_user_detail,
                    detail_prompt=excluded.detail_prompt,
                    usda_guidance=excluded.usda_guidance;
                """,
                (food_class, cat_id, cs_min, cs_max, cs_rec, detail, prompt, guidance)
            )

            # - Cooked Opened
            co_min, co_max, co_rec = item["cooked_opened"]
            conn.execute(
                """
                INSERT INTO storage_rules (
                    food_class, category_id, package_state, storage_location, is_cooked,
                    shelf_life_days_min, shelf_life_days_max, recommended_shelf_life_days,
                    requires_user_detail, detail_prompt, usda_guidance
                ) VALUES (?, ?, 'opened', 'refrigerator', 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(food_class, package_state, storage_location, is_cooked) DO UPDATE SET
                    shelf_life_days_min=excluded.shelf_life_days_min,
                    shelf_life_days_max=excluded.shelf_life_days_max,
                    recommended_shelf_life_days=excluded.recommended_shelf_life_days,
                    requires_user_detail=excluded.requires_user_detail,
                    detail_prompt=excluded.detail_prompt,
                    usda_guidance=excluded.usda_guidance;
                """,
                (food_class, cat_id, co_min, co_max, co_rec, detail, prompt, guidance)
            )

            # - Freezer Rule (both sealed and opened)
            freezer_days = item.get("freezer", 180)
            if freezer_days:
                for pkg in ('sealed', 'opened'):
                    conn.execute(
                        """
                        INSERT INTO storage_rules (
                            food_class, category_id, package_state, storage_location, is_cooked,
                            shelf_life_days_min, shelf_life_days_max, recommended_shelf_life_days,
                            requires_user_detail, detail_prompt, usda_guidance
                        ) VALUES (?, ?, ?, 'freezer', 0, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(food_class, package_state, storage_location, is_cooked) DO UPDATE SET
                            shelf_life_days_min=excluded.shelf_life_days_min,
                            shelf_life_days_max=excluded.shelf_life_days_max,
                            recommended_shelf_life_days=excluded.recommended_shelf_life_days;
                        """,
                        (food_class, cat_id, pkg, int(freezer_days * 0.75), freezer_days, freezer_days, detail, prompt, guidance)
                    )

            # - Pantry Rule if applicable
            pantry_days = item.get("pantry")
            if pantry_days:
                for pkg in ('sealed', 'opened'):
                    p_min = max(1, int(pantry_days * 0.6))
                    conn.execute(
                        """
                        INSERT INTO storage_rules (
                            food_class, category_id, package_state, storage_location, is_cooked,
                            shelf_life_days_min, shelf_life_days_max, recommended_shelf_life_days,
                            requires_user_detail, detail_prompt, usda_guidance
                        ) VALUES (?, ?, ?, 'pantry', 0, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(food_class, package_state, storage_location, is_cooked) DO UPDATE SET
                            shelf_life_days_min=excluded.shelf_life_days_min,
                            shelf_life_days_max=excluded.shelf_life_days_max,
                            recommended_shelf_life_days=excluded.recommended_shelf_life_days;
                        """,
                        (food_class, cat_id, pkg, p_min, pantry_days, pantry_days, detail, prompt, guidance)
                    )

