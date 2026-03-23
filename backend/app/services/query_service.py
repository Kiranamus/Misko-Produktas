import json
from typing import Optional

from sqlalchemy import text

from app.db_config import engine
from app.config import LT_BOUNDARY_WKT


def parse_bbox_string(bbox_str: str):
    vals = [float(v.strip()) for v in bbox_str.split(",")]
    if len(vals) != 4:
        raise ValueError("bbox must be minx,miny,maxx,maxy in EPSG:3346")
    return tuple(vals)


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

def query_grid(
    layer_name: str = "coarse",
    bbox: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: Optional[int] = None,
):
    where_parts = [
        "layer = :layer",
        "ST_Intersects(geometry, ST_GeomFromText(:lt_boundary, 3346))",
        "COALESCE(forest_pct, 0) > 0",
        "final_score >= 0.05"
    ]
    params = {"layer": layer_name, "lt_boundary": LT_BOUNDARY_WKT}

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

    if min_score is not None:
        where_parts.append("final_score >= :min_score")
        params["min_score"] = float(min_score)

    if max_score is not None:
        where_parts.append("final_score <= :max_score")
        params["max_score"] = float(max_score)

    sql = f"""
        SELECT
            id,
            layer,
            forest_pct,
            valstybinis_pct,
            n2000_pct,
            n2000_index,
            vmt_index,
            restrictions_index,
            soil_index,
            road_score,
            final_score,
            ST_AsGeoJSON(ST_Transform(geometry, 4326)) AS geom_json
        FROM forest_cells
        WHERE {' AND '.join(where_parts)}
    """

    if limit is not None and limit > 0:
        sql += " LIMIT :limit"
        params["limit"] = int(limit)

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()

        features = []
    for row in rows:
        r = row._mapping

        feature = {
            "type": "Feature",
            "id": str(r["id"]),
            "properties": {
                "layer": r["layer"],
                "forest_pct": 0.0 if r["forest_pct"] is None else float(r["forest_pct"]),
                "valstybinis_pct": 0.0 if r["valstybinis_pct"] is None else float(r["valstybinis_pct"]),
                "n2000_pct": 0.0 if r["n2000_pct"] is None else float(r["n2000_pct"]),
                "n2000_index": 0.0 if r["n2000_index"] is None else float(r["n2000_index"]),
                "vmt_index": 0.0 if r["vmt_index"] is None else float(r["vmt_index"]),
                "restrictions_index": 0.0 if r["restrictions_index"] is None else float(r["restrictions_index"]),
                "soil_index": 0.0 if r["soil_index"] is None else float(r["soil_index"]),
                "road_score": 0.0 if r["road_score"] is None else float(r["road_score"]),
                "final_score": 0.0 if r["final_score"] is None else float(r["final_score"]),
            },
            "geometry": json.loads(r["geom_json"]),
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def query_stats(
    layer_name: str = "coarse",
    bbox: Optional[str] = None,
    classes: Optional[list[str]] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
):
    data = query_grid(
        layer_name=layer_name,
        bbox=bbox,
        min_score=min_score,
        max_score=max_score,
        limit=None,
    )

    features = data.get("features", [])
    if not features:
        return {
            "layer": layer_name,
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
        props = feature.get("properties", {})
        score = float(props.get("final_score", 0.0))
        scores.append(score)

        if score >= 0.66:
            green += 1
        elif score >= 0.33:
            yellow += 1
        else:
            red += 1

    return {
        "layer": layer_name,
        "count": len(features),
        "green": green,
        "yellow": yellow,
        "red": red,
        "avg_score": round(sum(scores) / len(scores), 4),
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
    }