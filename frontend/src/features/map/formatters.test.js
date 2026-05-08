import test from "node:test";
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

test("getLayerName maps known layers and falls back", () => {
  assert.equal(getLayerName("coarse"), "Abstraktus rodymas");
  assert.equal(getLayerName("detail"), "Detalus rodymas");
  assert.equal(getLayerName("unknown"), "-");
});

test("formatValue formats numbers and missing values", () => {
  assert.equal(formatValue(1.234), "1.23");
  assert.equal(formatValue(null), "-");
  assert.equal(formatValue(undefined), "-");
});

test("rating helpers return expected threshold labels", () => {
  assert.equal(getIndexRating(0.9), "Puiku");
  assert.equal(getIndexRating(0.7), "Gerai");
  assert.equal(getIndexRating(0.5), "Vidutiniškai");
  assert.equal(getIndexRating(0.3), "Blogai");
  assert.equal(getIndexRating(0.1), "Labai blogai");

  assert.match(getForestRating(0.9), /^Labai daug/);
  assert.match(getRestrictionsRating(1), /^N/);
  assert.match(getRestrictionsRating(0.7), /ribojimai$/);
  assert.equal(getSoilRating(0.7), "Labai geras");
  assert.equal(getRoadRating(0.3), "Prastas");
});

test("buildFeaturePopupContent renders formatted values and fallbacks", () => {
  const html = buildFeaturePopupContent({
    layer: "coarse",
    final_score: 0.72,
    forest_pct: 0.456,
    restrictions_index: 0.9,
    soil_index: 0.5,
    road_score: 0.3,
  });

  assert.match(html, /Abstraktus rodymas/);
  assert.match(html, /0.72/);
  assert.match(html, /45.60%/);
  assert.match(html, /Savivaldyb/);
});
