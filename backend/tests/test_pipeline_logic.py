import unittest

import geopandas as gpd
from shapely.geometry import Point, box

from app.services import pipeline


class PipelineLogicTests(unittest.TestCase):
    def test_resolve_analysis_sizes_uses_layer_defaults(self):
        coarse = pipeline.resolve_analysis_sizes("coarse", None, None)
        detail = pipeline.resolve_analysis_sizes("detail", None, None)

        self.assertEqual(coarse, (pipeline.DEFAULT_COARSE_GRID_SIZE_M, pipeline.DEFAULT_COARSE_TILE_SIZE_M))
        self.assertEqual(detail, (pipeline.DEFAULT_DETAIL_GRID_SIZE_M, pipeline.DEFAULT_DETAIL_TILE_SIZE_M))

    def test_filter_area_by_bbox_keeps_intersecting_geometries(self):
        area = gpd.GeoDataFrame(
            {"name": ["inside", "outside"]},
            geometry=[box(0, 0, 10, 10), box(100, 100, 120, 120)],
            crs=pipeline.CRS_METRIC,
        )

        filtered = pipeline.filter_area_by_bbox(area, "0,0,20,20")

        self.assertEqual(filtered["name"].tolist(), ["inside"])

    def test_should_skip_tile_processing_checks_all_layers(self):
        empty = gpd.GeoDataFrame(geometry=[], crs=pipeline.CRS_METRIC)
        non_empty = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs=pipeline.CRS_METRIC)

        self.assertTrue(pipeline.should_skip_tile_processing({"a": empty, "b": empty}))
        self.assertFalse(pipeline.should_skip_tile_processing({"a": empty, "b": non_empty}))

    def test_compute_soil_texture_scores_builds_weighted_average(self):
        soil = gpd.GeoDataFrame(
            {
                "TEX_K_P": ["m"],
                "TEX_K_D": ["dm"],
                "TEX_F_P": ["z"],
                "TEX_F_D": [None],
            },
            geometry=[box(0, 0, 1, 1)],
            crs=pipeline.CRS_METRIC,
        )

        scored = pipeline.compute_soil_texture_scores(soil)

        self.assertEqual(scored.loc[0, "tex_k_p_score"], 100.0)
        self.assertEqual(scored.loc[0, "tex_k_d_score"], 97.0)
        self.assertEqual(scored.loc[0, "tex_f_p_score"], 5.0)
        self.assertEqual(scored.loc[0, "tex_f_d_score"], 0.0)
        self.assertAlmostEqual(scored.loc[0, "tex_score"], 50.5)

    def test_compute_profile_scores_maps_codes_to_scores(self):
        profile = gpd.GeoDataFrame(
            {
                "DRA": ["1"],
                "PH_L": [6.0],
                "TOP": ["F"],
                "LAEL": ["PL"],
                "SLGR": [2],
                "ABST": ["N"],
                "SIST": ["C"],
            },
            geometry=[Point(0, 0)],
            crs=pipeline.CRS_METRIC,
        )

        scored = pipeline.compute_profile_scores(profile)

        self.assertEqual(scored.loc[0, "dra_score"], 100.0)
        self.assertEqual(scored.loc[0, "ph_score"], 100.0)
        self.assertEqual(scored.loc[0, "reljef_score"], 100.0)
        self.assertEqual(scored.loc[0, "akmen_score"], 100.0)

    def test_calculate_vmt_index_handles_zero_forest_pct(self):
        grid = gpd.GeoDataFrame(
            {
                "forest_pct": [0.0, 0.8],
                "valstybinis_pct": [0.0, 0.2],
                "grp1_pct": [0.0, 0.1],
                "grp2_pct": [0.0, 0.2],
                "grp3_pct": [0.0, 0.1],
                "grp4_pct": [0.0, 0.4],
            },
            geometry=[box(0, 0, 1, 1), box(1, 1, 2, 2)],
            crs=pipeline.CRS_METRIC,
        )

        scored = pipeline.calculate_vmt_index(grid)

        self.assertEqual(scored.loc[0, "vmt_index"], 0.0)
        self.assertGreater(scored.loc[1, "vmt_index"], 0.0)
        self.assertLessEqual(scored.loc[1, "vmt_index"], 1.0)

    def test_apply_score_transforms_keeps_scores_in_expected_range(self):
        grid = gpd.GeoDataFrame(
            {"soil_index": [0.5, 1.0], "road_score": [0.25, 1.0]},
            geometry=[box(0, 0, 1, 1), box(1, 1, 2, 2)],
            crs=pipeline.CRS_METRIC,
        )

        transformed = pipeline.apply_score_transforms(grid)

        self.assertTrue(((transformed["soil_index"] >= 0.0) & (transformed["soil_index"] <= 1.0)).all())
        self.assertTrue(((transformed["road_score"] >= 0.0) & (transformed["road_score"] <= 1.0)).all())

    def test_build_analysis_metadata_aggregates_tile_counts(self):
        tile_index = gpd.GeoDataFrame(
            {
                "n_cells": [10, 15],
                "green_count": [2, 3],
                "yellow_count": [4, 5],
                "red_count": [4, 7],
            },
            geometry=[box(0, 0, 1, 1), box(1, 1, 2, 2)],
            crs=pipeline.CRS_METRIC,
        )

        metadata = pipeline.build_analysis_metadata(
            layer_name="coarse",
            grid_size=1500,
            tile_size=15000,
            simplify_tol_m=5,
            max_workers=4,
            tile_index=tile_index,
            tile_index_storage="parquet",
            total_seconds=12.345,
            bbox="1,2,3,4",
        )

        self.assertTrue(metadata["ok"])
        self.assertEqual(metadata["tiles_total"], 2)
        self.assertEqual(metadata["cells_total"], 25)
        self.assertEqual(metadata["green_total"], 5)
        self.assertEqual(metadata["yellow_total"], 9)
        self.assertEqual(metadata["red_total"], 11)
        self.assertEqual(metadata["total_seconds"], 12.35)


if __name__ == "__main__":
    unittest.main()
