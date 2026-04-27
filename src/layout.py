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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _metric_options() -> list[dict]:
    return [{"label": cfg["label"], "value": key} for key, cfg in METRICS.items()]


def _state_options() -> list[dict]:
    opts = [{"label": "All States", "value": "All"}]
    opts += [{"label": s, "value": s} for s in _data.STATES]
    return opts


def _stat_pill(number: str, label: str) -> dbc.Col:
    return dbc.Col(
        html.Div([
            html.Div(number, className="stat-number"),
            html.Div(label,  className="stat-label"),
        ], className="stat-pill"),
        width="auto",
    )


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

            # ── Stats strip ───────────────────────────────────────────────────
            dbc.Container(fluid=True, className="stats-strip py-3", children=[
                dbc.Row([
                    _stat_pill("3,144", "Counties"),
                    _stat_pill("7",     "Health Metrics"),
                    _stat_pill("4",     "Class Methods"),
                    _stat_pill("50",    "States"),
                ], className="justify-content-center g-3"),
            ]),

            # ── Feature cards ─────────────────────────────────────────────────
            dbc.Container(fluid=True, className="py-5 feature-section", children=[
                html.H2("Key Features", className="text-center fw-bold mb-4"),
                dbc.Row([
                    _feature_card("bi-map-fill",       "Choropleth Map",
                        "County-level choropleth with 4 classification methods: "
                        "Quantile, Equal Interval, Natural Breaks (Jenks), and Std. Mean.",
                        "#60a5fa", "rgba(96,165,250,0.12)"),
                    _feature_card("bi-bar-chart-fill", "Distribution Context",
                        "Histogram shows the full metric distribution with class-break "
                        "lines overlaid—so you see exactly what each colour class covers.",
                        "#34d399", "rgba(52,211,153,0.12)"),
                    _feature_card("bi-scatter-chart",  "Linked Scatter Plot",
                        "Bivariate scatter with lasso/box selection. Selected counties "
                        "highlight across all views simultaneously.",
                        "#fb923c", "rgba(251,146,60,0.12)"),
                    _feature_card("bi-list-columns",   "Parallel Coordinates",
                        "Compare 7 health and socioeconomic variables side by side. "
                        "Selected counties are highlighted in blue.",
                        "#818cf8", "rgba(129,140,248,0.12)"),
                    _feature_card("bi-hexagon-fill",   "Tile Cartogram (H3)",
                        "Each county maps to one equal-sized hex tile regardless of land "
                        "area — states with more counties occupy proportionally more tiles, "
                        "eliminating geographic area bias.",
                        "#22d3ee", "rgba(34,211,238,0.12)"),
                    _feature_card("bi-link-45deg",     "Coordinated Views",
                        "A shared selection store links map, scatter, histogram, and "
                        "parallel coordinates—brush in one, highlight in all.",
                        "#f472b6", "rgba(244,114,182,0.12)"),
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


def _feature_card(icon: str, title: str, body: str,
                  icon_color: str = "#60a5fa",
                  icon_bg:    str = "rgba(96,165,250,0.12)") -> dbc.Col:
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.I(
                    className=f"bi {icon} feature-icon mb-3",
                    style={"color": icon_color, "background": icon_bg},
                ),
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
        dcc.Store(id="selection-store",             data=[]),
        dcc.Store(id="hover-store",                 data=None),
        dcc.Store(id="parcoords-constraints-store", data={}),
        dcc.Download(id="download-csv"),

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

        # ── Main layout: sidebar + content ───────────────────────────────────
        dbc.Container(fluid=True, className="viz-container py-2", children=[
            dbc.Row([

                # ── LEFT SIDEBAR ──────────────────────────────────────────────
                dbc.Col(width=2, className="sidebar pe-0", children=[
                    html.Div(className="sidebar-inner", children=[

                        html.H6("MAP SETTINGS", className="sidebar-section-title"),

                        html.Div(className="d-flex align-items-center mb-1", children=[
                            html.Label("Health Metric", className="ctrl-label mb-0"),
                            html.I(
                                className="bi bi-info-circle ms-1 text-muted",
                                id="metric-info-icon",
                                style={"fontSize": "11px", "cursor": "help"},
                            ),
                        ]),
                        dbc.Tooltip(
                            id="metric-info-tooltip",
                            target="metric-info-icon",
                            placement="right",
                        ),
                        dcc.Dropdown(
                            id="metric-dropdown",
                            options=_metric_options(),
                            value=DEFAULT_METRIC,
                            clearable=False,
                            className="dash-dropdown mb-1",
                        ),
                        html.Div(id="sidebar-stats", className="sidebar-stats mb-3"),

                        html.Label("Classification / Color Encoding", className="ctrl-label"),
                        dcc.Dropdown(
                            id="method-dropdown",
                            options=[{"label": v, "value": k}
                                     for k, v in CLASSIFICATION_METHODS.items()],
                            value=DEFAULT_METHOD,
                            clearable=False,
                            className="dash-dropdown mb-3",
                        ),

                        html.Label("Number of Classes (k)", className="ctrl-label"),
                        dcc.Slider(
                            id="k-slider",
                            min=3, max=9, step=1, value=DEFAULT_K,
                            marks={i: str(i) for i in range(3, 10)},
                            className="mb-3",
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),

                        html.Label("Map Mode", className="ctrl-label"),
                        dbc.RadioItems(
                            id="map-mode-radio",
                            options=[
                                {"label": "County Choropleth",  "value": "county"},
                                {"label": "Tile Cartogram (H3)", "value": "hex"},
                            ],
                            value="county",
                            className="mb-3",
                            inputClassName="me-1",
                        ),

                        html.Hr(className="divider"),
                        html.H6("FILTER", className="sidebar-section-title"),

                        html.Label("State Filter", className="ctrl-label"),
                        dcc.Dropdown(
                            id="state-dropdown",
                            options=_state_options(),
                            value="All",
                            clearable=False,
                            className="dash-dropdown mb-2",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-x-circle me-1"), "Reset Selection"],
                            id="reset-btn",
                            color="secondary",
                            outline=True,
                            size="sm",
                            className="w-100 mb-2",
                            n_clicks=0,
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-download me-1"), "Export CSV"],
                            id="export-btn",
                            color="info",
                            outline=True,
                            size="sm",
                            className="w-100 mb-2",
                            n_clicks=0,
                        ),
                        html.Div(id="selection-info", className="selection-info"),

                        html.Hr(className="divider"),
                        html.H6("SCATTER AXES", className="sidebar-section-title"),

                        html.Label("X Axis", className="ctrl-label"),
                        dcc.Dropdown(
                            id="scatter-x-dropdown",
                            options=_metric_options(),
                            value=DEFAULT_X,
                            clearable=False,
                            className="dash-dropdown mb-2",
                        ),
                        html.Label([
                            "Y Axis",
                            dbc.Badge("synced to map", color="info",
                                      className="ms-2", style={"fontSize": "9px"}),
                        ], className="ctrl-label"),
                        dcc.Dropdown(
                            id="scatter-y-dropdown",
                            options=_metric_options(),
                            value=DEFAULT_Y,
                            clearable=False,
                            className="dash-dropdown mb-2",
                        ),
                        dbc.Checklist(
                            id="scatter-color-state",
                            options=[{"label": "Color by state", "value": "state"}],
                            value=[],
                            className="mb-3",
                            inputClassName="me-1",
                        ),

                        html.Hr(className="divider"),

                        # Suggested hypotheses panel
                        dbc.Card([
                            dbc.CardHeader(
                                html.Small("Suggested Hypotheses", className="fw-bold text-info"),
                                className="py-1 px-2",
                                style={"backgroundColor": "rgba(76,201,240,0.08)"},
                            ),
                            dbc.CardBody([
                                html.P("Does poverty predict premature death?",
                                       className="hyp-text mb-1"),
                                html.P("Expect r > 0.5 between Child Poverty & YPLL Rate",
                                       className="hyp-sub mb-1"),
                                dbc.Button("Test →", id="hyp-btn-1", size="sm",
                                           color="info", outline=True,
                                           className="hyp-test-btn mb-2", n_clicks=0),

                                html.P("Does uninsured rate predict poor health?",
                                       className="hyp-text mb-1"),
                                html.P("Expect r > 0.4 between Uninsured & Fair/Poor Health",
                                       className="hyp-sub mb-1"),
                                dbc.Button("Test →", id="hyp-btn-2", size="sm",
                                           color="info", outline=True,
                                           className="hyp-test-btn mb-2", n_clicks=0),

                                html.P("Do mental & physical health track together?",
                                       className="hyp-text mb-1"),
                                html.P("Expect r > 0.6 between Phys. & Ment. Unhealthy Days",
                                       className="hyp-sub mb-1"),
                                dbc.Button("Test →", id="hyp-btn-3", size="sm",
                                           color="info", outline=True,
                                           className="hyp-test-btn mb-0", n_clicks=0),
                            ], className="p-2"),
                        ], className="hyp-card mb-2"),
                    ]),
                ]),

                # ── MAIN CONTENT ──────────────────────────────────────────────
                dbc.Col(width=10, className="px-2 main-col", children=[

                    # ── ROW 1: Map + Scatter ──────────────────────────────────
                    dbc.Row([
                        # Map
                        dbc.Col(width=7, children=[
                            html.Div(className="panel map-panel panel-map-accent", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-map me-2 text-primary"),
                                    html.Span(id="map-title", className="panel-title fw-semibold"),
                                    dbc.Badge(id="map-mode-badge", color="info", className="ms-2 badge-sm"),
                                    html.Span(id="map-county-count", className="ms-auto text-muted",
                                              style={"fontSize": "10px"}),
                                ]),
                                dcc.Loading(
                                    type="circle", color="#60a5fa",
                                    children=dcc.Graph(
                                        id="map-plot",
                                        config={
                                            "displayModeBar": True,
                                            "displaylogo": False,
                                            "modeBarButtonsToRemove": ["select2d"],
                                            "scrollZoom": True,
                                        },
                                        style={"height": "420px"},
                                    ),
                                ),
                            ]),
                        ]),

                        # Scatter
                        dbc.Col(width=5, children=[
                            html.Div(className="panel panel-scatter-accent", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-scatter-chart me-2 text-warning"),
                                    html.Span("Scatter Plot", className="panel-title"),
                                    html.Small(" — lasso/box-select to highlight", className="text-muted ms-2"),
                                ]),
                                dcc.Loading(type="dot", color="#60a5fa", children=
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
                                        style={"height": "420px"},
                                    )
                                ),
                            ]),
                        ]),
                    ], className="g-2 mb-2"),

                    # ── Details strip ─────────────────────────────────────────
                    html.Div(className="panel details-panel panel-details-accent mb-2", children=[
                        html.Div(className="panel-header", children=[
                            html.I(className="bi bi-info-circle me-2 text-info"),
                            html.Span("County Details — hover map or scatter to inspect",
                                      className="panel-title"),
                        ]),
                        html.Div(id="details-panel", className="details-content"),
                    ]),

                    # ── ROW 2: Parcoords + Histogram ──────────────────────────
                    dbc.Row([
                        dbc.Col(width=8, children=[
                            html.Div(className="panel bottom-panel panel-parcoords-accent", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-list-columns me-2 text-info"),
                                    html.Span("Parallel Coordinates", className="panel-title"),
                                    html.Small(" — drag axes to filter · filtered counties highlight on map",
                                               className="text-muted ms-2"),
                                ]),
                                dcc.Loading(type="dot", color="#60a5fa", children=
                                    dcc.Graph(
                                        id="parcoords-plot",
                                        config={"displayModeBar": False},
                                        style={"height": "280px"},
                                    )
                                ),
                                html.Div(id="parcoords-county-label", className="parcoords-county-label"),
                            ]),
                        ]),
                        dbc.Col(width=4, children=[
                            html.Div(className="panel bottom-panel panel-hist-accent", children=[
                                html.Div(className="panel-header d-flex align-items-center", children=[
                                    html.I(className="bi bi-bar-chart-fill me-2 text-success"),
                                    html.Span("Distribution", className="panel-title"),
                                    html.Small(" — class breaks overlaid", className="text-muted ms-2"),
                                ]),
                                dcc.Loading(type="dot", color="#60a5fa", children=
                                    dcc.Graph(
                                        id="histogram-plot",
                                        config={"displayModeBar": False},
                                        style={"height": "280px"},
                                    )
                                ),
                            ]),
                        ]),
                    ], className="g-2 mb-2"),

                    # ── Tip text ──────────────────────────────────────────────
                    html.Div(
                        html.Small(
                            "Tip: Click map to select counties · Lasso-select on scatter · "
                            "Drag axes on parallel coordinates to filter",
                            className="text-muted",
                        ),
                        className="text-center py-1",
                    ),

                ]),
            ], className="g-0"),
        ]),
    ])
