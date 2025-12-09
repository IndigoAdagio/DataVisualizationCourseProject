import streamlit as st
import plotly.express as px
import pandas as pd


def render_time_view(
    hourly_df: pd.DataFrame,
    selected_cities: list[str],
    value_col: str = "aqi",
) -> None:
    """
    时间序列视图：支持按小时 / 按日聚合两种粒度。"""
    if hourly_df.empty:
        st.info("当前筛选条件下没有数据用于绘制时间序列。")
        return

    if "timestamp" not in hourly_df.columns:
        st.warning("缺少 timestamp 字段，无法绘制时间序列。")
        return

    # 时间粒度选择
    resolution = st.radio(
        "时间粒度",
        options=["按小时", "按日"],
        horizontal=True,
        key="time_resolution_radio",
    )

    df = hourly_df.copy()

    # 聚合到日粒度
    if resolution == "按日":
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
        st.info("筛选后的时间序列为空，请调整筛选条件。")
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
        xaxis_title="时间",
        yaxis_title=value_col.upper(),
        legend_title="城市",
    )
    fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True)
