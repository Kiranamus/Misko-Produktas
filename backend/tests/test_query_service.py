import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import query_service


class QueryServiceTests(unittest.TestCase):
    def test_normalize_weights_scales_to_one(self):
        weights = query_service.normalize_weights(40, 30, 30)

        self.assertEqual(weights, (0.4, 0.3, 0.3))

    def test_normalize_weights_rejects_zero_total(self):
        with self.assertRaises(ValueError):
            query_service.normalize_weights(0, 0, 0)

    def test_build_grid_filters_collects_optional_params(self):
        where_parts, params = query_service.build_grid_filters(
            layer_name="detail",
            bbox="1,2,3,4",
            county="Vilniaus apskritis",
            min_score=0.2,
            max_score=0.9,
            w_restr=0.4,
            w_soil=0.3,
            w_road=0.3,
        )

        self.assertIn("layer = :layer", where_parts)
        self.assertIn("county = :county", where_parts)
        self.assertTrue(any("geometry && ST_MakeEnvelope" in part for part in where_parts))
        self.assertTrue(any(":min_score" in part for part in where_parts))
        self.assertTrue(any(":max_score" in part for part in where_parts))
        self.assertEqual(params["county"], "Vilniaus apskritis")
        self.assertEqual(params["minx"], 1.0)
        self.assertEqual(params["maxy"], 4.0)

    def test_build_grid_query_adds_limit_only_when_requested(self):
        sql_without_limit = query_service.build_grid_query(["layer = :layer"], limit=None)
        sql_with_limit = query_service.build_grid_query(["layer = :layer"], limit=25)

        self.assertNotIn("LIMIT :limit", sql_without_limit)
        self.assertIn("LIMIT :limit", sql_with_limit)

    def test_serialize_grid_feature_applies_defaults_and_classification(self):
        row = SimpleNamespace(
            _mapping={
                "id": 11,
                "layer": "coarse",
                "forest_pct": None,
                "tex_score": 55,
                "dra_score": None,
                "ph_score": 80,
                "reljef_score": 60,
                "akmen_score": 70,
                "soil_index_raw": 65,
                "restrictions_index": 0.8,
                "soil_index": 0.6,
                "road_score": 0.5,
                "forest_type": "Spygliuociu miskai",
                "municipality": "Vilnius",
                "county": "Vilniaus apskritis",
                "final_score": 0.72,
                "geom_json": "{\"type\": \"Point\", \"coordinates\": [25.0, 54.7]}",
            }
        )

        feature = query_service.serialize_grid_feature(row, 0.4, 0.3, 0.3)

        self.assertEqual(feature["id"], "11")
        self.assertEqual(feature["properties"]["forest_pct"], 0.0)
        self.assertEqual(feature["properties"]["class"], "GREEN")
        self.assertEqual(feature["properties"]["weights"]["soil"], 0.3)
        self.assertEqual(feature["geometry"]["type"], "Point")

    def test_summarize_scores_counts_buckets(self):
        features = [
            {"properties": {"final_score": 0.9}},
            {"properties": {"final_score": 0.5}},
            {"properties": {"final_score": 0.1}},
        ]

        summary = query_service.summarize_scores(features)

        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["green"], 1)
        self.assertEqual(summary["yellow"], 1)
        self.assertEqual(summary["red"], 1)
        self.assertEqual(summary["min_score"], 0.1)
        self.assertEqual(summary["max_score"], 0.9)

    def test_query_stats_wraps_summary(self):
        with patch.object(
            query_service,
            "query_grid",
            return_value={"features": [{"properties": {"final_score": 0.8}}]},
        ):
            stats = query_service.query_stats(layer_name="detail")

        self.assertEqual(stats["layer"], "detail")
        self.assertEqual(stats["count"], 1)
        self.assertEqual(stats["green"], 1)


if __name__ == "__main__":
    unittest.main()
