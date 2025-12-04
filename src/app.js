const MAP_CENTER = [35.86, 104.19];
const MAP_ZOOM = 4.5;

const colorScale = d3
  .scaleThreshold()
  .domain([50, 100, 150, 200, 300])
  .range(["#0ae4a2", "#b4e400", "#f7d046", "#f08c42", "#d64045", "#7e0023"]);

const pollutants = [
  { key: "pm25", label: "PM2.5" },
  { key: "so2", label: "SO₂" },
  { key: "no2", label: "NO₂" },
  { key: "o3", label: "O₃" }
];

let map;
let cityLayer;
let timelineInterval;
let data;

async function loadData() {
  const res = await fetch("data/sample_data.json");
  data = await res.json();
  document.getElementById("lastUpdated").textContent = new Date(data.lastUpdated).toLocaleString();
  initializeControls();
  initializeMap();
  updateMap("aqi");
  drawLegend();
  populateEvents();
  drawTimeSeries();
  drawComposition();
}

function initializeControls() {
  const citySelect = document.getElementById("citySelect");
  data.cities.forEach(city => {
    const option = document.createElement("option");
    option.value = city.name;
    option.textContent = city.name;
    citySelect.appendChild(option);
  });
  citySelect.value = data.cities[0].name;
  citySelect.addEventListener("change", () => {
    drawTimeSeries();
    drawComposition();
  });

  const metricSelect = document.getElementById("metricSelect");
  metricSelect.addEventListener("change", () => updateMap(metricSelect.value));
  document.getElementById("playButton").addEventListener("click", toggleAnimation);
}

function initializeMap() {
  map = L.map("map", { zoomControl: false }).setView(MAP_CENTER, MAP_ZOOM);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 8,
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);

  cityLayer = L.layerGroup().addTo(map);
}

function computeAQI(pm25) {
  const breakpoints = [0, 35, 75, 115, 150, 250, 350, 500];
  const aqiValues = [0, 50, 100, 150, 200, 300, 400, 500];
  for (let i = 0; i < breakpoints.length - 1; i++) {
    if (pm25 <= breakpoints[i + 1]) {
      const ratio = (pm25 - breakpoints[i]) / (breakpoints[i + 1] - breakpoints[i]);
      return Math.round(aqiValues[i] + ratio * (aqiValues[i + 1] - aqiValues[i]));
    }
  }
  return 500;
}

function updateMap(metric) {
  cityLayer.clearLayers();
  data.cities.forEach(city => {
    const latest = city.records[city.records.length - 1];
    const value = metric === "aqi" ? computeAQI(latest.pm25) : latest[metric];
    const color = colorScale(metric === "aqi" ? value : computeAQI(value));
    const radius = Math.max(12, Math.min(40, metric === "aqi" ? value / 3 : value));

    const marker = L.circleMarker([city.lat, city.lon], {
      radius,
      color,
      weight: 1,
      fillOpacity: 0.7,
      bubblingMouseEvents: false
    }).bindPopup(
      `<strong>${city.name}</strong><br/>${metric.toUpperCase()} ${value}<br/>PM2.5 ${latest.pm25}`
    );

    marker.addTo(cityLayer);
  });

  drawInterpolation();
}

function drawInterpolation() {
  const bounds = map.getBounds();
  const grid = [];
  const steps = 14;
  for (let i = 0; i <= steps; i++) {
    for (let j = 0; j <= steps; j++) {
      const lat = bounds.getSouth() + ((bounds.getNorth() - bounds.getSouth()) * i) / steps;
      const lon = bounds.getWest() + ((bounds.getEast() - bounds.getWest()) * j) / steps;
      grid.push({ lat, lon });
    }
  }

  const cityPoints = data.cities.map(city => {
    const latest = city.records[city.records.length - 1];
    return { ...city, aqi: computeAQI(latest.pm25) };
  });

  const heatValues = grid.map(point => {
    const weighted = cityPoints.map(c => {
      const dist = Math.sqrt((c.lat - point.lat) ** 2 + (c.lon - point.lon) ** 2);
      return { weight: 1 / Math.max(dist, 0.2), value: c.aqi };
    });
    const numerator = weighted.reduce((sum, w) => sum + w.weight * w.value, 0);
    const denom = weighted.reduce((sum, w) => sum + w.weight, 0);
    return { ...point, value: numerator / denom };
  });

  const svgOverlay = d3.select(map.getPanes().overlayPane).select("svg#interpolation");
  const svg = svgOverlay.empty()
    ? d3.select(map.getPanes().overlayPane).append("svg").attr("id", "interpolation")
    : svgOverlay;
  const g = svg.select("g").empty() ? svg.append("g").attr("class", "leaflet-zoom-hide") : svg.select("g");

  const project = coord => map.latLngToLayerPoint([coord.lat, coord.lon]);
  const projected = heatValues.map(d => ({ ...project(d), value: d.value }));
  const [[x0, y0], [x1, y1]] = d3.extent(projected, d => [d.x, d.y]);
  svg.attr("width", x1 - x0 + 40).attr("height", y1 - y0 + 40).style("left", `${x0 - 20}px`).style("top", `${y0 - 20}px`);
  g.attr("transform", `translate(${-x0 + 20},${-y0 + 20})`);

  const rects = g.selectAll("rect").data(projected);
  rects
    .join("rect")
    .attr("x", d => d.x - 10)
    .attr("y", d => d.y - 10)
    .attr("width", 20)
    .attr("height", 20)
    .attr("fill", d => colorScale(d.value))
    .attr("opacity", 0.35);
}

