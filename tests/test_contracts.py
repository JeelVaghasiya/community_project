"""Contract compliance tests for the Urban Flood Risk Platform."""

import csv
import json
from pathlib import Path

from app.fusion import evaluate_fusion
from app.models import (
    CVOutput,
    DepthClass,
    FusionStatus,
    MapColour,
    PhotoMetadata,
)

BASE_DIR = Path(__file__).resolve().parent.parent


def test_contract_1_cv_output_valid():
    """Verifies that Contract 1 (P1 -> P4) schema strictly validates."""
    sample_data = {
        "image_id": "img_007",
        "flooded": True,
        "water_area_pct": 34.2,
        "depth_class": "knee",
        "confidence": 0.81,
        "annotated_image": "outputs/img_007_annot.png",
    }

    cv_out = CVOutput(**sample_data)
    assert cv_out.image_id == "img_007"
    assert cv_out.flooded is True
    assert cv_out.water_area_pct == 34.2
    assert cv_out.depth_class == DepthClass.KNEE
    assert cv_out.confidence == 0.81


def test_contract_2_hazard_layers_exist_and_conform():
    """Verifies that hazard geojson layers exist and contain risk_score between 0 and 1."""
    risk_dir = BASE_DIR / "data" / "risk"
    for scenario in ["50mmhr", "100mmhr", "150mmhr"]:
        file_path = risk_dir / f"hazard_{scenario}.geojson"
        assert file_path.exists(), f"Missing hazard layer for {scenario}"

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("type") == "FeatureCollection"
        features = data.get("features", [])
        assert len(features) > 0, f"Scenario {scenario} must have at least one feature"

        for feat in features:
            props = feat.get("properties", {})
            assert "risk_score" in props, "Each feature must have risk_score"
            risk = props["risk_score"]
            assert 0.0 <= risk <= 1.0, f"risk_score {risk} out of [0, 1] bounds"


def test_contract_3_photos_metadata_conforms():
    """Verifies that photos_meta.csv has the required columns: id, filename, lat, lon, timestamp, camera_id."""
    csv_path = BASE_DIR / "data" / "photos_meta.csv"
    assert csv_path.exists()

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        required_cols = {
            "id",
            "filename",
            "lat",
            "lon",
            "timestamp",
            "camera_id",
        }
        assert required_cols.issubset(set(fieldnames))

        rows = list(reader)
        assert len(rows) > 0
        for row in rows:
            meta = PhotoMetadata(
                id=row["id"],
                filename=row["filename"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                timestamp=row["timestamp"],
                camera_id=row["camera_id"],
            )
            assert -90.0 <= meta.lat <= 90.0
            assert -180.0 <= meta.lon <= 180.0


def test_fusion_rule_table_adherence():
    """Tests the exact 4-way decision matrix from Section 5 of the specification."""
    # 1. Predicted risk >= 0.6 AND CV flooded = True -> Confirmed hotspot (Red)
    status, colour = evaluate_fusion(predicted_risk=0.85, cv_flooded=True)
    assert status == FusionStatus.CONFIRMED_HOTSPOT
    assert colour == MapColour.RED

    # 2. Predicted risk >= 0.6 AND CV flooded = False -> Predicted, not observed (Orange)
    status, colour = evaluate_fusion(predicted_risk=0.72, cv_flooded=False)
    assert status == FusionStatus.PREDICTED_NOT_OBSERVED
    assert colour == MapColour.ORANGE

    # 3. Predicted risk < 0.6 AND CV flooded = True -> Unexpected flooding (Purple)
    status, colour = evaluate_fusion(predicted_risk=0.35, cv_flooded=True)
    assert status == FusionStatus.UNEXPECTED_FLOODING
    assert colour == MapColour.PURPLE

    # 4. Predicted risk < 0.6 AND CV flooded = False -> Clear (Green)
    status, colour = evaluate_fusion(predicted_risk=0.20, cv_flooded=False)
    assert status == FusionStatus.CLEAR
    assert colour == MapColour.GREEN
