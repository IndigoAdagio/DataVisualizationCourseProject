import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from ..config import POLLUTANT_COLUMNS


_POLLUTANT_LABELS = {
    "pm2_5": "PM2.5",
    "pm10": "PM10",
    "so2": "SO₂",
    "no2": "NO₂",
    "o3": "O₃",
    "co": "CO",
}


def render_composition_view(
    hourly_df: pd.DataFrame,
    selected_cities: list[str],
) -> None:
    """
    Pollutant composition view.

    - Bar chart: average pollutant concentrations across cities
    - Radar chart: pollutant profile for a single city
    """
    if hourly_df.empty:
        st.info("No data available for the current filters to render composition view.")
        return

    df = hourly_df.copy()

    if selected_cities:
        df = df[df["city"].isin(selected_cities)]

    if df.empty:
        st.info("Filtered data is empty. Try relaxing the filters.")
        return

    # Bar chart: average concentration by city
    numeric_cols = [c for c in POLLUTANT_COLUMNS if c in df.columns]
    if not numeric_cols:
        st.warning("No pollutant columns found in data.")
        return

    group = (
        df.groupby("city")[numeric_cols]
        .mean()
        .reset_index()
    )

    long_df = group.melt(
        id_vars="city",
        value_vars=numeric_cols,
        var_name="pollutant",
        value_name="value",
    )
    long_df["pollutant_label"] = long_df["pollutant"].map(_POLLUTANT_LABELS).fillna(
        long_df["pollutant"],
    )

    st.subheader("Average pollutant concentration across cities")
    fig_bar = px.bar(
        long_df,
        x="pollutant_label",
        y="value",
        color="city",
        barmode="group",
    )
    fig_bar.update_layout(
        height=450,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Pollutant",
        yaxis_title="Average concentration (illustrative units)",
        legend_title="City",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Radar chart: single city pollutant profile
    st.subheader("Single-city pollutant profile (radar chart)")
    city_options = group["city"].dropna().unique().tolist()
    default_city = (
        selected_cities[0]
        if selected_cities and selected_cities[0] in city_options
        else (city_options[0] if city_options else None)
    )

    if not city_options or default_city is None:
        st.info("No city data available to render radar chart.")
        return

    city = st.selectbox(
        "Select city",
        options=city_options,
        index=city_options.index(default_city),
    )

    row = group[group["city"] == city]
    if row.empty:
        st.info("Not enough data for this city to render radar chart.")
        return

    values = [float(row.iloc[0][c]) if c in row.columns else 0.0 for c in numeric_cols]
    labels = [_POLLUTANT_LABELS.get(c, c) for c in numeric_cols]

    # Radar chart needs closed loop (first value repeated at end)
    values_cycle = values + [values[0]]
    labels_cycle = labels + [labels[0]]

    fig_radar = go.Figure(
        data=[
            go.Scatterpolar(
                r=values_cycle,
                theta=labels_cycle,
                fill="toself",
                name=city,
            ),
        ],
    )
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_radar, use_container_width=True)
