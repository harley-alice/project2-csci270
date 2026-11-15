# project2-csci270
This is for project 2

## Run the full app

The app is the YOLOv8n detector, the FastAPI backend (`backend/`) and the React frontend (`frontend/`).
The backend applies the food-safety rules in `ml/food_safety/`.

1. **Model weights.** Unzip `model_export.zip` at the repo root so `ml/export/food_detector_v8n_baseline.pt` exists.
   Weights are not stored in git. Without them the backend still starts, but `GET /api/health` reports
   `"yolo_model": "not_loaded"` and `POST /api/detect` returns HTTP 503.
2. **Python environment.** Create a venv and install the requirements:
   ```
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Backend.** From the repo root:
   ```
   uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
   Check `http://127.0.0.1:8000/api/health` and the API docs at `http://127.0.0.1:8000/docs`.
   `POST /api/detect` is the detection endpoint (`POST /detect` is an alias).
4. **Frontend.** In a second terminal:
   ```
   cd frontend && npm install && npm run dev
   ```
   Open http://localhost:3000. The Vite dev server proxies `/api` and `/detect` to the backend on port 8000.
5. **Food-safety data (optional).** Ashton's FoodKeeper workflow reads `data/raw/foodkeeper.json`, which is
   gitignored. Without it every detected item is marked "Confirm this item" and has no shelf-life days.
6. **Tests.** From the repo root: `python -m pytest tests/test_backend.py tests/test_safety_adapter.py tests/test_detect_wiring.py`.
   The food-safety tests (`tests/test_food_safety_*.py`, `ml/food_safety/test_*.py`, `test_foodkeeper_*.py`)
   also need `data/raw/foodkeeper.json`. Frontend build check: `cd frontend && npm run build`.

`local_test_server.py` is Alice's standalone mock detection server (ONNX, no database). The FastAPI backend above
is the primary path.
