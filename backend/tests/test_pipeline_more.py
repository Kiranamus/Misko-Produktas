import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from app.services import pipeline


TEMP_DIR = "C:\\tmp"


class PipelineMoreTests(unittest.TestCase):
    def test_status_and_metadata_helpers_use_configured_paths(self):
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            base = Path(tmp)
            status_path = base / "status.json"
            metadata_path = base / "metadata.json"

            with patch.object(pipeline, "get_status_path", return_value=status_path):
                self.assertEqual(
                    pipeline.read_status("coarse"),
                    {"layer": "coarse", "status": "idle", "message": "No analysis yet."},
                )
                pipeline.write_status("coarse", "running", "Working", {"x": 1})
                self.assertEqual(pipeline.read_status("coarse")["x"], 1)

            with patch.object(pipeline, "get_metadata_path", return_value=metadata_path):
                self.assertEqual(
                    pipeline.get_metadata("coarse"),
                    {"ok": False, "layer": "coarse", "message": "No metadata yet."},
                )
                metadata_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
                self.assertEqual(pipeline.get_metadata("coarse"), {"ok": True})

    def test_clear_analysis_cache_removes_index_files(self):
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            base = Path(tmp)
            paths = [base / "index.parquet", base / "index.geojson", base / "metadata.json"]
            for path in paths:
                path.write_text("x", encoding="utf-8")

            with patch.object(pipeline, "clear_old_tiles") as mocked_clear, patch.object(
                pipeline,
                "get_tile_index_path",
                return_value=paths[0],
            ), patch.object(pipeline, "get_tile_index_geojson_path", return_value=paths[1]), patch.object(
                pipeline,
                "get_metadata_path",
                return_value=paths[2],
            ):
                pipeline.clear_analysis_cache("coarse")

            mocked_clear.assert_called_once_with("coarse")
            self.assertTrue(all(not path.exists() for path in paths))

    def test_read_vector_returns_empty_when_file_missing(self):
        result = pipeline.read_vector(Path("missing.shp"))

        self.assertTrue(result.empty)
        self.assertEqual(str(result.crs), pipeline.CRS_METRIC)

    def test_prepare_layer_and_layers_delegate_to_geometry_helpers(self):
        gdf = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs=pipeline.CRS_METRIC)

        with patch.object(pipeline, "simplify_geoms", return_value=gdf) as mocked_simplify, patch.object(
            pipeline,
            "fix_invalid",
            return_value=gdf,
        ) as mocked_fix:
            self.assertIs(pipeline.prepare_layer(gdf, 5), gdf)
            prepared = pipeline.prepare_layers({"a": gdf}, 5)

        self.assertEqual(prepared, {"a": gdf})
        self.assertEqual(mocked_simplify.call_count, 2)
        self.assertEqual(mocked_fix.call_count, 2)

    def test_calculate_road_score_scores_near_road_higher_than_far_cell(self):
        grid = gpd.GeoDataFrame(
            geometry=[box(0, 0, 10, 10), box(3000, 0, 3010, 10)],
            crs=pipeline.CRS_METRIC,
        )
        roads = gpd.GeoDataFrame(geometry=[Point(0, 0)], crs=pipeline.CRS_METRIC)

        scores = pipeline.calculate_road_score(grid, roads)

        self.assertGreater(scores.iloc[0], scores.iloc[1])
        self.assertGreater(scores.iloc[0], 0)

    def test_cover_pct_by_sindex_calculates_intersection_share(self):
        grid = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=pipeline.CRS_METRIC)
        layer = gpd.GeoDataFrame(geometry=[box(0, 0, 5, 10)], crs=pipeline.CRS_METRIC)

        result = pipeline.cover_pct_by_sindex(grid, layer, "covered")

        self.assertAlmostEqual(result.loc[0, "covered"], 0.5)

    def test_soil_weighted_texture_uses_intersection_area_weights(self):
        grid = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=pipeline.CRS_METRIC)
        soil = gpd.GeoDataFrame(
            {"tex_score": [100.0, 0.0]},
            geometry=[box(0, 0, 5, 10), box(5, 0, 10, 10)],
            crs=pipeline.CRS_METRIC,
        )

        result = pipeline.soil_weighted_texture(grid, soil)

        self.assertAlmostEqual(result.loc[0, "tex_score"], 50.0)

    def test_simplify_geoms_and_fix_invalid_keep_valid_non_empty_geometries(self):
        gdf = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1), None], crs=pipeline.CRS_METRIC)

        simplified = pipeline.simplify_geoms(gdf, 0)
        fixed = pipeline.fix_invalid(gdf)

        self.assertIs(simplified, gdf)
        self.assertEqual(len(fixed), 1)

    def test_aggregate_profile_scores_maps_point_scores_to_grid_cell(self):
        grid = gpd.GeoDataFrame(
            {"cell_local_id": [1]},
            geometry=[box(0, 0, 10, 10)],
            crs=pipeline.CRS_METRIC,
        )
        profile = gpd.GeoDataFrame(
            {"dra_score": [80], "ph_score": [70], "reljef_score": [60], "akmen_score": [50]},
            geometry=[Point(5, 5)],
            crs=pipeline.CRS_METRIC,
        )

        result = pipeline.aggregate_profile_scores(grid, profile)

        self.assertEqual(result.loc[0, "dra_score"], 80)
        self.assertEqual(result.loc[0, "akmen_score"], 50)

    def test_build_soil_index_adds_missing_columns_and_clips(self):
        grid = gpd.GeoDataFrame({"tex_score": [200.0]}, geometry=[box(0, 0, 1, 1)], crs=pipeline.CRS_METRIC)

        result = pipeline.build_soil_index(grid)

        self.assertEqual(result.loc[0, "soil_index_raw"], 80.0)
        self.assertEqual(result.loc[0, "soil_index"], 0.8)
        self.assertIn("ph_score", result.columns)

    def test_assign_admin_areas_sets_dominant_municipality_and_county(self):
        grid = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=pipeline.CRS_METRIC)
        admin = gpd.GeoDataFrame(
            {"Savivaldybe": ["Vilniaus m. sav."]},
            geometry=[box(0, 0, 10, 10)],
            crs=pipeline.CRS_METRIC,
        )

        result = pipeline.assign_admin_areas(grid, admin)

        self.assertEqual(result.loc[0, "municipality"], "Vilniaus m. sav.")
        self.assertEqual(result.loc[0, "county"], "Vilniaus apskritis")

    def test_assign_dominant_forest_type_uses_largest_intersection(self):
        grid = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=pipeline.CRS_METRIC)
        clc = gpd.GeoDataFrame(
            {"Code_18": ["311", "312"]},
            geometry=[box(0, 0, 7, 10), box(7, 0, 10, 10)],
            crs=pipeline.CRS_METRIC,
        )

        result = pipeline.assign_dominant_forest_type(grid, clc)

        self.assertEqual(result.loc[0, "forest_type"], "Lapuočių miškai")

    def test_tile_and_grid_builders_create_expected_shapes(self):
        self.assertEqual(pipeline.tile_filename((0, 1, 2, 3)), "tile_0_1_2_3")
        grid = pipeline.build_grid_for_bounds((0, 0, 2, 2), 1)
        tiles = pipeline.build_tiles(gpd.GeoDataFrame(geometry=[box(0, 0, 2, 2)], crs=pipeline.CRS_METRIC), 1)

        self.assertEqual(len(grid), 4)
        self.assertEqual(len(tiles), 4)

    def test_write_gdf_with_fallback_uses_geojson_when_parquet_fails(self):
        gdf = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs=pipeline.CRS_METRIC)
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            out_base = Path(tmp) / "tile"
            with patch.object(gdf, "to_parquet", side_effect=RuntimeError("no parquet")), patch.object(
                gdf,
                "to_file",
            ) as mocked_file:
                actual = pipeline.write_gdf_with_fallback(gdf, out_base)

        self.assertTrue(actual.endswith(".geojson"))
        mocked_file.assert_called_once()

    def test_combine_natura_layers_dissolves_non_empty_inputs(self):
        empty = gpd.GeoDataFrame(geometry=[], crs=pipeline.CRS_METRIC)
        layer = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs=pipeline.CRS_METRIC)

        combined = pipeline.combine_natura_layers(empty, layer)

        self.assertEqual(len(combined), 1)

    def test_forest_group_coverages_and_coverage_columns(self):
        grid = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=pipeline.CRS_METRIC)
        forest = gpd.GeoDataFrame(
            {"grupe": [1, 4]},
            geometry=[box(0, 0, 5, 10), box(5, 0, 10, 10)],
            crs=pipeline.CRS_METRIC,
        )

        covered = pipeline.apply_forest_group_coverages(grid, forest)
        ensured = pipeline.ensure_coverage_columns(covered.drop(columns=["grp2_pct"]), ["grp2_pct"])

        self.assertAlmostEqual(covered.loc[0, "grp1_pct"], 0.5)
        self.assertAlmostEqual(covered.loc[0, "grp4_pct"], 0.5)
        self.assertEqual(ensured.loc[0, "grp2_pct"], 0.0)

    def test_index_and_payload_helpers_calculate_expected_fields(self):
        grid = gpd.GeoDataFrame(
            {
                "n2000_index": [1.0],
                "vmt_index": [1.0],
                "soil_index": [1.0],
                "road_score": [1.0],
                "cell_local_id": [7],
                "forest_pct": [0.8],
                "tex_score": [50],
                "dra_score": [60],
                "ph_score": [70],
                "reljef_score": [80],
                "akmen_score": [90],
                "soil_index_raw": [75],
                "forest_type": ["A"],
                "municipality": ["B"],
                "county": ["C"],
            },
            geometry=[box(0, 0, 1, 1)],
            crs=pipeline.CRS_METRIC,
        )

        restricted = pipeline.calculate_restrictions_index(grid)
        preview = pipeline.calculate_preview_final_score(restricted)
        payload = pipeline.build_tile_payload(preview, 1, 2)
        result = pipeline.build_tile_result(preview, "tile.parquet", (1, 2, 3, 4))

        self.assertEqual(restricted.loc[0, "restrictions_index"], 1.0)
        self.assertEqual(preview.loc[0, "final_score"], 1.0)
        self.assertEqual(payload.loc[0, "tile_xmin"], 1)
        self.assertEqual(result["green_count"], 1)
        self.assertEqual(result["n_cells"], 1)

    def test_clear_old_tiles_removes_files_only(self):
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            tiles_dir = Path(tmp)
            file_path = tiles_dir / "tile.parquet"
            nested_dir = tiles_dir / "nested"
            file_path.write_text("x", encoding="utf-8")
            nested_dir.mkdir()

            with patch.object(pipeline, "get_tiles_dir", return_value=tiles_dir):
                pipeline.clear_old_tiles("coarse")

            self.assertFalse(file_path.exists())
            self.assertTrue(nested_dir.exists())


if __name__ == "__main__":
    unittest.main()
