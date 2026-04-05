"""
src/h3hex.py
============
H3 hexagonal aggregation utilities for the "equal-area hex view".

Motivation (area-bias mitigation)
----------------------------------
Traditional county choropleths are dominated visually by large western counties
even when those counties have small populations.  Mapping data to H3 hexagons
(each with the same area at a given resolution) gives equal screen space to
every hex regardless of the underlying county size, reducing this perceptual bias.

How it works
------------
1. Compute the centroid of each county polygon.
2. Assign each centroid an H3 cell index at the chosen resolution
   (config.H3_RESOLUTION = 4 → hex avg. area ≈ 1,770 km²).
3. Group counties by H3 index and compute the mean of the selected metric
   (area-weighted mean would be more accurate but is overkill here).
4. Convert H3 cell indices → polygon coordinates for rendering.

Public API
----------
build_hex_layer(df, geojson, metric, resolution)
    → (hex_geojson: dict, hex_df: pd.DataFrame)
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

try:
    import h3
    _H3_VERSION = int(h3.__version__.split(".")[0])
except ImportError:
    h3 = None
    _H3_VERSION = 0


# ══════════════════════════════════════════════════════════════════════════════
# Compatibility shims for h3-py v3 vs v4
# ══════════════════════════════════════════════════════════════════════════════

def _latlng_to_cell(lat: float, lng: float, res: int) -> str:
    if _H3_VERSION >= 4:
        return h3.latlng_to_cell(lat, lng, res)
    return h3.geo_to_h3(lat, lng, res)


def _cell_to_boundary(cell: str) -> list:
    """Returns list of (lat, lng) tuples."""
    if _H3_VERSION >= 4:
        return h3.cell_to_boundary(cell)
    return h3.h3_to_geo_boundary(cell)


# ══════════════════════════════════════════════════════════════════════════════
# Centroid extraction from GeoJSON
# ══════════════════════════════════════════════════════════════════════════════

def _geojson_centroid(feature: dict) -> tuple[float, float] | None:
    """
    Compute the approximate centroid of a GeoJSON polygon feature.
    Returns (lat, lon) or None if geometry is missing.
    """
    geom = feature.get("geometry") or {}
    gtype = geom.get("type", "")
    coords = geom.get("coordinates") or []

    try:
        if gtype == "Polygon":
            ring = coords[0]
        elif gtype == "MultiPolygon":
            # Use the largest ring (most coords) as representative
            ring = max((p[0] for p in coords), key=len)
        else:
            return None
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]
        return float(np.mean(lats)), float(np.mean(lons))
    except (IndexError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Main public function
# ══════════════════════════════════════════════════════════════════════════════

def build_hex_layer(
    df: pd.DataFrame,
    geojson: dict,
    metric: str,
    resolution: int = 4,
) -> tuple[dict, pd.DataFrame]:
    """
    Build an H3 hex choropleth layer from county-level data.

    Parameters
    ----------
    df         : county DataFrame (must have GEOID and the metric column)
    geojson    : county GeoJSON (features must have properties.GEOID)
    metric     : column name of the metric to aggregate
    resolution : H3 resolution (default 4)

    Returns
    -------
    hex_geojson : GeoJSON FeatureCollection of hex polygons
    hex_df      : DataFrame with columns [h3_index, value, count]
    """
    if h3 is None:
        warnings.warn("h3 library not installed – hex view unavailable.")
        return {"type": "FeatureCollection", "features": []}, pd.DataFrame(
            columns=["h3_index", "value", "count"]
        )

    # ── Build GEOID → centroid map from GeoJSON ────────────────────────────────
    centroid_map: dict[str, tuple[float, float]] = {}
    for feat in geojson.get("features", []):
        geoid = (feat.get("properties") or {}).get("GEOID")
        if not geoid:
            continue
        c = _geojson_centroid(feat)
        if c is not None:
            centroid_map[geoid] = c

    # ── Assign H3 index per county ─────────────────────────────────────────────
    rows = []
    for _, row in df.iterrows():
        geoid = str(row["GEOID"]).zfill(5)
        val   = row.get(metric)
        if pd.isna(val):
            continue
        centroid = centroid_map.get(geoid)
        if centroid is None:
            continue
        lat, lng = centroid
        try:
            h3_idx = _latlng_to_cell(lat, lng, resolution)
        except Exception:
            continue
        rows.append({"h3_index": h3_idx, "value": float(val)})

    if not rows:
        return {"type": "FeatureCollection", "features": []}, pd.DataFrame(
            columns=["h3_index", "value", "count"]
        )

    tmp = pd.DataFrame(rows)
    hex_df = tmp.groupby("h3_index").agg(
        value=("value", "mean"),
        count=("value", "count"),
    ).reset_index()

    # ── Build GeoJSON polygons ─────────────────────────────────────────────────
    features = []
    for _, row in hex_df.iterrows():
        cell = row["h3_index"]
        try:
            boundary = _cell_to_boundary(cell)   # [(lat, lng), ...]
        except Exception:
            continue
        # GeoJSON coordinates are [lng, lat]
        coords = [[round(lng, 5), round(lat, 5)] for lat, lng in boundary]
        coords.append(coords[0])                 # close ring
        features.append({
            "type": "Feature",
            "id":   cell,
            "properties": {
                "h3_index": cell,
                "value":    round(row["value"], 4),
                "count":    int(row["count"]),
            },
            "geometry": {
                "type":        "Polygon",
                "coordinates": [coords],
            },
        })

    hex_geojson = {"type": "FeatureCollection", "features": features}
    return hex_geojson, hex_df
