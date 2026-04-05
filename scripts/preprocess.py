"""
scripts/preprocess.py
=====================
Reads the Census TIGER shapefile and the 2025 County Health Rankings Excel file,
joins them on 5-digit FIPS (GEOID), and writes:
  outputs/counties_chr_2025.geojson   – county boundaries + CHR metrics
  outputs/chr_clean.csv               – tabular (no geometry)

Run once before starting the app:
    python scripts/preprocess.py
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SHP_PATH = DATA_DIR / "tl_2025_us_county.shp"
XLS_PATH = DATA_DIR / "2025 County Health Rankings Data - v4.xlsx"

# ── Import config (column positions + metric list) ────────────────────────────
sys.path.insert(0, str(ROOT))
from src.config import CHR_COL_POSITIONS, METRICS

SELECTED_METRICS = list(METRICS.keys())

# ── Geometry simplification tolerance (degrees; ~1 km) ────────────────────────
SIMPLIFY_TOL = 0.01


# ══════════════════════════════════════════════════════════════════════════════
# 1. Load shapefile
# ══════════════════════════════════════════════════════════════════════════════
def load_shapefile() -> gpd.GeoDataFrame:
    print(f"  Reading shapefile: {SHP_PATH}")
    gdf = gpd.read_file(str(SHP_PATH))
    gdf = gdf[["GEOID", "NAME", "STATEFP", "geometry"]].copy()
    gdf = gdf.to_crs("EPSG:4326")
    # Simplify geometry to reduce output file size
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOL, preserve_topology=True)
    print(f"  Shapefile: {len(gdf):,} county polygons loaded.")
    return gdf


# ══════════════════════════════════════════════════════════════════════════════
# 2. Load CHR Excel data
# ══════════════════════════════════════════════════════════════════════════════
def _safe_fips(val) -> str | None:
    """Convert a raw FIPS cell to a zero-padded 5-digit string."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return str(int(float(str(val).strip()))).zfill(5)
    except (ValueError, OverflowError):
        s = str(val).strip()
        return s.zfill(5) if s.isdigit() else None


def load_chr() -> pd.DataFrame:
    print(f"  Reading CHR Excel: {XLS_PATH}")
    # header=1: row 0 = group labels (skip), row 1 = column names, row 2+ = data
    raw = pd.read_excel(
        str(XLS_PATH),
        sheet_name="Select Measure Data",
        header=1,
        dtype=object,          # keep everything as object to avoid FIPS becoming float
    )
    print(f"  CHR sheet dimensions: {raw.shape[0]} rows × {raw.shape[1]} cols")

    # ── Extract columns by position (avoids duplicate-name ambiguity) ──────────
    selected: dict = {}
    for col_name, pos in CHR_COL_POSITIONS.items():
        if pos < raw.shape[1]:
            selected[col_name] = raw.iloc[:, pos].values
        else:
            print(f"  WARNING: column position {pos} ({col_name!r}) out of range – filling NaN")
            selected[col_name] = np.full(len(raw), np.nan)

    chr_df = pd.DataFrame(selected)

    # ── FIPS → GEOID (5-digit, zero-padded) ───────────────────────────────────
    chr_df["GEOID"] = chr_df["FIPS"].apply(_safe_fips)
    chr_df = chr_df.drop(columns=["FIPS"])

    # ── Drop state-level aggregates (GEOID ends in '000') ─────────────────────
    mask_county = chr_df["GEOID"].notna() & ~chr_df["GEOID"].str.endswith("000")
    chr_df = chr_df[mask_county].copy()
    print(f"  CHR: {len(chr_df):,} county rows after filtering state-level rows.")

    # ── Coerce metric columns to numeric ──────────────────────────────────────
    for metric in SELECTED_METRICS:
        if metric in chr_df.columns:
            chr_df[metric] = pd.to_numeric(chr_df[metric], errors="coerce")

    # ── Diagnostic: proportion of valid values per metric ─────────────────────
    print("\n  Metric coverage (non-null / total counties):")
    for metric in SELECTED_METRICS:
        if metric in chr_df.columns:
            n_valid = chr_df[metric].notna().sum()
            pct     = 100 * n_valid / len(chr_df)
            print(f"    {metric[:55]:<56s} {n_valid:4d} / {len(chr_df)} ({pct:.0f}%)")

    return chr_df


