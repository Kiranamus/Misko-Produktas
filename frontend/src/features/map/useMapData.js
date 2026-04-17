import { useCallback, useEffect, useRef, useState } from "react";
import proj4 from "proj4";
import { fetchGridData } from "../../services/mapApi";

proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");
proj4.defs(
  "EPSG:3346",
  "+proj=tmerc +lat_0=0 +lon_0=24 +k=0.9998 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs"
);

function buildTopThree(features) {
  return [...features]
    .filter((feature) => feature.properties?.final_score != null)
    .sort((a, b) => b.properties.final_score - a.properties.final_score)
    .slice(0, 3)
    .map((feature, index) => ({
      rank: index + 1,
      score: feature.properties.final_score,
      layer: feature.properties.layer,
    }));
}

function buildRequestKey(preferredLayer, bbox, weights, county) {
  return [
    preferredLayer,
    bbox,
    weights.restrictions,
    weights.soil,
    weights.road,
    county,
  ].join("|");
}

function mapBoundsToBbox(map) {
  const bounds = map.getBounds();
  const sw = bounds.getSouthWest();
  const ne = bounds.getNorthEast();
  const [minx, miny] = proj4("EPSG:4326", "EPSG:3346", [sw.lng, sw.lat]);
  const [maxx, maxy] = proj4("EPSG:4326", "EPSG:3346", [ne.lng, ne.lat]);
  return `${minx},${miny},${maxx},${maxy}`;
}

export function useMapData(weights, selectedCounty) {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [featureCount, setFeatureCount] = useState(0);
  const [currentLayer, setCurrentLayer] = useState("coarse");
  const [coords, setCoords] = useState(null);
  const [top3, setTop3] = useState([]);
  const debounceRef = useRef(null);
  const lastRequestKeyRef = useRef("");
  const mapRef = useRef(null);

  const fetchLayerData = useCallback(async (map, currentWeights) => {
    const preferredLayer = map.getZoom() >= 10 ? "detail" : "coarse";
    const bbox = mapBoundsToBbox(map);
    const requestKey = buildRequestKey(preferredLayer, bbox, currentWeights, selectedCounty);

    if (requestKey === lastRequestKeyRef.current) {
      return;
    }

    lastRequestKeyRef.current = requestKey;
    setLoading(true);

    try {
      let data = await fetchGridData({
        layer: preferredLayer,
        bbox,
        weights: currentWeights,
        county: selectedCounty,
      });
      let usedLayer = preferredLayer;

      if (preferredLayer === "detail" && (!data.features || data.features.length === 0)) {
        data = await fetchGridData({
          layer: "coarse",
          bbox,
          weights: currentWeights,
          county: selectedCounty,
        });
        usedLayer = "coarse";
      }

      setGeoData(data);
      setFeatureCount(data?.features?.length || 0);
      setCurrentLayer(usedLayer);
      setTop3(data?.features?.length ? buildTopThree(data.features) : []);
    } catch (error) {
      console.error("Fetch klaida:", error);
      setGeoData(null);
      setFeatureCount(0);
      setTop3([]);
    } finally {
      setLoading(false);
    }
  }, [selectedCounty]);

  const handleViewportChange = useCallback((map) => {
    mapRef.current = map;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchLayerData(map, weights);
    }, 250);
  }, [fetchLayerData, weights]);

  const handleMouseMove = useCallback((latlng) => {
    setCoords(latlng);
  }, []);

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchLayerData(mapRef.current, weights);
    }, 300);
  }, [weights, fetchLayerData]);

  useEffect(() => {
    lastRequestKeyRef.current = "";
    if (mapRef.current) {
      fetchLayerData(mapRef.current, weights);
    }
  }, [selectedCounty, fetchLayerData, weights]);

  useEffect(() => () => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
  }, []);

  return {
    coords,
    currentLayer,
    featureCount,
    geoData,
    handleMouseMove,
    handleViewportChange,
    loading,
    top3,
  };
}
