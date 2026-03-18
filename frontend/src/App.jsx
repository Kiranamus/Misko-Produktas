import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, useMapEvents } from "react-leaflet";
import proj4 from "proj4";
import "leaflet/dist/leaflet.css";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000/api";

// WGS84
proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");

// LKS94 / Lithuania TM
proj4.defs(
  "EPSG:3346",
  "+proj=tmerc +lat_0=0 +lon_0=24 +k=0.9998 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs"
);

function MapWatcher({ onViewportChange }) {
  useMapEvents({
    load(e) {
      const map = e.target;
      onViewportChange(map);
    },
    moveend(e) {
      const map = e.target;
      onViewportChange(map);
    },
    zoomend(e) {
      const map = e.target;
      onViewportChange(map);
    },
  });

  return null;
}

function App() {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [featureCount, setFeatureCount] = useState(0);
  const [currentLayer, setCurrentLayer] = useState("coarse");

  const lastRequestKeyRef = useRef("");
  const debounceRef = useRef(null);

  const styleFeature = useCallback((feature) => {
    const cls = feature?.properties?.class;

    let fillColor = "#888";
    if (cls === "GREEN") fillColor = "#2e7d32";
    else if (cls === "YELLOW") fillColor = "#fbc02d";
    else if (cls === "RED") fillColor = "#d32f2f";

    return {
      color: "#ffffff",
      weight: 0.2,
      fillColor,
      fillOpacity: 0.6,
    };
  }, []);

  const onEachFeature = useCallback((feature, layer) => {
    const p = feature.properties || {};
    layer.bindPopup(`
      <b>Klasė:</b> ${p.class ?? "-"}<br/>
      <b>Balas:</b> ${p.final_score ?? "-"}<br/>
      <b>Miško %:</b> ${p.forest_pct ?? "-"}<br/>
      <b>Ribojimų %:</b> ${p.restr_pct ?? "-"}
    `);
  }, []);

  const fetchLayerData = useCallback(async (map) => {
    const zoom = map.getZoom();
    const bounds = map.getBounds();

    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    // Leaflet duoda lng/lat (WGS84), backend nori EPSG:3346
    const [minx, miny] = proj4("EPSG:4326", "EPSG:3346", [sw.lng, sw.lat]);
    const [maxx, maxy] = proj4("EPSG:4326", "EPSG:3346", [ne.lng, ne.lat]);

    const layer = zoom >= 10 ? "detail" : "coarse";
    const bbox = `${minx},${miny},${maxx},${maxy}`;

    const requestKey = `${layer}|${bbox}`;
    if (requestKey === lastRequestKeyRef.current) {
      return;
    }
    lastRequestKeyRef.current = requestKey;

    setLoading(true);
    setCurrentLayer(layer);

    try {
      const res = await fetch(
        `${API_BASE}/grid?layer=${layer}&bbox=${encodeURIComponent(bbox)}`
      );

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      setGeoData(data);
      setFeatureCount(data?.features?.length || 0);
      console.log("Loaded layer:", layer, "features:", data?.features?.length || 0);
    } catch (err) {
      console.error("Fetch klaida:", err);
      setGeoData(null);
      setFeatureCount(0);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleViewportChange = useCallback((map) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchLayerData(map);
    }, 250);
  }, [fetchLayerData]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return (
    <div className="app">
      <div className="topbar">
        <h1>Miško investicinis žemėlapis</h1>
        <div>
          {loading
            ? "Kraunama..."
            : `Sluoksnis: ${currentLayer} | Objektų: ${featureCount}`}
        </div>
      </div>

      <div className="legend">
        <span className="legend-item green">■ Geras</span>
        <span className="legend-item yellow">■ Vidutinis</span>
        <span className="legend-item red">■ Blogas</span>
      </div>

      <div className="map-container">
        <MapContainer
          center={[55.2, 23.9]}
          zoom={7}
          minZoom={6}
          preferCanvas={true}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapWatcher onViewportChange={handleViewportChange} />

          {geoData && geoData.features && geoData.features.length > 0 && (
            <GeoJSON
              key={`${currentLayer}-${featureCount}`}
              data={geoData}
              style={styleFeature}
              onEachFeature={onEachFeature}
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
}

export default App;