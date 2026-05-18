from pathlib import Path
import datetime as _datetime
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "Senior-Project-Website_Add_Optimizer" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if not hasattr(_datetime, "UTC"):
    _datetime.UTC = _datetime.timezone.utc

from ml.calibration import SEGMENT_STRATEGY_MAPPING, calibrate_business_segment  # noqa: E402


class SegmentCalibrationTests(unittest.TestCase):
    def test_strong_purchase_signals_upgrade_medium_cluster_to_high_intent(self):
        calibrated = calibrate_business_segment(
            1,
            page_count=5,
            click_count=9,
            dwell_time_seconds=540,
            unique_products=3,
            add_to_cart_count=3,
            attribute_selection_count=3,
            avg_price=1437.49,
            price_stddev=757.77,
            category_diversity=1,
            electronics_ratio=1.0,
            clothing_ratio=0.0,
            beauty_ratio=0.0,
            home_appliances_ratio=0.0,
            books_ratio=0.0,
            sports_ratio=0.0,
        )

        self.assertEqual(calibrated["final_segment"], 2)
        self.assertEqual(SEGMENT_STRATEGY_MAPPING["high"], "ctr_performance")
        self.assertTrue(calibrated["calibration_applied"])
        self.assertEqual(
            calibrated["calibration_reason"],
            "strong_purchase_intent:add_to_cart_and_attribute_selection",
        )

    def test_low_activity_segment_is_not_calibrated(self):
        calibrated = calibrate_business_segment(
            0,
            page_count=2,
            click_count=1,
            dwell_time_seconds=50,
            unique_products=1,
            add_to_cart_count=0,
            attribute_selection_count=0,
            category_diversity=1,
        )

        self.assertEqual(calibrated["final_segment"], 0)
        self.assertFalse(calibrated["calibration_applied"])
        self.assertIsNone(calibrated["calibration_reason"])

    def test_moderate_product_interest_upgrades_low_cluster_to_medium(self):
        calibrated = calibrate_business_segment(
            0,
            page_count=3,
            click_count=2,
            dwell_time_seconds=260,
            unique_products=1,
            add_to_cart_count=0,
            attribute_selection_count=1,
            category_diversity=1,
        )

        self.assertEqual(calibrated["final_segment"], 1)
        self.assertTrue(calibrated["calibration_applied"])
        self.assertEqual(
            calibrated["calibration_reason"],
            "moderate_product_interest:attribute_selection_and_browsing",
        )


if __name__ == "__main__":
    unittest.main()
