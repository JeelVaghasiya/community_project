/**
 * Urban Flood Risk Platform - Leaflet Frontend Logic
 * Pilot Area: Central Silk Board Junction, Bengaluru
 */

// Central Silk Board Junction coordinates
const BENGALURU_PILOT = [12.9172, 77.6228];
const DEFAULT_ZOOM = 15;

let map;
let hazardLayerGroup;
let observationMarkersGroup;
let activeScenario = "100mmhr";
let selectedObservation = null;
let observationsMap = new Map();

// Initialize the map and event bindings
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  setupEventListeners();
  loadHazardLayer(activeScenario);
  pollObservations();
  setInterval(pollObservations, 3000); // 3-second auto-poll
});

function initMap() {
  map = L.map("map", {
    zoomControl: false,
  }).setView(BENGALURU_PILOT, DEFAULT_ZOOM);

  L.control.zoom({ position: "topright" }).addTo(map);

  // Standard free OpenStreetMap tile layer (requires no API key)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  hazardLayerGroup = L.layerGroup().addTo(map);
  observationMarkersGroup = L.layerGroup().addTo(map);
}

function setupEventListeners() {
  const scenarioSelect = document.getElementById("scenario-select");
  if (scenarioSelect) {
    scenarioSelect.addEventListener("change", (e) => {
      activeScenario = e.target.value;
      loadHazardLayer(activeScenario);
    });
  }

  const btnClose = document.getElementById("btn-close-panel");
  if (btnClose) {
    btnClose.addEventListener("click", () => {
      document.getElementById("panel-empty-state").style.display = "flex";
      document.getElementById("panel-content-state").style.display = "none";
    });
  }

  const btnSimulate = document.getElementById("btn-quick-simulate");
  if (btnSimulate) {
    btnSimulate.addEventListener("click", triggerQuickSimulation);
  }

  const btnCopy = document.getElementById("btn-copy-json");
  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      const code = document.getElementById("detail-json-block").innerText;
      navigator.clipboard.writeText(code).then(() => {
        btnCopy.innerText = "Copied!";
        setTimeout(() => (btnCopy.innerText = "Copy"), 1500);
      });
    });
  }
}

