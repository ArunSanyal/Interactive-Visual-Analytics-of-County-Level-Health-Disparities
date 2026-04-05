"""
src/figures.py
==============
Factory functions that return Plotly figures for each view panel.
All functions are pure (no side-effects) and designed to be called from
Dash callbacks with pre-filtered data.

Functions
---------
make_choropleth   – county choropleth map
make_hex_map      – H3 hex choropleth map
make_histogram    – metric distribution + class-break lines
make_scatter      – bivariate scatter with selection highlighting
make_parcoords    – parallel coordinates with selection highlighting
make_empty_fig    – placeholder when no data is available
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc

from src.config import (
    METRICS,
    COLORSCALE_HIGH_BAD,
    COLORSCALE_HIGH_GOOD,
    NEUTRAL_COLOR,
    PARCOORDS_METRICS,
)
from src.classify import ClassifyResult, discrete_colorscale


# ── Shared style constants ────────────────────────────────────────────────────
_BG         = "rgba(0,0,0,0)"
_PANEL_BG   = "#1e2130"
_GRID_COLOR = "rgba(255,255,255,0.08)"
_TEXT_COLOR = "#dee2e6"
_FONT       = dict(family="Inter, sans-serif", color=_TEXT_COLOR, size=12)
_MAPBOX_STYLE = "carto-darkmatter"


def _colorscale_for_metric(metric: str) -> str:
    cfg = METRICS.get(metric, {})
    return COLORSCALE_HIGH_BAD if cfg.get("higher_is_worse", True) else COLORSCALE_HIGH_GOOD


def _base_layout(**kwargs) -> dict:
    base = dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_PANEL_BG,
        font=_FONT,
        margin=dict(l=8, r=8, t=36, b=8),
    )
    base.update(kwargs)   # caller kwargs override defaults
    return base


def make_empty_fig(msg: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=14, color=_TEXT_COLOR),
    )
    fig.update_layout(**_base_layout())
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Choropleth map – county mode
# ══════════════════════════════════════════════════════════════════════════════

def make_choropleth(
    df: pd.DataFrame,
    geojson: dict,
    metric: str,
    result: ClassifyResult,
    selected_geoids: list[str] | None = None,
    center: dict | None = None,
    zoom: float = 3.0,
) -> go.Figure:
    """County-level choropleth coloured by classification class."""
    if df.empty or not geojson.get("features"):
        return make_empty_fig("No county data for selected filters.")

    label   = METRICS.get(metric, {}).get("label", metric)
    cs_name = _colorscale_for_metric(metric)
    k       = result.k
    cs      = discrete_colorscale(k, cs_name)

    sel_set = set(selected_geoids or [])

    # Prepare display dataframe
    plot_df = df[["GEOID", "State", "County", "NAME", metric]].copy()
    plot_df = plot_df.rename(columns={metric: "_val"})
    plot_df["_class"] = result.class_num.reindex(df.index).values
    plot_df["_val_fmt"] = plot_df["_val"].apply(
        lambda v: f"{v:,.2f}" if pd.notna(v) else "No data"
    )
    plot_df["_label"] = plot_df.apply(
        lambda r: f"<b>{r.get('County') or r.get('NAME', '')}, {r.get('State','')}</b>"
                  f"<br>{label}: {r['_val_fmt']}"
                  f"{'<br><b>✓ Selected</b>' if r['GEOID'] in sel_set else ''}",
        axis=1,
    )

    # Split counties: those with data vs those with no metric value
    valid   = plot_df[plot_df["_class"].notna()].copy()
    no_data = plot_df[plot_df["_class"].isna()].copy()
    valid["_class"] = valid["_class"].astype(float)

    if valid.empty:
        return make_empty_fig("All counties missing data for this metric.")

    # Gray "No data" layer rendered first (behind colored counties)
    traces = []
    if not no_data.empty:
        traces.append(go.Choroplethmapbox(
            geojson=geojson,
            locations=no_data["GEOID"],
            featureidkey="properties.GEOID",
            z=[0] * len(no_data),
            colorscale=[[0, "#6b7280"], [1, "#6b7280"]],
            zmin=0,
            zmax=1,
            marker_opacity=0.65,
            marker_line_width=0.3,
            marker_line_color="rgba(255,255,255,0.15)",
            text=no_data["_label"],
            hoverinfo="text",
            customdata=no_data["GEOID"].values,
            showscale=False,
            name="No data",
        ))

    traces.append(go.Choroplethmapbox(
        geojson=geojson,
        locations=valid["GEOID"],
        featureidkey="properties.GEOID",
        z=valid["_class"],
        colorscale=cs,
        zmin=1,
        zmax=k,
        marker_opacity=0.80,
        marker_line_width=0.3,
        marker_line_color="rgba(255,255,255,0.15)",
        text=valid["_label"],
        hoverinfo="text",
        customdata=valid["GEOID"].values,
        showscale=True,
        colorbar=dict(
            title=dict(text=f"Class<br>(1–{k})", font=dict(size=11, color=_TEXT_COLOR)),
            tickvals=list(range(1, k + 1)),
            ticktext=[f"C{i}" for i in range(1, k + 1)],
            bgcolor="rgba(30,33,48,0.85)",
            outlinewidth=0,
            thickness=12,
            len=0.6,
            x=1.01,
            tickfont=dict(color=_TEXT_COLOR, size=10),
        ),
        name=label,
    ))

    fig = go.Figure(traces)

    # Overlay selected counties with strong orange border
    if sel_set:
        sel_df = valid[valid["GEOID"].isin(sel_set)]
        if not sel_df.empty:
            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson,
                locations=sel_df["GEOID"],
                featureidkey="properties.GEOID",
                z=sel_df["_class"],
                colorscale=cs,
                zmin=1,
                zmax=k,
                marker_opacity=1.0,
                marker_line_width=3.5,
                marker_line_color="#f4a261",
                text=sel_df["_label"],
                hoverinfo="text",
                showscale=False,
            ))

    _center = center or {"lat": 38.5, "lon": -96.0}
    fig.update_layout(
        **_base_layout(
            mapbox_style=_MAPBOX_STYLE,
            mapbox_zoom=zoom,
            mapbox_center=_center,
            margin=dict(l=0, r=0, t=0, b=0),
            uirevision="map",
        )
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Choropleth map – H3 hex mode
# ══════════════════════════════════════════════════════════════════════════════

def make_hex_map(
    hex_geojson: dict,
    hex_df: pd.DataFrame,
    metric: str,
    result: ClassifyResult,
    center: dict | None = None,
    zoom: float = 3.0,
) -> go.Figure:
    """H3 hex choropleth coloured by mean metric value per hex."""
    if hex_df.empty or not hex_geojson.get("features"):
        return make_empty_fig("No hex data (h3 library may not be installed).")

    label   = METRICS.get(metric, {}).get("label", metric)
    cs_name = _colorscale_for_metric(metric)
    k       = result.k
    cs      = discrete_colorscale(k, cs_name)

    # Classify hex values using the same breaks from the county classification
    import numpy as _np
    bins = _np.array(result.bins)
    def _cls(v):
        idx = int(_np.searchsorted(bins, v, side="right"))
        return min(idx + 1, k)

    hex_df = hex_df.copy()
    hex_df["_class"] = hex_df["value"].apply(_cls).astype(float)
    hex_df["_label"] = hex_df.apply(
        lambda r: f"<b>H3 Hex</b><br>Mean {label}: {r['value']:,.3f}"
                  f"<br>Counties aggregated: {r['count']}",
        axis=1,
    )

    fig = go.Figure(go.Choroplethmapbox(
        geojson=hex_geojson,
        locations=hex_df["h3_index"],
        featureidkey="properties.h3_index",
        z=hex_df["_class"],
        colorscale=cs,
        zmin=1,
        zmax=k,
        marker_opacity=0.78,
        marker_line_width=0.5,
        marker_line_color="rgba(255,255,255,0.2)",
        text=hex_df["_label"],
        hoverinfo="text",
        showscale=True,
        colorbar=dict(
            title=dict(text=f"Class<br>(1–{k})", font=dict(size=11, color=_TEXT_COLOR)),
            tickvals=list(range(1, k + 1)),
            ticktext=[f"C{i}" for i in range(1, k + 1)],
            bgcolor="rgba(30,33,48,0.85)",
            outlinewidth=0,
            thickness=12,
            len=0.6,
            x=1.01,
            tickfont=dict(color=_TEXT_COLOR, size=10),
        ),
    ))

    _center = center or {"lat": 38.5, "lon": -96.0}
    fig.update_layout(
        **_base_layout(
            mapbox_style=_MAPBOX_STYLE,
            mapbox_zoom=zoom,
            mapbox_center=_center,
            margin=dict(l=0, r=0, t=0, b=0),
            uirevision="hex-map",
        )
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Histogram with class-break lines
# ══════════════════════════════════════════════════════════════════════════════

def make_histogram(
    df: pd.DataFrame,
    metric: str,
    result: ClassifyResult,
) -> go.Figure:
    """Distribution histogram with vertical lines marking class breaks."""
    series = df[metric].dropna() if metric in df.columns else pd.Series([], dtype=float)
    label  = METRICS.get(metric, {}).get("label", metric)
    unit   = METRICS.get(metric, {}).get("unit", "")

    if series.empty:
        return make_empty_fig("No data for histogram.")

    cs_name = _colorscale_for_metric(metric)
    k       = result.k
    colors  = pc.sample_colorscale(cs_name, [i / max(k - 1, 1) for i in range(k)])

    fig = go.Figure()

    # Histogram bars coloured by class
    bins_arr = np.array(result.breaks)
    for i in range(k):
        lo = bins_arr[i]
        hi = bins_arr[i + 1]
        mask = (series >= lo) & (series <= hi)
        if i < k - 1:
            mask = (series >= lo) & (series < hi)
        sub = series[mask]
        if sub.empty:
            continue
        fig.add_trace(go.Histogram(
            x=sub,
            name=f"Class {i+1}",
            marker_color=colors[i],
            opacity=0.85,
            showlegend=False,
            xbins=dict(start=lo, end=hi, size=(hi - lo) / max(10, 1)),
            hovertemplate=f"Class {i+1}<br>Count: %{{y}}<extra></extra>",
        ))

    # Class break lines
    interior_breaks = result.breaks[1:-1]
    for b in interior_breaks:
        fig.add_vline(
            x=b,
            line_width=1.5,
            line_dash="dash",
            line_color="rgba(255,255,255,0.6)",
            annotation_text=f"{b:,.2f}",
            annotation_position="top",
            annotation_font=dict(size=9, color="rgba(255,255,255,0.7)"),
        )

    fig.update_layout(
        **_base_layout(
            margin=dict(l=40, r=12, t=12, b=40),
            xaxis=dict(
                title=dict(text=unit or label, font=dict(size=10)),
                gridcolor=_GRID_COLOR,
                zeroline=False,
                color=_TEXT_COLOR,
                tickfont=dict(size=9),
            ),
            yaxis=dict(
                title=dict(text="Count", font=dict(size=10)),
                gridcolor=_GRID_COLOR,
                zeroline=False,
                color=_TEXT_COLOR,
                tickfont=dict(size=9),
            ),
            bargap=0.02,
            barmode="overlay",
            showlegend=False,
        )
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Scatter plot
# ══════════════════════════════════════════════════════════════════════════════

def make_scatter(
    df: pd.DataFrame,
    x_metric: str,
    y_metric: str,
    selected_geoids: list[str] | None = None,
) -> go.Figure:
    """Bivariate scatter; selected counties highlighted in a contrasting colour."""
    cols_needed = ["GEOID", "State", "County", x_metric, y_metric]
    cols_present = [c for c in cols_needed if c in df.columns]
    plot_df = df[cols_present].dropna(subset=[c for c in [x_metric, y_metric] if c in df.columns])

    if plot_df.empty:
        return make_empty_fig("Not enough data for scatter.")

    x_label = METRICS.get(x_metric, {}).get("label", x_metric)
    y_label = METRICS.get(y_metric, {}).get("label", y_metric)
    sel_set = set(selected_geoids or [])

    def _county_label(r):
        return f"{r.get('County', r.get('NAME', ''))}, {r.get('State', '')}"

    unsel = plot_df[~plot_df["GEOID"].isin(sel_set)]
    sel   = plot_df[plot_df["GEOID"].isin(sel_set)]

    fig = go.Figure()

    # Background dots — very faded when a selection exists, normal otherwise
    if sel_set:
        dot_color = "rgba(140,150,170,0.12)"
        dot_size  = 4
    else:
        dot_color = "rgba(99,110,250,0.50)"
        dot_size  = 5

    fig.add_trace(go.Scatter(
        x=unsel[x_metric] if x_metric in unsel.columns else [],
        y=unsel[y_metric] if y_metric in unsel.columns else [],
        mode="markers",
        marker=dict(color=dot_color, size=dot_size, line=dict(width=0)),
        name="All Counties",
        text=unsel.apply(_county_label, axis=1) if not unsel.empty else [],
        customdata=unsel[["GEOID"]].values if not unsel.empty else [],
        hovertemplate=(
            "<b>%{text}</b><br>"
            f"{x_label}: %{{x:.3f}}<br>"
            f"{y_label}: %{{y:.3f}}<extra></extra>"
        ),
        selected=dict(marker=dict(color="#f4a261", size=9, opacity=1)),
        unselected=dict(marker=dict(opacity=0.12)),
    ))

    # Selected — bold orange dots + county name labels (shown when ≤ 30 selected)
    if not sel.empty:
        show_labels = len(sel) <= 30
        sel_labels  = sel.apply(_county_label, axis=1) if show_labels else sel.apply(lambda r: "", axis=1)
        fig.add_trace(go.Scatter(
            x=sel[x_metric],
            y=sel[y_metric],
            mode="markers+text" if show_labels else "markers",
            marker=dict(
                color="#f4a261",
                size=12,
                line=dict(width=2, color="#ffffff"),
                symbol="circle",
            ),
            name="Selected",
            text=sel_labels,
            textposition="top center",
            textfont=dict(size=9, color="#f4a261"),
            customdata=sel[["GEOID"]].values,
            hovertemplate=(
                "<b>%{text}</b> ✓<br>"
                f"{x_label}: %{{x:.3f}}<br>"
                f"{y_label}: %{{y:.3f}}<extra></extra>"
            ),
        ))

    x_short = METRICS.get(x_metric, {}).get("short_label", x_label)
    y_short = METRICS.get(y_metric, {}).get("short_label", y_label)

    fig.update_layout(
        **_base_layout(
            margin=dict(l=48, r=12, t=12, b=48),
            xaxis=dict(
                title=dict(text=x_short, font=dict(size=10)),
                gridcolor=_GRID_COLOR, zeroline=False, color=_TEXT_COLOR,
                tickfont=dict(size=9),
            ),
            yaxis=dict(
                title=dict(text=y_short, font=dict(size=10)),
                gridcolor=_GRID_COLOR, zeroline=False, color=_TEXT_COLOR,
                tickfont=dict(size=9),
            ),
            legend=dict(
                font=dict(size=10, color=_TEXT_COLOR),
                bgcolor="rgba(22,27,39,0.85)",
                bordercolor=_GRID_COLOR,
                borderwidth=1,
                x=0.01, y=0.99,
                xanchor="left", yanchor="top",
            ),
            dragmode="lasso",
            uirevision="scatter",
        )
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Parallel coordinates
# ══════════════════════════════════════════════════════════════════════════════

def make_parcoords(
    df: pd.DataFrame,
    selected_geoids: list[str] | None = None,
) -> go.Figure:
    """
    Parallel coordinates for PARCOORDS_METRICS.
    Selected counties → bright blue; unselected → faded grey.
    """
    # Filter to metrics present in df
    avail_metrics = [m for m in PARCOORDS_METRICS if m in df.columns]
    if not avail_metrics:
        return make_empty_fig("No metrics available for parallel coordinates.")

    plot_df = df[["GEOID"] + avail_metrics].dropna(subset=avail_metrics[:1])

    if plot_df.empty:
        return make_empty_fig("No data for parallel coordinates.")

    sel_set = set(selected_geoids or [])
    has_sel = bool(sel_set)

    # full_df keeps the complete dataset so axis ranges are always consistent
    full_df = plot_df.copy()

    _BG_SAMPLE = 400   # max background lines — keeps render fast

    if has_sel:
        # Draw ONLY the selected counties so they're clearly visible.
        plot_df = full_df[full_df["GEOID"].isin(sel_set)].copy()
        if plot_df.empty:
            plot_df = full_df.sample(min(_BG_SAMPLE, len(full_df)), random_state=42)
        line_color  = "#4cc9f0"
        colorscale  = [[0.0, "#4cc9f0"], [1.0, "#4cc9f0"]]
        cmin, cmax  = 0.0, 1.0
        line_vals   = [1.0] * len(plot_df)
    else:
        # Sample for performance — 400 lines is representative and renders fast
        if len(full_df) > _BG_SAMPLE:
            plot_df = full_df.sample(_BG_SAMPLE, random_state=42)
        line_color  = "rgba(99,110,250,0.25)"
        colorscale  = [[0.0, "rgba(99,110,250,0.25)"], [1.0, "rgba(99,110,250,0.25)"]]
        cmin, cmax  = 0.0, 1.0
        line_vals   = [0.5] * len(plot_df)

    dimensions = []
    for m in avail_metrics:
        dimensions.append(dict(
            label=METRICS.get(m, {}).get("short_label", m),
            values=plot_df[m].tolist(),
            # Always use the FULL dataset range so axes are scaled consistently
            range=[float(full_df[m].min()), float(full_df[m].max())],
        ))

    fig = go.Figure(go.Parcoords(
        line=dict(
            color=line_vals,
            colorscale=colorscale,
            cmin=cmin,
            cmax=cmax,
            showscale=False,
        ),
        dimensions=dimensions,
        labelangle=0,
        labelfont=dict(size=11, color=_TEXT_COLOR),
        tickfont=dict(size=8, color="rgba(200,210,220,0.7)"),
        rangefont=dict(size=8, color="rgba(200,210,220,0.5)"),
    ))

    fig.update_layout(
        **_base_layout(
            margin=dict(l=100, r=100, t=50, b=40),
        )
    )
    return fig
