import unittest
from datetime import datetime

# Import the function you want to test from helperFunction.py
from helperFunction import calculate_sg_taxi_fare


class TestTaxiFareCalculator(unittest.TestCase):

    def test_short_distance_returns_minimum_fare(self):
        """A short 500m ride should trigger the minimum flagdown fare of $6 SGD."""
        result = calculate_sg_taxi_fare(distance_meters=500, duration_seconds=180)

        # Add a print statement to inspect the return dictionary
        print("\n🔍 TEST OUTPUT:", result)

        self.assertEqual(result["min_fare_sgd"], 6)
        self.assertIn("$6-$8 SGD", result["formatted_estimate"])

    def test_peak_hour_surcharge_increases_price(self):
        """Evening peak hours (6:30 PM) should cost more than off-peak hours (2:30 PM)."""
        peak_time = datetime(2026, 8, 7, 18, 30)  # Friday 6:30 PM (Peak)
        offpeak_time = datetime(2026, 8, 7, 14, 30)  # Friday 2:30 PM (Off-Peak)

        distance = 10000  # 10 km
        duration = 1200  # 20 mins

        peak_res = calculate_sg_taxi_fare(distance, duration, peak_time)
        offpeak_res = calculate_sg_taxi_fare(distance, duration, offpeak_time)

        self.assertGreater(
            peak_res["min_fare_sgd"],
            offpeak_res["min_fare_sgd"],
            "Peak fare should be strictly higher than off-peak fare"
        )

    def test_late_night_surcharge(self):
        """A ride at 2:00 AM should apply the 50% late night surcharge."""
        midnight_time = datetime(2026, 8, 7, 2, 0)
        offpeak_time = datetime(2026, 8, 7, 14, 30)

        distance = 5000
        duration = 600

        night_res = calculate_sg_taxi_fare(distance, duration, midnight_time)
        day_res = calculate_sg_taxi_fare(distance, duration, offpeak_time)

        self.assertGreater(night_res["min_fare_sgd"], day_res["min_fare_sgd"])


if __name__ == "__main__":
    unittest.main()