"""Session scoring utilities backed by a persisted KMeans model."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from ml.calibration import SEGMENT_STRATEGY_MAPPING

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
MODEL_METADATA_PATH = Path(__file__).resolve().parent / "model_metadata.json"
RANDOM_STATE = 42
N_CLUSTERS = 3
MODEL_TYPE = "kmeans_session_segmentation"
MODEL_VERSION = "kmeans-session-v1"
SEGMENT_LABELS = {
    0: "low",
    1: "medium",
    2: "high",
}
CATEGORY_SLUGS = [
    "electronics",
    "clothing",
    "beauty",
    "home-appliances",
    "books",
    "sports",
]
FEATURE_NAMES = [
    "page_count",
    "click_count",
    "dwell_time_seconds",
    "unique_products",
    "add_to_cart_count",
    "attribute_selection_count",
    "avg_price",
    "price_stddev",
    "category_diversity",
    "electronics_ratio",
    "clothing_ratio",
    "beauty_ratio",
    "home_appliances_ratio",
    "books_ratio",
    "sports_ratio",
]
SILHOUETTE_UNAVAILABLE = "not available for this model artifact"


def _generate_synthetic_sessions(sample_count: int = 500) -> np.ndarray:
    """Generate fallback session features with low, medium, and high engagement patterns."""
    rng = np.random.default_rng(RANDOM_STATE)

    low_count = sample_count // 3
    medium_count = sample_count // 3
    high_count = sample_count - low_count - medium_count

    def category_ratios(count: int, alpha: list[float]) -> np.ndarray:
        return rng.dirichlet(alpha, size=count)

    low = np.column_stack(
        (
            rng.integers(1, 4, size=low_count),
            rng.integers(0, 2, size=low_count),
            rng.integers(20, 121, size=low_count),
            rng.integers(0, 2, size=low_count),
            rng.integers(0, 1, size=low_count),
            rng.integers(0, 2, size=low_count),
            rng.uniform(15.0, 80.0, size=low_count),
            rng.uniform(0.0, 20.0, size=low_count),
            rng.integers(1, 2, size=low_count),
            category_ratios(low_count, [3, 2, 2, 1, 2, 2]),
        )
    )
    medium = np.column_stack(
        (
            rng.integers(3, 8, size=medium_count),
            rng.integers(1, 5, size=medium_count),
            rng.integers(90, 361, size=medium_count),
            rng.integers(1, 4, size=medium_count),
            rng.integers(0, 2, size=medium_count),
            rng.integers(1, 4, size=medium_count),
            rng.uniform(60.0, 220.0, size=medium_count),
            rng.uniform(10.0, 80.0, size=medium_count),
            rng.integers(1, 4, size=medium_count),
            category_ratios(medium_count, [2, 2, 2, 2, 2, 2]),
        )
    )
    high = np.column_stack(
        (
            rng.integers(6, 15, size=high_count),
            rng.integers(3, 10, size=high_count),
            rng.integers(240, 901, size=high_count),
            rng.integers(3, 8, size=high_count),
            rng.integers(1, 4, size=high_count),
            rng.integers(2, 7, size=high_count),
            rng.uniform(180.0, 950.0, size=high_count),
            rng.uniform(30.0, 200.0, size=high_count),
            rng.integers(2, 6, size=high_count),
            category_ratios(high_count, [3, 2, 1, 2, 1, 3]),
        )
    )

    dataset = np.vstack((low, medium, high)).astype(float)
    rng.shuffle(dataset)
    return dataset


def _cluster_engagement_score(cluster_center: np.ndarray) -> float:
    """Rank clusters from low to high engagement using raw feature values."""
    return float(
        cluster_center[0]
        + cluster_center[1]
        + (cluster_center[2] / 60.0)
        + cluster_center[3]
        + (cluster_center[4] * 1.5)
        + (cluster_center[5] * 0.75)
        + (cluster_center[6] / 250.0)
        + (cluster_center[7] / 50.0)
        + (cluster_center[8] * 0.5)
    )


def build_feature_vector(
    page_count: int,
    click_count: int,
    dwell_time_seconds: float,
    unique_products: int = 0,
    add_to_cart_count: int = 0,
    attribute_selection_count: int = 0,
    avg_price: float = 0.0,
    price_stddev: float = 0.0,
    category_diversity: int = 0,
    electronics_ratio: float = 0.0,
    clothing_ratio: float = 0.0,
    beauty_ratio: float = 0.0,
    home_appliances_ratio: float = 0.0,
    books_ratio: float = 0.0,
    sports_ratio: float = 0.0,
) -> np.ndarray:
    """Build a model-ready feature vector in a stable field order."""
    feature_map = {
        "page_count": float(page_count),
        "click_count": float(click_count),
        "dwell_time_seconds": float(dwell_time_seconds),
        "unique_products": float(unique_products),
        "add_to_cart_count": float(add_to_cart_count),
        "attribute_selection_count": float(attribute_selection_count),
        "avg_price": float(avg_price),
        "price_stddev": float(price_stddev),
        "category_diversity": float(category_diversity),
        "electronics_ratio": float(electronics_ratio),
        "clothing_ratio": float(clothing_ratio),
        "beauty_ratio": float(beauty_ratio),
        "home_appliances_ratio": float(home_appliances_ratio),
        "books_ratio": float(books_ratio),
        "sports_ratio": float(sports_ratio),
    }
    return np.array([[feature_map[name] for name in FEATURE_NAMES]], dtype=float)


def _build_metadata(
    *,
    training_source: str,
    training_session_count: int,
    silhouette_score_value: float | None = None,
    silhouette_score_note: str | None = None,
) -> dict[str, Any]:
    """Build metadata stored next to the persisted model artifact."""
    return {
        "algorithm": "KMeans",
        "model_type": MODEL_TYPE,
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(UTC).isoformat(),
        "training_source": training_source,
        "training_session_count": int(training_session_count),
        "feature_count": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "random_state": RANDOM_STATE,
        "n_clusters": N_CLUSTERS,
        "scaler": "StandardScaler",
        "scaler_type": "StandardScaler",
        "silhouette_score": silhouette_score_value,
        "silhouette_score_note": silhouette_score_note,
        "segment_labels": SEGMENT_LABELS,
        "segment_strategy_mapping": SEGMENT_STRATEGY_MAPPING,
    }


def _compute_silhouette_score(scaled_features: np.ndarray, labels: np.ndarray) -> tuple[float | None, str | None]:
    """Compute a cluster quality score when the fitted labels support it."""
    try:
        unique_labels = set(int(label) for label in labels)
        if len(unique_labels) < 2 or scaled_features.shape[0] <= len(unique_labels):
            return None, SILHOUETTE_UNAVAILABLE
        return round(float(silhouette_score(scaled_features, labels)), 4), None
    except Exception:
        return None, SILHOUETTE_UNAVAILABLE


def _write_metadata_artifact(metadata: dict[str, Any]) -> None:
    """Persist a human-readable metadata artifact without blocking model training."""
    try:
        MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        return


def load_model_metadata() -> dict[str, Any] | None:
    """Load the human-readable model metadata artifact when available."""
    if MODEL_METADATA_PATH.exists():
        try:
            metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
            if isinstance(metadata, dict):
                return metadata
        except Exception:
            return None
    return None


def _fit_model(
    feature_matrix: np.ndarray,
    *,
    training_source: str,
    training_session_count: int | None = None,
) -> dict[str, object]:
    """Train a KMeans model and build a stable low/medium/high segment mapping."""
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)

    model = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    model.fit(scaled_features)
    silhouette_score_value, silhouette_score_note = _compute_silhouette_score(scaled_features, model.labels_)

    raw_centers = scaler.inverse_transform(model.cluster_centers_)
    ranked_clusters = sorted(
        range(len(raw_centers)),
        key=lambda index: _cluster_engagement_score(raw_centers[index]),
    )
    cluster_to_segment = {cluster_index: segment for segment, cluster_index in enumerate(ranked_clusters)}

    metadata = _build_metadata(
        training_source=training_source,
        training_session_count=training_session_count or int(feature_matrix.shape[0]),
        silhouette_score_value=silhouette_score_value,
        silhouette_score_note=silhouette_score_note,
    )
    payload = {
        "model": model,
        "scaler": scaler,
        "feature_names": FEATURE_NAMES,
        "cluster_to_segment": cluster_to_segment,
        "metadata": metadata,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, MODEL_PATH)
    _write_metadata_artifact(metadata)
    return payload


def train_and_save_model(
    feature_matrix: np.ndarray,
    *,
    training_source: str = "real_db_sessions",
    training_session_count: int | None = None,
) -> Path:
    """Train a model from the provided feature matrix and persist it to disk."""
    if feature_matrix.ndim != 2:
        raise ValueError("feature_matrix must be a 2D array")
    if feature_matrix.shape[1] != len(FEATURE_NAMES):
        raise ValueError(f"feature_matrix must have {len(FEATURE_NAMES)} columns")
    if feature_matrix.shape[0] < 3:
        raise ValueError("Need at least 3 sessions to train a 3-cluster model")

    _fit_model(
        feature_matrix.astype(float),
        training_source=training_source,
        training_session_count=training_session_count,
    )
    return MODEL_PATH


def _fit_default_model() -> dict[str, object]:
    """Train and persist the fallback synthetic model."""
    feature_matrix = _generate_synthetic_sessions()
    return _fit_model(
        feature_matrix,
        training_source="synthetic_fallback",
        training_session_count=int(feature_matrix.shape[0]),
    )


def _load_or_train_model() -> dict[str, object]:
    """Load the persisted model or train and save it if missing."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return _fit_default_model()


