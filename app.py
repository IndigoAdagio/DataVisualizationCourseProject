import warnings
from types import SimpleNamespace

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import (
    HOURLY_PATH,
    DAILY_CITY_PATH,
    AQI_LABELS,
    AQI_BINS,
)
from src.ingest import build_and_save_datasets
from src.views.map_view import render_map_view
from src.views.time_view import render_time_view
from src.views.composition_view import render_composition_view
from src.views.story_view import render_story_view
from src import forecasting


warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------- 页面基础配置 ----------------------
st.set_page_config(
    page_title="Urban Air Quality Visual Analytics",
    layout="wide",
    page_icon="🌫️",
)


def _inject_custom_css() -> None:
    """通过少量 CSS 美化整体 UI，让它更像专业 dashboard。"""
    st.markdown(
        """
        <style>
        /* 全局字体与背景 */
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .main {
            background-color: #f5f7fb;
        }

        /* 顶部标题区域留白 */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* 指标卡片样式 */
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

        /* 隐藏默认的 Streamlit 菜单和 footer，可按需注释掉 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    加载（或构建）处理后的数据。

    - 若 Parquet 文件不存在，则自动基于 sample_raw 运行一次 ingest
    - 后续重复访问会由 Streamlit cache 加速
    """
    from pathlib import Path

    if not HOURLY_PATH.exists() or not DAILY_CITY_PATH.exists():
        # 为了保证“开箱即用”，这里默认先使用示例数据构建
        build_and_save_datasets(use_raw=False, overwrite=True)

    hourly = pd.read_parquet(HOURLY_PATH)
    daily = pd.read_parquet(DAILY_CITY_PATH)

    hourly["timestamp"] = pd.to_datetime(hourly["timestamp"])
    daily["date"] = pd.to_datetime(daily["date"])

    return hourly, daily


def _global_filters(hourly_df: pd.DataFrame) -> SimpleNamespace:
    """在侧边栏渲染全局筛选控件，并返回筛选条件。"""
    with st.sidebar:
        st.header("筛选面板")

        all_cities = sorted(
            c for c in hourly_df["city"].dropna().unique().tolist()
        )

        min_date = hourly_df["timestamp"].min().date()
        max_date = hourly_df["timestamp"].max().date()

        date_range = st.date_input(
            "日期范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="选择要分析的时间区间",
        )

        # 城市多选
        default_cities = all_cities[:5] if len(all_cities) > 5 else all_cities
        selected_cities = st.multiselect(
            "城市（可多选）",
            options=all_cities,
            default=default_cities,
        )

        # 指标选择
        pollutant_options = {
            "AQI (空气质量指数)": "aqi",
            "PM2.5 (细颗粒物)": "pm2_5",
            "PM10 (可吸入颗粒物)": "pm10",
            "NO₂ (二氧化氮)": "no2",
            "SO₂ (二氧化硫)": "so2",
            "O₃ (臭氧)": "o3",
            "CO (一氧化碳)": "co",
        }
        pollutant_label = st.selectbox(
            "主要分析指标",
            options=list(pollutant_options.keys()),
            index=0,
        )
        value_col = pollutant_options[pollutant_label]

        st.markdown("---")
        st.markdown(
            "在主区域中可通过 Tab 切换：**总览 / 组成分析 / 数据故事 / 预测**。",
        )

    # 处理日期输入（可能只选择单日）
    if isinstance(date_range, tuple) or isinstance(date_range, list):
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    return SimpleNamespace(
        start_date=start_date,
        end_date=end_date,
        selected_cities=selected_cities,
        value_col=value_col,
        pollutant_label=pollutant_label,
    )


def _apply_filters(
    hourly_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    filters: SimpleNamespace,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """根据全局筛选条件过滤小时级和日级数据。"""
    h = hourly_df.copy()
    d = daily_df.copy()

    h_mask = (h["timestamp"].dt.date >= filters.start_date) & (
        h["timestamp"].dt.date <= filters.end_date
    )
    d_mask = (d["date"].dt.date >= filters.start_date) & (
        d["date"].dt.date <= filters.end_date
    )

    if filters.selected_cities:
        h_mask &= h["city"].isin(filters.selected_cities)
        d_mask &= d["city"].isin(filters.selected_cities)

    h_filtered = h.loc[h_mask]
    d_filtered = d.loc[d_mask]

    return h_filtered, d_filtered


def _render_kpi_cards(hourly_df: pd.DataFrame, daily_df: pd.DataFrame) -> None:
    """顶部 KPI 卡片区。"""
    col1, col2, col3, col4 = st.columns(4)

    if hourly_df.empty or daily_df.empty:
        for col, title in zip(
            [col1, col2, col3, col4],
            ["平均 AQI", "最优城市", "最差城市", "重污染天数"],
        ):
            with col:
                st.markdown(
                    """
                    <div class="metric-card">
                        <h3>{title}</h3>
                        <div class="value">—</div>
                        <div class="sub">暂无数据</div>
                    </div>
                    """.format(title=title),
                    unsafe_allow_html=True,
                )
        return

    avg_aqi = hourly_df["aqi"].mean()

    # 最优 / 最差城市（根据 aqi_mean）
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
                <h3>当前筛选范围内平均 AQI</h3>
                <div class="value">{avg_aqi:.1f}</div>
                <div class="sub">所有城市 · 所有站点</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>平均空气质量最佳城市</h3>
                <div class="value">{best_city}</div>
                <div class="sub">基于日均 AQI</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>平均空气质量最差城市</h3>
                <div class="value">{worst_city}</div>
                <div class="sub">基于日均 AQI</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>重污染天数 (AQI ≥ 150)</h3>
                <div class="value">{heavy_days}</div>
                <div class="sub">选定时间范围内</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    _inject_custom_css()

    st.title("Real-time-inspired Visual Analytics of Urban Air Quality in China (2022–2025)")
    st.markdown(
        "中国城市空气质量多视图可视分析系统 —— 支持空间分布、时间序列、污染物组成、数据故事与简单预测。",
    )

    hourly_df, daily_df = load_processed_data()
    filters = _global_filters(hourly_df)
    h_filtered, d_filtered = _apply_filters(hourly_df, daily_df, filters)

    # 顶部 KPI 卡片
    _render_kpi_cards(h_filtered, d_filtered)

    st.markdown("### 多视图分析")

    tab_overview, tab_composition, tab_story, tab_forecast = st.tabs(
        ["总览", "组成分析", "数据故事", "预测"],
    )

    # -------------------- 总览 Tab --------------------
    with tab_overview:
        left_col, right_col = st.columns([1.1, 1.5])

        with left_col:
            st.subheader("空间分布地图")
            render_map_view(h_filtered, value_col=filters.value_col)

        with right_col:
            st.subheader("时间序列对比")
            render_time_view(
                h_filtered,
                selected_cities=filters.selected_cities,
                value_col=filters.value_col,
            )

    # -------------------- 组成分析 Tab --------------------
    with tab_composition:
        render_composition_view(
            h_filtered,
            selected_cities=filters.selected_cities,
        )

    # -------------------- 数据故事 Tab --------------------
    with tab_story:
        render_story_view(h_filtered)

    # -------------------- 预测 Tab --------------------
    with tab_forecast:
        if h_filtered.empty:
            st.info("当前筛选条件下没有数据用于预测。请适当放宽时间范围或城市筛选。")
        else:
            all_cities = sorted(h_filtered["city"].dropna().unique().tolist())
            if not all_cities:
                st.info("当前筛选条件下没有城市信息。")
            else:
                default_city = (
                    filters.selected_cities[0]
                    if filters.selected_cities and filters.selected_cities[0] in all_cities
                    else all_cities[0]
                )
                city = st.selectbox("选择要预测的城市", options=all_cities, index=all_cities.index(default_city))

                horizon_hours = st.slider(
                    "预测未来多少小时",
                    min_value=6,
                    max_value=48,
                    value=24,
                    step=6,
                )

                with st.spinner("正在生成简单预测结果……"):
                    result = forecasting.forecast_for_city(
                        hourly_df=h_filtered,
                        city=city,
                        value_col=filters.value_col,
                        horizon_hours=horizon_hours,
                    )

                if result is None:
                    st.info("该城市可用于训练的历史样本过少，无法生成预测结果。")
                else:
                    df_plot = pd.concat(
                        [
                            result.history.assign(kind="历史观测"),
                            result.forecast.assign(kind="模型预测"),
                        ],
                        ignore_index=True,
                    )

                    fig = px.line(
                        df_plot,
                        x="timestamp",
                        y="value",
                        color="kind",
                    )
                    fig.update_layout(
                        height=450,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_title="时间",
                        yaxis_title=filters.pollutant_label,
                        legend_title="曲线类型",
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        "预测模块采用简单的随机森林回归 + 滞后窗口特征，仅作为基线示例。你可以在报告中进一步扩展模型设计。",
                    )


if __name__ == "__main__":
    main()
