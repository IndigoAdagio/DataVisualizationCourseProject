from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


@dataclass
class ForecastResult:
    """Container object for forecast results used in visualization."""

    history: pd.DataFrame  # Historical observed values
    forecast: pd.DataFrame  # Future predicted values


def _prepare_series(hourly_df: pd.DataFrame, city: str, value_col: str) -> pd.Series:
    """Extract a time series for a given city and pollutant column."""
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
    Convert a time series into supervised learning format.

    Uses the past n_lags values to predict the value after 'horizon' steps.
    Returns X with shape (num_samples, n_lags) and y with shape (num_samples,).
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
    """Train a simple RandomForestRegressor as baseline model."""
    if X.shape[0] < 30:
        # Not enough samples to train a meaningful model
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
    Forecast AQI or a selected pollutant for a given city.

    Method:
    - Use the last n_lags hours as features
    - Train RandomForestRegressor on all historical data
    - Generate multi-step forecasts iteratively
    - Fallback to naive persistence forecast if not enough data
    """
    series = _prepare_series(hourly_df, city, value_col)
    if len(series) < max(n_lags + horizon_hours, 10):
        return None

    # Build supervised samples
    X, y = _make_supervised(series, n_lags=n_lags, horizon=1)
    model = _train_rf_regressor(X, y)

    # Prepare forecast index
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
        },
    )

    if model is None:
        # Naive persistence forecast
        last_value = float(series.iloc[-1])
        forecast_values = np.full(shape=horizon_hours, fill_value=last_value)
    else:
        # Multi-step iterative forecast
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
        },
    )

    return ForecastResult(history=history_df, forecast=forecast_df)
