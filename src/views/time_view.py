import streamlit as st
import plotly.express as px
import pandas as pd


def render_time_view(
    hourly_df: pd.DataFrame,
    selected_cities: list[str],
    value_col: str = "aqi",
) -> None:
    """Time-series view with hourly/daily aggregation options."""
    if hourly_df.empty:
        st.info("No data available for the current filters to render time-series view.")
        return

    if "timestamp" not in hourly_df.columns:
        st.warning("Missing 'timestamp' column, cannot render time-series view.")
        return

    # Time resolution selection
    resolution = st.radio(
        "Time resolution",
        options=["Daily", "Hourly"],
        horizontal=True,
        key="time_resolution_radio",
    )

    df = hourly_df.copy()

    if resolution == "Daily":
        if "date" not in df.columns:
            df["date"] = df["timestamp"].dt.date
        group_cols = ["date", "city"]
        df = (
            df.groupby(group_cols)[value_col]
            .mean()
            .reset_index()
            .rename(columns={value_col: f"{value_col}_mean"})
        )
        df["timestamp_plot"] = pd.to_datetime(df["date"])
        y_col = f"{value_col}_mean"
    else:
        y_col = value_col
        df["timestamp_plot"] = df["timestamp"]

    if selected_cities:
        df = df[df["city"].isin(selected_cities)]

    if df.empty:
        st.info("Filtered time-series is empty. Try relaxing the filters.")
        return

    fig = px.line(
        df,
        x="timestamp_plot",
        y=y_col,
        color="city",
        markers=False,
    )
    fig.update_layout(
        height=450,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Time",
        yaxis_title=value_col.upper(),
        legend_title="City",
    )
    fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True)
