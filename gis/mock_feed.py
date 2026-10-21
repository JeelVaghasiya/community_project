"""Mock Camera Feed Generator (P3 hand-off to P4).

Replays photos/cameras from data/photos_meta.csv every 3-5 seconds
with simulated timestamps by sending them to P4's FastAPI endpoint.
"""

from __future__ import annotations

import csv
import datetime
import os
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "photos_meta.csv"
API_URL = os.environ.get("FEED_API_URL", "http://127.0.0.1:8000/observations")


def run_mock_feed(delay_seconds: float = 3.0, loop_continuously: bool = False):
    print("==========================================================")
    print("  Urban Flood Risk Platform - Mock Camera Feed Generator   ")
    print("==========================================================")
    print(f"Target API Endpoint: {API_URL}")
    print(f"Reading records from: {CSV_PATH}")
    print(f"Interval: {delay_seconds} seconds\n")

    if not CSV_PATH.exists():
        print(f"Error: CSV file not found at {CSV_PATH}")
        sys.exit(1)

    while True:
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        if not records:
            print("Notice: No records found in photos_meta.csv")
            return

        for row in records:
            now_iso = datetime.datetime.now(datetime.UTC).isoformat()
            payload = {
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "image_id": row.get("id"),
                "camera_id": row.get("camera_id", "cam_mock"),
                "timestamp": now_iso,
                "rainfall_scenario": "100mmhr",
            }

            try:
                res = requests.post(API_URL, json=payload, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    status = data.get("fusion_status")
                    colour = data.get("map_colour")
                    pred_risk = data.get("predicted_risk")
                    cv_out = data.get("cv_output", {})
                    flooded = cv_out.get("flooded")
                    depth = cv_out.get("depth_class")
                    print(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Camera {payload['camera_id']} pinged: "
                        f"Status='{status}' ({colour.upper()}) | PredictedRisk={pred_risk:.2f} | "
                        f"CVFlooded={flooded} | Depth={depth}"
                    )
                else:
                    print(f"Warning: HTTP {res.status_code} response: {res.text}")
            except requests.exceptions.ConnectionError:
                print(
                    f"Connection refused: Is the API server running on {API_URL}? "
                    "Start it with: uvicorn app.main:app --reload"
                )
            except Exception as e:
                print(f"Error sending frame: {e}")

            time.sleep(delay_seconds)

        if not loop_continuously:
            print(
                "\nFinished replaying all records from photos_meta.csv. Use --loop to run continuously."
            )
            break


if __name__ == "__main__":
    is_loop = "--loop" in sys.argv
    run_mock_feed(delay_seconds=3.0, loop_continuously=is_loop)
