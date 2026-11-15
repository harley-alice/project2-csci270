"""Local test inference server for Project 2 (Food Expiration Date Predictor).

Loads Carter's baseline ONNX model (ml/export/food_detector_v8n_baseline.onnx) at startup.
"""
import io
import json
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parent
EXPORT_PT_PATH = REPO_ROOT / "ml" / "export" / "food_detector_v8n_baseline.pt"
FALLBACK_PT_PATH = REPO_ROOT / "ml" / "runs" / "baseline_v8n" / "weights" / "best.pt"
EXPORT_ONNX_PATH = REPO_ROOT / "ml" / "export" / "food_detector_v8n_baseline.onnx"
# Default to .pt for dynamic aspect-ratio handling on mobile/camera photos
MODEL_PATH = Path(os.environ.get("MODEL_PATH", str(EXPORT_PT_PATH if EXPORT_PT_PATH.exists() else (EXPORT_ONNX_PATH if EXPORT_ONNX_PATH.exists() else FALLBACK_PT_PATH))))

# Inference parameters: lower CONF to 0.05 so candidates reach frontend sensitivity slider
IMGSZ = 640
CONF = 0.05
IOU = 0.70

# Baseline shelf lives from USDA FoodKeeper (sealed days)
SHELF_LIFE = {
    'milk': 7, 'egg': 21, 'yogurt': 14, 'chicken': 2, 'beef': 4,
    'bacon': 14, 'cheese': 21, 'goat_cheese': 14, 'butter': 30, 'cream': 10,
    'apple': 21, 'banana': 5, 'strawberries': 5, 'blueberries': 7, 'orange': 14,
    'lemon': 21, 'lime': 21, 'tomato': 7, 'bell_pepper': 10, 'carrot': 21,
    'spinach': 5, 'mushrooms': 5, 'bread': 7, 'shrimp': 2, 'jar': 30
}

INVENTORY_DB = [
    {"id": "t1", "label": "yogurt", "packageState": "sealed", "days": 14},
    {"id": "t2", "label": "egg", "packageState": "sealed", "days": 21}
]

FEEDBACK_LOG = []
_model = None

def get_yolo_model():
    global _model
    if _model is not None:
        return _model
    if MODEL_PATH.exists():
        try:
            from ultralytics import YOLO
            print(f"Loading YOLO detector from {MODEL_PATH}...")
            # Load ONNX or PT model
            if MODEL_PATH.suffix.lower() == ".onnx":
                _model = YOLO(str(MODEL_PATH), task="detect")
            else:
                _model = YOLO(str(MODEL_PATH))
            print("YOLO detector loaded successfully!")
            return _model
        except Exception as e:
            print(f"Could not load ultralytics YOLO: {e}")
    else:
        print(f"Warning: Model file not found at {MODEL_PATH}")
    return None


class LocalTestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/inventory":
            self._set_headers(200)
            self.wfile.write(json.dumps(INVENTORY_DB).encode("utf-8"))
        elif parsed.path == "/api/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "healthy",
                "weights_found": WEIGHTS_PATH.exists(),
                "model_loaded": _model is not None
            }).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if parsed.path == "/detect":
            model = get_yolo_model()
            detections = []

            # Extract image from multipart or raw body
            img = None
            try:
                # Robust multipart boundary extraction
                content_type = self.headers.get("Content-Type", "")
                boundary = None
                if "boundary=" in content_type:
                    boundary = content_type.split("boundary=")[1].strip().split(";")[0].encode("ascii")

                if boundary and (b"--" + boundary) in body:
                    # Find end of headers
                    pos = body.find(b"\r\n\r\n")
                    if pos != -1:
                        content = body[pos + 4:]
                        boundary_marker = b"\r\n--" + boundary
                        end_pos = content.rfind(boundary_marker)
                        img_bytes = content[:end_pos] if end_pos != -1 else content.rsplit(b"\r\n--", 1)[0]
                    else:
                        img_bytes = body
                elif b"\r\n\r\n" in body:
                    img_bytes = body.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0]
                else:
                    img_bytes = body

                raw_img = Image.open(io.BytesIO(img_bytes))
                # Automatically fix rotation if mobile/camera photo has EXIF orientation
                img = ImageOps.exif_transpose(raw_img)
                # Convert RGBA/Palette/CMYK to standard RGB for YOLO
                if img.mode != "RGB":
                    img = img.convert("RGB")
            except Exception as e:
                print(f"Image parse error: {e}")

            try:
                if model and img:
                    print(f"Running ONNX YOLOv8 inference (imgsz={IMGSZ}, conf={CONF}, iou={IOU})...")
                    results = model.predict(img, conf=CONF, iou=IOU, imgsz=IMGSZ)
                    r = results[0]
                    W, H = img.size
                    
                    for idx, box in enumerate(r.boxes):
                        cls_id = int(box.cls[0])
                        # Map detection by class NAME, not index (result.names[int(cls)])
                        label = r.names[cls_id] if hasattr(r, "names") and cls_id in r.names else str(cls_id)
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()  # [xmin, ymin, xmax, ymax]
                        
                        # Convert to normalized [ymin, xmin, ymax, xmax] for frontend SVG
                        norm_bbox = [
                            xyxy[1] / H,
                            xyxy[0] / W,
                            xyxy[3] / H,
                            xyxy[2] / W
                        ]
                        
                        detections.append({
                            "id": str(idx + 1),
                            "label": label,
                            "confidence": round(conf, 2),
                            "bbox": norm_bbox,
                            "packageState": "sealed",
                            "days": SHELF_LIFE.get(label, 7)
                        })
                    print(f"YOLO detected {len(detections)} objects!")
                else:
                    print("Could not load image or model is unavailable.")
                    detections = []

                self._set_headers(200)
                self.wfile.write(json.dumps(detections).encode("utf-8"))
            except Exception as e:
                print(f"Inference error: {e}")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": f"Inference failed: {str(e)}"}).encode("utf-8"))

        elif parsed.path == "/api/feedback":
            try:
                data = json.loads(body.decode("utf-8"))
                FEEDBACK_LOG.append(data)
                print(f"[Active Learning Recorded]: {data.get('type')} on {data.get('predicted_label')}")
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "recorded", "total": len(FEEDBACK_LOG)}).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/inventory":
            try:
                data = json.loads(body.decode("utf-8"))
                INVENTORY_DB.extend(data.get("items", []))
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "saved", "count": len(INVENTORY_DB)}).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


def run(port=8000):
    # Preload YOLO model once at server startup as instructed
    get_yolo_model()
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, LocalTestHandler)
    print(f"🚀 Real YOLO Server running on http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()


