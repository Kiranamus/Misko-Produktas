import json
import math
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from shapely.geometry import box

from app.config import (
    GDB_DIRV,
    GDB_VMT,
    GDB_NATURA,
    SHP_ROADS,
    CRS_METRIC,
    LAYER_AREA,
    LAYER_FOREST,
    LAYER_RESTR,
    LAYER_DIRV,
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
#from app.api.routes import grid


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


def read_layer(gdb_path: Path, layer_name: str, bbox_bounds=None, columns=None) -> gpd.GeoDataFrame:
    read_kwargs = {"engine": "pyogrio", "bbox": bbox_bounds}

    if layer_name:
        read_kwargs["layer"] = layer_name
    else:
        try:
            if str(gdb_path).lower().endswith(".gdb"):
                detected = pyogrio.list_layers(str(gdb_path))
                if detected:
                    read_kwargs["layer"] = detected[0]
        except Exception:
            pass

    if columns is not None:
        read_kwargs["columns"] = columns

    gdf = gpd.read_file(gdb_path, **read_kwargs)

    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_METRIC)
    else:
        gdf = gdf.to_crs(CRS_METRIC)

    if "geometry" not in gdf.columns:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    if columns is None:
        gdf["geometry"] = gdf["geometry"].apply(lambda geom: geom.to_2d() if hasattr(geom, "to_2d") else geom)
        return gdf
    else:
        gdf["geometry"] = gdf["geometry"].apply(lambda geom: geom.to_2d() if hasattr(geom, "to_2d") else geom)
        return gdf["geometry"].to_frame().copy()


def read_vector(path: Path, bbox_bounds=None) -> gpd.GeoDataFrame:
    if not path.exists():
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    gdf = gpd.read_file(path, bbox=bbox_bounds)

    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_METRIC)
    else:
        gdf = gdf.to_crs(CRS_METRIC)

    if "geometry" not in gdf.columns:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    gdf["geometry"] = gdf["geometry"].apply(lambda g: g.to_2d() if hasattr(g, "to_2d") else g)
    return gdf[["geometry"]].copy()


# 🔥 FIXED ROAD SCORE (exponential)
def calculate_road_score(grid, roads):
    if roads is None or roads.empty or grid.empty:
        return pd.Series(np.zeros(len(grid)), index=grid.index)

    roads = roads.unary_union

    def score(geom):
        if geom is None or geom.is_empty:
            return 0.0
        dist = geom.distance(roads)
        return float(math.exp(-dist / 1000))

    return grid.geometry.apply(score)


def cover_pct_by_sindex(grid: gpd.GeoDataFrame, layer: gpd.GeoDataFrame, col_name: str) -> gpd.GeoDataFrame:
    grid = grid.copy()

    if layer is None or layer.empty or grid.empty:
        grid[col_name] = 0.0
        return grid

    layer = layer[layer.geometry.notna() & ~layer.geometry.is_empty].copy()
    if layer.empty:
        grid[col_name] = 0.0
        return grid

    sidx = layer.sindex
    results = []
    cell_areas = grid.geometry.area

    for geom, area in zip(grid.geometry, cell_areas):
        if geom is None or geom.is_empty:
            results.append(0.0)
            continue

        candidate_idx = list(sidx.intersection(geom.bounds))
        if not candidate_idx:
            results.append(0.0)
            continue

        candidates = layer.iloc[candidate_idx]
        inter = candidates.intersection(geom)
        covered_area = inter.area.sum() if len(inter) else 0.0

        results.append(float(max(0.0, min(1.0, covered_area / (area if area > 0 else 1.0)))))

    grid[col_name] = results
    return grid

def soil_weighted_average(grid: gpd.GeoDataFrame, soil: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()

    if soil is None or soil.empty or grid.empty:
        grid["soil_index"] = 0.5
        return grid

    soil = soil[soil.geometry.notna() & ~soil.geometry.is_empty].copy()
    if soil.empty:
        grid["soil_index"] = 0.5
        return grid

    sidx = soil.sindex
    results = []

    for geom in grid.geometry:
        if geom is None or geom.is_empty:
            results.append(0.5)
            continue

        candidate_idx = list(sidx.intersection(geom.bounds))
        if not candidate_idx:
            results.append(0.5)
            continue

        candidates = soil.iloc[candidate_idx].copy()
        inter = candidates.intersection(geom)

        candidates["inter_area"] = inter.area
        total_area = candidates["inter_area"].sum()

        if total_area == 0:
            results.append(0.5)
            continue

        weighted = (candidates["soil_index"] * candidates["inter_area"]).sum() / total_area
        results.append(float(weighted))

    grid["soil_index"] = results
    return grid


def simplify_geoms(gdf, tol):
    if gdf.empty or tol <= 0:
        return gdf
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(tol, preserve_topology=True)
    return gdf


def fix_invalid(gdf):
    if gdf.empty:
        return gdf
    gdf = gdf.copy()
    invalid = ~gdf.geometry.is_valid
    if invalid.any():
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid].buffer(0)
    return gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]


