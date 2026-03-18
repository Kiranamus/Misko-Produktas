import json
import math
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from app.config import (
    GDB_VMT,
    GDB_NATURA,
    CRS_METRIC,
    LAYER_AREA,
    LAYER_FOREST,
    LAYER_RESTR,
    TH_GREEN,
    TH_YELLOW,
    MAX_WORKERS,
    DEFAULT_COARSE_GRID_SIZE_M,
    DEFAULT_COARSE_TILE_SIZE_M,
    DEFAULT_DETAIL_GRID_SIZE_M,
    DEFAULT_DETAIL_TILE_SIZE_M,
    DEFAULT_SIMPLIFY_TOL_M,
    get_tiles_dir,
    get_tile_index_path,
    get_tile_index_geojson_path,
    get_status_path,
    get_metadata_path,
)


def write_status(layer_name: str, status: str, message: str, extra: Optional[dict] = None) -> None:
    path = get_status_path(layer_name)
    payload = {
        "layer": layer_name,
        "status": status,
        "message": message,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra:
        payload.update(extra)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_status(layer_name: str) -> dict:
    path = get_status_path(layer_name)
    if not path.exists():
        return {"layer": layer_name, "status": "idle", "message": "No analysis yet."}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_metadata(layer_name: str) -> dict:
    path = get_metadata_path(layer_name)
    if not path.exists():
        return {"ok": False, "layer": layer_name, "message": "No metadata yet."}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_layer(gdb_path: Path, layer_name: str, bbox_bounds=None) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(
        gdb_path,
        layer=layer_name,
        engine="pyogrio",
        columns=[],
        bbox=bbox_bounds,
    )

    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_METRIC)
    else:
        gdf = gdf.to_crs(CRS_METRIC)

    if "geometry" not in gdf.columns:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    return gdf[["geometry"]].copy()


def simplify_geoms(gdf: gpd.GeoDataFrame, tol_m: float) -> gpd.GeoDataFrame:
    if gdf.empty or tol_m <= 0:
        return gdf
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(tol_m, preserve_topology=True)
    return gdf


def fix_invalid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf

    gdf = gdf.copy()
    invalid = ~gdf.geometry.is_valid

    if invalid.any():
        try:
            from shapely.validation import make_valid
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].apply(make_valid)
        except Exception:
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)

    return gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()


def classify(score: float) -> str:
    if score >= TH_GREEN:
        return "GREEN"
    if score >= TH_YELLOW:
        return "YELLOW"
    return "RED"


def parse_bbox_string(bbox_str: str):
    vals = [float(v.strip()) for v in bbox_str.split(",")]
    if len(vals) != 4:
        raise ValueError("bbox must be minx,miny,maxx,maxy in EPSG:3346")
    return tuple(vals)


def build_grid_for_bounds(bounds, grid_size: int) -> gpd.GeoDataFrame:
    minx, miny, maxx, maxy = bounds

    minx = math.floor(minx / grid_size) * grid_size
    miny = math.floor(miny / grid_size) * grid_size
    maxx = math.ceil(maxx / grid_size) * grid_size
    maxy = math.ceil(maxy / grid_size) * grid_size

    cells = []
    ids = []
    cid = 0

    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cells.append(box(x, y, x + grid_size, y + grid_size))
            ids.append(cid)
            cid += 1
            y += grid_size
        x += grid_size

    grid = gpd.GeoDataFrame({"cell_local_id": ids}, geometry=cells, crs=CRS_METRIC)
    grid["cell_area"] = grid.geometry.area
    return grid


def build_tiles(area_gdf: gpd.GeoDataFrame, tile_size: int) -> list[tuple]:
    minx, miny, maxx, maxy = area_gdf.total_bounds

    minx = math.floor(minx / tile_size) * tile_size
    miny = math.floor(miny / tile_size) * tile_size
    maxx = math.ceil(maxx / tile_size) * tile_size
    maxy = math.ceil(maxy / tile_size) * tile_size

    tiles = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            tile_geom = box(x, y, x + tile_size, y + tile_size)
            if area_gdf.intersects(tile_geom).any():
                tiles.append((x, y, x + tile_size, y + tile_size))
            y += tile_size
        x += tile_size

    return tiles


