"""
gis/test_depression.py
======================
Controlled synthetic depression test for WhiteboxTools DepthInSink.

Purpose
-------
Verify that WBT DepthInSink correctly measures pit depths on a DEM that
contains two isolated, analytically-defined enclosed depressions of
different depths.  All output is isolated in ``outputs/depression_test/``
so existing ``outputs/terrain_test/`` files and ``data/risk/hazard_*.geojson``
files are never touched.

DEM design
----------
* 60 × 60 cells, EPSG:32643 (UTM 43N), 10 m pixel.
* Uniform south-east slope (0.5 m / row, 0.5 m / col) so every cell has a
  single defined D8 flow-direction and the raster drains unambiguously to
  the SE corner.  This is essential: WBT DepthInSink suppresses pit
  detection when surrounding cells form a flat plateau with no clear outlet.
* Two isolated single-pixel pits punched into the sloped surface:
    Pit 1  row=20, col=15  imposed depth = 5.0 m
    Pit 2  row=40, col=45  imposed depth = 2.0 m
  Each pit is placed so that its elevation = min(8 neighbours) − imposed_depth.
  WBT FillDepressions fills each pit to the level of its lowest neighbour,
  so expected DepthInSink = imposed_depth (exact for float32 arithmetic,
  tolerance ± 0.05 m).

Actual WBT output is read back and printed BEFORE any assertion is made, so
no assumption about exact values is baked in until the raster is inspected.

Usage
-----
    python gis/test_depression.py          # via .venv directly
    .venv/Scripts/python gis/test_depression.py

Protected files (never written by this module)
----------------------------------------------
  gis/terrain.py          — production terrain pipeline, unchanged
  outputs/terrain_test/   — Silk Board synthetic test outputs, unchanged
  data/risk/hazard_*.geojson — hazard scenario GeoJSONs, unchanged
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from whitebox.whitebox_tools import WhiteboxTools

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "depression_test"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEM_PATH = OUT_DIR / "controlled_dem.tif"
DEPTH_PATH = OUT_DIR / "depth_in_sink.tif"

# ── DEM geometry ──────────────────────────────────────────────────────────────
ROWS, COLS = 60, 60
BASE_ELEV = 150.0  # m  — NW-corner (highest point)
SLOPE_R = 0.5  # m per row  (south-ward drop)
SLOPE_C = 0.5  # m per col  (east-ward drop)
# → elevation[r, c] = BASE_ELEV − r*SLOPE_R − c*SLOPE_C

# ── Pit definitions ───────────────────────────────────────────────────────────
#
# On this slope the minimum-elevation neighbour of any interior cell (r, c) is
# always the SE neighbour (r+1, c+1):
#
#   min_neighbour(r, c) = BASE − (r+1)*SLOPE_R − (c+1)*SLOPE_C
#
# A pit whose elevation = min_neighbour − imposed_depth is a true D8 sink
# (strictly below all 8 neighbours), and WBT will fill it exactly to
# min_neighbour, yielding:
#
#   DepthInSink = min_neighbour − pit_elevation = imposed_depth
#
PIT1_ROW, PIT1_COL = 20, 15
PIT1_IMPOSED_DEPTH = 5.0  # m

PIT2_ROW, PIT2_COL = 40, 45
PIT2_IMPOSED_DEPTH = 2.0  # m

DEPTH_TOL = 0.05  # m  — assertion tolerance (float32 arithmetic headroom)


def _slope_elev(r: int, c: int) -> float:
    """Return the unperturbed slope elevation at (r, c)."""
    return BASE_ELEV - r * SLOPE_R - c * SLOPE_C


def _min_neighbour(r: int, c: int) -> float:
    """
    Return the minimum elevation among the 8 neighbours of (r, c) on the
    uniform slope.  On this south-east draining slope it is always the SE
    neighbour (r+1, c+1).
    """
    return _slope_elev(r + 1, c + 1)


# ── Step 1: create DEM ────────────────────────────────────────────────────────


def create_controlled_dem() -> None:
    """
    Write a 60 × 60 south-east-sloping DEM with two isolated pit cells to
    ``outputs/depression_test/controlled_dem.tif``.
    """
    r_idx, c_idx = np.mgrid[0:ROWS, 0:COLS]
    elevation = (BASE_ELEV - r_idx * SLOPE_R - c_idx * SLOPE_C).astype("float32")

    # Punch pit 1 — strictly below all 8 neighbours
    mn1 = _min_neighbour(PIT1_ROW, PIT1_COL)
    pit1_elev = mn1 - PIT1_IMPOSED_DEPTH
    elevation[PIT1_ROW, PIT1_COL] = pit1_elev

    # Punch pit 2 — strictly below all 8 neighbours
    mn2 = _min_neighbour(PIT2_ROW, PIT2_COL)
    pit2_elev = mn2 - PIT2_IMPOSED_DEPTH
    elevation[PIT2_ROW, PIT2_COL] = pit2_elev

    # Same CRS / pixel size as the Silk Board terrain test for consistency
    transform = from_origin(500000, 1500000, 10, 10)

    with rasterio.open(
        DEM_PATH,
        "w",
        driver="GTiff",
        height=ROWS,
        width=COLS,
        count=1,
        dtype="float32",
        crs="EPSG:32643",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(elevation, 1)

    print(f"[CREATE] {DEM_PATH}")
    print(f"         Grid {ROWS}x{COLS}, SE slope {SLOPE_R} m/row · {SLOPE_C} m/col")
    print(f"         Elevation range: {elevation.min():.2f} – {elevation.max():.2f} m")
    print()
    print(f"         Pit 1  @ ({PIT1_ROW:2d},{PIT1_COL:2d})")
    print(
        f"                  slope elev       = {_slope_elev(PIT1_ROW, PIT1_COL):.2f} m"
    )
    print(
        f"                  min neighbour    = {mn1:.2f} m  (SE cell {PIT1_ROW + 1},{PIT1_COL + 1})"
    )
    print(f"                  pit elevation    = {pit1_elev:.2f} m")
    print(f"                  imposed depth    = {PIT1_IMPOSED_DEPTH:.2f} m")
    print(f"                  expected WBT     = {mn1 - pit1_elev:.2f} m")
    print()
    print(f"         Pit 2  @ ({PIT2_ROW:2d},{PIT2_COL:2d})")
    print(
        f"                  slope elev       = {_slope_elev(PIT2_ROW, PIT2_COL):.2f} m"
    )
    print(
        f"                  min neighbour    = {mn2:.2f} m  (SE cell {PIT2_ROW + 1},{PIT2_COL + 1})"
    )
    print(f"                  pit elevation    = {pit2_elev:.2f} m")
    print(f"                  imposed depth    = {PIT2_IMPOSED_DEPTH:.2f} m")
    print(f"                  expected WBT     = {mn2 - pit2_elev:.2f} m")


# ── Step 2: run WhiteboxTools ─────────────────────────────────────────────────


def run_depth_in_sink() -> None:
    """
    Call WhiteboxTools ``depth_in_sink`` using absolute input / output paths.

    ``wbt.set_working_dir`` is set to ``OUT_DIR`` as WBT requires it even
    when absolute paths are supplied.  ``zero_background=False`` (default)
    means non-depression cells receive NoData rather than 0, enabling a
    precise count of flagged cells.

    Raises
    ------
    FileNotFoundError
        If the input DEM or the expected output file is missing.
    RuntimeError
        If WhiteboxTools returns a non-zero exit code.
    """
    if not DEM_PATH.exists():
        raise FileNotFoundError(f"Controlled DEM not found: {DEM_PATH}")

    wbt = WhiteboxTools()
    wbt.set_working_dir(str(OUT_DIR))  # required by WBT even with absolute paths
    wbt.verbose = True

    print("[WBT]  depth_in_sink")
    print(f"       input  -> {DEM_PATH}")
    print(f"       output -> {DEPTH_PATH}")
    print("       zero_background = False  (background => NoData, not 0)")
    print()

    ret = wbt.depth_in_sink(
        dem=str(DEM_PATH),
        output=str(DEPTH_PATH),
        zero_background=False,
    )

    if ret != 0:
        raise RuntimeError(
            f"WhiteboxTools depth_in_sink exited with code {ret}. "
            "Check WBT messages above."
        )

    # Explicit post-call existence check (WBT can return 0 yet not write output)
    if not DEPTH_PATH.exists():
        raise FileNotFoundError(
            f"Expected output file was not created: {DEPTH_PATH}\n"
            "Check WBT messages above for clues."
        )

    print(f"       output written: {DEPTH_PATH.stat().st_size:,} bytes")


# ── Step 3: inspect and verify ────────────────────────────────────────────────


def verify_depth_results() -> tuple[float, float]:
    """
    Read the DepthInSink raster, print a full summary of actual values,
    then assert correctness within tolerance.

    The actual WBT depths are printed unconditionally BEFORE any assertion
    is evaluated, so observed vs. expected is always visible in the output.

    Returns
    -------
    (pit1_actual, pit2_actual) — the raw depths read from the raster.

    Raises
    ------
    AssertionError
        If any assertion fails; all failures are collected and reported
        together rather than stopping at the first one.
    """
    with rasterio.open(DEPTH_PATH) as src:
        depth = src.read(1)
        nodata = src.nodata
        crs = src.crs
        dtype = src.dtypes[0]
        shape = (src.height, src.width)

    # Build valid (non-NoData) mask
    valid_mask = (depth != nodata) if nodata is not None else np.ones(shape, bool)

    valid_count = int(valid_mask.sum())
    positive_count = int((depth[valid_mask] > 0).sum()) if valid_count > 0 else 0

    # Read actual depths BEFORE asserting anything
    pit1_actual = float(depth[PIT1_ROW, PIT1_COL])
    pit2_actual = float(depth[PIT2_ROW, PIT2_COL])

    # Expected depths (analytically derived from DEM geometry)
    pit1_expected = PIT1_IMPOSED_DEPTH  # = mn1 - pit1_elev = imposed_depth
    pit2_expected = PIT2_IMPOSED_DEPTH

    # ── Print raster summary ──────────────────────────────────────────────────
    sep = "=" * 64
    print()
    print(sep)
    print("DEPTH-IN-SINK VERIFICATION REPORT")
    print(sep)
    print(f"  Output file   : {DEPTH_PATH.name}")
    print(f"  CRS           : {crs}")
    print(f"  Shape         : {shape[0]} rows x {shape[1]} cols")
    print(f"  Dtype         : {dtype}")
    print(f"  NoData value  : {nodata}")
    print(f"  Valid cells   : {valid_count} / {depth.size}")
    print(f"  Cells > 0 m   : {positive_count}")
    if valid_count > 0:
        valid_vals = depth[valid_mask]
        print(f"  Max depth     : {valid_vals.max():.4f} m")
        print(f"  Min depth     : {valid_vals.min():.4f} m")
    print()

    # Raw values at pit locations (no filtering — exact pixel read)
    print("  Raw raster values at pit locations (before any assertion):")
    print(f"    Pit 1 depth[{PIT1_ROW},{PIT1_COL}] = {pit1_actual:.6f} m")
    print(f"    Pit 2 depth[{PIT2_ROW},{PIT2_COL}] = {pit2_actual:.6f} m")
    print()

    # ── Per-pit result table ──────────────────────────────────────────────────
    hdr = f"{'Pit':<6}  {'(row,col)':<10}  {'Expected':>10}  {'WBT actual':>12}  {'Delta':>8}  {'Result':>8}"
    print(hdr)
    print("-" * len(hdr))

    failures: list[str] = []

    pits = [
        ("Pit 1", PIT1_ROW, PIT1_COL, pit1_expected, pit1_actual),
        ("Pit 2", PIT2_ROW, PIT2_COL, pit2_expected, pit2_actual),
    ]
    for label, row, col, expected, actual in pits:
        delta = actual - expected
        passed = abs(delta) <= DEPTH_TOL
        badge = "PASS" if passed else "FAIL"
        print(
            f"{label:<6}  ({row:2d},{col:2d})      "
            f"{expected:>10.4f}  {actual:>12.4f}  {delta:>+8.4f}  {badge:>8}"
        )
        if not passed:
            failures.append(
                f"  {label} @ ({row},{col}): expected {expected:.4f} m, "
                f"got {actual:.4f} m  (delta={delta:+.4f} m, tol +/- {DEPTH_TOL} m)"
            )

    # ── Positive-depth cell count (the key structural assertion) ──────────────
    #
    # On a uniform SE slope every anti-diagonal (r+c = K) shares one elevation.
    # WBT marks the entire iso-contour at the spill level as the depression
    # boundary, writing depth=0 (not NoData) for those rim cells.  This means
    # valid_count will be > 2 (one anti-diagonal per pit), but positive_count
    # (cells with depth > 0) will still equal exactly 2 -- one per true pit.
    # We therefore assert on positive_count, not valid_count.
    boundary_count = valid_count - positive_count
    count_ok = positive_count == 2
    count_badge = "PASS" if count_ok else "FAIL"
    print("-" * len(hdr))
    print(
        f"{'Cells with depth > 0 (true pits)':<40}  "
        f"expected=2  got={positive_count}  {count_badge}"
    )
    print(
        f"{'Cells with depth = 0 (rim boundary)':<40}  "
        f"got={boundary_count}  (iso-contour artefact, informational)"
    )
    print(sep)

    if not count_ok:
        failures.append(
            f"  Positive-depth cell count: expected 2, got {positive_count}. "
            f"(total valid={valid_count}, boundary rim={boundary_count})"
        )

    if failures:
        raise AssertionError(
            "Depression test FAILED — depth assertion(s) not met:\n"
            + "\n".join(failures)
        )

    print()
    print("  All depth assertions PASSED.")
    return pit1_actual, pit2_actual


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    sep = "=" * 64

    # Print WBT version (first line only)
    _wbt_version = WhiteboxTools().version().splitlines()[0]

    print(sep)
    print("CONTROLLED DEPRESSION TEST  --  gis/test_depression.py")
    print(f"  WhiteboxTools : {_wbt_version}")
    print(f"  Output dir    : {OUT_DIR}")
    print(sep)
    print()

    create_controlled_dem()
    print()
    run_depth_in_sink()
    verify_depth_results()

    print()
    print("[DONE]  Test complete.")
    print(f"        Outputs written to : {OUT_DIR}")
    print(
        "        Unchanged           : outputs/terrain_test/  |  data/risk/hazard_*.geojson"
    )
    print()


if __name__ == "__main__":
    main()
