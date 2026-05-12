const COPY = {
  lt: {
    layers: {
      coarse: "Abstraktus rodymas",
      detail: "Detalus rodymas",
    },
    fields: {
      forestType: "Miško tipas",
      municipality: "Savivaldybė",
      county: "Apskritis",
      finalScore: "Investicinis indeksas",
      forestShare: "Miško dalis pateiktame plote",
      restrictions: "Miško veiklos ribojimų indeksas",
      soil: "Dirvožemio indeksas",
      soilIndicators: "Dirvožemio rodikliai",
      road: "Kelių indeksas",
      accessibility: "Susisiekimas",
    },
    ratings: {
      index: ["Labai blogai", "Blogai", "Vidutiniškai", "Gerai", "Puiku"],
      forest: ["Labai mažai miško", "Mažai miško", "Vidutiniškai daug miško", "Daug miško", "Labai daug miško"],
      restrictions: ["Labai dideli ribojimai", "Dideli ribojimai", "Vidutiniai ribojimai", "Maži ribojimai", "Labai maži ribojimai", "Nėra ribojimų"],
      quality: ["Labai blogas", "Prastas", "Vidutiniškas", "Labai geras", "Puikus"],
    },
    forestTypes: {
      "spygliuociu miskai": "Spygliuočių miškai",
      "lapuociu miskai": "Lapuočių miškai",
      "misrus miskai": "Mišrūs miškai",
      "misrus miskas": "Mišrus miškas",
    },
  },
  en: {
    layers: {
      coarse: "Abstract view",
      detail: "Detailed view",
    },
    fields: {
      forestType: "Forest type",
      municipality: "Municipality",
      county: "County",
      finalScore: "Investment index",
      forestShare: "Forest share in the selected area",
      restrictions: "Forestry activity restriction index",
      soil: "Soil index",
      soilIndicators: "Soil indicators",
      road: "Road index",
      accessibility: "Accessibility",
    },
    ratings: {
      index: ["Very bad", "Bad", "Average", "Good", "Excellent"],
      forest: ["Very little forest", "Little forest", "Moderate forest coverage", "High forest coverage", "Very high forest coverage"],
      restrictions: ["Very high restrictions", "High restrictions", "Moderate restrictions", "Low restrictions", "Very low restrictions", "No restrictions"],
      quality: ["Very poor", "Poor", "Average", "Very good", "Excellent"],
    },
    forestTypes: {
      "spygliuociu miskai": "Coniferous forests",
      "lapuociu miskai": "Deciduous forests",
      "misrus miskai": "Mixed forests",
      "misrus miskas": "Mixed forest",
    },
  },
};

const COUNTY_TRANSLATIONS = {
  "alytaus apskritis": "Alytus county",
  "kauno apskritis": "Kaunas county",
  "klaipedos apskritis": "Klaipeda county",
  "marijampoles apskritis": "Marijampole county",
  "panevezio apskritis": "Panevezys county",
  "siauliu apskritis": "Siauliai county",
  "taurages apskritis": "Taurage county",
  "telsiu apskritis": "Telsiai county",
  "utenos apskritis": "Utena county",
  "vilniaus apskritis": "Vilnius county",
};

const PLACE_BASE_TRANSLATIONS = {
  alytaus: "Alytus",
  kauno: "Kaunas",
  klaipedos: "Klaipeda",
  marijampoles: "Marijampole",
  panevezio: "Panevezys",
  siauliu: "Siauliai",
  taurages: "Taurage",
  telsiu: "Telsiai",
  utenos: "Utena",
  vilniaus: "Vilnius",
};