def cover_pct_by_sindex(grid: gpd.GeoDataFrame, layer: gpd.GeoDataFrame, col_name: str) -> gpd.GeoDataFrame:
    grid = grid.copy()

    if layer is None or layer.empty:
        grid[col_name] = 0.0
        return grid

    layer = layer[layer.geometry.notna() & ~layer.geometry.is_empty].copy()
    if layer.empty:
        grid[col_name] = 0.0
        return grid

    sidx = layer.sindex
    results = []

    geoms = grid.geometry.values
    areas = grid["cell_area"].values

    for geom, cell_area in zip(geoms, areas):
        cand_idx = list(sidx.intersection(geom.bounds))
        if not cand_idx:
            results.append(0.0)
            continue

        cand = layer.iloc[cand_idx]
        inter = cand.intersection(geom)
        area_sum = inter.area.sum() if len(inter) else 0.0

        pct = area_sum / cell_area if cell_area > 0 else 0.0
        pct = max(0.0, min(1.0, pct))
        results.append(pct)

    grid[col_name] = results
    return grid


def write_gdf_with_fallback(gdf: gpd.GeoDataFrame, out_base: Path) -> str:
    """
    Bando rašyti parquet. Jei nepavyksta – rašo GeoJSON.
    Grąžina tikrą failo kelią.
    """
    parquet_path = out_base.with_suffix(".parquet")
    geojson_path = out_base.with_suffix(".geojson")

    try:
        gdf.to_parquet(parquet_path, index=False)
        return str(parquet_path)
    except Exception:
        gdf.to_file(geojson_path, driver="GeoJSON")
        return str(geojson_path)


def tile_filename(tile_bounds) -> str:
    xmin, ymin, xmax, ymax = tile_bounds
    return f"tile_{int(xmin)}_{int(ymin)}_{int(xmax)}_{int(ymax)}"


def process_tile(
    tile_bounds,
    layer_name: str,
    grid_size: int,
    simplify_tol_m: float,
) -> Optional[dict]:
    xmin, ymin, xmax, ymax = tile_bounds
    tile_geom = box(xmin, ymin, xmax, ymax)

    area = read_layer(GDB_VMT, LAYER_AREA, bbox_bounds=tile_bounds)
    forest = read_layer(GDB_VMT, LAYER_FOREST, bbox_bounds=tile_bounds)
    restr = read_layer(GDB_NATURA, LAYER_RESTR, bbox_bounds=tile_bounds)

    area = fix_invalid(simplify_geoms(area, simplify_tol_m))
    forest = fix_invalid(simplify_geoms(forest, simplify_tol_m))
    restr = fix_invalid(simplify_geoms(restr, simplify_tol_m))

    if area.empty:
        return None

    area = area[area.intersects(tile_geom)].copy()
    forest = forest[forest.intersects(tile_geom)].copy() if not forest.empty else forest
    restr = restr[restr.intersects(tile_geom)].copy() if not restr.empty else restr

    if area.empty:
        return None

    grid = build_grid_for_bounds(tile_bounds, grid_size)
    grid = gpd.sjoin(grid, area[["geometry"]], predicate="intersects", how="inner").drop(columns=["index_right"])
    grid = grid.drop_duplicates(subset=["cell_local_id"]).reset_index(drop=True)

    if grid.empty:
        return None

    grid["cell_area"] = grid.geometry.area
    grid = cover_pct_by_sindex(grid, forest, "forest_pct")
    grid = cover_pct_by_sindex(grid, restr, "restr_pct")

    grid["final_score"] = (0.7 * grid["forest_pct"] - 0.3 * grid["restr_pct"]).clip(lower=0.0, upper=1.0)
    grid["class"] = grid["final_score"].apply(classify)
    grid["tile_xmin"] = xmin
    grid["tile_ymin"] = ymin

    out = grid[[
        "geometry",
        "cell_local_id",
        "forest_pct",
        "restr_pct",
        "final_score",
        "class",
        "tile_xmin",
        "tile_ymin",
    ]].copy()

    out_base = get_tiles_dir(layer_name) / tile_filename(tile_bounds)
    actual_path = write_gdf_with_fallback(out, out_base)

    counts = out["class"].value_counts().to_dict()

    return {
        "tile_path": actual_path,
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
        "n_cells": int(len(out)),
        "avg_score": float(out["final_score"].mean()) if len(out) else 0.0,
        "green_count": int(counts.get("GREEN", 0)),
        "yellow_count": int(counts.get("YELLOW", 0)),
        "red_count": int(counts.get("RED", 0)),
        "geometry": tile_geom,
    }


