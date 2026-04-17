import json
from typing import Optional

from sqlalchemy import text

from app.db_config import engine
from app.config import LT_BOUNDARY_WKT
from app.utils.geo import parse_bbox_string


GRID_SCORE_EXPR = """
    (
        (
            POWER(COALESCE(restrictions_index, 0), 1.8) * :w_restr +
            POWER(COALESCE(soil_index, 0), 1.25) * :w_soil +
            POWER(COALESCE(road_score, 0), 1.15) * :w_road
        )
        *
        CASE
            WHEN COALESCE(restrictions_index, 0) < 0.35 THEN 0.5
            ELSE 1.0
        END
    )
"""


def normalize_weights(w_restr: float, w_soil: float, w_road: float):
    total = w_restr + w_soil + w_road
    if total <= 0:
        raise ValueError("Bent vienas svoris turi būti didesnis už 0")
    return (
        w_restr / total,
        w_soil / total,
        w_road / total,
    )


def classify(score: float) -> str:
    if score >= 0.66:
        return "GREEN"
    if score >= 0.33:
        return "YELLOW"
    return "RED"


def get_metadata(layer_name: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM forest_cells
                WHERE layer = :layer
            """),
            {"layer": layer_name},
        ).fetchone()

    return {
        "ok": True,
        "layer": layer_name,
        "count": int(row._mapping["cnt"] if row else 0),
    }


def build_grid_filters(
    layer_name: str,
    bbox: Optional[str],
    county: Optional[str],
    min_score: Optional[float],
    max_score: Optional[float],
    w_restr: float,
    w_soil: float,
    w_road: float,
) -> tuple[list[str], dict]:
    where_parts = [
        "layer = :layer",
        "ST_Intersects(geometry, ST_GeomFromText(:lt_boundary, 3346))",
        "COALESCE(forest_pct, 0) >= 0.2",
    ]

    params = {
        "layer": layer_name,
        "lt_boundary": LT_BOUNDARY_WKT,
        "w_restr": w_restr,
        "w_soil": w_soil,
        "w_road": w_road,
    }

    if bbox:
        minx, miny, maxx, maxy = parse_bbox_string(bbox)
        where_parts.append(
            "geometry && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 3346)"
        )
        params.update(
            {
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
            }
        )

    if county:
        where_parts.append("county = :county")
        params["county"] = county

    if min_score is not None:
        where_parts.append(f"{GRID_SCORE_EXPR} >= :min_score")
        params["min_score"] = float(min_score)

    if max_score is not None:
        where_parts.append(f"{GRID_SCORE_EXPR} <= :max_score")
        params["max_score"] = float(max_score)

    return where_parts, params


def build_grid_query(where_parts: list[str], limit: Optional[int]) -> str:
    sql = f"""
        SELECT
            id,
            layer,
            forest_pct,
            tex_score,
            dra_score,
            ph_score,
            reljef_score,
            akmen_score,
            soil_index_raw,
            restrictions_index,
            soil_index,
            road_score,
            forest_type,
            municipality,
            county,
            {GRID_SCORE_EXPR} AS final_score,
            ST_AsGeoJSON(ST_Transform(geometry, 4326)) AS geom_json
        FROM forest_cells
        WHERE {' AND '.join(where_parts)}
    """

    if limit is not None and limit > 0:
        sql += " LIMIT :limit"

    return sql


def serialize_grid_feature(row, w_restr: float, w_soil: float, w_road: float) -> dict:
    mapping = row._mapping
    score = 0.0 if mapping["final_score"] is None else float(mapping["final_score"])

    return {
        "type": "Feature",
        "id": str(mapping["id"]),
        "properties": {
            "layer": mapping["layer"],
            "forest_pct": 0.0 if mapping["forest_pct"] is None else float(mapping["forest_pct"]),
            "tex_score": 0.0 if mapping["tex_score"] is None else float(mapping["tex_score"]),
            "dra_score": 0.0 if mapping["dra_score"] is None else float(mapping["dra_score"]),
            "ph_score": 0.0 if mapping["ph_score"] is None else float(mapping["ph_score"]),
            "reljef_score": 0.0 if mapping["reljef_score"] is None else float(mapping["reljef_score"]),
            "akmen_score": 0.0 if mapping["akmen_score"] is None else float(mapping["akmen_score"]),
            "soil_index_raw": 0.0 if mapping["soil_index_raw"] is None else float(mapping["soil_index_raw"]),
            "restrictions_index": 0.0 if mapping["restrictions_index"] is None else float(mapping["restrictions_index"]),
            "soil_index": 0.0 if mapping["soil_index"] is None else float(mapping["soil_index"]),
            "road_score": 0.0 if mapping["road_score"] is None else float(mapping["road_score"]),
            "forest_type": mapping["forest_type"],
            "municipality": mapping["municipality"],
            "county": mapping["county"],
            "final_score": score,
            "class": classify(score),
            "weights": {
                "restrictions": round(w_restr, 4),
                "soil": round(w_soil, 4),
                "road": round(w_road, 4),
            },
        },
        "geometry": json.loads(mapping["geom_json"]),
    }


def summarize_scores(features: list[dict]) -> dict:
    if not features:
        return {
            "count": 0,
            "green": 0,
            "yellow": 0,
            "red": 0,
            "avg_score": 0.0,
        }

    green = 0
    yellow = 0
    red = 0
    scores = []

    for feature in features:
        score = float(feature["properties"].get("final_score", 0.0))
        scores.append(score)

        if score >= 0.66:
            green += 1
        elif score >= 0.33:
            yellow += 1
        else:
            red += 1

    return {
        "count": len(features),
        "green": green,
        "yellow": yellow,
        "red": red,
        "avg_score": round(sum(scores) / len(scores), 4),
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
    }


def get_counties() -> list[str]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT county
                FROM forest_cells
                WHERE county IS NOT NULL
                  AND county <> ''
                ORDER BY county
            """)
        ).fetchall()

    return [str(row._mapping["county"]) for row in rows]


