"""
src/layout.py
=============
Dash layout factories for the home page (/) and the visualization page (/viz).
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.config import (
    APP_TITLE,
    APP_SUBTITLE,
    METRICS,
    CLASSIFICATION_METHODS,
    DEFAULT_METRIC,
    DEFAULT_METHOD,
    DEFAULT_K,
    DEFAULT_X,
    DEFAULT_Y,
)
from src import data as _data


# ── Helper ────────────────────────────────────────────────────────────────────

def _metric_options() -> list[dict]:
    return [{"label": cfg["label"], "value": key} for key, cfg in METRICS.items()]


def _state_options() -> list[dict]:
    opts = [{"label": "All States", "value": "All"}]
    opts += [{"label": s, "value": s} for s in _data.STATES]
    return opts


# ══════════════════════════════════════════════════════════════════════════════
# Home page
# ══════════════════════════════════════════════════════════════════════════════

def home_layout() -> html.Div:
    return html.Div(
        className="home-page",
        children=[
            # ── Nav bar ──────────────────────────────────────────────────────
            dbc.Navbar(
                dbc.Container([
                    html.A(
                        dbc.Row([
                            dbc.Col(html.I(className="bi bi-heart-pulse-fill me-2 text-danger")),
                            dbc.Col(dbc.NavbarBrand(APP_TITLE, className="ms-0 fw-bold")),
                        ], align="center"),
                        href="/",
                        style={"textDecoration": "none"},
                    ),
                    dbc.Nav([
                        dbc.NavItem(dbc.NavLink("Dashboard", href="/viz", className="fw-semibold")),
                    ], className="ms-auto", navbar=True),
                ], fluid=True),
                color="dark",
                dark=True,
                className="border-bottom border-secondary",
            ),

            # ── Hero section ─────────────────────────────────────────────────
            html.Div(className="hero-section", children=[
                html.Div(className="hero-content text-center", children=[
                    html.Div(className="hero-badge mb-3", children=[
                        html.Span("CS 544 · Advanced Data Visualization · Spring 2025",
                                  className="badge-text"),
                    ]),
                    html.H1(APP_TITLE, className="hero-title mb-3"),
                    html.P(
                        "Explore county-level health disparities across the United States using "
                        "coordinated multiple views, four classification schemes, and an "
                        "equal-area hex view to mitigate area-size bias.",
                        className="hero-subtitle mb-4",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-bar-chart-line-fill me-2"),
                         "Open Visualization"],
                        href="/viz",
                        color="primary",
                        size="lg",
                        className="hero-btn px-5 py-3",
                    ),
                ]),
            ]),

            # ── Feature cards ─────────────────────────────────────────────────
            dbc.Container(fluid=True, className="py-5 feature-section", children=[
                html.H2("Key Features", className="text-center fw-bold mb-4"),
                dbc.Row([
                    _feature_card("bi-map-fill",      "Choropleth Map",
                        "County-level choropleth with 4 classification methods: "
                        "Quantile, Equal Interval, Natural Breaks (Jenks), and Std. Mean."),
                    _feature_card("bi-bar-chart-fill", "Distribution Context",
                        "Histogram shows the full metric distribution with class-break "
                        "lines overlaid—so you see exactly what each colour class covers."),
                    _feature_card("bi-scatter-chart",  "Linked Scatter Plot",
                        "Bivariate scatter with lasso/box selection. Selected counties "
                        "highlight across all views simultaneously."),
                    _feature_card("bi-list-columns",   "Parallel Coordinates",
                        "Compare 7 health and socioeconomic variables side by side. "
                        "Selected counties are highlighted in blue."),
                    _feature_card("bi-hexagon-fill",   "Equal-Area Hex View",
                        "Toggle to an H3 hex aggregation that gives equal screen area "
                        "to every hex, mitigating the large-county visual bias."),
                    _feature_card("bi-link-45deg",     "Coordinated Views",
                        "A shared selection store links map, scatter, histogram, and "
                        "parallel coordinates—brush in one, highlight in all."),
                ], className="g-4 justify-content-center"),
            ]),

            # ── Dataset note ──────────────────────────────────────────────────
            dbc.Container(className="pb-5", children=[
                dbc.Card(dbc.CardBody([
                    html.H5("Dataset", className="fw-bold mb-2"),
                    html.P([
                        "2025 County Health Rankings (University of Wisconsin Population "
                        "Health Institute) · Census TIGER/Line 2025 county boundaries · "
                        "7 metrics covering health outcomes and social determinants."
                    ], className="mb-0 text-muted small"),
                ]), className="border-secondary bg-dark"),
            ]),

            # ── Footer ────────────────────────────────────────────────────────
            html.Footer(className="footer text-center py-3 border-top border-secondary", children=[
                html.Small(f"{APP_SUBTITLE}", className="text-muted"),
            ]),
        ],
    )


def _feature_card(icon: str, title: str, body: str) -> dbc.Col:
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.I(className=f"bi {icon} feature-icon mb-2"),
                html.H6(title, className="fw-bold mb-2"),
                html.P(body, className="text-muted small mb-0"),
            ], className="text-center p-3"),
        ], className="feature-card h-100"),
        xs=12, sm=6, md=4,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Viz page  (/viz)
# ══════════════════════════════════════════════════════════════════════════════

def viz_layout() -> html.Div:
    return html.Div(className="viz-page", children=[

        # Shared state stores
        dcc.Store(id="selection-store", data=[]),
        dcc.Store(id="hover-store",     data=None),

        # ── Top bar ───────────────────────────────────────────────────────────
        dbc.Navbar(
            dbc.Container([
                html.A(
                    dbc.Row([
                        dbc.Col(html.I(className="bi bi-heart-pulse-fill me-2 text-danger")),
                        dbc.Col(dbc.NavbarBrand(APP_TITLE, className="ms-0 fw-bold")),
                    ], align="center"),
                    href="/",
                    style={"textDecoration": "none"},
                ),
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink(
                        [html.I(className="bi bi-house-fill me-1"), "Home"],
                        href="/",
                    )),
                ], className="ms-auto", navbar=True),
            ], fluid=True),
            color="dark",
            dark=True,
            className="border-bottom border-secondary",
        ),

        # ── Main layout: sidebar + center + right ────────────────────────────
        dbc.Container(fluid=True, className="viz-container py-2", children=[
            dbc.Row([

                # ── LEFT: Controls ────────────────────────────────────────────
                dbc.Col(width=2, className="sidebar pe-0", children=[
                    html.Div(className="sidebar-inner", children=[
                        html.H6("CONTROLS", className="sidebar-section-title"),

                        # Metric
                        html.Label("Health Metric", className="ctrl-label"),
                        dcc.Dropdown(
                            id="metric-dropdown",
                            options=_metric_options(),
                            value=DEFAULT_METRIC,
                            clearable=False,
                            className="dash-dropdown mb-3",
                        ),

                        # Classification method
                        html.Label("Classification Method", className="ctrl-label"),
                        dcc.Dropdown(
                            id="method-dropdown",
                            options=[{"label": v, "value": k}
                                     for k, v in CLASSIFICATION_METHODS.items()],
                            value=DEFAULT_METHOD,
                            clearable=False,
                            className="dash-dropdown mb-3",
                        ),

                        # Number of classes k
                        html.Label("Number of Classes (k)", className="ctrl-label"),
                        dcc.Slider(
                            id="k-slider",
                            min=3, max=9, step=1, value=DEFAULT_K,
                            marks={i: str(i) for i in range(3, 10)},
                            className="mb-3",
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),

                        # Map mode toggle
                        html.Label("Map Mode", className="ctrl-label"),
                        dbc.RadioItems(
                            id="map-mode-radio",
                            options=[
                                {"label": "County Choropleth", "value": "county"},
                                {"label": "H3 Hex View",       "value": "hex"},
                            ],
                            value="county",
                            className="mb-3",
                            inputClassName="me-1",
                        ),

                        # State filter
                        html.Label("State Filter", className="ctrl-label"),
                        dcc.Dropdown(
                            id="state-dropdown",
                            options=_state_options(),
                            value="All",
                            clearable=False,
                            className="dash-dropdown mb-3",
                        ),

                        html.Hr(className="divider"),

                        # Scatter axis selectors
                        html.H6("SCATTER AXES", className="sidebar-section-title"),
                        html.Label("X Axis", className="ctrl-label"),
                        dcc.Dropdown(
                            id="scatter-x-dropdown",
                            options=_metric_options(),
                            value=DEFAULT_X,
                            clearable=False,
                            className="dash-dropdown mb-2",
                        ),
                        html.Label("Y Axis", className="ctrl-label"),
                        dcc.Dropdown(
                            id="scatter-y-dropdown",
                            options=_metric_options(),
                            value=DEFAULT_Y,
                            clearable=False,
                            className="dash-dropdown mb-3",
                        ),

                        html.Hr(className="divider"),

                        # Reset button
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-1"), "Reset Selection"],
                            id="reset-btn",
                            color="secondary",
                            outline=True,
                            size="sm",
                            className="w-100 mb-2",
                            n_clicks=0,
                        ),

                        # Selection info badge
                        html.Div(id="selection-info", className="selection-info"),
                    ]),
                ]),

                # ── MAIN: stacked rows ────────────────────────────────────────
                dbc.Col(width=10, className="px-2 main-col", children=[

                    # ── ROW 1: Map ────────────────────────────────────────────
                    html.Div(className="panel map-panel mb-2", children=[
                        html.Div(className="panel-header d-flex align-items-center", children=[
                            html.I(className="bi bi-map me-2 text-primary"),
                            html.Span(id="map-title", className="panel-title fw-semibold"),
                            dbc.Badge(id="map-mode-badge", color="info", className="ms-2 badge-sm"),
                        ]),
                        dcc.Loading(
                            type="circle",
                            color="#4cc9f0",
                            children=dcc.Graph(
                                id="map-plot",
                                config={
                                    "displayModeBar": True,
                                    "displaylogo": False,
                                    "modeBarButtonsToRemove": ["select2d"],
                                    "scrollZoom": True,
                                },
                                style={"height": "440px"},
                            ),
                        ),
                    ]),

                    # Details strip
                    html.Div(className="panel details-panel mb-2", children=[
                        html.Div(className="panel-header", children=[
                            html.I(className="bi bi-info-circle me-2 text-info"),
                            html.Span("County Details — hover map or scatter to inspect", className="panel-title"),
                        ]),
                        html.Div(id="details-panel", className="details-content"),
                    ]),

                    # ── ROW 2: Scatter + Histogram ────────────────────────────
                    dbc.Row([
                        dbc.Col(width=7, children=[
                            html.Div(className="panel bottom-panel", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-scatter-chart me-2 text-warning"),
                                    html.Span("Scatter Plot", className="panel-title"),
                                    html.Small(" — lasso / box-select to highlight counties", className="text-muted ms-2"),
                                ]),
                                dcc.Loading(type="dot", color="#4cc9f0", children=
                                    dcc.Graph(
                                        id="scatter-plot",
                                        config={
                                            "displayModeBar": True,
                                            "displaylogo": False,
                                            "modeBarButtonsToRemove": [
                                                "zoom2d", "pan2d", "zoomIn2d",
                                                "zoomOut2d", "autoScale2d", "resetScale2d",
                                            ],
                                        },
                                        style={"height": "340px"},
                                    )
                                ),
                            ]),
                        ]),
                        dbc.Col(width=5, children=[
                            html.Div(className="panel bottom-panel", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-bar-chart-fill me-2 text-success"),
                                    html.Span("Distribution", className="panel-title"),
                                    html.Small(" — class breaks overlaid", className="text-muted ms-2"),
                                ]),
                                dcc.Loading(type="dot", color="#4cc9f0", children=
                                    dcc.Graph(
                                        id="histogram-plot",
                                        config={"displayModeBar": False},
                                        style={"height": "340px"},
                                    )
                                ),
                            ]),
                        ]),
                    ], className="g-2 mb-2"),

                    # ── ROW 3: Parallel Coordinates ───────────────────────────
                    dbc.Row([
                        dbc.Col(width=12, children=[
                            html.Div(className="panel bottom-panel", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-list-columns me-2 text-info"),
                                    html.Span("Parallel Coordinates", className="panel-title"),
                                    html.Small(" — all 7 health metrics · selected counties in blue", className="text-muted ms-2"),
                                ]),
                                dcc.Loading(type="dot", color="#4cc9f0", children=
                                    dcc.Graph(
                                        id="parcoords-plot",
                                        config={"displayModeBar": False},
                                        style={"height": "300px"},
                                    )
                                ),
                                html.Div(id="parcoords-county-label", className="parcoords-county-label"),
                            ]),
                        ]),
                    ], className="g-2"),

                ]),

            ], className="g-0"),
        ]),
    ])
