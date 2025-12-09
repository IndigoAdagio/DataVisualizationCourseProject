from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


@dataclass
class ForecastResult:
    """封装预测结果，便于前端可视化。"""

    history: pd.DataFrame  # 包含历史真实值
    forecast: pd.DataFrame  # 包含未来预测值（带时间戳）


def _prepare_series(hourly_df: pd.DataFrame, city: str, value_col: str) -> pd.Series:
    """
    从小时级数据中提取指定城市的时间序列。

    返回 index 为时间戳、值为目标污染物浓度的一维 Series。
    """
    df = (
        hourly_df[hourly_df["city"] == city]
        .dropna(subset=["timestamp", value_col])
        .sort_values("timestamp")
    )
    series = pd.Series(df[value_col].values, index=df["timestamp"])
    series = series[~series.index.duplicated(keep="last")]
    return series


def _make_supervised(
    series: pd.Series,
    n_lags: int = 24,
    horizon: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    将时间序列转换为监督学习格式：
    使用过去 n_lags 个时间步预测 horizon 步之后的值。

    返回 X.shape = (样本数, n_lags), y.shape = (样本数,)
    """
    values = series.values.astype(float)
    X, y = [], []
    for t in range(n_lags, len(values) - horizon + 1):
        X.append(values[t - n_lags : t])
        y.append(values[t + horizon - 1])
    if not X:
        return np.empty((0, n_lags)), np.empty((0,))
    return np.asarray(X), np.asarray(y)


def _train_rf_regressor(X: np.ndarray, y: np.ndarray) -> RandomForestRegressor | None:
    """训练一个简单的随机森林回归模型。"""
    if X.shape[0] < 30:
        # 样本太少，不足以训练有意义的模型
        return None
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)
    return model


def forecast_for_city(
    hourly_df: pd.DataFrame,
    city: str,
    value_col: str = "aqi",
    horizon_hours: int = 24,
    n_lags: int = 24,
) -> ForecastResult | None:
    """
    对指定城市的 AQI / PM2.5 等指标做简单预测。

    预测方法：
    - 使用最近 n_lags 小时的值作为特征
    - 使用 RandomForestRegressor 做回归
    - 若样本不足或训练失败，则退化为“持久性预测”（未来值等于最后一个观测值）

    返回
    ------
    ForecastResult 或 None
    """
    series = _prepare_series(hourly_df, city, value_col)
    if len(series) < max(n_lags + horizon_hours, 10):
        return None

    # 使用所有历史数据训练模型
    X, y = _make_supervised(series, n_lags=n_lags, horizon=1)
    model = _train_rf_regressor(X, y)

    # 预测未来 horizon_hours 小时
    last_timestamp = series.index.max()
    freq = pd.infer_freq(series.index) or "H"
    future_index = pd.date_range(
        start=last_timestamp + pd.Timedelta(hours=1),
        periods=horizon_hours,
        freq=freq,
    )

    history_df = pd.DataFrame(
        {
            "timestamp": series.index,
            "value": series.values,
            "type": "history",
        }
    )

    if model is None:
        # 简单持久性预测
        last_value = float(series.iloc[-1])
        forecast_values = np.full(shape=horizon_hours, fill_value=last_value)
    else:
        # 使用迭代方式做多步预测
        window = series.values.astype(float)[-n_lags:].copy()
        forecast_values = []
        for _ in range(horizon_hours):
            pred = model.predict(window.reshape(1, -1))[0]
            forecast_values.append(pred)
            window = np.roll(window, -1)
            window[-1] = pred
        forecast_values = np.asarray(forecast_values)

    forecast_df = pd.DataFrame(
        {
            "timestamp": future_index,
            "value": forecast_values,
            "type": "forecast",
        }
    )

    return ForecastResult(history=history_df, forecast=forecast_df)