# ══════════════════════════════════════════════════════════════════════════════
# 3. Merge shapefile + CHR on GEOID
# ══════════════════════════════════════════════════════════════════════════════
def merge_data(gdf: gpd.GeoDataFrame, chr_df: pd.DataFrame) -> gpd.GeoDataFrame:
    keep_cols = ["GEOID", "State", "County"] + SELECTED_METRICS
    keep_cols = [c for c in keep_cols if c in chr_df.columns]

    merged_left = gdf.merge(chr_df[keep_cols], on="GEOID", how="left")

    total     = len(gdf)
    matched   = merged_left["State"].notna().sum()
    unmatched = merged_left.loc[merged_left["State"].isna(), "GEOID"].head(15).tolist()

    print(f"\n  Merge diagnostics:")
    print(f"    Total shapefile polygons : {total:,}")
    print(f"    Matched to CHR data      : {matched:,}")
    print(f"    Unmatched (no CHR data)  : {total - matched:,}  (territories removed from GeoJSON)")
    if unmatched:
        print(f"    Sample unmatched GEOIDs  : {unmatched}")

    # Inner join: only keep polygons that have CHR data (removes territories/islands)
    merged = gdf.merge(chr_df[keep_cols], on="GEOID", how="inner")
    print(f"    Final GeoJSON polygons   : {len(merged):,}")
    return merged


# ══════════════════════════════════════════════════════════════════════════════
# 4. Save outputs
# ══════════════════════════════════════════════════════════════════════════════
def save_outputs(merged: gpd.GeoDataFrame) -> None:
    # ── GeoJSON ────────────────────────────────────────────────────────────────
    geojson_path = OUTPUT_DIR / "counties_chr_2025.geojson"
    print(f"\n  Writing GeoJSON → {geojson_path}")
    merged.to_file(str(geojson_path), driver="GeoJSON")

    # Reduce coordinate precision to 5 decimal places (~1 m accuracy)
    with open(geojson_path, "r", encoding="utf-8") as fh:
        gj = json.load(fh)

    def _round_coords(obj):
        if isinstance(obj, list):
            return [_round_coords(item) for item in obj]
        if isinstance(obj, float):
            return round(obj, 5)
        return obj

    for feature in gj.get("features", []):
        geom = feature.get("geometry") or {}
        if geom.get("coordinates") is not None:
            geom["coordinates"] = _round_coords(geom["coordinates"])

    with open(geojson_path, "w", encoding="utf-8") as fh:
        json.dump(gj, fh, separators=(",", ":"))

    size_mb = geojson_path.stat().st_size / 1_048_576
    print(f"  GeoJSON saved: {size_mb:.1f} MB")

    # ── CSV (no geometry) ──────────────────────────────────────────────────────
    csv_path = OUTPUT_DIR / "chr_clean.csv"
    csv_df   = merged.drop(columns=["geometry"])
    csv_df.to_csv(str(csv_path), index=False)
    print(f"  CSV saved: {csv_path.stat().st_size / 1_048_576:.1f} MB  ({len(csv_df):,} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("County Health Rankings – Preprocessing")
    print("=" * 60)

    print("\n[1/4] Loading shapefile …")
    gdf = load_shapefile()

    print("\n[2/4] Loading CHR Excel …")
    chr_df = load_chr()

    print("\n[3/4] Merging on GEOID …")
    merged = merge_data(gdf, chr_df)

    print("\n[4/4] Saving outputs …")
    save_outputs(merged)

    print("\n✓ Preprocessing complete.\n")
