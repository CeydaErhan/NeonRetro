"""Train a supervised session-product ranker from tracked interaction data."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import sys
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import select
from sqlalchemy.orm import selectinload

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import VisitorSession  # noqa: E402
from ml.product_ranker import (  # noqa: E402
    PRODUCT_RANKER_PATH,
    build_candidate_feature_map,
    derive_session_preference_snapshot,
    load_products_catalog,
)

RANDOM_STATE = 42


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Only train on the most recent N sessions.")
    parser.add_argument("--days", type=int, default=None, help="Only train on sessions from the last N days.")
    parser.add_argument("--min-sessions", type=int, default=50, help="Require at least this many sessions.")
    parser.add_argument(
        "--negatives-per-positive",
        type=int,
        default=3,
        help="How many negative candidate products to sample for each positive product.",
    )
    return parser.parse_args()


def load_sessions(limit: int | None, days: int | None) -> list[VisitorSession]:
    """Load sessions with events for supervised ranker training."""
    with SessionLocal() as db:
        stmt = select(VisitorSession).options(selectinload(VisitorSession.events))
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(VisitorSession.started_at >= cutoff)
        stmt = stmt.order_by(VisitorSession.started_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(db.execute(stmt).scalars().all())


def extract_positive_product_ids(events: list[Any]) -> set[int]:
    """Treat interacted products as positive labels."""
    positives: set[int] = set()
    for event in events:
        metadata = getattr(event, "metadata_json", None) or {}
        product_id = metadata.get("product_id")
        if isinstance(product_id, int):
            positives.add(product_id)
    return positives


def build_negative_product_pool(
    catalog: list[dict[str, Any]],
    positive_ids: set[int],
    preferred_categories: Counter[str],
) -> list[dict[str, Any]]:
    """Prioritize same-category negatives while keeping catalog diversity."""
    top_categories = {category for category, _ in preferred_categories.most_common(2)}
    same_category = [
        product for product in catalog if product.get("id") not in positive_ids and product.get("category") in top_categories
    ]
    other_products = [
        product for product in catalog if product.get("id") not in positive_ids and product.get("category") not in top_categories
    ]
    return same_category + other_products


def build_training_examples(
    sessions: list[VisitorSession],
    negatives_per_positive: int,
) -> tuple[list[dict[str, float | str | bool]], list[int], int]:
    """Generate labeled session-product examples for supervised learning."""
    rng = random.Random(RANDOM_STATE)
    catalog = load_products_catalog()
    catalog_by_id = {int(product["id"]): product for product in catalog if isinstance(product.get("id"), int)}

    rows: list[dict[str, float | str | bool]] = []
    labels: list[int] = []
    used_sessions = 0

    for visitor_session in sessions:
        events = sorted(visitor_session.events, key=lambda event: (event.timestamp, event.id))
        if not events:
            continue

        positive_ids = extract_positive_product_ids(events)
        if not positive_ids:
            continue

        snapshot = derive_session_preference_snapshot(events)
        negative_pool = build_negative_product_pool(catalog, positive_ids, snapshot.category_counts)
        if not negative_pool:
            continue

        used_sessions += 1

        for product_id in positive_ids:
            product = catalog_by_id.get(product_id)
            if product is None:
                continue
            rows.append(build_candidate_feature_map(snapshot, product))
            labels.append(1)

            negative_count = min(len(negative_pool), negatives_per_positive)
            sampled_negatives = rng.sample(negative_pool, k=negative_count)
            for negative_product in sampled_negatives:
                rows.append(build_candidate_feature_map(snapshot, negative_product))
                labels.append(0)

    return rows, labels, used_sessions


def main() -> int:
    """Train and persist the supervised product ranker."""
    args = parse_args()
    sessions = load_sessions(limit=args.limit, days=args.days)
    rows, labels, used_sessions = build_training_examples(sessions, args.negatives_per_positive)

    if used_sessions < args.min_sessions:
        print(
            f"Not enough sessions to train product ranker: found {used_sessions}, need at least {args.min_sessions}.",
            file=sys.stderr,
        )
        return 1

    if len(set(labels)) < 2:
        print("Training data must contain both positive and negative examples.", file=sys.stderr)
        return 1

    vectorizer = DictVectorizer(sparse=True)
    X = vectorizer.fit_transform(rows)
    y = np.asarray(labels, dtype=int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    model = LogisticRegression(
        max_iter=5000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        solver="liblinear",
    )
    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
    }

    artifact = {
        "model": model,
        "vectorizer": vectorizer,
        "metrics": metrics,
        "feature_names": vectorizer.get_feature_names_out().tolist(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "used_sessions": used_sessions,
        "example_count": len(labels),
        "positive_examples": int(np.sum(y)),
        "negative_examples": int(len(y) - np.sum(y)),
    }
    PRODUCT_RANKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, PRODUCT_RANKER_PATH)

    print(f"Product ranker trained successfully: {PRODUCT_RANKER_PATH}")
    print(f"Sessions used: {used_sessions}")
    print(f"Examples: {len(labels)}")
    print(f"Positive examples: {artifact['positive_examples']}")
    print(f"Negative examples: {artifact['negative_examples']}")
    print(
        "Metrics: "
        + ", ".join(f"{name}={value:.3f}" for name, value in metrics.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
