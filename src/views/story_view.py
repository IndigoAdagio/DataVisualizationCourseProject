import streamlit as st
import plotly.express as px
import pandas as pd


def _auto_detect_pollution_episode(df: pd.DataFrame) -> tuple[str, pd.Timestamp, pd.Timestamp] | None:
    """
    Automatically detect a typical pollution episode.

    Heuristic:
    - find the city with highest max AQI
    - within that city's time series, compute 6-hour rolling mean
    - pick the time of maximum rolling mean as peak
    - define episode as [peak - 6h, peak]
    """
    if df.empty or "aqi" not in df.columns:
        return None

    city_max = (
        df.groupby("city")["aqi"]
        .max()
        .sort_values(ascending=False)
    )
    if city_max.empty:
        return None

    focus_city = city_max.index[0]
    city_df = (
        df[df["city"] == focus_city]
        .dropna(subset=["timestamp", "aqi"])
        .sort_values("timestamp")
    )
    if city_df.empty:
        return None

    city_df = city_df.set_index("timestamp")
    city_df["aqi_rolling"] = city_df["aqi"].rolling("6H", min_periods=1).mean()

    if city_df["aqi_rolling"].isna().all():
        return None

    peak_ts = city_df["aqi_rolling"].idxmax()
    start_ts = peak_ts - pd.Timedelta(hours=6)
    end_ts = peak_ts

    return focus_city, start_ts, end_ts


def render_story_view(hourly_df: pd.DataFrame) -> None:
    """
    Data story view: highlight an automatically detected pollution episode.
    """
    if hourly_df.empty:
        st.info("No data available for the current filters to render story view.")
        return

    if "timestamp" not in hourly_df.columns or "aqi" not in hourly_df.columns:
        st.warning("Missing 'timestamp' or 'aqi' column, cannot build story view.")
        return

    result = _auto_detect_pollution_episode(hourly_df)
    if result is None:
        st.info("Failed to detect a clear pollution episode. Try expanding the time range.")
        return

    focus_city, start_ts, end_ts = result

    story_df = (
        hourly_df[hourly_df["city"] == focus_city]
        .copy()
    )
    story_df = story_df.sort_values("timestamp")

    st.markdown(f"### Automatically detected pollution episode in **{focus_city}**")

    fig = px.line(
        story_df,
        x="timestamp",
        y="aqi",
        title=None,
    )
    fig.add_vrect(
        x0=start_ts,
        x1=end_ts,
        fillcolor="salmon",
        opacity=0.2,
        layer="below",
        line_width=0,
    )
    fig.update_layout(
        height=450,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Time",
        yaxis_title="AQI",
    )

    st.plotly_chart(fig, use_container_width=True)

    episode_df = story_df[
        (story_df["timestamp"] >= start_ts)
        & (story_df["timestamp"] <= end_ts)
    ]
    max_aqi = episode_df["aqi"].max()
    mean_aqi = episode_df["aqi"].mean()
    global_mean = story_df["aqi"].mean()

    st.markdown(
        f"""
        **Episode summary (for report narrative)**

        - City: **{focus_city}**
        - Episode period: **{start_ts:%Y-%m-%d %H:%M} ~ {end_ts:%Y-%m-%d %H:%M}**
        - Max AQI during episode: **{max_aqi:.0f}**
        - Average AQI during episode: **{mean_aqi:.0f}**
        - City-wide average AQI over full period: **{global_mean:.0f}**
        """,
    )
