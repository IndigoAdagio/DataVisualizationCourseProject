from pathlib import Path

# Project root directory (air_quality_analytics)
BASE_DIR = Path(__file__).resolve().parents[1]

# Data directories
DATA_DIR = BASE_DIR / "data"
SAMPLE_RAW_DATA_DIR = DATA_DIR / "sample_raw"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Processed data paths
HOURLY_PATH = PROCESSED_DIR / "hourly.parquet"
DAILY_CITY_PATH = PROCESSED_DIR / "daily_city.parquet"

# Main pollutant columns
POLLUTANT_COLUMNS = [
    "pm2_5",
    "pm10",
    "so2",
    "no2",
    "o3",
    "co",
]

# Numeric columns used in aggregations
NUMERIC_COLUMNS = [
    "aqi",
    "pm2_5",
    "pm2_5_24h",
    "pm10",
    "pm10_24h",
    "so2",
    "so2_24h",
    "no2",
    "no2_24h",
    "o3",
    "o3_24h",
    "o3_8h",
    "o3_8h_24h",
    "co",
    "co_24h",
]

# AQI binning and labels (simple version for visualization)
AQI_BINS = [0, 50, 100, 150, 200, 300, 500]
AQI_LABELS = ["Excellent", "Good", "Lightly Polluted", "Moderately Polluted", "Heavily Polluted", "Severely Polluted"]
