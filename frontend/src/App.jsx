import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000/api";

function App() {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCoarse = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/grid?layer=coarse`);
        const data = await res.json();
        console.log("Coarse data:", data);
        setGeoData(data);
      } catch (err) {
        console.error("Failed to load coarse data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCoarse();
  }, []);

  const styleFeature = (feature) => {
    const cls = feature?.properties?.class;

    let fillColor = "#999";

    if (cls === "GREEN") fillColor = "#2e7d32";
    else if (cls === "YELLOW") fillColor = "#fbc02d";
    else if (cls === "RED") fillColor = "#d32f2f";

    return {
      color: "#ffffff",
      weight: 0.2,
      fillColor,
      fillOpacity: 0.6,
    };
  };

  const onEachFeature = (feature, layer) => {
    const p = feature.properties || {};
    layer.bindPopup(`
      <b>Klasė:</b> ${p.class ?? "-"}<br/>
      <b>Balas:</b> ${p.final_score ?? "-"}<br/>
      <b>Miško %:</b> ${p.forest_pct ?? "-"}<br/>
      <b>Ribojimų %:</b> ${p.restr_pct ?? "-"}
    `);
  };

  return (
    <div className="app">
      <div className="topbar">
        <h1>Miško investicinis žemėlapis</h1>
        <div>{loading ? "Kraunama..." : `Objektų: ${featureCount}`}</div>
      </div>
      <div style={{ display: "flex", gap: "15px", marginBottom: "10px" }}>
        <span style={{ color: "#2e7d32" }}>■ Geras</span>
        <span style={{ color: "#fbc02d" }}>■ Vidutinis</span>
        <span style={{ color: "#d32f2f" }}>■ Blogas</span>
      </div>
      <div className="map-container">
        <MapContainer
          center={[55.2, 23.9]}
          zoom={7}
          minZoom={6}
          preferCanvas={true}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {geoData && (
            <GeoJSON
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