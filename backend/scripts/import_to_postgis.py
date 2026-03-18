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

        # tik reikalingi stulpeliai
        keep_cols = [
            "layer",
            "class",
            "forest_pct",
            "restr_pct",
            "final_score",
            "tile_xmin",
            "tile_ymin",
            "geometry",
        ]

        existing = [c for c in keep_cols if c in gdf.columns]
        gdf = gdf[existing].copy()

        # jei kai kurių stulpelių nėra
        if "class" not in gdf.columns:
            gdf["class"] = None
        if "forest_pct" not in gdf.columns:
            gdf["forest_pct"] = None
        if "restr_pct" not in gdf.columns:
            gdf["restr_pct"] = None
        if "final_score" not in gdf.columns:
            gdf["final_score"] = None
        if "tile_xmin" not in gdf.columns:
            gdf["tile_xmin"] = None
        if "tile_ymin" not in gdf.columns:
            gdf["tile_ymin"] = None

        gdf = gdf[
            ["layer", "class", "forest_pct", "restr_pct", "final_score", "tile_xmin", "tile_ymin", "geometry"]
        ].copy()

        frames.append(gdf)

    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=CRS_METRIC)
    return merged


def clear_layer(layer_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM forest_cells WHERE layer = :layer"), {"layer": layer_name})
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
    clear_layer("coarse")
    import_layer(COARSE_DIR, "coarse")

    clear_layer("detail")
    import_layer(DETAIL_DIR, "detail")

    print("[ALL DONE] Import completed.")