function getCopy(language) {
  return COPY[language] || COPY.lt;
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function ratingByThreshold(value, labels) {
  if (value >= 0.9) return labels[4];
  if (value >= 0.7) return labels[3];
  if (value >= 0.5) return labels[2];
  if (value >= 0.3) return labels[1];
  return labels[0];
}

function translateMunicipality(value, language) {
  if (language !== "en" || !value) return value || "-";

  const normalized = normalizeText(value);
  const districtMatch = normalized.match(/^(.+?)\s+r\.\s+sav\.$/);
  const cityMatch = normalized.match(/^(.+?)\s+m\.\s+sav\.$/);
  const municipalityMatch = normalized.match(/^(.+?)\s+sav\.$/);
  const base = districtMatch?.[1] || cityMatch?.[1] || municipalityMatch?.[1];

  if (!base) return value;

  const translatedBase = PLACE_BASE_TRANSLATIONS[base] || value.replace(/\s+(r\.|m\.)?\s*sav\.$/i, "");
  if (districtMatch) return `${translatedBase} district municipality`;
  if (cityMatch) return `${translatedBase} city municipality`;
  return `${translatedBase} municipality`;
}

export function translatePlaceName(value, language = "lt", type = "generic") {
  if (!value) return "-";
  if (language !== "en") return value;

  const normalized = normalizeText(value);
  if (type === "county" || normalized.endsWith("apskritis")) {
    return COUNTY_TRANSLATIONS[normalized] || value.replace(/\s+apskritis$/i, " county");
  }

  if (type === "municipality" || normalized.endsWith("sav.")) {
    return translateMunicipality(value, language);
  }

  return value;
}

export function translateForestType(value, language = "lt") {
  if (!value) return "-";
  const copy = getCopy(language);
  return copy.forestTypes[normalizeText(value)] || value;
}

export function getLayerName(layer, language = "lt") {
  return getCopy(language).layers[layer] || "-";
}

export function formatValue(value) {
  return value != null ? Number(value).toFixed(2) : "-";
}

export function getIndexRating(value, language = "lt") {
  return ratingByThreshold(value, getCopy(language).ratings.index);
}

export function getForestRating(value, language = "lt") {
  return ratingByThreshold(value, getCopy(language).ratings.forest);
}

export function getRestrictionsRating(value, language = "lt") {
  const labels = getCopy(language).ratings.restrictions;
  if (value === 1) return labels[5];
  if (value >= 0.9) return labels[4];
  if (value >= 0.7) return labels[3];
  if (value >= 0.5) return labels[2];
  if (value >= 0.3) return labels[1];
  return labels[0];
}

export function getSoilRating(value, language = "lt") {
  return ratingByThreshold(value, getCopy(language).ratings.quality);
}

export function getRoadRating(value, language = "lt") {
  return ratingByThreshold(value, getCopy(language).ratings.quality);
}

export function getFeaturePopupRows(properties = {}, language = "lt") {
  const finalScore = properties.final_score ?? null;
  const forest = properties.forest_pct ?? null;
  const restrictions = properties.restrictions_index ?? null;
  const soil = properties.soil_index ?? null;
  const road = properties.road_score ?? null;
  const fields = getCopy(language).fields;

  return {
    title: getLayerName(properties.layer, language),
    rows: [
      { label: fields.forestType, value: translateForestType(properties.forest_type, language), spacing: "after" },
      { label: fields.municipality, value: translatePlaceName(properties.municipality, language, "municipality") },
      { label: fields.county, value: translatePlaceName(properties.county, language, "county"), spacing: "after" },
      {
        label: fields.finalScore,
        value: formatValue(finalScore),
        detail: finalScore != null ? getIndexRating(finalScore, language) : "-",
        spacing: "after",
      },
      {
        label: fields.forestShare,
        value: forest != null ? `${(forest * 100).toFixed(2)}%` : "-",
        detail: forest != null ? getForestRating(forest, language) : "-",
        spacing: "after",
      },
      {
        label: fields.restrictions,
        value: formatValue(restrictions),
        detail: restrictions != null ? getRestrictionsRating(restrictions, language) : "-",
        spacing: "after",
      },
      {
        label: fields.soil,
        value: formatValue(soil),
        detailLabel: fields.soilIndicators,
        detail: soil != null ? getSoilRating(soil, language) : "-",
        spacing: "after",
      },
      {
        label: fields.road,
        value: formatValue(road),
        detailLabel: fields.accessibility,
        detail: road != null ? getRoadRating(road, language) : "-",
      },
    ],
  };
}

export function buildFeaturePopupContent(properties = {}, language = "lt") {
  const content = getFeaturePopupRows(properties, language);

  return `
    <b>${content.title}</b><br/>
    ${content.rows.map((row) => {
      const detail = row.detailLabel ? `${row.detailLabel}: ${row.detail}` : row.detail;
      return `<b>${row.label}:</b> ${row.value}<br/>${detail ? `${detail}<br/>` : ""}${row.spacing === "after" ? "<br/>" : ""}`;
    }).join("")}
  `;
}
