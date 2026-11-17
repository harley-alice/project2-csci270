"""
Main server file for the Fridge Tracker application.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root path to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_db, init_db
from backend.foodkeeper_data import seed_database
from backend.routes.detect import router as detect_router
from backend.routes.feedback import router as feedback_router
from backend.routes.inventory import router as inventory_router
from backend.routes.rules import router as rules_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fridge_tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop tasks for the server process."""
    logger.info("Checking SQLite database schema and USDA FoodKeeper rules...")
    init_db()
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM storage_rules;")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("Seeding USDA FoodKeeper rules into database...")
            seed_database(conn)
        else:
            logger.info("FoodKeeper database already seeded (%d rules loaded). Skipping re-seed.", count)
    logger.info("Database ready.")
    yield
    logger.info("Shutting down Fridge Tracker server.")


app = FastAPI(
    title="Fridge Tracker API",
    description="Backend service for food storage duration calculation and inventory management.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow local web client connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(detect_router)
app.include_router(inventory_router)
app.include_router(rules_router)
app.include_router(feedback_router)


@app.get("/", tags=["Root"])
def root():
    """Return status and links to main service endpoints."""
    return {
        "message": "Fridge Tracker API is running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "endpoints": {
            "detect": "POST /api/detect",
            "inventory": "GET, POST /api/inventory",
            "verify": "POST /api/inventory/{id}/verify",
            "storage_duration": "PATCH /api/inventory/{id}/duration",
            "rules": "GET /api/rules",
            "categories": "GET /api/categories",
            "calculate": "POST /api/rules/calculate",
            "feedback": "POST /api/feedback",
        },
    }


@app.get("/api", tags=["Root"])
def api_root():
    return root()


@app.get("/api/health", tags=["Health"])
def health_check():
    """Return health condition of the service."""
    return {
        "status": "healthy",
        "service": "fridge_tracker_api",
        "yolo_model": "loaded",
        "database": "sqlite_ready",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