def query_grid(
    layer_name: str = "coarse",
    bbox: Optional[str] = None,
    county: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: Optional[int] = None,
    w_restr: float = 40,
    w_soil: float = 30,
    w_road: float = 30,
):
    w_restr, w_soil, w_road = normalize_weights(w_restr, w_soil, w_road)
    where_parts, params = build_grid_filters(
        layer_name=layer_name,
        bbox=bbox,
        county=county,
        min_score=min_score,
        max_score=max_score,
        w_restr=w_restr,
        w_soil=w_soil,
        w_road=w_road,
    )
    sql = build_grid_query(where_parts, limit)
    if limit is not None and limit > 0:
        params["limit"] = int(limit)

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    features = [
        serialize_grid_feature(row, w_restr=w_restr, w_soil=w_soil, w_road=w_road)
        for row in rows
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def query_stats(
    layer_name: str = "coarse",
    bbox: Optional[str] = None,
    county: Optional[str] = None,
    classes: Optional[list[str]] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    w_restr: float = 40,
    w_soil: float = 30,
    w_road: float = 30,
):
    data = query_grid(
        layer_name=layer_name,
        bbox=bbox,
        county=county,
        min_score=min_score,
        max_score=max_score,
        limit=None,
        w_restr=w_restr,
        w_soil=w_soil,
        w_road=w_road,
    )

    features = data.get("features", [])
    return {"layer": layer_name, **summarize_scores(features)}

def query_distribution(layer_name: str = "coarse") -> dict:
    sql = """
        SELECT
            COUNT(*) AS cnt,
            MIN(forest_pct) AS forest_min,
            MAX(forest_pct) AS forest_max,
            AVG(forest_pct) AS forest_avg,
            MIN(restrictions_index) AS restr_min,
            MAX(restrictions_index) AS restr_max,
            AVG(restrictions_index) AS restr_avg,

            MIN(soil_index) AS soil_min,
            MAX(soil_index) AS soil_max,
            AVG(soil_index) AS soil_avg,

            MIN(road_score) AS road_min,
            MAX(road_score) AS road_max,
            AVG(road_score) AS road_avg
        FROM forest_cells
        WHERE layer = :layer
    """

    with engine.begin() as conn:
        row = conn.execute(text(sql), {"layer": layer_name}).fetchone()

    if not row:
        return {"layer": layer_name, "count": 0}

    r = row._mapping
    return {
        "layer": layer_name,
        "count": int(r["cnt"] or 0),
        "forest_pct": {
            "min": float(r["forest_min"] or 0),
            "max": float(r["forest_max"] or 0),
            "avg": float(r["forest_avg"] or 0),
        },
        "restrictions_index": {
            "min": float(r["restr_min"] or 0),
            "max": float(r["restr_max"] or 0),
            "avg": float(r["restr_avg"] or 0),
        },
        "soil_index": {
            "min": float(r["soil_min"] or 0),
            "max": float(r["soil_max"] or 0),
            "avg": float(r["soil_avg"] or 0),
        },
        "road_score": {
            "min": float(r["road_min"] or 0),
            "max": float(r["road_max"] or 0),
            "avg": float(r["road_avg"] or 0),
        },
    }
