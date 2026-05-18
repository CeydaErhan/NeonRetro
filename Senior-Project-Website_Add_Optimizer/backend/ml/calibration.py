"""Business calibration rules applied after KMeans session segmentation."""

from __future__ import annotations

HIGH_INTENT_SEGMENT = 2
MEDIUM_INTENT_SEGMENT = 1
STRONG_PURCHASE_INTENT_REASON = "strong_purchase_intent:add_to_cart_and_attribute_selection"
MODERATE_PRODUCT_INTEREST_REASON = "moderate_product_interest:attribute_selection_and_browsing"
SEGMENT_STRATEGY_MAPPING = {
    "low": "least_exposed_ads",
    "medium": "impression_popularity",
    "high": "ctr_performance",
}


def calibrate_business_segment(kmeans_segment: int, **features: object) -> dict[str, object]:
    """Return the final business segment after explicit purchase-intent calibration."""
    add_to_cart_count = int(float(features.get("add_to_cart_count") or 0))
    attribute_selection_count = int(float(features.get("attribute_selection_count") or 0))
    click_count = int(float(features.get("click_count") or 0))
    dwell_time_seconds = float(features.get("dwell_time_seconds") or 0)

    if (
        kmeans_segment < HIGH_INTENT_SEGMENT
        and add_to_cart_count >= 2
        and attribute_selection_count >= 2
    ):
        return {
            "kmeans_segment": kmeans_segment,
            "final_segment": HIGH_INTENT_SEGMENT,
            "calibration_applied": True,
            "calibration_reason": STRONG_PURCHASE_INTENT_REASON,
        }

    if (
        kmeans_segment < MEDIUM_INTENT_SEGMENT
        and click_count >= 2
        and attribute_selection_count >= 1
        and dwell_time_seconds >= 180
    ):
        return {
            "kmeans_segment": kmeans_segment,
            "final_segment": MEDIUM_INTENT_SEGMENT,
            "calibration_applied": True,
            "calibration_reason": MODERATE_PRODUCT_INTEREST_REASON,
        }

    return {
        "kmeans_segment": kmeans_segment,
        "final_segment": kmeans_segment,
        "calibration_applied": False,
        "calibration_reason": None,
    }
