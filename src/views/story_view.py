import streamlit as st
import plotly.express as px
import pandas as pd


def _auto_detect_pollution_episode(df: pd.DataFrame) -> tuple[str, pd.Timestamp, pd.Timestamp] | None:
    """
    自动在数据中识别一个“典型污染过程”：

    - 先选择最大 AQI 的城市
    - 再在该城市的时间序列上计算 6 小时滚动平均
    - 取滚动平均最大的时间点作为污染高峰
    - 向前回溯 6 小时作为污染过程的开始

    返回 (city, start_ts, end_ts) 或 None。
    """
    if df.empty or "aqi" not in df.columns:
        return None

    # 选出 AQI 峰值最高的城市
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
    数据故事视图：自动挖掘一个“典型污染过程”，并用阴影区高亮。"""
    if hourly_df.empty:
        st.info("当前筛选条件下没有数据用于讲述故事。")
        return

    if "timestamp" not in hourly_df.columns or "aqi" not in hourly_df.columns:
        st.warning("缺少 timestamp / aqi 字段，无法构建数据故事。")
        return

    result = _auto_detect_pollution_episode(hourly_df)
    if result is None:
        st.info("未能自动识别出明显的污染过程，可尝试扩大时间范围。")
        return

    focus_city, start_ts, end_ts = result

    story_df = (
        hourly_df[hourly_df["city"] == focus_city]
        .copy()
    )
    story_df = story_df.sort_values("timestamp")

    st.markdown(f"### 自动生成的数据故事示例：**{focus_city}** 的一次污染过程")

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
        xaxis_title="时间",
        yaxis_title="AQI",
    )

    st.plotly_chart(fig, use_container_width=True)

    # 文本说明，可在报告中扩写
    episode_df = story_df[
        (story_df["timestamp"] >= start_ts)
        & (story_df["timestamp"] <= end_ts)
    ]
    max_aqi = episode_df["aqi"].max()
    mean_aqi = episode_df["aqi"].mean()
    global_mean = story_df["aqi"].mean()

    st.markdown(
        f"""
        **故事摘要（可在报告中扩写）**

        - 城市：**{focus_city}**
        - 污染过程时间段：**{start_ts:%Y-%m-%d %H:%M} ~ {end_ts:%Y-%m-%d %H:%M}**
        - 该时间段内 AQI 最大值约为 **{max_aqi:.0f}**
        - 该时间段 AQI 平均值约为 **{mean_aqi:.0f}**，显著高于该城市全局平均 AQI **{global_mean:.0f}**

        在期末报告中，你可以进一步结合气象条件、节假日、管控措施等外部信息，
        对这段污染过程进行更深入的叙事分析。
        """,
    )
