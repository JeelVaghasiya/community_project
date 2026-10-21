"""Hazard layer and rainfall scenario endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Hazard Risk"])

DATA_RISK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "risk"


@router.get("/scenarios", summary="List available rainfall scenarios")
def get_scenarios() -> list[str]:
    """Returns available design storm rainfall scenarios."""
    scenarios: list[str] = []
    if DATA_RISK_DIR.exists():
        for file in sorted(DATA_RISK_DIR.glob("hazard_*.geojson")):
            name = file.stem.replace("hazard_", "")
            scenarios.append(name)
    if not scenarios:
        scenarios = ["50mmhr", "100mmhr", "150mmhr"]
    return scenarios


@router.get(
    "/risk/{scenario}",
    summary="Get hazard layer GeoJSON for a rainfall scenario",
    response_model=dict[str, Any],
)
def get_hazard_layer(scenario: str) -> dict[str, Any]:
    """Returns GeoJSON hazard polygons/points with risk_score field in EPSG:4326."""
    file_path = DATA_RISK_DIR / f"hazard_{scenario}.geojson"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Hazard layer for scenario '{scenario}' not found. Available scenarios: {get_scenarios()}",
        )

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to read hazard layer: {exc}"
        ) from exc
