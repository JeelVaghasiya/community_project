"""Observation endpoints for accepting camera feeds, running CV, and saving fused observations."""

from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.fusion import evaluate_fusion, sample_hazard_risk
from app.models import (
    CVOutput,
    DepthClass,
    FusionStatus,
    MapColour,
    ObservationCreate,
    ObservationResponse,
)

router = APIRouter(tags=["Observations"])

# ---------------------------------------------------------------------
# Database Setup: SQLite via SQLAlchemy
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "observations.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ObservationRecord(Base):
    """SQLAlchemy model for persistent observation storage."""

    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(String, index=True)
    camera_id = Column(String, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    scenario = Column(String, default="100mmhr")
    predicted_risk = Column(Float, nullable=False)
    flooded = Column(Boolean, nullable=False)
    water_area_pct = Column(Float, nullable=False)
    depth_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    annotated_image = Column(String, nullable=False)
    fusion_status = Column(String, nullable=False)
    map_colour = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------
# CV Module Integration Hook (Calls P1 cv.analyze if available)
# ---------------------------------------------------------------------
def run_cv_analysis(image_path: str, image_id: str) -> CVOutput:
    """Invokes P1's cv.analyze function if available, falling back to an intelligent contract stub."""
    try:
        # P1's future import: from cv.analyze import analyze
        import importlib

        cv_module = importlib.import_module("cv.analyze")
        if hasattr(cv_module, "analyze"):
            result = cv_module.analyze(image_path)
            return CVOutput(
                image_id=result.get("image_id", image_id),
                flooded=bool(result.get("flooded", False)),
                water_area_pct=float(result.get("water_area_pct", 0.0)),
                depth_class=DepthClass(result.get("depth_class", "unknown")),
                confidence=float(result.get("confidence", 0.85)),
                annotated_image=result.get(
                    "annotated_image", "outputs/placeholder_annot.png"
                ),
            )
    except Exception:
        pass

    # High-fidelity stub adhering strictly to Contract 1 (Section 4)
    # Generate deterministic stub outputs for demo testing
    stub_flooded = ("flood" in image_id.lower()) or (hash(image_id) % 3 != 0)
    depth = DepthClass.KNEE if stub_flooded else DepthClass.NONE
    water_pct = 38.5 if stub_flooded else 0.0
    conf = 0.89 if stub_flooded else 0.94

    return CVOutput(
        image_id=image_id,
        flooded=stub_flooded,
        water_area_pct=water_pct,
        depth_class=depth,
        confidence=conf,
        annotated_image=f"outputs/{image_id}_annot.png",
    )


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------
@router.post(
    "/observations",
    summary="Submit photo observation and compute real-time fusion",
    response_model=ObservationResponse,
)
def create_observation_json(payload: ObservationCreate) -> ObservationResponse:
    """Accepts JSON metadata (used by mock_feed or API clients)."""
    now = datetime.datetime.now(datetime.UTC)
    now_str = payload.timestamp or now.isoformat()
    image_id = payload.image_id or f"img_{now.strftime('%H%M%S%f')[:10]}"

    # 1. Sample predicted risk at photo location
    predicted_risk = sample_hazard_risk(
        lat=payload.lat, lon=payload.lon, scenario=payload.rainfall_scenario
    )

    # 2. Run CV analysis (stub or P1 cv.analyze)
    cv_output = run_cv_analysis(
        image_path=f"data/photos/{image_id}.jpg", image_id=image_id
    )

    # 3. Apply fusion decision matrix
    status, colour = evaluate_fusion(
        predicted_risk=predicted_risk, cv_flooded=cv_output.flooded
    )

    # 4. Save to SQLite database
    db = SessionLocal()
    try:
        record = ObservationRecord(
            image_id=image_id,
            camera_id=payload.camera_id,
            lat=payload.lat,
            lon=payload.lon,
            scenario=payload.rainfall_scenario,
            predicted_risk=predicted_risk,
            flooded=cv_output.flooded,
            water_area_pct=cv_output.water_area_pct,
            depth_class=cv_output.depth_class.value,
            confidence=cv_output.confidence,
            annotated_image=cv_output.annotated_image,
            fusion_status=status.value,
            map_colour=colour.value,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return ObservationResponse(
            id=record.id,
            image_id=record.image_id,
            camera_id=record.camera_id,
            lat=record.lat,
            lon=record.lon,
            timestamp=now_str,
            scenario=record.scenario,
            predicted_risk=record.predicted_risk,
            cv_output=cv_output,
            fusion_status=status,
            map_colour=colour,
        )
    finally:
        db.close()


@router.post(
    "/observations/upload",
    summary="Upload image file with location coordinates",
    response_model=ObservationResponse,
)
async def upload_observation(
    lat: float = Form(...),
    lon: float = Form(...),
    camera_id: str = Form("cam_upload"),
    scenario: str = Form("100mmhr"),
    file: UploadFile = File(...),
) -> ObservationResponse:
    """Accepts multipart photo upload + location from mobile client or web UI."""
    photos_dir = BASE_DIR / "data" / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    image_id = f"upload_{timestamp_str}"
    save_path = photos_dir / f"{image_id}_{file.filename}"

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Sample risk
    predicted_risk = sample_hazard_risk(lat=lat, lon=lon, scenario=scenario)

    # CV Analysis
    cv_output = run_cv_analysis(image_path=str(save_path), image_id=image_id)

    # Fusion
    status, colour = evaluate_fusion(
        predicted_risk=predicted_risk, cv_flooded=cv_output.flooded
    )

    db = SessionLocal()
    try:
        record = ObservationRecord(
            image_id=image_id,
            camera_id=camera_id,
            lat=lat,
            lon=lon,
            scenario=scenario,
            predicted_risk=predicted_risk,
            flooded=cv_output.flooded,
            water_area_pct=cv_output.water_area_pct,
            depth_class=cv_output.depth_class.value,
            confidence=cv_output.confidence,
            annotated_image=cv_output.annotated_image,
            fusion_status=status.value,
            map_colour=colour.value,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return ObservationResponse(
            id=record.id,
            image_id=record.image_id,
            camera_id=record.camera_id,
            lat=record.lat,
            lon=record.lon,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            scenario=record.scenario,
            predicted_risk=record.predicted_risk,
            cv_output=cv_output,
            fusion_status=status,
            map_colour=colour,
        )
    finally:
        db.close()


@router.get(
    "/observations",
    summary="List all recorded observations",
    response_model=list[ObservationResponse],
)
def list_observations() -> list[ObservationResponse]:
    """Retrieves all observation records for live map polling."""
    db = SessionLocal()
    try:
        records = (
            db.query(ObservationRecord).order_by(ObservationRecord.id.desc()).all()
        )
        responses: list[ObservationResponse] = []
        for r in records:
            responses.append(
                ObservationResponse(
                    id=r.id,
                    image_id=r.image_id,
                    camera_id=r.camera_id,
                    lat=r.lat,
                    lon=r.lon,
                    timestamp=r.timestamp.isoformat()
                    if r.timestamp
                    else datetime.datetime.now(datetime.UTC).isoformat(),
                    scenario=r.scenario,
                    predicted_risk=r.predicted_risk,
                    cv_output=CVOutput(
                        image_id=r.image_id,
                        flooded=r.flooded,
                        water_area_pct=r.water_area_pct,
                        depth_class=DepthClass(r.depth_class),
                        confidence=r.confidence,
                        annotated_image=r.annotated_image,
                    ),
                    fusion_status=FusionStatus(r.fusion_status),
                    map_colour=MapColour(r.map_colour),
                )
            )
        return responses
    finally:
        db.close()
