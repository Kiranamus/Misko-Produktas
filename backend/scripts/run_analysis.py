import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import (
    DEFAULT_COARSE_GRID_SIZE_M,
    DEFAULT_COARSE_TILE_SIZE_M,
    DEFAULT_DETAIL_GRID_SIZE_M,
    DEFAULT_DETAIL_TILE_SIZE_M,
    DEFAULT_SIMPLIFY_TOL_M,
    MAX_WORKERS,
)
from app.services.pipeline import process_analysis


def run_coarse():
    print("[RUN] coarse analysis")
    result = process_analysis(
        layer_name="coarse",
        grid_size=DEFAULT_COARSE_GRID_SIZE_M,
        tile_size=DEFAULT_COARSE_TILE_SIZE_M,
        simplify_tol_m=DEFAULT_SIMPLIFY_TOL_M,
        max_workers=8,
        clear_cache=True,
        bbox=None,
    )
    print("[DONE] coarse")
    print(result)


def run_detail():
    print("[RUN] detail analysis")
    result = process_analysis(
        layer_name="detail",
        grid_size=DEFAULT_DETAIL_GRID_SIZE_M,
        tile_size=DEFAULT_DETAIL_TILE_SIZE_M,
        simplify_tol_m=DEFAULT_SIMPLIFY_TOL_M,
        max_workers=8,
        clear_cache=True,
        bbox=None,
    )
    print("[DONE] detail")
    print(result)


if __name__ == "__main__":
    mode = "both"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if mode == "coarse":
        run_coarse()
    elif mode == "detail":
        run_detail()
    else:
        run_coarse()
        run_detail()