export function getLayerName(layer) {
  if (layer === "coarse") return "Abstraktus rodymas";
  if (layer === "detail") return "Detalus rodymas";
  return "-";
}

export function formatValue(value) {
  return value != null ? Number(value).toFixed(2) : "-";
}

export function getIndexRating(value) {
  if (value >= 0.9) return "Puiku";
  if (value >= 0.7) return "Gerai";
  if (value >= 0.5) return "Vidutiniškai";
  if (value >= 0.3) return "Blogai";
  return "Labai blogai";
}

export function getForestRating(value) {
  if (value >= 0.9) return "Labai daug miško";
  if (value >= 0.7) return "Daug miško";
  if (value >= 0.5) return "Vidutiniškai daug miško";
  if (value >= 0.3) return "Mažai miško";
  return "Labai mažai miško";
}

export function getRestrictionsRating(value) {
  if (value === 1) return "Nėra ribojimų";
  if (value >= 0.9) return "Labai maži ribojimai";
  if (value >= 0.7) return "Maži ribojimai";
  if (value >= 0.5) return "Vidutiniai ribojimai";
  if (value >= 0.3) return "Dideli ribojimai";
  return "Labai dideli ribojimai";
}

export function getSoilRating(value) {
  if (value >= 0.9) return "Puikus";
  if (value >= 0.7) return "Labai geras";
  if (value >= 0.5) return "Vidutiniškas";
  if (value >= 0.3) return "Prastas";
  return "Labai blogas";
}

export function getRoadRating(value) {
  if (value >= 0.9) return "Puikus";
  if (value >= 0.7) return "Labai geras";
  if (value >= 0.5) return "Vidutiniškas";
  if (value >= 0.3) return "Prastas";
  return "Labai blogas";
}

export function buildFeaturePopupContent(properties = {}) {
  const finalScore = properties.final_score ?? null;
  const forest = properties.forest_pct ?? null;
  const forestType = properties.forest_type ?? null;
  const municipality = properties.municipality ?? null;
  const county = properties.county ?? null;
  const restrictions = properties.restrictions_index ?? null;
  const soil = properties.soil_index ?? null;
  const road = properties.road_score ?? null;

  return `
    <b>${getLayerName(properties.layer)}</b><br/>
    <b>Miško tipas:</b> ${forestType || "-"}<br/><br/>
    <b>Savivaldybė:</b> ${municipality || "-"}<br/>
    <b>Apskritis:</b> ${county || "-"}<br/><br/>
    <b>Investicinis indeksas:</b> ${formatValue(finalScore)}<br/>
    ${finalScore != null ? getIndexRating(finalScore) : "-"}<br/><br/>
    <b>Miško dalis pateiktame plote:</b> ${forest != null ? `${(forest * 100).toFixed(2)}%` : "-"}<br/>
    ${forest != null ? getForestRating(forest) : "-"}<br/><br/>
    <b>Miško veiklos ribojimų indeksas:</b> ${formatValue(restrictions)}<br/>
    ${restrictions != null ? getRestrictionsRating(restrictions) : "-"}<br/><br/>
    <b>Dirvožemio indeksas:</b> ${formatValue(soil)}<br/>
    Dirvožemio rodikliai ${soil != null ? getSoilRating(soil) : "-"}<br/><br/>
    <b>Kelių indeksas:</b> ${formatValue(road)}<br/>
    Susisiekimas ${road != null ? getRoadRating(road) : "-"}
  `;
}
