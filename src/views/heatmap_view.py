import streamlit as st
import plotly.express as px
import pandas as pd


def _build_station_level_frame(hourly_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Aggregate to station-level mean values over the filtered time range
    (memory-safe for categorical dtypes)."""
    # 只取绘图所需列，避免无关大列参与分组造成开销
    needed = ["stationcode", "station_name", "city", "latitude", "longitude", value_col]
    cols = [c for c in needed if c in hourly_df.columns]
    if not cols:
        return pd.DataFrame(columns=["stationcode", "station_name", "city", "latitude", "longitude", "value"])

    df = hourly_df[cols].copy()

    # 数值列确保是数值，非法转 NaN；去掉无效行
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude", value_col])

    # 分类列裁掉“未出现”的类别，避免全组合
    for c in ["stationcode", "station_name", "city"]:
        if c in df.columns and pd.api.types.is_categorical_dtype(df[c]):
            df[c] = df[c].cat.remove_unused_categories()

    group_cols = [c for c in ["stationcode", "station_name", "city", "latitude", "longitude"] if c in df.columns]

    if not group_cols:
        return pd.DataFrame(columns=["latitude", "longitude", "value"])

    # 关键：observed=True 只对“实际出现”的分类取值分组；sort=False 避免额外重排
    agg_df = (
        df.groupby(group_cols, observed=True, sort=False, as_index=False)[[value_col]]
          .mean()
          .rename(columns={value_col: "value"})
    )
    return agg_df


def _build_city_level_frame(hourly_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Aggregate to city-level mean values + approximate city coordinates
    (memory-safe for categorical dtypes)."""
    cols = [c for c in ["city", "latitude", "longitude", value_col] if c in hourly_df.columns]
    if not cols:
        return pd.DataFrame(columns=["city", "latitude", "longitude", "value"])

    df = hourly_df[cols].copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["city", "latitude", "longitude", value_col])

    if "city" in df.columns and pd.api.types.is_categorical_dtype(df["city"]):
        df["city"] = df["city"].cat.remove_unused_categories()

    agg_df = (
        df.groupby(["city"], observed=True, sort=False, as_index=False)
          .agg(
              value=(value_col, "mean"),
              latitude=("latitude", "mean"),
              longitude=("longitude", "mean"),
          )
    )
    return agg_df


def _render_density_map(df: pd.DataFrame, value_col_name: str, level_label: str) -> None:
    """Render a density_mapbox heatmap based on aggregated data frame."""
    if df.empty:
        st.info(f"No valid data to render {level_label} heatmap for current filters.")
        return

    center_lat = float(df["latitude"].mean())
    center_lon = float(df["longitude"].mean())

    fig = px.density_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        z=value_col_name,
        radius=40,  # 如需更流畅，可适当减小（例如 25）
        center={"lat": center_lat, "lon": center_lon},
        zoom=3,
        mapbox_style="open-street-map",
    )
    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_colorbar=dict(title=value_col_name.upper()),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_heatmap_view(
    hourly_df: pd.DataFrame,
    value_col: str,
    selected_cities: list[str],
    selected_stations: list[str],
) -> None:
    """
    Heatmap view: geographic pollution heatmap.

    - Uses density_mapbox for a continuous-looking spatial field
    - Supports station-level and city-level aggregation
    - Fully respects global filters through the passed hourly_df
    """
    if hourly_df.empty:
        st.info("No data available for the current filters to render heatmap.")
        return

    if "latitude" not in hourly_df.columns or "longitude" not in hourly_df.columns:
        st.warning("Missing latitude/longitude columns, cannot render heatmap.")
        return

    if value_col not in hourly_df.columns:
        st.warning(f"Column '{value_col}' not found, falling back to 'aqi'.")
        value_col = "aqi"

    mode = st.radio(
        "Aggregation level",
        options=["Station level", "City level"],
        horizontal=True,
        key="heatmap_level_radio",
    )

    with st.expander("Current filter context", expanded=False):
        st.write(
            {
                "selected_cities": selected_cities,
                "selected_stations": selected_stations,
                "value_column": value_col,
            },
        )

    if mode == "Station level":
        agg_df = _build_station_level_frame(hourly_df, value_col)
        _render_density_map(agg_df, "value", "station-level")
    else:
        agg_df = _build_city_level_frame(hourly_df, value_col)
        _render_density_map(agg_df, "value", "city-level")
