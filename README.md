# Urban Flood Risk Platform (Bengaluru Pilot)

[![Ruff Lint Check](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/frontend-Leaflet.js-199900.svg)](https://leafletjs.com/)

> **Street-level urban flood risk calculation for Bengaluru** combining physics-based hydrological simulation (EPA SWMM + DEM) with real-time computer vision camera ground truth (SegFormer + YOLOv8-pose).

---

## 1. The Idea in Brief

Cities like Bengaluru flood repeatedly during intense monsoon showers, but conventional flood alerts are either too coarse (city-wide rainfall warnings) or too late (reports after an underpass is already submerged).

This platform fuses two independent streams of evidence:
1. **Terrain & Drainage Physics (The Prediction)**: A Digital Elevation Model (DEM) and EPA SWMM drainage simulation calculate which junctions and roadways overflow under design-storm intensities (50, 100, and 150 mm/hr).
2. **Computer Vision (The Observation)**: Existing traffic signals and smartphone cameras are processed by vision models to detect standing water, calculate water surface area percentage, and estimate coarse depth class (ankle, knee, thigh).
3. **Evidence Fusion Engine**:
   - **Confirmed Hotspot (Red)**: Physics predicts flooding AND camera observes water.
   - **Predicted, Not Observed (Orange)**: Physics predicts flooding, but camera observes clear road (warning/monitoring).
   - **Unexpected Flooding (Purple)**: Physics predicted safe, but camera observes flooding (**Model Gap / Blocked Drain**).
   - **Clear (Green)**: Both agree no flooding.

**Pilot Area:** ~1 km² around **Central Silk Board Junction / Hosur Road Underpass**, Bengaluru.

---

## 2. Monorepo Structure & Team Roles

```text
flood-demo/
├── data/
│   ├── photos/              # Raw phone photos (P3)
│   ├── photos_meta.csv      # Photo metadata: id, filename, lat, lon, timestamp, camera_id (P3)
│   ├── dem/                 # DEM tiles (P3) - NOT committed to Git, stored on Drive
│   ├── pilot.gpkg           # Roads, buildings, hospitals (P3)
│   └── risk/                # Hazard GeoJSON outputs for 50, 100, 150 mm/hr (P2 & P3)
├── cv/                      # Computer vision models (P1)
├── hydro/                   # SWMM models and storm simulations (P2)
├── gis/                     # Terrain analysis and mock camera feed (P3)
├── app/                     # Web application and fusion engine (P4)
│   ├── static/              # Leaflet frontend (HTML, CSS, JS)
│   ├── routes/              # FastAPI endpoints (/observations, /risk, /scenarios)
│   ├── models.py            # Pydantic contract definitions
│   ├── fusion.py            # Decision matrix & risk sampler
│   └── main.py              # Application entrypoint
├── docs/                    # Architecture notes, branch protection, evaluation reports
├── tests/                   # Pytest suite validating contracts and API routes
├── pyproject.toml           # Ruff and tooling configuration
├── requirements.txt         # Project dependencies
└── README.md
```

### Team Responsibilities

| Role | Engineer | Focus Area | Branch | Owned Directory |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | Computer Vision | SegFormer-b0 water segmentation, YOLOv8-pose depth heuristic | `p1/cv` | `cv/`, `docs/cv_eval_report.md` |
| **P2** | Hydrology & SWMM | EPA SWMM 5.2, design-storm hyetographs, blocked drain scenarios | `p2/hydro` | `hydro/`, `data/risk/` |
| **P3** | GIS & Data | DEM processing, OSM extraction, photo EXIF, mock camera feed | `p3/gis` | `gis/`, `data/` |
| **P4** | Integration & Lead | Architecture, FastAPI backend, Leaflet UI, real-time fusion engine | `p4/app` | `app/`, repo root files |

---

## 3. Git Workflow & Branch Protection

### Branch Rules
- Work on role branches: `p1/cv`, `p2/hydro`, `p3/gis`, `p4/app`.
- Direct pushes to `main` are disabled. All merges require a Pull Request.
- PRs require:
  1. At least **one peer review** from a teammate.
  2. Passing **Ruff Lint Check** CI workflow (`.github/workflows/lint.yml`).
  3. Passing **Pytest** CI workflow (`.github/workflows/test.yml`).
- Keep PRs small and focused on one task at a time.
- **Commit format**: `area: what changed` (e.g. `cv: add depth heuristic using pose keypoints`).
- **Commit boundaries**: Only commit inside your assigned folder.

For step-by-step instructions on setting up GitHub branch protection rules, see [docs/BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md).

---

## 4. Shared Contracts

Three shared contracts decouple development across team members:

### 1. CV Output (P1 &rarr; P4)
```json
{
  "image_id": "img_007",
  "flooded": true,
  "water_area_pct": 34.2,
  "depth_class": "knee",
  "confidence": 0.81,
  "annotated_image": "outputs/img_007_annot.png"
}
```
*`depth_class` must be one of:* `none`, `ankle`, `knee`, `thigh`, `unknown`.

### 2. Hazard Layers (P2 & P3 &rarr; P4)
Files located at `data/risk/hazard_{50|100|150}mmhr.geojson`. Each contains points or polygons with a `risk_score` property between `0.0` and `1.0` in EPSG:4326.

### 3. Photo Metadata (P3 &rarr; P1 & P4)
`data/photos_meta.csv` with standard header:
```csv
id,filename,lat,lon,timestamp,camera_id
```

---

## 5. Fusion Rule Table

| Predicted Risk (&ge; 0.6) | CV Observed Flooding | Fusion Status | Map Marker Colour | Action |
| :---: | :---: | :--- | :---: | :--- |
| **Yes** | **Yes** | **Confirmed Hotspot** | <span style="color:red">**Red**</span> | Issue high-priority alert to traffic police and commuters |
| **Yes** | **No** | **Predicted, Not Observed** | <span style="color:orange">**Orange**</span> | Active surveillance (drain capacity holding or localized pump) |
| **No** | **Yes** | **Unexpected Flooding** | <span style="color:purple">**Purple**</span> | **Model Gap Alert**: Investigate blocked drains, debris, or culvert failure |
| **No** | **No** | **Clear** | <span style="color:green">**Green**</span> | Normal road condition |

---

## 6. Quickstart Guide

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/JeelVaghasiya/community_project.git
cd community_project

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Ruff Lint & Format Checks
```bash
# Check code style and formatting
ruff check .
ruff format --check .

# Automatically apply safe fixes
ruff check --fix .
ruff format .
```

### 3. Run Automated Tests
```bash
pytest -v
```

### 4. Launch the Platform
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive Map & UI: **http://127.0.0.1:8000**
- Interactive OpenAPI Docs: **http://127.0.0.1:8000/docs**
- Health & Pilot Area: **http://127.0.0.1:8000/health**

### 5. Run Mock Camera Feed
In a separate terminal window:
```bash
python gis/mock_feed.py --loop
```
Watch the camera markers update live on the Leaflet map every 3 seconds!

---

## 7. Large File Policy

Per Section 3 of the project explainer, **never commit large files to git**:
- DEM rasters (`data/dem/*.tif`)
- Deep learning model weights (`*.pt`, `*.pth`, `*.onnx`)
- High-resolution uncompressed photo collections

These assets are hosted on the team's shared Google Drive. Only lightweight GeoJSON vector layers, small output JSONs, and metadata CSV files belong in version control.
