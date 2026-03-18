import json
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from app.config import (
    CRS_METRIC,
    CRS_WEB,
    get_tile_index_path,
    get_tile_index_geojson_path,
    get_metadata_path,
)


def parse_bbox_string(bbox_str: str):
    vals = [float(v.strip()) for v in bbox_str.split(",")]
    if len(vals) != 4:
        raise ValueError("bbox must be minx,miny,maxx,maxy in EPSG:3346")
    return tuple(vals)


def load_tile_index(layer_name: str) -> gpd.GeoDataFrame:
    parquet_path = get_tile_index_path(layer_name)
    geojson_path = get_tile_index_geojson_path(layer_name)

    if parquet_path.exists():
        return gpd.read_parquet(parquet_path)

    if geojson_path.exists():
        return gpd.read_file(geojson_path)

    return gpd.GeoDataFrame(columns=["tile_path", "geometry"], geometry="geometry", crs=CRS_METRIC)


def get_metadata(layer_name: str) -> dict:
    path = get_metadata_path(layer_name)
    if not path.exists():
        return {"ok": False, "layer": layer_name, "message": "No analysis results yet."}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tile_file(path: Path) -> gpd.GeoDataFrame:
    if path.suffix.lower() == ".parquet":
        return gpd.read_parquet(path)
    return gpd.read_file(path)


def query_grid(
    layer_name: str = "coarse",
    bbox: Optional[str] = None,
    classes: Optional[list[str]] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: Optional[int] = None,
):
    tile_index = load_tile_index(layer_name)
    if tile_index.empty:
        return {"type": "FeatureCollection", "features": []}

    bbox_geom = None
    if bbox:
        minx, miny, maxx, maxy = parse_bbox_string(bbox)
        bbox_geom = box(minx, miny, maxx, maxy)
        tile_index = tile_index[tile_index.intersects(bbox_geom)].copy()

    if tile_index.empty:
        return {"type": "FeatureCollection", "features": []}

    frames = []
    for path_str in tile_index["tile_path"].tolist():
        path = Path(path_str)
        if path.exists():
            frames.append(load_tile_file(path))

    if not frames:
        return {"type": "FeatureCollection", "features": []}

    gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=CRS_METRIC)

    if bbox_geom is not None:
        gdf = gdf[gdf.intersects(bbox_geom)].copy()

    if classes:
        allowed = [c.upper() for c in classes]
        gdf = gdf[gdf["class"].isin(allowed)].copy()

    if min_score is not None:
        gdf = gdf[gdf["final_score"] >= float(min_score)].copy()

    if max_score is not None:
        gdf = gdf[gdf["final_score"] <= float(max_score)].copy()

    if limit is not None and limit > 0:
        gdf = gdf.head(limit).copy()

    if gdf.empty:
        return {"type": "FeatureCollection", "features": []}

    gdf = gdf.to_crs(CRS_WEB)
    return json.loads(gdf.to_json())


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

    green = yellow = red = 0
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