const API_BASE = "http://localhost:8000";

export async function fetchGridData({ layer, bbox, weights, county }) {
  const params = new URLSearchParams({
    layer,
    bbox,
    w_restr: String(weights.restrictions),
    w_soil: String(weights.soil),
    w_road: String(weights.road),
  });

  if (county) {
    params.set("county", county);
  }

  const response = await fetch(`${API_BASE}/grid?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}
