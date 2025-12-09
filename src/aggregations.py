import pandas as pd
from .config import NUMERIC_COLUMNS


def aggregate_daily_city(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    将站点-小时级别数据聚合为城市-日级别：

    - 对各数值型字段取城市内所有站点的日均值
    - 计算每日城市内 AQI 最大值和重污染小时数
    """
    if hourly_df.empty:
        return pd.DataFrame()

    df = hourly_df.copy()

    # 确保日期字段为日期类型
    df["date"] = pd.to_datetime(df["date"])

    group_cols = ["date", "city"]

    # 数值字段日均
    numeric_cols = [c for c in NUMERIC_COLUMNS if c in df.columns]
    mean_df = (
        df.groupby(group_cols)[numeric_cols]
        .mean()
        .reset_index()
    )

    # AQI 日最大值
    if "aqi" in df.columns:
        max_aqi = (
            df.groupby(group_cols)["aqi"]
            .max()
            .reset_index(name="aqi_max")
        )
        mean_df = mean_df.merge(max_aqi, on=group_cols, how="left")

        # 重污染小时数（AQI >= 150）
        heavy_hours = (
            df.assign(heavy=lambda x: x["aqi"] >= 150)
            .groupby(group_cols)["heavy"]
            .sum()
            .reset_index(name="heavy_pollution_hours")
        )
        mean_df = mean_df.merge(heavy_hours, on=group_cols, how="left")
    else:
        mean_df["aqi_max"] = pd.NA
        mean_df["heavy_pollution_hours"] = pd.NA

    # 列重命名：均值字段加后缀 _mean，方便在可视化中区分
    rename_map = {c: f"{c}_mean" for c in numeric_cols if c != "aqi"}
    if "aqi" in numeric_cols:
        rename_map["aqi"] = "aqi_mean"

    mean_df = mean_df.rename(columns=rename_map)

    return mean_df
