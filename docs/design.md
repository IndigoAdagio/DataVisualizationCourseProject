# System Design Notes

This document summarizes the architecture and design choices of the
air quality visual analytics system.

## 1. High-level architecture

The system is organized into three layers:

1. **Data layer**
   - Input: raw station-hour CSV files under `data/raw/` or `data/sample_raw/`
   - Pipeline:
     - `src/ingest.py` loads and merges CSVs
     - `src/preprocessing.py` cleans and enriches the data
     - `src/aggregations.py` aggregates to city-day level
   - Output: two Parquet files under `data/processed/`:
     - `hourly.parquet` (station-hour level)
     - `daily_city.parquet` (city-day level)

2. **Logic/analytics layer**
   - `config.py`: centralizes paths and shared constants
   - `forecasting.py`: baseline forecasting model using RandomForestRegressor
   - Additional functions for aggregations and feature derivation

3. **Presentation layer**
   - `app.py`: Streamlit entry point, layout, global filters, and tab routing
   - `views/`: modular visualization components
     - `map_view.py`: spatial scatter map
     - `time_view.py`: time-series view
     - `composition_view.py`: pollutant composition
     - `story_view.py`: data story
     - `heatmap_view.py`: geographic heatmap

## 2. Global filters and data flow

- Global filters are implemented in the sidebar (`_global_filters` in `app.py`):
  - date range
  - cities (multi-select)
  - stations (optional multi-select)
  - main pollutant/indicator
- Filters are applied in `_apply_filters` and the filtered subsets
  (`h_filtered`, `d_filtered`) are passed down to each view function.
- This ensures all views are consistent and coordinated.

## 3. View modules

- **Overview (map + time-series)**
  - Map uses the latest time slice from the filtered dataset.
  - Time-series supports hourly and daily resolutions.

- **Composition view**
  - Bar chart: average pollutant concentrations across cities.
  - Radar chart: single-city pollutant profile.

- **Story view**
  - Detects a typical pollution episode using 6-hour rolling mean AQI.
  - Highlights the episode with a shaded region in the time-series plot.

- **Forecast view**
  - Allows selecting a city and forecast horizon (in hours).
  - Uses a RandomForest-based baseline model with lag features.
  - Plots historical vs forecasted values in one figure.

- **Heatmap view (new)**
  - Uses Plotly `density_mapbox` to render a geographic heatmap.
  - Supports two aggregation levels:
    - station-level: average value per station over filtered time range
    - city-level: average value per city, with approximate coordinates from station means
  - Fully synchronized with global filters (date, city, station, pollutant).

## 4. Styling

- Global CSS is injected in `app.py` to create card-style KPI components
  and a light dashboard background.
- Plotly figures are configured with reasonable margins and axis labels
  to fit wide-screen layouts (`layout="wide"`).

## 5. Extensibility

- New views can be added under `src/views/` and plugged into `app.py` as
  additional tabs.
- The ingestion pipeline can be extended to handle more data types
  (e.g., meteorological variables) with minimal changes to the views.
- The forecasting module can be upgraded to more advanced time-series
  models while keeping the same interface (`forecast_for_city`).
