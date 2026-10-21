# P3: GIS and Data Engineer

**Branch:** `p3/gis`  
**Folder Ownership:** `gis/`, `data/`  
**Main Language:** Python  

## Stack
- `rasterio`, `geopandas`, `shapely`, `osmnx`
- `WhiteboxTools`
- `exifread` & `pandas`
- GeoPackage & QGIS

## Key Deliverables & Shared Contract
- `gis/get_dem.py`: Copernicus GLO-30 DEM downloader and clipper
- `gis/get_osm.py`: OpenStreetMap roads, buildings, and critical infrastructure
- `gis/terrain.py`: D8 flow direction, depression depth, Topographic Wetness Index (TWI)
- `gis/ingest_photos.py`: EXIF GPS & timestamp extractor writing to `data/photos_meta.csv`
- `gis/mock_feed.py`: Replays photos every 5 seconds with simulated timestamps sending to P4's API
- Outputs:
  - `data/photos_meta.csv`: `id, filename, lat, lon, timestamp, camera_id`
  - `data/risk/catchments.geojson`
  - `data/risk/terrain_hazard.geojson`
