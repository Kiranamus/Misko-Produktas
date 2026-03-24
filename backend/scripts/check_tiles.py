import geopandas as gpd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
coarse_dir = ROOT / "data" / "processed" / "coarse" / "tiles"

files = list(coarse_dir.glob("*.parquet")) + list(coarse_dir.glob("*.geojson"))
print("Found files:", len(files))

if not files:
    raise SystemExit("No tile files found")

sample = files[0]
print("Sample file:", sample)

if sample.suffix.lower() == ".parquet":
    gdf = gpd.read_parquet(sample)
else:
    gdf = gpd.read_file(sample)

print("\nColumns:")
print(list(gdf.columns))

print("\nHead:")
print(
    gdf[
        [
            c for c in [
                "forest_pct",
                "valstybinis_pct",
                "n2000_pct",
                "n2000_index",
                "vmt_index",
                "restrictions_index",
                "soil_index",
                "road_score",
                "final_score",
            ] if c in gdf.columns
        ]
    ].head(20)
)

print("\nDescribe:")
for col in [
    "forest_pct",
    "valstybinis_pct",
    "n2000_pct",
    "n2000_index",
    "vmt_index",
    "restrictions_index",
    "soil_index",
    "road_score",
    "final_score",
]:
    if col in gdf.columns:
        print(col, "min=", gdf[col].min(), "max=", gdf[col].max(), "avg=", gdf[col].mean())