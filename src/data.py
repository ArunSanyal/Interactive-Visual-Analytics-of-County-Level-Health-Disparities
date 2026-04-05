"""
src/data.py
===========
Loads pre-processed outputs at module-import time and exposes them as
module-level globals so every callback uses cached data without re-reading.

Globals
-------
GEOJSON   : dict          – full county GeoJSON
COUNTIES  : pd.DataFrame  – tabular county data (matches GeoJSON)
STATES    : list[str]     – sorted state names for the dropdown
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import METRICS

METRIC_COLS: list = list(METRICS.keys())

# ── Resolve paths ─────────────────────────────────────────────────────────────
_ROOT         = Path(__file__).resolve().parent.parent
_GEOJSON_PATH = _ROOT / "outputs" / "counties_chr_2025.geojson"
_CSV_PATH     = _ROOT / "outputs" / "chr_clean.csv"


# ══════════════════════════════════════════════════════════════════════════════
def _load() -> tuple:
    if not _GEOJSON_PATH.exists() or not _CSV_PATH.exists():
        raise FileNotFoundError(
            "Preprocessed outputs not found.\n"
            "Run:  python scripts/preprocess.py\n"
            f"Expected:\n  {_GEOJSON_PATH}\n  {_CSV_PATH}"
        )

    # GeoJSON ─────────────────────────────────────────────────────────────────
    with open(_GEOJSON_PATH, "r", encoding="utf-8") as fh:
        geojson = json.load(fh)

    # Tabular CSV ─────────────────────────────────────────────────────────────
    df = pd.read_csv(
        str(_CSV_PATH),
        dtype={"GEOID": str, "STATEFP": str},
        low_memory=False,
    )
    df["GEOID"] = df["GEOID"].astype(str).str.zfill(5)

    for col in METRIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            warnings.warn(f"Metric column not found in CSV: {col!r}")
            df[col] = np.nan

    states = sorted(df["State"].dropna().unique().tolist())
    return geojson, df, states


# Module-level load – runs once at import
try:
    GEOJSON, COUNTIES, STATES = _load()
    _LOAD_ERROR: str | None = None
except Exception as _exc:
    GEOJSON   = {"type": "FeatureCollection", "features": []}
    COUNTIES  = pd.DataFrame(
        columns=["GEOID", "State", "County", "NAME", "STATEFP"] + METRIC_COLS
    )
    STATES    = []
    _LOAD_ERROR = str(_exc)


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions used by callbacks
# ══════════════════════════════════════════════════════════════════════════════

def filter_by_state(df: pd.DataFrame, state: str | None) -> pd.DataFrame:
    """Return subset of df for a given state name, or full df when state is 'All'."""
    if not state or state == "All":
        return df
    return df[df["State"] == state].copy()


def filter_geojson(geojson: dict, geoid_set: set) -> dict:
    """Return a GeoJSON FeatureCollection limited to features in geoid_set."""
    return {
        "type": "FeatureCollection",
        "features": [
            f for f in geojson["features"]
            if (f.get("properties") or {}).get("GEOID") in geoid_set
        ],
    }


def load_error() -> str | None:
    """Return load error string if data is missing, else None."""
    return _LOAD_ERROR
