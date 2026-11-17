"""
Database connection and schema setup for the Fridge Tracker application.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "fridge_tracker.sqlite"

# Read database path from environment variable if present
DB_PATH = Path(os.environ.get("FRIDGE_DB_PATH", DEFAULT_DB_PATH))


def get_db_connection() -> sqlite3.Connection:
    """Open a SQLite database connection with row access and foreign key checks enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a database connection context that commits changes and closes safely."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """
    Create the database tables if they do not exist:
    - food_categories: Safety tiers and categories.
    - storage_rules: Storage duration rules by food item, package condition, and location.
    - inventory_items: Stored food items and calculated expiration dates.
    - model_feedback: User correction entries and review records.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS food_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                tier TEXT NOT NULL,
                priority INTEGER NOT NULL,
                description TEXT
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS storage_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_class TEXT NOT NULL,
                category_id INTEGER,
                package_state TEXT NOT NULL DEFAULT 'sealed',
                storage_location TEXT NOT NULL DEFAULT 'refrigerator',
                is_cooked INTEGER NOT NULL DEFAULT 0,
                shelf_life_days_min INTEGER NOT NULL,
                shelf_life_days_max INTEGER NOT NULL,
                recommended_shelf_life_days INTEGER NOT NULL,
                requires_user_detail INTEGER NOT NULL DEFAULT 0,
                detail_prompt TEXT,
                usda_guidance TEXT,
                FOREIGN KEY (category_id) REFERENCES food_categories (id) ON DELETE SET NULL,
                UNIQUE (food_class, package_state, storage_location, is_cooked)
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory_items (
                id TEXT PRIMARY KEY,
                food_class TEXT NOT NULL,
                custom_name TEXT,
                category_id INTEGER,
                package_state TEXT NOT NULL DEFAULT 'sealed',
                storage_location TEXT NOT NULL DEFAULT 'refrigerator',
                is_cooked INTEGER NOT NULL DEFAULT 0,
                added_date TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                shelf_life_days INTEGER NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0,
                confidence REAL,
                bbox_ymin REAL,
                bbox_xmin REAL,
                bbox_ymax REAL,
                bbox_xmax REAL,
                safety_tier TEXT,
                user_notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (category_id) REFERENCES food_categories (id) ON DELETE SET NULL
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS model_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                feedback_type TEXT NOT NULL,
                image_source TEXT,
                detection_id TEXT,
                predicted_label TEXT,
                corrected_label TEXT,
                confidence REAL,
                bbox_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """)

            # Fast search index creation
            conn.execute("CREATE INDEX IF NOT EXISTS idx_storage_rules_lookup ON storage_rules (food_class, package_state, storage_location);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_food_class ON inventory_items (food_class);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_expiration ON inventory_items (expiration_date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_verified ON inventory_items (verified);")
    finally:
        if should_close:
            conn.close()

