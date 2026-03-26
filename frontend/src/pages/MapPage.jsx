import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, useMapEvents } from "react-leaflet";
import proj4 from "proj4";
import "leaflet/dist/leaflet.css";
import "./MapPage.css";

const API_BASE = "http://127.0.0.1:8000/api";

proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");
proj4.defs(
  "EPSG:3346",
  "+proj=tmerc +lat_0=0 +lon_0=24 +k=0.9998 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs"
);

function MapWatcher({ onViewportChange, onMouseMove }) {
  useMapEvents({
    moveend(e) {
      onViewportChange(e.target);
    },
    zoomend(e) {
      onViewportChange(e.target);
    },
    mousemove(e) {
      onMouseMove(e.latlng);
    },
  });

  return null;
}

export default function MapPage() {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [featureCount, setFeatureCount] = useState(0);
  const [currentLayer, setCurrentLayer] = useState("coarse");
  const [coords, setCoords] = useState(null);

  const [weights, setWeights] = useState({
    restrictions: 40,
    soil: 30,
    road: 30,
  });

  const [top3, setTop3] = useState([]);

  const debounceRef = useRef(null);
  const lastRequestKeyRef = useRef("");
  const mapRef = useRef(null);

  const styleFeature = useCallback((feature) => {
    const score = feature?.properties?.final_score ?? 0;
    let fillColor;

    if (score > 0.8) fillColor = "#245a43";
    else if (score >= 0.6) fillColor = "#5d9d78";
    else if (score >= 0.4) fillColor = "#d8b94c";
    else if (score >= 0.2) fillColor = "#cf8646";
    else fillColor = "#b85454";

    return {
      color: "#ffffff",
      weight: 0.3,
      fillColor,
      fillOpacity: 0.72,
    };
  }, []);

  const getLayerName = (layer) => {
    if (layer === "coarse") return "Abstraktus rodymas";
    if (layer === "detail") return "Detalus rodymas";
    return "-";
  };

  const format = (v) => (v != null ? Number(v).toFixed(2) : "-");

  const getIndexRating = (v) => {
    if (v >= 0.9) return "Puiku ★★★★★";
    if (v >= 0.7) return "Gerai ★★★★☆";
    if (v >= 0.5) return "Vidutiniškai ★★★☆☆";
    if (v >= 0.3) return "Blogai ★★☆☆☆";
    return "Labai blogai ★☆☆☆☆";
  };

  const getForestRating = (v) => {
    if (v >= 0.9) return "Labai daug miško ★★★★★";
    if (v >= 0.7) return "Daug miško ★★★★☆";
    if (v >= 0.5) return "Vidutiniškai daug miško ★★★☆☆";
    if (v >= 0.3) return "Mažai miško ★★☆☆☆";
    return "Labai mažai miško ★☆☆☆☆";
  };

  const getRestrictionsRating = (v) => {
    if (v === 1) return "Nėra ribojimų ★★★★★";
    if (v >= 0.9) return "Labai maži ribojimai ★★★★⯪";
    if (v >= 0.7) return "Maži ribojimai ★★★★☆";
    if (v >= 0.5) return "Vidutiniai ribojimai ★★★☆☆";
    if (v >= 0.3) return "Dideli ribojimai ★★☆☆☆";
    return "Labai dideli ribojimai ★☆☆☆☆";
  };

  const getSoilRating = (v) => {
    if (v >= 0.9) return "puikūs ★★★★⯪";
    if (v >= 0.7) return "labai geri ★★★★☆";
    if (v >= 0.5) return "vidutiniški ★★★☆☆";
    if (v >= 0.3) return "prasti ★★☆☆☆";
    return "labai blogi ★☆☆☆☆";
  };

  const getRoadRating = (v) => {
    if (v >= 0.9) return "puikus ★★★★⯪";
    if (v >= 0.7) return "labai geras ★★★★☆";
    if (v >= 0.5) return "vidutiniškas ★★★☆☆";
    if (v >= 0.3) return "prastas ★★☆☆☆";
    return "labai blogas ★☆☆☆☆";
  };

  const onEachFeature = useCallback((feature, layer) => {
    const p = feature.properties || {};

    const finalScore = p.final_score ?? null;
    const forest = p.forest_pct ?? null;
    const restrictions = p.restrictions_index ?? null;
    const soil = p.soil_index ?? null;
    const road = p.road_score ?? null;

    layer.bindPopup(`
      <b>${getLayerName(p.layer)}</b><br/><br/>
      <b>Investicinis indeksas:</b> ${format(finalScore)}<br/>
      ${finalScore != null ? getIndexRating(finalScore) : "-"}<br/><br/>

      <b>Miško dalis pateiktame plote:</b> ${forest != null ? (forest * 100).toFixed(2) + "%" : "-"
      }<br/>
      ${forest != null ? getForestRating(forest) : "-"}<br/><br/>

      <b>Miško veiklos ribojimų indeksas:</b> ${format(restrictions)}<br/>
      ${restrictions != null ? getRestrictionsRating(restrictions) : "-"}<br/><br/>

      <b>Dirvožemio indeksas:</b> ${format(soil)}<br/>
      Dirvožemio rodikliai ${soil != null ? getSoilRating(soil) : "-"}<br/><br/>

      <b>Kelių indeksas:</b> ${format(road)}<br/>
      Susisiekimas ${road != null ? getRoadRating(road) : "-"}
    `);
  }, []);

  const fetchGrid = async (layer, bbox, currentWeights) => {
    const params = new URLSearchParams({
      layer,
      bbox,
      w_restr: String(currentWeights.restrictions),
      w_soil: String(currentWeights.soil),
      w_road: String(currentWeights.road),
    });
    const res = await fetch(`${API_BASE}/grid?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  };

  const fetchLayerData = useCallback(async (map, currentWeights) => {
    const zoom = map.getZoom();
    const bounds = map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    const [minx, miny] = proj4("EPSG:4326", "EPSG:3346", [sw.lng, sw.lat]);
    const [maxx, maxy] = proj4("EPSG:4326", "EPSG:3346", [ne.lng, ne.lat]);
    const bbox = `${minx},${miny},${maxx},${maxy}`;
    const preferredLayer = zoom >= 10 ? "detail" : "coarse";
    const requestKey = `${preferredLayer}|${bbox}|${currentWeights.restrictions}|${currentWeights.soil}|${currentWeights.road}`;

    if (requestKey === lastRequestKeyRef.current) return;
    lastRequestKeyRef.current = requestKey;

    setLoading(true);

    try {
      let data = await fetchGrid(preferredLayer, bbox, currentWeights);
      let usedLayer = preferredLayer;

      if (preferredLayer === "detail" && (!data.features || data.features.length === 0)) {
        data = await fetchGrid("coarse", bbox, currentWeights);
        usedLayer = "coarse";
      }

      setGeoData(data);
      setFeatureCount(data?.features?.length || 0);
      setCurrentLayer(usedLayer);

      if (data?.features?.length) {
        const sorted = [...data.features]
          .filter((f) => f.properties?.final_score != null)
          .sort((a, b) => b.properties.final_score - a.properties.final_score)
          .slice(0, 3)
          .map((f, index) => ({
            rank: index + 1,
            score: f.properties.final_score,
            layer: f.properties.layer,
          }));

        setTop3(sorted);
      } else {
        setTop3([]);
      }
    } catch (err) {
      console.error("Fetch klaida:", err);
      setGeoData(null);
      setFeatureCount(0);
      setTop3([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleViewportChange = useCallback((map) => {
    mapRef.current = map;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchLayerData(map, weights);
    }, 250);
  }, [fetchLayerData, weights]);

  const handleMouseMove = (latlng) => setCoords(latlng);

  const applyWeightChange = (field, rawValue) => {
    let newValue = Number(rawValue);

    if (Number.isNaN(newValue)) newValue = 0;
    if (newValue < 0) newValue = 0;
    if (newValue > 100) newValue = 100;

    setWeights((prev) => {
      const otherSum =
        prev.restrictions + prev.soil + prev.road - prev[field];

      const allowedValue = Math.min(newValue, 100 - otherSum);

      return {
        ...prev,
        [field]: allowedValue < 0 ? 0 : allowedValue,
      };
    });
  };

  useEffect(() => {
    if (!mapRef.current) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      fetchLayerData(mapRef.current, weights);
    }, 300);
  }, [weights, fetchLayerData]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const weightSum = weights.restrictions + weights.soil + weights.road;

  const weightLabels = {
    restrictions: "Ribojimai",
    soil: "Dirvožemis",
    road: "Keliai",
  };

  return (
    <div className="content">
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
                    key={`${currentLayer}-${featureCount}-${weights.restrictions}-${weights.soil}-${weights.road}`}
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
                <span className="legend-score">0.8–1.0</span>
              </div>

              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box light-green" />
                  <span>Gerai</span>
                </div>
                <span className="legend-score">0.6–0.8</span>
              </div>

              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box yellow" />
                  <span>Vidutiniškai</span>
                </div>
                <span className="legend-score">0.4–0.6</span>
              </div>

              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box orange" />
                  <span>Blogai</span>
                </div>
                <span className="legend-score">0.2–0.4</span>
              </div>

              <div className="legend-row">
                <div className="legend-left">
                  <span className="legend-box red" />
                  <span>Labai blogai</span>
                </div>
                <span className="legend-score">0.0–0.2</span>
              </div>
            </div>
          </div>

          <div className="card status-card">
            <h3>Būsena</h3>
            <div className="status-main">
              {loading ? "Kraunama duomenų ištrauka..." : "Duomenys paruošti peržiūrai"}
            </div>
            <div className="status-sub">
              <span className="status-tag">{getLayerName(currentLayer)}</span>
              <span className="status-tag">Objektų kiekis: {featureCount}</span>
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
                    onChange={(e) => applyWeightChange(field, e.target.value)}
                  />

                  <input
                    className="weight-number"
                    type="number"
                    min="0"
                    max="100"
                    value={weights[field]}
                    onChange={(e) => applyWeightChange(field, e.target.value)}
                  />
                </div>
              </div>
            ))}

            <div className="weight-sum">
              Svorių suma: <strong>{weightSum}</strong> / 100
            </div>

            <div className="weight-note">
              Jei bandysi įvesti per didelę reikšmę, ji bus automatiškai apribota,
              kad bendra suma neviršytų 100. Celės su mažesne nei 20 % miško dalimi
              nerodomos.
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
                        {item.rank} vieta · {getLayerName(item.layer)}
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