function drawLegend() {
  const legend = document.getElementById("legend");
  legend.innerHTML = "";
  colorScale.range().forEach((color, i) => {
    const swatch = document.createElement("div");
    swatch.className = "swatch";
    swatch.style.background = color;
    const label = document.createElement("span");
    label.textContent = i === 0 ? "0-50" : `${colorScale.domain()[i - 1]}+`;
    const wrapper = document.createElement("div");
    wrapper.style.display = "flex";
    wrapper.style.gap = "6px";
    wrapper.style.alignItems = "center";
    wrapper.appendChild(swatch);
    wrapper.appendChild(label);
    legend.appendChild(wrapper);
  });
}

function getSelectedCity() {
  const name = document.getElementById("citySelect").value;
  return data.cities.find(c => c.name === name);
}

function drawTimeSeries() {
  const city = getSelectedCity();
  const metric = document.getElementById("metricSelect").value;
  const svg = d3.select("#timeSeries");
  svg.selectAll("*").remove();

  const margin = { top: 16, right: 16, bottom: 40, left: 44 };
  const width = svg.node().clientWidth || 600;
  const height = svg.node().clientHeight || 280;
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const parsed = city.records.map(r => ({ ...r, date: new Date(r.date), aqi: computeAQI(r.pm25) }));
  const yMetric = metric === "aqi" ? "aqi" : metric;

  const x = d3.scaleTime().domain(d3.extent(parsed, d => d.date)).range([0, innerWidth]);
  const y = d3
    .scaleLinear()
    .domain([0, d3.max(parsed, d => (yMetric === "aqi" ? d[yMetric] : d[yMetric] * 1.2))])
    .nice()
    .range([innerHeight, 0]);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.append("g").call(d3.axisLeft(y).ticks(5)).selectAll("text").attr("fill", "#9ca3af");
  g.append("g")
    .attr("transform", `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).ticks(5))
    .selectAll("text")
    .attr("fill", "#9ca3af");

  const line = d3
    .line()
    .x(d => x(d.date))
    .y(d => y(d[yMetric]))
    .curve(d3.curveCatmullRom.alpha(0.8));

  g.append("path")
    .datum(parsed)
    .attr("fill", "none")
    .attr("stroke", "#00c2ff")
    .attr("stroke-width", 3)
    .attr("d", line);

  const brush = d3
    .brushX()
    .extent([
      [0, 0],
      [innerWidth, innerHeight]
    ])
    .on("brush end", ({ selection }) => {
      if (!selection) return;
      const [x0, x1] = selection.map(x.invert);
      const filtered = parsed.filter(d => d.date >= x0 && d.date <= x1);
      drawComposition(filtered[filtered.length - 1] ? filtered[filtered.length - 1].date : null);
    });

  g.append("g").call(brush);
}

function populateEvents() {
  const strip = document.getElementById("eventStrip");
  strip.innerHTML = "";
  data.events.forEach(evt => {
    const badge = document.createElement("div");
    badge.className = "event-badge";
    badge.textContent = `${evt.date}: ${evt.label}`;
    strip.appendChild(badge);
  });
}

function drawComposition(focusDate = null) {
  const city = getSelectedCity();
  const latest = focusDate
    ? city.records.find(r => new Date(r.date).getTime() === new Date(focusDate).getTime())
    : city.records[city.records.length - 1];
  const values = pollutants.map(p => ({ key: p.key, label: p.label, value: latest[p.key] }));

  drawStackedBar(values, city.name, latest.date);
  drawRadar(values, city.name, latest.date);
}

function drawStackedBar(values, cityName, date) {
  const svg = d3.select("#stackedBar");
  svg.selectAll("*").remove();
  const margin = { top: 20, right: 12, bottom: 40, left: 60 };
  const width = svg.node().clientWidth || 320;
  const height = svg.node().clientHeight || 260;
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const x = d3.scaleBand().domain([cityName]).range([0, innerWidth]).padding(0.4);
  const y = d3.scaleLinear().domain([0, d3.sum(values, d => d.value) * 1.2]).range([innerHeight, 0]);
  const color = d3.scaleOrdinal().domain(values.map(d => d.key)).range(["#00c2ff", "#f7d046", "#f08c42", "#d64045"]);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  let cumulative = 0;
  values.forEach(v => {
    g.append("rect")
      .attr("x", x(cityName))
      .attr("y", y(cumulative + v.value))
      .attr("width", x.bandwidth())
      .attr("height", y(cumulative) - y(cumulative + v.value))
      .attr("fill", color(v.key))
      .append("title")
      .text(`${v.label}: ${v.value}`);
    cumulative += v.value;
  });

  g.append("g").call(d3.axisLeft(y).ticks(5)).selectAll("text").attr("fill", "#9ca3af");
  g.append("g")
    .attr("transform", `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x))
    .selectAll("text")
    .attr("fill", "#9ca3af");

  g.append("text")
    .attr("x", innerWidth / 2)
    .attr("y", -6)
    .attr("fill", "#e5e7eb")
    .attr("text-anchor", "middle")
    .text(`${cityName} composition on ${date}`);
}

