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
    污染物组成视图：

    - 柱状图：多个城市的主要污染物平均浓度对比
    - 雷达图：单城市的污染物构成
    """
    if hourly_df.empty:
        st.info("当前筛选条件下没有数据用于组成分析。")
        return

    df = hourly_df.copy()

    if selected_cities:
        df = df[df["city"].isin(selected_cities)]

    if df.empty:
        st.info("筛选后的数据为空，请调整筛选条件。")
        return

    # ---------- 柱状图：多城市平均浓度对比 ----------
    numeric_cols = [c for c in POLLUTANT_COLUMNS if c in df.columns]
    if not numeric_cols:
        st.warning("数据中不包含任何主要污染物字段。")
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

    st.subheader("主要污染物平均浓度对比")
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
        xaxis_title="污染物",
        yaxis_title="平均浓度（示意单位）",
        legend_title="城市",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ---------- 雷达图：单城市污染物构成 ----------
    st.subheader("单城市污染物构成（雷达图）")
    city_options = group["city"].dropna().unique().tolist()
    default_city = (
        selected_cities[0]
        if selected_cities and selected_cities[0] in city_options
        else (city_options[0] if city_options else None)
    )

    if not city_options or default_city is None:
        st.info("当前没有可用于绘制雷达图的城市数据。")
        return

    city = st.selectbox(
        "选择城市",
        options=city_options,
        index=city_options.index(default_city),
    )

    row = group[group["city"] == city]
    if row.empty:
        st.info("该城市没有足够的数据绘制雷达图。")
        return

    values = [float(row.iloc[0][c]) if c in row.columns else 0.0 for c in numeric_cols]
    labels = [_POLLUTANT_LABELS.get(c, c) for c in numeric_cols]

    # 雷达图需要首尾闭合
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
