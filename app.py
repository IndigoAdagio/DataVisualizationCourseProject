import warnings
from types import SimpleNamespace

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import (
    HOURLY_PATH,
    DAILY_CITY_PATH,
)
from src.ingest import build_and_save_datasets
from src.views.map_view import render_map_view
from src.views.time_view import render_time_view
from src.views.composition_view import render_composition_view
from src.views.story_view import render_story_view
from src.views.heatmap_view import render_heatmap_view
from src import forecasting


warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------- Page configuration ----------------------
st.set_page_config(
    page_title="Urban Air Quality Visual Analytics",
    layout="wide",
    page_icon="🌫️",
)


def _inject_custom_css() -> None:
    """Inject light-weight CSS to make the app look more like a dashboard."""
    st.markdown(
        """
        <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .main {
            background-color: #f5f7fb;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        .metric-card {
            background: #ffffff;
            padding: 1rem 1.2rem;
            border-radius: 0.8rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
            border: 1px solid #eef0f6;
        }
        .metric-card h3 {
            font-size: 0.9rem;
            font-weight: 500;
            color: #64748b;
            margin-bottom: 0.35rem;
        }
        .metric-card .value {
            font-size: 1.6rem;
            font-weight: 600;
            color: #0f172a;
        }
        .metric-card .sub {
            font-size: 0.8rem;
            color: #94a3b8;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load processed Parquet datasets.

    If they do not exist yet, automatically build them from sample_raw.
    """
    from pathlib import Path

    if not HOURLY_PATH.exists() or not DAILY_CITY_PATH.exists():
        build_and_save_datasets(use_raw=False, overwrite=True)

    hourly = pd.read_parquet(HOURLY_PATH)
    daily = pd.read_parquet(DAILY_CITY_PATH)

    hourly["timestamp"] = pd.to_datetime(hourly["timestamp"])
    daily["date"] = pd.to_datetime(daily["date"])

    for c in ["city", "station", "station_name"]:
        if c in hourly.columns:
            hourly[c] = hourly[c].astype("category")
    if "city" in daily.columns:
        daily["city"] = daily["city"].astype("category")

    hourly = hourly.sort_values("timestamp")
    daily  = daily.sort_values("date")

    return hourly, daily


def _global_filters(hourly_df: pd.DataFrame) -> SimpleNamespace:
    """Render global filters in sidebar and return selected options."""
    with st.sidebar:
        st.header("Global filters")

        all_cities = sorted(
            c for c in hourly_df["city"].dropna().unique().tolist()
        )

        if hourly_df["timestamp"].notna().any():
            min_date = hourly_df["timestamp"].min().date()
            max_date = hourly_df["timestamp"].max().date()
        else:
            min_date = max_date = pd.to_datetime("today").date()

        # date_range = st.date_input(
        #     "Date range",
        #     value=(min_date, max_date),
        #     min_value=min_date,
        #     max_value=max_date,
        #     help="Select the time window for analysis.",
        # )
        desired_start = pd.to_datetime("2025-11-01").date()
        desired_end   = pd.to_datetime("2025-11-30").date()

        default_start = max(min_date, desired_start)
        default_end   = min(max_date, desired_end)

        if default_start > default_end:
            default_range = (min_date, max_date)
        else:
            default_range = (default_start, default_end)

        date_range = st.date_input(
            "Date range",
            value=default_range,
            min_value=min_date,
            max_value=max_date,
            help="Select the time window for analysis.",
        )

        default_cities = all_cities if len(all_cities) > 5 else all_cities
        selected_cities = st.multiselect(
            "Cities",
            options=all_cities,
            default=default_cities,
        )

        # Station selector (optional)
        station_df = hourly_df.copy()
        if selected_cities:
            station_df = station_df[station_df["city"].isin(selected_cities)]
        all_stations = sorted(
            s for s in station_df["station_name"].dropna().unique().tolist()
        )
        selected_stations = st.multiselect(
            "Stations (optional)",
            options=all_stations,
            default=[],
            help="If set, filters station-level views to these stations only.",
        )

        pollutant_options = {
            "AQI (Air Quality Index)": "aqi",
            "PM2.5 (fine particles)": "pm2_5",
            "PM10 (coarse particles)": "pm10",
            "NO₂ (nitrogen dioxide)": "no2",
            "SO₂ (sulfur dioxide)": "so2",
            "O₃ (ozone)": "o3",
            "CO (carbon monoxide)": "co",
        }
        pollutant_label = st.selectbox(
            "Main indicator",
            options=list(pollutant_options.keys()),
            index=0,
        )
        value_col = pollutant_options[pollutant_label]

    if isinstance(date_range, (tuple, list)):
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    return SimpleNamespace(
        start_date=start_date,
        end_date=end_date,
        selected_cities=selected_cities,
        selected_stations=selected_stations,
        value_col=value_col,
        pollutant_label=pollutant_label,
    )


def _apply_filters(
    hourly_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    filters: SimpleNamespace,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply global filters to hourly and daily data frames (fast path)."""
    start_ts = pd.Timestamp(filters.start_date)
    end_ts_exclusive = pd.Timestamp(filters.end_date) + pd.Timedelta(days=1)

    h_idx = hourly_df.set_index("timestamp")
    d_idx = daily_df.set_index("date")

    h = h_idx.loc[start_ts:end_ts_exclusive].reset_index()
    d = d_idx.loc[filters.start_date:filters.end_date].reset_index()

    if filters.selected_cities:
        h = h[h["city"].isin(filters.selected_cities)]
        d = d[d["city"].isin(filters.selected_cities)]
    if filters.selected_stations:
        station_col = "station_name" if "station_name" in h.columns else "station"
        h = h[h[station_col].isin(filters.selected_stations)]

    return h, d



def _render_kpi_cards(hourly_df: pd.DataFrame, daily_df: pd.DataFrame) -> None:
    """Render top KPI cards based on filtered data."""
    col1, col2, col3, col4 = st.columns(4)

    if hourly_df.empty or daily_df.empty:
        titles = ["Average AQI", "Best city", "Worst city", "Heavy-pollution days"]
        for col, title in zip([col1, col2, col3, col4], titles):
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <h3>{title}</h3>
                        <div class="value">—</div>
                        <div class="sub">No data</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        return

    avg_aqi = hourly_df["aqi"].mean()

    if "aqi_mean" in daily_df.columns:
        city_stats = (
            daily_df.groupby("city")["aqi_mean"]
            .mean()
            .dropna()
            .sort_values()
        )
        best_city = city_stats.index[0] if not city_stats.empty else "—"
        worst_city = city_stats.index[-1] if not city_stats.empty else "—"
    else:
        best_city = worst_city = "—"

    heavy_days = 0
    if "aqi_max" in daily_df.columns:
        heavy_days = int((daily_df["aqi_max"] >= 150).sum())

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Average AQI (filtered)</h3>
                <div class="value">{avg_aqi:.1f}</div>
                <div class="sub">All cities · all stations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Best air quality city</h3>
                <div class="value">{best_city}</div>
                <div class="sub">Based on daily mean AQI</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Worst air quality city</h3>
                <div class="value">{worst_city}</div>
                <div class="sub">Based on daily mean AQI</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Heavy-pollution days (AQI ≥ 150)</h3>
                <div class="value">{heavy_days}</div>
                <div class="sub">Within selected period</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    _inject_custom_css()

    st.title("Real-time-inspired Visual Analytics of Urban Air Quality in China (2022–2025)")
    st.markdown(
        "Multi-view visual analytics system for Chinese urban air quality, "
        "supporting spatial, temporal, composition, story, forecast and heatmap views.",
    )

    hourly_df, daily_df = load_processed_data()
    filters = _global_filters(hourly_df)
    h_filtered, d_filtered = _apply_filters(hourly_df, daily_df, filters)

    _render_kpi_cards(h_filtered, d_filtered)

    st.markdown("### Multi-view analysis")

    view = st.radio(
        "Choose a view",
        ["Overview", "Heatmap", "Composition", "Story", "Forecast"],
        horizontal=True,
    )

    if view == "Overview":
        left_col, right_col = st.columns([1.1, 1.5])
        with left_col:
            st.subheader("Spatial distribution map (latest time slice)")
            render_map_view(h_filtered, value_col=filters.value_col)
        with right_col:
            st.subheader("Time-series comparison")
            render_time_view(
                h_filtered,
                selected_cities=filters.selected_cities,
                value_col=filters.value_col,
            )

    elif view == "Heatmap":
        st.subheader("Geographic pollution heatmap")
        render_heatmap_view(
            h_filtered,
            value_col=filters.value_col,
            selected_cities=filters.selected_cities,
            selected_stations=filters.selected_stations,
        )

    elif view == "Composition":
        st.subheader("Pollutant composition by city")
        render_composition_view(
            h_filtered,
            selected_cities=filters.selected_cities,
        )

    elif view == "Story":
        st.subheader("Story explorer")
        render_story_view(h_filtered)

    else:  # Forecast
        st.subheader("Simple forecasting (per-city)")
        if h_filtered.empty:
            st.info("No data available for the current filters to render forecast view.")
        else:
            all_cities = sorted(h_filtered["city"].dropna().unique().tolist())
            if not all_cities:
                st.info("No city information available in filtered data.")
            else:
                default_city = (
                    filters.selected_cities[0]
                    if filters.selected_cities and filters.selected_cities[0] in all_cities
                    else all_cities[0]
                )
                city = st.selectbox("City for forecasting", options=all_cities, index=all_cities.index(default_city))

                horizon_hours = st.slider(
                    "Forecast horizon (hours)",
                    min_value=6,
                    max_value=48,
                    value=24,
                    step=6,
                )

                with st.spinner("Running baseline forecasting model..."):
                    result = forecasting.forecast_for_city(
                        hourly_df=h_filtered,
                        city=city,
                        value_col=filters.value_col,
                        horizon_hours=horizon_hours,
                    )

                if result is None:
                    st.info("Not enough historical samples for this city to train the forecast model.")
                else:
                    df_plot = pd.concat(
                        [
                            result.history.assign(kind="History"),
                            result.forecast.assign(kind="Forecast"),
                        ],
                        ignore_index=True,
                    )

                    fig = px.line(
                        df_plot,
                        x="timestamp",
                        y="value",
                        color="kind",
                        render_mode="webgl",
                    )
                    fig.update_layout(
                        height=450,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_title="Time",
                        yaxis_title=filters.pollutant_label,
                        legend_title="Series",
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        "Forecasting module uses a simple RandomForest baseline with lag features; "
                        "it is intended as a baseline example rather than a production model.",
                    )


if __name__ == "__main__":
    main()
