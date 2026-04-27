"""
app.py
======
Entry point for the County Health Disparities Explorer.

Run:
    python app.py

Then open  http://127.0.0.1:8050/  in your browser.
"""

import re
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, no_update, dcc, html
import pandas as pd
import numpy as np

from src import data as _data
from src.config import (
    METRICS, DEFAULT_METRIC, DEFAULT_K, DEFAULT_METHOD,
    H3_RESOLUTION, PARCOORDS_METRICS, DEFAULT_Y,
)
from src import classify as _cls
from src import h3hex  as _hex
from src import figures as _figs
from src import layout  as _layout

# ── App setup ─────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="County Health Explorer",
)
server = app.server   # for WSGI deployment

# ── Root layout with routing ──────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
])


# ══════════════════════════════════════════════════════════════════════════════
# Page routing
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname: str):
    err = _data.load_error()
    if err and pathname == "/viz":
        return dbc.Container([
            dbc.Alert(
                [html.H4("Data not loaded", className="alert-heading"),
                 html.P("Run the preprocessing script first:"),
                 html.Code("python scripts/preprocess.py"),
                 html.Hr(),
                 html.P(err, className="mb-0 small")],
                color="danger",
                className="mt-5",
            )
        ])
    if pathname == "/viz":
        return _layout.viz_layout()
    return _layout.home_layout()


# ══════════════════════════════════════════════════════════════════════════════
# Helper: classify filtered data
# ══════════════════════════════════════════════════════════════════════════════

def _classify_filtered(df: pd.DataFrame, metric: str, method: str, k: int) -> _cls.ClassifyResult:
    series = df[metric] if metric in df.columns else pd.Series([], dtype=float)
    return _cls.classify(series, method, k)


