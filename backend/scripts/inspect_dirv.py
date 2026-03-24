import geopandas as gpd
from app.config import GDB_DIRV

for layer_name in ["konturas", "profilis", "apreptis_db"]:
    print(f"\n--- LAYER: {layer_name} ---")
    try:
        gdf = gpd.read_file(GDB_DIRV, layer=layer_name, rows=5)
        print("Columns:")
        print(list(gdf.columns))
        print("\nHead:")
        print(gdf.head())
    except Exception as e:
        print("ERROR:", e)