def aggregate_point_scores(grid: gpd.GeoDataFrame, points: gpd.GeoDataFrame, score_col: str, default: float = 0.0) -> gpd.GeoDataFrame:
    grid = grid.copy()

    if points is None or points.empty or grid.empty:
        grid[score_col] = default
        return grid

    points = points[points.geometry.notna() & ~points.geometry.is_empty].copy()
    if points.empty:
        grid[score_col] = default
        return grid

    pts = points.sjoin(grid[["cell_local_id", "geometry"]], predicate="within", how="inner")
    if pts.empty:
        grid[score_col] = default
        return grid

    mapping = pts.groupby("cell_local_id")[score_col].mean()
    grid[score_col] = grid["cell_local_id"].map(mapping).fillna(default)
    return grid


def compute_soil_scores(soil_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if soil_gdf is None or soil_gdf.empty:
        return soil_gdf

    soil_gdf = soil_gdf.copy()

    for col in ["TEX_F", "TEX_K", "PH_L", "DRA", "TOP", "LAEL", "SLGR", "ABST", "SIST"]:
        if col not in soil_gdf.columns:
            soil_gdf[col] = np.nan

    tex_f_map = {
        's': 0.1, 's1': 0.2, 'ps': 0.3, 'sp': 0.4, 'sp2': 0.5,
        'p1': 0.6, 'p2': 0.7, 'dps': 0.8, 'da': 0.85, 'dp': 0.9,
        'dp1': 0.92, 'dp2': 0.94, 'sm': 0.95, 'dm': 0.97, 'm': 1.0,
    }
    tex_k_map = {
        'z': 0.05, 's': 0.1, 's1': 0.2, 'ps': 0.3, 'p': 0.4,
        'p1': 0.5, 'p2': 0.6, 'm': 0.7, 'm1': 0.8, 'm2': 0.9,
        'pv': 0.95, 'd': 0.1,
    }
    top_map = {'F': 1.0, 'A': 0.95, 'G': 0.85, 'U': 0.7, 'R': 0.5, 'H': 0.3, 'S': 0.2}
    lael_map = {'PL': 1.0, 'WW': 0.9, 'HI': 0.8, 'RV': 0.7, 'VA': 0.6, 'DE': 0.5, 'IF': 0.4, 'DU': 0.3, 'ID': 0.2, 'SL': 0.4, 'OR': 0.3, 'TE': 0.5}
    slgr_map = {1: 1.0, 2: 0.95, 3: 0.85, 4: 0.7, 5: 0.5, 6: 0.3, 7: 0.1}
    abst_map = {'n': 1.0, 'v': 0.9, 'f': 0.8, 'c': 0.5, 'm': 0.2}
    sist_map = {'c': 1.0, 's': 0.9, 'b': 0.7, 'l': 0.4}

    soil_gdf['tex_f_score'] = soil_gdf['TEX_F'].astype(str).str.lower().apply(lambda v: tex_f_map.get(v, 0.5))
    soil_gdf['tex_k_score'] = soil_gdf['TEX_K'].astype(str).str.lower().apply(lambda v: tex_k_map.get(v, 0.5))

    def ph_score(ph):
        try:
            ph = float(ph)
        except Exception:
            return 0.5
        if 6.0 <= ph <= 7.0:
            return 1.0
        if 4.0 <= ph < 6.0:
            return max(0.0, min(1.0, (ph - 4.0) / 2.0))
        if 7.0 < ph <= 9.0:
            return max(0.0, min(1.0, (9.0 - ph) / 2.0))
        return 0.0

    soil_gdf['ph_score'] = soil_gdf['PH_L'].apply(ph_score)

    def dra_score(v):
        try:
            d = float(v)
        except Exception:
            return 0.5
        if d < 0:
            d = 0
        if d > 5:
            d = 5
        return 1.0 - d / 5.0

    soil_gdf['dra_score'] = soil_gdf['DRA'].apply(dra_score)
    soil_gdf['top_score'] = soil_gdf['TOP'].astype(str).str.upper().apply(lambda v: top_map.get(v, 0.5))
    soil_gdf['lael_score'] = soil_gdf['LAEL'].astype(str).str.upper().apply(lambda v: lael_map.get(v, 0.5))
    soil_gdf['slgr_score'] = soil_gdf['SLGR'].apply(lambda v: slgr_map.get(int(v), 0.5) if pd.notna(v) and str(v).isdigit() else 0.5)
    soil_gdf['abst_score'] = soil_gdf['ABST'].astype(str).str.lower().apply(lambda v: abst_map.get(v, 0.5))
    soil_gdf['sist_score'] = soil_gdf['SIST'].astype(str).str.lower().apply(lambda v: sist_map.get(v, 0.5))

    score_cols = ['tex_f_score', 'tex_k_score', 'ph_score', 'dra_score', 'top_score', 'lael_score', 'slgr_score', 'abst_score', 'sist_score']
    soil_gdf['soil_index'] = soil_gdf[score_cols].mean(axis=1)
    return soil_gdf


def tile_filename(tile_bounds):
    xmin, ymin, xmax, ymax = tile_bounds
    return f"tile_{int(xmin)}_{int(ymin)}_{int(xmax)}_{int(ymax)}"


def write_gdf_with_fallback(gdf: gpd.GeoDataFrame, out_base: Path) -> str:
    parquet_path = out_base.with_suffix('.parquet')
    geojson_path = out_base.with_suffix('.geojson')
    try:
        gdf.to_parquet(parquet_path, index=False)
        return str(parquet_path)
    except Exception:
        gdf.to_file(geojson_path, driver='GeoJSON')
        return str(geojson_path)


def parse_bbox_string(bbox_str: str):
    vals = [float(v.strip()) for v in bbox_str.split(",")]
    if len(vals) != 4:
        raise ValueError("bbox must be minx,miny,maxx,maxy in EPSG:3346")
    return tuple(vals)


def classify(score: float) -> str:
    if score >= TH_GREEN:
        return "GREEN"
    if score >= TH_YELLOW:
        return "YELLOW"
    return "RED"


def build_grid_for_bounds(bounds, size):
    minx, miny, maxx, maxy = bounds
    cells = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cells.append(box(x, y, x + size, y + size))
            y += size
        x += size
    return gpd.GeoDataFrame(geometry=cells, crs=CRS_METRIC)


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


def process_tile(tile_bounds, layer_name, grid_size, simplify_tol_m):
    xmin, ymin, xmax, ymax = tile_bounds

    area = read_layer(GDB_VMT, LAYER_AREA, bbox_bounds=tile_bounds)
    forest = read_layer(GDB_VMT, LAYER_FOREST, bbox_bounds=tile_bounds)
    n2000_uk = read_layer(GDB_NATURA, "UK_teritorijos", bbox_bounds=tile_bounds)
    n2000_pk = read_layer(GDB_NATURA, "PK_teritorijos", bbox_bounds=tile_bounds)
    n2000_nm = read_layer(GDB_NATURA, "NM_teritorijos", bbox_bounds=tile_bounds)
    n2000_dm = read_layer(GDB_NATURA, "DM_teritorijos", bbox_bounds=tile_bounds)
    soil = read_layer(GDB_DIRV, LAYER_DIRV, bbox_bounds=tile_bounds)
    roads = read_vector(SHP_ROADS, bbox_bounds=tile_bounds)

    area = fix_invalid(simplify_geoms(area, simplify_tol_m))
    forest = fix_invalid(simplify_geoms(forest, simplify_tol_m))
    n2000_uk = fix_invalid(simplify_geoms(n2000_uk, simplify_tol_m))
    n2000_pk = fix_invalid(simplify_geoms(n2000_pk, simplify_tol_m))
    n2000_nm = fix_invalid(simplify_geoms(n2000_nm, simplify_tol_m))
    n2000_dm = fix_invalid(simplify_geoms(n2000_dm, simplify_tol_m))
    soil = fix_invalid(simplify_geoms(soil, simplify_tol_m))
    roads = fix_invalid(simplify_geoms(roads, simplify_tol_m))

    n2000 = gpd.GeoDataFrame(
        pd.concat([n2000_uk, n2000_pk, n2000_nm, n2000_dm], ignore_index=True),
        crs=CRS_METRIC,
    ) if any(not g.empty for g in [n2000_uk, n2000_pk, n2000_nm, n2000_dm]) else gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    if not n2000.empty:
        n2000 = n2000.dissolve().reset_index(drop=True)

    if area.empty and forest.empty and n2000.empty and soil.empty and roads.empty:
        return None

    grid = build_grid_for_bounds(tile_bounds, grid_size)
    grid = grid.reset_index(drop=True)               # saugumo sumetimais
    grid["cell_local_id"] = range(len(grid))
    if grid.empty:
        return None

    grid["cell_area"] = grid.geometry.area

    grid = cover_pct_by_sindex(grid, forest, "forest_pct")
    grid = cover_pct_by_sindex(grid, area, "valstybinis_pct")
    grid = cover_pct_by_sindex(grid, n2000, "n2000_pct")

    if not forest.empty:
        for i in [1, 2, 3, 4]:
            subset = forest[forest.get("grupe") == i] if "grupe" in forest.columns else gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)
            grid = cover_pct_by_sindex(grid, subset, f"grp{i}_pct")
    else:
        grid[["grp1_pct", "grp2_pct", "grp3_pct", "grp4_pct"]]=0.0

    for c in ["forest_pct", "valstybinis_pct", "n2000_pct", "grp1_pct", "grp2_pct", "grp3_pct", "grp4_pct"]:
        if c not in grid.columns:
            grid[c] = 0.0

    grid["n2000_index"] = (1.0 - grid["n2000_pct"]).clip(0.0, 1.0)

    forest_pct = grid["forest_pct"].fillna(0.0)
    valstybinis_pct = grid["valstybinis_pct"].fillna(0.0)

    groups_score = (
        0.1 * grid["grp1_pct"].fillna(0.0)
        + 0.4 * grid["grp2_pct"].fillna(0.0)
        + 0.7 * grid["grp3_pct"].fillna(0.0)
        + 1.0 * grid["grp4_pct"].fillna(0.0)
    )

    vmt_index = np.zeros(len(grid))
    nonzero = forest_pct > 1e-9
    vmt_index[nonzero] = (
        0.4 * forest_pct[nonzero]
        + 0.2 * (1.0 - (valstybinis_pct[nonzero] / forest_pct[nonzero]).clip(0.0, 1.0))
        + 0.4 * (groups_score[nonzero] / forest_pct[nonzero]).clip(0.0, 1.0)
    )
    grid["vmt_index"] = np.clip(vmt_index, 0.0, 1.0)

    if not soil.empty:
        soil = compute_soil_scores(soil)

    grid = soil_weighted_average(grid, soil)
    grid["road_score"] = calculate_road_score(grid, roads)
    #grid["restrictions_index"] = ((grid["n2000_index"].fillna(0.0) + grid["vmt_index"].fillna(0.0)) / 2.0).clip(0.0, 1.0)
    #grid["final_score"] = ((grid["restrictions_index"].fillna(0.0) + grid["soil_index"].fillna(0.0) + grid["road_score"].fillna(0.0)) / 3.0).clip(0.0, 1.0)

    grid["restrictions_index"] = (
    (grid["n2000_index"].fillna(0.0) + grid["vmt_index"].fillna(0.0)) / 2.0).clip(0.0, 1.0)

