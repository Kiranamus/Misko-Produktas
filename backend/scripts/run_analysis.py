import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.pipeline import process_analysis

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run forest analysis pipeline")
    parser.add_argument("layer", choices=["coarse", "detail"], help="Layer to process")
    parser.add_argument("--bbox", help="Bounding box as minx,miny,maxx,maxy in EPSG:3346")
    parser.add_argument("--clear-cache", action="store_true", help="Clear old tiles before processing")

    args = parser.parse_args()

    result = process_analysis(
        layer_name=args.layer,
        grid_size=None,  # use defaults
        tile_size=None,
        simplify_tol_m=5.0,
        max_workers=4,
        clear_cache=args.clear_cache,
        bbox=args.bbox,
    )

    print("Analysis result:", result)