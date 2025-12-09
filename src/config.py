from pathlib import Path

# 项目根目录（air_quality_analytics）
BASE_DIR = Path(__file__).resolve().parents[1]

# 数据目录
DATA_DIR = BASE_DIR / "data"
SAMPLE_RAW_DATA_DIR = DATA_DIR / "sample_raw"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# 处理后数据路径
HOURLY_PATH = PROCESSED_DIR / "hourly.parquet"
DAILY_CITY_PATH = PROCESSED_DIR / "daily_city.parquet"

# 主要污染物字段（列名）
POLLUTANT_COLUMNS = [
    "pm2_5",
    "pm10",
    "so2",
    "no2",
    "o3",
    "co",
]

# 所有数值型字段，可用于聚合
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

# AQI 简单等级阈值（可在可视化中使用）
AQI_BINS = [0, 50, 100, 150, 200, 300, 500]
AQI_LABELS = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]
