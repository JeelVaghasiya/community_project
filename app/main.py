"""Main FastAPI application for the Urban Flood Risk Platform.

Serves the interactive Leaflet frontend and REST API endpoints.
"""

from __future__ import annotations

import csv
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.fusion import evaluate_fusion, sample_hazard_risk
from app.routes.observations import (
    ObservationRecord,
    SessionLocal,
    run_cv_analysis,
)
from app.routes.observations import (
    router as observations_router,
)
from app.routes.risk import router as risk_router

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = PROJECT_ROOT / "data"


def seed_initial_observations_if_empty() -> None:
    """Seeds initial observations from data/photos_meta.csv if database is empty."""
    db = SessionLocal()
    try:
        count = db.query(ObservationRecord).count()
        if count > 0:
            return

        csv_path = DATA_DIR / "photos_meta.csv"
        if not csv_path.exists():
            return

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                lat = float(row["lat"])
                lon = float(row["lon"])
                image_id = row["id"]
                camera_id = row["camera_id"]

                # Sample risk & run CV
                pred_risk = sample_hazard_risk(lat=lat, lon=lon, scenario="100mmhr")
                cv_res = run_cv_analysis(
                    image_path=f"data/photos/{image_id}.jpg", image_id=image_id
                )
                status, colour = evaluate_fusion(
                    predicted_risk=pred_risk, cv_flooded=cv_res.flooded
                )

                record = ObservationRecord(
                    image_id=image_id,
                    camera_id=camera_id,
                    lat=lat,
                    lon=lon,
                    scenario="100mmhr",
                    predicted_risk=pred_risk,
                    flooded=cv_res.flooded,
                    water_area_pct=cv_res.water_area_pct,
                    depth_class=cv_res.depth_class.value,
                    confidence=cv_res.confidence,
                    annotated_image=cv_res.annotated_image,
                    fusion_status=status.value,
                    map_colour=colour.value,
                )
                db.add(record)
            db.commit()
    except Exception as exc:
        print(f"Note: Seed observations skipped or encountered notice: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure seed data is available for immediate visual testing
    seed_initial_observations_if_empty()
    yield


app = FastAPI(
    title="Urban Flood Risk Platform",
    description="Street-level flood risk platform combining EPA SWMM/DEM physical predictions with Computer Vision camera observations for Bengaluru.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for external client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(risk_router)
app.include_router(observations_router)

# Mount frontend static directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def get_index():
    """Serves the main Leaflet interactive frontend."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "status": "online",
        "message": "Urban Flood Risk Platform API is running. Visit /docs for OpenAPI specs.",
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health status and pilot area bounding box."""
    return {
        "status": "healthy",
        "pilot_city": "Bengaluru",
        "pilot_area": "Central Silk Board Junction (1 km²)",
        "bounding_box": {
            "min_lat": 12.9120,
            "max_lat": 12.9220,
            "min_lon": 77.6180,
            "max_lon": 77.6280,
        },
        "available_scenarios": ["50mmhr", "100mmhr", "150mmhr"],
        "version": "0.1.0",
    }
