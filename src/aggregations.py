import pandas as pd

from .config import NUMERIC_COLUMNS


def aggregate_daily_city(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate station-hour level data to city-day level.

    For each (date, city):
    - compute daily mean for numeric columns
    - compute max AQI of the day
    - compute number of hours with AQI >= 150 (heavy-pollution hours)
    """
    if hourly_df.empty:
        return pd.DataFrame()

    df = hourly_df.copy()

    df["date"] = pd.to_datetime(df["date"])

    group_cols = ["date", "city"]

    # Daily mean for numeric columns
    numeric_cols = [c for c in NUMERIC_COLUMNS if c in df.columns]
    mean_df = (
        df.groupby(group_cols)[numeric_cols]
        .mean()
        .reset_index()
    )

    # Daily max AQI and heavy-pollution hours
    if "aqi" in df.columns:
        max_aqi = (
            df.groupby(group_cols)["aqi"]
            .max()
            .reset_index(name="aqi_max")
        )
        mean_df = mean_df.merge(max_aqi, on=group_cols, how="left")

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

    # Rename mean columns with suffix _mean
    rename_map = {c: f"{c}_mean" for c in numeric_cols if c != "aqi"}
    if "aqi" in numeric_cols:
        rename_map["aqi"] = "aqi_mean"
    mean_df = mean_df.rename(columns=rename_map)

    return mean_df
