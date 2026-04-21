import assert from "node:assert/strict";

import {
  buildFeaturePopupContent,
  formatValue,
  getForestRating,
  getIndexRating,
  getLayerName,
  getRestrictionsRating,
  getRoadRating,
  getSoilRating,
} from "./formatters.js";

export function run() {
  assert.equal(getLayerName("coarse"), "Abstraktus rodymas");
  assert.equal(getLayerName("detail"), "Detalus rodymas");
  assert.equal(getLayerName("unknown"), "-");
 
  assert.equal(formatValue(0.456), "0.46");
  assert.equal(formatValue("1"), "1.00");
  assert.equal(formatValue(null), "-");
  assert.equal(formatValue(undefined), "-");

  assert.equal(getIndexRating(0.95), "Puiku");
  assert.equal(getForestRating(0.72), "Daug miško");
  assert.equal(getRestrictionsRating(1), "Nėra ribojimų");
  assert.equal(getSoilRating(0.55), "Vidutiniškas");
  assert.equal(getRoadRating(0.2), "Labai blogas");

  const html = buildFeaturePopupContent({
    layer: "detail",
    forest_type: "Spygliuočių miškai",
    municipality: "Vilniaus m. sav.",
    county: "Vilniaus apskritis",
    final_score: 0.82,
    forest_pct: 0.45,
    restrictions_index: 0.91,
    soil_index: 0.66,
    road_score: 0.5,
  });

  assert.match(html, /Detalus rodymas/);
  assert.match(html, /Vilniaus apskritis/);
  assert.match(html, /0\.82/);
  assert.match(html, /45\.00%/);
}
