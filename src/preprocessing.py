import pandas as pd
from .config import NUMERIC_COLUMNS


def _infer_season(month: int) -> str:
    """根据月份推断季节，便于后续做季节性分析。"""
    if month in (12, 1, 2):
        return "冬季"
    if month in (3, 4, 5):
        return "春季"
    if month in (6, 7, 8):
        return "夏季"
    return "秋季"


def preprocess_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """
    对站点-小时级别原始数据做预处理：

    - 解析时间字段 (timepoint -> timestamp)
    - 派生 year/month/day/hour/season 等时间维度
    - 增加统一的 city / station_name 字段
    - 转换数值型字段为数值类型
    - 简单过滤掉明显异常的 AQI 值

    参数
    ------
    df : pd.DataFrame
        原始合并后的长表数据。

    返回
    ------
    pd.DataFrame
        预处理后的 DataFrame。
    """
    df = df.copy()

    # 解析时间字段（示例格式：2025-12-06T0000）
    df["timestamp"] = pd.to_datetime(
        df["timepoint"].astype(str),
        format="%Y-%m-%dT%H%M",
        errors="coerce",
    )
    df = df.dropna(subset=["timestamp"])

    # 衍生时间维度
    df["date"] = df["timestamp"].dt.date
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["day"] = df["timestamp"].dt.day
    df["hour"] = df["timestamp"].dt.hour
    df["season"] = df["month"].apply(_infer_season)

    # 统一命名
    df["city"] = df.get("area")
    df["station_name"] = df.get("positionname")

    # 数值字段转换为 float
    for col in NUMERIC_COLUMNS + ["longitude", "latitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 简单过滤异常 AQI（可在报告中说明这是轻量级清洗策略）
    if "aqi" in df.columns:
        df = df[(df["aqi"].isna()) | ((df["aqi"] >= 0) & (df["aqi"] <= 500))]

    # 去重：同一时间同一监测站只保留一行
    if {"timestamp", "stationcode"}.issubset(df.columns):
        df = df.drop_duplicates(subset=["timestamp", "stationcode"])

    # 按时间排序，便于后续时间序列操作
    df = df.sort_values(["timestamp", "stationcode"])

    return df
