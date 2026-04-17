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
    GDB_CLC,
    GDB_STATS,
    GDB_VMT,
    GDB_NATURA,
    SHP_ROADS,
    CRS_METRIC,
    LAYER_AREA,
    LAYER_FOREST,
    LAYER_DIRV,
    LAYER_DIRV_PROFILE,
    LAYER_CLC,
    LAYER_MUNICIPALITY_2022,
    MAX_WORKERS,
    DEFAULT_COARSE_GRID_SIZE_M,
    DEFAULT_COARSE_TILE_SIZE_M,
    DEFAULT_DETAIL_GRID_SIZE_M,
    DEFAULT_DETAIL_TILE_SIZE_M,
    get_tiles_dir,
    get_tile_index_path,
    get_tile_index_geojson_path,
    get_status_path,
    get_metadata_path,
)
from app.utils.geo import parse_bbox_string


# Status and metadata helpers
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


# IO helpers
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


def prepare_layer(gdf: gpd.GeoDataFrame, simplify_tol_m: float) -> gpd.GeoDataFrame:
    return fix_invalid(simplify_geoms(gdf, simplify_tol_m))


def prepare_layers(layer_map: dict[str, gpd.GeoDataFrame], simplify_tol_m: float) -> dict[str, gpd.GeoDataFrame]:
    return {
        name: prepare_layer(gdf, simplify_tol_m)
        for name, gdf in layer_map.items()
    }


# Geometry and scoring helpers
def calculate_road_score(grid, roads):
    if roads is None or roads.empty or grid.empty:
        return pd.Series(np.zeros(len(grid)), index=grid.index)

    roads_union = roads.unary_union

    def score(geom):
        if geom is None or geom.is_empty:
            return 0.0
        dist = geom.distance(roads_union)
        return float(1.0 / (1.0 + dist / 1500.0))

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

