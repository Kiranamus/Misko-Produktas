import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import query_service


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return FakeResult(self.rows)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeEngine:
    def __init__(self, rows):
        self.conn = FakeConnection(rows)

    def begin(self):
        return self.conn


class QueryServiceMoreTests(unittest.TestCase):
    def test_classify_thresholds(self):
        self.assertEqual(query_service.classify(0.66), "GREEN")
        self.assertEqual(query_service.classify(0.33), "YELLOW")
        self.assertEqual(query_service.classify(0.32), "RED")

    def test_get_metadata_counts_rows(self):
        row = SimpleNamespace(_mapping={"cnt": 12})
        engine = FakeEngine([row])

        with patch.object(query_service, "engine", engine):
            result = query_service.get_metadata("coarse")

        self.assertEqual(result, {"ok": True, "layer": "coarse", "count": 12})

    def test_query_grid_executes_and_serializes_rows(self):
        row = SimpleNamespace(
            _mapping={
                "id": 1,
                "layer": "coarse",
                "forest_pct": 0.7,
                "tex_score": 50,
                "dra_score": 60,
                "ph_score": 70,
                "reljef_score": 80,
                "akmen_score": 90,
                "soil_index_raw": 75,
                "restrictions_index": 0.8,
                "soil_index": 0.6,
                "road_score": 0.5,
                "forest_type": "A",
                "municipality": "B",
                "county": "C",
                "final_score": 0.67,
                "geom_json": '{"type":"Point","coordinates":[0,0]}',
            }
        )
        engine = FakeEngine([row])

        with patch.object(query_service, "engine", engine):
            result = query_service.query_grid(limit=5)

        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(result["features"][0]["properties"]["class"], "GREEN")
        self.assertEqual(engine.conn.calls[0][1]["limit"], 5)

    def test_get_counties_returns_strings(self):
        engine = FakeEngine([SimpleNamespace(_mapping={"county": "Vilniaus apskritis"})])

        with patch.object(query_service, "engine", engine):
            self.assertEqual(query_service.get_counties(), ["Vilniaus apskritis"])

    def test_query_distribution_handles_missing_row_and_values(self):
        with patch.object(query_service, "engine", FakeEngine([])):
            self.assertEqual(query_service.query_distribution("coarse"), {"layer": "coarse", "count": 0})

        row = SimpleNamespace(
            _mapping={
                "cnt": 2,
                "forest_min": 0.2,
                "forest_max": 0.8,
                "forest_avg": 0.5,
                "restr_min": None,
                "restr_max": None,
                "restr_avg": None,
                "soil_min": 0.1,
                "soil_max": 0.9,
                "soil_avg": 0.4,
                "road_min": 0.3,
                "road_max": 0.7,
                "road_avg": 0.5,
            }
        )

        with patch.object(query_service, "engine", FakeEngine([row])):
            result = query_service.query_distribution("coarse")

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["restrictions_index"]["min"], 0.0)
        self.assertEqual(result["soil_index"]["max"], 0.9)


if __name__ == "__main__":
    unittest.main()
