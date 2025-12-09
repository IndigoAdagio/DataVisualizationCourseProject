import streamlit as st
import plotly.express as px
import pandas as pd


def render_map_view(hourly_df: pd.DataFrame, value_col: str = "aqi") -> None:
    """
    空间分布地图视图。

    逻辑：
    - 取当前筛选数据中最新时间点的一帧数据作为“空间切片”
    - 使用 Plotly 的 scatter_geo 画出全国站点/城市分布
    """
    if hourly_df.empty:
        st.info("当前筛选条件下没有数据用于绘制地图。")
        return

    if "timestamp" not in hourly_df.columns:
        st.warning("缺少 timestamp 字段，无法绘制地图。")
        return

    latest_ts = hourly_df["timestamp"].max()
    latest_df = hourly_df[hourly_df["timestamp"] == latest_ts].copy()

    if latest_df.empty:
        st.info("当前筛选条件下最新时间片为空。")
        return

    if {"latitude", "longitude"}.issubset(latest_df.columns) is False:
        st.warning("数据中缺少经纬度信息，无法绘制地图。")
        return

    # 若指标列不存在，则退回到 AQI
    if value_col not in latest_df.columns:
        st.warning(f"列 {value_col} 在数据中不存在，已退回使用 aqi。")
        value_col = "aqi"

    fig = px.scatter_geo(
        latest_df,
        lat="latitude",
        lon="longitude",
        color=value_col,
        hover_name="station_name",
        hover_data={
            "city": True,
            "aqi": True,
            "pm2_5": True,
            "pm10": True,
            "so2": True,
            "no2": True,
            "o3": True,
            "co": True,
            "latitude": False,
            "longitude": False,
        },
        color_continuous_scale="RdYlGn_r",
        projection="natural earth",
    )

    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=10, b=0),
        geo=dict(
            showcountries=True,
            showland=True,
            landcolor="rgb(240,240,240)",
        ),
        coloraxis_colorbar=dict(title=value_col.upper()),
    )

    st.caption(f"地图时间截面：{latest_ts}")
    st.plotly_chart(fig, use_container_width=True)
