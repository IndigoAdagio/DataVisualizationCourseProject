# src/views/map_view.py
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

_CHINA_CENTER = {"lat": 35.0, "lon": 103.8}
_CHINA_ZOOM = 2.2

@st.cache_data(show_spinner=False)
def _load_cn_province_geojson() -> dict:
    url = "https://geo.datav.aliyun.com/areas_v3/bound/geojson?code=100000_full"
    try:
        import requests
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        local = Path(__file__).resolve().parents[2] / "data" / "china_provinces.geojson"
        if local.exists():
            with open(local, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"type": "FeatureCollection", "features": []}

def _guess_lat_lon_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    lon_candidates = ["lon", "lng", "longitude", "LONGITUDE", "Lon", "Lng"]
    lat_candidates = ["lat", "latitude", "LATITUDE", "Lat"]
    lon_col = next((c for c in lon_candidates if c in df.columns), None)
    lat_col = next((c for c in lat_candidates if c in df.columns), None)
    return lat_col, lon_col

def render_map_view(df: pd.DataFrame, value_col: str = "aqi") -> None:
    if df is None or df.empty:
        st.info("No data available!")
        return

    ts_col = "timestamp" if "timestamp" in df.columns else None
    if ts_col is None or df[ts_col].isna().all():
        latest = df.copy()
    else:
        latest_ts = df[ts_col].max()
        latest = df[df[ts_col] == latest_ts].copy()

    lat_col, lon_col = _guess_lat_lon_columns(latest)
    if not lat_col or not lon_col:
        city_centers = latest.groupby("city", as_index=False)[value_col].mean()
        fig = px.scatter_geo(
            city_centers,
            locations="city",
            locationmode="country names",
            size=value_col,
            color=value_col,
            projection="natural earth",
        )
        fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, use_container_width=True)
        return

    fig = px.scatter_mapbox(
        latest,
        lat=lat_col,
        lon=lon_col,
        color=value_col,
        hover_name=latest["city"] if "city" in latest.columns else None,
        hover_data=[value_col] + ([ts_col] if ts_col else []),
        color_continuous_scale="RdYlGn_r",
        zoom=_CHINA_ZOOM,
        height=430,
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title=value_col.upper()),
        mapbox=dict(center=_CHINA_CENTER, zoom=_CHINA_ZOOM),
    )

    provinces_geo = _load_cn_province_geojson()
    existing_layers = list(fig.layout.mapbox.layers) if fig.layout.mapbox.layers else []
    boundary_layer = dict(
        source=provinces_geo,
        type="line",
        line={"width": 1},
        color="rgba(80,80,80,0.75)",
    )
    existing_layers.insert(0, boundary_layer)
    fig.update_layout(mapbox_layers=existing_layers)

    st.plotly_chart(fig, use_container_width=True)
