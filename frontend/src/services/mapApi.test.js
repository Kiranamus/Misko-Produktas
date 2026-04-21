import assert from "node:assert/strict";

import { fetchGridData } from "./mapApi.js";


export async function run() {
  let requestedUrl = null;
  globalThis.fetch = async (url) => {
    requestedUrl = url;
    return {
      ok: true,
      async json() {
        return { ok: true };
      },
    };
  };

  const result = await fetchGridData({
    layer: "detail",
    bbox: "1,2,3,4",
    county: "Vilniaus apskritis",
    weights: {
      restrictions: 40,
      soil: 30,
      road: 30,
    },
  });

  assert.deepEqual(result, { ok: true });
  assert.match(requestedUrl, /layer=detail/);
  assert.match(requestedUrl, /bbox=1%2C2%2C3%2C4/);
  assert.match(requestedUrl, /w_restr=40/);
  assert.match(requestedUrl, /w_soil=30/);
  assert.match(requestedUrl, /w_road=30/);
  assert.match(requestedUrl, /county=Vilniaus\+apskritis|county=Vilniaus%20apskritis|county=Vilniaus%20apskritis/);

  requestedUrl = null;
  globalThis.fetch = async (url) => {
    requestedUrl = url;
    return {
      ok: true,
      async json() {
        return { ok: true };
      },
    };
  };

  await fetchGridData({
    layer: "coarse",
    bbox: "5,6,7,8",
    county: "",
    weights: {
      restrictions: 50,
      soil: 20,
      road: 30,
    },
  });

  assert.doesNotMatch(requestedUrl, /county=/);

  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
  });

  await assert.rejects(
    () =>
      fetchGridData({
        layer: "coarse",
        bbox: "1,2,3,4",
        county: null,
        weights: {
          restrictions: 40,
          soil: 30,
          road: 30,
        },
        }),
    /HTTP 500/,
  );
  delete globalThis.fetch;
}