def ensure_model() -> Path:
    """Ensure the model exists on disk and return its path."""
    _load_or_train_model()
    return MODEL_PATH


def score_session(
    page_count: int,
    click_count: int,
    dwell_time_seconds: float,
    unique_products: int = 0,
    add_to_cart_count: int = 0,
    attribute_selection_count: int = 0,
    avg_price: float = 0.0,
    price_stddev: float = 0.0,
    category_diversity: int = 0,
    electronics_ratio: float = 0.0,
    clothing_ratio: float = 0.0,
    beauty_ratio: float = 0.0,
    home_appliances_ratio: float = 0.0,
    books_ratio: float = 0.0,
    sports_ratio: float = 0.0,
) -> int:
    """Score a visitor session into low, medium, or high engagement segments."""
    payload = _load_or_train_model()
    model: KMeans = payload["model"]
    cluster_to_segment: dict[int, int] = payload["cluster_to_segment"]
    scaler: StandardScaler | None = payload.get("scaler")
    feature_names: list[str] = payload.get("feature_names", FEATURE_NAMES[:3])

    feature_map = {
        "page_count": float(page_count),
        "click_count": float(click_count),
        "dwell_time_seconds": float(dwell_time_seconds),
        "unique_products": float(unique_products),
        "add_to_cart_count": float(add_to_cart_count),
        "attribute_selection_count": float(attribute_selection_count),
        "avg_price": float(avg_price),
        "price_stddev": float(price_stddev),
        "category_diversity": float(category_diversity),
        "electronics_ratio": float(electronics_ratio),
        "clothing_ratio": float(clothing_ratio),
        "beauty_ratio": float(beauty_ratio),
        "home_appliances_ratio": float(home_appliances_ratio),
        "books_ratio": float(books_ratio),
        "sports_ratio": float(sports_ratio),
    }
    features = np.array([[feature_map.get(name, 0.0) for name in feature_names]], dtype=float)

    if scaler is not None:
        features = scaler.transform(features)

    cluster = int(model.predict(features)[0])
    return cluster_to_segment[cluster]
