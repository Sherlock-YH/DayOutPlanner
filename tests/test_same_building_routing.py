import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

# Dynamically add the project root directory to sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gmaps_service import get_transit_route_by_name


class TestSameBuildingRouting(unittest.TestCase):

    @patch("gmaps_service.gmaps")
    def test_same_building_venue_returns_zero_mins(self, mock_gmaps):
        """
        Verifies that when Google Maps returns ZERO_RESULTS for two venues in
        the same building (e.g. museum and an internal cafe), the service
        gracefully returns 0 commute minutes with a friendly walking string.
        """
        # 1. Simulate Google Maps returning empty directions list (ZERO_RESULTS)
        mock_gmaps.directions.return_value = []

        start_venue = "National Gallery Singapore"
        end_venue = "Courtyard Cafe inside National Gallery"
        departure_time = datetime(2026, 8, 1, 10, 0)

        # 2. Call the transit routing service
        result = get_transit_route_by_name(
            start_venue=start_venue,
            end_venue=end_venue,
            departure_datetime=departure_time
        )

        # 3. Assertions
        self.assertEqual(
            result["real_commute_mins"], 0,
            "Commute time should be 0 minutes for same-building transitions"
        )
        self.assertIn(
            "inside or adjacent",
            result["step_by_step"].lower(),
            "Step-by-step description should indicate same/adjacent venue"
        )

    @patch("gmaps_service.gmaps")
    def test_unrelated_venues_no_route_returns_error_string(self, mock_gmaps):
        """
        Verifies that completely unrelated venues with no directions still return
        the standard fallback error message rather than the same-building message.
        """
        mock_gmaps.directions.return_value = []

        start_venue = "Random Spot A"
        end_venue = "Unrelated Spot B"
        departure_time = datetime(2026, 8, 1, 10, 0)

        result = get_transit_route_by_name(
            start_venue=start_venue,
            end_venue=end_venue,
            departure_datetime=departure_time
        )

        self.assertEqual(result["real_commute_mins"], 0)
        self.assertTrue(
            result["step_by_step"].startswith("No transit route found"),
            "Should output standard 'No transit route found' message for unrelated venues"
        )


if __name__ == "__main__":
    unittest.main()