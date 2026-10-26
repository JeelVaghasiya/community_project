"""Extract photo metadata into the project's shared CSV contract."""

import csv
from pathlib import Path

import exifread

ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = ROOT / "data" / "photos"
OUTPUT_FILE = ROOT / "data" / "photos_meta.csv"

COLUMNS = ["id", "filename", "lat", "lon", "timestamp", "camera_id"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff"}


def to_decimal(degrees, minutes, seconds, hemisphere):
    """Convert EXIF GPS coordinates to signed decimal degrees."""
    value = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if hemisphere in ("S", "W"):
        value = -value
    return value


def get_gps(tags):
    """Return (latitude, longitude), or (None, None) if unavailable."""
    try:
        lat = tags["GPS GPSLatitude"].values
        lat_ref = str(tags["GPS GPSLatitudeRef"])
        lon = tags["GPS GPSLongitude"].values
        lon_ref = str(tags["GPS GPSLongitudeRef"])

        latitude = to_decimal(lat[0], lat[1], lat[2], lat_ref)
        longitude = to_decimal(lon[0], lon[1], lon[2], lon_ref)
        return latitude, longitude
    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError):
        return None, None


def main():
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    photos = sorted(
        path
        for path in PHOTO_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    for index, photo in enumerate(photos, start=1):
        try:
            with photo.open("rb") as file:
                tags = exifread.process_file(file, details=False)

            latitude, longitude = get_gps(tags)
            timestamp = str(tags.get("EXIF DateTimeOriginal", "")) or str(
                tags.get("Image DateTime", "")
            )

            records.append(
                {
                    "id": f"photo_{index:04d}",
                    "filename": str(photo.relative_to(PHOTO_DIR)),
                    "lat": "" if latitude is None else latitude,
                    "lon": "" if longitude is None else longitude,
                    "timestamp": timestamp,
                    "camera_id": str(tags.get("Image Model", "")),
                }
            )

        except (OSError, ValueError) as error:
            print(f"Skipping {photo.name}: {error}")

    # Write the agreed schema even when no photos are available.
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    print(f"Photos found: {len(photos)}")
    print(f"Metadata records written: {len(records)}")
    print(f"CSV saved to: {OUTPUT_FILE}")

    if not photos:
        print("No photos yet. Add test photos to data/photos and rerun.")


if __name__ == "__main__":
    main()
