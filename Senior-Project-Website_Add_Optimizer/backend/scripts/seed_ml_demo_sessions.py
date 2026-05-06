"""Seed low, medium, and high engagement sessions for KMeans ML demos."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import random
import sys
from typing import Any

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import Event, VisitorSession  # noqa: E402

DEMO_VISITOR_PREFIX = "ml-demo-"
CATEGORY_SLUGS = (
    "electronics",
    "clothing",
    "beauty",
    "home-appliances",
    "books",
    "sports",
)

PRODUCT_FIXTURES = {
    "electronics": {
        "product_id": 101,
        "product_name": "Demo Wireless Headphones",
        "category": "electronics",
        "category_name": "Electronics",
        "price": 129.99,
        "brand": "Neon Audio",
    },
    "clothing": {
        "product_id": 201,
        "product_name": "Demo Retro Jacket",
        "category": "clothing",
        "category_name": "Clothing",
        "price": 74.99,
        "brand": "SynthWear",
    },
    "beauty": {
        "product_id": 301,
        "product_name": "Demo Night Serum",
        "category": "beauty",
        "category_name": "Beauty",
        "price": 39.99,
        "brand": "Glow Grid",
    },
    "home-appliances": {
        "product_id": 401,
        "product_name": "Demo Smart Blender",
        "category": "home-appliances",
        "category_name": "Home Appliances",
        "price": 159.99,
        "brand": "HomeWave",
    },
    "books": {
        "product_id": 501,
        "product_name": "Demo Cyberpunk Novel",
        "category": "books",
        "category_name": "Books",
        "price": 18.99,
        "brand": "Neon Press",
    },
    "sports": {
        "product_id": 601,
        "product_name": "Demo Training Shoes",
        "category": "sports",
        "category_name": "Sports",
        "price": 94.99,
        "brand": "Arcade Athletics",
    },
}

SEGMENT_PATTERNS = {
    "low": {
        "page_views": (1, 3),
        "product_clicks": (0, 1),
        "attribute_clicks": (0, 1),
        "cart_clicks": (0, 0),
        "dwell_seconds": (25, 110),
    },
    "medium": {
        "page_views": (3, 6),
        "product_clicks": (1, 3),
        "attribute_clicks": (1, 3),
        "cart_clicks": (0, 1),
        "dwell_seconds": (140, 380),
    },
    "high": {
        "page_views": (6, 11),
        "product_clicks": (3, 7),
        "attribute_clicks": (2, 6),
        "cart_clicks": (1, 3),
        "dwell_seconds": (420, 980),
    },
}


def parse_args() -> argparse.Namespace:
    """Parse CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sessions-per-segment",
        type=int,
        default=12,
        help="Number of low, medium, and high demo sessions to seed.",
    )
    parser.add_argument("--days", type=int, default=14, help="Spread demo sessions across this many recent days.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible demo data.")
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Delete only previously seeded ML demo sessions before inserting new ones.",
    )
    return parser.parse_args()


