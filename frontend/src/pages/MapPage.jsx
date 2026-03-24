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

  const debounceRef = useRef(null);
  const lastRequestKeyRef = useRef("");
  const mapRef = useRef(null);

  const styleFeature = useCallback((feature) => {
    const score = feature?.properties?.final_score ?? 0;

    let fillColor = "#d32f2f";
    if (score >= 0.66) fillColor = "#2e7d32";
    else if (score >= 0.33) fillColor = "#fbc02d";

    return {
      color: "#ffffff",
      weight: 0.2,
      fillColor,
      fillOpacity: 0.65,
    };
  }, []);

  const onEachFeature = useCallback((feature, layer) => {
    const p = feature.properties || {};

    layer.bindPopup(`
      <b>Sluoksnis:</b> ${p.layer ?? "-"}<br/>
      <b>Galutinis balas:</b> ${p.final_score != null ? Number(p.final_score).toFixed(3) : "-"}<br/>
      <b>Klasė:</b> ${p.class ?? "-"}<br/>
      <b>Miško %:</b> ${p.forest_pct != null ? Number(p.forest_pct).toFixed(3) : "-"}<br/>
      <b>Ribojimų indeksas:</b> ${p.restrictions_index != null ? Number(p.restrictions_index).toFixed(3) : "-"}<br/>
      <b>Dirvožemio indeksas:</b> ${p.soil_index != null ? Number(p.soil_index).toFixed(3) : "-"}<br/>
      <b>Kelių indeksas:</b> ${p.road_score != null ? Number(p.road_score).toFixed(3) : "-"}
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
    } catch (err) {
      console.error("Fetch klaida:", err);
      setGeoData(null);
      setFeatureCount(0);
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

  const handleMouseMove = (latlng) => {
    setCoords(latlng);
  };

  const handleWeightChange = (field, value) => {
    setWeights((prev) => ({
      ...prev,
      [field]: Number(value),
    }));
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

  const weightSum =
    weights.restrictions + weights.soil + weights.road;

  return (
    <div className="content">
      <div className="layout">
        <div className="map-column">
          <div className="map-container">
            <MapContainer
              center={[55.2, 23.9]}
              zoom={7}
              minZoom={6}
              preferCanvas={true}
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
                  Lat: {coords.lat.toFixed(5)}, Lng: {coords.lng.toFixed(5)}
                </div>
              )}
            </MapContainer>
          </div>
        </div>

        <div className="info-column">
          <div className="legend">
            <span className="legend-item green">■ Geras (≥ 0.66)</span>
            <span className="legend-item yellow">■ Vidutinis (0.33–0.65)</span>
            <span className="legend-item red">■ Blogas (&lt; 0.33)</span>
          </div>

          <div className="loading">
            {loading
              ? "Kraunama..."
              : `Sluoksnis: ${currentLayer} | Objektų: ${featureCount}`}
          </div>

          <div className="weights-panel">
            <h3>Naudotojo svoriai</h3>

            <label>
              Ribojimai: <strong>{weights.restrictions}</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.restrictions}
                onChange={(e) => handleWeightChange("restrictions", e.target.value)}
              />
            </label>

            <label>
              Dirvožemis: <strong>{weights.soil}</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.soil}
                onChange={(e) => handleWeightChange("soil", e.target.value)}
              />
            </label>

            <label>
              Keliai: <strong>{weights.road}</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.road}
                onChange={(e) => handleWeightChange("road", e.target.value)}
              />
            </label>

            <div className="weight-sum">
              Svorių suma: <strong>{weightSum}</strong>
            </div>

            <div className="weight-note">
              Jei miško celėje mažiau nei 20%, ji visai nerodoma.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}