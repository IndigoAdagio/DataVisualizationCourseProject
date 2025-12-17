import pandas as pd

from .config import NUMERIC_COLUMNS


def _infer_season(month: int) -> str:
    """Infer season label from month index."""
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"


def preprocess_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess station-hour level raw data.

    Steps:
    - Parse the time field (timepoint -> timestamp)
    - Derive temporal features: year, month, day, hour, season
    - Normalize naming: city, station_name
    - Convert numeric columns to numeric types
    - Filter obviously invalid AQI values
    - Deduplicate by (timestamp, stationcode)
    """
    df = df.copy()

    # Parse time field, example format: 2025-12-06T0000
    df["timestamp"] = pd.to_datetime(
        df["timepoint"].astype(str),
        format="%Y-%m-%dT%H%M",
        errors="coerce",
    )
    df = df.dropna(subset=["timestamp"])

    # Temporal features
    df["date"] = df["timestamp"].dt.date
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["day"] = df["timestamp"].dt.day
    df["hour"] = df["timestamp"].dt.hour
    df["season"] = df["month"].apply(_infer_season)

    # Naming normalization
    df["city"] = df.get("area")
    df["station_name"] = df.get("positionname")

    # Convert numeric columns
    for col in NUMERIC_COLUMNS + ["longitude", "latitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filter invalid AQI values
    if "aqi" in df.columns:
        df = df[(df["aqi"].isna()) | ((df["aqi"] >= 0) & (df["aqi"] <= 500))]

    # Deduplicate per (timestamp, station)
    if {"timestamp", "stationcode"}.issubset(df.columns):
        df = df.drop_duplicates(subset=["timestamp", "stationcode"])

    # Sort by time for later time-series operations
    df = df.sort_values(["timestamp", "stationcode"])

    return df