# ←←← NAUJA LOGIKA ←←←
    has_forest = grid["forest_pct"] > 0.2                     # minimalus slenkstis (5%)
    grid["final_score"] = 0.0

    grid.loc[has_forest, "final_score"] = (
    grid.loc[has_forest, "forest_pct"]
    * (
        grid.loc[has_forest, "restrictions_index"] * 0.4
        + grid.loc[has_forest, "soil_index"] * 0.3
        + grid.loc[has_forest, "road_score"] * 0.3
    )).clip(0.0, 1.0)

    grid = grid[grid["final_score"] >= 0.05].copy()

    grid["class"] = grid["final_score"].apply(classify)
    grid["tile_xmin"] = xmin
    grid["tile_ymin"] = ymin

    out = grid[[
        "geometry",
        "cell_local_id",
        "forest_pct",
        "valstybinis_pct",
        "n2000_pct",
        "n2000_index",
        "vmt_index",
        "restrictions_index",
        "soil_index",
        "road_score",
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
        "geometry": box(xmin, ymin, xmax, ymax),
    }


def run_analysis():
    tiles = [(0, 0, 10000, 10000)]
    results = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(process_tile, t, "coarse", 1000, 0) for t in tiles]
        for f in as_completed(futures):
            results.append(f.result())

    return results


def clear_old_tiles(layer_name: str) -> None:
    tiles_dir = get_tiles_dir(layer_name)
    if tiles_dir.exists():
        for f in tiles_dir.glob("*"):
            if f.is_file():
                f.unlink()


def process_analysis(
    layer_name: str,
    grid_size: int,
    tile_size: int,
    simplify_tol_m: float,
    max_workers: int,
    clear_cache: bool,
    bbox: Optional[str],
) -> dict:

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

    forest = read_layer(GDB_VMT, LAYER_FOREST)
    forest = fix_invalid(simplify_geoms(forest, simplify_tol_m))

    if bbox:
        bounds = parse_bbox_string(bbox)
        bbox_geom = box(*bounds)
        area = area[area.intersects(bbox_geom)].copy()

    if area.empty:
        write_status(layer_name, "error", "No area after bbox filtering.")
        return {"ok": False, "layer": layer_name, "message": "No area after bbox filtering."}

    write_status(layer_name, "running", "Building tiles...")
    
    tiles = build_tiles(forest, tile_size)

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