import json
from typing import Optional

from sqlalchemy import text

from app.db_config import engine


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
    classes: Optional[list[str]] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: Optional[int] = None,
):
    where_parts = ["layer = :layer"]
    params = {"layer": layer_name}

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

    if classes:
        class_clauses = []
        for i, cls in enumerate(classes):
            key = f"class_{i}"
            class_clauses.append(f"class = :{key}")
            params[key] = cls.upper()

        where_parts.append("(" + " OR ".join(class_clauses) + ")")

    if min_score is not None:
        where_parts.append("final_score >= :min_score")
        params["min_score"] = float(min_score)

    if max_score is not None:
        where_parts.append("final_score <= :max_score")
        params["max_score"] = float(max_score)

    sql = f"""
        SELECT
            id,
            class,
            forest_pct,
            restr_pct,
            final_score,
            tile_xmin,
            tile_ymin,
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
                "class": r["class"],
                "forest_pct": r["forest_pct"],
                "restr_pct": r["restr_pct"],
                "final_score": r["final_score"],
                "tile_xmin": r["tile_xmin"],
                "tile_ymin": r["tile_ymin"],
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
        classes=classes,
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
        cls = props.get("class")
        score = float(props.get("final_score", 0.0))
        scores.append(score)

        if cls == "GREEN":
            green += 1
        elif cls == "YELLOW":
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