def clear_old_tiles(layer_name: str) -> None:
    tiles_dir = get_tiles_dir(layer_name)
    for p in tiles_dir.glob("*"):
        try:
            if p.is_file():
                p.unlink()
        except Exception:
            pass


def run_analysis(
    layer_name: str = "coarse",
    grid_size: Optional[int] = None,
    tile_size: Optional[int] = None,
    simplify_tol_m: float = DEFAULT_SIMPLIFY_TOL_M,
    max_workers: int = MAX_WORKERS,
    clear_cache: bool = True,
    bbox: Optional[str] = None,
) -> dict:
    if layer_name not in {"coarse", "detail"}:
        raise ValueError("layer_name must be 'coarse' or 'detail'")

    if grid_size is None:
        grid_size = DEFAULT_DETAIL_GRID_SIZE_M if layer_name == "detail" else DEFAULT_COARSE_GRID_SIZE_M

    if tile_size is None:
        tile_size = DEFAULT_DETAIL_TILE_SIZE_M if layer_name == "detail" else DEFAULT_COARSE_TILE_SIZE_M

    t0 = time.perf_counter()
    write_status(layer_name, "running", "Reading area layer...")

    if clear_cache:
        clear_old_tiles(layer_name)

        for p in [
            get_tile_index_path(layer_name),
            get_tile_index_geojson_path(layer_name),
            get_metadata_path(layer_name),
        ]:
            if p.exists():
                p.unlink()

    area = read_layer(GDB_VMT, LAYER_AREA)
    area = fix_invalid(simplify_geoms(area, simplify_tol_m))

    if bbox:
        bounds = parse_bbox_string(bbox)
        bbox_geom = box(*bounds)
        area = area[area.intersects(bbox_geom)].copy()

    if area.empty:
        write_status(layer_name, "error", "No area after bbox filtering.")
        return {"ok": False, "layer": layer_name, "message": "No area after bbox filtering."}

    write_status(layer_name, "running", "Building tiles...")
    tiles = build_tiles(area, tile_size)

    results = []
    total = len(tiles)
    done = 0

    write_status(layer_name, "running", f"Processing {total} tiles in parallel...", {
        "tiles_total": total,
        "max_workers": max_workers,
    })

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_tile, tile, layer_name, grid_size, simplify_tol_m): tile
            for tile in tiles
        }

        for future in as_completed(futures):
            done += 1
            tile = futures[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"[WARN] Failed tile {tile}: {e}")

            write_status(layer_name, "running", f"Processed {done}/{total} tiles", {
                "tiles_done": done,
                "tiles_total": total,
                "max_workers": max_workers,
            })

    if not results:
        write_status(layer_name, "error", "No results generated.")
        return {"ok": False, "layer": layer_name, "message": "No results generated."}

    tile_index = gpd.GeoDataFrame(results, geometry="geometry", crs=CRS_METRIC)

    try:
        tile_index.to_parquet(get_tile_index_path(layer_name), index=False)
        tile_index_storage = "parquet"
    except Exception:
        tile_index.to_file(get_tile_index_geojson_path(layer_name), driver="GeoJSON")
        tile_index_storage = "geojson"

    metadata = {
        "ok": True,
        "layer": layer_name,
        "grid_size_m": grid_size,
        "tile_size_m": tile_size,
        "simplify_tol_m": simplify_tol_m,
        "max_workers": max_workers,
        "tiles_total": int(len(tile_index)),
        "cells_total": int(tile_index["n_cells"].sum()),
        "green_total": int(tile_index["green_count"].sum()),
        "yellow_total": int(tile_index["yellow_count"].sum()),
        "red_total": int(tile_index["red_count"].sum()),
        "tile_index_storage": tile_index_storage,
        "total_seconds": round(time.perf_counter() - t0, 2),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "bbox": bbox,
    }

    with open(get_metadata_path(layer_name), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    write_status(layer_name, "done", "Analysis completed.", metadata)
    return metadata