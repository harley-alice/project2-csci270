from pathlib import Path
from PIL import Image, ImageOps

# Project paths
ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "qa" / "fridge_images"
OUTPUT_DIR = ROOT / "data" / "qa" / "fridge_images_normalized"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

processed = 0
rotated = 0

for image_path in SOURCE_DIR.iterdir():
    if image_path.suffix.lower() not in image_extensions:
        continue

    with Image.open(image_path) as image:
        original_orientation = image.getexif().get(274, 1)

        # Apply EXIF rotation to the actual image pixels.
        upright_image = ImageOps.exif_transpose(image)

        # Remove the old orientation metadata.
        exif = upright_image.getexif()
        exif[274] = 1

        output_path = OUTPUT_DIR / image_path.name

        save_kwargs = {"exif": exif.tobytes()} if image_path.suffix.lower() in {".jpg", ".jpeg"} else {}

        if image_path.suffix.lower() in {".jpg", ".jpeg"}:
            upright_image.save(output_path, quality=95, exif=exif.tobytes())
        else:
            upright_image.save(output_path)

        processed += 1

        if original_orientation != 1:
            rotated += 1

        print(
            f"{image_path.name}: orientation {original_orientation} "
            f"-> 1 | {image.size} -> {upright_image.size}"
        )

print("\nImage normalization complete.")
print(f"Images processed: {processed}")
print(f"Images requiring rotation: {rotated}")
print(f"Output folder: {OUTPUT_DIR}")
