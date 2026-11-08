Model export (food_detector_v8n_baseline) - sharing instructions

The weight files are gitignored (*.pt, *.onnx, *.torchscript) and are NOT in git:
  ml/export/food_detector_v8n_baseline.pt
  ml/export/food_detector_v8n_baseline.onnx
  ml/export/food_detector_v8n_baseline.torchscript
Read ml/export/MODEL_CARD.md first (classes, input/output, settings, usage).

To share:
  1. From the repo root, zip the whole folder:  zip -r model_export.zip ml/export
     (it holds the .pt, .onnx, .torchscript and MODEL_CARD.md)
  2. Upload model_export.zip to Google Drive / the shared drive and send the link.

To use:
  1. Download and unzip at the repo root so the files land in ml/export/.
  2. Confirm ml/export/food_detector_v8n_baseline.onnx exists.
  3. Do NOT commit these files. Map detections by class NAME, not index.

To regenerate: python ml/export.py && python ml/verify_export.py --write-card
