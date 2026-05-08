const fs = require("fs");
const path = require("path");

const inputPath = process.argv[2];
const outputPath = path.resolve(__dirname, "../src/features/map/lithuaniaBoundary.js");

if (!inputPath) {
  console.error("Usage: node frontend/scripts/generateLithuaniaBoundary.cjs <ne_10m_admin_0_countries.geojson>");
  process.exit(1);
}

const source = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const features = source.type === "FeatureCollection" ? source.features : [source];
const lithuania = features.find((feature) => {
  const properties = feature.properties || {};
  return (
    properties.ADM0_A3 === "LTU" ||
    properties.ISO_A3 === "LTU" ||
    properties.shapeISO === "LTU" ||
    properties.iso3 === "LTU" ||
    properties.NAME === "Lithuania" ||
    properties.shapeName === "Lithuania"
  );
});

if (!lithuania) {
  console.error("Lithuania feature was not found in the Natural Earth file.");
  process.exit(1);
}

const samePoint = (a, b) => a && b && Math.abs(a[0] - b[0]) < 1e-12 && Math.abs(a[1] - b[1]) < 1e-12;

const distance = (a, b) => {
  const avgLat = ((a[1] + b[1]) / 2) * (Math.PI / 180);
  const dx = (b[0] - a[0]) * Math.cos(avgLat);
  const dy = b[1] - a[1];
  return Math.hypot(dx, dy);
};

const interpolate = (a, b, ratio) => [
  a[0] + (b[0] - a[0]) * ratio,
  a[1] + (b[1] - a[1]) * ratio,
];

const roundCoord = ([lng, lat]) => [
  Number(lng.toFixed(6)),
  Number(lat.toFixed(6)),
];

const resampleClosedRing = (ring, targetCount) => {
  const openRing = samePoint(ring[0], ring[ring.length - 1]) ? ring.slice(0, -1) : ring.slice();
  const segments = [];
  let perimeter = 0;

  for (let index = 0; index < openRing.length; index += 1) {
    const start = openRing[index];
    const end = openRing[(index + 1) % openRing.length];
    const length = distance(start, end);
    segments.push({ start, end, from: perimeter, length });
    perimeter += length;
  }

  const samples = [];
  for (let sampleIndex = 0; sampleIndex < targetCount; sampleIndex += 1) {
    const target = (sampleIndex / targetCount) * perimeter;
    const segment = segments.find((candidate) => target <= candidate.from + candidate.length) || segments[segments.length - 1];
    const ratio = segment.length === 0 ? 0 : (target - segment.from) / segment.length;
    samples.push(roundCoord(interpolate(segment.start, segment.end, ratio)));
  }

  samples.push(samples[0]);
  return samples;
};

const resamplePolygon = (polygon) =>
  polygon.map((ring, ringIndex) => {
    const baseCount = ring.length;
    const targetCount = ringIndex === 0 ? Math.max(baseCount, 1000) : baseCount;
    return resampleClosedRing(ring, targetCount);
  });

const geometry = {
  type: lithuania.geometry.type,
  coordinates:
    lithuania.geometry.type === "MultiPolygon"
      ? lithuania.geometry.coordinates.map(resamplePolygon)
      : resamplePolygon(lithuania.geometry.coordinates),
};

const maskRings =
  geometry.type === "MultiPolygon"
    ? geometry.coordinates.flatMap((polygon) => polygon.map((ring) => ring.map(([lng, lat]) => [lat, lng])))
    : geometry.coordinates.map((ring) => ring.map(([lng, lat]) => [lat, lng]));

const feature = {
  type: "Feature",
  properties: {
    name: "Lithuania",
    source: lithuania.properties?.boundarySource || lithuania.properties?.source || "Lithuania ADM0 boundary",
    contour: "high-density perimeter interpolation",
  },
  geometry,
};

const contents = [
  "// Generated from the highest-resolution Lithuania ADM0 boundary provided to the generator.",
  "// The boundary follows the supplied contour workflow: extract rings, parameterize the",
  "// contour, and interpolate it densely. Low-pass Fourier compression is intentionally",
  "// omitted because maximum positional accuracy is more important than a smaller contour.",
  `export const LITHUANIA_BOUNDARY_GEOJSON = ${JSON.stringify(feature)};`,
  "",
  `export const LITHUANIA_MASK_RINGS = ${JSON.stringify([[[-90, -180], [-90, 180], [90, 180], [90, -180]], ...maskRings])};`,
  "",
].join("\n");

fs.writeFileSync(outputPath, contents);
console.log(`Wrote ${outputPath}`);
console.log(`Rings: ${maskRings.map((ring) => ring.length).join(", ")}`);
