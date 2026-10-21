"""Data models and shared contracts for the Urban Flood Risk Platform.

Contracts defined in Section 4 of the Project Explainer:
1. CV output (P1 to P4)
2. Hazard layers (P2/P3 to P4)
3. Photo metadata (P3 to P1/P4)
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DepthClass(StrEnum):
    """Water depth categories estimated by CV pose keypoints."""

    NONE = "none"
    ANKLE = "ankle"
    KNEE = "knee"
    THIGH = "thigh"
    UNKNOWN = "unknown"


class FusionStatus(StrEnum):
    """Four-way fusion status combining physics predictions and CV observations."""

    CONFIRMED_HOTSPOT = "Confirmed hotspot"
    PREDICTED_NOT_OBSERVED = "Predicted, not observed"
    UNEXPECTED_FLOODING = "Unexpected flooding (model gap)"
    CLEAR = "Clear"


class MapColour(StrEnum):
    """Map display color corresponding to the fusion status."""

    RED = "red"
    ORANGE = "orange"
    PURPLE = "purple"
    GREEN = "green"


# ---------------------------------------------------------------------
# Contract 1: CV Output (P1 to P4)
# ---------------------------------------------------------------------
class CVOutput(BaseModel):
    """Computer vision model output payload."""

    image_id: str = Field(..., description="Unique identifier of the image frame")
    flooded: bool = Field(..., description="True if standing water is detected")
    water_area_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of frame area covered by water",
    )
    depth_class: DepthClass = Field(
        ...,
        description="Coarse depth classification (none, ankle, knee, thigh, unknown)",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence score between 0 and 1"
    )
    annotated_image: str = Field(
        ..., description="Relative path or URI to the annotated image with mask overlay"
    )


# ---------------------------------------------------------------------
# Contract 2: Hazard Layer Feature (P2 & P3 to P4)
# ---------------------------------------------------------------------
class HazardProperties(BaseModel):
    """Feature properties inside hazard GeoJSON files."""

    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Predicted risk score from 0.0 to 1.0"
    )
    zone_id: str | None = None
    name: str | None = None
    rainfall_scenario: str | None = None
    assumed_drain_status: str | None = None


class HazardFeature(BaseModel):
    """A single GeoJSON feature in the hazard layer."""

    type: str = "Feature"
    properties: HazardProperties
    geometry: dict[str, Any]


class HazardLayer(BaseModel):
    """GeoJSON FeatureCollection representing a flood hazard scenario."""

    type: str = "FeatureCollection"
    name: str | None = None
    features: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Contract 3: Photo Metadata (P3 to P1 & P4)
# ---------------------------------------------------------------------
class PhotoMetadata(BaseModel):
    """Photo metadata record matching data/photos_meta.csv."""

    id: str = Field(..., description="Unique photo identifier")
    filename: str = Field(..., description="Path to photo relative to data/")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in EPSG:4326")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in EPSG:4326")
    timestamp: str = Field(..., description="ISO 8601 or EXIF capture timestamp")
    camera_id: str = Field(..., description="Camera or sensor station identifier")


# ---------------------------------------------------------------------
# Observation Submission and Response Models (P4 API)
# ---------------------------------------------------------------------
class ObservationCreate(BaseModel):
    """Payload to submit a live camera observation."""

    lat: float = Field(..., description="Camera latitude")
    lon: float = Field(..., description="Camera longitude")
    image_id: str | None = Field(default=None, description="Optional image identifier")
    camera_id: str = Field(
        default="cam_live", description="Camera or sensor station identifier"
    )
    timestamp: str | None = Field(default=None, description="Timestamp of observation")
    rainfall_scenario: str = Field(
        default="100mmhr", description="Scenario used for evaluation"
    )


class ObservationResponse(BaseModel):
    """Full fused observation returned to frontend and clients."""

    id: int = Field(..., description="Internal sequential ID")
    image_id: str
    camera_id: str
    lat: float
    lon: float
    timestamp: str
    scenario: str
    predicted_risk: float
    cv_output: CVOutput
    fusion_status: FusionStatus
    map_colour: MapColour