def _event(
    session_id: int,
    timestamp: datetime,
    event_type: str,
    page: str,
    *,
    element: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Event:
    return Event(
        session_id=session_id,
        type=event_type,
        page=page,
        element=element,
        timestamp=timestamp,
        metadata_json=metadata,
    )


def _product_metadata(category: str, index: int) -> dict[str, Any]:
    product = dict(PRODUCT_FIXTURES[category])
    product["product_id"] = int(product["product_id"]) + index
    return {
        **product,
        "available_attributes": {
            "brand": product["brand"],
            "colors": ["Black", "Neon Blue", "Chrome"],
            "sizes": ["S", "M", "L"],
            "storage": ["128GB", "256GB"],
            "skin_type": ["Normal", "Dry"],
        },
    }


def _create_demo_session(segment_name: str, index: int, days: int) -> tuple[VisitorSession, list[Event]]:
    pattern = SEGMENT_PATTERNS[segment_name]
    now = datetime.now(UTC)
    started_at = now - timedelta(days=random.randint(0, max(days - 1, 0)), minutes=random.randint(5, 720))
    dwell_seconds = random.randint(*pattern["dwell_seconds"])
    ended_at = started_at + timedelta(seconds=dwell_seconds)

    session = VisitorSession(
        user_agent=f"ML demo browser ({segment_name})",
        referrer="http://localhost:8000/index.html",
        created_at=started_at,
        visitor_id=f"{DEMO_VISITOR_PREFIX}{segment_name}-{index}",
        started_at=started_at,
        ended_at=ended_at,
        page_count=0,
    )

    event_specs: list[tuple[str, str, str | None, dict[str, Any] | None]] = []
    page_views = random.randint(*pattern["page_views"])
    product_clicks = random.randint(*pattern["product_clicks"])
    attribute_clicks = random.randint(*pattern["attribute_clicks"])
    cart_clicks = random.randint(*pattern["cart_clicks"])
    preferred_categories = random.sample(list(CATEGORY_SLUGS), k=1 if segment_name == "low" else 2 if segment_name == "medium" else 3)

    event_specs.append(("page_view", "home", None, {"path": "/index.html", "query": None}))
    for page_index in range(max(page_views - 1, 0)):
        category = preferred_categories[page_index % len(preferred_categories)]
        event_specs.append(
            (
                "page_view",
                category,
                None,
                {"path": "/category.html", "query": f"?cat={category}"},
            )
        )

    for click_index in range(product_clicks):
        category = preferred_categories[click_index % len(preferred_categories)]
        metadata = _product_metadata(category, index + click_index)
        event_specs.append(("click", "category", "open-product", metadata))
        event_specs.append(
            (
                "page_view",
                "product",
                None,
                {"path": "/product.html", "query": f"?id={metadata['product_id']}"},
            )
        )

    for attr_index in range(attribute_clicks):
        category = preferred_categories[attr_index % len(preferred_categories)]
        metadata = {
            **_product_metadata(category, index + attr_index),
            "attribute_group": "colors",
            "attribute_label": "Colors",
            "attribute_value": "Neon Blue",
            "selected_attributes": {"colors": "Neon Blue"},
        }
        event_specs.append(("click", "product", "select-attribute", metadata))

    for cart_index in range(cart_clicks):
        category = preferred_categories[cart_index % len(preferred_categories)]
        metadata = {
            **_product_metadata(category, index + cart_index),
            "selected_attributes": {"colors": "Neon Blue"},
            "quantity": 1,
            "cart_size_after_add": cart_index + 1,
        }
        event_specs.append(("click", "product", "add-to-cart", metadata))

    session.page_count = sum(1 for event_type, _, _, _ in event_specs if event_type == "page_view")

    step_seconds = max(1, dwell_seconds // max(len(event_specs), 1))
    events = [
        _event(
            session_id=0,
            timestamp=started_at + timedelta(seconds=offset * step_seconds),
            event_type=event_type,
            page=page,
            element=element,
            metadata=metadata,
        )
        for offset, (event_type, page, element, metadata) in enumerate(event_specs)
    ]
    return session, events


def _reset_demo_sessions(db_session: Any) -> int:
    demo_sessions = list(
        db_session.execute(
            select(VisitorSession).where(VisitorSession.visitor_id.like(f"{DEMO_VISITOR_PREFIX}%"))
        )
        .scalars()
        .all()
    )
    for session in demo_sessions:
        db_session.delete(session)
    db_session.flush()
    return len(demo_sessions)


def seed_demo_sessions(sessions_per_segment: int, days: int, reset_demo: bool) -> None:
    """Insert balanced demo sessions for all three engagement levels."""
    with SessionLocal() as db_session:
        deleted_count = _reset_demo_sessions(db_session) if reset_demo else 0
        session_count = 0
        event_count = 0

        for segment_name in ("low", "medium", "high"):
            for index in range(sessions_per_segment):
                session, events = _create_demo_session(segment_name, index, days)
                db_session.add(session)
                db_session.flush()
                for event in events:
                    event.session_id = session.id
                db_session.add_all(events)
                session_count += 1
                event_count += len(events)

        db_session.commit()

    if reset_demo:
        print(f"Deleted {deleted_count} existing ML demo sessions")
    print(f"Seeded {session_count} ML demo sessions")
    print(f"Seeded {event_count} ML demo events")
    print("Segment balance:")
    for segment_name in ("low", "medium", "high"):
        print(f"  {segment_name}: {sessions_per_segment} sessions")


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    seed_demo_sessions(
        sessions_per_segment=args.sessions_per_segment,
        days=args.days,
        reset_demo=args.reset_demo,
    )


if __name__ == "__main__":
    main()
