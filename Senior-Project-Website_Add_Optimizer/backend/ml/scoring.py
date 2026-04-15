"""Session scoring utilities backed by a persisted KMeans model."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
RANDOM_STATE = 42


def _generate_synthetic_sessions(sample_count: int = 500) -> np.ndarray:
    """Generate synthetic session features with low, medium, and high engagement patterns."""
    rng = np.random.default_rng(RANDOM_STATE)

    low_count = sample_count // 3
    medium_count = sample_count // 3
    high_count = sample_count - low_count - medium_count

    low = np.column_stack(
        (
            rng.integers(1, 4, size=low_count),
            rng.integers(0, 2, size=low_count),
            rng.integers(20, 121, size=low_count),
        )
    )
    medium = np.column_stack(
        (
            rng.integers(3, 8, size=medium_count),
            rng.integers(1, 5, size=medium_count),
            rng.integers(90, 361, size=medium_count),
        )
    )
    high = np.column_stack(
        (
            rng.integers(6, 15, size=high_count),
            rng.integers(3, 10, size=high_count),
            rng.integers(240, 901, size=high_count),
        )
    )

    dataset = np.vstack((low, medium, high)).astype(float)
    rng.shuffle(dataset)
    return dataset


def _fit_model() -> dict[str, object]:
    """Train a KMeans model and build a stable low/medium/high segment mapping."""
    training_data = _generate_synthetic_sessions()
    model = KMeans(n_clusters=3, random_state=RANDOM_STATE, n_init=10)
    model.fit(training_data)

    centers = model.cluster_centers_
    ranked_clusters = sorted(
        range(len(centers)),
        key=lambda index: float(centers[index][0] + centers[index][1] + (centers[index][2] / 60.0)),
    )
    cluster_to_segment = {cluster_index: segment for segment, cluster_index in enumerate(ranked_clusters)}

    payload = {
        "model": model,
        "cluster_to_segment": cluster_to_segment,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, MODEL_PATH)
    return payload


def _load_or_train_model() -> dict[str, object]:
    """Load the persisted model or train and save it if missing."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return _fit_model()


def ensure_model() -> Path:
    """Ensure the model exists on disk and return its path."""
    _load_or_train_model()
    return MODEL_PATH


def score_session(page_count: int, click_count: int, dwell_time_seconds: float) -> int:
    """Score a visitor session into low, medium, or high engagement segments."""
    payload = _load_or_train_model()
    model: KMeans = payload["model"]
    cluster_to_segment: dict[int, int] = payload["cluster_to_segment"]

    features = np.array([[page_count, click_count, dwell_time_seconds]], dtype=float)
    cluster = int(model.predict(features)[0])
    return cluster_to_segment[cluster]
