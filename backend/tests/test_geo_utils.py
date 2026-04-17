import unittest

from app.utils.geo import parse_bbox_string


class GeoUtilsTests(unittest.TestCase):
    def test_parse_bbox_string_returns_float_tuple(self):
        bbox = parse_bbox_string("1, 2, 3, 4")

        self.assertEqual(bbox, (1.0, 2.0, 3.0, 4.0))

    def test_parse_bbox_string_rejects_wrong_part_count(self):
        with self.assertRaises(ValueError):
            parse_bbox_string("1,2,3")


if __name__ == "__main__":
    unittest.main()
