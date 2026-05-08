import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { GeoJSON, MapContainer, Polygon, TileLayer, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import PageTopbar from "../components/PageTopbar";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { buildFeaturePopupContent, getLayerName } from "../features/map/formatters";
import { LITHUANIA_BOUNDARY_GEOJSON, LITHUANIA_MASK_RINGS } from "../features/map/lithuaniaBoundary";
import { useMapData } from "../features/map/useMapData";
import "./MapPage.css";

const COUNTY_BOUNDS = {
  "alytaus apskritis": [[53.86, 23.45], [54.82, 25.25]],
  "kauno apskritis": [[54.52, 22.78], [55.58, 25.05]],
  "klaipėdos apskritis": [[55.17, 20.86], [56.45, 22.38]],
  "klaipedos apskritis": [[55.17, 20.86], [56.45, 22.38]],
  "marijampolės apskritis": [[54.20, 22.50], [55.13, 23.78]],
  "marijampoles apskritis": [[54.20, 22.50], [55.13, 23.78]],
  "panevėžio apskritis": [[55.34, 23.45], [56.45, 25.60]],
  "panevezio apskritis": [[55.34, 23.45], [56.45, 25.60]],
  "šiaulių apskritis": [[55.55, 22.30], [56.48, 24.45]],
  "siauliu apskritis": [[55.55, 22.30], [56.48, 24.45]],
  "tauragės apskritis": [[55.00, 21.55], [56.05, 23.35]],
  "taurages apskritis": [[55.00, 21.55], [56.05, 23.35]],
  "telšių apskritis": [[55.65, 21.25], [56.45, 22.95]],
  "telsiu apskritis": [[55.65, 21.25], [56.45, 22.95]],
  "utenos apskritis": [[55.05, 24.55], [56.45, 26.85]],
  "vilniaus apskritis": [[54.05, 24.35], [55.55, 26.95]],
};

const LITHUANIA_BOUNDS = [[53.85, 20.75], [56.45, 26.95]];

function normalizeCountyName(county) {
  return county.trim().toLowerCase();
}

function getFeatureId(feature) {
  return feature?.id ?? feature?.properties?.id ?? null;
}

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

function InitialZoom({ selectedCounty, onViewportChange }) {
  const map = useMap();

  useEffect(() => {
    const bounds = COUNTY_BOUNDS[normalizeCountyName(selectedCounty || "")] || LITHUANIA_BOUNDS;

    const timeoutId = window.setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(bounds, {
        animate: false,
        padding: [18, 18],
      });
      onViewportChange(map);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [map, onViewportChange, selectedCounty]);

  return null;
}

function MapResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      map.invalidateSize();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [map]);

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

function MapContent({ geoData, styleFeature, onEachFeature, handleViewportChange, handleMouseMove, coords, mapDataLoading, currentLayer, featureCount, selectedCounty, dataVersion, t }) {
  return (
    <>
      <MapWatcher
        onViewportChange={handleViewportChange}
        onMouseMove={handleMouseMove}
      />
      <InitialZoom
        selectedCounty={selectedCounty}
        onViewportChange={handleViewportChange}
      />
      <MapResizeHandler />
      <Polygon
        positions={LITHUANIA_MASK_RINGS}
        pathOptions={{
          color: "transparent",
          fillColor: "#eef3ee",
          fillOpacity: 0.72,
          interactive: false,
        }}
      />
      <GeoJSON
        data={LITHUANIA_BOUNDARY_GEOJSON}
        style={() => ({
          color: "#1f6b48",
          weight: 2.5,
          fillOpacity: 0,
          dashArray: "6 6",
          interactive: false,
        })}
      />
      {geoData?.features?.length > 0 && (
        <GeoJSON
          key={`${currentLayer}-${featureCount}-${selectedCounty}-${dataVersion}`}
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
      {mapDataLoading && (
        <div className="loading">
          {t("mapLoading")}
        </div>
      )}
    </>
  );
}

export default function MapPage() {
  const { isAuthenticated, hasActivePlan, loading: authLoading } = useAuth();
  const { t } = useLanguage();
  const [searchParams] = useSearchParams();
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [weights, setWeights] = useState({
    restrictions: 40,
    soil: 30,
    road: 30,
  });
  const [weightInputs, setWeightInputs] = useState({
    restrictions: "40",
    soil: "30",
    road: "30",
  });

  const selectedCounty = searchParams.get("county") || "";
  const {
    coords,
    currentLayer,
    dataVersion,
    featureCount,
    geoData,
    handleMouseMove,
    handleViewportChange,
    loading: mapDataLoading,
    top3,
  } = useMapData(weights, selectedCounty);

  const mapRef = useRef(null);
  const featureLayerRef = useRef(new WeakMap());
  const featureLayerByIdRef = useRef(new Map());

  const styleFeature = useCallback(
    (feature) => getFeatureStyle(feature, hoveredFeature, selectedFeature),
    [hoveredFeature, selectedFeature]
  );

  const onEachFeature = useCallback((feature, layer) => {
    featureLayerRef.current.set(feature, layer);
    const featureId = getFeatureId(feature);
    if (featureId != null) {
      featureLayerByIdRef.current.set(String(featureId), layer);
    }

    layer.on({
      mouseover: () => setHoveredFeature(feature),
      mouseout: () => setHoveredFeature(null),
      click: (event) => {
        setSelectedFeature(feature);
        event.originalEvent?.stopPropagation();
        layer.openPopup(event.latlng);
      },
    });

    layer.bindPopup(buildFeaturePopupContent(feature.properties || {}), {
      autoClose: false,
      closeOnClick: false,
      autoPan: false,
      keepInView: false,
    });
  }, []);

  const applyWeightChange = (field, rawValue, syncInput = true) => {
    let newValue = Number(rawValue);

    if (Number.isNaN(newValue)) newValue = 0;
    if (newValue < 0) newValue = 0;
    if (newValue > 100) newValue = 100;

    setWeights((previous) => {
      const otherSum =
        previous.restrictions + previous.soil + previous.road - previous[field];
      const allowedValue = Math.min(newValue, 100 - otherSum);
      const nextValue = allowedValue < 0 ? 0 : allowedValue;

      if (syncInput) {
        setWeightInputs((current) => ({
          ...current,
          [field]: String(nextValue),
        }));
      }

      return {
        ...previous,
        [field]: nextValue,
      };
    });
  };

  const handleWeightInputChange = (field, rawValue) => {
    if (!/^\d{0,3}$/.test(rawValue)) return;

    setWeightInputs((current) => ({
      ...current,
      [field]: rawValue,
    }));

    if (rawValue !== "") {
      applyWeightChange(field, rawValue);
    }
  };

  const handleWeightInputBlur = (field) => {
    if (weightInputs[field] === "") {
      applyWeightChange(field, 0);
    } else {
      setWeightInputs((current) => ({
        ...current,
        [field]: String(weights[field]),
      }));
    }
  };

  const openFeaturePopup = useCallback((feature) => {
    if (!feature || !mapRef.current) return;

    const featureId = getFeatureId(feature);
    const layer =
      featureLayerRef.current.get(feature) ||
      (featureId != null ? featureLayerByIdRef.current.get(String(featureId)) : null);
    if (!layer?.openPopup) return;

    const latlng = layer.getBounds ? layer.getBounds().getCenter() : undefined;
    layer.openPopup(latlng);
  }, []);

  useEffect(() => {
    if (!selectedFeature) return undefined;

    const timeoutId = window.setTimeout(() => {
      openFeaturePopup(selectedFeature);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [openFeaturePopup, selectedFeature]);

  const handleTop3Click = useCallback((item) => {
    const feature = item.feature;

    if (!feature) {
      return;
    }

    setSelectedFeature(feature);

    window.setTimeout(() => {
      openFeaturePopup(feature);
    }, 0);
  }, [openFeaturePopup]);

  if (authLoading) {
    return <div className="loading">{t("mapAccessCheck")}</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!hasActivePlan) {
    return <Navigate to="/" replace />;
  }

  const weightSum = weights.restrictions + weights.soil + weights.road;
  const weightLabels = {
    restrictions: t("restrictions"),
    soil: t("soil"),
    road: t("roads"),
  };

  return (
    <div className="content">
      <PageTopbar />

      <div className="layout">
        <div className="map-column">
          <div className="map-shell">
            <div className="map-container" style={{ position: "relative" }}>
              <MapContainer
                ref={mapRef}
                center={[55.2, 23.9]}
                zoom={7}
                minZoom={6}
                closePopupOnClick={false}
                preferCanvas
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  attribution="© OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapContent
                  geoData={geoData}
                  styleFeature={styleFeature}
                  onEachFeature={onEachFeature}
                  handleViewportChange={handleViewportChange}
                  handleMouseMove={handleMouseMove}
                  coords={coords}
                  mapDataLoading={mapDataLoading}
                  currentLayer={currentLayer}
                  featureCount={featureCount}
                  selectedCounty={selectedCounty}
                  dataVersion={dataVersion}
                  t={t}
                />
              </MapContainer>
            </div>

            <div className="card legend-card">
              <h3>{t("legend")}</h3>
              <div className="legend">
                {[
                  ["green", t("excellent"), "0.8-1.0"],
                  ["light-green", t("good"), "0.6-0.8"],
                  ["yellow", t("average"), "0.4-0.6"],
                  ["orange", t("bad"), "0.2-0.4"],
                  ["red", t("veryBad"), "0.0-0.2"],
                ].map(([className, label, score]) => (
                  <div className="legend-row" key={className}>
                    <div className="legend-left">
                      <span className={`legend-box ${className}`} />
                      <span>{label}</span>
                    </div>
                    <span className="legend-score">{score}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="info-column">
          <div className="card status-card">
            <h3>{t("status")}</h3>
            <div className="status-main">
              {mapDataLoading ? t("dataLoadingShort") : t("dataReady")}
            </div>
            <div className="status-sub">
              <span className="status-tag">{getLayerName(currentLayer)}</span>
              <span className="status-tag">{t("objectCount")}: {featureCount}</span>
              {selectedCounty && <span className="status-tag">{selectedCounty}</span>}
            </div>
          </div>

          <div className="card weights-panel">
            <h3>{t("userWeights")}</h3>
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
                    value={weightInputs[field]}
                    onChange={(event) => handleWeightInputChange(field, event.target.value)}
                    onBlur={() => handleWeightInputBlur(field)}
                  />
                </div>
              </div>
            ))}

            <div className="weight-sum">
              {t("weightsSum")}: <strong>{weightSum}</strong> / 100
            </div>

            <div className="weight-note">{t("weightsNote")}</div>
          </div>

          <div className="card top3-panel">
            <h3>{t("top3")}</h3>
            {top3.length === 0 ? (
              <div className="top3-score">{t("noTop3")}</div>
            ) : (
              <div className="top3-list">
                {top3.map((item) => (
                  <div className="top3-item" key={item.rank}>
                    <div className="top3-rank">{item.rank}</div>
                    <div className="top3-content">
                      <div className="top3-title">
                        {item.rank} {t("rank")} - {item.forestType}, {item.municipality}, {item.county}
                      </div>
                      <div className="top3-score">
                        {t("index")}: <strong>{item.score.toFixed(2)}</strong>
                      </div>
                      <button
                        className="top3-btn"
                        onClick={() => handleTop3Click(item)}
                      >
                        {t("openOnMap")}
                      </button>
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