def soil_weighted_texture(grid: gpd.GeoDataFrame, soil: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()

    if soil is None or soil.empty or grid.empty:
        grid["tex_score"] = 0.0
        return grid

    soil = soil[soil.geometry.notna() & ~soil.geometry.is_empty].copy()
    if soil.empty:
        grid["tex_score"] = 0.0
        return grid

    sidx = soil.sindex
    results = []

    for geom in grid.geometry:
        if geom is None or geom.is_empty:
            results.append(0.0)
            continue

        candidate_idx = list(sidx.intersection(geom.bounds))
        if not candidate_idx:
            results.append(0.0)
            continue

        candidates = soil.iloc[candidate_idx].copy()
        inter = candidates.intersection(geom)

        candidates["inter_area"] = inter.area
        total_area = candidates["inter_area"].sum()

        if total_area == 0:
            results.append(0.0)
            continue

        weighted = (candidates["tex_score"] * candidates["inter_area"]).sum() / total_area
        results.append(float(weighted))

    grid["tex_score"] = results
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


# Soil scoring
def compute_soil_texture_scores(soil_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if soil_gdf is None or soil_gdf.empty:
        return soil_gdf

    soil_gdf = soil_gdf.copy()

    for col in ["TEX_K_P", "TEX_K_D", "TEX_F_P", "TEX_F_D"]:
        if col not in soil_gdf.columns:
            soil_gdf[col] = None

    tex_map = {
        "z": 5.0,
        "s": 10.0,
        "s1": 20.0,
        "ps": 30.0,
        "sp": 40.0,
        "sp2": 50.0,
        "p": 55.0,
        "p1": 60.0,
        "p2": 70.0,
        "dps": 80.0,
        "da": 85.0,
        "dp": 90.0,
        "dp1": 92.0,
        "dp2": 94.0,
        "sm": 95.0,
        "dm": 97.0,
        "m": 100.0,
    }

    def score_tex(value):
        if value is None:
            return 0.0
        value = str(value).strip().lower()
        if not value:
            return 0.0
        return tex_map.get(value, 0.0)

    soil_gdf["tex_k_p_score"] = soil_gdf["TEX_K_P"].apply(score_tex)
    soil_gdf["tex_k_d_score"] = soil_gdf["TEX_K_D"].apply(score_tex)
    soil_gdf["tex_f_p_score"] = soil_gdf["TEX_F_P"].apply(score_tex)
    soil_gdf["tex_f_d_score"] = soil_gdf["TEX_F_D"].apply(score_tex)
    soil_gdf["tex_score"] = soil_gdf[
        ["tex_k_p_score", "tex_k_d_score", "tex_f_p_score", "tex_f_d_score"]
    ].mean(axis=1).fillna(0.0).clip(0.0, 100.0)

    return soil_gdf


def compute_profile_scores(profile_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if profile_gdf is None or profile_gdf.empty:
        return profile_gdf

    profile_gdf = profile_gdf.copy()

    for col in ["DRA", "PH_L", "TOP", "LAEL", "SLGR", "ABST", "SIST"]:
        if col not in profile_gdf.columns:
            profile_gdf[col] = None

    dra_map = {
        "0": 100.0,
        "1": 100.0,
        "2": 75.0,
        "3": 50.0,
        "4": 25.0,
        "5": 0.0,
        "E": 100.0,
        "S": 100.0,
        "W": 100.0,
        "M": 75.0,
        "I": 50.0,
        "P": 25.0,
        "V": 0.0,
    }
    top_map = {
        "F": 100.0,
        "A": 100.0,
        "G": 100.0,
        "U": 75.0,
        "R": 50.0,
        "H": 50.0,
        "S": 25.0,
    }
    lael_map = {
        "PL": 100.0,
        "WW": 100.0,
        "IF": 100.0,
        "TE": 100.0,
        "HI": 75.0,
        "DU": 75.0,
        "SL": 50.0,
        "OR": 50.0,
        "RV": 50.0,
        "DE": 25.0,
        "VA": 25.0,
        "ID": 25.0,
    }
    abst_map = {
        "N": 100.0,
        "V": 100.0,
        "F": 75.0,
        "C": 50.0,
        "M": 25.0,
    }
    sist_map = {
        "C": 100.0,
        "S": 100.0,
        "B": 50.0,
        "L": 25.0,
    }

    def clean_str(value):
        if value is None:
            return ""
        return str(value).strip().upper()

    def dra_score(value):
        return dra_map.get(clean_str(value), 0.0)

    def ph_score(value):
        try:
            v = float(value)
        except Exception:
            return 0.0
        if 5.5 <= v <= 7.0:
            return 100.0
        if 5.0 <= v < 5.5 or 7.0 < v <= 7.5:
            return 75.0
        if 4.5 <= v < 5.0 or 7.5 < v <= 8.0:
            return 50.0
        return 25.0

    def slgr_score(value):
        try:
            v = int(float(value))
        except Exception:
            return 0.0
        if 1 <= v <= 3:
            return 100.0
        if v == 4:
            return 75.0
        if v == 5:
            return 50.0
        if 6 <= v <= 7:
            return 25.0
        return 0.0

    profile_gdf["dra_score"] = profile_gdf["DRA"].apply(dra_score)
    profile_gdf["ph_score"] = profile_gdf["PH_L"].apply(ph_score)
    profile_gdf["top_score"] = profile_gdf["TOP"].apply(lambda v: top_map.get(clean_str(v), 0.0))
    profile_gdf["lael_score"] = profile_gdf["LAEL"].apply(lambda v: lael_map.get(clean_str(v), 0.0))
    profile_gdf["slgr_score"] = profile_gdf["SLGR"].apply(slgr_score)
    profile_gdf["abst_score"] = profile_gdf["ABST"].apply(lambda v: abst_map.get(clean_str(v), 0.0))
    profile_gdf["sist_score"] = profile_gdf["SIST"].apply(lambda v: sist_map.get(clean_str(v), 0.0))
    profile_gdf["reljef_score"] = profile_gdf[
        ["top_score", "lael_score", "slgr_score"]
    ].mean(axis=1).fillna(0.0)
    profile_gdf["akmen_score"] = profile_gdf[
        ["abst_score", "sist_score"]
    ].mean(axis=1).fillna(0.0)

    return profile_gdf


def aggregate_profile_scores(grid: gpd.GeoDataFrame, profile_points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    score_cols = ["dra_score", "ph_score", "reljef_score", "akmen_score"]

    for col in score_cols:
        grid[col] = 0.0

    if profile_points is None or profile_points.empty or grid.empty:
        return grid

    profile_points = profile_points[profile_points.geometry.notna() & ~profile_points.geometry.is_empty].copy()
    if profile_points.empty:
        return grid

    pts = profile_points.sjoin(grid[["cell_local_id", "geometry"]], predicate="within", how="inner")
    if pts.empty:
        return grid

    grouped = pts.groupby("cell_local_id")[score_cols].mean()
    for col in score_cols:
        grid[col] = grid["cell_local_id"].map(grouped[col]).fillna(0.0)

    return grid


def build_soil_index(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()

    for col in ["tex_score", "dra_score", "ph_score", "reljef_score", "akmen_score"]:
        if col not in grid.columns:
            grid[col] = 0.0

    soil_score_100 = np.round(
        grid["tex_score"].fillna(0.0) * 0.40
        + grid["ph_score"].fillna(0.0) * 0.20
        + grid["reljef_score"].fillna(0.0) * 0.20
        + grid["akmen_score"].fillna(0.0) * 0.20,
        0,
    )

    grid["soil_index_raw"] = soil_score_100.clip(0.0, 100.0)
    grid["soil_index"] = (grid["soil_index_raw"] / 100.0).clip(0.0, 1.0)
    return grid


def assign_admin_areas(grid: gpd.GeoDataFrame, admin_layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    grid["municipality"] = None
    grid["county"] = None

    if admin_layer is None or admin_layer.empty or grid.empty or "Savivaldybe" not in admin_layer.columns:
        return grid

    admin_layer = admin_layer[admin_layer.geometry.notna() & ~admin_layer.geometry.is_empty].copy()
    if admin_layer.empty:
        return grid

    county_by_municipality = {
        "Alytaus m. sav.": "Alytaus apskritis",
        "Alytaus r. sav.": "Alytaus apskritis",
        "Druskininkų sav.": "Alytaus apskritis",
        "Lazdijų r. sav.": "Alytaus apskritis",
        "Varėnos r. sav.": "Alytaus apskritis",
        "Kauno m. sav.": "Kauno apskritis",
        "Kauno r. sav.": "Kauno apskritis",
        "Jonavos r. sav.": "Kauno apskritis",
        "Kaišiadorių r. sav.": "Kauno apskritis",
        "Kėdainių r. sav.": "Kauno apskritis",
        "Prienų r. sav.": "Kauno apskritis",
        "Birštono sav.": "Kauno apskritis",
        "Klaipėdos m. sav.": "Klaipėdos apskritis",
        "Klaipėdos r. sav.": "Klaipėdos apskritis",
        "Kretingos r. sav.": "Klaipėdos apskritis",
        "Skuodo r. sav.": "Klaipėdos apskritis",
        "Šilutės r. sav.": "Klaipėdos apskritis",
        "Neringos sav.": "Klaipėdos apskritis",
        "Palangos m. sav.": "Klaipėdos apskritis",
        "Marijampolės sav.": "Marijampolės apskritis",
        "Vilkaviškio r. sav.": "Marijampolės apskritis",
        "Šakių r. sav.": "Marijampolės apskritis",
        "Kalvarijos sav.": "Marijampolės apskritis",
        "Kazlų Rūdos sav.": "Marijampolės apskritis",
        "Panevėžio r. sav.": "Panevėžio apskritis",
        "Biržų r. sav.": "Panevėžio apskritis",
        "Kupiškio r. sav.": "Panevėžio apskritis",
        "Pasvalio r. sav.": "Panevėžio apskritis",
        "Rokiškio r. sav.": "Panevėžio apskritis",
        "Panevėžio m. sav.": "Panevėžio apskritis",
        "Šiaulių m. sav.": "Šiaulių apskritis",
        "Šiaulių r. sav.": "Šiaulių apskritis",
        "Akmenės r. sav.": "Šiaulių apskritis",
        "Joniškio r. sav.": "Šiaulių apskritis",
        "Kelmės r. sav.": "Šiaulių apskritis",
        "Pakruojo r. sav.": "Šiaulių apskritis",
        "Radviliškio r. sav.": "Šiaulių apskritis",
        "Tauragės r. sav.": "Tauragės apskritis",
        "Šilalės r. sav.": "Tauragės apskritis",
        "Jurbarko r. sav.": "Tauragės apskritis",
        "Pagėgių sav.": "Tauragės apskritis",
        "Telšių r. sav.": "Telšių apskritis",
        "Mažeikių r. sav.": "Telšių apskritis",
        "Plungės r. sav.": "Telšių apskritis",
        "Rietavo sav.": "Telšių apskritis",
        "Utenos r. sav.": "Utenos apskritis",
        "Molėtų r. sav.": "Utenos apskritis",
        "Ignalinos r. sav.": "Utenos apskritis",
        "Zarasų r. sav.": "Utenos apskritis",
        "Visagino sav.": "Utenos apskritis",
        "Anykščių r. sav.": "Utenos apskritis",
        "Vilniaus m. sav.": "Vilniaus apskritis",
        "Vilniaus r. sav.": "Vilniaus apskritis",
        "Elektrėnų sav.": "Vilniaus apskritis",
        "Trakų r. sav.": "Vilniaus apskritis",
        "Ukmergės r. sav.": "Vilniaus apskritis",
        "Širvintų r. sav.": "Vilniaus apskritis",
        "Šalčininkų r. sav.": "Vilniaus apskritis",
        "Švenčionių r. sav.": "Vilniaus apskritis",
    }

    sidx = admin_layer.sindex
    municipalities = []
    counties = []

    for geom in grid.geometry:
        if geom is None or geom.is_empty:
            municipalities.append(None)
            counties.append(None)
            continue

        candidate_idx = list(sidx.intersection(geom.bounds))
        if not candidate_idx:
            municipalities.append(None)
            counties.append(None)
            continue

        candidates = admin_layer.iloc[candidate_idx].copy()
        inter = candidates.intersection(geom)
        candidates["inter_area"] = inter.area
        candidates = candidates[candidates["inter_area"] > 0].copy()
        if candidates.empty:
            municipalities.append(None)
            counties.append(None)
            continue

        municipality = (
            candidates.groupby("Savivaldybe")["inter_area"]
            .sum()
            .sort_values(ascending=False)
            .index[0]
        )
        municipality = str(municipality).strip().strip('"')
        municipality = " ".join(municipality.split())
        municipalities.append(municipality)
        counties.append(county_by_municipality.get(municipality))

    grid["municipality"] = municipalities
    grid["county"] = counties
    return grid


def assign_dominant_forest_type(grid: gpd.GeoDataFrame, clc: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    grid["forest_type"] = None

    if clc is None or clc.empty or grid.empty:
        return grid

    clc = clc[clc.geometry.notna() & ~clc.geometry.is_empty].copy()
    if clc.empty:
        return grid

    code_col = None
    for candidate in ["Code_18", "code_18", "CODE_18"]:
        if candidate in clc.columns:
            code_col = candidate
            break
    if code_col is None:
        return grid

    type_map = {
        "311": "Lapuočių miškai",
        "312": "Spygliuočių miškai",
        "313": "Mišrūs miškai",
    }

    clc["forest_type"] = clc[code_col].astype(str).str.strip().map(type_map)
    clc = clc[clc["forest_type"].notna()].copy()
    if clc.empty:
        return grid

    sidx = clc.sindex
    results = []

    for geom in grid.geometry:
        if geom is None or geom.is_empty:
            results.append(None)
            continue

        candidate_idx = list(sidx.intersection(geom.bounds))
        if not candidate_idx:
            results.append(None)
            continue

        candidates = clc.iloc[candidate_idx].copy()
        inter = candidates.intersection(geom)
        candidates["inter_area"] = inter.area
        candidates = candidates[candidates["inter_area"] > 0].copy()

        if candidates.empty:
            results.append(None)
            continue

        dominant = (
            candidates.groupby("forest_type")["inter_area"]
            .sum()
            .sort_values(ascending=False)
            .index[0]
        )
        results.append(dominant)

    grid["forest_type"] = results
    return grid


# Grid building and export
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


def combine_natura_layers(*layers: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    non_empty_layers = [layer for layer in layers if not layer.empty]
    if not non_empty_layers:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    natura = gpd.GeoDataFrame(pd.concat(non_empty_layers, ignore_index=True), crs=CRS_METRIC)
    return natura.dissolve().reset_index(drop=True) if not natura.empty else natura


def apply_forest_group_coverages(grid: gpd.GeoDataFrame, forest: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()

    if forest.empty:
        grid[["grp1_pct", "grp2_pct", "grp3_pct", "grp4_pct"]] = 0.0
        return grid

    for group_number in [1, 2, 3, 4]:
        subset = (
            forest[forest.get("grupe") == group_number]
            if "grupe" in forest.columns
            else gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)
        )
        grid = cover_pct_by_sindex(grid, subset, f"grp{group_number}_pct")

    return grid


def ensure_coverage_columns(grid: gpd.GeoDataFrame, columns: list[str]) -> gpd.GeoDataFrame:
    grid = grid.copy()
    for column in columns:
        if column not in grid.columns:
            grid[column] = 0.0
    return grid


def calculate_vmt_index(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
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
    return grid


def calculate_restrictions_index(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    grid["restrictions_index"] = (
        (grid["n2000_index"] + grid["vmt_index"]) / 2.0
    ).clip(0.0, 1.0)
    grid["restrictions_index"] = np.power(
        grid["restrictions_index"],
        (1 - grid["restrictions_index"]) * 10,
    )
    return grid


def calculate_preview_final_score(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    grid["final_score"] = (
        (
            np.power(grid["restrictions_index"].fillna(0.0), 1.8) * 0.4
            + np.power(grid["soil_index"].fillna(0.0), 1.25) * 0.3
            + np.power(grid["road_score"].fillna(0.0), 1.15) * 0.3
        )
        * np.where(grid["restrictions_index"].fillna(0.0) < 0.35, 0.5, 1.0)
    ).clip(0.0, 1.0)
    return grid


def build_tile_payload(grid: gpd.GeoDataFrame, xmin: float, ymin: float) -> gpd.GeoDataFrame:
    grid = grid.copy()
    grid["tile_xmin"] = xmin
    grid["tile_ymin"] = ymin

    return grid[
        [
            "geometry",
            "cell_local_id",
            "forest_pct",
            "tex_score",
            "dra_score",
            "ph_score",
            "reljef_score",
            "akmen_score",
            "soil_index_raw",
            "restrictions_index",
            "soil_index",
            "road_score",
            "forest_type",
            "municipality",
            "county",
            "final_score",
            "tile_xmin",
            "tile_ymin",
        ]
    ].copy()


def build_tile_result(out: gpd.GeoDataFrame, actual_path: str, tile_bounds: tuple[float, float, float, float]) -> dict:
    xmin, ymin, xmax, ymax = tile_bounds
    return {
        "tile_path": actual_path,
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
        "n_cells": int(len(out)),
        "avg_score": float(out["final_score"].mean()) if len(out) else 0.0,
        "green_count": int((out["final_score"] >= 0.66).sum()),
        "yellow_count": int(((out["final_score"] >= 0.33) & (out["final_score"] < 0.66)).sum()),
        "red_count": int((out["final_score"] < 0.33).sum()),
        "geometry": box(xmin, ymin, xmax, ymax),
    }


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

    layers = prepare_layers(
        {
            "area": read_layer(GDB_VMT, LAYER_AREA, bbox_bounds=tile_bounds),
            "forest": read_layer(GDB_VMT, LAYER_FOREST, bbox_bounds=tile_bounds),
            "n2000_uk": read_layer(GDB_NATURA, "UK_teritorijos", bbox_bounds=tile_bounds),
            "n2000_pk": read_layer(GDB_NATURA, "PK_teritorijos", bbox_bounds=tile_bounds),
            "n2000_nm": read_layer(GDB_NATURA, "NM_teritorijos", bbox_bounds=tile_bounds),
            "n2000_dm": read_layer(GDB_NATURA, "DM_teritorijos", bbox_bounds=tile_bounds),
            "admin_2022": read_layer(GDB_STATS, LAYER_MUNICIPALITY_2022, bbox_bounds=tile_bounds),
            "soil": read_layer(GDB_DIRV, LAYER_DIRV, bbox_bounds=tile_bounds),
            "soil_profile": read_layer(GDB_DIRV, LAYER_DIRV_PROFILE, bbox_bounds=tile_bounds),
            "clc": read_layer(GDB_CLC, LAYER_CLC, bbox_bounds=tile_bounds),
            "roads": read_vector(SHP_ROADS, bbox_bounds=tile_bounds),
        },
        simplify_tol_m,
    )

    area = layers["area"]
    forest = layers["forest"]
    admin_2022 = layers["admin_2022"]
    soil = layers["soil"]
    soil_profile = layers["soil_profile"]
    clc = layers["clc"]
    roads = layers["roads"]
    n2000 = combine_natura_layers(
        layers["n2000_uk"],
        layers["n2000_pk"],
        layers["n2000_nm"],
        layers["n2000_dm"],
    )

    if area.empty and forest.empty and n2000.empty and admin_2022.empty and soil.empty and soil_profile.empty and clc.empty and roads.empty:
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
    grid = apply_forest_group_coverages(grid, forest)
    grid = ensure_coverage_columns(
        grid,
        ["forest_pct", "valstybinis_pct", "n2000_pct", "grp1_pct", "grp2_pct", "grp3_pct", "grp4_pct"],
    )

    grid["n2000_index"] = (1.0 - grid["n2000_pct"]).clip(0.0, 1.0)
    grid = calculate_vmt_index(grid)

    if not soil.empty:
        soil = compute_soil_texture_scores(soil)
    if not soil_profile.empty:
        soil_profile = compute_profile_scores(soil_profile)

    grid = soil_weighted_texture(grid, soil)
    grid = aggregate_profile_scores(grid, soil_profile)
    grid = build_soil_index(grid)

    grid["soil_index"] = np.power(
        grid["soil_index"],
        (1 - grid["soil_index"]) * 5
    )

    grid["road_score"] = calculate_road_score(grid, roads)

    grid["road_score"] = np.power(
    grid["road_score"],
    (1 - grid["road_score"]) * 10
    )
    grid = calculate_restrictions_index(grid)

    grid = assign_dominant_forest_type(grid, clc)
    grid = assign_admin_areas(grid, admin_2022)

    has_forest = grid["forest_pct"] >= 0.2
    grid = grid[has_forest].copy()

    if grid.empty:
        return None

    grid = calculate_preview_final_score(grid)
    out = build_tile_payload(grid, xmin, ymin)

    out_base = get_tiles_dir(layer_name) / tile_filename(tile_bounds)
    actual_path = write_gdf_with_fallback(out, out_base)
    return build_tile_result(out, actual_path, tile_bounds)


def clear_old_tiles(layer_name: str) -> None:
    tiles_dir = get_tiles_dir(layer_name)
    if tiles_dir.exists():
        for f in tiles_dir.glob("*"):
            if f.is_file():
                f.unlink()


# Public pipeline entrypoint
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
