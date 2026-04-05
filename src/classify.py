"""
src/classify.py
===============
Classification utilities wrapping mapclassify.

Supported methods (matching config.CLASSIFICATION_METHODS keys):
  quantile       – Quantile breaks
  equal_interval – Equal-interval breaks
  natural_breaks – Natural Breaks (Jenks)
  std_mean       – Standard deviation from mean

Public API
----------
classify(values, method, k)  →  ClassifyResult
    .bins        – list of break upper-bounds (length k)
    .breaks      – full list [min, b1, b2, …, max]   (length k+1)
    .class_num   – pd.Series of integer class labels 1..k (NaN → NaN)
    .k           – actual number of classes used
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import mapclassify as mc


@dataclass
class ClassifyResult:
    bins:      list        # upper bounds from mapclassify (len == k)
    breaks:    list        # [data_min, b1, …, data_max] (len == k+1)
    class_num: pd.Series   # 1-indexed class labels, NaN where data is NaN
    k:         int         # actual number of classes (may be < requested)
    method:    str


# ── internal ──────────────────────────────────────────────────────────────────

def _safe_k(values: pd.Series, k: int) -> int:
    """Clamp k to [2, number_of_unique_valid_values]."""
    n_unique = values.dropna().nunique()
    return max(2, min(k, n_unique))


def _build_classifier(values_arr: np.ndarray, method: str, k: int):
    """Run mapclassify and return the classifier object."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if method == "quantile":
            return mc.Quantiles(values_arr, k=k)
        elif method == "equal_interval":
            return mc.EqualInterval(values_arr, k=k)
        elif method == "natural_breaks":
            return mc.NaturalBreaks(values_arr, k=k)
        elif method == "std_mean":
            clf = mc.StdMean(values_arr)
            return clf
        else:
            return mc.Quantiles(values_arr, k=k)


def _assign_classes(clf, values: pd.Series) -> pd.Series:
    """
    Assign 1-based class label to every element of values.
    NaN → NaN.  Uses clf.bins (upper bounds) with searchsorted.
    """
    bins = np.array(clf.bins)
    k    = len(bins)

    def _label(v):
        if pd.isna(v):
            return np.nan
        idx = int(np.searchsorted(bins, v, side="right"))
        return min(idx + 1, k)          # 1-indexed, clipped to k

    return values.apply(_label)


# ── public ────────────────────────────────────────────────────────────────────

def classify(values: pd.Series, method: str, k: int) -> ClassifyResult:
    """
    Classify a numeric Series.

    Parameters
    ----------
    values : pd.Series   – raw metric values (may contain NaN)
    method : str         – one of the CLASSIFICATION_METHODS keys
    k      : int         – desired number of classes (clamped to data)

    Returns
    -------
    ClassifyResult
    """
    valid = values.dropna()
    if len(valid) == 0:
        # No data – return a dummy result
        return ClassifyResult(
            bins=[0.0], breaks=[0.0, 0.0], class_num=values * np.nan, k=1, method=method
        )

    k_actual = _safe_k(valid, k)
    clf      = _build_classifier(valid.values.astype(float), method, k_actual)
    k_actual = len(clf.bins)            # StdMean sets its own k

    data_min = float(valid.min())
    data_max = float(valid.max())
    bins_list = [float(b) for b in clf.bins]
    breaks    = [data_min] + bins_list
    # Ensure last break == data_max (floating-point guard)
    if breaks[-1] < data_max:
        breaks[-1] = data_max

    class_num = _assign_classes(clf, values)

    return ClassifyResult(
        bins=bins_list,
        breaks=breaks,
        class_num=class_num,
        k=k_actual,
        method=method,
    )


def class_labels(result: ClassifyResult) -> list[str]:
    """
    Build human-readable class labels for the legend/colorbar.
    Returns a list of k strings like  "1: ≤ 1,234"  or  "5: ≤ 56.7%".
    """
    labels = []
    for i, ub in enumerate(result.bins):
        if i == 0:
            labels.append(f"Class 1: ≤ {_fmt(ub)}")
        else:
            lb = result.bins[i - 1]
            labels.append(f"Class {i+1}: {_fmt(lb)} – {_fmt(ub)}")
    return labels


def _fmt(v: float) -> str:
    """Compact number formatter for class labels."""
    if abs(v) >= 1_000:
        return f"{v:,.0f}"
    if abs(v) >= 1:
        return f"{v:.2f}"
    return f"{v:.4f}"


def discrete_colorscale(k: int, palette: str = "RdYlGn_r") -> list[list]:
    """
    Build a discrete (step) colorscale suitable for plotly choropleth.
    Returns list of [position, color] pairs that create solid bands.
    """
    import plotly.colors as pc
    positions = [i / k for i in range(k + 1)]
    sampled   = pc.sample_colorscale(palette, [i / (k - 1) if k > 1 else 0.5 for i in range(k)])
    cs = []
    for i, color in enumerate(sampled):
        cs.append([positions[i],     color])
        cs.append([positions[i + 1], color])
    return cs