function drawRadar(values, cityName, date) {
  const svg = d3.select("#radarChart");
  svg.selectAll("*").remove();
  const width = svg.node().clientWidth || 320;
  const height = svg.node().clientHeight || 260;
  const radius = Math.min(width, height) / 2 - 30;
  const center = { x: width / 2, y: height / 2 };
  const maxValue = d3.max(values, d => d.value) * 1.2;

  const angleSlice = (Math.PI * 2) / values.length;

  const g = svg.append("g").attr("transform", `translate(${center.x},${center.y})`);

  const levels = 4;
  d3.range(1, levels + 1).forEach(lvl => {
    const r = (radius / levels) * lvl;
    g.append("circle")
      .attr("r", r)
      .attr("fill", "none")
      .attr("stroke", "#1f2937")
      .attr("stroke-dasharray", "3,3");
  });

  values.forEach((v, i) => {
    const angle = i * angleSlice - Math.PI / 2;
    const x = Math.cos(angle) * (radius + 12);
    const y = Math.sin(angle) * (radius + 12);
    g.append("text")
      .attr("x", x)
      .attr("y", y)
      .attr("fill", "#9ca3af")
      .attr("text-anchor", "middle")
      .attr("font-size", 12)
      .text(v.label);
  });

  const line = d3
    .lineRadial()
    .radius(d => (d.value / maxValue) * radius)
    .angle((_, i) => i * angleSlice)
    .curve(d3.curveLinearClosed);

  g.append("path")
    .datum(values)
    .attr("d", line)
    .attr("fill", "rgba(0, 194, 255, 0.2)")
    .attr("stroke", "#00c2ff")
    .attr("stroke-width", 2);

  g.append("text")
    .attr("y", radius + 30)
    .attr("fill", "#e5e7eb")
    .attr("text-anchor", "middle")
    .text(`${cityName} proportions on ${date}`);
}

function toggleAnimation() {
  const button = document.getElementById("playButton");
  const playing = button.dataset.playing === "true";
  if (playing) {
    clearInterval(timelineInterval);
    button.dataset.playing = "false";
    button.textContent = "Play";
    return;
  }

  const records = data.cities[0].records;
  let idx = 0;
  button.dataset.playing = "true";
  button.textContent = "Pause";
  timelineInterval = setInterval(() => {
    if (idx >= records.length) {
      clearInterval(timelineInterval);
      button.dataset.playing = "false";
      button.textContent = "Play";
      return;
    }
    drawComposition(records[idx].date);
    idx += 1;
  }, 1600);
}

document.addEventListener("DOMContentLoaded", loadData);