// -------------------------------------------------------------
// Hazard Layer Rendering
// -------------------------------------------------------------
async function loadHazardLayer(scenario) {
  try {
    const res = await fetch(`/risk/${scenario}`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const geojson = await res.json();

    hazardLayerGroup.clearLayers();

    L.geoJSON(geojson, {
      style: (feature) => {
        const risk = feature.properties ? feature.properties.risk_score || 0 : 0;
        let fillColor = "#38bdf8"; // Light cyan for low risk
        if (risk >= 0.8) fillColor = "#dc2626"; // Deep Red
        else if (risk >= 0.6) fillColor = "#ea580c"; // Orange
        else if (risk >= 0.4) fillColor = "#eab308"; // Amber

        return {
          color: fillColor,
          weight: 2,
          opacity: 0.8,
          fillColor: fillColor,
          fillOpacity: 0.35,
          dashArray: "4, 4",
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        layer.bindPopup(`
          <div style="font-family: Inter, sans-serif; font-size: 13px;">
            <strong>${p.name || "Hazard Zone"}</strong><br/>
            <span>Scenario: ${p.rainfall_scenario || scenario}</span><br/>
            <span>Risk Score: <strong>${p.risk_score}</strong></span><br/>
            <small style="color:#6b7280;">Drain status: ${p.assumed_drain_status || "assumed"}</small>
          </div>
        `);
      },
    }).addTo(hazardLayerGroup);
  } catch (err) {
    console.error("Failed to load hazard layer:", err);
  }
}

// -------------------------------------------------------------
// Live Observations Polling & Markers
// -------------------------------------------------------------
async function pollObservations() {
  try {
    const res = await fetch("/observations");
    if (!res.ok) return;
    const observations = await res.json();

    updateStats(observations);
    renderMarkers(observations);
  } catch (err) {
    console.error("Error polling observations:", err);
  }
}

function updateStats(observations) {
  const total = observations.length;
  let hotspots = 0;
  let gaps = 0;

  observations.forEach((obs) => {
    if (obs.map_colour === "red") hotspots++;
    if (obs.map_colour === "purple") gaps++;
  });

  const totalEl = document.getElementById("stat-total-obs");
  const hotspotsEl = document.getElementById("stat-hotspots");
  const gapsEl = document.getElementById("stat-gaps");

  if (totalEl) totalEl.innerText = total;
  if (hotspotsEl) hotspotsEl.innerText = hotspots;
  if (gapsEl) gapsEl.innerText = gaps;
}

function getMarkerColorHex(colourName) {
  switch (colourName) {
    case "red":
      return "#ef4444";
    case "orange":
      return "#f97316";
    case "purple":
      return "#a855f7";
    case "green":
      return "#22c55e";
    default:
      return "#3b82f6";
  }
}

function renderMarkers(observations) {
  observationMarkersGroup.clearLayers();

  observations.forEach((obs) => {
    const colorHex = getMarkerColorHex(obs.map_colour);

    const marker = L.circleMarker([obs.lat, obs.lon], {
      radius: 9,
      fillColor: colorHex,
      color: "#ffffff",
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9,
      className: "custom-circle-marker",
    });

    marker.bindTooltip(
      `<strong>${obs.camera_id}</strong><br/>${obs.fusion_status}`,
      { direction: "top", offset: [0, -10] }
    );

    marker.on("click", () => {
      showObservationDetails(obs);
    });

    marker.addTo(observationMarkersGroup);
  });
}

// -------------------------------------------------------------
// Side Panel Inspector Logic
// -------------------------------------------------------------
function showObservationDetails(obs) {
  selectedObservation = obs;

  const emptyState = document.getElementById("panel-empty-state");
  const contentState = document.getElementById("panel-content-state");
  emptyState.style.display = "none";
  contentState.style.display = "block";

  // Status Banner
  const banner = document.getElementById("detail-status-banner");
  banner.className = `status-banner ${obs.map_colour}`;
  document.getElementById("detail-status-text").innerText = obs.fusion_status;

  // Metadata
  document.getElementById("detail-camera-id").innerText = obs.camera_id;
  document.getElementById("detail-image-id").innerText = obs.image_id;
  document.getElementById(
    "detail-coords"
  ).innerText = `${obs.lat.toFixed(4)}, ${obs.lon.toFixed(4)}`;
  document.getElementById("detail-timestamp").innerText = new Date(
    obs.timestamp
  ).toLocaleTimeString();

  // Fusion Meters
  const riskPct = Math.min(100, Math.round(obs.predicted_risk * 100));
  document.getElementById("detail-risk-val").innerText = obs.predicted_risk.toFixed(2);
  document.getElementById("detail-risk-bar").style.width = `${riskPct}%`;

  // CV metrics
  const cv = obs.cv_output || {};
  const floodedEl = document.getElementById("detail-cv-flooded");
  if (cv.flooded) {
    floodedEl.innerText = `Detected (${cv.water_area_pct}% area)`;
    floodedEl.className = "cv-metric-value text-red";
  } else {
    floodedEl.innerText = "Clear (0.0% water)";
    floodedEl.className = "cv-metric-value text-green";
  }

  document.getElementById("detail-cv-depth").innerText = (
    cv.depth_class || "UNKNOWN"
  ).toUpperCase();
  document.getElementById("detail-cv-conf").innerText = `${(
    (cv.confidence || 0.85) * 100
  ).toFixed(1)}%`;

  // Annotated Image Path
  document.getElementById("detail-annot-path").innerText =
    cv.annotated_image || "outputs/img_annot.png";

  // Raw Contract 1 JSON block
  document.getElementById("detail-json-block").innerText = JSON.stringify(
    cv,
    null,
    2
  );
}

// -------------------------------------------------------------
// Quick Simulation Helper
// -------------------------------------------------------------
async function triggerQuickSimulation() {
  // Generate random coordinate near Central Silk Board
  const latOffset = (Math.random() - 0.5) * 0.007;
  const lonOffset = (Math.random() - 0.5) * 0.007;
  const simLat = 12.9172 + latOffset;
  const simLon = 77.6228 + lonOffset;
  const camNum = Math.floor(Math.random() * 20) + 1;
  const camId = `cam_silkboard_${String(camNum).padStart(2, "0")}`;

  try {
    const res = await fetch("/observations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: simLat,
        lon: simLon,
        camera_id: camId,
        rainfall_scenario: activeScenario,
      }),
    });

    if (res.ok) {
      const newObs = await res.json();
      pollObservations();
      showObservationDetails(newObs);
    }
  } catch (err) {
    console.error("Failed to trigger simulation:", err);
  }
}