def _geoids_from_constraints(constraints: dict, df: pd.DataFrame) -> list:
    """Return GEOIDs from df whose values satisfy all active parcoords axis constraints.

    constraints: {dim_idx_str: [[lo, hi], ...]}  — accumulated from restyleData events.
    Dimension indices map positionally to PARCOORDS_METRICS order.
    """
    if not constraints or df.empty:
        return []

    avail_metrics = [m for m in PARCOORDS_METRICS if m in df.columns]
    mask = pd.Series(True, index=df.index)

    for dim_idx_str, ranges in constraints.items():
        dim_idx = int(dim_idx_str)
        if dim_idx >= len(avail_metrics):
            continue
        col = avail_metrics[dim_idx]
        if col not in df.columns:
            continue
        # ranges may be [[lo, hi]] or [lo, hi]; normalise to list-of-lists
        if ranges and not isinstance(ranges[0], (list, tuple)):
            ranges = [ranges]
        col_mask = pd.Series(False, index=df.index)
        for (lo, hi) in ranges:
            col_mask |= (df[col] >= lo) & (df[col] <= hi)
        mask &= col_mask

    return df[mask]["GEOID"].astype(str).tolist()


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update map  (fires on metric / method / k / mode / state / selection)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("map-plot",          "figure"),
    Output("map-title",         "children"),
    Output("map-mode-badge",    "children"),
    Output("map-county-count",  "children"),
    Input("metric-dropdown",  "value"),
    Input("method-dropdown",  "value"),
    Input("k-slider",         "value"),
    Input("map-mode-radio",   "value"),
    Input("state-dropdown",   "value"),
    Input("selection-store",  "data"),
)
def update_map(metric, method, k, map_mode, state, selected_geoids):
    if _data.load_error():
        return _figs.make_empty_fig("Run  python scripts/preprocess.py  first."), "No data", "", ""

    metric = metric or DEFAULT_METRIC
    method = method or DEFAULT_METHOD
    k      = k or DEFAULT_K

    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    result      = _classify_filtered(df_filtered, metric, method, k)

    label      = METRICS.get(metric, {}).get("label", metric)
    mode_label = "Tile Cartogram (H3)" if map_mode == "hex" else "County Choropleth"

    geoid_set    = set(df_filtered["GEOID"].astype(str))
    filt_geojson = _data.filter_geojson(_data.GEOJSON, geoid_set)

    if map_mode == "hex":
        hex_geojson, hex_df = _hex.build_hex_layer(
            df_filtered, filt_geojson, metric, H3_RESOLUTION
        )
        map_fig = _figs.make_hex_map(hex_geojson, hex_df, metric, result)
    else:
        map_fig = _figs.make_choropleth(
            df_filtered, filt_geojson, metric, result,
            selected_geoids=selected_geoids or [],
        )

    n_sel   = len(selected_geoids or [])
    n_total = len(df_filtered)
    if n_sel:
        count_text = f"{n_sel} selected / {n_total} counties"
    else:
        count_text = f"{n_total} counties"
    return map_fig, label, mode_label, count_text


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update histogram  (selection-independent — only metric/method/k/state)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("histogram-plot", "figure"),
    Input("metric-dropdown",  "value"),
    Input("method-dropdown",  "value"),
    Input("k-slider",         "value"),
    Input("state-dropdown",   "value"),
    Input("selection-store",  "data"),
)
def update_histogram(metric, method, k, state, selected_geoids):
    if _data.load_error():
        return _figs.make_empty_fig("Run  python scripts/preprocess.py  first.")

    metric = metric or DEFAULT_METRIC
    method = method or DEFAULT_METHOD
    k      = k or DEFAULT_K

    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    result      = _classify_filtered(df_filtered, metric, method, k)
    return _figs.make_histogram(df_filtered, metric, result, selected_geoids or [])


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update parcoords  (metric-independent — only state / selection)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("parcoords-plot",  "figure"),
    Input("state-dropdown",   "value"),
    Input("selection-store",  "data"),
    Input("metric-dropdown",  "value"),
)
def update_parcoords(state, selected_geoids, metric):
    if _data.load_error():
        return _figs.make_empty_fig("Run  python scripts/preprocess.py  first.")

    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    # uirevision key: changes only when axes/state change, NOT on selection changes.
    # This preserves the axis-brush constraint UI when the selection-store fires.
    uirev = f"pc-{state or 'All'}-{metric or DEFAULT_METRIC}"
    return _figs.make_parcoords(
        df_filtered, selected_geoids or [], metric or DEFAULT_METRIC,
        uirevision=uirev,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Callback: coordinated axes — scatter Y follows the primary metric
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("scatter-y-dropdown", "value", allow_duplicate=True),
    Input("metric-dropdown", "value"),
    prevent_initial_call=True,
)
def sync_scatter_y(metric):
    """Keep scatter Y axis coordinated with the choropleth metric."""
    return metric or DEFAULT_Y


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update scatter
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("scatter-plot",        "figure"),
    Input("scatter-x-dropdown",   "value"),
    Input("scatter-y-dropdown",   "value"),
    Input("state-dropdown",       "value"),
    Input("selection-store",      "data"),
    Input("scatter-color-state",  "value"),
    State("reset-btn",            "n_clicks"),
)
def update_scatter(x_metric, y_metric, state, selected_geoids, color_state, reset_clicks):
    if _data.load_error():
        return _figs.make_empty_fig("Run preprocessing first.")
    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    return _figs.make_scatter(
        df_filtered, x_metric, y_metric,
        selected_geoids or [],
        color_by_state=bool(color_state),
        reset_count=reset_clicks or 0,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Callback: accumulate parcoords axis constraint ranges
# ══════════════════════════════════════════════════════════════════════════════
# restyleData fires on every axis-brush interaction but only reports the
# changed dimension.  We merge each event into a running dict so that
# update_selection can see ALL active constraints at once.
# The Reset button also clears this store.

@app.callback(
    Output("parcoords-constraints-store", "data"),
    Input("parcoords-plot", "restyleData"),
    Input("reset-btn",      "n_clicks"),
    State("parcoords-constraints-store", "data"),
    prevent_initial_call=True,
)
def update_parcoords_constraints(restyle_data, reset_clicks, current_constraints):
    if ctx.triggered_id == "reset-btn":
        return {}

    if not restyle_data:
        return current_constraints or {}

    # restyleData is [changed_props_dict, [trace_indices]]
    changed = restyle_data[0] if isinstance(restyle_data, list) else restyle_data
    constraints = dict(current_constraints or {})

    for key, value in changed.items():
        m = re.match(r"dimensions\[(\d+)\]\.constraintrange", key)
        if m:
            dim_idx = m.group(1)   # keep as string for JSON Store serialisation
            if value is None:
                constraints.pop(dim_idx, None)
            else:
                constraints[dim_idx] = value

    return constraints


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update selection store
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("selection-store", "data"),
    Input("reset-btn",                    "n_clicks"),
    Input("scatter-plot",                 "selectedData"),
    Input("map-plot",                     "clickData"),
    Input("parcoords-constraints-store",  "data"),
    State("selection-store",              "data"),
    State("state-dropdown",               "value"),
    prevent_initial_call=True,
)
def update_selection(reset_clicks, scatter_sel, map_click, parcoords_constraints,
                     current_sel, state):
    triggered = ctx.triggered_id

    if triggered == "reset-btn":
        return []

    if triggered == "scatter-plot":
        if scatter_sel is None:
            # selectedData resets to None when the figure re-renders — not a user action.
            return no_update
        pts = scatter_sel.get("points") or []
        if pts:
            new_sel = [
                str(p["customdata"][0])
                for p in pts
                if p.get("customdata") and len(p["customdata"]) > 0
            ]
            if not new_sel:
                return no_update
            # Don't cascade if Plotly replayed the same selection via uirevision preservation.
            if sorted(new_sel) == sorted(str(g) for g in (current_sel or [])):
                return no_update
            return new_sel
        # Empty-points payload ({"points": []}) can arrive when Plotly resets the figure
        # due to uirevision change — treat as no-op so we don't wipe a valid selection.
        # The Reset button is the explicit control for clearing.
        return no_update

    if triggered == "map-plot":
        if map_click and map_click.get("points"):
            pt    = map_click["points"][0]
            geoid = str(pt.get("location") or (pt.get("customdata") or [None])[0] or "")
            if geoid:
                current = [str(g) for g in (current_sel or [])]
                if geoid in current:
                    current.remove(geoid)   # toggle off
                else:
                    current.append(geoid)   # toggle on
                return current
        return [str(g) for g in (current_sel or [])]

    if triggered == "parcoords-constraints-store":
        if parcoords_constraints:
            df = _data.filter_by_state(_data.COUNTIES, state or "All")
            return _geoids_from_constraints(parcoords_constraints, df)
        # All axis brushes cleared → clear selection
        return []

    return no_update


