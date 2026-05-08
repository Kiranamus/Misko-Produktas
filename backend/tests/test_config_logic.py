import unittest

from app import config


class ConfigLogicTests(unittest.TestCase):
    def test_cache_dir_selects_detail_or_coarse(self):
        self.assertEqual(config.get_cache_dir("detail"), config.CACHE_DETAIL_DIR)
        self.assertEqual(config.get_cache_dir("coarse"), config.CACHE_COARSE_DIR)
        self.assertEqual(config.get_cache_dir("anything-else"), config.CACHE_COARSE_DIR)

    def test_tiles_dir_selects_detail_or_coarse(self):
        self.assertEqual(config.get_tiles_dir("detail"), config.DETAIL_TILES_DIR)
        self.assertEqual(config.get_tiles_dir("coarse"), config.COARSE_TILES_DIR)

    def test_index_status_and_metadata_paths_are_under_layer_cache(self):
        self.assertEqual(
            config.get_tile_index_path("detail"),
            config.CACHE_DETAIL_DIR / "tile_index.parquet",
        )
        self.assertEqual(
            config.get_tile_index_geojson_path("coarse"),
            config.CACHE_COARSE_DIR / "tile_index.geojson",
        )
        self.assertEqual(config.get_status_path("coarse"), config.CACHE_COARSE_DIR / "status.json")
        self.assertEqual(config.get_metadata_path("detail"), config.CACHE_DETAIL_DIR / "metadata.json")


if __name__ == "__main__":
    unittest.main()
