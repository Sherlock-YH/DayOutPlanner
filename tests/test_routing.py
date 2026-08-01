import json
import os
import sys
import unittest
from datetime import datetime

# 1. Dynamically add the project root directory to sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gmaps_service import get_transit_route_by_name


class TestRoutingEngine(unittest.TestCase):

    def setUp(self):
        """Construct absolute path to the fixture file regardless of current working directory."""
        fixture_path = os.path.join(TESTS_DIR, "fixtures", "nature_food_plan.json")

        if not os.path.exists(fixture_path):
            self.fail(
                f"❌ Fixture missing! Expected file at:\n{fixture_path}\n"
                "Please create 'tests/fixtures/nature_food_plan.json'."
            )

        with open(fixture_path, "r", encoding="utf-8") as f:
            self.fixture_data = json.load(f)

    def test_national_gallery_to_raffles_city(self):
        """Verify adjacent venues result in short walk/commute times (< 15 mins)."""
        stops = self.fixture_data.get("stops", [])
        self.assertGreaterEqual(len(stops), 2, "Fixture must contain at least 2 stops")

        stop1 = stops[0]["venue_name"]
        stop2 = stops[1]["venue_name"]

        # Run routing on frozen inputs
        transit = get_transit_route_by_name(stop1, stop2, datetime.now())

        self.assertIsNotNone(transit, "Transit router returned None")
        self.assertLess(
            transit.get("real_commute_mins", 999),
            15,
            f"Commute between {stop1} and {stop2} took longer than 15 mins"
        )


if __name__ == "__main__":
    unittest.main()