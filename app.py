"""
app.py
======
Entry point for the County Health Disparities Explorer.

Run:
    python app.py

Then open  http://127.0.0.1:8050/  in your browser.
"""

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
    H3_RESOLUTION, PARCOORDS_METRICS,
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


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update map  (fires on metric / method / k / mode / state / selection)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("map-plot",       "figure"),
    Output("map-title",      "children"),
    Output("map-mode-badge", "children"),
    Input("metric-dropdown",  "value"),
    Input("method-dropdown",  "value"),
    Input("k-slider",         "value"),
    Input("map-mode-radio",   "value"),
    Input("state-dropdown",   "value"),
    Input("selection-store",  "data"),
)
def update_map(metric, method, k, map_mode, state, selected_geoids):
    if _data.load_error():
        return _figs.make_empty_fig("Run  python scripts/preprocess.py  first."), "No data", ""

    metric = metric or DEFAULT_METRIC
    method = method or DEFAULT_METHOD
    k      = k or DEFAULT_K

    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    result      = _classify_filtered(df_filtered, metric, method, k)

    label      = METRICS.get(metric, {}).get("label", metric)
    mode_label = "H3 Hex View" if map_mode == "hex" else "County Choropleth"

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

    return map_fig, label, mode_label


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update histogram  (selection-independent — only metric/method/k/state)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("histogram-plot", "figure"),
    Input("metric-dropdown", "value"),
    Input("method-dropdown", "value"),
    Input("k-slider",        "value"),
    Input("state-dropdown",  "value"),
)
def update_histogram(metric, method, k, state):
    if _data.load_error():
        return _figs.make_empty_fig("Run  python scripts/preprocess.py  first.")

    metric = metric or DEFAULT_METRIC
    method = method or DEFAULT_METHOD
    k      = k or DEFAULT_K

    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    result      = _classify_filtered(df_filtered, metric, method, k)
    return _figs.make_histogram(df_filtered, metric, result)


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update parcoords  (metric-independent — only state / selection)
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("parcoords-plot", "figure"),
    Input("state-dropdown",  "value"),
    Input("selection-store", "data"),
)
def update_parcoords(state, selected_geoids):
    if _data.load_error():
        return _figs.make_empty_fig("Run  python scripts/preprocess.py  first.")

    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    return _figs.make_parcoords(df_filtered, selected_geoids or [])


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update scatter
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("scatter-plot", "figure"),
    Input("scatter-x-dropdown", "value"),
    Input("scatter-y-dropdown", "value"),
    Input("state-dropdown",     "value"),
    Input("selection-store",    "data"),
)
def update_scatter(x_metric, y_metric, state, selected_geoids):
    if _data.load_error():
        return _figs.make_empty_fig("Run preprocessing first.")
    df_filtered = _data.filter_by_state(_data.COUNTIES, state)
    return _figs.make_scatter(df_filtered, x_metric, y_metric, selected_geoids or [])


# ══════════════════════════════════════════════════════════════════════════════
# Callback: update selection store
# ══════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("selection-store", "data"),
    Input("reset-btn",    "n_clicks"),
    Input("scatter-plot", "selectedData"),
    Input("map-plot",     "clickData"),
    State("selection-store", "data"),
    prevent_initial_call=True,
)
def update_selection(reset_clicks, scatter_sel, map_click, current_sel):
    triggered = ctx.triggered_id

    if triggered == "reset-btn":
        return []

    if triggered == "scatter-plot":
        if scatter_sel and scatter_sel.get("points"):
            return [
                p["customdata"][0]
                for p in scatter_sel["points"]
                if p.get("customdata") and len(p["customdata"]) > 0
            ]
        return []

    if triggered == "map-plot":
        if map_click and map_click.get("points"):
            pt    = map_click["points"][0]
            geoid = pt.get("location") or (pt.get("customdata") or [None])[0]
            if geoid:
                current = list(current_sel or [])
                if geoid in current:
                    current.remove(geoid)   # toggle off
                else:
                    current.append(geoid)   # toggle on
                return current
        return current_sel or []

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

    names = []
    for _, row in df_sel.iterrows():
        county = row.get(name_col, "")
        st     = row.get(state_col, "") if state_col else ""
        names.append(f"{county}, {st}" if st else county)

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
        if pd.isna(val):
            val_str = "No data"
            color   = "text-muted"
        else:
            val_str = f"{val:,.3f}"
            color   = ""
        items.append(
            html.Div(className="detail-row", children=[
                html.Span(cfg["label"], className="detail-label text-muted"),
                html.Span(val_str, className=f"detail-value {color}"),
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
# Run
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
