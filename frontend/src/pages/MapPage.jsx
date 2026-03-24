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

    if (score > 0.8) fillColor = "#1b5e20";
    else if (score >= 0.6) fillColor = "#66bb6a";
    else if (score >= 0.4) fillColor = "#fbc02d";
    else if (score >= 0.2) fillColor = "#ff8f00";
    else fillColor = "#c62828";

    return {
      color: "#ffffff",
      weight: 0.2,
      fillColor,
      fillOpacity: 0.65,
    };
  }, []);

  const getLayerName = (layer) => {
    if (layer === "coarse") return "Abstraktus rodymas";
    if (layer === "detail") return "Detalus rodymas";
    return "-";
  };

  const format = (v) =>
  v != null ? Number(v).toFixed(2) : "-";

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

    <b>Investicinis indeksas:</b> ${format(finalScore)} | 
    ${finalScore != null ? getIndexRating(finalScore) : "-"}<br/><br/>

    <b>Miško dalis pateiktame plote:</b> ${
      forest != null ? (forest * 100).toFixed(2) + "%" : "-"
    } | ${forest != null ? getForestRating(forest) : "-"}<br/><br/>

    <b>Miško veiklos ribojimų indeksas:</b> ${format(restrictions)} | 
    ${restrictions != null ? getRestrictionsRating(restrictions) : "-"}<br/><br/>

    <b>Dirvožemio indeksas:</b> ${format(soil)} | 
    Dirvožemio rodikliai ${soil != null ? getSoilRating(soil) : "-"}<br/><br/>

    <b>Kelių indeksas:</b> ${format(road)} | 
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

      // TOP3 vietos pagal final_score
      if (data?.features?.length) {
        const sorted = [...data.features]
          .filter(f => f.properties?.final_score != null)
          .sort((a, b) => b.properties.final_score - a.properties.final_score)
          .slice(0, 3)
          .map(f => ({
            id: f.properties.cell_local_id,
            score: f.properties.final_score,
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

  const handleWeightChange = (field, value) => {
    const newValue = Number(value);
    setWeights((prev) => {
      const otherSum = prev.restrictions + prev.soil + prev.road - prev[field];
      const allowedValue = Math.min(newValue, 100 - otherSum);
      return { ...prev, [field]: allowedValue };
    });
  };

  useEffect(() => {
    if (!mapRef.current) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchLayerData(mapRef.current, weights), 300);
  }, [weights, fetchLayerData]);

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  const weightSum = weights.restrictions + weights.soil + weights.road;

  return (
    <div className="content">
      <div className="layout">
        <div className="map-column">
          <div className="map-container">
            <MapContainer center={[55.2, 23.9]} zoom={7} minZoom={6} preferCanvas style={{ height: "100%", width: "100%" }}>
              <TileLayer attribution="© OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <MapWatcher onViewportChange={handleViewportChange} onMouseMove={handleMouseMove} />
              {geoData?.features?.length > 0 && (
                <GeoJSON
                  key={`${currentLayer}-${featureCount}-${weights.restrictions}-${weights.soil}-${weights.road}`}
                  data={geoData}
                  style={styleFeature}
                  onEachFeature={onEachFeature}
                />
              )}
              {coords && <div className="coords-box">{coords.lat.toFixed(5)}, {coords.lng.toFixed(5)}</div>}
            </MapContainer>
          </div>
        </div>

        <div className="info-column">
          <div className="card">
            <h3>Legenda</h3>
            <div className="legend">
              <div className="legend-row"><span className="legend-box green" />Puiku (0.8–1.0)</div>
              <div className="legend-row"><span className="legend-box light-green" />Gerai (0.6–0.8)</div>
              <div className="legend-row"><span className="legend-box yellow" />Vidutiniškai (0.4–0.6)</div>
              <div className="legend-row"><span className="legend-box orange" />Blogai (0.2–0.4)</div>
              <div className="legend-row"><span className="legend-box red" />Labai blogai (0.0–0.2)</div>
            </div>
          </div>

          <div className="card status-card">
            {loading ? "Kraunama..." : <>
              <strong>{getLayerName(currentLayer)}</strong> | <b>Objektų kiekis:</b> <strong>{featureCount}</strong>
            </>}
          </div>

          <div className="card weights-panel">
            <h3>Naudotojo svoriai</h3>
            {["restrictions","soil","road"].map(f => (
              <label key={f}>
                <div className="label-row">
                  {f === "restrictions" ? "Ribojimai" : f === "soil" ? "Dirvožemis" : "Keliai"} <span>{weights[f]}</span>
                </div>
                <input type="range" min="0" max="100" value={weights[f]} onChange={(e) => handleWeightChange(f, e.target.value)} />
              </label>
            ))}
            <div className="weight-sum">Svorių suma: <strong>{weightSum}</strong></div>
            <div className="weight-note">Jei miško celėje mažiau nei 20%, ji nerodoma.</div>
          </div>

          {/* Top3 vietos apačioje dešinėje */}
          <div className="card top3-panel top3-simple">
            <h3>Top 3 vietos</h3>
            {top3.length === 0 ? (
              <div className="top3-text">-</div>
            ) : (
              <div className="top3-text">
                {top3.map((f, i) => (
                  <div key={i}>
                    {i + 1}. Investicinis indeksas: {f.score.toFixed(2)}
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