# ══════════════════════════════════════════════════════════════════════════════
# Callback: parcoords county label strip
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("parcoords-county-label", "children"),
    Input("selection-store", "data"),
    Input("state-dropdown",  "value"),
)
def update_parcoords_label(selected_geoids, state):
    sel = selected_geoids or []
    if not sel:
        return html.Small("No counties selected — use the map or scatter plot to highlight lines.",
                          className="text-muted")

    df_sel = _data.COUNTIES[_data.COUNTIES["GEOID"].isin(sel)]
    name_col  = "County" if "County" in df_sel.columns else "NAME"
    state_col = "State"  if "State"  in df_sel.columns else None

    if state_col and state_col in df_sel.columns:
        names = (df_sel[name_col].fillna("") + ", " + df_sel[state_col].fillna("")).tolist()
    else:
        names = df_sel[name_col].fillna("").tolist()

    n = len(names)
    shown = names[:10]
    chips = [
        html.Span(name, className="parcoords-county-chip")
        for name in shown
    ]
    if n > 10:
        chips.append(html.Span(f"+{n - 10} more", className="parcoords-county-chip parcoords-county-more"))

    return html.Div([
        html.Span(
            f"{'County' if n == 1 else f'{n} Counties'} shown: ",
            className="parcoords-county-heading",
        ),
        *chips,
    ])


# ══════════════════════════════════════════════════════════════════════════════
# Callback: selection info badge
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("selection-info", "children"),
    Input("selection-store", "data"),
)
def update_selection_info(selected_geoids):
    n = len(selected_geoids or [])
    if n == 0:
        return html.Small("No counties selected.", className="text-muted")
    return dbc.Badge(f"{n} county{'s' if n != 1 else ''} selected",
                     color="warning", className="w-100 text-center")


