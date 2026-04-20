import { useCallback, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { GeoJSON, MapContainer, TileLayer, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import PageTopbar from "../components/PageTopbar";
import { useAuth } from "../context/AuthContext";
import { buildFeaturePopupContent, getLayerName } from "../features/map/formatters";
import { useMapData } from "../features/map/useMapData";
import "./MapPage.css";

function MapWatcher({ onViewportChange, onMouseMove }) {
  useMapEvents({
    moveend(event) {
      onViewportChange(event.target);
    },
    zoomend(event) {
      onViewportChange(event.target);
    },
    mousemove(event) {
      onMouseMove(event.latlng);
    },
  });

  return null;
}

function getFeatureStyle(feature, hoveredFeature, selectedFeature) {
  const score = feature?.properties?.final_score ?? 0;

  let fillColor = "#b85454";
  if (score > 0.8) fillColor = "#245a43";
  else if (score >= 0.6) fillColor = "#5d9d78";
  else if (score >= 0.4) fillColor = "#d8b94c";
  else if (score >= 0.2) fillColor = "#cf8646";

  let weight = 0.3;
  let fillOpacity = 0.72;

  if (feature === hoveredFeature) {
    weight = 2;
    fillOpacity = 0.8;
  }

  if (feature === selectedFeature) {
    weight = 3;
    fillOpacity = 0.85;
  }

  return {
    color: "#ffffff",
    weight,
    fillColor,
    fillOpacity,
  };
}

export default function MapPage() {
  const { isAuthenticated, hasActivePlan, loading: authLoading } = useAuth(); // Renamed to authLoading
  const [searchParams] = useSearchParams();
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [weights, setWeights] = useState({
    restrictions: 40,
    soil: 30,
    road: 30,
  });

  const selectedCounty = searchParams.get("county") || "";
  const {
    coords,
    currentLayer,
    featureCount,
    geoData,
    handleMouseMove,
    handleViewportChange,
    loading: mapDataLoading, // Renamed to mapDataLoading
    top3,
  } = useMapData(weights, selectedCounty);

  // Check authentication first
  if (authLoading) {
    return <div className="loading">Tikrinama prieiga...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!hasActivePlan) {
    return <Navigate to="/" replace />;
  }

  // Show loading state while map data is being fetched
  if (mapDataLoading) {
    return <div className="loading">Kraunama žemėlapio duomenys...</div>;
  }

  const styleFeature = useCallback(
    (feature) => getFeatureStyle(feature, hoveredFeature, selectedFeature),
    [hoveredFeature, selectedFeature]
  );

  const onEachFeature = useCallback((feature, layer) => {
    layer.on({
      mouseover: () => setHoveredFeature(feature),
      mouseout: () => setHoveredFeature(null),
      click: () => setSelectedFeature(feature),
    });

    layer.bindPopup(buildFeaturePopupContent(feature.properties || {}));
  }, []);

  const applyWeightChange = (field, rawValue) => {
    let newValue = Number(rawValue);

    if (Number.isNaN(newValue)) newValue = 0;
    if (newValue < 0) newValue = 0;
    if (newValue > 100) newValue = 100;

    setWeights((previous) => {
      const otherSum =
        previous.restrictions + previous.soil + previous.road - previous[field];
      const allowedValue = Math.min(newValue, 100 - otherSum);

      return {
        ...previous,
        [field]: allowedValue < 0 ? 0 : allowedValue,
      };
    });
  };

  const weightSum = weights.restrictions + weights.soil + weights.road;
  const weightLabels = {
    restrictions: "Ribojimai",
    soil: "Dirvožemis",
    road: "Keliai",
  };

  return (
    <div className="content">
      <PageTopbar />

      <div className="layout">
        <div className="map-column">
          <div className="map-shell">
            <div className="map-container">
              <MapContainer 
                center={[55.2, 23.9]} 
                zoom={7} 
                minZoom={6} 
                preferCanvas 
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer 
                  attribution="© OpenStreetMap contributors" 
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
                />
                <MapWatcher 
                  onViewportChange={handleViewportChange} 
                  onMouseMove={handleMouseMove} 
                />
                {geoData?.features?.length > 0 && (
                  <GeoJSON
                    key={`${currentLayer}-${featureCount}-${weights.restrictions}-${weights.soil}-${weights.road}-${selectedCounty}`}
                    data={geoData}
                    style={styleFeature}
                    onEachFeature={onEachFeature}
                  />
                )}
                {coords && (
                  <div className="coords-box">
                    {coords.lat.toFixed(5)}, {coords.lng.toFixed(5)}
                  </div>
                )}
              </MapContainer>
            </div>
          </div>
        </div>

        <div className="info-column">
          <div className="card">
            <h3>Legenda</h3>
            <div className="legend">
              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box green" />
                  <span>Puiku</span>
                </div>
                <span className="legend-score">0.8-1.0</span>
              </div>
              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box light-green" />
                  <span>Gerai</span>
                </div>
                <span className="legend-score">0.6-0.8</span>
              </div>
              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box yellow" />
                  <span>Vidutiniškai</span>
                </div>
                <span className="legend-score">0.4-0.6</span>
              </div>
              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box orange" />
                  <span>Blogai</span>
                </div>
                <span className="legend-score">0.2-0.4</span>
              </div>
              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box red" />
                  <span>Labai blogai</span>
                </div>
                <span className="legend-score">0.0-0.2</span>
              </div>
            </div>
          </div>

          <div className="card status-card">
            <h3>Būsena</h3>
            <div className="status-main">
              {mapDataLoading ? "Kraunama duomenų ištrauka..." : "Duomenys paruošti peržiūrai"}
            </div>
            <div className="status-sub">
              <span className="status-tag">{getLayerName(currentLayer)}</span>
              <span className="status-tag">Objektų kiekis: {featureCount}</span>
              {selectedCounty && <span className="status-tag">{selectedCounty}</span>}
            </div>
          </div>

          <div className="card weights-panel">
            <h3>Naudotojo svoriai</h3>
            {["restrictions", "soil", "road"].map((field) => (
              <div key={field} className="weight-block">
                <div className="label-row">
                  <span>{weightLabels[field]}</span>
                </div>
                <div className="weight-input-wrap">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={weights[field]}
                    onChange={(event) => applyWeightChange(field, event.target.value)}
                  />
                  <input
                    className="weight-number"
                    type="number"
                    min="0"
                    max="100"
                    value={weights[field]}
                    onChange={(event) => applyWeightChange(field, event.target.value)}
                  />
                </div>
              </div>
            ))}

            <div className="weight-sum">
              Svorių suma: <strong>{weightSum}</strong> / 100
            </div>

            <div className="weight-note">
              Jei bandysi įvesti per didelę reikšmę, ji bus automatiškai apribota, kad bendra suma neviršytų 100.
              Celės su mažesne nei 20 % miško dalimi nerodomos.
            </div>
          </div>

          <div className="card top3-panel">
            <h3>Top 3 vietos</h3>
            {top3.length === 0 ? (
              <div className="top3-score">Šiuo metu nėra pakankamai duomenų.</div>
            ) : (
              <div className="top3-list">
                {top3.map((item) => (
                  <div className="top3-item" key={item.rank}>
                    <div className="top3-rank">{item.rank}</div>
                    <div>
                      <div className="top3-title">
                        {item.rank} vieta – {getLayerName(item.layer)}
                      </div>
                      <div className="top3-score">
                        Investicinis indeksas: <strong>{item.score.toFixed(2)}</strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}