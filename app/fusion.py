"""Fusion engine combining physics predictions and CV observations.

Implements the Fusion Rule Table (Section 5, P4):
---------------------------------------------------------------------------------
Predicted risk >= 0.6 | CV says flooded | Status                       | Map colour
---------------------------------------------------------------------------------
Yes                   | Yes             | Confirmed hotspot            | Red
Yes                   | No              | Predicted, not observed      | Orange
No                    | Yes             | Unexpected flooding (gap)    | Purple
No                    | No              | Clear                        | Green
---------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape

from app.models import FusionStatus, MapColour

RISK_THRESHOLD = 0.6


def evaluate_fusion(
    predicted_risk: float, cv_flooded: bool
) -> tuple[FusionStatus, MapColour]:
    """Applies the four-way fusion decision matrix.

    Args:
        predicted_risk: Float between 0.0 and 1.0 from the SWMM / terrain hazard model.
        cv_flooded: Boolean indicator from the computer vision model.

    Returns:
        Tuple of (FusionStatus, MapColour).
    """
    is_high_risk = predicted_risk >= RISK_THRESHOLD

    if is_high_risk and cv_flooded:
        return FusionStatus.CONFIRMED_HOTSPOT, MapColour.RED
    elif is_high_risk and not cv_flooded:
        return FusionStatus.PREDICTED_NOT_OBSERVED, MapColour.ORANGE
    elif not is_high_risk and cv_flooded:
        return FusionStatus.UNEXPECTED_FLOODING, MapColour.PURPLE
    else:
        return FusionStatus.CLEAR, MapColour.GREEN


def sample_hazard_risk(
    lat: float,
    lon: float,
    scenario: str = "100mmhr",
    risk_dir: Path | None = None,
) -> float:
    """Samples predicted risk score from the GeoJSON hazard layer at (lat, lon).

    If point falls inside a hazard polygon, returns its risk_score.
    Otherwise finds the nearest hazard feature with inverse distance decay.
    """
    if risk_dir is None:
        risk_dir = Path(__file__).resolve().parent.parent / "data" / "risk"

    geojson_path = risk_dir / f"hazard_{scenario}.geojson"
    if not geojson_path.exists():
        # Fallback to 100mmhr or default moderate risk
        geojson_path = risk_dir / "hazard_100mmhr.geojson"
        if not geojson_path.exists():
            return 0.45

    try:
        with open(geojson_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except Exception:
        return 0.45

    point = Point(lon, lat)  # GeoJSON stores [lon, lat]
    features = data.get("features", [])
    if not features:
        return 0.0

    # 1. Exact geometric containment
    for feat in features:
        geom = feat.get("geometry")
        props = feat.get("properties", {})
        if geom:
            geom_shape = shape(geom)
            if geom_shape.contains(point) or geom_shape.distance(point) < 1e-5:
                return float(props.get("risk_score", 0.5))

    # 2. Nearest feature distance decay
    min_dist = float("inf")
    closest_risk = 0.0
    for feat in features:
        geom = feat.get("geometry")
        props = feat.get("properties", {})
        if geom:
            geom_shape = shape(geom)
            dist = geom_shape.distance(point)
            if dist < min_dist:
                min_dist = dist
                closest_risk = float(props.get("risk_score", 0.0))

    # Decay risk with distance: at ~0.005 deg (~500m), risk drops
    decay_factor = max(0.0, 1.0 - (min_dist / 0.008))
    return round(closest_risk * decay_factor, 2)
