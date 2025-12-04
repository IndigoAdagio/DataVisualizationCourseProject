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

## How to test
Because the project is a static front-end, testing is done interactively in the browser. The steps below verify that the sample data loads and that the coordinated views behave as expected:

1. **Start the local server** using `python -m http.server 8000` (or open `index.html` directly).
2. **Load the dashboard** at <http://localhost:8000> and confirm you see the map, time-series panel, stacked bars, and radar chart.
3. **Hover on the map markers** to view latest pollutant values per city and confirm the heatmap colors change with concentration.
4. **Click a city marker** and verify the time-series chart updates to that city’s history while the composition charts update to the same selection.
5. **Drag on the time-series brush** to zoom into a time window; check that stacked bars and the radar chart respect the brushed range.
6. **Use the “Play Timeline” control** to animate through dates and observe the map and charts updating in sync with the current frame.
7. **Switch events in the legend** (e.g., holidays/policy actions) to see the event markers highlighted along the timeline.

If you replace `data/sample_data.json` with your own data, repeat steps 2–6 to confirm loading works and the derived AQI and chart updates remain synchronized.

## Updating data sources
Replace `data/sample_data.json` with real CNEMC API responses or meteorological data. Each city entry expects latitude, longitude, and dated pollutant measurements (PM2.5, SO₂, NO₂, O₃). The latest record is used for the heatmap, while the full history powers the time series and composition charts.
