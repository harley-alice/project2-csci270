
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# Project paths
ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "data" / "qa" / "fridge_images"
OUTPUT_DIR = ROOT / "data" / "qa" / "preprocessed"

# Image settings
GAMMA = 0.8
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def adjust_brightness(image):
    """Brighten an image using gamma correction."""
    image_array = np.array(image)

    lookup_table = np.array([
        ((i / 255.0) ** GAMMA) * 255
        for i in range(256)
    ]).clip(0, 255).astype(np.uint8)

    adjusted = cv2.LUT(image_array, lookup_table)
    return Image.fromarray(adjusted)


def apply_clahe(image):
    """Improve local contrast using CLAHE on image brightness."""
    image_array = np.array(image)

    lab = cv2.cvtColor(image_array, cv2.COLOR_RGB2LAB)

    lightness, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT,
        tileGridSize=CLAHE_TILE_GRID
    )

    enhanced_lightness = clahe.apply(lightness)

    enhanced_lab = cv2.merge((enhanced_lightness, a, b))
    enhanced_rgb = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

    return Image.fromarray(enhanced_rgb)


def correct_white_balance(image):
    """Apply gray-world white balance correction."""
    image_array = np.array(image).astype(np.float32)

    channel_means = image_array.mean(axis=(0, 1))
    gray_mean = channel_means.mean()

    # Prevent division by zero
    channel_means = np.maximum(channel_means, 1)

    scale = gray_mean / channel_means

    corrected = image_array * scale
    corrected = np.clip(corrected, 0, 255).astype(np.uint8)

    return Image.fromarray(corrected)


def process_image(image_path, relative_path):
    """Create all four preprocessing versions of an image."""

    with Image.open(image_path) as source:
        original = source.convert("RGB")

    # Generate individual transformations
    brightness = adjust_brightness(original)
    clahe = apply_clahe(original)
    white_balance = correct_white_balance(original)

    # Combined brightness + CLAHE
    combined = apply_clahe(brightness)

    variants = {
        "brightness": brightness,
        "clahe": clahe,
        "white_balance": white_balance,
        "brightness_clahe": combined
    }

    for variant_name, processed_image in variants.items():

        destination = (
            OUTPUT_DIR / variant_name / relative_path
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        processed_image.save(destination)


def main():

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            f"QA image directory not found: {IMAGE_DIR}"
        )

    image_files = [
        path for path in IMAGE_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    print(f"QA images found: {len(image_files)}")

    if not image_files:
        print("No images found. Exiting.")
        return

    successful = 0
    failed = 0

    for image_path in image_files:

        relative_path = image_path.relative_to(IMAGE_DIR)

        try:
            process_image(image_path, relative_path)
            successful += 1

        except Exception as error:
            failed += 1
            print(f"Error processing {image_path.name}: {error}")

    print("\nPREPROCESSING COMPLETE")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {failed}")
    print(f"Versions per image: 4")
    print(f"Output directory: {OUTPUT_DIR}")

    print("\nCreated folders:")
    for variant in [
        "brightness",
        "clahe",
        "white_balance",
        "brightness_clahe"
    ]:
        print(f"  {OUTPUT_DIR / variant}")


if __name__ == "__main__":
    main()
