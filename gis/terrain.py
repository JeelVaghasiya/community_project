"""Terrain processing for the Urban Flood Risk Platform.

The default run uses synthetic data for testing only.
Do not use synthetic outputs as real Silk Board flood-risk results.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from whitebox.whitebox_tools import WhiteboxTools

ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = ROOT / "outputs" / "terrain_test"
TEST_DIR.mkdir(parents=True, exist_ok=True)

DEM = TEST_DIR / "synthetic_dem.tif"
FILLED = TEST_DIR / "filled_dem.tif"
SLOPE = TEST_DIR / "slope.tif"
POINTER = TEST_DIR / "d8_pointer.tif"
ACCUM = TEST_DIR / "flow_accumulation.tif"
DEPRESSION = TEST_DIR / "depression_depth.tif"
SCA = TEST_DIR / "specific_catchment_area.tif"
TWI = TEST_DIR / "twi.tif"
POUR_POINTS = TEST_DIR / "pour_points.tif"
CATCHMENT = TEST_DIR / "test_catchment.tif"


def create_synthetic_dem():
    """Create a projected synthetic elevation raster for software testing."""
    rows, cols = 100, 100
    y, x = np.mgrid[0:rows, 0:cols]

    elevation = 100.0 + (rows - y) * 0.2 + x * 0.1
    distance = np.sqrt((x - 50) ** 2 + (y - 50) ** 2)
    elevation -= 3.0 * np.exp(-(distance**2) / (2 * 8.0**2))

    transform = from_origin(500000, 1500000, 10, 10)

    with rasterio.open(
        DEM,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float32",
        crs="EPSG:32643",
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(elevation.astype("float32"), 1)

    print(f"Synthetic DEM created: {DEM}")


def run_terrain_tools(dem_path=DEM):
    """Run terrain tools on an input DEM."""
    wbt = WhiteboxTools()
    wbt.set_working_dir(str(TEST_DIR))
    wbt.verbose = True

    dem_path = Path(dem_path)
    if not dem_path.exists():
        raise FileNotFoundError(f"DEM not found: {dem_path}")

    print("Filling depressions...")
    if wbt.fill_depressions(str(dem_path), str(FILLED)) != 0:
        raise RuntimeError("Depression filling failed")

    print("Calculating slope...")
    if wbt.slope(str(FILLED), str(SLOPE)) != 0:
        raise RuntimeError("Slope calculation failed")

    print("Calculating D8 flow direction...")
    if wbt.d8_pointer(str(FILLED), str(POINTER)) != 0:
        raise RuntimeError("D8 flow direction failed")

    print("Calculating D8 flow accumulation...")
    if wbt.d8_flow_accumulation(str(FILLED), str(ACCUM), out_type="cells") != 0:
        raise RuntimeError("Flow accumulation failed")

    print("Calculating depression depth on original DEM...")
    if wbt.depth_in_sink(str(dem_path), str(DEPRESSION)) != 0:
        raise RuntimeError("Depression-depth calculation failed")

    print("Calculating specific catchment area...")
    if wbt.d8_flow_accumulation(str(FILLED), str(SCA), out_type="sca") != 0:
        raise RuntimeError("Specific catchment area calculation failed")

    print("Calculating Topographic Wetness Index...")
    if wbt.wetness_index(str(SCA), str(SLOPE), str(TWI)) != 0:
        raise RuntimeError("TWI calculation failed")

    # One synthetic pour point for testing the watershed workflow.
    with rasterio.open(POINTER) as src:
        profile = src.profile.copy()
        height, width = src.height, src.width
        point_data = np.zeros((height, width), dtype=np.uint8)
        point_data[height // 2, width // 2] = 1
        profile.update(dtype="uint8", count=1, nodata=0)

    with rasterio.open(POUR_POINTS, "w", **profile) as dst:
        dst.write(point_data, 1)

    print("Delineating test catchment...")
    if wbt.watershed(str(POINTER), str(POUR_POINTS), str(CATCHMENT)) != 0:
        raise RuntimeError("Watershed delineation failed")

    print(f"Terrain test completed. Outputs: {TEST_DIR}")


if __name__ == "__main__":
    create_synthetic_dem()
    run_terrain_tools()
