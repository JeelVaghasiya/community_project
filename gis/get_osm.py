
"""Download OpenStreetMap data for the Silk Board flood-risk pilot."""

from pathlib import Path

import geopandas as gpd
import osmnx as ox

# Project root and pilot-area bounds
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "osm"

NORTH = 12.922
SOUTH = 12.912
EAST = 77.628
WEST = 77.618

ox.settings.timeout = 180
ox.settings.use_cache = True


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # OSMnx expects (west, south, east, north) for a bounding box.
    bbox = (WEST, SOUTH, EAST, NORTH)

    print("Downloading road network...")
    graph = ox.graph_from_bbox(
        bbox, network_type="drive", simplify=True
    )
    roads = ox.graph_to_gdfs(graph, nodes=False, edges=True)
    roads.to_file(OUTPUT_DIR / "roads.geojson", driver="GeoJSON")
    print(f"Saved {len(roads)} road segments.")

    print("Downloading building footprints...")
    buildings = ox.features_from_bbox(
        bbox, tags={"building": True}
    )
    buildings = buildings[
        buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ]
    buildings.to_file(
        OUTPUT_DIR / "buildings.geojson", driver="GeoJSON"
    )
    print(f"Saved {len(buildings)} buildings.")

  
    print("Downloading hospitals and critical facilities...")

    try:
        facilities = ox.features_from_bbox(
            bbox,
            tags={
                "amenity": [
                    "hospital",
                    "clinic",
                    "doctors",
                    "police",
                    "fire_station",
                ]
            },
        )

        facilities.to_file(
            OUTPUT_DIR / "critical_facilities.geojson",
            driver="GeoJSON",
        )
        print(f"Saved {len(facilities)} facilities.")

    except Exception as error:
        print(f"Facilities download failed: {error}")
        print("Roads and buildings were already saved.")
        print("Retry the facilities download later.")

    print(f"\nOSM extraction finished. Files saved in: {OUTPUT_DIR}")



if __name__ == "__main__":
    main()
