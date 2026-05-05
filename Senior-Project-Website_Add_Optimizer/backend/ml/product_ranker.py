"""Helpers for training and using a supervised product ranking model."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

PRODUCT_RANKER_PATH = Path(__file__).resolve().parent / "product_ranker.pkl"
PRODUCTS_PATHS = (
    Path(__file__).resolve().parents[3] / "frontend" / "data" / "products.json",
    Path("/seed-data/products.json"),
)


@dataclass
class SessionPreferenceSnapshot:
    """Compact behavior profile used to compare a session with candidate products."""

    seen_product_ids: set[int]
    top_category: str | None
    category_counts: Counter[str]
    avg_price: float | None
    min_price: float | None
    max_price: float | None
    preferred_brands: Counter[str]
    preferred_colors: Counter[str]
    preferred_sizes: Counter[str]
    preferred_storage: Counter[str]
    preferred_skin_types: Counter[str]


@lru_cache(maxsize=1)
def load_products_catalog() -> list[dict[str, Any]]:
    """Load the storefront product catalog."""
    for path in PRODUCTS_PATHS:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("Unable to locate frontend/data/products.json")


def _counter_weights(counter: Counter[str]) -> dict[str, float]:
    """Normalize preference counts into [0, 1] weights."""
    if not counter:
        return {}
    top_count = max(counter.values()) or 1
    return {key: value / top_count for key, value in counter.items()}


def derive_session_preference_snapshot(events: list[Any]) -> SessionPreferenceSnapshot:
    """Extract category, price, and attribute preferences from tracked events."""
    category_counts: Counter[str] = Counter()
    brand_counts: Counter[str] = Counter()
    color_counts: Counter[str] = Counter()
    size_counts: Counter[str] = Counter()
    storage_counts: Counter[str] = Counter()
    skin_type_counts: Counter[str] = Counter()
    prices: list[float] = []
    seen_product_ids: set[int] = set()

    for event in events:
        metadata = getattr(event, "metadata_json", None) or {}

        product_id = metadata.get("product_id")
        if isinstance(product_id, int):
            seen_product_ids.add(product_id)

        category = metadata.get("category")
        if isinstance(category, str) and category:
            category_counts[category] += 1

        price = metadata.get("price")
        if isinstance(price, (int, float)):
            prices.append(float(price))

        available_attributes = metadata.get("available_attributes") or {}
        selected_attributes = metadata.get("selected_attributes") or {}

        brand = available_attributes.get("brand")
        if isinstance(brand, str) and brand:
            brand_counts[brand] += 1

        for key, value in selected_attributes.items():
            if not isinstance(value, str) or not value:
                continue
            if key == "colors":
                color_counts[value] += 1
            elif key == "sizes":
                size_counts[value] += 1
            elif key == "storage":
                storage_counts[value] += 1
            elif key == "skin_type":
                skin_type_counts[value] += 1

        attribute_group = metadata.get("attribute_group")
        attribute_value = metadata.get("attribute_value")
        if isinstance(attribute_group, str) and isinstance(attribute_value, str) and attribute_value:
            if attribute_group == "colors":
                color_counts[attribute_value] += 1
            elif attribute_group == "sizes":
                size_counts[attribute_value] += 1
            elif attribute_group == "storage":
                storage_counts[attribute_value] += 1
            elif attribute_group == "skin_type":
                skin_type_counts[attribute_value] += 1

    top_category = category_counts.most_common(1)[0][0] if category_counts else None
    return SessionPreferenceSnapshot(
        seen_product_ids=seen_product_ids,
        top_category=top_category,
        category_counts=category_counts,
        avg_price=(sum(prices) / len(prices)) if prices else None,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        preferred_brands=brand_counts,
        preferred_colors=color_counts,
        preferred_sizes=size_counts,
        preferred_storage=storage_counts,
        preferred_skin_types=skin_type_counts,
    )


def build_candidate_feature_map(snapshot: SessionPreferenceSnapshot, product: dict[str, Any]) -> dict[str, float | str | bool]:
    """Build a supervised-learning feature map for one session-product pair."""
    attributes = product.get("attributes") or {}
    if not isinstance(attributes, dict):
        attributes = {}

    brand_weights = _counter_weights(snapshot.preferred_brands)
    color_weights = _counter_weights(snapshot.preferred_colors)
    size_weights = _counter_weights(snapshot.preferred_sizes)
    storage_weights = _counter_weights(snapshot.preferred_storage)
    skin_type_weights = _counter_weights(snapshot.preferred_skin_types)

    def best_list_match(values: Any, weights: dict[str, float]) -> float:
        if not isinstance(values, list) or not weights:
            return 0.0
        best = 0.0
        for value in values:
            if isinstance(value, str):
                best = max(best, weights.get(value, 0.0))
        return best

    product_price = float(product.get("price") or 0.0)
    avg_price = snapshot.avg_price or 0.0
    price_delta = abs(product_price - avg_price) if avg_price > 0 else product_price
    price_delta_ratio = (price_delta / avg_price) if avg_price > 0 else 1.0

    return {
        "candidate_category": str(product.get("category") or ""),
        "candidate_brand": str(attributes.get("brand") or ""),
        "candidate_price": product_price,
        "candidate_discount": float(product.get("discount") or 0.0),
        "candidate_rating": float(product.get("rating") or 0.0),
        "candidate_sales_count": float(product.get("salesCount") or 0.0),
        "session_top_category": snapshot.top_category or "",
        "session_avg_price": avg_price,
        "session_price_min": float(snapshot.min_price or 0.0),
        "session_price_max": float(snapshot.max_price or 0.0),
        "price_delta_ratio": price_delta_ratio,
        "matches_top_category": snapshot.top_category == product.get("category"),
        "in_session_price_range": (
            snapshot.min_price is not None
            and snapshot.max_price is not None
            and snapshot.min_price <= product_price <= snapshot.max_price
        ),
        "brand_preference_weight": brand_weights.get(str(attributes.get("brand") or ""), 0.0),
        "color_preference_weight": best_list_match(attributes.get("colors"), color_weights),
        "size_preference_weight": best_list_match(attributes.get("sizes"), size_weights),
        "storage_preference_weight": best_list_match(attributes.get("storage"), storage_weights),
        "skin_type_preference_weight": best_list_match(attributes.get("skin_type"), skin_type_weights),
        "session_seen_products": float(len(snapshot.seen_product_ids)),
        "session_category_diversity": float(len(snapshot.category_counts)),
    }


def load_product_ranker_artifact() -> dict[str, Any]:
    """Load the persisted supervised product ranker artifact."""
    if not PRODUCT_RANKER_PATH.exists():
        raise FileNotFoundError(f"Product ranker not found: {PRODUCT_RANKER_PATH}")
    return joblib.load(PRODUCT_RANKER_PATH)


def rank_products_with_model(
    events: list[Any],
    limit: int = 8,
    exclude_viewed: bool = True,
) -> list[dict[str, Any]]:
    """Score catalog products with the trained supervised ranker."""
    artifact = load_product_ranker_artifact()
    vectorizer = artifact["vectorizer"]
    model = artifact["model"]

    snapshot = derive_session_preference_snapshot(events)
    scored_rows: list[dict[str, Any]] = []

    for product in load_products_catalog():
        product_id = product.get("id")
        if exclude_viewed and isinstance(product_id, int) and product_id in snapshot.seen_product_ids:
            continue

        feature_map = build_candidate_feature_map(snapshot, product)
        feature_matrix = vectorizer.transform([feature_map])
        probability = float(model.predict_proba(feature_matrix)[0][1])
        scored_rows.append({"product": product, "score": probability, "snapshot": snapshot})

    scored_rows.sort(key=lambda row: row["score"], reverse=True)
    return scored_rows[:limit]
