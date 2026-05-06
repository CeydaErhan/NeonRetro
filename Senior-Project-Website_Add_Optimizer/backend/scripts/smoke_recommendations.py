"""Smoke test the explainable KMeans recommendation path for one session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import joblib
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import Event, VisitorSession  # noqa: E402
from ml.recommendation import get_recommendations  # noqa: E402
from ml.scoring import CATEGORY_SLUGS, MODEL_PATH, SEGMENT_LABELS, score_session  # noqa: E402


def _derive_session_ml_features(visitor_session: VisitorSession, events: list[Event]) -> dict[str, float]:
    """Compute the feature set consumed by the persisted KMeans model."""
    page_count = sum(1 for event in events if event.type in {"page_view", "pageview"})
    click_count = sum(1 for event in events if event.type == "click")
    add_to_cart_count = sum(1 for event in events if event.element == "add-to-cart")
    attribute_selection_count = sum(1 for event in events if event.element == "select-attribute")

    product_ids: set[int] = set()
    categories: set[str] = set()
    prices: list[float] = []
    category_counts = {slug: 0 for slug in CATEGORY_SLUGS}

    for event in events:
        metadata = event.metadata_json or {}
        product_id = metadata.get("product_id")
        if isinstance(product_id, int):
            product_ids.add(product_id)

        category = metadata.get("category")
        if isinstance(category, str) and category:
            categories.add(category)
            if category in category_counts:
                category_counts[category] += 1

        price = metadata.get("price")
        if isinstance(price, (int, float)):
            prices.append(float(price))

    session_end = visitor_session.ended_at or (events[-1].timestamp if events else None) or visitor_session.started_at
    dwell_time_seconds = max((session_end - visitor_session.started_at).total_seconds(), 0.0)
    avg_price = float(sum(prices) / len(prices)) if prices else 0.0
    price_stddev = float(sum((price - avg_price) ** 2 for price in prices) / len(prices)) ** 0.5 if len(prices) > 1 else 0.0
    total_category_hits = sum(category_counts.values()) or 1

    return {
        "page_count": page_count,
        "click_count": click_count,
        "dwell_time_seconds": dwell_time_seconds,
        "unique_products": len(product_ids),
        "add_to_cart_count": add_to_cart_count,
        "attribute_selection_count": attribute_selection_count,
        "avg_price": avg_price,
        "price_stddev": price_stddev,
        "category_diversity": len(categories),
        "electronics_ratio": category_counts["electronics"] / total_category_hits,
        "clothing_ratio": category_counts["clothing"] / total_category_hits,
        "beauty_ratio": category_counts["beauty"] / total_category_hits,
        "home_appliances_ratio": category_counts["home-appliances"] / total_category_hits,
        "books_ratio": category_counts["books"] / total_category_hits,
        "sports_ratio": category_counts["sports"] / total_category_hits,
    }


def _segment_label(segment: int) -> str:
    """Return the stable human-readable label for a KMeans segment."""
    return SEGMENT_LABELS.get(segment, f"segment-{segment}")


def _ranking_strategy(segment: int) -> str:
    """Return the SDD ad ranking strategy used for a KMeans segment."""
    if segment == 0:
        return "newest_ads"
    if segment == 1:
        return "impression_popularity"
    return "ctr_performance"


def _load_model_metadata() -> dict[str, object] | None:
    """Read safe metadata from the persisted KMeans artifact when available."""
    if not MODEL_PATH.exists():
        return None
    try:
        payload = joblib.load(MODEL_PATH)
    except Exception:
        return None

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return None
    return metadata


def parse_args() -> argparse.Namespace:
    """Parse CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", type=int, required=True, help="Visitor session id to score.")
    parser.add_argument("--limit", type=int, default=3, help="Number of recommended ads to inspect.")
    return parser.parse_args()


def main() -> int:
    """Print the explainable recommendation payload pieces for one session."""
    args = parse_args()

    with SessionLocal() as db:
        visitor_session = db.execute(
            select(VisitorSession).where(VisitorSession.id == args.session_id)
        ).scalar_one_or_none()
        if visitor_session is None:
            print(f"Visitor session not found: {args.session_id}", file=sys.stderr)
            return 1

        events = list(
            db.execute(
                select(Event)
                .where(Event.session_id == args.session_id)
                .order_by(Event.timestamp.asc(), Event.id.asc())
            )
            .scalars()
            .all()
        )
        features = _derive_session_ml_features(visitor_session, events)
        segment = score_session(**features)
        ads = get_recommendations(segment=segment, db_session=db, limit=args.limit)

    payload = {
        "session_id": args.session_id,
        "segment": segment,
        "segment_label": _segment_label(segment),
        "ranking_strategy": _ranking_strategy(segment),
        "features_used": features,
        "model_metadata": _load_model_metadata(),
        "recommended_ad_ids": [ad.id for ad in ads],
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
