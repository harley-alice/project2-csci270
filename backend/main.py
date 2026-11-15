"""
Main FastAPI Application Entrypoint for Fridge Tracker.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure the repository root is in sys.path regardless of how main.py is invoked
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_db, init_db
from backend.foodkeeper_data import seed_database
from backend.routes.detect import alias_router as detect_alias_router
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
    """Lifecycle startup and shutdown hooks."""
    logger.info("Initializing SQLite database schema and seeding USDA FoodKeeper rules...")
    init_db()
    with get_db() as conn:
        seed_database(conn)
    logger.info("Database initialization and FoodKeeper seeding complete.")
    yield
    logger.info("Shutting down Fridge Tracker server.")


app = FastAPI(
    title="Fridge Tracker AI & FoodKeeper API",
    description=(
        "Hybrid AI inference server and deterministic FoodKeeper decision engine "
        "for automated fridge inventory tracking and foodborne illness risk mitigation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for local Vite frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(detect_router)
app.include_router(detect_alias_router)
app.include_router(inventory_router)
app.include_router(rules_router)
app.include_router(feedback_router)


@app.get("/", tags=["Root"])
def root():
    """Root entrypoint linking to documentation and core endpoints."""
    return {
        "message": "Fridge Tracker API is running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "endpoints": {
            "detect": "POST /api/detect (alias: POST /detect)",
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
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "fridge_tracker_api",
        "yolo_model": "loaded",
        "database": "sqlite_ready",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

