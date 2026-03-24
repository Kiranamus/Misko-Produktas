import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import geopandas as gpd
import pandas as pd
from sqlalchemy import text

from app.db_config import engine

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

COARSE_DIR = PROCESSED_DIR / "coarse" / "tiles"
DETAIL_DIR = PROCESSED_DIR / "detail" / "tiles"

CRS_METRIC = "EPSG:3346"


def ensure_database_columns() -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS forest_cells"))

        conn.execute(text("""
            CREATE TABLE forest_cells (
                id serial PRIMARY KEY,
                layer text NOT NULL,
                forest_pct double precision,
                valstybinis_pct double precision,
                n2000_pct double precision,
                n2000_index double precision,
                vmt_index double precision,
                restrictions_index double precision,
                soil_index double precision,
                road_score double precision,
                geometry geometry(Geometry, 3346)
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_forest_cells_geometry
            ON forest_cells
            USING GIST (geometry)
        """))

        conn.execute(text("""
            CREATE INDEX idx_forest_cells_layer
            ON forest_cells(layer)
        """))

    print("[OK] Recreated forest_cells table")


def load_tile_files(folder: Path, layer_name: str) -> gpd.GeoDataFrame:
    if not folder.exists():
        print(f"[WARN] Folder not found: {folder}")
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    files = list(folder.glob("*.parquet")) + list(folder.glob("*.geojson"))

    if not files:
        print(f"[WARN] No files found in {folder}")
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    frames = []

    for file in files:
        print(f"[READ] {file.name}")

        if file.suffix.lower() == ".parquet":
            gdf = gpd.read_parquet(file)
        else:
            gdf = gpd.read_file(file)

        if gdf.empty:
            continue

        if gdf.crs is None:
            gdf = gdf.set_crs(CRS_METRIC)
        else:
            gdf = gdf.to_crs(CRS_METRIC)

        gdf["layer"] = layer_name

        # Suderinamumas su senesniais failais
        legacy_rename = {
            "restr_pct": "restrictions_index",
            "soil_pct": "soil_index",
            "vmt_pct": "vmt_index",
            "n2000_idx": "n2000_index",
            "n2000_prc": "n2000_pct",
            "valstybinis_prc": "valstybinis_pct",
            "road_prc": "road_score",
        }

        for old_col, new_col in legacy_rename.items():
            if old_col in gdf.columns and new_col not in gdf.columns:
                gdf[new_col] = gdf[old_col]

        keep_cols = [
            "layer",
            "forest_pct",
            "valstybinis_pct",
            "n2000_pct",
            "n2000_index",
            "vmt_index",
            "restrictions_index",
            "soil_index",
            "road_score",
            "geometry",
        ]

        existing = [c for c in keep_cols if c in gdf.columns]
        gdf = gdf[existing].copy()

        defaults = {
            "forest_pct": 0.0,
            "valstybinis_pct": 0.0,
            "n2000_pct": 0.0,
            "n2000_index": 0.0,
            "vmt_index": 0.0,
            "restrictions_index": 0.0,
            "soil_index": 0.0,
            "road_score": 0.0,
        }

        for col, default in defaults.items():
            if col not in gdf.columns:
                gdf[col] = default

        numeric_cols = [
            "forest_pct",
            "valstybinis_pct",
            "n2000_pct",
            "n2000_index",
            "vmt_index",
            "restrictions_index",
            "soil_index",
            "road_score",
        ]

        for col in numeric_cols:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce").fillna(0.0)

        gdf = gdf[
            [
                "layer",
                "forest_pct",
                "valstybinis_pct",
                "n2000_pct",
                "n2000_index",
                "vmt_index",
                "restrictions_index",
                "soil_index",
                "road_score",
                "geometry",
            ]
        ].copy()

        frames.append(gdf)

    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=CRS_METRIC)
    return merged


def clear_layer(layer_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM forest_cells WHERE layer = :layer"),
            {"layer": layer_name},
        )
    print(f"[OK] Cleared layer: {layer_name}")


def import_layer(folder: Path, layer_name: str) -> None:
    gdf = load_tile_files(folder, layer_name)

    if gdf.empty:
        print(f"[WARN] No data to import for layer: {layer_name}")
        return

    print(f"[IMPORT] Layer={layer_name}, rows={len(gdf)}")

    gdf.to_postgis(
        name="forest_cells",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=2000,
    )

    print(f"[DONE] Imported layer: {layer_name}")


if __name__ == "__main__":
    ensure_database_columns()

    clear_layer("coarse")
    import_layer(COARSE_DIR, "coarse")

    clear_layer("detail")
    import_layer(DETAIL_DIR, "detail")

    print("[ALL DONE] Import completed.")