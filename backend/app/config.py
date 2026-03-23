from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

CACHE_COARSE_DIR = PROCESSED_DIR / "coarse"
CACHE_DETAIL_DIR = PROCESSED_DIR / "detail"

COARSE_TILES_DIR = CACHE_COARSE_DIR / "tiles"
DETAIL_TILES_DIR = CACHE_DETAIL_DIR / "tiles"

GDB_VMT = RAW_DIR / "VMT_DB" / "vmt_db.gdb"
GDB_NATURA = RAW_DIR / "VSTT-NATURA-miskai" / "Natura2000_misku_ribojimai.gdb"
GDB_DIRV = RAW_DIR / "Dirv_DR10LT" / "Dirv_DR10LT" / "DIRV_DB10LT.gdb"
SHP_ROADS = RAW_DIR / "ValstybiniuKeliuTinklas_2025" / "ValstybiniuKeliuTinklas_2025.shp"

LAYER_AREA = "Valstybines_reiksmes_misku_plotu_ribos"
LAYER_FOREST = "Misku_pogrupiai"
LAYER_RESTR = "NM_teritorijos"
LAYER_DIRV = os.getenv("LAYER_DIRV", "apreptis_db")
LAYER_ROADS = os.getenv("LAYER_ROADS", "")

CRS_METRIC = "EPSG:3346"
CRS_WEB = "EPSG:4326"

DEFAULT_COARSE_GRID_SIZE_M = int(os.getenv("DEFAULT_COARSE_GRID_SIZE_M", "1500"))
DEFAULT_COARSE_TILE_SIZE_M = int(os.getenv("DEFAULT_COARSE_TILE_SIZE_M", "15000"))

DEFAULT_DETAIL_GRID_SIZE_M = int(os.getenv("DEFAULT_DETAIL_GRID_SIZE_M", "300"))
DEFAULT_DETAIL_TILE_SIZE_M = int(os.getenv("DEFAULT_DETAIL_TILE_SIZE_M", "5000"))

DEFAULT_SIMPLIFY_TOL_M = float(os.getenv("DEFAULT_SIMPLIFY_TOL_M", "5"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", str(max(1, (os.cpu_count() or 4) - 1))))

TH_GREEN = 0.8
TH_YELLOW = 0.5

# Lithuania boundary in EPSG:3346 (rough bounding box as polygon)
LT_BOUNDARY_WKT = "POLYGON((200000 5960000, 700000 5960000, 700000 6260000, 200000 6260000, 200000 5960000))"


def get_cache_dir(layer_name: str) -> Path:
    if layer_name == "detail":
        return CACHE_DETAIL_DIR
    return CACHE_COARSE_DIR


def get_tiles_dir(layer_name: str) -> Path:
    if layer_name == "detail":
        return DETAIL_TILES_DIR
    return COARSE_TILES_DIR


def get_tile_index_path(layer_name: str) -> Path:
    return get_cache_dir(layer_name) / "tile_index.parquet"


def get_tile_index_geojson_path(layer_name: str) -> Path:
    return get_cache_dir(layer_name) / "tile_index.geojson"


def get_status_path(layer_name: str) -> Path:
    return get_cache_dir(layer_name) / "status.json"


def get_metadata_path(layer_name: str) -> Path:
    return get_cache_dir(layer_name) / "metadata.json"


EXPORT_GEOJSON_PATH = EXPORTS_DIR / "latest.geojson"
EXPORT_STATS_PATH = EXPORTS_DIR / "latest_stats.json"

for p in [
    PROCESSED_DIR,
    EXPORTS_DIR,
    CACHE_COARSE_DIR,
    CACHE_DETAIL_DIR,
    COARSE_TILES_DIR,
    DETAIL_TILES_DIR,
]:
    p.mkdir(parents=True, exist_ok=True)