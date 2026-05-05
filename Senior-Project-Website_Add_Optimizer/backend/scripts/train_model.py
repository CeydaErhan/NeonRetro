"""Train the session engagement model from real visitor session data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import Event, VisitorSession  # noqa: E402
from ml.scoring import CATEGORY_SLUGS, FEATURE_NAMES, MODEL_PATH, train_and_save_model  # noqa: E402


@dataclass
class SessionFeatures:
    """Feature values extracted from one visitor session."""

    page_count: int
    click_count: int
    dwell_time_seconds: float
    unique_products: int
    add_to_cart_count: int
    attribute_selection_count: int
    avg_price: float
    price_stddev: float
    category_diversity: int
    electronics_ratio: float
    clothing_ratio: float
    beauty_ratio: float
    home_appliances_ratio: float
    books_ratio: float
    sports_ratio: float

    def to_row(self) -> list[float]:
        """Return the feature row in model order."""
        return [
            float(self.page_count),
            float(self.click_count),
            float(self.dwell_time_seconds),
            float(self.unique_products),
            float(self.add_to_cart_count),
            float(self.attribute_selection_count),
            float(self.avg_price),
            float(self.price_stddev),
            float(self.category_diversity),
            float(self.electronics_ratio),
            float(self.clothing_ratio),
            float(self.beauty_ratio),
            float(self.home_appliances_ratio),
            float(self.books_ratio),
            float(self.sports_ratio),
        ]


def _coerce_utc(dt: datetime | None) -> datetime | None:
    """Normalize a timestamp into UTC to make subtraction safe."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def extract_session_features(visitor_session: VisitorSession) -> SessionFeatures | None:
    """Build one training row from a visitor session and its event history."""
    events = sorted(visitor_session.events, key=lambda event: (event.timestamp, event.id))
    if not events:
        return None

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

    session_start = _coerce_utc(visitor_session.started_at) or _coerce_utc(events[0].timestamp)
    session_end = (
        _coerce_utc(visitor_session.ended_at)
        or _coerce_utc(events[-1].timestamp)
        or session_start
        or datetime.now(timezone.utc)
    )

    dwell_time_seconds = 0.0
    if session_start is not None:
        dwell_time_seconds = max((session_end - session_start).total_seconds(), 0.0)

    avg_price = float(sum(prices) / len(prices)) if prices else 0.0
    price_stddev = float(np.std(prices)) if len(prices) > 1 else 0.0
    total_category_hits = sum(category_counts.values()) or 1
    category_ratios = {
        slug.replace("-", "_") + "_ratio": category_counts[slug] / total_category_hits for slug in CATEGORY_SLUGS
    }

    return SessionFeatures(
        page_count=page_count,
        click_count=click_count,
        dwell_time_seconds=dwell_time_seconds,
        unique_products=len(product_ids),
        add_to_cart_count=add_to_cart_count,
        attribute_selection_count=attribute_selection_count,
        avg_price=avg_price,
        price_stddev=price_stddev,
        category_diversity=len(categories),
        electronics_ratio=category_ratios["electronics_ratio"],
        clothing_ratio=category_ratios["clothing_ratio"],
        beauty_ratio=category_ratios["beauty_ratio"],
        home_appliances_ratio=category_ratios["home_appliances_ratio"],
        books_ratio=category_ratios["books_ratio"],
        sports_ratio=category_ratios["sports_ratio"],
    )


def load_training_rows(limit: int | None, days: int | None) -> tuple[np.ndarray, int]:
    """Load real session-derived feature rows from the database."""
    with SessionLocal() as db:
        stmt = select(VisitorSession).options(selectinload(VisitorSession.events))

        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(VisitorSession.started_at >= cutoff)

        stmt = stmt.order_by(VisitorSession.started_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)

        sessions = list(db.execute(stmt).scalars().all())

    rows: list[list[float]] = []
    for visitor_session in sessions:
        features = extract_session_features(visitor_session)
        if features is None:
            continue
        rows.append(features.to_row())

    if not rows:
        return np.empty((0, len(FEATURE_NAMES))), 0

    return np.array(rows, dtype=float), len(rows)


def count_total_sessions() -> int:
    """Return the number of sessions with at least one tracked event."""
    with SessionLocal() as db:
        stmt = (
            select(VisitorSession.id)
            .join(Event, Event.session_id == VisitorSession.id)
            .group_by(VisitorSession.id)
        )
        return len(list(db.execute(stmt).scalars().all()))


def parse_args() -> argparse.Namespace:
    """Parse CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Only train on the most recent N sessions.")
    parser.add_argument("--days", type=int, default=None, help="Only train on sessions from the last N days.")
    parser.add_argument(
        "--min-sessions",
        type=int,
        default=50,
        help="Require at least this many sessions before training the model.",
    )
    return parser.parse_args()


def main() -> int:
    """Train and persist the KMeans session model."""
    args = parse_args()

    feature_matrix, used_sessions = load_training_rows(limit=args.limit, days=args.days)
    total_sessions = count_total_sessions()

    if used_sessions < args.min_sessions:
        print(
            f"Not enough sessions to train model: found {used_sessions}, need at least {args.min_sessions}.",
            file=sys.stderr,
        )
        print(f"Total sessions with events currently available: {total_sessions}", file=sys.stderr)
        return 1

    model_path = train_and_save_model(feature_matrix)
    print(f"Model trained successfully: {model_path}")
    print(f"Sessions used: {used_sessions}")
    print(f"Feature set: {', '.join(FEATURE_NAMES)}")
    print(f"Output file: {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