# ══════════════════════════════════════════════════════════════════════════════
# Callback: details panel (hover-driven)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("details-panel", "children"),
    Input("map-plot",     "hoverData"),
    Input("scatter-plot", "hoverData"),
    prevent_initial_call=True,
)
def update_details(map_hover, scatter_hover):
    triggered = ctx.triggered_id

    geoid = None
    if triggered == "map-plot" and map_hover:
        pts   = map_hover.get("points", [])
        if pts:
            geoid = pts[0].get("location") or (pts[0].get("customdata") or [None])[0]
    elif triggered == "scatter-plot" and scatter_hover:
        pts = scatter_hover.get("points", [])
        if pts:
            cd = pts[0].get("customdata")
            if cd and len(cd) > 0:
                geoid = cd[0]

    if not geoid:
        return html.Small("Hover over a county on the map or scatter plot.", className="text-muted")

    row = _data.COUNTIES[_data.COUNTIES["GEOID"] == str(geoid)]
    if row.empty:
        return html.Small(f"GEOID {geoid} not found.", className="text-muted")

    row = row.iloc[0]
    county_name = row.get("County") or row.get("NAME", "—")
    state_name  = row.get("State", "—")

    items = []
    for metric, cfg in METRICS.items():
        val = row.get(metric, np.nan)
        higher_is_worse = cfg.get("higher_is_worse", True)
        if pd.isna(val):
            val_str   = "No data"
            val_class = "text-muted"
        else:
            val_str  = f"{val:,.3f}"
            col_data = _data.COUNTIES[metric].dropna() if metric in _data.COUNTIES.columns else pd.Series([], dtype=float)
            if len(col_data) > 0:
                pct_rank = float((col_data < val).sum()) / len(col_data)
                if higher_is_worse:
                    val_class = "text-danger" if pct_rank >= 0.75 else ("text-success" if pct_rank <= 0.25 else "")
                else:
                    val_class = "text-danger" if pct_rank <= 0.25 else ("text-success" if pct_rank >= 0.75 else "")
            else:
                val_class = ""
        items.append(
            html.Div(className="detail-row", children=[
                html.Span(cfg["label"], className="detail-label text-muted"),
                html.Span(val_str, className=f"detail-value {val_class}".strip()),
            ])
        )

    return html.Div([
        html.Div(className="detail-county-name", children=[
            html.Strong(f"{county_name},"),
            html.Span(f" {state_name}", className="text-muted"),
            html.Small(f"  GEOID: {geoid}", className="text-muted ms-1"),
        ]),
        html.Div(items, className="detail-metrics mt-1"),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# Callback: hypothesis "Test →" buttons — load the relevant axis pair into scatter
# ══════════════════════════════════════════════════════════════════════════════

_HYP_AXES = {
    "hyp-btn-1": ("% Children in Poverty",                    "Years of Potential Life Lost Rate"),
    "hyp-btn-2": ("% Uninsured",                              "% Fair or Poor Health"),
    "hyp-btn-3": ("Average Number of Mentally Unhealthy Days", "Average Number of Physically Unhealthy Days"),
}

@app.callback(
    Output("scatter-x-dropdown", "value", allow_duplicate=True),
    Output("scatter-y-dropdown", "value", allow_duplicate=True),
    Input("hyp-btn-1", "n_clicks"),
    Input("hyp-btn-2", "n_clicks"),
    Input("hyp-btn-3", "n_clicks"),
    prevent_initial_call=True,
)
def test_hypothesis(_b1, _b2, _b3):
    triggered = ctx.triggered_id
    if triggered in _HYP_AXES:
        x, y = _HYP_AXES[triggered]
        return x, y
    return no_update, no_update


# ══════════════════════════════════════════════════════════════════════════════
# Callback: metric description tooltip
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("metric-info-tooltip", "children"),
    Input("metric-dropdown", "value"),
)
def update_metric_tooltip(metric):
    cfg = METRICS.get(metric or DEFAULT_METRIC, {})
    return cfg.get("description", "")


# ══════════════════════════════════════════════════════════════════════════════
# Callback: sidebar mini-stats (n / mean / median for active metric + filter)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("sidebar-stats", "children"),
    Input("metric-dropdown",  "value"),
    Input("state-dropdown",   "value"),
    Input("selection-store",  "data"),
)
def update_sidebar_stats(metric, state, selected_geoids):
    metric = metric or DEFAULT_METRIC
    df  = _data.filter_by_state(_data.COUNTIES, state)
    col = df[metric].dropna() if metric in df.columns else pd.Series([], dtype=float)
    if col.empty:
        return ""
    n, mean_v, med_v = len(col), col.mean(), col.median()
    fmt = lambda v: f"{v:,.2f}"

    sel = selected_geoids or []
    if sel:
        sel_col = df[df["GEOID"].isin(sel)][metric].dropna() if metric in df.columns else pd.Series([], dtype=float)
        if not sel_col.empty:
            return html.Div([
                html.Div([
                    html.Span("All  ", className="text-muted"),
                    html.Span(f"n={n} · μ={fmt(mean_v)} · med={fmt(med_v)}",
                              className="text-muted"),
                ]),
                html.Div([
                    html.Span("Sel  ", style={"color": "#fb923c"}),
                    html.Span(
                        f"n={len(sel_col)} · μ={fmt(sel_col.mean())} · med={fmt(sel_col.median())}",
                        style={"color": "#fb923c"},
                    ),
                ]),
            ], className="sidebar-stats")

    return html.Div(
        f"n={n} · μ={fmt(mean_v)} · med={fmt(med_v)}",
        className="sidebar-stats text-muted",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Callback: export selected counties as CSV
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("download-csv", "data"),
    Input("export-btn",      "n_clicks"),
    State("selection-store", "data"),
    State("state-dropdown",  "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, selected_geoids, state):
    df  = _data.filter_by_state(_data.COUNTIES, state)
    sel = selected_geoids or []
    export_df = df[df["GEOID"].isin(sel)] if sel else df
    cols      = ["GEOID", "State", "County"] + list(METRICS.keys())
    export_df = export_df[[c for c in cols if c in export_df.columns]]
    tag       = "selection" if sel else "all"
    filename  = f"health_export_{tag}_{len(export_df)}counties.csv"
    return dcc.send_data_frame(export_df.to_csv, filename, index=False)


# ══════════════════════════════════════════════════════════════════════════════
# Run
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
