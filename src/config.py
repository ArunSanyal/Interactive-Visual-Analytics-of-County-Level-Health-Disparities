"""
Configuration for County Health Disparities Explorer.
=======================================================
Edit the METRICS dict to change column names or add/remove metrics.
Keys must match column names in outputs/chr_clean.csv (set in preprocess.py).
"""

# ---------------------------------------------------------------------------
# Metric definitions
# key   = exact column name in outputs/chr_clean.csv
# label = display label shown in UI dropdowns
# unit  = shown in hover tooltips
# higher_is_worse = True means high value = bad (drives colorscale direction)
# ---------------------------------------------------------------------------
METRICS: dict = {
    "Average Number of Physically Unhealthy Days": {
        "label": "Physically Unhealthy Days",
        "short_label": "Phys. Unhealthy",
        "description": "Avg. physically unhealthy days per month (self-reported)",
        "unit": "days/month",
        "higher_is_worse": True,
    },
    "Years of Potential Life Lost Rate": {
        "label": "Premature Death (YPLL Rate)",
        "short_label": "YPLL Rate",
        "description": "Years of Potential Life Lost per 100,000 population (age-adjusted)",
        "unit": "per 100k",
        "higher_is_worse": True,
    },
    "Average Number of Mentally Unhealthy Days": {
        "label": "Mentally Unhealthy Days",
        "short_label": "Ment. Unhealthy",
        "description": "Avg. mentally unhealthy days per month (self-reported)",
        "unit": "days/month",
        "higher_is_worse": True,
    },
    "% Fair or Poor Health": {
        "label": "% Fair or Poor Health",
        "short_label": "Fair/Poor Health",
        "description": "Adults reporting fair or poor health status",
        "unit": "proportion (0–1)",
        "higher_is_worse": True,
    },
    "% Uninsured": {
        "label": "% Uninsured",
        "short_label": "Uninsured",
        "description": "Population without health insurance coverage",
        "unit": "proportion (0–1)",
        "higher_is_worse": True,
    },
    "% Unemployed": {
        "label": "% Unemployed",
        "short_label": "Unemployed",
        "description": "Civilian labor force that is unemployed",
        "unit": "proportion (0–1)",
        "higher_is_worse": True,
    },
    "% Children in Poverty": {
        "label": "% Children in Poverty",
        "short_label": "Child Poverty",
        "description": "Children living below the federal poverty level",
        "unit": "proportion (0–1)",
        "higher_is_worse": True,
    },
}

# ---------------------------------------------------------------------------
# Column positions in the CHR Excel "Select Measure Data" sheet (0-indexed).
# These are used by scripts/preprocess.py via iloc.
# Edit these if the CHR data layout changes in a future release.
# ---------------------------------------------------------------------------
CHR_COL_POSITIONS: dict = {
    "FIPS":                                          0,
    "State":                                         1,
    "County":                                        2,
    "Years of Potential Life Lost Rate":             5,
    "Average Number of Physically Unhealthy Days":  37,
    "Average Number of Mentally Unhealthy Days":    67,
    "% Fair or Poor Health":                        71,
    "% Uninsured":                                 113,
    "% Unemployed":                                179,
    "% Children in Poverty":                       185,
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_METRIC  = "Average Number of Physically Unhealthy Days"
DEFAULT_X       = "% Uninsured"
DEFAULT_Y       = "Average Number of Physically Unhealthy Days"
DEFAULT_METHOD  = "quantile"
DEFAULT_K       = 7

# ---------------------------------------------------------------------------
# Classification methods (key → display label)
# ---------------------------------------------------------------------------
CLASSIFICATION_METHODS: dict = {
    "quantile":       "Quantile",
    "equal_interval": "Equal Interval",
    "natural_breaks": "Natural Breaks (Jenks)",
    "std_mean":       "Std. Mean Deviation",
}

# ---------------------------------------------------------------------------
# Parallel coordinates: order of dimensions (must all be keys in METRICS)
# ---------------------------------------------------------------------------
PARCOORDS_METRICS: list = list(METRICS.keys())

# ---------------------------------------------------------------------------
# H3 hex resolution (4 ≈ ~1,770 km² hexes → ~1,000–2,000 hexes over the US)
# Increase for finer hexes, decrease for coarser.
# ---------------------------------------------------------------------------
H3_RESOLUTION: int = 4

# ---------------------------------------------------------------------------
# Visual
# ---------------------------------------------------------------------------
COLORSCALE_HIGH_BAD  = "YlOrRd"     # high value = worse (most health metrics)
COLORSCALE_HIGH_GOOD = "RdYlGn"     # high value = better
NEUTRAL_COLOR        = "#adb5bd"    # missing / suppressed data

APP_TITLE    = "County Health Disparities Explorer"
APP_SUBTITLE = "2025 County Health Rankings  ·  CS 544 Advanced Data Visualization"
