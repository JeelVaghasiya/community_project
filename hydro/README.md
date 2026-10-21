# P2: Hydrology and SWMM Modeller

**Branch:** `p2/hydro`  
**Folder Ownership:** `hydro/`, `data/risk/`  
**Main Language:** Python  

## Stack
- EPA SWMM 5.2
- `pyswmm` & `swmmio`
- `pandas` & `geopandas`
- `matplotlib`

## Key Deliverables & Shared Contract
- `hydro/toy.inp`: 5-node toy SWMM model
- `hydro/storms.py`: Design-storm generator (50, 100, 150 mm/hr peak intensity)
- `hydro/pilot.inp`: Pilot area SWMM model for Bengaluru
- `hydro/run_scenarios.py`: Multi-scenario simulation including 50% blocked drain analysis
- Outputs: `data/risk/hazard_{50|100|150}mmhr.geojson` with normalized `risk_score` (0.0 to 1.0) in EPSG:4326.
