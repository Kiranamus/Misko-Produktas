import test from "node:test";
import assert from "node:assert/strict";

import { fetchGridData } from "./mapApi.js";

test("fetchGridData builds query params and returns JSON", async () => {
  globalThis.fetch = async (url) => {
    assert.match(url, /^http:\/\/localhost:8000\/grid\?/);
    assert.match(url, /layer=detail/);
    assert.match(url, /bbox=1%2C2%2C3%2C4/);
    assert.match(url, /county=Vilnius/);
    assert.match(url, /w_restr=40/);
    return {
      ok: true,
      json: async () => ({ features: [] }),
    };
  };

  const result = await fetchGridData({
    layer: "detail",
    bbox: "1,2,3,4",
    county: "Vilnius",
    weights: { restrictions: 40, soil: 30, road: 30 },
  });

  assert.deepEqual(result, { features: [] });
});

test("fetchGridData throws on non-ok response", async () => {
  globalThis.fetch = async () => ({ ok: false, status: 500 });

  await assert.rejects(
    fetchGridData({
      layer: "coarse",
      bbox: "1,2,3,4",
      weights: { restrictions: 40, soil: 30, road: 30 },
    }),
    /HTTP 500/,
  );
});
