# Spatiotemporal Air Quality Explorer

A single-page, multi-view dashboard that combines a national pollution heatmap, brushable historical trends, and pollutant composition charts. The design follows the interactive storytelling ideas in [Zeng et al. (2025)](https://arxiv.org/pdf/2507.09917) and uses mock data that can be replaced with live CNEMC and meteorological feeds.

## Features
- **Multi-view coordination**: Leaflet map heatmap, D3 time series, stacked bar, and radar chart linked by city and timeline selections.
- **Data storytelling**: Event strip and timeline animation to show how holidays and policy actions affect air quality.
- **Preprocessing hooks**: AQI computation from PM2.5, outlier-resistant spatial interpolation, and daily aggregation utilities inside `src/app.js`.

## Running locally
No build step is required. Open `index.html` in a modern browser or serve the folder with a lightweight server:

```bash
python -m http.server 8000
```

Then visit <http://localhost:8000>.

## Updating data sources
Replace `data/sample_data.json` with real CNEMC API responses or meteorological data. Each city entry expects latitude, longitude, and dated pollutant measurements (PM2.5, SO₂, NO₂, O₃). The latest record is used for the heatmap, while the full history powers the time series and composition charts.
